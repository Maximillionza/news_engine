# Stats tab API routes: explicit serializers over webapp.stats_service.
import datetime as dt

import pytest

import webapp.app as app_module
from scoring import backtest_store as bs
from webapp import store as ws

UTC = dt.timezone.utc
WHEN = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)


@pytest.fixture
def client(monkeypatch):
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("CPI m/m", WHEN.isoformat(), "0.3%", "0.1%", "0.4%", None, WHEN.isoformat(), WHEN.isoformat(), "t", "High", "USD"))
    dash.commit()
    bs.record_nowcast_snapshot(bt, "CPI m/m", WHEN, 0.4, WHEN - dt.timedelta(hours=40), "cleveland", "live")
    monkeypatch.setattr(app_module, "_stats_connections", lambda: (dash, bt))
    return app_module.app.test_client()


def test_events_route_serves_every_field_the_tab_renders(client):
    row = client.get("/api/stats/events?event=CPI%20m/m").get_json()["rows"][0]
    for key in ("event_title", "event_time_utc", "forecast", "actual", "forecast_text", "actual_text", "status",
                "tier1_tracked", "nowcast_as_of_utc", "pre_news_period", "tier1", "news", "combined"):
        assert key in row, key
    assert set(row["tier1"]) >= {"predicted", "surprise", "verdict", "miss", "leans", "note", "kind"}
    assert row["tier1"]["verdict"] == "right" and row["tier1"]["leans"]["XAUUSD"] == "sell"


def test_filters_and_empty_result(client):
    assert client.get("/api/stats/events?year=2025").get_json()["rows"] == []
    assert len(client.get("/api/stats/events?year=2026&month=10").get_json()["rows"]) == 1


def test_chart_route(client):
    data = client.get("/api/stats/chart?event=CPI%20m/m&method=combined").get_json()
    assert data["method"] == "combined" and data["points"][0]["month"] == "2026-10"
    assert client.get("/api/stats/chart?event=CPI%20m/m&method=nope").status_code == 400
    assert client.get("/api/stats/chart?method=tier1").status_code == 400


def test_scoreboard_route_has_the_fixed_weight_footnote(client):
    data = client.get("/api/stats/scoreboard?event=CPI%20m/m").get_json()
    assert set(data["methods"]) == {"tier1", "news", "combined"}
    assert "70/30" in data["footnote"] and "2027-01-15" in data["footnote"]


def test_components_route(client):
    assert client.get("/api/stats/components/cleveland_nowcast").get_json()["components"]
    assert client.get("/api/stats/components/nope").status_code == 404
