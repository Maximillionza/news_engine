"""
Tests for webapp.scoring_service — synthetic, no network needed.
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from scoring.probability_engine import Direction
from webapp.symbols import classify_symbol
from webapp.scoring_service import score_event_for_symbol


def test_fx_cross_not_applicable():
    print("=== fx_cross symbol is not applicable to a USD event ===")
    event = EconomicEvent(
        title="Non-Farm Employment Change", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
        forecast="75K", actual="44K",
    )
    symbol_class = classify_symbol("GBPAUD")
    result = score_event_for_symbol(event, symbol_class)
    assert result.applicable is False
    assert result.probability is None
    print("PASS\n")


def test_pending_event_has_no_score_yet():
    print("=== event with no actual value yet reports pending, not a fabricated score ===")
    event = EconomicEvent(
        title="Non-Farm Employment Change", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
        forecast="75K", actual=None,
    )
    symbol_class = classify_symbol("XAUUSD")
    result = score_event_for_symbol(event, symbol_class)
    assert result.applicable is True
    assert result.pending is True
    assert result.probability is None
    print("PASS\n")


def test_adp_miss_flips_gold_bullish():
    print("=== real ADP miss (75K forecast, 44K actual) scores gold BULLISH via inverse relationship ===")
    # Same real numbers used in tests/test_scoring_smoke.py's
    # test_precursor_leading_indicator — confirms this independent,
    # article-free path agrees with the precursor-contribution path,
    # since both are built on the same EconomicEvent.usd_surprise_score().
    event = EconomicEvent(
        title="ADP Non-Farm Employment Change", country="USD", impact="Medium",
        event_time_utc=dt.datetime(2026, 8, 5, 13, 0, tzinfo=UTC_TZ),
        forecast="75K", actual="44K",
    )
    symbol_class = classify_symbol("XAUUSD")
    result = score_event_for_symbol(event, symbol_class)
    assert result.applicable is True
    assert result.pending is False
    assert result.direction == Direction.BULLISH
    print(f"  probability={result.probability:.0%} raw_score={result.raw_score:+.4f}")
    print("PASS\n")


def test_adp_miss_flips_usdjpy_bearish():
    print("=== same ADP miss scores USDJPY BEARISH via direct relationship (USD weak -> USDJPY falls) ===")
    event = EconomicEvent(
        title="ADP Non-Farm Employment Change", country="USD", impact="Medium",
        event_time_utc=dt.datetime(2026, 8, 5, 13, 0, tzinfo=UTC_TZ),
        forecast="75K", actual="44K",
    )
    symbol_class = classify_symbol("USDJPY")
    result = score_event_for_symbol(event, symbol_class)
    assert result.direction == Direction.BEARISH
    print("PASS\n")


if __name__ == "__main__":
    test_fx_cross_not_applicable()
    test_pending_event_has_no_score_yet()
    test_adp_miss_flips_gold_bullish()
    test_adp_miss_flips_usdjpy_bearish()
    print("All scoring_service tests passed.")
