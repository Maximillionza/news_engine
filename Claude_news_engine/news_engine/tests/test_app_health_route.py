# tests/test_app_health_route.py
# GET /api/health (B4 O6): explicit serializer with exact key sets. The
# connections, clock and macro marker are all patched, so the worktree's own
# DBs and marker file are never read.
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

import webapp.app as app_module
from alerting import store as alerting_store
from ops import health
from ops import state as ops_state
from scoring import backtest_store as bs
from webapp import store as ws

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
TOP_KEYS = {"generated_at_utc", "overall", "items"}
ITEM_KEYS = {"key", "label", "status", "last_success_utc", "age_seconds", "expected_every_seconds", "detail"}


def _client(monkeypatch, tmp_path: Path, populate):
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    alerts = alerting_store.get_connection(":memory:")
    ops = ops_state.get_connection(tmp_path / "ops.db", now=NOW - dt.timedelta(days=30))
    populate(dash, bt, alerts, ops)
    monkeypatch.setattr(app_module, "_health_connections", lambda: (dash, bt, alerts, ops))
    monkeypatch.setattr(app_module, "_health_clock", lambda: NOW)
    monkeypatch.setattr(health, "MACRO_MARKER_PATH", tmp_path / "no_marker")
    return app_module.app.test_client()


def _silent_failures(dash, bt, alerts, ops) -> None:
    for job in ops_state.JOB_NAMES:
        ops_state.record_job_run(ops, job, NOW - dt.timedelta(minutes=1), 0)
    dash.execute(
        "INSERT INTO macro_calendar (event_title, event_date, time_source, source, recorded_at_utc, updated_at_utc) "
        "VALUES ('CPI m/m', '2026-09-17', 'unconfirmed', 'fred', '2026-08-16T10:48:00+00:00', "
        "'2026-08-16T10:48:00+00:00')")
    dash.commit()
    alerting_store.set_provider_cooldown(alerts, "claude", dt.datetime(2026, 10, 20, 9, 55, tzinfo=UTC))


def test_health_route_exact_keys(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path, _silent_failures)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data) == TOP_KEYS
    assert data["generated_at_utc"] == NOW.isoformat()
    assert data["overall"] == "red"
    assert [item["key"] for item in data["items"]][:2] == ["shock_poll", "outcome_confirm"]
    for item in data["items"]:
        assert set(item) == ITEM_KEYS
    by_key = {item["key"]: item for item in data["items"]}
    assert by_key["macro_calendar"]["status"] == "red"
    assert by_key["shock_poll"]["status"] == "ok"
    assert by_key["shock_poll"]["age_seconds"] == 60
    assert by_key["shock_poll"]["last_success_utc"] == (NOW - dt.timedelta(minutes=1)).isoformat()


def test_health_route_on_empty_dbs_returns_200(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path, lambda *conns: None)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["overall"] in {"ok", "amber", "red"}
    assert {item["status"] for item in data["items"]} <= {"ok", "amber", "red"}
    assert not any(item["detail"].startswith("check failed") for item in data["items"])
