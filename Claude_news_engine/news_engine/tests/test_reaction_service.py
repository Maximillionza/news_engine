# tests/test_reaction_service.py
"""
Tests for webapp/reaction_service.py (market-reaction spec §4, §4.1, §4.2, §5; controller decisions C-E).

In-memory dashboard and backtest DBs with seeded rows only: never the live DBs, never the network.
Gold leans used below (stats_methods.market_lean on XAUUSD): CPI m/m / Core CPI m/m hotter than forecast ->
sell, cooler -> buy; Unemployment Rate / Unemployment Claims higher -> buy. "Federal Funds Rate" has no
surprise map, so it never has a lean.
"""
import datetime as dt
from types import SimpleNamespace

import pytest

from data_layer import brent_feed
from scoring import backtest_store as bs
from webapp import reaction_service as rs
from webapp import store as ws
from webapp.reaction_rules import REACTION_BASELINE_QUANTILE as Q

UTC = dt.timezone.utc
P0 = 2000.0                      # every seeded reaction starts here, so move_pct = move / 20
GOLD = "XAUUSD"


@pytest.fixture(autouse=True)
def no_live_brent(monkeypatch):
    """The engine column reuses stats_service.build_rows; nothing may reach FRED."""
    monkeypatch.setattr(brent_feed, "get_brent_series", lambda *a, **kw: None)


@pytest.fixture
def conns():
    return ws.get_connection(":memory:"), bs.get_connection(":memory:")


def _t(month: int, day: int = 3, hour: int = 12, minute: int = 30) -> dt.datetime:
    return dt.datetime(2026, month, day, hour, minute, tzinfo=UTC)


def _ev(dash, title, when, forecast=None, actual=None, impact="High", country="USD", when_text=None):
    stamp = when_text if when_text is not None else when.isoformat()
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, stamp, forecast, None, actual, None, stamp, stamp, "t", impact, country))
    dash.commit()


def _hot_cpi(dash, when, title="CPI m/m", impact="High"):
    _ev(dash, title, when, "0.3%", "0.4%", impact)          # hotter -> gold sell


def _react(bt, when, reaction, move, typical=1.0, instrument=GOLD):
    bs.record_release_reaction(bt, when, instrument, "ok", p0=P0, p5=P0 + move, typical_abs_move=typical,
                               reaction=reaction, baseline_quantile=Q, reaction_multiple=1.0)


def _no_data(bt, when, typical=1.0, instrument=GOLD):
    bs.record_release_reaction(bt, when, instrument, "no_data", typical_abs_move=typical,
                               baseline_quantile=Q, reaction_multiple=1.0)


def _board(dash, bt, instrument=GOLD, impacts=None, year=None, month=None):
    return rs.build_leaderboard(dash, bt, instrument, impacts, year, month)


def _row(board, title):
    found = [r for r in board["rows"] if r["event_title"] == title]
    assert len(found) == 1, f"{title} not exactly once in {[r['event_title'] for r in board['rows']]}"
    return found[0]


def _releases(dash, bt, title, instrument=GOLD, impacts=None, year=None, month=None):
    return rs.build_event_releases(dash, bt, instrument, title, impacts, year, month)["releases"]


# ---- payload shape --------------------------------------------------------------------------------

LEADERBOARD_ROW_KEYS = {"event_title", "impact_effective", "impact_inferred", "releases", "solo", "shared",
                        "in_conflict", "reaction", "hit", "avg_move_pct", "engine", "few"}
RELEASE_KEYS = {"event_time_utc", "move", "move_pct", "threshold", "reaction", "lean", "credit", "cluster_size",
                "hidden_in_cluster", "cluster", "engine_call", "note"}


def test_leaderboard_payload_shape_and_exact_disclaimers(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _react(bt, _t(3), "sell", -4.0)
    board = _board(dash, bt)
    assert set(board) == {"instrument", "quantile", "rows", "disclaimers", "reactions_available"}
    assert board["instrument"] == GOLD and board["quantile"] == Q == 0.75
    assert board["disclaimers"] == {
        "association": "Reaction is measured over 5 minutes against the 75th-percentile ordinary move for that "
                       "hour; it shows association, not proof that the release caused the move.",
        "cluster": "Credit in a cluster is shared or matched, never exclusive.",
    }
    assert set(board["rows"][0]) == LEADERBOARD_ROW_KEYS
    payload = rs.build_event_releases(dash, bt, GOLD, "CPI m/m", None, None, None)
    assert set(payload) == {"event_title", "instrument", "releases"}
    assert payload["event_title"] == "CPI m/m" and payload["instrument"] == GOLD
    assert set(payload["releases"][0]) == RELEASE_KEYS
    assert set(payload["releases"][0]["cluster"][0]) == {"event_title", "lean", "credit", "impact_effective"}


# ---- solo / shared / conflict ---------------------------------------------------------------------

def test_solo_cluster_hit(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _react(bt, _t(3), "sell", -4.0)
    row = _row(_board(dash, bt), "CPI m/m")
    assert (row["releases"], row["solo"], row["shared"], row["in_conflict"]) == (1, 1, 0, 0)
    assert (row["reaction"]["k"], row["reaction"]["n"]) == (1, 1)
    assert (row["hit"]["k"], row["hit"]["n"]) == (1, 1)
    assert row["avg_move_pct"] == pytest.approx(0.2)          # -0.2% move, signed in the sell direction
    assert row["impact_effective"] == "High" and row["impact_inferred"] is False
    [rel] = _releases(dash, bt, "CPI m/m")
    assert rel["event_time_utc"] == _t(3).isoformat()
    assert rel["lean"] == "sell" and rel["reaction"] == "sell" and rel["credit"] == "solo_hit"
    assert rel["move"] == pytest.approx(-4.0) and rel["move_pct"] == pytest.approx(-0.2)
    assert rel["threshold"] == pytest.approx(1.0)
    assert (rel["cluster_size"], rel["hidden_in_cluster"], rel["note"]) == (1, 0, None)
    assert rel["cluster"] == [{"event_title": "CPI m/m", "lean": "sell", "credit": "solo_hit",
                               "impact_effective": "High"}]


def test_shared_cluster_two_agreeing_events_share_the_miss(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _hot_cpi(dash, _t(3), title="Core CPI m/m")
    _react(bt, _t(3), "buy", 4.0)
    board = _board(dash, bt)
    for title in ("CPI m/m", "Core CPI m/m"):
        row = _row(board, title)
        assert (row["releases"], row["solo"], row["shared"], row["in_conflict"]) == (1, 0, 1, 0)
        assert (row["hit"]["k"], row["hit"]["n"]) == (0, 1)
        assert row["avg_move_pct"] == pytest.approx(-0.2)     # moved against the implied sell
    [rel] = _releases(dash, bt, "CPI m/m")
    assert rel["credit"] == "shared_miss" and rel["cluster_size"] == 2 and rel["hidden_in_cluster"] == 0
    assert [(m["event_title"], m["credit"]) for m in rel["cluster"]] == [
        ("CPI m/m", "shared_miss"), ("Core CPI m/m", "shared_miss")]


def test_conflict_cluster_matched_and_overruled(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))                                         # sell
    _ev(dash, "Unemployment Rate", _t(3), "4.1%", "4.3%")        # higher -> buy
    _react(bt, _t(3), "buy", 3.0)
    board = _board(dash, bt)
    cpi, ur = _row(board, "CPI m/m"), _row(board, "Unemployment Rate")
    assert (cpi["in_conflict"], cpi["solo"], cpi["shared"], cpi["hit"]["k"]) == (1, 0, 0, 0)
    assert (ur["in_conflict"], ur["hit"]["k"], ur["hit"]["n"]) == (1, 1, 1)
    assert ur["avg_move_pct"] == pytest.approx(0.15) and cpi["avg_move_pct"] == pytest.approx(-0.15)
    assert _releases(dash, bt, "CPI m/m")[0]["credit"] == "overruled"
    assert _releases(dash, bt, "Unemployment Rate")[0]["credit"] == "matched"


def test_all_mixed_cluster_has_no_signal_and_is_excluded_from_every_rate(conns):
    dash, bt = conns
    _ev(dash, "CPI m/m", _t(3), "0.3%", "0.3%")                  # in line
    _ev(dash, "Federal Funds Rate", _t(3), "4.50%", "4.75%")     # no surprise map
    _react(bt, _t(3), "buy", 5.0)
    assert _board(dash, bt)["rows"] == []
    [rel] = _releases(dash, bt, "CPI m/m")
    assert rel["lean"] == "mixed" and rel["credit"] == "no_signal" and rel["reaction"] == "buy"
    assert all(m["credit"] == "no_signal" for m in rel["cluster"])


def test_missing_or_unparseable_numbers_are_no_signal(conns):
    dash, bt = conns
    _ev(dash, "CPI m/m", _t(3), "0.3%", None)                    # not released yet
    _ev(dash, "CPI m/m", _t(4), "N/A", "0.4%")
    for month in (3, 4):
        _react(bt, _t(month), "sell", -4.0)
    assert _board(dash, bt)["rows"] == []
    assert [r["lean"] for r in _releases(dash, bt, "CPI m/m")] == ["mixed", "mixed"]


def test_none_reaction_counts_as_a_release_without_a_reaction(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _react(bt, _t(3), "none", -0.5)
    row = _row(_board(dash, bt), "CPI m/m")
    assert row["releases"] == 1 and (row["solo"], row["shared"], row["in_conflict"]) == (0, 0, 0)
    assert (row["reaction"]["k"], row["reaction"]["n"]) == (0, 1)
    assert (row["hit"]["k"], row["hit"]["n"]) == (0, 0)
    assert row["avg_move_pct"] is None
    rel = _releases(dash, bt, "CPI m/m")[0]
    assert rel["credit"] == "no_reaction" and rel["reaction"] == "none"


def test_no_data_and_missing_minutes_are_excluded_from_rates_but_listed(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _hot_cpi(dash, _t(4))
    _hot_cpi(dash, _t(5))
    _react(bt, _t(3), "sell", -4.0)
    _no_data(bt, _t(4), typical=1.5)
    # 2026-05 has no reaction row at all
    row = _row(_board(dash, bt), "CPI m/m")
    assert row["releases"] == 1
    rels = _releases(dash, bt, "CPI m/m")
    assert [r["event_time_utc"][:7] for r in rels] == ["2026-05", "2026-04", "2026-03"]      # newest first
    assert [(r["reaction"], r["credit"]) for r in rels] == [(None, "no_data"), (None, "no_data"), ("sell", "solo_hit")]
    assert rels[1]["move_pct"] is None and rels[1]["threshold"] == pytest.approx(1.5)
    assert rels[0]["threshold"] is None


# ---- filters and hidden cluster members -----------------------------------------------------------

def test_hidden_event_still_takes_part_in_the_cluster_credit(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))                                                   # High, sell
    _ev(dash, "Unemployment Claims", _t(3), "220K", "240K", impact="Low")   # Low, higher -> buy
    _react(bt, _t(3), "sell", -4.0)
    high = frozenset({"High"})
    board = _board(dash, bt, impacts=high)
    assert [r["event_title"] for r in board["rows"]] == ["CPI m/m"]
    cpi = _row(board, "CPI m/m")
    assert (cpi["in_conflict"], cpi["solo"], cpi["hit"]["k"]) == (1, 0, 1)     # matched, never solo
    [rel] = _releases(dash, bt, "CPI m/m", impacts=high)
    assert rel["credit"] == "matched" and rel["cluster_size"] == 2 and rel["hidden_in_cluster"] == 1
    assert [m["event_title"] for m in rel["cluster"]] == ["CPI m/m"]
    claims = _row(_board(dash, bt), "Unemployment Claims")                     # unfiltered: listed, overruled
    assert claims["in_conflict"] == 1 and claims["hit"]["k"] == 0
    assert _releases(dash, bt, "Unemployment Claims", impacts=high) == []


def test_impact_inheritance_and_the_unrated_bucket(conns):
    dash, bt = conns
    _ev(dash, "CPI m/m", _t(1), "0.3%", "0.4%", impact=None)     # seeded history, untagged
    _hot_cpi(dash, _t(3))
    _hot_cpi(dash, _t(4))
    for month in (1, 3, 4):
        _react(bt, _t(month), "sell", -4.0)
    unrated = _row(_board(dash, bt, impacts=frozenset({"Unrated"})), "CPI m/m")
    assert unrated["releases"] == 1 and unrated["impact_effective"] == "High" and unrated["impact_inferred"] is True
    high = _row(_board(dash, bt, impacts=frozenset({"High"})), "CPI m/m")
    assert high["releases"] == 2 and high["impact_inferred"] is False
    both = _row(_board(dash, bt, impacts=frozenset({"High", "Unrated"})), "CPI m/m")
    assert both["releases"] == 3 and both["impact_effective"] == "High" and both["impact_inferred"] is True
    [rel] = _releases(dash, bt, "CPI m/m", impacts=frozenset({"Unrated"}))
    assert rel["cluster"][0]["impact_effective"] == "High"
    assert _board(dash, bt, impacts=frozenset())["rows"] == []


def test_year_and_month_filters_apply_to_the_utc_release_date(conns):
    dash, bt = conns
    _hot_cpi(dash, dt.datetime(2025, 12, 10, 13, 30, tzinfo=UTC))
    _hot_cpi(dash, _t(1))
    _hot_cpi(dash, _t(3))
    _react(bt, dt.datetime(2025, 12, 10, 13, 30, tzinfo=UTC), "sell", -4.0)
    _react(bt, _t(1), "sell", -4.0)
    _react(bt, _t(3), "buy", 4.0)
    assert _row(_board(dash, bt), "CPI m/m")["releases"] == 3
    assert _row(_board(dash, bt, year=2026), "CPI m/m")["releases"] == 2
    march = _row(_board(dash, bt, year=2026, month=3), "CPI m/m")
    assert march["releases"] == 1 and march["hit"]["k"] == 0
    assert _board(dash, bt, year=2024)["rows"] == []
    assert len(_releases(dash, bt, "CPI m/m", year=2026)) == 2
    assert [r["event_time_utc"] for r in _releases(dash, bt, "CPI m/m", month=12)] == [
        dt.datetime(2025, 12, 10, 13, 30, tzinfo=UTC).isoformat()]


def test_release_times_are_normalised_to_utc(conns):
    dash, bt = conns
    _ev(dash, "CPI m/m", _t(3), "0.3%", "0.4%", when_text="2026-03-03T14:30:00+02:00")   # SAST stamp
    _react(bt, _t(3), "sell", -4.0)
    assert _row(_board(dash, bt), "CPI m/m")["hit"]["k"] == 1
    assert _releases(dash, bt, "CPI m/m")[0]["event_time_utc"] == "2026-03-03T12:30:00+00:00"


# ---- rate floors -----------------------------------------------------------------------------------

def _seed_hot_releases(dash, bt, count, start=0):
    first = dt.datetime(2026, 1, 5, 12, 30, tzinfo=UTC)
    for i in range(start, start + count):
        when = first + dt.timedelta(days=7 * i)
        _hot_cpi(dash, when)
        _react(bt, when, "sell", -4.0)


def test_percent_is_hidden_at_19_releases_and_shown_at_20(conns):
    dash, bt = conns
    _seed_hot_releases(dash, bt, 19)
    row = _row(_board(dash, bt), "CPI m/m")
    assert row["releases"] == 19 and row["reaction"]["percent"] is None and row["hit"]["percent"] is None
    assert row["reaction"]["interval"] is not None
    _seed_hot_releases(dash, bt, 1, start=19)
    row = _row(_board(dash, bt), "CPI m/m")
    assert row["releases"] == 20 and row["reaction"]["percent"] == 100.0 and row["hit"]["percent"] == 100.0


def test_few_tag_at_7_but_not_at_8(conns):
    dash, bt = conns
    _seed_hot_releases(dash, bt, 7)
    assert _row(_board(dash, bt), "CPI m/m")["few"] is True
    _seed_hot_releases(dash, bt, 1, start=7)
    assert _row(_board(dash, bt), "CPI m/m")["few"] is False


def test_avg_move_is_signed_in_the_implied_direction_over_reactions_only(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(1))                                   # sell, moved -4 -> +0.2
    _ev(dash, "CPI m/m", _t(2), "0.3%", "0.2%")             # cooler -> buy, moved -2 -> -0.1
    _hot_cpi(dash, _t(3))                                   # no reaction: left out of the average
    _react(bt, _t(1), "sell", -4.0)
    _react(bt, _t(2), "sell", -2.0)
    _react(bt, _t(3), "none", 0.5)
    row = _row(_board(dash, bt), "CPI m/m")
    assert row["releases"] == 3 and row["reaction"]["k"] == 2
    assert row["avg_move_pct"] == pytest.approx((0.2 - 0.1) / 2)


# ---- engine column ----------------------------------------------------------------------------------

def _call(verdict):
    return SimpleNamespace(verdict=verdict)


def test_engine_column_prefers_combined_then_tier1_then_news(conns, monkeypatch):
    dash, bt = conns
    months = (1, 2, 3, 4)
    for month in months:
        _hot_cpi(dash, _t(month))
        _react(bt, _t(month), "sell", -4.0)
    _hot_cpi(dash, _t(5), title="Core CPI m/m")
    _react(bt, _t(5), "sell", -4.0)
    fake = [
        SimpleNamespace(event_title="CPI m/m", event_time_utc=_t(1),
                        combined=_call("right"), tier1=_call("wrong"), news=_call("wrong")),
        SimpleNamespace(event_title="CPI m/m", event_time_utc=_t(2),
                        combined=None, tier1=_call("wrong"), news=_call("right")),
        SimpleNamespace(event_title="CPI m/m", event_time_utc=_t(3),
                        combined=_call(None), tier1=None, news=_call("right")),
        SimpleNamespace(event_title="CPI m/m", event_time_utc=_t(4), combined=None, tier1=None, news=None),
        SimpleNamespace(event_title="Core CPI m/m", event_time_utc=_t(5), combined=None, tier1=None, news=None),
    ]
    monkeypatch.setattr(rs.stats_service, "build_rows", lambda *a, **kw: fake)
    board = _board(dash, bt)
    assert _row(board, "CPI m/m")["engine"] == {"k": 2, "n": 3}
    assert _row(board, "Core CPI m/m")["engine"] is None
    calls = {r["event_time_utc"][:7]: r["engine_call"] for r in _releases(dash, bt, "CPI m/m")}
    assert calls == {"2026-01": {"method": "combined", "verdict": "right"},
                     "2026-02": {"method": "tier1", "verdict": "wrong"},
                     "2026-03": {"method": "news", "verdict": "right"},
                     "2026-04": None}


def test_engine_column_from_a_real_nowcast_snapshot(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    bs.record_nowcast_snapshot(bt, "CPI m/m", _t(3), 0.4, _t(3) - dt.timedelta(days=2), "cleveland", "live")
    _react(bt, _t(3), "sell", -4.0)
    assert _row(_board(dash, bt), "CPI m/m")["engine"] == {"k": 1, "n": 1}
    assert _releases(dash, bt, "CPI m/m")[0]["engine_call"] == {"method": "combined", "verdict": "right"}


def test_engine_failure_degrades_to_no_engine_column(conns, monkeypatch):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _react(bt, _t(3), "sell", -4.0)

    def boom(*a, **kw):
        raise RuntimeError("stats down")

    monkeypatch.setattr(rs.stats_service, "build_rows", boom)
    row = _row(_board(dash, bt), "CPI m/m")
    assert row["engine"] is None and row["hit"]["k"] == 1


def _news_print_call(bt, title, when, direction, confidence):
    """A print call scored a day before the release; Stats turns it into the News lean (rule R3)."""
    bs.record_print_prediction_if_changed(
        bt, title, when, SimpleNamespace(direction=direction, confidence=confidence, article_count=7),
        now=when - dt.timedelta(days=1))


def test_engine_column_shows_the_st1_news_verdict_and_no_in_line_news_guess(conns):
    """
    B9 side effect (docs/b9-deploy.md section 1), no Market reaction code change: the engine column falls back
    to the Stats News verdict when Combined and Tier 1 have none, so it carries the ST1 News call. A News lean
    under 0.2 is a no-call, so the old "in line" News guess no longer earns a verdict here; a lean of 0.2 or
    more is a graded higher/lower call. Real stats_service.build_rows, no Tier 1 snapshot, so Combined is n/a.
    """
    dash, bt = conns
    for m, f, a in [(1, "0.3%", "0.2%"), (2, "0.3%", "0.4%"), (3, "0.3%", "0.4%")]:   # scale history, no calls
        _ev(dash, "CPI m/m", _t(m), f, a)
    _ev(dash, "CPI m/m", _t(4), "0.3%", "0.3%")              # in line: pre-B9 News 0.3 + 0.1 x 0.1 read 'right'
    _news_print_call(bt, "CPI m/m", _t(4), "higher", 0.1)    # |lean| 0.1 < 0.2 -> no call
    _ev(dash, "CPI m/m", _t(5), "0.3%", "0.4%")              # hotter
    _news_print_call(bt, "CPI m/m", _t(5), "higher", 0.5)    # |lean| 0.5 -> 'higher' call, right
    _react(bt, _t(4), "none", 0.5)
    _react(bt, _t(5), "sell", -4.0)

    stats_rows = {row.event_time_utc: row for row in rs.stats_service.build_rows(dash, bt)}
    no_call, called = stats_rows[_t(4)], stats_rows[_t(5)]
    assert no_call.combined is None and no_call.tier1 is None
    assert no_call.news_call == "no_call" and no_call.news.verdict is None
    assert rs._engine_call(no_call) is None
    assert called.combined is None and called.tier1 is None and called.news_call == "higher"
    assert rs._engine_call(called) == {"method": "news", "verdict": "right"}

    calls = {r["event_time_utc"][:7]: r["engine_call"] for r in _releases(dash, bt, "CPI m/m")}
    assert calls["2026-04"] is None
    assert calls["2026-05"] == {"method": "news", "verdict": "right"}


# ---- overlap note, duplicate collapse, sorting, robustness -------------------------------------------

def test_overlap_note_tags_a_release_inside_the_5_minute_window_without_changing_credit(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _ev(dash, "Federal Funds Rate", _t(3, minute=33), "4.50%", "4.50%", impact="Low")
    _hot_cpi(dash, _t(4))
    _ev(dash, "Federal Funds Rate", _t(4, minute=35), "4.50%", "4.50%", impact="Low")   # t+5: outside
    for when in (_t(3), _t(4)):
        _react(bt, when, "sell", -4.0)
    rels = _releases(dash, bt, "CPI m/m", impacts=frozenset({"High"}))
    assert [r["note"] for r in rels] == [None, "another release 3 min later"]
    assert [r["credit"] for r in rels] == ["solo_hit", "solo_hit"]
    assert _row(_board(dash, bt), "CPI m/m")["releases"] == 2


def test_same_title_duplicates_collapse_before_clustering(conns):
    dash, bt = conns
    for minute in (14, 15, 16):                                    # ADP-style chain: one release at 12:14
        _ev(dash, "CPI m/m", _t(3, minute=minute), "0.3%", "0.4%", impact="Low")
    _ev(dash, "Unemployment Rate", _t(3, minute=15), "4.1%", "4.3%", impact="Low")   # a different title at 12:15
    for minute in (14, 15, 16):
        _react(bt, _t(3, minute=minute), "sell", -4.0)
    board = _board(dash, bt)
    cpi = _row(board, "CPI m/m")
    assert (cpi["releases"], cpi["solo"]) == (1, 1)
    [rel] = _releases(dash, bt, "CPI m/m")
    assert rel["event_time_utc"] == _t(3, minute=14).isoformat()
    assert rel["cluster_size"] == 1
    assert rel["note"] == "another release 1 min later"            # Unemployment Rate at 12:15 is a real release
    ur = _releases(dash, bt, "Unemployment Rate")[0]
    assert (ur["cluster_size"], ur["credit"], ur["note"]) == (1, "solo_miss", None)   # duplicates never join it


def test_non_usd_rows_never_join_a_cluster(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _ev(dash, "Unemployment Rate", _t(3), "4.1%", "4.3%", country=None)
    _ev(dash, "German Ifo", _t(3), "88.0", "90.0", country="EUR")
    _react(bt, _t(3), "sell", -4.0)
    assert [r["event_title"] for r in _board(dash, bt)["rows"]] == ["CPI m/m"]
    assert _releases(dash, bt, "CPI m/m")[0]["cluster_size"] == 1


def test_rows_sort_by_reactions_then_releases_then_title(conns):
    dash, bt = conns
    # Retail Sales: 2 releases, 2 reactions. CPI: 3 releases, 1 reaction. Core CPI: 1 release, 1 reaction.
    # Unemployment Claims: 1 release, 1 reaction (ties Core CPI; title order decides).
    _ev(dash, "Retail Sales m/m", _t(1, hour=13), "0.3%", "0.5%")
    _ev(dash, "Retail Sales m/m", _t(2, hour=13), "0.3%", "0.5%")
    for month, reaction in ((1, "sell"), (2, "none"), (3, "none")):
        _hot_cpi(dash, _t(month))
        _react(bt, _t(month), reaction, -4.0 if reaction == "sell" else 0.1)
    _hot_cpi(dash, _t(5, hour=14), title="Core CPI m/m")
    _ev(dash, "Unemployment Claims", _t(6, hour=14), "220K", "240K")
    for when in (_t(1, hour=13), _t(2, hour=13), _t(5, hour=14), _t(6, hour=14)):
        _react(bt, when, "sell", -4.0)
    titles = [r["event_title"] for r in _board(dash, bt)["rows"]]
    assert titles == ["Retail Sales m/m", "CPI m/m", "Core CPI m/m", "Unemployment Claims"]


def test_instrument_without_reaction_rows_gives_empty_rows_and_never_crashes(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _react(bt, _t(3), "sell", -4.0)                       # gold only
    assert _board(dash, bt, instrument="US30")["rows"] == []
    assert _board(dash, bt, instrument="NOTASYMBOL")["rows"] == []
    [rel] = _releases(dash, bt, "CPI m/m", instrument="NOTASYMBOL")
    assert rel["lean"] == "mixed" and rel["credit"] == "no_signal" and rel["reaction"] is None


def test_us30_reads_its_own_rows(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _react(bt, _t(3), "sell", -4.0)
    _react(bt, _t(3), "buy", 40.0, typical=10.0, instrument="US30")
    row = _row(_board(dash, bt, instrument="US30"), "CPI m/m")
    assert row["hit"]["k"] == 0 and row["avg_move_pct"] == pytest.approx(-2.0)
    assert _releases(dash, bt, "CPI m/m", instrument="US30")[0]["threshold"] == pytest.approx(10.0)


def test_an_unreadable_row_is_skipped_and_the_rest_still_render(conns):
    dash, bt = conns
    _ev(dash, "CPI m/m", _t(2), "0.3%", "0.4%", when_text="not a time")
    _hot_cpi(dash, _t(3))
    _react(bt, _t(3), "sell", -4.0)
    assert _row(_board(dash, bt), "CPI m/m")["releases"] == 1
    assert len(_releases(dash, bt, "CPI m/m")) == 1


def test_an_unknown_title_has_no_releases(conns):
    dash, bt = conns
    assert rs.build_event_releases(dash, bt, GOLD, "Nope", None, None, None) == {
        "event_title": "Nope", "instrument": GOLD, "releases": []}


def test_service_writes_nothing(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _react(bt, _t(3), "sell", -4.0)
    before = (dash.total_changes, bt.total_changes)
    _board(dash, bt)
    _releases(dash, bt, "CPI m/m")
    assert (dash.total_changes, bt.total_changes) == before


# ---- reactions_available (final fix wave B) -----------------------------------------------------------

def test_reactions_available_is_true_when_any_row_exists_even_if_no_row_matches_the_filter(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    _no_data(bt, _t(3))                                    # a no_data row still means "computed"
    board = _board(dash, bt, impacts=frozenset())
    assert board["rows"] == [] and board["reactions_available"] is True


def test_reactions_available_is_false_without_rows_for_the_instrument_or_version(conns):
    dash, bt = conns
    _hot_cpi(dash, _t(3))
    assert _board(dash, bt)["reactions_available"] is False
    _react(bt, _t(3), "sell", -4.0, instrument="US30")
    bs.record_release_reaction(bt, _t(3), GOLD, "ok", p0=P0, p5=P0 - 4.0, typical_abs_move=1.0, reaction="sell",
                               baseline_quantile=0.5, reaction_multiple=1.0)        # another quantile
    bs.record_release_reaction(bt, _t(3), GOLD, "ok", p0=P0, p5=P0 - 4.0, typical_abs_move=1.0, reaction="sell",
                               baseline_quantile=Q, reaction_multiple=1.5)          # another multiple
    board = _board(dash, bt)
    assert board["reactions_available"] is False and board["rows"] == []
    assert _board(dash, bt, instrument="US30")["reactions_available"] is True
