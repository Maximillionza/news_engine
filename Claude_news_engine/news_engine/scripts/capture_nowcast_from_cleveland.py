"""
Deterministic LIVE capture of the Cleveland Fed CPI nowcast for the scheduler (spec 2026-10-15 section 6.1 Freshness).
No LLM and no hand-typed numbers: the value comes straight from the Fed's published nowcast_month.json.

What it does, once per run:
  1. Finds USD rows in event_history for the formula-tier Tier 1 titles ("CPI m/m" / "Core CPI m/m", from
     data_layer.tier1_events) whose release time is within the window (strictly after now; --window-hours,
     default 48; the weekly Windows task uses 192 so a release 8 days out is captured early). If there are
     none - the common case - it says so and does nothing, without even downloading the file.
  2. Downloads nowcast_month.json once (60 s timeout, descriptive User-Agent), finds the chart for each
     release's reference month (the month before the release month), and takes that chart's LAST non-blank
     nowcast value dated before the release day.
  3. Records it as a LIVE snapshot via scripts/capture_nowcast_snapshot.capture() with as_of = the real fetch
     time (capture refuses anything after the release). The store is append-only; a later run adds a newer
     snapshot, which is intended: the latest pre-release snapshot is the one scored.
  4. Writes the dashboard's Tier 1 call (B3): one tier1_predictions row per tracked instrument via
     webapp.tier1_formula (nowcast vs the event's forecast, source "Cleveland Fed nowcast (formula)",
     confidence "Likely"), only when the nowcast differs from the last formula row for that occurrence.
     No readable forecast -> no row (never a guessed neutral); it is reported as TIER1 PENDING, and counts
     as skipped (exit 2) once the release is within MISSING_FORECAST_ALERT_WITHIN.

It never writes a value it could not parse, never falls back to an older slot when the newest one is unreadable,
and refuses a value dated more than MAX_VALUE_AGE_DAYS before now (the snapshot is stamped as of the fetch time,
so a stale Fed value must not be passed off as fresh). A fetch failure exits 1 with a clear message; releases
due but skipped exit 2 so the scheduler notices.

Usage:
    python scripts/capture_nowcast_from_cleveland.py [--dry-run] [--window-hours H] [--dash-db PATH] [--bt-db PATH]
Defaults are the app's live databases; dashboard.db is only ever opened read-only (mode=ro; it supplies the
releases, their forecasts and the tracked instruments). --dry-run prints what would be captured and the Tier 1
rows that would be written, and writes nothing (it does not even open the backtest DB).

Data is CC BY 4.0 (Cleveland Fed Inflation Nowcasting); the attribution stays in the snapshot's source column.
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional

import requests

# Allow `python scripts/capture_nowcast_from_cleveland.py ...` (script dir, not the app root, is on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_layer.tier1_events import TIER1_FORMULA, TIER1_FORMULA_SOURCE, tier1_titles  # noqa: E402
from scoring import backtest_store  # noqa: E402
from scripts.backfill_tier1_reconstructed import open_dash_readonly  # noqa: E402
from scripts.capture_nowcast_snapshot import capture  # noqa: E402
from scripts.cleveland_nowcast_to_csv import SERIES_MAP, SOURCE, _series, _slot_dates  # noqa: E402
from webapp.store import list_tracked_symbols  # noqa: E402
from webapp.tier1_formula import record_formula_calls  # noqa: E402

UTC = dt.timezone.utc
NOWCAST_URL = "https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json"
USER_AGENT = "news-fundamental-engine/0.1 (scheduled Cleveland Fed inflation nowcast capture; CC BY 4.0 attribution kept)"
FETCH_TIMEOUT_SECONDS = 60
WINDOW = dt.timedelta(hours=48)       # default: a release is "upcoming" when it is strictly after now and within this long
MAX_WINDOW_HOURS = 240                # --window-hours ceiling (the weekly task uses 192 = 8 days)
MISSING_FORECAST_ALERT_WITHIN = dt.timedelta(hours=24)   # no forecast this close to the release -> exit 2
MAX_DAYS_PAST_CHART = 45             # a release further than this after the chart's last date label is not that chart's
MAX_VALUE_AGE_DAYS = 5                # the Fed updates every business day; a long weekend is at most 4 days


class FetchError(RuntimeError):
    """The Cleveland Fed file could not be downloaded or is not the document we expect."""


def fetch_cleveland_json(http_get: Callable = requests.get):
    """Download and parse nowcast_month.json once. Raises on any HTTP or JSON problem."""
    resp = http_get(NOWCAST_URL, timeout=FETCH_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return resp.json()


# --- pure parsing --------------------------------------------------------------------------------

def _reference_month(release: dt.datetime) -> tuple[int, int]:
    """CPI for month M is released in month M+1, so the chart is the one for the month before the release."""
    year, month = release.year, release.month - 1
    return (year - 1, 12) if month == 0 else (year, month)


def _find_chart(charts: Iterable[dict], ref: tuple[int, int]) -> Optional[dict]:
    for chart in charts:
        try:
            year, month = (int(part) for part in chart["chart"]["subcaption"].split("-"))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if (year, month) == ref:
            return chart
    return None


def _reading(title: str, release: dt.datetime, value: Optional[float] = None,
             value_date: Optional[dt.date] = None, reason: Optional[str] = None) -> dict:
    return {"event_title": title, "release_utc": release, "value": value, "value_date": value_date, "reason": reason}


def _is_blank(text) -> bool:
    """A slot with no value: the file may hold "", null (None, or the string "None" after str()) or spaces."""
    return text is None or str(text).strip().lower() in ("", "none")


def _latest_for_release(charts: list[dict], title: str, release: dt.datetime) -> dict:
    if title not in SERIES_MAP:
        return _reading(title, release, reason="not a CPI-family title")
    ref = _reference_month(release)
    chart = _find_chart(charts, ref)
    if chart is None:
        return _reading(title, release, reason=f"no Cleveland Fed chart for reference month {ref[0]}-{ref[1]}")
    nowcast_name, actual_name = SERIES_MAP[title]
    release_day = release.date()
    try:
        dates = _slot_dates(chart)
        values = _series(chart, nowcast_name)
        actuals = _series(chart, actual_name)
        if len(values) != len(dates) or len(actuals) != len(dates):
            raise ValueError("series length does not match its date labels")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return _reading(title, release, reason=f"could not read the Fed chart: {exc}")

    # Released month: the converter finds the release day from the Actual series; do the same. Our release
    # is upcoming, so a chart that already has an actual is not the chart for it (matching day or not).
    released = [i for i, text in enumerate(actuals) if not _is_blank(text)]
    if released:
        return _reading(title, release, reason=(
            f"the Fed chart already shows an actual for this release (marked {dates[released[0]]}, ours {release_day})"))

    # Month arithmetic picked the chart; confirm it really belongs to this release (a delayed release must
    # not be matched to the next month's unreleased chart).
    if not dates or dates[0] > release_day:
        return _reading(title, release, reason=(
            f"the Fed chart for {ref[0]}-{ref[1]} starts after the release day ({release_day})"))
    if release_day > dates[-1] + dt.timedelta(days=MAX_DAYS_PAST_CHART):
        return _reading(title, release, reason=(
            f"the release ({release_day}) is more than {MAX_DAYS_PAST_CHART} days after the last date in the "
            f"Fed chart for {ref[0]}-{ref[1]} ({dates[-1]}): not this chart's release"))
    if all(_is_blank(text) for text in values):
        return _reading(title, release, reason=f"no non-blank {nowcast_name} value in the Fed chart for {ref[0]}-{ref[1]}")

    # Last non-blank slot dated strictly before the release day (the release-day slot is never used).
    for date, text in zip(reversed(dates), reversed(values)):
        if date >= release_day or _is_blank(text):
            continue
        try:
            value = float(str(text).strip())
        except ValueError:
            value = math.nan
        if not math.isfinite(value):
            return _reading(title, release, value_date=date, reason=f"could not parse the latest value {text!r} dated {date}")
        return _reading(title, release, value=value, value_date=date)
    return _reading(title, release, reason="no nowcast value before the release day in the Fed chart")


def latest_nowcasts(json_data, release_dates: Iterable[tuple[str, dt.datetime]]) -> list[dict]:
    """
    For each (title, release_utc): the LAST non-blank nowcast in that release's chart and its date.
    Returns one dict per release: {"event_title", "release_utc", "value", "value_date", "reason"}; when the
    value cannot be taken, value and value_date are None and `reason` says why (nothing is guessed, and an
    unreadable newest slot is never replaced by an older one). Pure: no network, no database.
    """
    if not isinstance(json_data, list):
        raise ValueError(f"expected a list of charts, got {type(json_data).__name__}")
    return [_latest_for_release(json_data, title, release) for title, release in release_dates]


# --- run -----------------------------------------------------------------------------------------

def _due_releases(dash_conn, now: dt.datetime,
                  window: dt.timedelta = WINDOW) -> list[tuple[str, dt.datetime, Optional[str]]]:
    """(title, release_utc, forecast_text) for every formula-tier release strictly after now and within window."""
    titles = tier1_titles(TIER1_FORMULA)
    marks = ",".join("?" for _ in titles)
    rows = dash_conn.execute(
        f"SELECT DISTINCT event_title, event_time_utc, forecast FROM event_history "
        f"WHERE country = 'USD' AND event_title IN ({marks})", titles).fetchall()
    due = []
    for row in rows:
        title, when, forecast = row[0], row[1], row[2]
        try:
            release = dt.datetime.fromisoformat(when)
        except (TypeError, ValueError):
            continue
        release = release.replace(tzinfo=UTC) if release.tzinfo is None else release.astimezone(UTC)
        if now < release <= now + window:
            due.append((title, release, forecast))
    return sorted(due, key=lambda item: (item[1], item[0]))


def _record_tier1(summary: dict, bt_conn, title: str, release: dt.datetime, nowcast: float,
                  forecast: Optional[str], value_date: dt.date, symbols: list[str], now: dt.datetime,
                  dry_run: bool) -> None:
    """Write (or report) the formula Tier 1 rows for one captured release into the run summary."""
    release_iso = release.isoformat()
    result = record_formula_calls(bt_conn, title, release, nowcast, forecast, value_date, symbols, now,
                                  dry_run=dry_run)
    for symbol, direction in result["written"]:
        summary["tier1_rows"].append((title, release_iso, symbol, direction, "written"))
    for symbol in result["unchanged"]:
        # Report the direction actually on the dashboard (the stored row), not a recomputation.
        row = backtest_store.get_latest_tier1_prediction_for_occurrence(
            bt_conn, title, symbol, release, source=TIER1_FORMULA_SOURCE)
        summary["tier1_rows"].append((title, release_iso, symbol, row.predicted_direction, "unchanged"))
    if result["pending"] is not None:
        summary["tier1_pending"].append((title, release_iso, result["pending"]))
        if release - now <= MISSING_FORECAST_ALERT_WITHIN:
            # Too close for the next daily run to fix it: make the scheduler notice (exit 2).
            summary["skipped"].append((title, release_iso, f"no Tier 1 formula call: {result['pending']}"))


def run(dash_conn, bt_conn, now: dt.datetime, fetch: Optional[Callable] = None, dry_run: bool = False,
        window: dt.timedelta = WINDOW) -> dict:
    """
    Capture a live snapshot for every CPI-family release within `window` after `now`, then write the
    dashboard's formula Tier 1 row for each tracked instrument.
    Returns {"captured": [(title, release_iso, value)], "skipped": [(title, release_iso, reason)],
    "tier1_rows": [(title, release_iso, symbol, direction, "written"|"unchanged")],
    "tier1_pending": [(title, release_iso, reason)], "dry_run": bool, "message": str}. With dry_run nothing
    is written (bt_conn may be None) and "captured" / "tier1_rows" list what would be. Raises FetchError if
    the file cannot be fetched or is not a chart list.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError(f"now must be timezone-aware, got naive {now!r}")
    now = now.astimezone(UTC)
    summary: dict = {"captured": [], "skipped": [], "tier1_rows": [], "tier1_pending": [],
                     "dry_run": dry_run, "message": ""}
    due = _due_releases(dash_conn, now, window)
    if not due:
        hours = window.total_seconds() / 3600
        summary["message"] = f"No CPI-family release within {hours:g} hours: nothing to capture."
        return summary
    forecasts = {(title, release): forecast for title, release, forecast in due}
    symbols = list_tracked_symbols(dash_conn)          # read once: every due release uses the same list

    try:
        data = (fetch or fetch_cleveland_json)()
        readings = latest_nowcasts(data, [(title, release) for title, release, _ in due])
    except Exception as exc:  # noqa: BLE001 -- anything here means we have no trustworthy number: fail loud
        raise FetchError(f"could not get the Cleveland Fed nowcast: {exc}") from exc

    for r in readings:
        title, release = r["event_title"], r["release_utc"]
        release_iso = release.isoformat()
        reason = r["reason"]
        if reason is None:
            age_days = (now.date() - r["value_date"]).days
            if age_days > MAX_VALUE_AGE_DAYS:
                reason = f"stale: the latest Fed value is dated {r['value_date']} ({age_days} days before now)"
            elif age_days < -1:
                reason = f"the latest Fed value is dated {r['value_date']}, in the future"
        if reason is not None:
            summary["skipped"].append((title, release_iso, reason))
            continue
        if not dry_run:
            try:
                capture(bt_conn, title, release, r["value"], as_of_utc=now, source=SOURCE)
            except ValueError as exc:       # capture() refuses a snapshot stamped after the release
                summary["skipped"].append((title, release_iso, str(exc)))
                continue
        summary["captured"].append((title, release_iso, r["value"]))
        _record_tier1(summary, bt_conn, title, release, r["value"], forecasts[(title, release)],
                      r["value_date"], symbols, now, dry_run)
    summary["message"] = (f"{'Would capture' if dry_run else 'Captured'} {len(summary['captured'])}, "
                          f"skipped {len(summary['skipped'])}.")
    return summary


# --- CLI -----------------------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None, fetch: Optional[Callable] = None,
         now: Optional[dt.datetime] = None) -> int:
    """fetch and now are test seams; the scheduler uses the defaults (live download, real clock)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print what would be captured; write nothing")
    parser.add_argument("--dash-db", type=Path, default=None, help="dashboard.db to read event_history from (read-only)")
    parser.add_argument("--bt-db", type=Path, default=None, help="backtest_log.db to write snapshots to (default: live)")
    parser.add_argument("--window-hours", type=float, default=WINDOW.total_seconds() / 3600,
                        help="capture releases due within this many hours after now (default 48; weekly task: 192)")
    args = parser.parse_args(argv)
    if not 0 < args.window_hours <= MAX_WINDOW_HOURS:
        parser.error(f"--window-hours must be > 0 and <= {MAX_WINDOW_HOURS}, got {args.window_hours:g}")

    now = now or dt.datetime.now(UTC)
    dash_conn = open_dash_readonly(args.dash_db)
    bt_conn = None if args.dry_run else backtest_store.get_connection(args.bt_db)
    try:
        summary = run(dash_conn, bt_conn, now, fetch, dry_run=args.dry_run,
                      window=dt.timedelta(hours=args.window_hours))
    except FetchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        dash_conn.close()
        if bt_conn is not None:
            bt_conn.close()

    print(summary["message"])
    verb = "WOULD capture" if args.dry_run else "captured"
    for title, release_iso, value in summary["captured"]:
        print(f"  {verb} {title} release {release_iso} nowcast {value:g} (as of {now.isoformat()})")
    for title, release_iso, reason in summary["skipped"]:
        print(f"  SKIPPED {title} release {release_iso}: {reason}")
    for title, _release_iso, symbol, direction, status in summary["tier1_rows"]:
        print(f"  TIER1 {title} {symbol}: {direction} ({'would write' if args.dry_run else status})")
    for title, release_iso, reason in summary["tier1_pending"]:
        print(f"  TIER1 PENDING {title} release {release_iso}: {reason}")
    return 2 if summary["skipped"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
