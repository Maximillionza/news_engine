"""Tests for webapp/trend.py — plain-Python arithmetic over event_history rows, no I/O."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.store import EventHistoryRow
from webapp.trend import summarize_trend, compute_trend_signal


def _row(month, surprise):
    return EventHistoryRow(
        event_title="CPI m/m", event_time_utc=f"2026-{month:02d}-12T12:30:00+00:00",
        forecast="0.3%", previous="0.3%", actual="0.4%", surprise_direction=surprise,
    )


def test_not_enough_history_with_zero_rows():
    print("=== summarize_trend: zero rows returns 'not enough history' ===")
    assert summarize_trend([]) == "Not enough history yet"
    print("PASS\n")


def test_not_enough_history_with_one_confirmed_row():
    print("=== summarize_trend: a single confirmed row is still not enough for a trend ===")
    assert summarize_trend([_row(8, "higher")]) == "Not enough history yet"
    print("PASS\n")


def test_not_enough_history_when_all_rows_still_pending():
    print("=== summarize_trend: rows with surprise_direction=None (still pending) don't count toward history ===")
    rows = [_row(8, None), _row(7, None)]
    assert summarize_trend(rows) == "Not enough history yet"
    print("PASS\n")


def test_consecutive_streak_trending_higher():
    print("=== summarize_trend: 2+ consecutive same-direction rows (most recent first) reports a trending streak ===")
    rows = [_row(8, "higher"), _row(7, "higher"), _row(6, "lower")]
    assert summarize_trend(rows) == "Trending higher for 2 consecutive releases"
    print("PASS\n")


def test_no_streak_reports_beat_miss_tally():
    print("=== summarize_trend: no consecutive streak falls back to a beat/miss tally over the window ===")
    rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "higher")]
    assert summarize_trend(rows) == "Beat forecast 3 of last 4"
    print("PASS\n")


def test_mixed_no_clear_majority():
    print("=== summarize_trend: an even split reports 'mixed', not a fabricated lean ===")
    rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "lower")]
    assert summarize_trend(rows) == "Mixed — no clean streak over the last 4 prints"
    print("PASS\n")


def test_in_line_rows_excluded_from_beat_miss_tally():
    print("=== summarize_trend: 'in_line' rows count toward the window but not toward beat/miss ===")
    rows = [_row(8, "higher"), _row(7, "in_line"), _row(6, "higher")]
    assert summarize_trend(rows) == "Beat forecast 2 of last 2"
    print("PASS\n")


def test_compute_trend_signal_streak_direction_and_strength():
    print("=== compute_trend_signal: a 3-length streak maps to direction='higher', strength=3/5=0.6 ===")
    rows = [_row(8, "higher"), _row(7, "higher"), _row(6, "higher"), _row(5, "lower")]
    signal = compute_trend_signal(rows)
    assert signal is not None
    assert signal.direction == "higher"
    assert abs(signal.strength - 0.6) < 1e-9
    print("PASS\n")


def test_compute_trend_signal_streak_strength_caps_at_one():
    print("=== compute_trend_signal: a streak of 5+ caps strength at 1.0, does not exceed it ===")
    rows = [_row(m, "higher") for m in range(12, 4, -1)]  # 8 consecutive 'higher'
    signal = compute_trend_signal(rows)
    assert signal.direction == "higher"
    assert signal.strength == 1.0
    print("PASS\n")


def test_compute_trend_signal_tally_majority_strength():
    print("=== compute_trend_signal: a 3-of-4 tally (no streak) maps strength=(3/4-0.5)*2=0.5 ===")
    rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "higher")]
    signal = compute_trend_signal(rows)
    assert signal is not None
    assert signal.direction == "higher"
    assert abs(signal.strength - 0.5) < 1e-9
    print("PASS\n")


def test_compute_trend_signal_mixed_returns_none():
    print("=== compute_trend_signal: an exact tie (mixed, no majority) returns None ===")
    rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "lower")]
    signal = compute_trend_signal(rows)
    assert signal is None
    print("PASS\n")


def test_compute_trend_signal_all_in_line_returns_none():
    print("=== compute_trend_signal: all in_line rows (no directional lean at all) returns None ===")
    rows = [_row(8, "in_line"), _row(7, "in_line")]
    signal = compute_trend_signal(rows)
    assert signal is None
    print("PASS\n")


def test_compute_trend_signal_single_row_saturates_tally_at_one():
    print("=== compute_trend_signal: a single confirmed row can never reach MIN_STREAK_LENGTH, so it lands in the tally branch at strength=1.0 ===")
    rows = [_row(8, "higher")]
    signal = compute_trend_signal(rows)
    assert signal is not None
    assert signal.direction == "higher"
    assert signal.strength == 1.0
    print("PASS\n")


def test_compute_trend_signal_in_line_lead_then_unanimous_still_saturates():
    print("=== compute_trend_signal: an in_line row breaks the streak check without affecting the tally, so a short unanimous run behind it still saturates at 1.0 via the tally branch ===")
    rows = [_row(8, "in_line"), _row(7, "higher"), _row(6, "higher")]
    signal = compute_trend_signal(rows)
    assert signal is not None
    assert signal.direction == "higher"
    assert signal.strength == 1.0
    print("PASS\n")


def test_summarize_trend_and_compute_trend_signal_agree_on_no_signal_cases():
    print("=== parity: summarize_trend's 'Mixed'/'Not enough history' cases correspond to compute_trend_signal returning None ===")
    mixed_rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "lower")]
    assert summarize_trend(mixed_rows).startswith("Mixed")
    assert compute_trend_signal(mixed_rows) is None

    streak_rows = [_row(8, "higher"), _row(7, "higher")]
    assert summarize_trend(streak_rows).startswith("Trending")
    assert compute_trend_signal(streak_rows) is not None
    print("PASS\n")


if __name__ == "__main__":
    test_not_enough_history_with_zero_rows()
    test_not_enough_history_with_one_confirmed_row()
    test_not_enough_history_when_all_rows_still_pending()
    test_consecutive_streak_trending_higher()
    test_no_streak_reports_beat_miss_tally()
    test_mixed_no_clear_majority()
    test_in_line_rows_excluded_from_beat_miss_tally()
    test_compute_trend_signal_streak_direction_and_strength()
    test_compute_trend_signal_streak_strength_caps_at_one()
    test_compute_trend_signal_tally_majority_strength()
    test_compute_trend_signal_mixed_returns_none()
    test_compute_trend_signal_all_in_line_returns_none()
    test_compute_trend_signal_single_row_saturates_tally_at_one()
    test_compute_trend_signal_in_line_lead_then_unanimous_still_saturates()
    test_summarize_trend_and_compute_trend_signal_agree_on_no_signal_cases()
    print("All webapp_trend tests passed.")
