import pytest

from webapp.stats_methods import (
    NEWS_CALL_MIN_LEAN, NEWS_WEIGHT, TIER1_WEIGHT, combine, market_lean, news_lean, news_scale, news_side,
    news_surprise, tier1_surprise,
)


def test_weights_are_the_declared_70_30():
    assert (TIER1_WEIGHT, NEWS_WEIGHT) == (0.70, 0.30)


def test_news_scale_is_the_median_of_prior_absolute_surprises_and_needs_three():
    assert news_scale([0.1, 0.3, 0.2]) == pytest.approx(0.2)
    assert news_scale([0.1, 0.3]) is None
    assert news_scale([]) is None


def test_tier1_and_news_surprise():
    assert tier1_surprise(0.4, 0.3) == pytest.approx(0.1)
    assert tier1_surprise(None, 0.3) is None
    assert news_surprise(0.5, 0.2) == pytest.approx(0.1)
    assert news_surprise(None, 0.2) is None and news_surprise(0.5, None) is None


def test_combine_blends_70_30():
    result = combine(0.10, 0.20)
    assert result.surprise == pytest.approx(0.7 * 0.10 + 0.3 * 0.20)
    assert result.news_missing is False


def test_combine_falls_back_to_tier1_when_news_is_missing_and_is_none_without_tier1():
    result = combine(0.10, None)
    assert result.surprise == pytest.approx(0.10) and result.news_missing is True
    assert combine(None, 0.2) is None and combine(None, None) is None


def test_news_lean_prefers_a_print_call_that_takes_a_side():
    assert news_lean("CPI m/m", "higher", 0.75, None, None) == pytest.approx(0.75)
    assert news_lean("CPI m/m", "lower", 0.5, "bearish", 0.3) == pytest.approx(-0.5)


def test_news_lean_falls_back_to_the_xauusd_accumulator_when_print_is_in_line_or_absent():
    # CPI is higher_bullish (hot print = USD up). Gold bearish = USD up = hotter print.
    assert news_lean("CPI m/m", "in_line", 0.5, "bearish", 0.32) == pytest.approx(abs(2 * 0.32 - 1))
    assert news_lean("CPI m/m", None, None, "bullish", 0.7) == pytest.approx(-abs(2 * 0.7 - 1))


def test_news_lean_is_none_with_no_usable_signal_and_zero_for_a_neutral_accumulator():
    assert news_lean("CPI m/m", None, None, None, None) is None
    assert news_lean("CPI m/m", "in_line", 0.5, "neutral", 0.5) is None


def test_market_lean_follows_usd_direction_and_symbol_relationship():
    # Hotter CPI -> USD bullish -> gold (inverse) sell, US30 (risk sentiment) sell.
    assert market_lean("CPI m/m", 1, "XAUUSD") == "sell"
    assert market_lean("CPI m/m", 1, "US30") == "sell"
    assert market_lean("CPI m/m", -1, "XAUUSD") == "buy"
    # Unemployment Rate is higher_bearish: a higher print is USD bearish -> gold buy.
    assert market_lean("Unemployment Rate", 1, "XAUUSD") == "buy"
    assert market_lean("CPI m/m", 0, "XAUUSD") == "mixed"
    assert market_lean("FOMC Statement", 1, "XAUUSD") == "mixed"      # no surprise-direction entry
    assert market_lean("CPI m/m", 1, "NOT_A_SYMBOL_123") == "mixed"   # unrecognized symbol never raises


def test_news_lean_of_exactly_zero_is_no_call_not_zero():
    # Accumulator p == 0.5 gives strength |2p - 1| = 0: no lean, so no call (not 0.0 / -0.0).
    assert news_lean("CPI m/m", None, None, "bearish", 0.5) is None
    assert news_lean("CPI m/m", None, None, "bullish", 0.5) is None
    # A print call that takes a side with confidence 0 carries no lean either.
    assert news_lean("CPI m/m", "higher", 0.0, None, None) is None
    assert news_lean("CPI m/m", "lower", 0.0, None, None) is None


# --- B9 ST1: pre-registered News side ------------------------------------------------------------

def test_news_side_pre_registered_threshold():
    assert NEWS_CALL_MIN_LEAN == 0.2
    assert news_side(0.2) == 1 and news_side(-0.2) == -1
    assert news_side(abs(2 * 0.6 - 1)) == 1              # 0.19999999999999996: float noise, still a call
    assert news_side(0.1999) is None and news_side(-0.19) is None
    assert news_side(0.5) == 1 and news_side(-1.0) == -1
    assert news_side(None) is None
    assert all(news_side(i / 100) != 0 for i in range(-100, 101))     # never 'in line'


def test_market_lean_override_and_default_unchanged():
    # B12: Federal Funds Rate has no EVENT_SURPRISE_DIRECTION entry, so the default stays "mixed"; the Kalshi
    # phase passes its own higher = USD-bullish sign.
    assert market_lean("Federal Funds Rate", 1, "XAUUSD") == "mixed"
    assert market_lean("Federal Funds Rate", 1, "XAUUSD", surprise_direction="higher_bullish") == "sell"
    assert market_lean("Federal Funds Rate", -1, "USDJPY", surprise_direction="higher_bullish") == "sell"
    assert market_lean("Federal Funds Rate", 0, "XAUUSD", surprise_direction="higher_bullish") == "mixed"
    # The override replaces the shared map, it does not merge with it.
    assert market_lean("CPI m/m", 1, "XAUUSD", surprise_direction="higher_bearish") == "buy"
    assert market_lean("CPI m/m", 1, "XAUUSD") == "sell"
