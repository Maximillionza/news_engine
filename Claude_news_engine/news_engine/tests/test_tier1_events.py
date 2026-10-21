"""
Tests for data_layer/tier1_events.py -- the Tier 1 registry and timing rules (B3 / T2, T7).
Pure module: no DB, no network.
"""
import datetime as dt

import pytest

from data_layer.tier1_events import (
    TIER1_EVENTS, TIER1_FORMULA, TIER1_FORMULA_SOURCE, TIER1_JUDGMENT,
    TIER1_MARKET_IMPLIED, TIER1_TIERS, late_check_reason, tier1_row_tier, tier1_titles,
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
