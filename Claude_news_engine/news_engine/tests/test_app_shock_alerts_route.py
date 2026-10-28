from __future__ import annotations

import datetime as dt

import pytest

from alerting import lean_grading
from alerting import store as alerting_store
from config import settings as config_settings
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
    "incident_id", "incident_role", "incident_rule", "grades",
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


# ---------------------------------------------------------------------------
# B10 (2026-10-28) K13: SAST date range, grades and hit-rate summary
# ---------------------------------------------------------------------------
GRADE_KEYS = {"symbol", "anchor", "window_minutes", "lean", "anchor_utc", "move", "baseline", "verdict"}
SUMMARY_KEYS = {"window_minutes", "symbols", "overall", "by_symbol", "incidents", "ungraded_alerts"}


def _grade(alert_id, symbol="XAUUSD", anchor="detected", verdict="right", move=1.5, baseline=1.0):
    return lean_grading.Grade(
        alert_id=alert_id, symbol=symbol, anchor=anchor, window_minutes=5, lean="buy",
        anchor_utc=dt.datetime(2026, 10, 20, 8, 0, tzinfo=UTC), p0=2000.0, p_end=2000.0 + move,
        move=move, baseline=baseline, baseline_multiple=1.0, moved=verdict in ("right", "wrong"),
        verdict=verdict,
    )


def _at(conn, detected, **extra):
    return _record(conn, detected_at_utc=detected, published_utc=detected - dt.timedelta(minutes=2), **extra)


def test_response_top_level_keys_exact(monkeypatch):
    conn = _conn(monkeypatch)
    _record(conn)
    with app.test_client() as c:
        data = c.get("/api/shock-alerts").get_json()
    assert set(data) == {"rows", "range", "summary"}
    assert set(data["range"]) == {"from", "to"}


def test_grade_and_summary_key_sets_are_exact(monkeypatch):
    conn = _conn(monkeypatch)
    alert_id = _record(conn)
    now = dt.datetime.now(UTC)
    alerting_store.record_grade(conn, _grade(alert_id, anchor="published"), now)
    alerting_store.record_grade(conn, _grade(alert_id, anchor="detected", symbol="US30"), now)
    with app.test_client() as c:
        data = c.get("/api/shock-alerts").get_json()
    row = data["rows"][0]
    assert set(row) == EXPECTED_ROW_KEYS | {"grades"}
    assert len(row["grades"]) == 2
    for g in row["grades"]:
        assert set(g) == GRADE_KEYS
    assert set(data["summary"]) == SUMMARY_KEYS
    assert data["summary"]["symbols"] == ["US30", "XAUUSD"]
    assert data["summary"]["window_minutes"] == 5
    assert data["summary"]["ungraded_alerts"] == 0
    assert set(data["summary"]["overall"]) == {"published", "detected"}
    assert set(data["summary"]["incidents"][0]) == {
        "incident_id", "headline", "first_detected_utc", "alerts", "published", "detected"}


def test_ungraded_rows_have_empty_grades_and_fallback_symbols(monkeypatch):
    conn = _conn(monkeypatch)
    _record(conn)
    with app.test_client() as c:
        data = c.get("/api/shock-alerts").get_json()
    assert data["rows"][0]["grades"] == []
    assert data["summary"]["symbols"] == ["US30", "XAUUSD"]
    assert data["summary"]["ungraded_alerts"] == 1


def test_range_is_sast_days_inclusive(monkeypatch):
    conn = _conn(monkeypatch)
    before = _at(conn, dt.datetime(2026, 10, 19, 21, 59, tzinfo=UTC), headline="before")   # 10-19 23:59 SAST
    first = _at(conn, dt.datetime(2026, 10, 19, 22, 0, tzinfo=UTC), headline="first")      # 10-20 00:00 SAST
    last = _at(conn, dt.datetime(2026, 10, 20, 21, 59, tzinfo=UTC), headline="last")       # 10-20 23:59 SAST
    after = _at(conn, dt.datetime(2026, 10, 20, 22, 0, tzinfo=UTC), headline="after")      # 10-21 00:00 SAST
    with app.test_client() as c:
        data = c.get("/api/shock-alerts?from=2026-10-20&to=2026-10-20").get_json()
    ids = {r["id"] for r in data["rows"]}
    assert ids == {first, last}
    assert before not in ids and after not in ids
    assert data["range"] == {"from": "2026-10-20", "to": "2026-10-20"}


def test_default_range_is_today_and_six_days_before_sast(monkeypatch):
    conn = _conn(monkeypatch)
    today = dt.datetime.now(config_settings.LOCAL_TZ).date()
    start = dt.datetime.combine(today - dt.timedelta(days=6), dt.time(0, 0), tzinfo=config_settings.LOCAL_TZ)
    inside = _at(conn, (start + dt.timedelta(minutes=1)).astimezone(UTC))
    outside = _at(conn, (start - dt.timedelta(minutes=1)).astimezone(UTC), headline="too old")
    with app.test_client() as c:
        data = c.get("/api/shock-alerts").get_json()
    assert {r["id"] for r in data["rows"]} == {inside}
    assert outside not in {r["id"] for r in data["rows"]}
    assert data["range"] == {"from": (today - dt.timedelta(days=6)).isoformat(), "to": today.isoformat()}


@pytest.mark.parametrize("query", [
    "from=2026-13-01&to=2026-13-02",
    "from=2026-10-20&to=2026-10-19",
    "from=2025-10-01&to=2026-10-02",          # 367 days inclusive
    "from=not-a-date",
])
def test_bad_range_is_400(monkeypatch, query):
    _conn(monkeypatch)
    with app.test_client() as c:
        resp = c.get("/api/shock-alerts?" + query)
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_max_span_366_days_is_accepted(monkeypatch):
    _conn(monkeypatch)
    with app.test_client() as c:
        resp = c.get("/api/shock-alerts?from=2025-10-02&to=2026-10-02")
    assert resp.status_code == 200


def test_summary_hit_rate_per_incident_and_overall(monkeypatch):
    conn = _conn(monkeypatch)
    now = dt.datetime.now(UTC)
    root = _record(conn)
    follow = _record(conn, headline="widens", url="https://y", incident_id=root, incident_role="follow_up",
                     incident_rule="url")
    other = _record(conn, headline="other", url="https://z")
    for alert_id, verdict in ((root, "right"), (follow, "right"), (other, "wrong")):
        alerting_store.record_grade(conn, _grade(alert_id, verdict=verdict), now)
    alerting_store.record_grade(conn, _grade(root, symbol="US30", verdict="right"), now)
    alerting_store.record_grade(conn, _grade(other, symbol="US30", verdict="no_move"), now)
    with app.test_client() as c:
        summary = c.get("/api/shock-alerts").get_json()["summary"]
    incident = next(i for i in summary["incidents"] if i["incident_id"] == root)
    assert incident["alerts"] == 2
    assert incident["detected"]["n"] == 3 and incident["detected"]["right"] == 3
    overall = summary["overall"]["detected"]
    assert (overall["right"], overall["wrong"], overall["n"]) == (3, 1, 4)
    assert overall["hit_rate"] == 0.75
    assert overall["no_move"] == 1                      # counted, but not in n
    assert summary["by_symbol"]["US30"]["detected"]["n"] == 1
