# tests/test_stats_service.py
import datetime as dt
from types import SimpleNamespace

import pytest

from config.settings import EVENT_SURPRISE_DIRECTION
from scoring import backtest_store as bs
from webapp import stats_service as svc
from webapp import store as ws

UTC = dt.timezone.utc


def _t(month, day=14):
    return dt.datetime(2026, month, day, 12, 30, tzinfo=UTC)


@pytest.fixture
def conns():
    return ws.get_connection(":memory:"), bs.get_connection(":memory:")


def _event(dash, title, when, forecast, actual, previous="0.1%", country="USD"):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), forecast, previous, actual, None, when.isoformat(), when.isoformat(), "t", "High", country),
    )
    dash.commit()


def _snap(bt, title, when, value, hours_before=48):
    bs.record_nowcast_snapshot(bt, title, when, value, when - dt.timedelta(hours=hours_before), "cleveland", "live")


def _cpi_history(dash):
    """Three prior CPI m/m prints, each |actual - forecast| = 0.1, so the news scale is 0.1."""
    for m, f, a in [(1, "0.3%", "0.2%"), (2, "0.3%", "0.4%"), (3, "0.3%", "0.4%")]:
        _event(dash, "CPI m/m", _t(m), f, a)


def _print_call(bt, title, when, direction, confidence, scored_at):
    bs.record_print_prediction_if_changed(
        bt, title, when, SimpleNamespace(direction=direction, confidence=confidence, article_count=7), now=scored_at,
    )


def _acc_call(bt, title, when, direction, probability, scored_at):
    bs.record_prediction(bt, title, "XAUUSD", when, probability, direction, 0.5, 7, False, scored_at_utc=scored_at)


# --- plan tests ---------------------------------------------------------------------------------

def test_tier1_hotter_call_against_a_hotter_print_is_right_and_combined_blends(conns):
    dash, bt = conns
    for m, f, a in [(1, "0.3%", "0.3%"), (2, "0.3%", "0.2%"), (3, "0.3%", "0.4%")]:   # history for the scale
        _event(dash, "CPI m/m", _t(m), f, a)
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _snap(bt, "CPI m/m", _t(10), 0.4)
    row = svc.build_rows(dash, bt, event_title="CPI m/m")[-1]
    assert row.status == "scored" and row.tier1_tracked is True
    assert row.tier1.predicted == pytest.approx(0.4) and row.tier1.verdict == "right"
    assert row.tier1.leans == {"XAUUSD": "sell", "US30": "sell"}
    assert row.tier1.kind == "live" and row.nowcast_as_of_utc is not None
    assert row.combined.verdict == "right" and row.combined.note == "news_missing"
    assert row.news is None   # controller ruling 2: no lean means no news call at all


def test_exactly_the_in_line_call_against_a_hotter_print_is_wrong(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _snap(bt, "CPI m/m", _t(10), 0.3)
    assert svc.build_rows(dash, bt)[-1].tier1.verdict == "wrong"


def test_unparseable_numbers_are_listed_but_not_scoreable_and_never_crash(conns):
    dash, bt = conns
    _event(dash, "Weird Event", _t(10), "N/A", "1.2|0.9")
    row = svc.build_rows(dash, bt)[-1]
    assert row.status == "not_scoreable" and row.tier1 is None and row.tier1_tracked is False


def test_future_event_is_pending_with_no_verdict(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(12), "0.3%", None)
    row = svc.build_rows(dash, bt)[-1]
    assert row.status == "pending" and (row.tier1 is None or row.tier1.verdict is None)


def test_events_without_a_tier1_rule_are_not_tracked_and_combined_is_none(conns):
    dash, bt = conns
    _event(dash, "Unemployment Claims", _t(10), "220K", "230K")
    row = svc.build_rows(dash, bt)[-1]
    assert row.status == "scored" and row.tier1_tracked is False
    assert row.tier1 is None and row.combined is None


def test_hand_logged_tier1_direction_is_scored_by_side_when_there_is_no_nowcast(conns):
    dash, bt = conns
    _event(dash, "PPI m/m", _t(10), "0.2%", "0.5%")
    bs.record_tier1_prediction(bt, "PPI m/m", "XAUUSD", _t(10), "hot", "Likely", "BLS", "bearish",
                               logged_at_utc=_t(10) - dt.timedelta(days=3))
    row = svc.build_rows(dash, bt)[-1]
    assert row.tier1_tracked is True and row.tier1.predicted is None
    assert row.tier1.verdict == "right"   # gold bearish = USD up = hotter; actual hotter
    assert row.tier1.note == "hand-logged"


def test_news_call_uses_the_print_call_and_the_median_scale(conns):
    dash, bt = conns
    _cpi_history(dash)
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _snap(bt, "CPI m/m", _t(10), 0.4)
    _print_call(bt, "CPI m/m", _t(10), "higher", 0.5, scored_at=_t(10) - dt.timedelta(days=1))
    last = svc.build_rows(dash, bt, event_title="CPI m/m")[-1]
    assert last.news.predicted == pytest.approx(0.3 + 0.5 * 0.1)     # forecast + lean * scale
    assert last.news.verdict == "wrong"                              # 0.35 is under one 0.1 step above 0.3 = in line; actual 0.4 is hotter
    assert last.combined.note is None                                # news present, so not news_missing


def test_pre_news_period_flag_is_set_only_before_12_aug(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", dt.datetime(2026, 8, 11, 12, 30, tzinfo=UTC), "0.3%", "0.4%")
    _event(dash, "CPI m/m", dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC), "0.3%", "0.4%")
    rows = svc.build_rows(dash, bt, event_title="CPI m/m")
    assert [r.pre_news_period for r in rows] == [True, False]


def test_filters_apply_after_history_and_empty_result_is_an_empty_list(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(9), "0.3%", "0.4%")
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    assert [r.event_time_utc.month for r in svc.build_rows(dash, bt, year=2026, month=10)] == [10]
    assert svc.build_rows(dash, bt, year=2025) == []


def test_scoreboard_suppresses_percentages_below_20_and_shows_them_at_20(conns):
    dash, bt = conns
    for i in range(20):
        when = dt.datetime(2025, 1, 1, 12, 30, tzinfo=UTC) + dt.timedelta(days=30 * i)
        _event(dash, "CPI m/m", when, "0.3%", "0.4%")
        _snap(bt, "CPI m/m", when, 0.4)
    all_rows = svc.build_rows(dash, bt, event_title="CPI m/m")
    board = svc.build_scoreboard(all_rows)["methods"]["tier1"]
    assert board["scored"] == 20 and board["accuracy_shown"] is True and board["accuracy"] == pytest.approx(1.0)
    board19 = svc.build_scoreboard(all_rows[:19])["methods"]["tier1"]
    assert board19["scored"] == 19 and board19["accuracy_shown"] is False and board19["accuracy"] is None
    assert svc.build_scoreboard(all_rows)["min_for_percent"] == 20


def test_chart_has_a_point_per_scored_month_and_gaps_for_no_call(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(9), "0.3%", "0.4%")
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _snap(bt, "CPI m/m", _t(10), 0.4)
    chart = svc.build_chart(svc.build_rows(dash, bt, event_title="CPI m/m"), "tier1")
    assert chart["unit"] == "%" and [p["month"] for p in chart["points"]] == ["2026-09", "2026-10"]
    assert chart["points"][0]["predicted"] is None and chart["points"][0]["verdict"] is None
    assert chart["points"][1]["predicted"] == pytest.approx(0.4) and chart["points"][1]["verdict"] == "right"
    assert svc.build_chart([], "combined")["points"] == []


# --- controller ruling 1: no lookahead in news / hand-logged inputs -----------------------------

def test_print_call_scored_after_the_release_is_ignored(conns):
    dash, bt = conns
    _cpi_history(dash)
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _print_call(bt, "CPI m/m", _t(10), "higher", 1.0, scored_at=_t(10) + dt.timedelta(hours=1))
    row = svc.build_rows(dash, bt, event_title="CPI m/m")[-1]
    assert row.news is None


def test_latest_print_call_at_or_before_the_release_wins_over_a_later_one(conns):
    dash, bt = conns
    _cpi_history(dash)
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _print_call(bt, "CPI m/m", _t(10), "lower", 0.5, scored_at=_t(10) - dt.timedelta(days=1))
    _print_call(bt, "CPI m/m", _t(10), "higher", 1.0, scored_at=_t(10) + dt.timedelta(minutes=5))
    row = svc.build_rows(dash, bt, event_title="CPI m/m")[-1]
    assert row.news.predicted == pytest.approx(0.3 - 0.5 * 0.1)
    assert row.news.verdict == "wrong"


def test_accumulator_call_is_the_fallback_and_one_scored_after_the_release_is_ignored(conns):
    dash, bt = conns
    _cpi_history(dash)
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _acc_call(bt, "CPI m/m", _t(10), "bearish", 0.8, scored_at=_t(10) - dt.timedelta(hours=6))
    _acc_call(bt, "CPI m/m", _t(10), "bullish", 0.95, scored_at=_t(10) + dt.timedelta(hours=1))
    row = svc.build_rows(dash, bt, event_title="CPI m/m")[-1]
    # gold bearish = USD up = hotter CPI; strength |2*0.8 - 1| = 0.6 -> surprise 0.06
    assert row.news.predicted == pytest.approx(0.3 + 0.6 * 0.1)


def test_accumulator_call_only_after_the_release_gives_no_news_call(conns):
    dash, bt = conns
    _cpi_history(dash)
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _acc_call(bt, "CPI m/m", _t(10), "bearish", 0.9, scored_at=_t(10) + dt.timedelta(seconds=1))
    assert svc.build_rows(dash, bt, event_title="CPI m/m")[-1].news is None


def test_hand_logged_tier1_after_the_release_is_ignored(conns):
    dash, bt = conns
    _event(dash, "PPI m/m", _t(10), "0.2%", "0.5%")
    bs.record_tier1_prediction(bt, "PPI m/m", "XAUUSD", _t(10), "hot", "Likely", "BLS", "bearish",
                               logged_at_utc=_t(10) + dt.timedelta(hours=2))
    row = svc.build_rows(dash, bt)[-1]
    assert row.tier1 is None and row.tier1_tracked is False


def test_hand_logged_tier1_uses_the_latest_row_logged_before_the_release(conns):
    dash, bt = conns
    _event(dash, "PPI m/m", _t(10), "0.2%", "0.5%")
    bs.record_tier1_prediction(bt, "PPI m/m", "XAUUSD", _t(10), "hot", "Likely", "BLS", "bearish",
                               logged_at_utc=_t(10) - dt.timedelta(days=2))
    bs.record_tier1_prediction(bt, "PPI m/m", "XAUUSD", _t(10), "cool", "Likely", "BLS", "bullish",
                               logged_at_utc=_t(10) + dt.timedelta(hours=2))
    assert svc.build_rows(dash, bt)[-1].tier1.verdict == "right"


def test_nowcast_snapshot_after_the_release_is_not_scored(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _snap(bt, "CPI m/m", _t(10), 0.4, hours_before=-1)   # as-of one hour AFTER the release
    row = svc.build_rows(dash, bt)[-1]
    assert row.tier1 is None and row.tier1_tracked is True and row.combined is None


# --- controller ruling 4: titles with no surprise map never get a news lean ---------------------

def test_title_without_a_surprise_map_has_no_news_call(conns):
    dash, bt = conns
    title = "Federal Funds Rate"
    assert title not in EVENT_SURPRISE_DIRECTION      # precondition: one of the nine unmapped titles
    for m in (1, 3, 6):
        _event(dash, title, _t(m), "4.25%", "4.00%")
    _event(dash, title, _t(9), "4.25%", "4.00%")
    _acc_call(bt, title, _t(9), "bullish", 0.9, scored_at=_t(9) - dt.timedelta(hours=6))
    row = svc.build_rows(dash, bt, event_title=title)[-1]
    assert row.status == "scored"
    assert row.news is None and row.combined is None


# --- coordinator ruling: USD events only -----------------------------------------------------

def test_non_usd_and_unattributed_rows_are_excluded_from_rows_and_chart(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(8, 26), "0.9%", "1.1%", country=None)     # e.g. an AUD print reusing the title
    _event(dash, "CPI m/m", _t(9, 3), "0.0%", "0.2%", country="CHF")
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    rows = svc.build_rows(dash, bt, event_title="CPI m/m")
    assert [r.event_time_utc for r in rows] == [_t(10)]
    chart = svc.build_chart(rows, "tier1")
    assert [p["event_time_utc"] for p in chart["points"]] == [_t(10).isoformat()]


def test_non_usd_rows_do_not_feed_the_news_scale_history(conns):
    dash, bt = conns
    _cpi_history(dash)                                                    # three USD rows, |surprise| 0.1 each
    for day in (15, 16, 17, 18):                                          # four NULL-country rows, |surprise| 1.0
        _event(dash, "CPI m/m", _t(4, day), "0.3%", "1.3%", country=None)
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _print_call(bt, "CPI m/m", _t(10), "higher", 0.5, scored_at=_t(10) - dt.timedelta(days=1))
    row = svc.build_rows(dash, bt, event_title="CPI m/m")[-1]
    assert row.news.predicted == pytest.approx(0.3 + 0.5 * 0.1)          # median of USD-only history; 1.0 if leaked


def test_non_usd_rows_do_not_count_toward_the_minimum_scale_history(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(1), "0.3%", "0.4%")
    _event(dash, "CPI m/m", _t(2), "0.3%", "0.4%")
    _event(dash, "CPI m/m", _t(3), "0.3%", "0.4%", country=None)          # would be the third prior print
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _print_call(bt, "CPI m/m", _t(10), "higher", 0.5, scored_at=_t(10) - dt.timedelta(days=1))
    assert svc.build_rows(dash, bt, event_title="CPI m/m")[-1].news is None


# --- coordinator ruling: mean miss only within one event title ----------------------------------

def test_scoreboard_mean_miss_is_none_when_calls_span_more_than_one_title(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _snap(bt, "CPI m/m", _t(10), 0.5)
    _event(dash, "Core CPI m/m", _t(10), "0.2%", "0.3%")
    _snap(bt, "Core CPI m/m", _t(10), 0.4)
    mixed = svc.build_scoreboard(svc.build_rows(dash, bt))["methods"]["tier1"]
    assert mixed["scored"] == 2 and mixed["right"] == 2 and mixed["mean_miss"] is None
    single = svc.build_scoreboard(svc.build_rows(dash, bt, event_title="CPI m/m"))["methods"]["tier1"]
    assert single["scored"] == 1 and single["mean_miss"] == pytest.approx(0.1)


# --- fail-open --------------------------------------------------------------------------------

def test_one_failing_row_degrades_to_not_scoreable_and_the_rest_still_render(conns, monkeypatch):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(9), "0.3%", "0.4%")
    _event(dash, "PPI m/m", _t(10), "0.2%", "0.5%")
    real = svc._build_one

    def boom(bt_conn, r, title, when, prior):
        if title == "CPI m/m":
            raise RuntimeError("bad row")
        return real(bt_conn, r, title, when, prior)

    monkeypatch.setattr(svc, "_build_one", boom)
    rows = svc.build_rows(dash, bt)
    assert [(r.event_title, r.status) for r in rows] == [("CPI m/m", "not_scoreable"), ("PPI m/m", "scored")]


def test_chart_rejects_an_unknown_method():
    with pytest.raises(ValueError):
        svc.build_chart([], "magic")


# --- review fix round 1 -----------------------------------------------------------------------

def test_print_call_on_a_title_without_a_surprise_map_gives_no_news_call(conns):
    dash, bt = conns
    title = "Federal Funds Rate"
    assert title not in EVENT_SURPRISE_DIRECTION
    for m in (1, 3, 6):                                                  # enough history for a scale
        _event(dash, title, _t(m), "4.25%", "4.00%")
    _event(dash, title, _t(9), "4.25%", "4.00%")
    _print_call(bt, title, _t(9), "higher", 0.75, scored_at=_t(9) - dt.timedelta(days=1))
    row = svc.build_rows(dash, bt, event_title=title)[-1]
    assert row.status == "scored"
    assert row.news is None
    assert row.combined is None                                          # same as without the print call: no Tier 1


def _raw_insert(bt, table, values):
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    bt.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(values.values()))
    bt.commit()


def test_lookups_match_equivalent_time_formats_not_just_identical_strings(conns):
    dash, bt = conns
    _cpi_history(dash)
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    # Same instants as the release / a day before it, written as 'Z' and with a space separator.
    _raw_insert(bt, "print_predictions", {
        "event_title": "CPI m/m", "event_time_utc": "2026-10-14T12:30:00Z", "predicted_vs_forecast": "higher",
        "confidence": 0.5, "article_count": 7, "scored_at_utc": "2026-10-13 12:30:00+00:00",
    })
    row = svc.build_rows(dash, bt, event_title="CPI m/m")[-1]
    assert row.news.predicted == pytest.approx(0.3 + 0.5 * 0.1)


def test_time_bounds_compare_instants_not_strings_across_offsets(conns):
    dash, bt = conns
    _event(dash, "PPI m/m", _t(10), "0.2%", "0.5%")
    # 14:00+02:00 is 12:00Z, BEFORE the 12:30Z release (a string compare would call it later).
    _raw_insert(bt, "tier1_predictions", {
        "event_title": "PPI m/m", "instrument": "XAUUSD", "event_time_utc": "2026-10-14 12:30:00+00:00",
        "value": "hot", "confidence": "Likely", "source": "BLS", "predicted_direction": "bearish",
        "logged_at_utc": "2026-10-14T14:00:00+02:00",
    })
    # 08:00-05:00 is 13:00Z, AFTER the release (a string compare would call it earlier) -- must be ignored.
    _raw_insert(bt, "tier1_predictions", {
        "event_title": "PPI m/m", "instrument": "XAUUSD", "event_time_utc": "2026-10-14T12:30:00Z",
        "value": "cool", "confidence": "Likely", "source": "BLS", "predicted_direction": "bullish",
        "logged_at_utc": "2026-10-14T08:00:00-05:00",
    })
    _raw_insert(bt, "predictions", {
        "event_title": "PPI m/m", "instrument": "XAUUSD", "event_time_utc": "2026-10-14T12:30:00Z",
        "scored_at_utc": "2026-10-14T08:00:00-05:00", "probability": 0.9, "direction": "bearish",
        "confidence": 0.5, "article_count": 7, "contradiction_flag": 0,
    })
    row = svc.build_rows(dash, bt)[-1]
    assert row.tier1.verdict == "right"        # the 12:00Z bearish call, not the 13:00Z bullish one
    assert row.news is None                    # the only accumulator row is after the release (and no scale)


def test_unit_ignores_rows_whose_forecast_is_not_a_number(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(9), "N/A", "0.4%")
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    assert svc.build_chart(svc.build_rows(dash, bt, event_title="CPI m/m"), "tier1")["unit"] == "%"


def test_chart_label_is_the_month_for_monthly_series(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", _t(9), "0.3%", "0.4%")
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    points = svc.build_chart(svc.build_rows(dash, bt, event_title="CPI m/m"), "tier1")["points"]
    assert [p["label"] for p in points] == ["2026-09", "2026-10"]
    assert [p["month"] for p in points] == ["2026-09", "2026-10"]


def test_chart_label_is_the_date_when_any_month_repeats(conns):
    dash, bt = conns
    for month, day in [(9, 4), (10, 2), (10, 9)]:
        _event(dash, "Unemployment Claims", _t(month, day), "220K", "230K")
    points = svc.build_chart(svc.build_rows(dash, bt, event_title="Unemployment Claims"), "news")["points"]
    assert [p["label"] for p in points] == ["2026-09-04", "2026-10-02", "2026-10-09"]
    assert [p["month"] for p in points] == ["2026-09", "2026-10", "2026-10"]


# --- final review fix wave ------------------------------------------------------------------------

def test_hand_logged_neutral_tier1_is_no_call_and_not_scored(conns):
    # 'neutral' means no call (backtest_store tier1_comparisons convention), never an 'in line' call.
    dash, bt = conns
    _event(dash, "PPI m/m", _t(10), "0.2%", "0.2%")          # actual in line: an in-line call would be 'right'
    bs.record_tier1_prediction(bt, "PPI m/m", "XAUUSD", _t(10), "flat", "Likely", "BLS", "neutral",
                               logged_at_utc=_t(10) - dt.timedelta(days=1))
    row = svc.build_rows(dash, bt)[-1]
    assert row.tier1_tracked is True and row.tier1.note == "hand-logged"
    assert row.tier1.side is None and row.tier1.verdict is None and row.tier1.leans == {}
    board = svc.build_scoreboard([row])["methods"]["tier1"]
    assert board["scored"] == 0 and board["right"] == 0


def _mixed_population(dash, bt):
    """Sep: reconstructed Tier 1, no news. Oct: live Tier 1 + a print call (news present)."""
    _cpi_history(dash)
    _event(dash, "CPI m/m", _t(9), "0.3%", "0.4%")
    bs.record_nowcast_snapshot(bt, "CPI m/m", _t(9), 0.4, _t(9) - dt.timedelta(days=1), "cleveland",
                               "reconstructed", rule_version="v1")
    _event(dash, "CPI m/m", _t(10), "0.3%", "0.4%")
    _snap(bt, "CPI m/m", _t(10), 0.5)
    _print_call(bt, "CPI m/m", _t(10), "higher", 0.5, scored_at=_t(10) - dt.timedelta(days=1))
    return svc.build_rows(dash, bt, event_title="CPI m/m")


def test_combined_call_carries_the_tier1_snapshot_kind(conns):
    rows = _mixed_population(*conns)
    assert [(r.tier1.kind, r.combined.kind) for r in rows[-2:]] == [("reconstructed", "reconstructed"), ("live", "live")]


def test_scoreboard_separates_live_reconstructed_and_with_news_populations(conns):
    board = svc.build_scoreboard(_mixed_population(*conns))["methods"]
    # Tier 1: Sep 0.4 vs 0.3 hotter, right; Oct 0.5 hotter, right.
    assert board["tier1"]["by_kind"] == {"live": {"scored": 1, "right": 1}, "reconstructed": {"scored": 1, "right": 1}}
    # News: Oct only (0.3 + 0.5 x 0.1 = 0.35 is in line; actual hotter -> wrong). Kind None counts as live.
    assert board["news"]["by_kind"] == {"live": {"scored": 1, "right": 0}, "reconstructed": {"scored": 0, "right": 0}}
    # Combined: Sep is Tier 1 only (news_missing), Oct is a real blend 0.7 x 0.2 + 0.3 x 0.05 -> hotter, right.
    assert board["combined"]["by_kind"] == {"live": {"scored": 1, "right": 1}, "reconstructed": {"scored": 1, "right": 1}}
    assert board["combined"]["with_news"] == {"scored": 1, "right": 1}
    assert "with_news" not in board["tier1"] and "with_news" not in board["news"]
    # Existing keys unchanged; the percentage threshold is still on the total.
    assert {k: board["tier1"][k] for k in ("scored", "right", "accuracy", "accuracy_shown")} == {
        "scored": 2, "right": 2, "accuracy": None, "accuracy_shown": False}
