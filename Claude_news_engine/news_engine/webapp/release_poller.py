"""
Release-time poller for official-publisher actuals (ACT Task 3).

Runs on its own daemon thread (started once by webapp.scheduler.start_scheduler)
and gets every numeric USD release its actual from the official publisher
(data_layer/official_actuals) within minutes of the release time, instead of
waiting for Forex Factory or the hourly FRED backfill, which both stay as they
are. FF remains the calendar: only rows already in event_history are polled,
and only for titles whose gate result is `verified` (gate_results.json).

Cadence per row: every 60 s from the release time to T+15 min, every 5 min to
T+2 h, then handed over to the hourly backfill. After a restart or a machine
wake (a gap well beyond the planned sleep) one catch-up pass polls the rows of
the last 7 days that still have no actual, once each.

Failure handling: a publisher error never writes anything. Inside the first 15
minutes the 60 s cadence is kept whatever the back-off says (a 429 must not
cost the window); later the source backs off exponentially with jitter, up to
15 min. BLS (500 queries/day on the v2 key) has a daily budget that only the
slow window respects.

Every write goes through store.fill_actual_if_missing (first writer wins,
never overwrites), with the publisher as the row's `source` and the surprise
direction from classify_surprise() against FF's stored forecast.
"""
from __future__ import annotations

import datetime as dt
import random
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from config.settings import LOCAL_TZ
from data_layer.calendar_feed import EconomicEvent, classify_surprise
from data_layer.official_actuals import keys as official_keys
from data_layer.official_actuals.coverage import enabled_titles, later_release_for, load_gate_results
from data_layer.official_actuals.fetch import FetchOutcome, fetch_for_specs, series_key
from data_layer.official_actuals.http import requests_fetcher
from data_layer.official_actuals.registry import OFFICIAL_SPECS, OfficialSpec, decide_fill
from ops import state as ops_state
from webapp import store

POLLER_ENABLED = True                     # tests/conftest.py sets False
FAST_POLL_SECONDS = 60
SLOW_POLL_SECONDS = 300
FAST_WINDOW = dt.timedelta(minutes=15)
HANDOVER_AFTER = dt.timedelta(hours=2)    # later rows are left to the hourly FRED/ALFRED backfill
CATCHUP_LOOKBACK = dt.timedelta(days=7)
IDLE_SLEEP_SECONDS = 300
WAKE_GAP_SECONDS = 120                    # slack beyond the planned sleep before a gap counts as a wake
FAST_BACKOFF_CAP_SECONDS = 60
SLOW_BACKOFF_CAP_SECONDS = 900
JITTER_SECONDS = 10
BLS_DAILY_BUDGET = 450                    # of the 500 queries/day a registered v2 key allows
MIN_SLEEP_SECONDS = 1.0
_ROW_QUERY_SLACK = dt.timedelta(minutes=1)    # SQL pre-filter margin; the exact window is checked in Python
_MAX_BACKOFF_DOUBLINGS = 10

_UTC = dt.timezone.utc


@dataclass
class PollerState:
    last_polled: dict[tuple[str, str], dt.datetime] = field(default_factory=dict)   # (title, event_time_utc iso)
    failures: dict[str, int] = field(default_factory=dict)                        # consecutive failed requests per source
    retry_at: dict[str, dt.datetime] = field(default_factory=dict)                # source -> no slow-window polls before
    last_tick_utc: Optional[dt.datetime] = None
    catchup_due: bool = True                  # a fresh state is a start: one catch-up pass
    bls_day: Optional[dt.date] = None
    bls_calls: int = 0
    # Beyond the plan's fields: catch-up rows already answered by their publisher (cleared when the pass ends),
    # so a source that was backing off is retried without re-polling the rows that were done, and the sleep
    # the loop planned (the wake check compares the real gap with it).
    catchup_done: set[tuple[str, str]] = field(default_factory=set)
    planned_sleep_seconds: float = float(IDLE_SLEEP_SECONDS)


@dataclass
class TickReport:
    filled: list[tuple[str, str, str, str]]       # (title, event_time_utc iso, actual, source)
    waiting: list[tuple[str, str, str]]           # (title, event_time_utc iso, reason)
    errors: dict[str, str]                        # source -> exception class name


FetchFn = Callable[[list[OfficialSpec], dt.date], FetchOutcome]


def _utc_now() -> dt.datetime:
    return dt.datetime.now(_UTC)


def _parse_utc(text: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(text)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=_UTC)


# ---------------------------------------------------------------- cadence

def poll_due(release_utc: dt.datetime, last_polled: Optional[dt.datetime], now: dt.datetime) -> bool:
    """True when a row released at `release_utc` should be polled at `now` (60 s to T+15, 5 min to T+2 h)."""
    age = now - release_utc
    if age < dt.timedelta(0) or age > HANDOVER_AFTER:
        return False
    if last_polled is None:
        return True
    interval = FAST_POLL_SECONDS if age <= FAST_WINDOW else SLOW_POLL_SECONDS
    return (now - last_polled).total_seconds() >= interval


def backoff_seconds(failures: int, in_fast_window: bool, rand: Callable[[], float] = random.random,
                    retry_after: Optional[float] = None) -> float:
    """
    Seconds to leave a failing source alone: 60 s doubling to 15 min, plus up to
    JITTER_SECONDS. Inside the first 15 minutes it never exceeds the fast cadence
    (and ignores Retry-After): the window is too short to sit out a 429.
    """
    doublings = min(max(failures, 1) - 1, _MAX_BACKOFF_DOUBLINGS)
    base = float(FAST_POLL_SECONDS * 2 ** doublings)
    if in_fast_window:
        return min(base, float(FAST_BACKOFF_CAP_SECONDS)) + JITTER_SECONDS * rand()
    if retry_after is not None:
        base = max(base, retry_after)
    return min(base, float(SLOW_BACKOFF_CAP_SECONDS)) + JITTER_SECONDS * rand()


def note_wake(state: PollerState, now: dt.datetime, planned_sleep_seconds: float) -> None:
    """Arms the catch-up pass when the real gap since the last tick far exceeds the planned sleep (sleep/wake)."""
    if state.last_tick_utc is None:
        return
    gap = (now - state.last_tick_utc).total_seconds()
    if gap > planned_sleep_seconds + WAKE_GAP_SECONDS:
        state.catchup_due = True
        state.catchup_done.clear()


# ---------------------------------------------------------------- rows

def _candidate_rows(conn: sqlite3.Connection, enabled: frozenset[str], start: dt.datetime,
                    end: dt.datetime) -> list[sqlite3.Row]:
    """USD rows of enabled titles with no actual and an event time in (about) [start, end], oldest first."""
    titles = sorted(t for t in enabled if t in OFFICIAL_SPECS)
    if not titles:
        return []
    marks = ",".join("?" for _ in titles)
    return conn.execute(
        f"SELECT * FROM event_history WHERE country = 'USD' AND actual IS NULL AND event_title IN ({marks}) "
        "AND julianday(event_time_utc) BETWEEN julianday(?) AND julianday(?) ORDER BY event_time_utc, id",
        (*titles, (start - _ROW_QUERY_SLACK).isoformat(), (end + _ROW_QUERY_SLACK).isoformat()),
    ).fetchall()


# ---------------------------------------------------------------- one tick

@dataclass
class _Due:
    row: sqlite3.Row
    spec: OfficialSpec
    release: dt.datetime
    catchup: bool

    @property
    def key(self) -> tuple[str, str]:
        return (self.row["event_title"], self.row["event_time_utc"])


def _record_status(ops_conn: sqlite3.Connection, source: str, ok: bool, now: dt.datetime,
                   error: Optional[str] = None) -> None:
    try:
        ops_state.record_source_status(ops_conn, source, ok, now, error)
    except Exception as exc:  # noqa: BLE001 - status is display-only; it must never cost a fill
        print(f"[release_poller] WARNING: source status not recorded: {type(exc).__name__}")


def run_tick(conn: sqlite3.Connection, ops_conn: sqlite3.Connection, now: dt.datetime, state: PollerState,
             fetch: FetchFn, enabled: frozenset[str]) -> TickReport:
    """One polling pass at `now`: select the due rows, fetch once, write what the publishers have published."""
    report = TickReport([], [], {})
    today = now.astimezone(_UTC).date()
    if state.bls_day != today:
        state.bls_day, state.bls_calls = today, 0

    window_start = now - (CATCHUP_LOOKBACK if state.catchup_due else HANDOVER_AFTER)
    due: list[_Due] = []
    catchup_blocked = False
    for row in _candidate_rows(conn, enabled, window_start, now):
        spec = OFFICIAL_SPECS.get(row["event_title"])
        release = _parse_utc(row["event_time_utc"])
        age = now - release
        if spec is None or age < dt.timedelta(0) or age > CATCHUP_LOOKBACK:
            continue
        key = (row["event_title"], row["event_time_utc"])
        catchup = age > HANDOVER_AFTER
        if catchup:
            if not state.catchup_due or key in state.catchup_done:
                continue
        elif not poll_due(release, state.last_polled.get(key), now):
            continue
        in_fast = age <= FAST_WINDOW
        retry_at = state.retry_at.get(spec.source)
        blocked = (retry_at is not None and retry_at > now and not in_fast) or (
            spec.source == "bls" and state.bls_calls >= BLS_DAILY_BUDGET and not in_fast)
        if blocked:
            catchup_blocked = catchup_blocked or catchup
            continue
        due.append(_Due(row, spec, release, catchup))

    if not due:
        if state.catchup_due and not catchup_blocked:
            state.catchup_due = False
            state.catchup_done.clear()
        state.last_tick_utc = now
        return report

    specs: dict[str, OfficialSpec] = {}
    for item in due:
        specs.setdefault(series_key(item.spec), item.spec)
    sources = {item.spec.source for item in due}
    since = min(item.release for item in due).astimezone(_UTC).date()
    if "bls" in sources:
        state.bls_calls += 1

    outcome: Optional[FetchOutcome] = None
    retry_after: dict[str, Optional[float]] = {}
    try:
        outcome = fetch(list(specs.values()), since)
        error_names = {s: type(e).__name__ for s, e in outcome.errors.items() if s in sources}
        retry_after = {s: getattr(e, "retry_after_seconds", None) for s, e in outcome.errors.items()}
    except Exception as exc:  # noqa: BLE001 - fetch_for_specs absorbs SourceError; this is anything else
        print(f"[release_poller] WARNING: fetch failed: {type(exc).__name__}")
        error_names = {s: type(exc).__name__ for s in sources}

    for source in sorted(sources):
        if source in error_names:
            state.failures[source] = state.failures.get(source, 0) + 1
            in_fast = any(d.spec.source == source and not d.catchup and now - d.release <= FAST_WINDOW for d in due)
            state.retry_at[source] = now + dt.timedelta(
                seconds=backoff_seconds(state.failures[source], in_fast, retry_after=retry_after.get(source)))
            report.errors[source] = error_names[source]
            _record_status(ops_conn, source, False, now, error_names[source])
        else:
            state.failures.pop(source, None)
            state.retry_at.pop(source, None)
            _record_status(ops_conn, source, True, now)

    for item in due:
        state.last_polled[item.key] = now
        title, stamp = item.key
        if item.spec.source in error_names or outcome is None:
            continue
        if item.catchup:
            state.catchup_done.add(item.key)
        later_release, later_previous = later_release_for(conn, item.spec, item.release, now)
        decision = decide_fill(
            item.spec, item.release, item.row["forecast"], item.row["previous"],
            outcome.data.get(series_key(item.spec), {}), later_release, later_previous,
            reestimate_evidence=outcome.evidence.get(series_key(item.spec)))
        if decision.actual is None:
            report.waiting.append((title, stamp, decision.reason))
            continue
        event = EconomicEvent(title, "USD", item.row["impact"] or "High", item.release,
                              forecast=item.row["forecast"], previous=item.row["previous"], actual=decision.actual)
        if store.fill_actual_if_missing(conn, item.row["id"], decision.actual, classify_surprise(event),
                                        item.spec.source, now):
            report.filled.append((title, stamp, decision.actual, item.spec.source))
        else:
            report.waiting.append((title, stamp, "already has an actual"))   # filled by someone else meanwhile

    if state.catchup_due and not catchup_blocked and not any(d.catchup and d.spec.source in error_names for d in due):
        state.catchup_due = False
        state.catchup_done.clear()
    state.last_tick_utc = now
    return report


# ---------------------------------------------------------------- sleeping

def _next_midnight(now: dt.datetime) -> dt.datetime:
    return dt.datetime.combine(now.astimezone(_UTC).date() + dt.timedelta(days=1), dt.time(0), tzinfo=_UTC)


def next_sleep_seconds(conn: sqlite3.Connection, now: dt.datetime, state: PollerState,
                       enabled: frozenset[str]) -> float:
    """
    Seconds until the earliest row could next be polled (60 s inside a fast window, a release that is
    due within IDLE_SLEEP_SECONDS counts down to the second); IDLE_SLEEP_SECONDS when nothing is near.
    Honours back-off and the BLS budget so a skipped row never makes the loop spin.
    """
    horizon = now + dt.timedelta(seconds=IDLE_SLEEP_SECONDS)
    bls_calls = state.bls_calls if state.bls_day == now.astimezone(_UTC).date() else 0
    soonest: Optional[dt.datetime] = None
    for row in _candidate_rows(conn, enabled, now - HANDOVER_AFTER, horizon):
        spec = OFFICIAL_SPECS.get(row["event_title"])
        release = _parse_utc(row["event_time_utc"])
        if spec is None or release > horizon:
            continue
        last = state.last_polled.get((row["event_title"], row["event_time_utc"]))
        if last is None:
            ready = max(release, now)
        else:
            fast_next = last + dt.timedelta(seconds=FAST_POLL_SECONDS)
            ready = fast_next if fast_next - release <= FAST_WINDOW else last + dt.timedelta(seconds=SLOW_POLL_SECONDS)
            ready = max(ready, release)
        if ready - release > FAST_WINDOW:                        # slow window: back-off and BLS budget apply
            retry_at = state.retry_at.get(spec.source)
            if retry_at is not None and retry_at > ready:
                ready = retry_at
            if spec.source == "bls" and bls_calls >= BLS_DAILY_BUDGET:
                ready = max(ready, _next_midnight(now))
        if ready - release > HANDOVER_AFTER:
            continue
        soonest = ready if soonest is None or ready < soonest else soonest
    seconds = float(IDLE_SLEEP_SECONDS) if soonest is None else (soonest - now).total_seconds()
    if state.catchup_due:
        seconds = min(seconds, float(FAST_POLL_SECONDS))         # a catch-up row is still waiting on its source
    return min(float(IDLE_SLEEP_SECONDS), max(MIN_SLEEP_SECONDS, seconds))


# ---------------------------------------------------------------- the thread

def _sast_label(stamp: str) -> str:
    return _parse_utc(stamp).astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M SAST")


def run_iteration(db_path: Optional[Path], state: PollerState, fetch: FetchFn, enabled: frozenset[str],
                  clock: Callable[[], dt.datetime]) -> float:
    """
    One loop pass on fresh connections; returns the seconds to sleep. Never raises: any error
    (class name only in the log: messages can carry URLs) leaves a 60 s retry, and the
    `actuals_poller` heartbeat is touched whatever happened (the thread is alive).
    """
    conn: Optional[sqlite3.Connection] = None
    ops_conn: Optional[sqlite3.Connection] = None
    seconds = float(FAST_POLL_SECONDS)
    try:
        now = clock()
        note_wake(state, now, state.planned_sleep_seconds)
        conn = store.get_connection(db_path)
        try:
            ops_conn = ops_state.get_connection()
        except Exception as exc:  # noqa: BLE001 - without the ops DB the poller still fills; status goes nowhere
            print(f"[release_poller] WARNING: ops state unavailable: {type(exc).__name__}")
            ops_conn = sqlite3.connect(":memory:")
        report = run_tick(conn, ops_conn, now, state, fetch, enabled)
        for title, stamp, actual, source in report.filled:
            print(f"[release_poller] filled {title} {_sast_label(stamp)} = {actual} ({source})")
        seconds = next_sleep_seconds(conn, now, state, enabled)
    except Exception as exc:  # noqa: BLE001 - the thread must outlive any single failure
        print(f"[release_poller] ERROR: pass failed, retrying in {FAST_POLL_SECONDS}s: {type(exc).__name__}")
    finally:
        for handle in (conn, ops_conn):
            if handle is not None:
                try:
                    handle.close()
                except Exception:  # noqa: BLE001
                    pass
        ops_state.touch_heartbeat("actuals_poller")
    state.planned_sleep_seconds = seconds
    return seconds


def _default_fetch(specs: list[OfficialSpec], since: dt.date) -> FetchOutcome:
    # Keys are read per call (from .env via config.settings), never kept or logged here.
    return fetch_for_specs(specs, since, requests_fetcher(), official_keys.load_keys())


_started = False
_start_lock = threading.Lock()


def start_release_poller(db_path: Optional[Path] = None, *, fetch: Optional[FetchFn] = None,
                         clock: Callable[[], dt.datetime] = _utc_now,
                         sleep: Callable[[float], None] = time.sleep) -> Optional[threading.Thread]:
    """
    Starts the `actuals-poller` daemon thread; None when disabled (tests) or already started in this process.
    The verified-title list is read once, at start: re-running the gate means a restart.
    """
    global _started
    if not POLLER_ENABLED:
        return None
    with _start_lock:
        if _started:
            return None
        _started = True
    enabled = enabled_titles(load_gate_results())
    fetch_fn: FetchFn = fetch if fetch is not None else _default_fetch
    state = PollerState()

    def _loop() -> None:
        while True:
            sleep(run_iteration(db_path, state, fetch_fn, enabled, clock))

    thread = threading.Thread(target=_loop, name="actuals-poller", daemon=True)
    thread.start()
    print(f"[release_poller] started: {len(enabled)} verified title(s)")
    return thread
