"""
Tests for data_layer/discovery_detector.py.
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer import discovery_detector


def test_detector_series_is_exactly_four_series():
    print("=== discovery_detector: DETECTOR_SERIES is exactly the 4 verified series, in order ===")
    assert discovery_detector.DETECTOR_SERIES == ["DXY", "UST_BOND", "XAUUSD", "US30"]
    print("PASS\n")


def test_compute_daily_move_unknown_series_raises_value_error():
    print("=== discovery_detector: compute_daily_move raises ValueError for a series with no instrument mapping (caller bug, not a data-availability issue) ===")
    try:
        discovery_detector.compute_daily_move("NOT_A_REAL_SERIES", dt.date(2026, 9, 10))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "NOT_A_REAL_SERIES" in str(exc)
    print("PASS\n")


def test_compute_daily_move_returns_a_real_percentage_for_a_real_past_date():
    print("=== discovery_detector: compute_daily_move returns a real, plausible daily move for XAUUSD on a real past trading day ===")
    # 2026-09-10 is a real, already-resolved PPI release day used
    # elsewhere in this project's own real backtest cases (Causation-
    # Matrix Option A) -- a real trading day, not a weekend/holiday.
    move = discovery_detector.compute_daily_move("XAUUSD", dt.date(2026, 9, 10))
    assert move is not None
    assert -20.0 < move < 20.0, f"expected a plausible single-day %% move, got {move}"
    print("PASS\n")


if __name__ == "__main__":
    test_detector_series_is_exactly_four_series()
    test_compute_daily_move_unknown_series_raises_value_error()
    test_compute_daily_move_returns_a_real_percentage_for_a_real_past_date()
    print("All discovery_detector tests passed.")
