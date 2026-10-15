# Stats tab API routes: explicit serializers over webapp.stats_service.
import datetime as dt
import sqlite3
from types import SimpleNamespace

import pytest

import webapp.app as app_module
from scoring import backtest_store as bs
from webapp import store as ws

UTC = dt.timezone.utc
WHEN = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
AS_OF = WHEN - dt.timedelta(hours=40)

ROW_KEYS = {"event_title", "event_time_utc", "forecast", "actual", "forecast_text", "actual_text", "status",
            "tier1_tracked", "nowcast_as_of_utc", "pre_news_period", "tier1", "news", "combined"}
CALL_KEYS = {"predicted", "surprise", "verdict", "miss", "leans", "note", "kind"}


def _insert_event(dash, when, forecast, actual):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("CPI m/m", when.isoformat(), forecast, "0.1%", actual, None, when.isoformat(), when.isoformat(),
         "t", "High", "USD"))
    dash.commit()


@pytest.fixture
def client(monkeypatch):
    """One scored CPI print with a Tier 1 snapshot only: no news, no prior history."""
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    _insert_event(dash, WHEN, "0.3%", "0.4%")
    bs.record_nowcast_snapshot(bt, "CPI m/m", WHEN, 0.4, AS_OF, "cleveland", "live")
    monkeypatch.setattr(app_module, "_stats_connections", lambda: (dash, bt))
    return app_module.app.test_client()


@pytest.fixture
def full_client(monkeypatch):
    """Tier 1 snapshot + a print call stamped before the release + 3 prior USD prints (scale = median 0.2)."""
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    for when, actual in ((dt.datetime(2026, 7, 14, 12, 30, tzinfo=UTC), "0.3%"),    # |a-f| 0.1
                         (dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC), "0.4%"),    # 0.2
                         (dt.datetime(2026, 9, 11, 12, 30, tzinfo=UTC), "0.5%")):   # 0.3
        _insert_event(dash, when, "0.2%", actual)
    _insert_event(dash, WHEN, "0.3%", "0.4%")
    bs.record_nowcast_snapshot(bt, "CPI m/m", WHEN, 0.4, AS_OF, "cleveland", "live")
    call = SimpleNamespace(direction="higher", confidence=0.5, article_count=7)
    assert bs.record_print_prediction_if_changed(bt, "CPI m/m", WHEN, call, now=WHEN - dt.timedelta(hours=2))
    monkeypatch.setattr(app_module, "_stats_connections", lambda: (dash, bt))
    return app_module.app.test_client()


def test_events_route_serves_every_field_the_tab_renders(client):
    data = client.get("/api/stats/events?event=CPI%20m/m").get_json()
    row = data["rows"][0]
    assert set(row) == ROW_KEYS
    assert row["event_title"] == "CPI m/m" and row["event_time_utc"] == WHEN.isoformat()
    assert row["forecast"] == 0.3 and row["actual"] == 0.4
    assert row["forecast_text"] == "0.3%" and row["actual_text"] == "0.4%"
    assert row["status"] == "scored" and row["tier1_tracked"] is True
    assert row["pre_news_period"] is False
    assert row["nowcast_as_of_utc"] == AS_OF.isoformat()
    assert set(row["tier1"]) == CALL_KEYS
    assert row["tier1"]["verdict"] == "right" and row["tier1"]["leans"]["XAUUSD"] == "sell"
    assert row["tier1"]["predicted"] == 0.4 and row["tier1"]["kind"] == "live"
    assert row["news"] is None                                  # no articles and no scale history
    assert row["combined"]["note"] == "news_missing"            # Tier 1 only, flagged
    assert data["news_start_utc"] == "2026-08-12T00:00:00+00:00"
    assert data["disclaimers"] == {
        "pre_news": "No news articles exist before 12 Aug 2026. Combined for these months is Tier 1 only.",
        "reconstructed": "Reconstructed after the fact from the stated rule; not a live call.",
        "typical_reaction": "Typical reaction, not a trade signal.",
    }


def test_events_route_serves_real_news_and_combined_calls(full_client):
    rows = full_client.get("/api/stats/events?event=CPI%20m/m&month=10").get_json()["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == ROW_KEYS
    tier1, news, combined = row["tier1"], row["news"], row["combined"]
    for call in (tier1, news, combined):
        assert set(call) == CALL_KEYS
        assert call["verdict"] == "right"
        assert call["leans"]["XAUUSD"] == "sell"
        assert call["predicted"] == pytest.approx(0.4)
        assert call["surprise"] == pytest.approx(0.1)           # tier1 0.1; news 0.5 x 0.2; blend 0.7x0.1+0.3x0.1
        assert call["miss"] == pytest.approx(0.0)
    assert tier1["note"] is None and tier1["kind"] == "live"
    assert news["note"] == "scaled" and news["kind"] is None
    assert combined["note"] is None and combined["kind"] == "live"  # real blend; carries the Tier 1 snapshot kind


def test_filters_and_empty_result(client):
    assert client.get("/api/stats/events?year=2025").get_json()["rows"] == []
    assert len(client.get("/api/stats/events?year=2026&month=10").get_json()["rows"]) == 1


@pytest.mark.parametrize("value", ["abc", "²", "0", "-3"])
def test_garbage_year_is_ignored_not_a_500(client, value):
    resp = client.get(f"/api/stats/events?year={value}")
    assert resp.status_code == 200 and len(resp.get_json()["rows"]) == 1


def test_chart_route(client):
    data = client.get("/api/stats/chart?event=CPI%20m/m&method=combined").get_json()
    assert data["method"] == "combined" and data["unit"] == "%"
    point = data["points"][0]
    assert point["month"] == "2026-10" and point["label"] == "2026-10"
    assert point["event_time_utc"] == WHEN.isoformat()
    assert point["forecast"] == 0.3 and point["actual"] == 0.4
    assert point["predicted"] == pytest.approx(0.4) and point["verdict"] == "right"
    assert client.get("/api/stats/chart?event=CPI%20m/m&method=nope").status_code == 400
    assert client.get("/api/stats/chart?method=tier1").status_code == 400


def test_scoreboard_route_has_the_fixed_weight_footnote(client):
    data = client.get("/api/stats/scoreboard?event=CPI%20m/m").get_json()
    assert set(data["methods"]) == {"tier1", "news", "combined"}
    assert data["footnote"] == "Weights fixed at 70/30 until the 2027-01-15 review."


def test_scoreboard_route_serves_live_reconstructed_and_with_news_counts(full_client):
    data = full_client.get("/api/stats/scoreboard?event=CPI%20m/m&month=10").get_json()
    zero = {"scored": 0, "right": 0}
    one_right = {"scored": 1, "right": 1}
    for name in ("tier1", "news"):
        assert data["methods"][name] == {
            "scored": 1, "right": 1, "accuracy": None, "accuracy_shown": False,
            "mean_miss": pytest.approx(0.0), "by_kind": {"live": one_right, "reconstructed": zero},
        }
    assert data["methods"]["combined"] == {
        "scored": 1, "right": 1, "accuracy": None, "accuracy_shown": False, "mean_miss": pytest.approx(0.0),
        "by_kind": {"live": one_right, "reconstructed": zero}, "with_news": one_right,
    }
    assert data["min_for_percent"] == 20


def test_components_route(client):
    data = client.get("/api/stats/components/cleveland_nowcast").get_json()
    assert set(data) == {"metric", "title", "summary", "components", "note"}
    assert data["metric"] == "cleveland_nowcast" and data["components"]
    assert client.get("/api/stats/components/nope").status_code == 404


# --- connection handling (default factory only; the seam above shares in-memory DBs across requests) ---------

def test_default_connections_are_closed_after_each_request(monkeypatch):
    opened = []

    def fake_dash(*a, **kw):
        opened.append(ws.get_connection(":memory:"))
        return opened[-1]

    def fake_bt(*a, **kw):
        opened.append(bs.get_connection(":memory:"))
        return opened[-1]

    monkeypatch.setattr(app_module, "get_connection", fake_dash)
    monkeypatch.setattr(app_module, "get_backtest_connection", fake_bt)
    client = app_module.app.test_client()
    for url in ("/api/stats/events", "/api/stats/scoreboard", "/api/stats/chart?event=CPI%20m/m&method=tier1"):
        opened.clear()
        assert client.get(url).status_code == 200
        assert len(opened) == 2
        for conn in opened:
            with pytest.raises(sqlite3.ProgrammingError):       # closed
                conn.execute("SELECT 1")


def test_first_connection_is_closed_if_opening_the_second_fails(monkeypatch):
    opened = []

    def fake_dash(*a, **kw):
        opened.append(ws.get_connection(":memory:"))
        return opened[-1]

    def boom(*a, **kw):
        raise sqlite3.OperationalError("cannot open")

    monkeypatch.setattr(app_module, "get_connection", fake_dash)
    monkeypatch.setattr(app_module, "get_backtest_connection", boom)
    with pytest.raises(sqlite3.OperationalError):
        app_module._open_stats_connections()
    with pytest.raises(sqlite3.ProgrammingError):
        opened[0].execute("SELECT 1")
