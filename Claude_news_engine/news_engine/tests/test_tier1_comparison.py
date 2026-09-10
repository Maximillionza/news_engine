"""
Tests for scoring/tier1_comparison.py — uses a temp SQLite file, no network needed.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import (
    get_connection, record_prediction, record_tier1_prediction,
    get_tier1_comparison_for_occurrence,
)
from scoring.tier1_comparison import compute_and_record_tier1_comparison
from scoring.probability_engine import Direction


def test_compute_and_record_builds_and_persists_a_real_comparison():
    print("=== tier1_comparison: a real sentiment prediction + a real Tier 1 prediction + a real outcome produces a persisted comparison ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)

        record_prediction(
            conn, "PPI m/m", "XAUUSD", event_time,
            scored_at_utc=dt.datetime(2026, 9, 10, 6, 10, tzinfo=dt.timezone.utc),
            probability=0.44, direction="bearish", confidence=0.33,
            article_count=142, contradiction_flag=False,
        )
        record_tier1_prediction(
            conn, "PPI m/m", "XAUUSD", event_time,
            value="muted, non-reaccelerating", confidence="Certain",
            source="BLS/ISM", predicted_direction="bullish",
        )

        row_id = compute_and_record_tier1_comparison(
            conn, "PPI m/m", "XAUUSD", event_time,
            actual_direction=Direction.BEARISH, actual_move_note="Dukascopy: -0.54% in 30min (auto)",
        )
        assert row_id is not None

        comparison = get_tier1_comparison_for_occurrence(conn, "PPI m/m", "XAUUSD", event_time)
        assert comparison.sentiment_direction == "bearish"
        assert comparison.sentiment_correct is True
        assert comparison.tier1_direction == "bullish"
        assert comparison.tier1_correct is False
        conn.close()
    print("PASS\n")


def test_compute_and_record_returns_none_without_a_logged_tier1_prediction():
    print("=== tier1_comparison: no Tier 1 prediction was ever logged (the overwhelmingly common case) -> None, nothing persisted, no crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)

        record_prediction(
            conn, "Unemployment Claims", "XAUUSD", event_time,
            scored_at_utc=dt.datetime(2026, 9, 10, 6, 10, tzinfo=dt.timezone.utc),
            probability=0.45, direction="bearish", confidence=0.35,
            article_count=142, contradiction_flag=False,
        )

        row_id = compute_and_record_tier1_comparison(
            conn, "Unemployment Claims", "XAUUSD", event_time,
            actual_direction=Direction.BEARISH, actual_move_note="Dukascopy: -0.54% in 30min (auto)",
        )
        assert row_id is None
        assert get_tier1_comparison_for_occurrence(conn, "Unemployment Claims", "XAUUSD", event_time) is None
        conn.close()
    print("PASS\n")


def test_compute_and_record_returns_none_without_a_real_sentiment_prediction():
    print("=== tier1_comparison: a Tier 1 call was logged but the accumulator never scored this occurrence -> None, not a fabricated comparison ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)

        record_tier1_prediction(
            conn, "PPI m/m", "XAUUSD", event_time,
            value="muted, non-reaccelerating", confidence="Certain",
            source="BLS/ISM", predicted_direction="bullish",
        )

        row_id = compute_and_record_tier1_comparison(
            conn, "PPI m/m", "XAUUSD", event_time,
            actual_direction=Direction.BEARISH, actual_move_note="Dukascopy: -0.54% in 30min (auto)",
        )
        assert row_id is None
        conn.close()
    print("PASS\n")


def test_compute_and_record_handles_a_no_call_tier1_prediction():
    print("=== tier1_comparison: Tier 1 logged NEUTRAL (no confident call, e.g. the Sep 2026 CPI case) -> tier1_correct is None, not True/False ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 11, 12, 30, tzinfo=dt.timezone.utc)

        record_prediction(
            conn, "CPI m/m", "XAUUSD", event_time,
            scored_at_utc=dt.datetime(2026, 9, 11, 6, 0, tzinfo=dt.timezone.utc),
            probability=0.5, direction="bearish", confidence=0.3,
            article_count=100, contradiction_flag=False,
        )
        record_tier1_prediction(
            conn, "CPI m/m", "XAUUSD", event_time,
            value="NO CONFIDENT DIRECTIONAL CALL", confidence="Guessing",
            source="Cleveland Fed nowcast", predicted_direction="neutral",
        )

        compute_and_record_tier1_comparison(
            conn, "CPI m/m", "XAUUSD", event_time,
            actual_direction=Direction.BEARISH, actual_move_note="Dukascopy: -0.30% in 30min (auto)",
        )
        comparison = get_tier1_comparison_for_occurrence(conn, "CPI m/m", "XAUUSD", event_time)
        assert comparison.tier1_correct is None
        assert comparison.sentiment_correct is True
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_compute_and_record_builds_and_persists_a_real_comparison()
    test_compute_and_record_returns_none_without_a_logged_tier1_prediction()
    test_compute_and_record_returns_none_without_a_real_sentiment_prediction()
    test_compute_and_record_handles_a_no_call_tier1_prediction()
    print("All tests passed.")
