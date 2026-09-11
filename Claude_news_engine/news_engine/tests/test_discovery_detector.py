"""
Tests for data_layer/discovery_detector.py.
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer import discovery_detector
from unittest.mock import patch


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


def test_rolling_baseline_computes_mean_and_stdev_from_prior_days_only():
    print("=== discovery_detector: rolling_baseline computes real mean/stdev from the window_days BEFORE as_of_date, never including as_of_date itself ===")
    as_of = dt.date(2026, 9, 10)
    # 3 fabricated daily moves for a 3-day window -- fabricated ONLY
    # here, to test pure math in isolation; compute_daily_move itself
    # (Task 1) is never faked on the live path.
    fake_moves = {
        dt.date(2026, 9, 7): 1.0,
        dt.date(2026, 9, 8): 2.0,
        dt.date(2026, 9, 9): 3.0,
    }

    def fake_compute(series, date):
        return fake_moves.get(date)

    with patch.object(discovery_detector, "compute_daily_move", side_effect=fake_compute):
        result = discovery_detector.rolling_baseline("XAUUSD", as_of, window_days=3)
    assert result is not None
    mean, stdev = result
    assert abs(mean - 2.0) < 1e-9
    assert stdev > 0
    print("PASS\n")


def test_rolling_baseline_returns_none_with_fewer_than_window_days_of_real_data():
    print("=== discovery_detector: rolling_baseline returns None (never a fabricated partial baseline) when fewer than window_days real moves are available ===")
    as_of = dt.date(2026, 9, 10)

    def fake_compute(series, date):
        return 1.0 if date == dt.date(2026, 9, 9) else None  # only 1 of 3 days has real data

    with patch.object(discovery_detector, "compute_daily_move", side_effect=fake_compute):
        result = discovery_detector.rolling_baseline("XAUUSD", as_of, window_days=3)
    assert result is None
    print("PASS\n")


if __name__ == "__main__":
    test_detector_series_is_exactly_four_series()
    test_compute_daily_move_unknown_series_raises_value_error()
    test_compute_daily_move_returns_a_real_percentage_for_a_real_past_date()
    test_rolling_baseline_computes_mean_and_stdev_from_prior_days_only()
    test_rolling_baseline_returns_none_with_fewer_than_window_days_of_real_data()
    print("All discovery_detector tests passed.")
