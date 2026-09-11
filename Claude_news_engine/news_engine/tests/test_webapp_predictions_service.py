"""Tests for webapp/predictions_service.py's compute_tier1_sentiment_conflict() — the shared Tier1-vs-sentiment comparison used by both /api/predictions (Dashboard) and webapp/history.py (History tab)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.predictions_service import compute_tier1_sentiment_conflict


def test_opposing_directional_calls_flagged_as_conflict():
    print("=== compute_tier1_sentiment_conflict: bullish vs bearish is a real conflict ===")
    result = compute_tier1_sentiment_conflict("bearish", "bullish")
    assert result == {"sentiment_direction": "bearish", "tier1_direction": "bullish"}
    print("PASS\n")


def test_agreeing_directional_calls_are_not_a_conflict():
    print("=== compute_tier1_sentiment_conflict: agreement is never flagged ===")
    assert compute_tier1_sentiment_conflict("bullish", "bullish") is None
    print("PASS\n")


def test_neutral_or_missing_side_is_never_a_conflict():
    print("=== compute_tier1_sentiment_conflict: 'neutral' or None on either side is never a conflict ===")
    assert compute_tier1_sentiment_conflict("bullish", "neutral") is None
    assert compute_tier1_sentiment_conflict(None, "bullish") is None
    assert compute_tier1_sentiment_conflict("bearish", None) is None
    assert compute_tier1_sentiment_conflict(None, None) is None
    print("PASS\n")


if __name__ == "__main__":
    test_opposing_directional_calls_flagged_as_conflict()
    test_agreeing_directional_calls_are_not_a_conflict()
    test_neutral_or_missing_side_is_never_a_conflict()
    print("All webapp_predictions_service tests passed.")
