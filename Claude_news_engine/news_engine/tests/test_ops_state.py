# tests/test_ops_state.py
from __future__ import annotations

import datetime as dt

import pytest

from ops import state

UTC = dt.timezone.utc


def _conn(tmp_path, now=None):
    return state.get_connection(tmp_path / "s.db", now=now)


def test_record_job_run_keeps_last_success_across_a_failure(tmp_path):
    conn = _conn(tmp_path)
    ok = dt.datetime(2026, 10, 21, 9, 0, tzinfo=UTC)
    bad = dt.datetime(2026, 10, 21, 9, 15, tzinfo=UTC)
    state.record_job_run(conn, "shock_poll", ok, 0)
    state.record_job_run(conn, "shock_poll", bad, 2)
    run = state.get_job_runs(conn)["shock_poll"]
    assert run.last_exit_code == 2
    assert run.last_run_utc == bad
    assert run.last_success_utc == ok


def test_record_job_run_rejects_an_unknown_job(tmp_path):
    conn = _conn(tmp_path)
    with pytest.raises(ValueError):
        state.record_job_run(conn, "nope", dt.datetime(2026, 10, 21, tzinfo=UTC), 0)


def test_failure_with_no_prior_success_leaves_success_empty(tmp_path):
    conn = _conn(tmp_path)
    state.record_job_run(conn, "shock_poll", dt.datetime(2026, 10, 21, tzinfo=UTC), 2)
    assert state.get_job_runs(conn)["shock_poll"].last_success_utc is None


def test_tracking_since_is_set_once(tmp_path):
    first = dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC)
    _conn(tmp_path, now=first)
    conn = _conn(tmp_path, now=dt.datetime(2026, 10, 22, 8, 0, tzinfo=UTC))
    assert state.get_tracking_since(conn) == first


def test_health_notice_ledger_is_one_row_per_utc_day(tmp_path):
    conn = _conn(tmp_path)
    day = dt.date(2026, 10, 21)
    sent = dt.datetime(2026, 10, 21, 7, 0, tzinfo=UTC)
    state.record_health_notice(conn, day, sent, "first")
    state.record_health_notice(conn, day, sent, "second")
    assert conn.execute("SELECT COUNT(*) FROM health_notices").fetchone()[0] == 1
    assert state.health_notice_sent(conn, day) is True
    assert state.health_notice_sent(conn, dt.date(2026, 10, 22)) is False


def test_touch_heartbeat_records_a_success(tmp_path):
    db = tmp_path / "s.db"
    state.touch_heartbeat("article_accumulator", now=dt.datetime(2026, 10, 21, 9, 0, tzinfo=UTC), db_path=db)
    run = state.get_job_runs(state.get_connection(db))["article_accumulator"]
    assert run.last_exit_code == 0 and run.last_success_utc is not None


def test_touch_heartbeat_never_raises(tmp_path):
    # A directory is not an openable database: must be swallowed.
    assert state.touch_heartbeat("shock_poll", db_path=tmp_path) is None
