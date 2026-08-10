"""
Tests for data_layer/calendar_feed.py's period validation — no network
needed, the invalid-period cases are rejected before any request is made.
Same plain-assert/__main__ style as tests/test_scoring_smoke.py.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.calendar_feed import fetch_calendar


def test_lastweek_rejected_with_informative_error():
    print("=== fetch_calendar: 'lastweek' is rejected with a clear reason, not a generic 404 ===")
    try:
        fetch_calendar("lastweek")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "lastweek" in str(exc)
        assert "thisweek" in str(exc)
    print("PASS\n")


def test_nextweek_rejected_with_informative_error():
    print("=== fetch_calendar: 'nextweek' is rejected with a clear reason, not a generic 404 ===")
    try:
        fetch_calendar("nextweek")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "nextweek" in str(exc)
    print("PASS\n")


def test_arbitrary_invalid_period_rejected():
    print("=== fetch_calendar: any period other than 'thisweek' is rejected ===")
    try:
        fetch_calendar("thismonth")
        assert False, "expected ValueError"
    except ValueError:
        pass
    print("PASS\n")


if __name__ == "__main__":
    test_lastweek_rejected_with_informative_error()
    test_nextweek_rejected_with_informative_error()
    test_arbitrary_invalid_period_rejected()
    print("All calendar_feed tests passed.")
