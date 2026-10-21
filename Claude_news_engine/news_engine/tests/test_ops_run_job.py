# tests/test_ops_run_job.py
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pytest

from ops import run_job, state

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 21, 9, 45, 21, tzinfo=UTC)
APP_DIR = Path(__file__).resolve().parent.parent


def _run(tmp_path, snippet: str, job: str = "outcome_confirm", **kw):
    log = tmp_path / "job.log"
    db = tmp_path / "ops.db"
    code = run_job.run_logged(job, log, ["-c", snippet], clock=lambda: NOW, ops_db=db, **kw)
    return code, log, db


def test_every_child_line_gets_a_sast_timestamp(tmp_path):
    code, log, _ = _run(tmp_path, "print('alpha'); print('beta')")
    assert code == 0
    lines = log.read_text(encoding="utf-8").splitlines()
    assert "2026-10-21 11:45:21 SAST alpha" in lines
    assert "2026-10-21 11:45:21 SAST beta" in lines
    assert all(re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} SAST ", ln) for ln in lines)
    assert "[run_job] outcome_confirm starting" in lines[0]
    assert "finished (exit 0)" in lines[-1]


def test_child_exit_code_is_returned_logged_and_recorded(tmp_path):
    code, log, db = _run(tmp_path, "import sys; sys.exit(2)")
    assert code == 2
    assert "finished (exit 2)" in log.read_text(encoding="utf-8")
    run = state.get_job_runs(state.get_connection(db))["outcome_confirm"]
    assert run.last_exit_code == 2
    assert run.last_success_utc is None


def test_stderr_and_tracebacks_reach_the_log(tmp_path):
    code, log, _ = _run(tmp_path, "raise RuntimeError('boom')")
    assert code == 1
    assert "RuntimeError: boom" in log.read_text(encoding="utf-8")


def test_log_over_limit_rotates_to_one_backup(tmp_path):
    log = tmp_path / "job.log"
    log.write_bytes(b"x" * 1_000_000)
    (tmp_path / "job.log.1").write_text("old")
    _run(tmp_path, "print('hi')")
    assert (tmp_path / "job.log.1").stat().st_size == 1_000_000
    assert "x" * 50 not in log.read_text(encoding="utf-8")
    assert not (tmp_path / "job.log.2").exists()


def test_log_under_limit_is_appended_not_rotated(tmp_path):
    log = tmp_path / "job.log"
    log.write_bytes(b"0123456789")
    _run(tmp_path, "print('hi')")
    assert log.read_bytes().startswith(b"0123456789")
    assert not (tmp_path / "job.log.1").exists()


def test_locked_log_never_breaks_the_job(tmp_path, monkeypatch):
    def locked(*a, **k):
        raise PermissionError("locked")
    monkeypatch.setattr(run_job.os, "replace", locked)
    monkeypatch.setattr(run_job, "_open_log", lambda p: None)
    log = tmp_path / "job.log"
    log.write_bytes(b"x" * 1_000_000)  # forces the rotate attempt too
    db = tmp_path / "ops.db"
    code = run_job.run_logged("shock_poll", log, ["-c", "print('hi')"], clock=lambda: NOW, ops_db=db)
    assert code == 0
    run = state.get_job_runs(state.get_connection(db))["shock_poll"]
    assert run.last_exit_code == 0 and run.last_success_utc is not None


def test_large_child_output_does_not_deadlock(tmp_path):
    code, log, _ = _run(tmp_path, "for i in range(20000): print('x' * 100)")
    assert code == 0
    assert len(log.read_text(encoding="utf-8").splitlines()) == 20_002


def test_child_that_cannot_start_returns_1_and_is_recorded(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise OSError("no exe")
    monkeypatch.setattr(run_job.subprocess, "Popen", boom)
    code, log, db = _run(tmp_path, "pass")
    assert code == 1
    assert state.get_job_runs(state.get_connection(db))["outcome_confirm"].last_exit_code == 1


def test_main_rejects_unknown_job_and_missing_separator(tmp_path):
    x = str(tmp_path / "x.log")
    with pytest.raises(SystemExit) as e1:
        run_job.main(["--job", "nope", "--log", x, "--", "-c", "pass"])
    assert e1.value.code == 2
    with pytest.raises(SystemExit) as e2:
        run_job.main(["--job", "shock_poll", "--log", x])
    assert e2.value.code == 2


def _raw(rel: str) -> bytes:
    return (APP_DIR / rel).read_bytes()


def test_wrappers_route_every_scheduled_job_through_run_job():
    expected = {
        "scripts/confirm_outcomes_scheduled.bat": [
            b"python -m ops.run_job --job outcome_confirm --log scripts\\confirm_outcomes_scheduled.log -- scripts\\confirm_backtest_outcomes.py --auto --list"],
        "scripts/reaction_compute_scheduled.bat": [
            b"set JOB=reaction_incremental", b"set JOB=reaction_baselines",
            b"python -m ops.run_job --job %JOB% --log scripts\\reaction_compute_scheduled.log -- scripts\\compute_release_reactions.py %MODE% --bt-db scoring\\backtest_log.db --dash-db webapp\\dashboard.db"],
        "scripts/tier1_capture_scheduled.bat": [
            b"set JOB=tier1_capture_daily", b"set JOB=tier1_capture_weekly",
            b"python -m ops.run_job --job %JOB% --log scripts\\tier1_capture_scheduled.log -- scripts\\capture_nowcast_from_cleveland.py --window-hours %WINDOW% --bt-db scoring\\backtest_log.db --dash-db webapp\\dashboard.db"],
        "alerting/scripts/poll_once_hidden.vbs": [
            b'-m ops.run_job --job shock_poll --log alerting\\poll_once.log -- -m alerting.poll_once"'],
        "alerting/scripts/reality_check_hidden.vbs": [
            b'-m ops.run_job --job shock_reality_check --log alerting\\reality_check.log -- -m alerting.reality_check"'],
    }
    for rel, needles in expected.items():
        data = _raw(rel)
        for needle in needles:
            assert needle in data, f"{rel} missing {needle!r}"
        assert b">>" not in data, f"{rel} still redirects with >>"
        assert data.count(b"\n") == data.count(b"\r\n"), f"{rel} has bare LF"
