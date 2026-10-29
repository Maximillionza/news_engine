"""
Tests for webapp/release_poller.py (ACT Task 3): the release-time poller that
fills official actuals within minutes of the release. Temp dashboard and ops
DBs, a fake `fetch` and fixed clocks only: no network, no real thread (the
suite's conftest switches the poller off).
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import threading
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from data_layer.calendar_feed import EconomicEvent, classify_surprise
from data_layer.official_actuals.fetch import FetchOutcome, series_key
from data_layer.official_actuals.http import SourceRateLimited
from data_layer.official_actuals.registry import OFFICIAL_SPECS, OfficialSpec, ReestimateEvidence
from ops import state as ops_state
from webapp import release_poller as poller
from webapp import store as ws

UTC = dt.timezone.utc
D = dt.date
RELEASE = dt.datetime(2026, 10, 29, 12, 30, tzinfo=UTC)
PCE = "Core PCE Price Index m/m"


def at(hour: int, minute: int, second: int = 0, day: int = 29) -> dt.datetime:
    return dt.datetime(2026, 10, day, hour, minute, second, tzinfo=UTC)


# ---------------------------------------------------------------- fixtures

class FakeFetch:
    """A scripted `fetch`: returns `outcome` (or the result of `outcome(specs)`), recording every call."""

    def __init__(self, outcome=None) -> None:
        self.outcome = outcome if outcome is not None else FetchOutcome({}, {})
        self.calls: list[tuple[list[OfficialSpec], dt.date]] = []

    def __call__(self, specs: list[OfficialSpec], since: dt.date) -> FetchOutcome:
        self.calls.append((list(specs), since))
        return self.outcome(specs) if callable(self.outcome) else self.outcome


@pytest.fixture
def conns(tmp_path):
    dash = ws.get_connection(tmp_path / "dash.db")
    ops = ops_state.get_connection(tmp_path / "ops.db")
    yield dash, ops
    dash.close()
    ops.close()


def _row(conn, title: str, when: dt.datetime, forecast: Optional[str] = None, previous: Optional[str] = None,
         actual: Optional[str] = None, source: str = "live", country: str = "USD") -> int:
    stamp = when.isoformat()
    cur = conn.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, stamp, forecast, previous, actual, None, stamp, stamp, source, "High", country))
    conn.commit()
    return cur.lastrowid


def _get(conn, row_id: int):
    return conn.execute("SELECT * FROM event_history WHERE id = ?", (row_id,)).fetchone()


def _outcome(title: str, data: dict, **extra) -> FetchOutcome:
    return FetchOutcome({series_key(OFFICIAL_SPECS[title]): data}, extra.get("errors", {}),
                        extra.get("evidence", {}))


def _tick(conn, ops, now, state, fetch, enabled=frozenset({PCE})):
    return poller.run_tick(conn, ops, now, state, fetch, enabled)


# ---------------------------------------------------------------- cadence

def test_poll_due_cadence():
    due = poller.poll_due
    assert due(RELEASE, None, at(12, 30, 0)) is True                       # never polled, at the release
    assert due(RELEASE, at(12, 30, 0), at(12, 30, 30)) is False
    assert due(RELEASE, at(12, 30, 0), at(12, 31, 0)) is True              # 60 s cadence to T+15
    assert due(RELEASE, at(12, 44, 0), at(12, 45, 0)) is True              # T+15 min still fast
    assert due(RELEASE, at(12, 45, 0), at(12, 46, 0)) is False             # slow: 5 min cadence
    assert due(RELEASE, at(12, 45, 0), at(12, 50, 0)) is True
    assert due(RELEASE, None, at(14, 30, 1)) is False                      # handed over after T+2 h
    assert due(RELEASE, at(14, 25, 0), at(14, 30, 0)) is True              # T+2 h itself still polled
    assert due(RELEASE, None, at(12, 29, 59)) is False                     # before the release: never


def test_backoff_never_exceeds_fast_cadence_inside_15_minutes():
    one = lambda: 1.0  # noqa: E731 - jitter at its maximum
    for failures in range(1, 7):
        assert poller.backoff_seconds(failures, True, rand=one) <= poller.FAST_POLL_SECONDS + poller.JITTER_SECONDS
    assert poller.backoff_seconds(3, True, rand=one, retry_after=600) <= 70
    slow = [poller.backoff_seconds(f, False, rand=lambda: 0.0) for f in range(1, 7)]
    assert slow == [60, 120, 240, 480, 900, 900]
    assert poller.backoff_seconds(1, False, rand=one) == 60 + poller.JITTER_SECONDS
    # Retry-After lengthens a slow back-off but never beyond the slow cap.
    assert poller.backoff_seconds(1, False, rand=lambda: 0.0, retry_after=600) == 600
    assert poller.backoff_seconds(1, False, rand=lambda: 0.0, retry_after=5000) == poller.SLOW_BACKOFF_CAP_SECONDS


# ---------------------------------------------------------------- fills

def test_tick_fills_with_publisher_source_and_classified_direction(conns):
    dash, ops = conns
    row = _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    fetch = FakeFetch(_outcome(PCE, {D(2026, 9, 1): 0.4}))
    report = _tick(dash, ops, at(12, 30, 5), poller.PollerState(), fetch)
    got = _get(dash, row)
    assert got["actual"] == "0.4%" and got["source"] == "bea"
    expected = classify_surprise(EconomicEvent(PCE, "USD", "High", RELEASE, forecast="0.3%", previous="0.2%",
                                               actual="0.4%"))
    assert expected == "higher"
    assert got["surprise_direction"] == expected
    assert report.filled == [(PCE, RELEASE.isoformat(), "0.4%", "bea")]
    status = ops_state.get_source_status(ops)["bea"]
    assert status.last_ok_utc == at(12, 30, 5) and status.last_error_utc is None


def test_tick_writes_nothing_before_publication(conns):
    dash, ops = conns
    row = _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    fetch = FakeFetch(_outcome(PCE, {D(2026, 8, 1): 0.2}))                    # data only through August
    report = _tick(dash, ops, at(12, 30, 5), poller.PollerState(), fetch)
    assert _get(dash, row)["actual"] is None
    assert report.filled == [] and report.waiting == [(PCE, RELEASE.isoformat(), "awaiting publication")]
    assert ops_state.get_source_status(ops)["bea"].last_ok_utc is not None


def test_tick_passes_reestimate_evidence(conns):
    dash, ops = conns
    title = "Prelim GDP q/q"
    when = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC)
    row = _row(dash, title, when, forecast="1.5%", previous="1.5%")
    data = {D(2026, 4, 1): 1.5}                                               # unchanged re-estimate
    stale = FakeFetch(_outcome(title, data, evidence={
        series_key(OFFICIAL_SPECS[title]): ReestimateEvidence(last_revised=D(2026, 7, 30))}))
    now = dt.datetime(2026, 8, 26, 12, 31, tzinfo=UTC)
    _tick(dash, ops, now, poller.PollerState(), stale, enabled=frozenset({title}))
    assert _get(dash, row)["actual"] is None
    fresh = FakeFetch(_outcome(title, data, evidence={
        series_key(OFFICIAL_SPECS[title]): ReestimateEvidence(last_revised=D(2026, 8, 26))}))
    _tick(dash, ops, now, poller.PollerState(), fresh, enabled=frozenset({title}))
    got = _get(dash, row)
    assert got["actual"] == "1.5%" and got["source"] == "bea"


def test_tick_never_overwrites_existing_actual(conns):
    dash, ops = conns
    done = _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%", actual="0.3%", source="fred")
    fetch = FakeFetch(_outcome(PCE, {D(2026, 9, 1): 0.4}))
    report = _tick(dash, ops, at(12, 31), poller.PollerState(), fetch)
    assert fetch.calls == []                                                  # nothing to poll
    got = _get(dash, done)
    assert (got["actual"], got["source"]) == ("0.3%", "fred") and report.filled == []

    # A row filled by someone else between the fetch and the write: no write, reported, not retried.
    racing = _row(dash, PCE, at(12, 30, day=30), forecast="0.3%", previous="0.2%")
    state = poller.PollerState()

    def racer(specs):
        dash.execute("UPDATE event_history SET actual = '0.5%', source = 'fred' WHERE id = ?", (racing,))
        dash.commit()
        return _outcome(PCE, {D(2026, 9, 1): 0.4})

    report = _tick(dash, ops, at(12, 31, day=30), state, FakeFetch(racer))
    assert _get(dash, racing)["actual"] == "0.5%" and _get(dash, racing)["source"] == "fred"
    assert report.filled == [] and any(reason == "already has an actual" for _t, _w, reason in report.waiting)
    again = FakeFetch(_outcome(PCE, {D(2026, 9, 1): 0.4}))
    _tick(dash, ops, at(12, 32, day=30), state, again)
    assert again.calls == []


def test_tick_writes_nothing_on_source_error(conns):
    dash, ops = conns
    row = _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    state = poller.PollerState()
    fetch = FakeFetch(FetchOutcome({}, {"bea": SourceRateLimited("busy")}))
    now = at(12, 30, 5)
    report = _tick(dash, ops, now, state, fetch)
    assert _get(dash, row)["actual"] is None and report.filled == []
    status = ops_state.get_source_status(ops)["bea"]
    assert status.last_error_utc == now and status.last_error == "SourceRateLimited"
    assert state.failures["bea"] == 1 and report.errors == {"bea": "SourceRateLimited"}


def test_tick_only_polls_enabled_titles_and_usd_rows(conns):
    dash, ops = conns
    _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    foreign = _row(dash, PCE, RELEASE + dt.timedelta(minutes=1), forecast="0.3%", previous="0.2%", country="EUR")
    suspect = _row(dash, "CPI m/m", RELEASE, forecast="0.3%", previous="0.2%")
    fetch = FakeFetch(_outcome(PCE, {D(2026, 9, 1): 0.4}))
    _tick(dash, ops, at(12, 32), poller.PollerState(), fetch)                 # only PCE is enabled
    assert len(fetch.calls) == 1
    specs = fetch.calls[0][0]
    assert [s.series for s in specs] == [OFFICIAL_SPECS[PCE].series]
    assert _get(dash, foreign)["actual"] is None and _get(dash, suspect)["actual"] is None


def test_tick_batches_bls_titles_into_one_fetch_call(conns):
    dash, ops = conns
    titles = ["CPI m/m", "CPI y/y", "Core CPI m/m", "Core CPI y/y"]
    for title in titles:
        _row(dash, title, RELEASE, forecast="0.3%", previous="0.2%")
    fetch = FakeFetch()
    state = poller.PollerState()
    _tick(dash, ops, at(12, 30, 5), state, fetch, enabled=frozenset(titles))
    assert len(fetch.calls) == 1 and len(fetch.calls[0][0]) == 4
    assert state.bls_calls == 1


def test_rate_limited_source_is_retried_inside_window(conns):
    dash, ops = conns
    row = _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    state = poller.PollerState()
    failing = FakeFetch(FetchOutcome({}, {"bea": SourceRateLimited("busy", retry_after_seconds=600)}))
    for minute in (30, 31, 32, 33):
        _tick(dash, ops, at(12, minute), state, failing)
    assert len(failing.calls) == 4                                            # one poll per minute, no gap
    assert state.failures["bea"] == 4
    ok = FakeFetch(_outcome(PCE, {D(2026, 9, 1): 0.4}))
    _tick(dash, ops, at(12, 34), state, ok)
    assert _get(dash, row)["actual"] == "0.4%"
    assert state.failures.get("bea", 0) == 0 and "bea" not in state.retry_at


def test_slow_window_source_in_backoff_is_skipped(conns):
    dash, ops = conns
    row = _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    state = poller.PollerState()
    failing = FakeFetch(FetchOutcome({}, {"bea": SourceRateLimited("busy")}))
    _tick(dash, ops, at(12, 50), state, failing)                              # T+20 min: slow window
    assert at(12, 50) + dt.timedelta(seconds=60) <= state.retry_at["bea"] <= at(12, 50) + dt.timedelta(seconds=70)
    state.retry_at["bea"] = at(13, 10)                                        # as after a run of failures
    quiet = FakeFetch(_outcome(PCE, {D(2026, 9, 1): 0.4}))
    _tick(dash, ops, at(12, 55), state, quiet)                                # due by cadence, but backing off
    assert quiet.calls == [] and _get(dash, row)["actual"] is None
    _tick(dash, ops, at(13, 11), state, quiet)                                # back-off over
    assert len(quiet.calls) == 1 and _get(dash, row)["actual"] == "0.4%"


# ---------------------------------------------------------------- catch-up

def test_catch_up_polls_missed_release_once_after_wake(conns):
    dash, ops = conns
    row = _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    old = _row(dash, PCE, at(12, 30, day=20), forecast="0.3%", previous="0.2%")      # 9 days ago
    state = poller.PollerState(catchup_due=False, last_tick_utc=at(8, 0))
    poller.note_wake(state, at(15, 0), planned_sleep_seconds=300)
    assert state.catchup_due is True
    fetch = FakeFetch(_outcome(PCE, {}))                                      # published? no data: stays waiting
    _tick(dash, ops, at(15, 0), state, fetch)
    assert len(fetch.calls) == 1 and state.catchup_due is False
    _tick(dash, ops, at(15, 1), state, fetch)
    assert len(fetch.calls) == 1                                              # not polled again
    assert _get(dash, row)["actual"] is None and _get(dash, old)["actual"] is None


def test_note_wake_only_after_a_long_gap():
    state = poller.PollerState(catchup_due=False, last_tick_utc=at(12, 0))
    poller.note_wake(state, at(12, 5, 20), planned_sleep_seconds=300)          # 320 s <= 300 + 120
    assert state.catchup_due is False
    poller.note_wake(state, at(12, 20), planned_sleep_seconds=300)
    assert state.catchup_due is True


def test_catch_up_fills_a_missed_row_on_start(conns):
    dash, ops = conns
    recent = _row(dash, PCE, at(12, 30, day=27), forecast="0.3%", previous="0.2%")   # 2 days ago, never revised later
    too_old = _row(dash, PCE, at(12, 30, day=20), forecast="0.3%", previous="0.2%")
    fetch = FakeFetch(_outcome(PCE, {D(2026, 9, 1): 0.4}))
    state = poller.PollerState()                                              # fresh: catchup_due
    _tick(dash, ops, at(15, 0), state, fetch)
    assert len(fetch.calls) == 1
    assert _get(dash, too_old)["actual"] is None
    # The 27th row has a later release? No: the next PCE row (the 20th) is earlier, so it is the latest.
    assert _get(dash, recent)["actual"] == "0.4%"


def test_catch_up_retries_a_source_that_was_backing_off(conns):
    dash, ops = conns
    _row(dash, PCE, at(12, 30, day=27), forecast="0.3%", previous="0.2%")
    state = poller.PollerState()
    failing = FakeFetch(FetchOutcome({}, {"bea": SourceRateLimited("busy")}))
    _tick(dash, ops, at(15, 0), state, failing)
    assert state.catchup_due is True                                          # the source failed: not done yet
    ok = FakeFetch(_outcome(PCE, {D(2026, 9, 1): 0.4}))
    later = at(15, 0) + dt.timedelta(seconds=1000)
    _tick(dash, ops, later, state, ok)
    assert len(ok.calls) == 1 and state.catchup_due is False


def test_bls_daily_budget_skips_slow_window_only(conns):
    dash, ops = conns
    slow = _row(dash, "CPI m/m", at(12, 30), forecast="0.3%", previous="0.2%")
    fast = _row(dash, "Core CPI m/m", at(13, 35), forecast="0.3%", previous="0.2%")
    state = poller.PollerState(bls_day=D(2026, 10, 29), bls_calls=poller.BLS_DAILY_BUDGET)
    fetch = FakeFetch()
    both = frozenset({"CPI m/m", "Core CPI m/m"})
    _tick(dash, ops, at(13, 40), state, fetch, enabled=both)
    assert len(fetch.calls) == 1
    assert [s.series for s in fetch.calls[0][0]] == [OFFICIAL_SPECS["Core CPI m/m"].series]
    # A new UTC day resets the counter.
    _tick(dash, ops, at(0, 5, day=30), state, FakeFetch(), enabled=both)
    assert state.bls_day == D(2026, 10, 30) and state.bls_calls == 0
    assert _get(dash, slow)["actual"] is None and _get(dash, fast)["actual"] is None


# ---------------------------------------------------------------- sleeping

def test_next_sleep_seconds(conns):
    dash, ops = conns
    enabled = frozenset({PCE})
    state = poller.PollerState(catchup_due=False)
    assert poller.next_sleep_seconds(dash, at(12, 0), state, enabled) == poller.IDLE_SLEEP_SECONDS   # nothing near
    _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    assert poller.next_sleep_seconds(dash, at(12, 28, 30), state, enabled) == 90                   # release in 90 s
    assert poller.next_sleep_seconds(dash, at(12, 30, 10), state, enabled) <= 60                   # due now
    state.last_polled[(PCE, RELEASE.isoformat())] = at(12, 30, 10)
    assert poller.next_sleep_seconds(dash, at(12, 30, 20), state, enabled) == 50                   # next minute
    state.last_polled[(PCE, RELEASE.isoformat())] = at(13, 0)
    assert poller.next_sleep_seconds(dash, at(13, 0, 1), state, enabled) == 299                    # slow cadence


def test_next_sleep_never_spins_on_a_backing_off_source(conns):
    dash, ops = conns
    _row(dash, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    state = poller.PollerState(catchup_due=False)
    state.retry_at["bea"] = at(13, 20)
    now = at(13, 0)
    sleep = poller.next_sleep_seconds(dash, now, state, frozenset({PCE}))
    assert sleep == 300 or sleep >= 5                                          # never a 0-1 s busy loop
    assert sleep >= 5


# ---------------------------------------------------------------- the loop

def test_heartbeat_and_thread_never_dies(tmp_path, capsys):
    db = tmp_path / "loop.db"
    conn = ws.get_connection(db)
    _row(conn, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    conn.close()

    def boom(specs, since):
        raise RuntimeError("https://example.invalid/?key=SECRET")

    state = poller.PollerState()
    seconds = poller.run_iteration(db, state, boom, frozenset({PCE}), lambda: at(12, 31))
    assert seconds > 0
    out = capsys.readouterr().out
    assert "RuntimeError" in out and "SECRET" not in out and "example.invalid" not in out
    runs = ops_state.get_job_runs(ops_state.get_connection())
    assert "actuals_poller" in runs and runs["actuals_poller"].last_exit_code == 0
    # Still alive: a second iteration runs after the failure.
    assert poller.run_iteration(db, state, boom, frozenset({PCE}), lambda: at(12, 32)) > 0


def test_iteration_prints_fills_in_sast(tmp_path, capsys):
    db = tmp_path / "loop.db"
    conn = ws.get_connection(db)
    _row(conn, PCE, RELEASE, forecast="0.3%", previous="0.2%")
    conn.close()
    fetch = FakeFetch(_outcome(PCE, {D(2026, 9, 1): 0.4}))
    poller.run_iteration(db, poller.PollerState(), fetch, frozenset({PCE}), lambda: at(12, 30, 5))
    assert "[release_poller] filled Core PCE Price Index m/m 2026-10-29 14:30 SAST = 0.4% (bea)" in capsys.readouterr().out


def test_conftest_disables_poller():
    assert poller.POLLER_ENABLED is False
    assert poller.start_release_poller() is None


def test_start_release_poller_starts_one_daemon_thread(tmp_path, monkeypatch):
    monkeypatch.setattr(poller, "POLLER_ENABLED", True)
    monkeypatch.setattr(poller, "_started", False)
    db = tmp_path / "loop.db"
    ws.get_connection(db).close()
    ran = threading.Event()

    def stop_sleep(seconds: float) -> None:
        ran.set()
        raise SystemExit                                                       # ends the thread after one pass

    thread = poller.start_release_poller(db, fetch=FakeFetch(), clock=lambda: at(12, 0), sleep=stop_sleep)
    assert thread is not None and thread.daemon and thread.name == "actuals-poller"
    assert ran.wait(10)
    assert poller.start_release_poller(db, fetch=FakeFetch(), sleep=stop_sleep) is None      # only once
    thread.join(10)
