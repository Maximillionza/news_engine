"""
Tests for webapp/actuals_backfill.py (B8 Task 2) — hourly Medium/Low FRED
actuals backfill. Temp DBs and a fake `requests.get` only.
"""
from __future__ import annotations

import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer import fred_history as fh
from tests.test_fred_history import FakeRequests, FakeResp, _init_obs
from webapp import actuals_backfill as ab
from webapp import store as ws

D = dt.date
UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
JOLTS_TIME = dt.datetime(2026, 10, 7, 14, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _reset_throttle(monkeypatch):
    monkeypatch.setattr(ab, "_last_run_utc", None)


def _db(tmp_path):
    return ws.get_connection(tmp_path / "d.db")


def _row(conn, title="JOLTS Job Openings", when=JOLTS_TIME, forecast="7.20M", previous="7.23M",
         actual=None, country="USD", impact="Medium"):
    conn.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), forecast, previous, actual, None, when.isoformat(), when.isoformat(), "live", impact, country),
    )
    conn.commit()


def _jolts_fake():
    return FakeRequests(
        initial={"JTSJOL": [_init_obs(D(2026, 8, 1), D(2026, 10, 7))]},
        vintages={("JTSJOL", "2026-10-07"): {D(2026, 7, 1): 7230.0, D(2026, 8, 1): 7400.0}},
    )


def _client(fake, monkeypatch):
    monkeypatch.setattr(fh, "requests", fake)
    return fh.FredClient("KEY", pace_seconds=0)


def test_backfill_fills_medium_row_when_previous_matches(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn)
    report = ab.backfill_missing_actuals(conn, _client(_jolts_fake(), monkeypatch), NOW)
    assert report.written == 1
    row = conn.execute("SELECT * FROM event_history").fetchone()
    assert row["actual"] == "7.40M"
    assert row["source"] == "fred"
    assert row["surprise_direction"] is None          # JOLTS has no EVENT_SURPRISE_DIRECTION entry
    assert row["forecast"] == "7.20M" and row["previous"] == "7.23M" and row["impact"] == "Medium"


def test_backfill_sets_surprise_direction_for_tracked_title(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, title="Unemployment Rate", when=dt.datetime(2026, 10, 2, 12, 30, tzinfo=UTC),
         forecast="4.0%", previous="4.2%", impact="High")
    fake = FakeRequests(
        initial={"UNRATE": [_init_obs(D(2026, 9, 1), D(2026, 10, 2))]},
        vintages={("UNRATE", "2026-10-02"): {D(2026, 8, 1): 4.2, D(2026, 9, 1): 4.3}},
    )
    ab.backfill_missing_actuals(conn, _client(fake, monkeypatch), NOW)
    row = conn.execute("SELECT * FROM event_history").fetchone()
    assert row["actual"] == "4.3%" and row["surprise_direction"] == "higher"


def test_backfill_skips_on_previous_mismatch(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, previous="6.10M")
    report = ab.backfill_missing_actuals(conn, _client(_jolts_fake(), monkeypatch), NOW)
    assert report.written == 0 and report.skipped == 1
    assert any("previous" in r for r in report.skip_reasons)
    assert conn.execute("SELECT actual FROM event_history").fetchone()[0] is None


def test_backfill_ignores_non_usd_rows(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, country="CAD")
    _row(conn, country=None, when=JOLTS_TIME + dt.timedelta(minutes=5))
    fake = _jolts_fake()
    report = ab.backfill_missing_actuals(conn, _client(fake, monkeypatch), NOW)
    assert report.written == 0
    assert fake.calls == []                                   # no FRED request for them
    assert conn.execute("SELECT COUNT(*) FROM event_history WHERE actual IS NOT NULL").fetchone()[0] == 0


def test_backfill_respects_time_window(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, when=NOW - dt.timedelta(minutes=30))                   # too fresh (< 1 h)
    _row(conn, when=NOW - dt.timedelta(days=60))                      # outside the 45 day lookback
    fake = _jolts_fake()
    ab.backfill_missing_actuals(conn, _client(fake, monkeypatch), NOW)
    assert fake.calls == []


def test_backfill_throttled_to_hourly(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, previous="6.10M")          # stays unfilled, so a real run always makes requests
    fake = _jolts_fake()
    monkeypatch.setattr(fh, "requests", fake)
    made = []

    def factory():
        made.append(1)
        return fh.FredClient("KEY", pace_seconds=0)

    assert ab.maybe_backfill(conn, NOW, client_factory=factory) is not None
    n_calls = len(fake.calls)
    assert n_calls > 0
    assert ab.maybe_backfill(conn, NOW + dt.timedelta(minutes=30), client_factory=factory) is None
    assert len(fake.calls) == n_calls and len(made) == 1
    assert ab.maybe_backfill(conn, NOW + dt.timedelta(minutes=61), client_factory=factory) is not None
    assert len(fake.calls) > n_calls


def test_maybe_backfill_without_key_returns_none(tmp_path):
    conn = _db(tmp_path)
    assert ab.maybe_backfill(conn, NOW, client_factory=lambda: None) is None
    # No key must not start the hourly gate: a later keyed call still runs.
    assert ab.maybe_backfill(conn, NOW, client_factory=lambda: fh.FredClient("K")) is not None


def test_default_client_none_without_key(monkeypatch):
    monkeypatch.setattr(ab, "FRED_API_KEY", "")
    assert ab.default_client() is None
    monkeypatch.setattr(ab, "FRED_API_KEY", "abc")
    assert ab.default_client() is not None


def test_backfill_maintenance_logs_and_returns(tmp_path, monkeypatch, capsys):
    class Maint(FakeRequests):
        def get(self, url, params=None, timeout=None):
            return FakeResp(status=200, text="<html><body>FRED is down for maintenance</body></html>")

    conn = _db(tmp_path)
    _row(conn)
    report = ab.backfill_missing_actuals(conn, _client(Maint(), monkeypatch), NOW)
    assert report.written == 0
    assert "FRED under maintenance" in capsys.readouterr().out


def test_backfill_fetch_error_skips_title_not_run(tmp_path, monkeypatch):
    class Err(FakeRequests):
        def get(self, url, params=None, timeout=None):
            return FakeResp(status=500, text="boom")

    conn = _db(tmp_path)
    _row(conn)
    report = ab.backfill_missing_actuals(conn, _client(Err(), monkeypatch), NOW)
    assert report.written == 0
    assert any("FRED" in r for r in report.skip_reasons)


UNRATE_TIME = dt.datetime(2026, 10, 2, 12, 30, tzinfo=UTC)     # sorts before JOLTS_TIME


def _two_title_fake():
    """UNRATE (attempted first: earlier row) and JOLTS, both fillable."""
    return FakeRequests(
        initial={"UNRATE": [_init_obs(D(2026, 9, 1), D(2026, 10, 2))],
                 "JTSJOL": [_init_obs(D(2026, 8, 1), D(2026, 10, 7))]},
        vintages={("UNRATE", "2026-10-02"): {D(2026, 8, 1): 4.2, D(2026, 9, 1): 4.3},
                  ("JTSJOL", "2026-10-07"): {D(2026, 7, 1): 7230.0, D(2026, 8, 1): 7400.0}},
    )


def _two_title_rows(conn):
    _row(conn, title="Unemployment Rate", when=UNRATE_TIME, forecast="4.0%", previous="4.2%", impact="High")
    _row(conn)


def test_backfill_aborts_pass_on_first_transport_error(tmp_path, monkeypatch, capsys):
    # FRED unreachable: one timeout, not one 20 s timeout per title.
    class Down(FakeRequests):
        def get(self, url, params=None, timeout=None):
            self.calls.append(dict(params))
            raise TimeoutError("read timed out")

    conn = _db(tmp_path)
    _two_title_rows(conn)
    fake = Down()
    report = ab.backfill_missing_actuals(conn, _client(fake, monkeypatch), NOW)
    assert len(fake.calls) == 1                       # second title never requested
    assert report.written == 0 and report.skipped == 2
    assert len(report.skip_reasons) == 2 and all("aborted" in r for r in report.skip_reasons)
    assert "FRED unreachable" in capsys.readouterr().out


def test_backfill_http_error_still_only_skips_that_title(tmp_path, monkeypatch):
    # An HTTP error is title-specific (FRED answered), so the pass carries on.
    class FirstFails(FakeRequests):
        def get(self, url, params=None, timeout=None):
            if params["series_id"] == "UNRATE":
                self.calls.append(dict(params))
                return FakeResp(status=500, text="boom")
            return super().get(url, params, timeout)

    conn = _db(tmp_path)
    _two_title_rows(conn)
    base = _two_title_fake()
    fake = FirstFails(initial=base.initial, vintages=base.vintages)
    report = ab.backfill_missing_actuals(conn, _client(fake, monkeypatch), NOW)
    assert report.written == 1 and report.skipped == 1


def test_backfill_stops_at_wall_clock_budget(tmp_path, monkeypatch, capsys):
    conn = _db(tmp_path)
    _two_title_rows(conn)
    fake = _two_title_fake()
    ticks = iter([0.0, 0.0, 301.0])                    # start, before title 1, before title 2
    report = ab.backfill_missing_actuals(conn, _client(fake, monkeypatch), NOW,
                                         budget_seconds=300, clock=lambda: next(ticks))
    assert report.written == 1 and report.skipped == 1
    assert {c["series_id"] for c in fake.calls} == {"UNRATE"}     # JOLTS never requested
    assert any("budget" in r for r in report.skip_reasons)
    assert "budget used" in capsys.readouterr().out
    actuals = dict(conn.execute("SELECT event_title, actual FROM event_history").fetchall())
    assert actuals == {"Unemployment Rate": "4.3%", "JOLTS Job Openings": None}


def test_start_backfill_thread_never_blocks_and_never_overlaps(tmp_path, monkeypatch):
    import threading
    import time

    started, release = threading.Event(), threading.Event()
    passes = []

    def slow_pass(conn, client, now, **kwargs):
        passes.append(now)
        started.set()
        release.wait(30)                                 # a hanging FRED pass
        return ab.FillReport()

    monkeypatch.setattr(ab, "backfill_missing_actuals", slow_pass)
    factory = lambda: fh.FredClient("K", pace_seconds=0)
    db_path = tmp_path / "d.db"
    _db(tmp_path).close()

    t0 = time.monotonic()
    thread = ab.start_backfill_thread(db_path, NOW, client_factory=factory)
    try:
        assert thread is not None
        assert time.monotonic() - t0 < 2.0               # returned while the pass is still running
        assert started.wait(5) and thread.is_alive()
        # Hours later but the first pass is still running: nothing new starts.
        assert ab.start_backfill_thread(db_path, NOW + dt.timedelta(hours=2), client_factory=factory) is None
    finally:
        release.set()                                    # never leave the lock held for later tests
    thread.join(5)
    assert not thread.is_alive() and len(passes) == 1
    # Throttled within the hour; free again (lock released) after it.
    assert ab.start_backfill_thread(db_path, NOW + dt.timedelta(minutes=30), client_factory=factory) is None
    later = ab.start_backfill_thread(db_path, NOW + dt.timedelta(hours=3), client_factory=factory)
    assert later is not None
    later.join(5)
    assert len(passes) == 2


def test_start_backfill_thread_keyless_starts_nothing(tmp_path):
    assert ab.start_backfill_thread(tmp_path / "d.db", NOW, client_factory=lambda: None) is None
    assert ab._last_run_utc is None


def test_start_backfill_thread_fills_via_own_connection(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn)
    fake = _jolts_fake()
    monkeypatch.setattr(fh, "requests", fake)
    thread = ab.start_backfill_thread(tmp_path / "d.db", NOW, client_factory=lambda: fh.FredClient("K", pace_seconds=0))
    thread.join(10)
    assert conn.execute("SELECT actual FROM event_history").fetchone()[0] == "7.40M"


def test_maybe_backfill_never_raises(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    monkeypatch.setattr(ab, "backfill_missing_actuals", lambda *a, **k: (_ for _ in ()).throw(ValueError("boom")))
    assert ab.maybe_backfill(conn, NOW, client_factory=lambda: fh.FredClient("K")) is None
