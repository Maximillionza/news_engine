"""
Hourly FRED/ALFRED actuals backfill for Medium/Low USD titles (B8 U2, 2026-10-27).

Root cause: Forex Factory's weekly JSON never carries an `actual`, and both
existing fallbacks (the same-day FRED fast path and the web-fallback queue)
cover only a handful of mostly-High titles, so Medium/Low rows stay NULL
forever. This pass reads the release-day ALFRED vintage
(data_layer/fred_history.py) for every USD row of a mapped title whose actual
is still NULL and fills it, first-writer-wins.

Safety: a fill is written only when FF's own `previous` on the row matches the
FRED reading's previous period (revised or first print) - that is the check
that the right series and units are being read. Non-USD / NULL-country rows
are never touched. Forecast/previous/impact are never modified.

Timing: webapp/scheduler.py starts it via start_backfill_thread() on its own
daemon thread and DB connection, so a slow or hanging FRED pass never delays
the next scheduler cycle (the release / post-release cycles record the essence
call). The scheduler additionally never starts a pass near a release window.
A pass stops on the first transport-level failure (FRED unreachable: no point
waiting out the request timeout once per title) and after
BACKFILL_BUDGET_SECONDS of wall-clock time. Throttled to once an hour; never
raises.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from config.settings import FRED_API_KEY, NY_TZ
from data_layer.calendar_feed import EconomicEvent, classify_surprise
from data_layer.fred_history import (
    FRED_HISTORY_SPECS, FredClient, FredFetchError, FredMaintenanceError, FredTransportError, VintageReading,
    previous_check, releases_between,
)
from scripts.fill_missing_actuals import FillReport
import webapp.store as store

BACKFILL_INTERVAL_SECONDS = 3600
BACKFILL_LOOKBACK_DAYS = 45
# Hard wall-clock cap on one pass (checked between titles). A healthy pass over
# ~28 titles at the request pace below takes ~1-2 min; titles not reached are
# simply retried next hour.
BACKFILL_BUDGET_SECONDS = 300
# FF can list a release a day or two off the FRED vintage date (same window as reading_for_event_date).
_MAX_LAG_DAYS = 3
_MIN_AGE = dt.timedelta(hours=1)          # leave the same-day fast path / FF a chance first
_PACE_SECONDS = 0.6                       # FRED allows 120 requests/min

_last_run_utc: Optional[dt.datetime] = None
# Held for the whole life of a background pass, so passes can never overlap.
_run_lock = threading.Lock()


def default_client() -> Optional[FredClient]:
    """A paced client, or None when no FRED key is configured."""
    return FredClient(FRED_API_KEY, pace_seconds=_PACE_SECONDS) if FRED_API_KEY else None


def _reading_for(readings: list[VintageReading], event_date: dt.date) -> Optional[VintageReading]:
    """The release whose vintage date is in [event_date, event_date + lag], earliest first."""
    window_end = event_date + dt.timedelta(days=_MAX_LAG_DAYS)
    for reading in readings:                      # ascending by vintage date
        if event_date <= reading.vintage_date <= window_end:
            return reading
    return None


def _skip_remaining(report: FillReport, pending: list[tuple[str, list]], reason: str) -> None:
    """Counts every row of the titles not yet attempted as skipped, with one reason per title."""
    for title, title_rows in pending:
        report.skipped += len(title_rows)
        report.skip_reasons.append(f"{title}: {reason}")


def backfill_missing_actuals(
    conn: sqlite3.Connection, client: FredClient, now: dt.datetime, lookback_days: int = BACKFILL_LOOKBACK_DAYS,
    budget_seconds: float = BACKFILL_BUDGET_SECONDS, clock: Callable[[], float] = time.monotonic,
) -> FillReport:
    report = FillReport()
    titles = list(FRED_HISTORY_SPECS)
    placeholders = ",".join("?" for _ in titles)
    rows = conn.execute(
        f"SELECT * FROM event_history WHERE country = 'USD' AND actual IS NULL AND event_title IN ({placeholders}) "
        "AND julianday(event_time_utc) >= julianday(?) AND julianday(event_time_utc) <= julianday(?) "
        "ORDER BY event_time_utc",
        (*titles, (now - dt.timedelta(days=lookback_days)).isoformat(), (now - _MIN_AGE).isoformat()),
    ).fetchall()

    by_title: dict[str, list] = {}
    for row in rows:
        by_title.setdefault(row["event_title"], []).append(row)

    started = clock()
    work = list(by_title.items())
    for index, (title, title_rows) in enumerate(work):
        if clock() - started >= budget_seconds:
            print(f"[actuals_backfill] {budget_seconds:.0f}s budget used, {len(work) - index} titles left for next pass")
            _skip_remaining(report, work[index:], "wall-clock budget exhausted, retried next pass")
            return report
        dates = [dt.datetime.fromisoformat(r["event_time_utc"]).astimezone(NY_TZ).date() for r in title_rows]
        try:
            # One range query per title (cached vintages) instead of one lookup per row.
            readings = releases_between(client, title, min(dates), max(dates) + dt.timedelta(days=_MAX_LAG_DAYS))
        except FredMaintenanceError:
            print("[actuals_backfill] FRED under maintenance, backfill skipped")
            return report
        except FredTransportError as exc:
            # FRED unreachable: every further title would just wait out the same timeout.
            print(f"[actuals_backfill] FRED unreachable, pass aborted: {exc}")
            _skip_remaining(report, work[index:], f"pass aborted, {exc}")
            return report
        except FredFetchError as exc:
            report.skipped += len(title_rows)
            report.skip_reasons.append(f"{title}: {exc}")
            continue
        for row, event_date in zip(title_rows, dates):
            where = f"{title}@{row['event_time_utc']}"
            reading = _reading_for(readings, event_date)
            if reading is None:
                report.skipped += 1
                report.skip_reasons.append(f"{where}: no FRED release within {_MAX_LAG_DAYS} days")
                continue
            if previous_check(reading, row["previous"]) != "match":
                report.skipped += 1
                report.skip_reasons.append(f"{where}: previous does not match FRED, not filled")
                continue
            event = EconomicEvent(title, "USD", row["impact"] or "Low", dt.datetime.fromisoformat(row["event_time_utc"]),
                                  forecast=row["forecast"], previous=row["previous"], actual=reading.actual)
            if store.fill_actual_if_missing(conn, row["id"], reading.actual, classify_surprise(event), "fred", now):
                report.written += 1
            else:
                report.skipped += 1
                report.skip_reasons.append(f"{where}: filled by another writer meanwhile")
    return report


def _throttled(now: dt.datetime) -> bool:
    return _last_run_utc is not None and (now - _last_run_utc).total_seconds() < BACKFILL_INTERVAL_SECONDS


def maybe_backfill(
    conn: sqlite3.Connection, now: dt.datetime, client_factory: Callable[[], Optional[FredClient]] = default_client,
) -> Optional[FillReport]:
    """Synchronous pass. Runs at most once per BACKFILL_INTERVAL_SECONDS; None when throttled, keyless, or on any error."""
    global _last_run_utc
    if _throttled(now):
        return None
    try:
        client = client_factory()
        if client is None:
            return None                       # no key: don't start the hourly gate
        _last_run_utc = now                   # set before the run so a failing run waits an hour too
        return backfill_missing_actuals(conn, client, now)
    except Exception as exc:  # noqa: BLE001 - the scheduler cycle must never be broken by the backfill
        print(f"[actuals_backfill] WARNING: backfill failed: {type(exc).__name__}")
        return None


def start_backfill_thread(
    db_path: Optional[Path], now: dt.datetime,
    client_factory: Optional[Callable[[], Optional[FredClient]]] = None,
) -> Optional[threading.Thread]:
    """
    Non-blocking: runs maybe_backfill on a daemon thread with its own DB
    connection and returns that thread, or None (nothing started) when
    throttled, keyless, a previous pass is still running, or on any error.
    The throttle and key checks happen here, so an idle hour costs no thread.
    """
    try:
        if _throttled(now):
            return None
        client = (client_factory or default_client)()   # resolved at call time so tests can patch default_client
        if client is None:
            return None                       # no key: don't start the hourly gate
        if not _run_lock.acquire(blocking=False):
            return None                       # a pass is still running; never overlap two
    except Exception as exc:  # noqa: BLE001
        print(f"[actuals_backfill] WARNING: backfill not started: {type(exc).__name__}")
        return None

    def _worker() -> None:
        try:
            conn = store.get_connection(db_path)
            try:
                report = maybe_backfill(conn, now, lambda: client)
            finally:
                conn.close()
            if report is not None and report.written > 0:
                print(f"[actuals_backfill] filled {report.written}")
        except Exception as exc:  # noqa: BLE001 - a background pass must die quietly
            print(f"[actuals_backfill] WARNING: backfill error: {type(exc).__name__}")
        finally:
            _run_lock.release()

    thread = threading.Thread(target=_worker, name="actuals-backfill", daemon=True)
    try:
        thread.start()
    except Exception as exc:  # noqa: BLE001
        _run_lock.release()
        print(f"[actuals_backfill] WARNING: backfill thread not started: {type(exc).__name__}")
        return None
    return thread
