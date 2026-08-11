"""Tests for webapp/trend.py — plain-Python arithmetic over event_history rows, no I/O."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.store import EventHistoryRow
from webapp.trend import summarize_trend


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


if __name__ == "__main__":
    test_not_enough_history_with_zero_rows()
    test_not_enough_history_with_one_confirmed_row()
    test_not_enough_history_when_all_rows_still_pending()
    test_consecutive_streak_trending_higher()
    test_no_streak_reports_beat_miss_tally()
    test_mixed_no_clear_majority()
    test_in_line_rows_excluded_from_beat_miss_tally()
    print("All webapp_trend tests passed.")
