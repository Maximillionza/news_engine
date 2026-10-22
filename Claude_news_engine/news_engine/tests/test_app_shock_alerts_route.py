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


def test_shock_alerts_route_serves_the_lean_fields_the_tab_renders(monkeypatch):
    # The route returns affected_symbols whole; this pins that it keeps doing so, because the
    # last time a new field was added a hand-listed serializer silently dropped it.
    conn = alerting_store.get_connection(":memory:")
    monkeypatch.setattr(alerting_store, "get_connection", lambda *a, **kw: conn)
    affected = [
        {"symbol": "XAUUSD", "channel": "safe_haven", "lean": "buy", "lean_why": "safe-haven demand [convention]"},
        {"symbol": "US30", "channel": "risk_sentiment", "lean": "sell", "lean_why": "risk-off [convention]"},
    ]
    alerting_store.record_alert(
        conn, headline="Strait of Hormuz closed", source="reuters_business", url="https://x",
        published_utc=dt.datetime.now(UTC), detected_at_utc=dt.datetime.now(UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None,
        affected_symbols=affected,
    )
    with app.test_client() as c:
        data = c.get("/api/shock-alerts").get_json()
    assert data["rows"][0]["affected_symbols"] == affected


EXPECTED_ROW_KEYS = {
    "id", "headline", "sources", "detected_at_utc", "category", "severity",
    "classification_method", "rationale", "affected_symbols", "delivery_status",
    "reality_mismatch", "polarity", "country", "us_link", "capped_no_us_link",
    "original_severity", "first_published_utc", "age_minutes", "freshness_band",
    "incident_id", "incident_role", "incident_rule",
}


def _conn(monkeypatch):
    conn = alerting_store.get_connection(":memory:")
    monkeypatch.setattr(alerting_store, "get_connection", lambda *a, **kw: conn)
    return conn


def _record(conn, **extra):
    detected = dt.datetime.now(UTC).replace(microsecond=0)
    kwargs = dict(
        headline="Russia strikes pipeline", source="reuters_business", url="https://x",
        published_utc=detected - dt.timedelta(minutes=2), detected_at_utc=detected,
        category="energy", severity="Medium", classification_method="llm", rationale=None,
        affected_symbols=[],
    )
    kwargs.update(extra)
    return alerting_store.record_alert(conn, **kwargs)


def test_shock_alert_route_row_key_set_is_exact(monkeypatch):
    conn = _conn(monkeypatch)
    _record(conn)
    with app.test_client() as c:
        row = c.get("/api/shock-alerts").get_json()["rows"][0]
    assert set(row) == EXPECTED_ROW_KEYS


def test_shock_alert_route_serves_new_fields(monkeypatch):
    conn = _conn(monkeypatch)
    _record(conn, polarity="escalation", country="RU", us_link="none",
            capped_no_us_link=True, original_severity="High")
    with app.test_client() as c:
        row = c.get("/api/shock-alerts").get_json()["rows"][0]
    assert (row["polarity"], row["country"], row["us_link"]) == ("escalation", "RU", "none")
    assert row["capped_no_us_link"] is True
    assert row["original_severity"] == "High"
    assert row["age_minutes"] == 2
    assert row["freshness_band"] == "Fresh"
    assert dt.datetime.fromisoformat(row["first_published_utc"]) == (
        dt.datetime.fromisoformat(row["detected_at_utc"]) - dt.timedelta(minutes=2)
    )


def test_shock_alert_route_serves_freshness_for_old_rows(monkeypatch):
    conn = _conn(monkeypatch)
    alert_id = _record(conn)
    # Simulate a pre-B2 row: every new column NULL, so the time must come from sources[0].
    conn.execute(
        "UPDATE shock_alerts SET polarity=NULL, country=NULL, us_link=NULL, "
        "capped_no_us_link=NULL, original_severity=NULL, first_published_utc=NULL WHERE id=?",
        (alert_id,),
    )
    conn.commit()
    with app.test_client() as c:
        row = c.get("/api/shock-alerts").get_json()["rows"][0]
    assert row["first_published_utc"] is not None
    assert row["age_minutes"] == 2
    assert row["freshness_band"] == "Fresh"
    assert row["country"] is None and row["us_link"] is None and row["polarity"] is None
    assert row["capped_no_us_link"] is None and row["original_severity"] is None

    conn.execute("UPDATE shock_alerts SET sources_json='[]' WHERE id=?", (alert_id,))
    conn.commit()
    with app.test_client() as c:
        resp = c.get("/api/shock-alerts")
    assert resp.status_code == 200
    row = resp.get_json()["rows"][0]
    assert row["first_published_utc"] is None
    assert row["age_minutes"] is None
    assert row["freshness_band"] is None


def test_shock_alert_route_serves_incident_fields(monkeypatch):
    conn = _conn(monkeypatch)
    root = _record(conn)
    follow = _record(conn, headline="Russia pipeline strike widens", url="https://y",
                     incident_id=root, incident_role="follow_up", incident_rule="url")
    with app.test_client() as c:
        rows = {r["id"]: r for r in c.get("/api/shock-alerts").get_json()["rows"]}
    assert (rows[root]["incident_id"], rows[root]["incident_role"], rows[root]["incident_rule"]) == (root, None, None)
    assert (rows[follow]["incident_id"], rows[follow]["incident_role"], rows[follow]["incident_rule"]) == (
        root, "follow_up", "url")

    # A raw pre-B7 row (NULL incident columns) is served as its own incident.
    conn.execute("UPDATE shock_alerts SET incident_id=NULL, incident_role=NULL, incident_rule=NULL WHERE id=?", (root,))
    conn.commit()
    with app.test_client() as c:
        rows = {r["id"]: r for r in c.get("/api/shock-alerts").get_json()["rows"]}
    assert rows[root]["incident_id"] == root
    assert rows[root]["incident_role"] is None and rows[root]["incident_rule"] is None
