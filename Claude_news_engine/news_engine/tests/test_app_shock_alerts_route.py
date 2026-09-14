from __future__ import annotations

import datetime as dt

import pytest

from alerting import store as alerting_store
from webapp.app import app

UTC = dt.timezone.utc


@pytest.fixture
def client(monkeypatch):
    conn = alerting_store.get_connection(":memory:")
    monkeypatch.setattr(alerting_store, "get_connection", lambda *a, **kw: conn)
    alerting_store.record_alert(
        conn, headline="Strait of Hormuz closed", source="reuters_business", url="https://x",
        published_utc=dt.datetime.now(UTC), detected_at_utc=dt.datetime.now(UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None,
        affected_symbols=[{"symbol": "XAUUSD", "channel": "safe_haven"}],
    )
    with app.test_client() as c:
        yield c


def test_shock_alerts_route_returns_recent_rows(client):
    resp = client.get("/api/shock-alerts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["rows"]) == 1
    assert data["rows"][0]["headline"] == "Strait of Hormuz closed"
    assert data["rows"][0]["severity"] == "High"
    assert data["rows"][0]["affected_symbols"] == [{"symbol": "XAUUSD", "channel": "safe_haven"}]
