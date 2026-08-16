"""
Tests for data_layer/fred_calendar_feed.py — no live network, requests.get
is mocked with synthetic FRED API responses. get_upcoming_release_dates()'s
FRED_API_KEY dependency is patched per-test (this module reads it at
call time via config.settings, not at import time).
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.fred_calendar_feed as fred_calendar_feed
from data_layer.fred_calendar_feed import FredReleaseDate, compare_fred_to_ff


def _fake_response(json_body, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = json_body
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


def test_get_upcoming_release_dates_returns_empty_without_api_key():
    print("=== fred_calendar_feed: get_upcoming_release_dates returns [] (not a crash) when FRED_API_KEY is unset ===")
    with patch.object(fred_calendar_feed, "FRED_API_KEY", ""):
        result = fred_calendar_feed.get_upcoming_release_dates(10)
        assert result == []
    print("PASS\n")


def test_get_upcoming_release_dates_parses_real_response_shape():
    print("=== fred_calendar_feed: get_upcoming_release_dates parses a real FRED /releases/dates response shape ===")
    body = {"release_dates": [{"release_id": "10", "date": "2026-09-15"}, {"release_id": "10", "date": "2026-10-14"}]}
    with patch.object(fred_calendar_feed, "FRED_API_KEY", "test-key"), \
         patch.object(fred_calendar_feed.requests, "get", return_value=_fake_response(body)) as mock_get:
        result = fred_calendar_feed.get_upcoming_release_dates(10, today=dt.date(2026, 8, 15))
        assert len(result) == 2
        assert result[0] == FredReleaseDate(release_id=10, release_date=dt.date(2026, 9, 15))
        assert result[1] == FredReleaseDate(release_id=10, release_date=dt.date(2026, 10, 14))
        params = mock_get.call_args.kwargs["params"]
        assert params["release_id"] == 10
        assert params["api_key"] == "test-key"
        assert params["realtime_start"] == "2026-08-15"
        assert params["realtime_end"] == "2026-09-19"  # today + 35 days default
    print("PASS\n")


def test_get_upcoming_release_dates_returns_empty_on_request_failure():
    print("=== fred_calendar_feed: get_upcoming_release_dates returns [] (not a crash) when the request fails ===")
    with patch.object(fred_calendar_feed, "FRED_API_KEY", "test-key"), \
         patch.object(fred_calendar_feed.requests, "get", side_effect=Exception("network down")):
        result = fred_calendar_feed.get_upcoming_release_dates(10)
        assert result == []
    print("PASS\n")


def test_get_upcoming_release_dates_skips_malformed_rows_not_the_whole_response():
    print("=== fred_calendar_feed: a malformed row is skipped, doesn't drop the rest of the response ===")
    body = {"release_dates": [{"release_id": "10", "date": "not-a-date"}, {"release_id": "10", "date": "2026-09-15"}]}
    with patch.object(fred_calendar_feed, "FRED_API_KEY", "test-key"), \
         patch.object(fred_calendar_feed.requests, "get", return_value=_fake_response(body)):
        result = fred_calendar_feed.get_upcoming_release_dates(10)
        assert len(result) == 1
        assert result[0].release_date == dt.date(2026, 9, 15)
    print("PASS\n")


def test_compare_fred_to_ff_matches_within_tolerance():
    print("=== fred_calendar_feed: compare_fred_to_ff matches a FRED date and an FF date within tolerance_days ===")
    fred_dates_by_title = {"CPI m/m": [FredReleaseDate(release_id=10, release_date=dt.date(2026, 9, 15))]}
    ff_events = [{"title": "CPI m/m", "event_time_utc": "2026-09-15T12:30:00+00:00"}]
    rows = compare_fred_to_ff(fred_dates_by_title, ff_events)
    assert len(rows) == 1
    assert rows[0].status == "match"
    assert rows[0].fred_date == dt.date(2026, 9, 15)
    assert rows[0].ff_date == dt.date(2026, 9, 15)
    print("PASS\n")


def test_compare_fred_to_ff_flags_fred_only_when_ff_has_nothing_yet():
    print("=== fred_calendar_feed: compare_fred_to_ff flags fred_only when FF's feed hasn't populated that date yet ===")
    fred_dates_by_title = {"CPI m/m": [FredReleaseDate(release_id=10, release_date=dt.date(2026, 9, 15))]}
    rows = compare_fred_to_ff(fred_dates_by_title, ff_events=[])
    assert len(rows) == 1
    assert rows[0].status == "fred_only"
    assert rows[0].fred_date == dt.date(2026, 9, 15)
    assert rows[0].ff_date is None
    print("PASS\n")


def test_compare_fred_to_ff_flags_ff_only_when_fred_has_no_matching_date():
    print("=== fred_calendar_feed: compare_fred_to_ff flags ff_only when FF has a date FRED's window didn't predict ===")
    fred_dates_by_title = {"CPI m/m": []}
    ff_events = [{"title": "CPI m/m", "event_time_utc": "2026-09-15T12:30:00+00:00"}]
    rows = compare_fred_to_ff(fred_dates_by_title, ff_events)
    assert len(rows) == 1
    assert rows[0].status == "ff_only"
    assert rows[0].fred_date is None
    assert rows[0].ff_date == dt.date(2026, 9, 15)
    print("PASS\n")


def test_compare_fred_to_ff_outside_tolerance_is_not_a_match():
    print("=== fred_calendar_feed: a FRED date and FF date more than tolerance_days apart are NOT treated as a match ===")
    fred_dates_by_title = {"CPI m/m": [FredReleaseDate(release_id=10, release_date=dt.date(2026, 9, 10))]}
    ff_events = [{"title": "CPI m/m", "event_time_utc": "2026-09-15T12:30:00+00:00"}]
    rows = compare_fred_to_ff(fred_dates_by_title, ff_events, tolerance_days=1)
    statuses = {r.status for r in rows}
    assert statuses == {"fred_only", "ff_only"}
    print("PASS\n")


def test_compare_fred_to_ff_ignores_events_with_a_different_title():
    print("=== fred_calendar_feed: compare_fred_to_ff only compares FF events matching the mapped title, not everything ===")
    fred_dates_by_title = {"CPI m/m": [FredReleaseDate(release_id=10, release_date=dt.date(2026, 9, 15))]}
    ff_events = [{"title": "PPI m/m", "event_time_utc": "2026-09-15T12:30:00+00:00"}]
    rows = compare_fred_to_ff(fred_dates_by_title, ff_events)
    assert len(rows) == 1
    assert rows[0].status == "fred_only"  # the PPI event never enters this title's comparison at all
    print("PASS\n")


if __name__ == "__main__":
    test_get_upcoming_release_dates_returns_empty_without_api_key()
    test_get_upcoming_release_dates_parses_real_response_shape()
    test_get_upcoming_release_dates_returns_empty_on_request_failure()
    test_get_upcoming_release_dates_skips_malformed_rows_not_the_whole_response()
    test_compare_fred_to_ff_matches_within_tolerance()
    test_compare_fred_to_ff_flags_fred_only_when_ff_has_nothing_yet()
    test_compare_fred_to_ff_flags_ff_only_when_fred_has_no_matching_date()
    test_compare_fred_to_ff_outside_tolerance_is_not_a_match()
    test_compare_fred_to_ff_ignores_events_with_a_different_title()
    print("All fred_calendar_feed tests passed.")
