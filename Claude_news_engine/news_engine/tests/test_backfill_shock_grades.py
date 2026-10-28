# tests/test_backfill_shock_grades.py
"""B10 K14: scripts/backfill_shock_grades.py -- dry run by default, read-only DBs, idempotent --apply."""
from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

import pytest

from alerting import store
from scoring import backtest_store
from scripts import backfill_shock_grades as backfill
from webapp import store as web_store

UTC = dt.timezone.utc
DETECTED = dt.datetime(2026, 10, 20, 12, 30, 40, tzinfo=UTC)


def _fake_fetch(symbol, start, end):
    # m = 12:31; bars 12:31 (100.0) and 12:36 (101.5), then a later bar so nothing is pending.
    base = dt.datetime(2026, 10, 20, 12, 31, tzinfo=UTC)
    return {base: 100.0, base + dt.timedelta(minutes=5): 101.5, base + dt.timedelta(hours=4): 102.0}


@pytest.fixture
def dbs(tmp_path: Path):
    alerts, bt, dash = tmp_path / "alerts.db", tmp_path / "bt.db", tmp_path / "dash.db"
    conn = store.get_connection(alerts)
    store.record_alert(
        conn, headline="H", source="s", url="u", published_utc=DETECTED, detected_at_utc=DETECTED,
        category="energy", severity="High", classification_method="rule_tier", rationale=None,
        affected_symbols=[{"symbol": "XAUUSD", "channel": "safe_haven", "lean": "buy"}])
    conn.close()
    bt_conn = backtest_store.get_connection(bt)
    bt_conn.execute("INSERT INTO reaction_baselines (symbol, utc_hour, quantile, baseline, period_end_utc, "
                    "computed_at_utc) VALUES ('XAUUSD', 12, 0.75, 1.0, '2026-10-16T18:00:00+00:00', "
                    "'2026-10-16T18:00:00+00:00')") if _baseline_cols(bt_conn) else None
    bt_conn.commit()
    bt_conn.close()
    dash_conn = web_store.get_connection(dash)
    web_store.add_tracked_symbol(dash_conn, "XAUUSD")
    dash_conn.close()
    return alerts, bt, dash


def _baseline_cols(conn) -> bool:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(reaction_baselines)")}
    return {"symbol", "utc_hour", "quantile", "baseline", "period_end_utc", "computed_at_utc"} <= cols


def _args(dbs, *extra):
    alerts, bt, dash = dbs
    return ["--alerts-db", str(alerts), "--bt-db", str(bt), "--dash-db", str(dash), *extra]


def test_refuses_live_default_without_flag(monkeypatch, capsys):
    monkeypatch.delenv(backfill.LIVE_ENV_VAR, raising=False)

    def boom(*args, **kwargs):
        pytest.fail("sqlite3.connect reached before refusing")
    monkeypatch.setattr(sqlite3, "connect", boom)
    assert backfill.main([]) == 2
    assert "REFUSING" in capsys.readouterr().out


def test_backfill_dry_run_opens_every_db_read_only(dbs, monkeypatch, capsys):
    # Pre-B10 alerts DB: drop the grade tables a fresh get_connection created.
    conn = sqlite3.connect(dbs[0])
    conn.execute("DROP TABLE shock_alert_grades")
    conn.execute("DROP TABLE shock_grading_runs")
    conn.commit()
    conn.close()
    calls: list[str] = []
    real = sqlite3.connect

    def spy(target, *args, **kwargs):
        calls.append(str(target))
        return real(target, *args, **kwargs)
    monkeypatch.setattr(sqlite3, "connect", spy)
    monkeypatch.setattr(backfill, "FETCH_BARS", _fake_fetch)
    assert backfill.main(_args(dbs)) == 0
    assert calls and all("mode=ro" in c for c in calls), calls
    assert "dry run" in capsys.readouterr().out.lower()
    monkeypatch.undo()
    check = sqlite3.connect(dbs[0])
    tables = {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check.close()
    assert "shock_alert_grades" not in tables       # nothing created or written


def test_apply_writes_then_rerun_writes_zero(dbs, monkeypatch, capsys):
    monkeypatch.setattr(backfill, "FETCH_BARS", _fake_fetch)
    assert backfill.main(_args(dbs, "--apply")) == 0
    first = capsys.readouterr().out
    assert "graded 2:" in first                      # published + detected for XAUUSD
    conn = sqlite3.connect(dbs[0])
    assert conn.execute("SELECT COUNT(*) FROM shock_alert_grades").fetchone()[0] == 2
    assert conn.execute("SELECT source FROM shock_grading_runs").fetchone()[0] == "backfill"
    conn.close()
    assert backfill.main(_args(dbs, "--apply")) == 0
    assert "graded 0" in capsys.readouterr().out


def test_output_reports_starting_point(dbs, monkeypatch, capsys):
    monkeypatch.setattr(backfill, "FETCH_BARS", _fake_fetch)
    backfill.main(_args(dbs))
    out = capsys.readouterr().out
    assert "starting point before B10: 14 of 26" in out
    assert "overall 5-minute detection-anchored hit rate:" in out


def test_fetch_failure_exits_1(dbs, monkeypatch, capsys):
    def failing(symbol, start, end):
        raise RuntimeError("feed down")
    monkeypatch.setattr(backfill, "FETCH_BARS", failing)
    assert backfill.main(_args(dbs)) == 1
    assert "XAUUSD" in capsys.readouterr().out
