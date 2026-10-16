# tests/test_reaction_rules.py
import datetime as dt

import pytest

from webapp.reaction_rules import (
    DUPLICATE_WITHIN,
    FEW_RELEASES_TAG,
    MIN_PERCENT_RELEASES,
    REACTION_BASELINE_QUANTILE,
    REACTION_MIN_MULTIPLE,
    classify_reaction,
    cluster_credit,
    collapse_same_title_duplicates,
    impact_info,
    rate_display,
    single_outcome,
    wilson_interval,
)


def test_constants_match_the_spec():
    assert REACTION_MIN_MULTIPLE == 1.0
    assert REACTION_BASELINE_QUANTILE == 0.75     # owner ruling 2026-10-16: 75th percentile, not the median
    assert MIN_PERCENT_RELEASES == 20
    assert FEW_RELEASES_TAG == 8


# ---- classify_reaction ----------------------------------------------------

def test_move_equal_to_typical_is_no_reaction():
    assert classify_reaction(2.0, 2.0) == "none"
    assert classify_reaction(-2.0, 2.0) == "none"


def test_float_noise_at_the_threshold_does_not_flip_the_result():
    # 0.3 is typical * 3 only up to float noise (0.1 * 3 == 0.30000000000000004)
    assert classify_reaction(0.3, 0.1, 3.0) == "none"
    assert classify_reaction(-0.3, 0.1, 3.0) == "none"
    # 0.1 * 3 == 0.30000000000000004 is a hair ABOVE 0.3: only the epsilon keeps this "none"
    assert classify_reaction(0.1 * 3, 0.3) == "none"
    assert classify_reaction(-(0.1 * 3), 0.3) == "none"
    # a genuinely larger move still flips
    assert classify_reaction(0.3 + 1e-6, 0.3) == "buy"
    assert classify_reaction(-(0.3 + 1e-6), 0.3) == "sell"


def test_missing_or_zero_baseline_gives_none():
    assert classify_reaction(None, 2.0) is None
    assert classify_reaction(1.0, None) is None
    assert classify_reaction(1.0, 0.0) is None
    assert classify_reaction(1.0, -1.0) is None


def test_move_above_typical_gives_market_direction():
    assert classify_reaction(2.5, 2.0) == "buy"
    assert classify_reaction(-2.5, 2.0) == "sell"


def test_multiple_scales_the_threshold():
    assert classify_reaction(5.0, 2.0, 3.0) == "none"
    assert classify_reaction(6.5, 2.0, 3.0) == "buy"


# ---- single_outcome -------------------------------------------------------

@pytest.mark.parametrize("lean,reaction,expected", [
    ("buy", "buy", "hit"),
    ("sell", "sell", "hit"),
    ("buy", "sell", "miss"),
    ("sell", "buy", "miss"),
    ("buy", "none", "no_reaction"),
    ("sell", "none", "no_reaction"),
    ("buy", None, "no_data"),
    ("sell", None, "no_data"),
    ("mixed", "buy", "no_signal"),
    ("mixed", "none", "no_signal"),
    ("mixed", None, "no_signal"),   # no_signal is checked before no_data
])
def test_single_outcome(lean, reaction, expected):
    assert single_outcome(lean, reaction) == expected


# ---- cluster_credit -------------------------------------------------------

def test_solo_leaned_event_among_no_signal_ones():
    leans = {"a": "buy", "b": "mixed", "c": "mixed"}
    assert cluster_credit(leans, "buy") == {"a": "solo_hit", "b": "no_signal", "c": "no_signal"}
    assert cluster_credit(leans, "sell") == {"a": "solo_miss", "b": "no_signal", "c": "no_signal"}


def test_two_agreeing_events_share_the_credit():
    leans = {"a": "buy", "b": "buy"}
    assert cluster_credit(leans, "buy") == {"a": "shared_hit", "b": "shared_hit"}
    assert cluster_credit(leans, "sell") == {"a": "shared_miss", "b": "shared_miss"}


def test_conflict_marks_matched_and_overruled():
    leans = {"a": "buy", "b": "sell"}
    assert cluster_credit(leans, "buy") == {"a": "matched", "b": "overruled"}
    assert cluster_credit(leans, "sell") == {"a": "overruled", "b": "matched"}


def test_conflict_with_no_signal_event_keeps_it_unscored():
    leans = {"a": "buy", "b": "sell", "c": "mixed"}
    assert cluster_credit(leans, "buy") == {"a": "matched", "b": "overruled", "c": "no_signal"}


def test_no_reaction_gives_every_leaned_event_no_reaction():
    assert cluster_credit({"a": "buy", "b": "sell"}, "none") == {"a": "no_reaction", "b": "no_reaction"}
    assert cluster_credit({"a": "buy", "b": "buy"}, "none") == {"a": "no_reaction", "b": "no_reaction"}
    assert cluster_credit({"a": "buy", "b": "mixed"}, "none") == {"a": "no_reaction", "b": "no_signal"}


def test_all_mixed_cluster_is_all_no_signal():
    leans = {"a": "mixed", "b": "mixed"}
    for reaction in ("buy", "sell", "none", None):
        assert cluster_credit(leans, reaction) == {"a": "no_signal", "b": "no_signal"}


def test_missing_reaction_gives_leaned_events_no_data():
    leans = {"a": "buy", "b": "sell", "c": "mixed"}
    assert cluster_credit(leans, None) == {"a": "no_data", "b": "no_data", "c": "no_signal"}


def test_single_event_cluster_is_solo():
    assert cluster_credit({"a": "sell"}, "sell") == {"a": "solo_hit"}
    assert cluster_credit({"a": "sell"}, "buy") == {"a": "solo_miss"}


def test_empty_cluster_returns_empty_dict():
    assert cluster_credit({}, "buy") == {}


# ---- wilson_interval / rate_display ---------------------------------------

def test_wilson_interval_known_value():
    lo, hi = wilson_interval(7, 10)
    assert lo == pytest.approx(0.397, abs=0.001)
    assert hi == pytest.approx(0.892, abs=0.001)


def test_wilson_interval_is_rounded_to_four_decimals():
    lo, hi = wilson_interval(7, 10)
    assert lo == round(lo, 4) and hi == round(hi, 4)


def test_wilson_interval_empty_sample_is_none():
    assert wilson_interval(0, 0) is None


def test_wilson_interval_edges_stay_within_zero_and_one():
    lo, hi = wilson_interval(0, 5)
    assert lo == 0.0 and 0.0 < hi < 1.0
    lo, hi = wilson_interval(5, 5)
    assert hi == 1.0 and 0.0 < lo < 1.0


@pytest.mark.parametrize("k,n", [(11, 10), (-1, 10)])
def test_wilson_interval_rejects_impossible_counts(k, n):
    with pytest.raises(ValueError):
        wilson_interval(k, n)


def test_rate_display_hides_percent_below_20_and_shows_at_20():
    below = rate_display(10, 19)
    at = rate_display(10, 20)
    assert below["percent"] is None
    assert at["percent"] == 50.0
    assert below["k"] == 10 and below["n"] == 19


def test_rate_display_percent_is_rounded_to_one_decimal():
    assert rate_display(1, 30)["percent"] == 3.3


def test_rate_display_few_flag_flips_at_8():
    assert rate_display(3, 7)["few"] is True
    assert rate_display(3, 8)["few"] is False


def test_rate_display_interval_is_a_list_or_none():
    shown = rate_display(7, 10)
    assert isinstance(shown["interval"], list) and len(shown["interval"]) == 2
    assert shown["interval"][0] == pytest.approx(0.397, abs=0.001)
    empty = rate_display(0, 0)
    assert empty == {"k": 0, "n": 0, "percent": None, "interval": None, "few": True}


# ---- impact_info ----------------------------------------------------------

def test_own_tag_is_used_as_is():
    assert impact_info("High", {"Low": 9}) == {"bucket": "High", "effective": "High", "inferred": False}


def test_missing_tag_is_inferred_from_most_common_title_tag():
    got = impact_info(None, {"High": 5, "Medium": 3})
    assert got == {"bucket": "Unrated", "effective": "High", "inferred": True}


def test_tie_prefers_high_over_medium_over_low():
    assert impact_info(None, {"High": 5, "Medium": 5})["effective"] == "High"
    assert impact_info(None, {"Medium": 4, "Low": 4})["effective"] == "Medium"
    assert impact_info(None, {"High": 2, "Medium": 2, "Low": 2})["effective"] == "High"


def test_missing_tag_and_no_title_tags_is_unrated():
    expected = {"bucket": "Unrated", "effective": "Unrated", "inferred": True}
    assert impact_info(None, {}) == expected
    assert impact_info(None, {"High": 0, "Medium": 0}) == expected


# ---- collapse_same_title_duplicates (moved from scripts/compute_release_reactions.py) ----

def _m(hour: int, minute: int) -> dt.datetime:
    return dt.datetime(2026, 3, 3, hour, minute, tzinfo=dt.timezone.utc)


def test_duplicate_window_is_3_minutes():
    assert DUPLICATE_WITHIN == dt.timedelta(minutes=3)


def test_collapse_is_anchored_on_the_earliest_row_of_a_run():
    events = [("A", _m(12, 0)), ("A", _m(12, 2)), ("A", _m(12, 4)), ("A", _m(12, 3))]
    # 12:02 and 12:03 are within 3 minutes of 12:00; 12:04 is 4 minutes after the kept 12:00 row.
    assert collapse_same_title_duplicates(events) == [("A", _m(12, 0)), ("A", _m(12, 4))]


def test_an_adp_style_chain_is_one_release_at_the_earliest_minute():
    events = [("ADP Weekly Employment Change", _m(12, minute)) for minute in (16, 14, 15)]
    assert collapse_same_title_duplicates(events) == [("ADP Weekly Employment Change", _m(12, 14))]


def test_collapse_keeps_other_titles_and_a_9_minute_pair():
    events = [("A", _m(12, 14)), ("B", _m(12, 15)), ("C", _m(14, 1)), ("C", _m(14, 10)),
              ("D", _m(17, 58)), ("D", _m(18, 0))]
    assert collapse_same_title_duplicates(events) == [
        ("A", _m(12, 14)), ("B", _m(12, 15)), ("C", _m(14, 1)), ("C", _m(14, 10)), ("D", _m(17, 58))]


def test_collapse_honours_a_custom_window_and_empty_input():
    events = [("A", _m(12, 0)), ("A", _m(12, 2))]
    assert collapse_same_title_duplicates(events, within=dt.timedelta(minutes=1)) == events
    assert collapse_same_title_duplicates([]) == []
