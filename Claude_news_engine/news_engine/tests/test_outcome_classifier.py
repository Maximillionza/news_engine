"""
Tests for scoring/outcome_classifier.py — data_layer.dukascopy_feed.get_price_at
is mocked, no live network or real Dukascopy calls.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.probability_engine import Direction
from data_layer.dukascopy_feed import PricePoint
import scoring.outcome_classifier as outcome_classifier


def test_clear_upward_move_classifies_bullish():
    print("=== outcome_classifier: a clear upward move (>=0.15%) classifies BULLISH ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=2400.00), PricePoint(price=2404.00)]):
        result = outcome_classifier.classify("XAUUSD", event_time)
        assert result.direction == Direction.BULLISH
        assert result.move_pct > 0.15
        assert "(auto)" in result.note
    print("PASS\n")


def test_clear_downward_move_classifies_bearish():
    print("=== outcome_classifier: a clear downward move classifies BEARISH ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), PricePoint(price=995.00)]):
        result = outcome_classifier.classify("US30", event_time)
        assert result.direction == Direction.BEARISH
        assert result.move_pct < -0.15
    print("PASS\n")


def test_move_exactly_at_threshold_classifies_not_ambiguous():
    print("=== outcome_classifier: a move exactly AT the 0.15% threshold still classifies, not ambiguous ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), PricePoint(price=1001.50)]):
        result = outcome_classifier.classify("XAUUSD", event_time)
        assert result.direction == Direction.BULLISH
        assert abs(result.move_pct - 0.15) < 1e-9
    print("PASS\n")


def test_move_just_under_threshold_is_ambiguous():
    print("=== outcome_classifier: a move just under the threshold is ambiguous (no direction) ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), PricePoint(price=1001.49)]):
        result = outcome_classifier.classify("XAUUSD", event_time)
        assert result.direction is None
        assert result.move_pct is not None
        assert "below" in result.note
    print("PASS\n")


def test_fetch_failure_is_ambiguous_with_no_move_pct():
    print("=== outcome_classifier: a fetch failure (either side) classifies as ambiguous with move_pct=None ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), None]):
        result = outcome_classifier.classify("XAUUSD", event_time)
        assert result.direction is None
        assert result.move_pct is None
        assert "no data available" in result.note
    print("PASS\n")


def test_never_returns_neutral():
    print("=== outcome_classifier: never auto-classifies NEUTRAL — ambiguous is always direction=None, not Direction.NEUTRAL ===")
    event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(outcome_classifier, "get_price_at", side_effect=[PricePoint(price=1000.00), PricePoint(price=1000.00)]):
        result = outcome_classifier.classify("XAUUSD", event_time)  # exactly 0% move
        assert result.direction is None, "a below-threshold move must be ambiguous (needs a human), never a confident NEUTRAL call"
        assert result.direction != Direction.NEUTRAL
    print("PASS\n")


if __name__ == "__main__":
    test_clear_upward_move_classifies_bullish()
    test_clear_downward_move_classifies_bearish()
    test_move_exactly_at_threshold_classifies_not_ambiguous()
    test_move_just_under_threshold_is_ambiguous()
    test_fetch_failure_is_ambiguous_with_no_move_pct()
    test_never_returns_neutral()
    print("All outcome_classifier tests passed.")
