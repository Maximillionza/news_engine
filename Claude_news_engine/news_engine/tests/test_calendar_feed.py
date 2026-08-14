"""
Tests for data_layer/calendar_feed.py's period validation — no network
needed, the invalid-period cases are rejected before any request is made.
Same plain-assert/__main__ style as tests/test_scoring_smoke.py.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime as dt

from data_layer.calendar_feed import (
    EconomicEvent,
    classify_surprise,
    fetch_calendar,
    filter_relevant_events,
)
from config.settings import UTC_TZ


def _fake_event(title="CPI m/m", impact="High"):
    """Helper for creating fake EconomicEvent with customizable title/impact."""
    return EconomicEvent(
        title=title, country="USD", impact=impact,
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.2%", actual=None,
    )


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


def test_classify_surprise_higher_when_actual_above_forecast():
    print("=== classify_surprise: actual clearly above forecast returns 'higher' ===")
    event = EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", actual="0.5%",
    )
    assert classify_surprise(event) == "higher"
    print("PASS\n")


def test_classify_surprise_lower_when_actual_below_forecast():
    print("=== classify_surprise: actual clearly below forecast returns 'lower' ===")
    event = EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.5%", actual="0.2%",
    )
    assert classify_surprise(event) == "lower"
    print("PASS\n")


def test_classify_surprise_in_line_within_tolerance():
    print("=== classify_surprise: a tiny delta within EVENT_HISTORY_IN_LINE_TOLERANCE returns 'in_line' ===")
    event = EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.40%", actual="0.41%",  # 2.5% relative delta, well under the 5% tolerance
    )
    assert classify_surprise(event) == "in_line"
    print("PASS\n")


def test_classify_surprise_none_when_title_not_tracked():
    print("=== classify_surprise: an event title outside EVENT_SURPRISE_DIRECTION returns None, never guessed ===")
    event = EconomicEvent(
        title="Some Untracked Indicator", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", actual="0.5%",
    )
    assert classify_surprise(event) is None
    print("PASS\n")


def test_classify_surprise_none_when_forecast_or_actual_missing():
    print("=== classify_surprise: missing forecast or actual returns None, not a fabricated guess ===")
    event = EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", actual=None,
    )
    assert classify_surprise(event) is None
    print("PASS\n")


def test_classify_surprise_is_literal_not_bullish_bearish():
    print("=== classify_surprise: 'higher' means actual > forecast literally, independent of USD-bullish/bearish direction ===")
    # Unemployment Rate is 'higher_bearish' in EVENT_SURPRISE_DIRECTION (a
    # higher actual is USD-bearish) — but classify_surprise must still say
    # 'higher' here, since actual DID come in above forecast. Conflating the
    # two would silently invert the displayed history for bearish-mapped
    # indicators.
    event = EconomicEvent(
        title="Unemployment Rate", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="4.0%", actual="4.3%",
    )
    assert classify_surprise(event) == "higher"
    print("PASS\n")


def test_filter_relevant_events_extra_titles_admits_medium_regardless_of_threshold():
    print("=== filter_relevant_events: extra_titles admits a specific Medium title even under the default High threshold ===")
    high_event = _fake_event(title="CPI m/m", impact="High")
    allowlisted_medium = _fake_event(title="Retail Sales m/m", impact="Medium")
    other_medium = _fake_event(title="Building Permits", impact="Medium")
    result = filter_relevant_events(
        [high_event, allowlisted_medium, other_medium],
        extra_titles=frozenset({"Retail Sales m/m"}),
    )
    titles = {e.title for e in result}
    assert titles == {"CPI m/m", "Retail Sales m/m"}
    print("PASS\n")


def test_filter_relevant_events_extra_titles_defaults_to_empty():
    print("=== filter_relevant_events: omitting extra_titles reproduces today's exact High-only default ===")
    high_event = _fake_event(title="CPI m/m", impact="High")
    medium_event = _fake_event(title="Retail Sales m/m", impact="Medium")
    result = filter_relevant_events([high_event, medium_event])
    assert {e.title for e in result} == {"CPI m/m"}
    print("PASS\n")


if __name__ == "__main__":
    test_lastweek_rejected_with_informative_error()
    test_nextweek_rejected_with_informative_error()
    test_arbitrary_invalid_period_rejected()
    test_classify_surprise_higher_when_actual_above_forecast()
    test_classify_surprise_lower_when_actual_below_forecast()
    test_classify_surprise_in_line_within_tolerance()
    test_classify_surprise_none_when_title_not_tracked()
    test_classify_surprise_none_when_forecast_or_actual_missing()
    test_classify_surprise_is_literal_not_bullish_bearish()
    test_filter_relevant_events_extra_titles_admits_medium_regardless_of_threshold()
    test_filter_relevant_events_extra_titles_defaults_to_empty()
    print("All calendar_feed tests passed.")
