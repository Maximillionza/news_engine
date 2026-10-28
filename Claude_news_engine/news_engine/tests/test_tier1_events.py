"""
Tests for data_layer/tier1_events.py -- the Tier 1 registry and timing rules (B3 / T2, T7).
Pure module: no DB, no network.
"""
import datetime as dt

import pytest

from data_layer.tier1_events import (
    TIER1_EVENTS, TIER1_FORMULA, TIER1_FORMULA_SOURCE, TIER1_JUDGMENT,
    TIER1_MARKET_IMPLIED, TIER1_MARKET_IMPLIED_CONFIDENCE, TIER1_MARKET_IMPLIED_SOURCE, TIER1_TIERS,
    late_check_reason, tier1_row_tier, tier1_titles,
)

UTC = dt.timezone.utc
RELEASE = dt.datetime(2026, 11, 12, 13, 30, tzinfo=UTC)
CALL_AT = dt.datetime(2026, 11, 2, 6, 0, tzinfo=UTC)


def _at(day: int, hour: int, minute: int = 0) -> dt.datetime:
    return dt.datetime(2026, 11, day, hour, minute, tzinfo=UTC)


def test_tier1_events_has_16_titles_2_formula_14_judgment_0_market_implied():
    assert list(TIER1_EVENTS) == [
        "CPI m/m", "Core CPI m/m",
        "PPI m/m", "Non-Farm Employment Change", "FOMC Meeting Minutes", "FOMC Statement",
        "Federal Funds Rate", "Prelim GDP q/q", "Advance GDP q/q", "Final GDP q/q", "GDP q/q",
        "Core PCE Price Index m/m", "ISM Manufacturing PMI", "ISM Services PMI",
        "Retail Sales m/m", "Core Retail Sales m/m",
    ]
    assert tier1_titles(TIER1_FORMULA) == ["CPI m/m", "Core CPI m/m"]
    assert len(tier1_titles(TIER1_JUDGMENT)) == 14
    assert tier1_titles(TIER1_MARKET_IMPLIED) == []
    assert all(tier in TIER1_TIERS for tier in TIER1_EVENTS.values())


def test_tier1_titles_rejects_an_unknown_tier():
    with pytest.raises(ValueError):
        tier1_titles("astrology")


def test_tier1_row_tier_formula_only_for_the_formula_source():
    assert tier1_row_tier(TIER1_FORMULA_SOURCE) == TIER1_FORMULA
    assert tier1_row_tier("BLS/ISM") == TIER1_JUDGMENT


# Live 2026-10-26 / 2026-09-16 tier1_predictions strings: FedWatch sits in the source of the September rows but only
# in the value's leading citation of the October rows, so the helper must read both (and nothing mid-text).
_URL_ONLY_SOURCE = (
    "https://fxstreet.com/news/us-dollar-index-falls-to-near-10150-amid-fed-rate-pause-odds-easing-safe-haven-"
    "demand-202610260532 ; https://alanlongbon.substack.com/p/the-us-feds-october-meeting-a-pause"
)


@pytest.mark.parametrize("source, value, expected", [
    ("CME FedWatch via CBS News ('Fed rate hike in September is all but guaranteed after CPI report')", None,
     TIER1_MARKET_IMPLIED),
    (_URL_ONLY_SOURCE,
     "CME FedWatch (via FXStreet 2026-10-26 and Longbon 2026-10-22): ~90.6-91% hold at 3.75-4.00%",
     TIER1_MARKET_IMPLIED),
    (_URL_ONLY_SOURCE, "FedWatch: ~91% hold priced, Dec hike ~80-87% priced", TIER1_MARKET_IMPLIED),
    (_URL_ONLY_SOURCE, None, TIER1_JUDGMENT),
    ("BLS/ISM", "PPI hot; FedWatch hike odds rose after it", TIER1_JUDGMENT),     # mid-text mention: still judgment
    (TIER1_FORMULA_SOURCE, "FedWatch: ~91% hold priced", TIER1_FORMULA),          # formula source always wins
    (TIER1_MARKET_IMPLIED_SOURCE, "NFP 70.0K implied median", TIER1_MARKET_IMPLIED),
    (TIER1_MARKET_IMPLIED_SOURCE, None, TIER1_MARKET_IMPLIED),
])
def test_tier1_row_tier_routes_fedwatch_rows_to_market_implied(source, value, expected):
    assert tier1_row_tier(source, value) == expected


def test_market_implied_capture_constants():
    assert TIER1_MARKET_IMPLIED_SOURCE == "Kalshi market-implied"
    assert TIER1_MARKET_IMPLIED_CONFIDENCE == "Likely"      # a market price is not a certainty


def test_late_check_reason_fresh_call_is_none():
    assert late_check_reason(CALL_AT, RELEASE, _at(5, 6), False) is None


def test_late_check_reason_stale_call():
    assert late_check_reason(CALL_AT, RELEASE, _at(9, 6, 6), False) == "stale_call"


def test_late_check_reason_release_within_24h():
    assert late_check_reason(CALL_AT, RELEASE, _at(11, 14), False) == "release_within_24h"


def test_late_check_reason_window_check_already_done_is_none():
    assert late_check_reason(CALL_AT, RELEASE, _at(11, 14), True) is None


def test_late_check_reason_at_or_after_release_is_none():
    assert late_check_reason(CALL_AT, RELEASE, RELEASE, False) is None
    assert late_check_reason(CALL_AT, RELEASE, _at(12, 14), False) is None


def test_late_check_reason_call_logged_inside_the_window_is_none():
    assert late_check_reason(_at(11, 20), RELEASE, _at(12, 6), False) is None


def test_late_check_reason_fresh_late_check_resets_staleness():
    # newest reading is a late check at 11-09 06:06 -> 11-10 06:00 is not stale
    assert late_check_reason(_at(9, 6, 6), RELEASE, _at(10, 6), False) is None


def test_daily_0806_sast_run_fires_the_24h_check_on_the_release_morning_not_the_day_before():
    # Research task cadence: daily 08:06 SAST = 06:06 UTC (owner ruling 2026-10-20, refresh on the release morning).
    release_1230 = dt.datetime(2026, 11, 12, 12, 30, tzinfo=UTC)
    call = _at(9, 6, 6)                                   # fresh call (3 days before), not stale on either run
    day_before = _at(11, 6, 6)                            # ~30.4h out: outside the 24h window
    release_morning = _at(12, 6, 6)                       # ~6.4h out
    assert late_check_reason(call, release_1230, day_before, False) is None
    assert late_check_reason(call, release_1230, release_morning, False) == "release_within_24h"
    assert late_check_reason(call, release_1230, _at(12, 6, 12), False) == "release_within_24h"  # scheduler jitter
