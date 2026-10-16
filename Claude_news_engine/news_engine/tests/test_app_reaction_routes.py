# tests/test_app_reaction_routes.py
"""
Market-reaction Stats routes (spec sections 5, 7, 8): /api/stats/reaction/leaderboard and /releases.

Explicit serializers: every served object's field set is asserted exactly. In-memory dashboard and backtest
DBs behind the existing `_stats_connections` seam: never the live DBs, never the network. Seeded scenario
(gold; CPI m/m hotter than forecast -> sell, Unemployment Claims higher -> buy):

  Jan 05 12:30  CPI m/m        untagged (inferred High)  hot   -> sell    gold -4.0 sell   solo hit
  Mar 03 12:30  CPI m/m        High                      hot   -> sell  \\ gold -4.0 sell   CPI matched
  Mar 03 12:30  Unemp. Claims  Low                       higher-> buy   /                  Claims overruled
  Apr 07 12:30  CPI m/m        High                      hot   -> sell    gold -4.0 sell   solo hit (+ Tier 1 call, right)
  US30 has one reaction row at Apr 07 (buy, +40): CPI misses there.
"""
import datetime as dt
import sqlite3

import pytest

import webapp.app as app_module
from data_layer import brent_feed
from scoring import backtest_store as bs
from webapp import store as ws
from webapp.reaction_rules import REACTION_BASELINE_QUANTILE as Q, rate_display

UTC = dt.timezone.utc
P0 = 2000.0                    # move_pct = move / 20

LEADERBOARD_KEYS = {"instrument", "instruments", "window", "quantile", "rows", "disclaimers",
                    "reactions_available"}
ROW_KEYS = {"event_title", "impact_effective", "impact_inferred", "releases", "solo", "shared", "in_conflict",
            "reaction", "hit", "avg_move_pct", "engine", "few"}
RATE_KEYS = {"k", "n", "percent", "interval", "few"}
ENGINE_KEYS = {"k", "n"}
RELEASES_KEYS = {"event_title", "instrument", "releases"}
RELEASE_KEYS = {"event_time_utc", "move", "move_pct", "threshold", "reaction", "lean", "credit", "cluster_size",
                "hidden_in_cluster", "cluster", "engine_call", "note"}
CLUSTER_KEYS = {"event_title", "lean", "credit", "impact_effective"}
ENGINE_CALL_KEYS = {"method", "verdict"}
DISCLAIMERS = {
    "association": "Reaction is measured over 5 minutes against the 75th-percentile ordinary move for that "
                   "hour; it shows association, not proof that the release caused the move.",
    "cluster": "Credit in a cluster is shared or matched, never exclusive.",
}


def _t(month: int, day: int) -> dt.datetime:
    return dt.datetime(2026, month, day, 12, 30, tzinfo=UTC)


JAN, MAR, APR = _t(1, 5), _t(3, 3), _t(4, 7)


def _ev(dash, title, when, forecast, actual, impact):
    stamp = when.isoformat()
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, stamp, forecast, None, actual, None, stamp, stamp, "t", impact, "USD"))
    dash.commit()


def _react(bt, when, reaction, move, typical=1.0, instrument="XAUUSD"):
    bs.record_release_reaction(bt, when, instrument, "ok", p0=P0, p5=P0 + move, typical_abs_move=typical,
                               reaction=reaction, baseline_quantile=Q, reaction_multiple=1.0)


def _seed(dash, bt):
    for symbol in ("XAUUSD", "US30"):
        ws.add_tracked_symbol(dash, symbol)
    _ev(dash, "CPI m/m", JAN, "0.3%", "0.4%", None)
    _ev(dash, "CPI m/m", MAR, "0.3%", "0.4%", "High")
    _ev(dash, "Unemployment Claims", MAR, "220K", "240K", "Low")
    _ev(dash, "CPI m/m", APR, "0.3%", "0.4%", "High")
    for when in (JAN, MAR, APR):
        _react(bt, when, "sell", -4.0)
    _react(bt, APR, "buy", 40.0, typical=10.0, instrument="US30")
    bs.record_nowcast_snapshot(bt, "CPI m/m", APR, 0.4, APR - dt.timedelta(days=2), "cleveland", "live")


@pytest.fixture(autouse=True)
def no_live_brent(monkeypatch):
    monkeypatch.setattr(brent_feed, "get_brent_series", lambda *a, **kw: None)


@pytest.fixture
def client(monkeypatch):
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    _seed(dash, bt)
    monkeypatch.setattr(app_module, "_stats_connections", lambda: (dash, bt))
    return app_module.app.test_client()


def _board(client, query=""):
    resp = client.get("/api/stats/reaction/leaderboard" + query)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()


def _rows(board):
    return {r["event_title"]: r for r in board["rows"]}


def _releases(client, query):
    resp = client.get("/api/stats/reaction/releases" + query)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()


# ---- leaderboard: exact fields, real values -------------------------------------------------------------

def test_leaderboard_serves_every_field_the_page_renders(client):
    board = _board(client, "?instrument=XAUUSD")
    assert set(board) == LEADERBOARD_KEYS
    assert board["instrument"] == "XAUUSD" and board["quantile"] == Q == 0.75
    assert board["instruments"] == ["US30", "XAUUSD"]              # the tracked symbols, for the select
    assert board["window"] == "5 min after release"
    assert board["disclaimers"] == DISCLAIMERS
    rows = _rows(board)
    assert [r["event_title"] for r in board["rows"]] == ["CPI m/m", "Unemployment Claims"]   # reactions desc
    for row in board["rows"]:
        assert set(row) == ROW_KEYS
        assert set(row["reaction"]) == RATE_KEYS and set(row["hit"]) == RATE_KEYS

    cpi = rows["CPI m/m"]
    assert (cpi["releases"], cpi["solo"], cpi["shared"], cpi["in_conflict"]) == (3, 2, 0, 1)
    assert cpi["impact_effective"] == "High" and cpi["impact_inferred"] is True    # Jan row is untagged
    assert cpi["reaction"] == rate_display(3, 3) == {
        "k": 3, "n": 3, "percent": None, "interval": cpi["reaction"]["interval"], "few": True}
    assert cpi["reaction"]["interval"] == pytest.approx([0.4385, 1.0], abs=1e-3)   # Wilson 95% for 3 of 3
    assert cpi["hit"] == cpi["reaction"]                                             # matched + 2 solo hits
    assert cpi["avg_move_pct"] == pytest.approx(0.2)                                 # -0.2% move, sell lean
    assert cpi["engine"] == {"k": 1, "n": 1} and set(cpi["engine"]) == ENGINE_KEYS    # only April has a call
    assert cpi["few"] is True

    claims = rows["Unemployment Claims"]
    assert (claims["releases"], claims["solo"], claims["shared"], claims["in_conflict"]) == (1, 0, 0, 1)
    assert claims["impact_effective"] == "Low" and claims["impact_inferred"] is False
    assert (claims["reaction"]["k"], claims["reaction"]["n"]) == (1, 1)
    assert (claims["hit"]["k"], claims["hit"]["n"]) == (0, 1)                        # overruled
    assert claims["avg_move_pct"] == pytest.approx(-0.2)
    assert claims["engine"] is None and claims["few"] is True


def test_leaderboard_instrument_defaults_to_gold_and_us30_reads_its_own_rows(client):
    assert _board(client)["instrument"] == "XAUUSD"
    us30 = _board(client, "?instrument=US30")
    assert us30["instrument"] == "US30" and us30["instruments"] == ["US30", "XAUUSD"]
    [cpi] = us30["rows"]
    assert cpi["event_title"] == "CPI m/m" and (cpi["releases"], cpi["hit"]["k"]) == (1, 0)
    assert cpi["avg_move_pct"] == pytest.approx(-2.0)


def test_instrument_defaults_to_the_first_tracked_symbol_when_gold_is_not_tracked(monkeypatch):
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    _seed(dash, bt)
    dash.execute("DELETE FROM tracked_symbols WHERE symbol = 'XAUUSD'")
    dash.commit()
    monkeypatch.setattr(app_module, "_stats_connections", lambda: (dash, bt))
    board = _board(app_module.app.test_client())
    assert board["instrument"] == "US30" and board["instruments"] == ["US30"]


# ---- the impacts filter, shared with the existing Stats routes ----------------------------------------------

def test_leaderboard_impacts_filter(client):
    assert set(_rows(_board(client))) == {"CPI m/m", "Unemployment Claims"}                # default: no filter
    high = _board(client, "?impacts=High")
    assert set(_rows(high)) == {"CPI m/m"}
    cpi = high["rows"][0]
    assert (cpi["releases"], cpi["solo"], cpi["in_conflict"], cpi["impact_inferred"]) == (2, 1, 1, False)
    assert set(_rows(_board(client, "?impacts=Low"))) == {"Unemployment Claims"}
    unrated = _board(client, "?impacts=Unrated")
    assert unrated["rows"][0]["releases"] == 1 and unrated["rows"][0]["impact_inferred"] is True
    assert set(_rows(_board(client, "?impacts=High,Low"))) == {"CPI m/m", "Unemployment Claims"}
    assert _board(client, "?impacts=Medium")["rows"] == []


@pytest.mark.parametrize("query", ["?impacts=", "?impacts=Bogus", "?impacts=high", "?impacts=,,", "?impacts=%20"])
def test_unknown_or_empty_impacts_mean_no_filter(client, query):
    assert set(_rows(_board(client, query))) == {"CPI m/m", "Unemployment Claims"}


def test_unknown_impact_values_are_ignored_next_to_valid_ones(client):
    assert set(_rows(_board(client, "?impacts=Bogus,High,nope"))) == {"CPI m/m"}


def test_year_and_month_filters(client):
    assert _rows(_board(client, "?year=2026&month=3"))["CPI m/m"]["releases"] == 1
    assert _board(client, "?year=2025")["rows"] == []
    assert _rows(_board(client, "?year=abc&month=0"))["CPI m/m"]["releases"] == 3         # garbage = no filter


# ---- releases: exact fields, real values --------------------------------------------------------------------

def test_releases_serves_every_field_the_drilldown_renders(client):
    data = _releases(client, "?instrument=XAUUSD&event=CPI%20m/m")
    assert set(data) == RELEASES_KEYS
    assert data["event_title"] == "CPI m/m" and data["instrument"] == "XAUUSD"
    releases = data["releases"]
    assert [r["event_time_utc"] for r in releases] == [APR.isoformat(), MAR.isoformat(), JAN.isoformat()]   # newest first
    for rel in releases:
        assert set(rel) == RELEASE_KEYS
        for member in rel["cluster"]:
            assert set(member) == CLUSTER_KEYS

    apr, mar, jan = releases
    assert apr["move"] == pytest.approx(-4.0) and apr["move_pct"] == pytest.approx(-0.2)
    assert apr["threshold"] == pytest.approx(1.0)
    assert (apr["reaction"], apr["lean"], apr["credit"]) == ("sell", "sell", "solo_hit")
    assert (apr["cluster_size"], apr["hidden_in_cluster"], apr["note"]) == (1, 0, None)
    assert apr["cluster"] == [{"event_title": "CPI m/m", "lean": "sell", "credit": "solo_hit",
                               "impact_effective": "High"}]
    assert set(apr["engine_call"]) == ENGINE_CALL_KEYS
    assert apr["engine_call"] == {"method": "combined", "verdict": "right"}

    assert (mar["credit"], mar["cluster_size"], mar["hidden_in_cluster"]) == ("matched", 2, 0)
    assert mar["cluster"] == [
        {"event_title": "CPI m/m", "lean": "sell", "credit": "matched", "impact_effective": "High"},
        {"event_title": "Unemployment Claims", "lean": "buy", "credit": "overruled", "impact_effective": "Low"}]
    assert mar["engine_call"] is None

    assert jan["credit"] == "solo_hit" and jan["cluster"][0]["impact_effective"] == "High"   # inferred, not Unrated


def test_releases_hidden_cluster_members_follow_the_impacts_filter(client):
    data = _releases(client, "?event=CPI%20m/m&impacts=High")
    assert [r["event_time_utc"] for r in data["releases"]] == [APR.isoformat(), MAR.isoformat()]
    mar = data["releases"][1]
    assert mar["credit"] == "matched"                       # the hidden Low event still shapes the credit
    assert (mar["cluster_size"], mar["hidden_in_cluster"]) == (2, 1)
    assert [m["event_title"] for m in mar["cluster"]] == ["CPI m/m"]
    assert _releases(client, "?event=Unemployment%20Claims&impacts=High")["releases"] == []
    assert len(_releases(client, "?event=CPI%20m/m&impacts=Unrated")["releases"]) == 1
    assert len(_releases(client, "?event=CPI%20m/m&impacts=")["releases"]) == 3


def test_releases_year_month_and_us30(client):
    assert len(_releases(client, "?event=CPI%20m/m&year=2026&month=4")["releases"]) == 1
    assert _releases(client, "?event=CPI%20m/m&year=2025")["releases"] == []
    data = _releases(client, "?event=CPI%20m/m&instrument=US30")
    assert data["instrument"] == "US30"
    apr, mar, jan = data["releases"]                         # only April has a US30 reaction row
    assert (apr["credit"], apr["reaction"], apr["lean"]) == ("solo_miss", "buy", "sell")
    assert apr["threshold"] == pytest.approx(10.0) and apr["move"] == pytest.approx(40.0)
    assert (mar["credit"], mar["reaction"], mar["move"], mar["threshold"]) == ("no_data", None, None, None)
    assert (jan["credit"], jan["reaction"]) == ("no_data", None)


def test_unknown_event_gives_an_empty_release_list_not_an_error(client):
    assert _releases(client, "?event=Nope") == {"event_title": "Nope", "instrument": "XAUUSD", "releases": []}


# ---- 400s -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "/api/stats/reaction/leaderboard?instrument=EURUSD",
    "/api/stats/reaction/leaderboard?instrument=xauusd",                  # case-sensitive: not a tracked symbol
    "/api/stats/reaction/releases?event=CPI%20m/m&instrument=EURUSD",
])
def test_untracked_instrument_is_a_400_with_an_error_message(client, url):
    resp = client.get(url)
    assert resp.status_code == 400
    body = resp.get_json()
    assert set(body) == {"error"} and "instrument" in body["error"]


@pytest.mark.parametrize("url", ["/api/stats/reaction/releases", "/api/stats/reaction/releases?event=",
                                 "/api/stats/reaction/releases?instrument=XAUUSD"])
def test_releases_requires_an_event(client, url):
    resp = client.get(url)
    assert resp.status_code == 400
    body = resp.get_json()
    assert set(body) == {"error"} and "event" in body["error"]


def test_no_tracked_symbols_is_a_400(monkeypatch):
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    monkeypatch.setattr(app_module, "_stats_connections", lambda: (dash, bt))
    client = app_module.app.test_client()
    assert client.get("/api/stats/reaction/leaderboard").status_code == 400
    assert client.get("/api/stats/reaction/releases?event=CPI%20m/m").status_code == 400


def test_empty_instrument_param_is_treated_as_absent(client):
    assert _board(client, "?instrument=")["instrument"] == "XAUUSD"


# ---- read-only and connection handling ----------------------------------------------------------------------

def test_routes_write_nothing(monkeypatch):
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    _seed(dash, bt)
    monkeypatch.setattr(app_module, "_stats_connections", lambda: (dash, bt))
    before = (dash.total_changes, bt.total_changes)
    client = app_module.app.test_client()
    _board(client)
    _releases(client, "?event=CPI%20m/m")
    assert (dash.total_changes, bt.total_changes) == before


def test_default_connections_are_closed_after_each_request(monkeypatch):
    opened = []

    def fake_dash(*a, **kw):
        conn = ws.get_connection(":memory:")
        ws.add_tracked_symbol(conn, "XAUUSD")
        opened.append(conn)
        return conn

    def fake_bt(*a, **kw):
        opened.append(bs.get_connection(":memory:"))
        return opened[-1]

    monkeypatch.setattr(app_module, "get_connection", fake_dash)
    monkeypatch.setattr(app_module, "get_backtest_connection", fake_bt)
    client = app_module.app.test_client()
    ok = ("/api/stats/reaction/leaderboard", "/api/stats/reaction/leaderboard?impacts=High&instrument=XAUUSD",
          "/api/stats/reaction/releases?event=CPI%20m/m")
    bad = ("/api/stats/reaction/leaderboard?instrument=EURUSD",
           "/api/stats/reaction/releases?event=CPI%20m/m&instrument=EURUSD")
    for url, status in [(u, 200) for u in ok] + [(u, 400) for u in bad]:
        opened.clear()
        assert client.get(url).status_code == status
        assert len(opened) == 2, url
        for conn in opened:
            with pytest.raises(sqlite3.ProgrammingError):           # closed
                conn.execute("SELECT 1")


# ---- reactions_available (final fix wave B) ---------------------------------------------------------------

def test_leaderboard_says_whether_reactions_were_computed_for_the_instrument(monkeypatch):
    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    _seed(dash, bt)
    ws.add_tracked_symbol(dash, "EURUSD")                       # tracked, never computed
    monkeypatch.setattr(app_module, "_stats_connections", lambda: (dash, bt))
    client = app_module.app.test_client()
    gold = _board(client, "?instrument=XAUUSD")
    assert set(gold) == LEADERBOARD_KEYS and gold["reactions_available"] is True
    assert _board(client, "?instrument=XAUUSD&impacts=Medium")["reactions_available"] is True
    eur = _board(client, "?instrument=EURUSD")
    assert set(eur) == LEADERBOARD_KEYS
    assert eur["reactions_available"] is False and eur["rows"] == []
