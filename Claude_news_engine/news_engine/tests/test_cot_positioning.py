"""
Tests for data_layer/cot_positioning.py — CFTC's free "Traders in
Financial Futures" (TFF) report, used for a confidence-only "is this
positioning already crowded" dampener (never a directional lean — see
docs/superpowers/specs/2026-09-02-fundamental-signals-batch-design.md).
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import data_layer.cot_positioning as cot_positioning
from data_layer.cot_positioning import (
    get_cot_positioning_read, CotPositioningRead,
    COT_CROWDING_PERCENTILE_THRESHOLD, COT_CROWDING_LOOKBACK_WEEKS,
)


@pytest.fixture(autouse=True)
def _reset_cot_cache():
    """The module caches its last read per calendar day in module-level
    globals. Without resetting them, one test's cached result leaks into
    the next test that calls get_cot_positioning_read() on the same real
    day — reset before (and after, for safety) every test."""
    cot_positioning._cache_date = None
    cot_positioning._cache_read = None
    yield
    cot_positioning._cache_date = None
    cot_positioning._cache_read = None


def _cftc_response(rows):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = rows
    return mock_resp


def _row(report_date, net_long):
    """One TFF report row shaped like the real CFTC API response — only
    the fields this module actually reads."""
    return {
        "market_and_exchange_names": "U.S. DOLLAR INDEX - ICE FUTURES U.S.",
        "report_date_as_yyyy_mm_dd": report_date,
        "lev_money_positions_long": str(net_long if net_long > 0 else 0),
        "lev_money_positions_short": str(-net_long if net_long < 0 else 0),
    }


def test_fetch_failure_returns_none():
    print("=== get_cot_positioning_read: a failed request returns None, never raises ===")
    with patch("requests.get", side_effect=requests.exceptions.RequestException("simulated failure")):
        assert get_cot_positioning_read() is None
    print("PASS\n")


def test_empty_response_returns_none():
    print("=== get_cot_positioning_read: an empty result set (no matching rows) returns None ===")
    with patch("requests.get", return_value=_cftc_response([])):
        assert get_cot_positioning_read() is None
    print("PASS\n")


def test_real_data_computes_percentile_and_is_crowded():
    print("=== get_cot_positioning_read: a real trailing window computes a percentile and .is_crowded ===")
    # 20 weekly rows, net long climbing from 1000 to 20000 — the newest
    # (20000) is the highest in the window, so it should rank at/near the
    # 100th percentile and read as crowded-long.
    rows = [_row(f"2026-{(i % 12) + 1:02d}-01T00:00:00.000", 1000 * (i + 1)) for i in range(20)]
    # Ensure rows are returned newest-first, matching a real $order=...DESC query
    rows = list(reversed(rows))
    with patch("requests.get", return_value=_cftc_response(rows)):
        read = get_cot_positioning_read()

    assert read is not None
    assert isinstance(read, CotPositioningRead)
    assert read.net_leveraged_funds_position == 20000
    assert read.percentile_in_trailing_window == pytest.approx(100.0, abs=0.01)
    assert read.is_crowded == 1  # extreme long
    print("PASS\n")


def test_mid_range_positioning_is_not_crowded():
    print("=== get_cot_positioning_read: positioning in the middle of its trailing range is NOT flagged crowded ===")
    # Net long oscillating in a tight band around 5000 — the newest
    # reading sits near the middle of the range, not an extreme.
    values = [4800, 5200, 4900, 5100, 5000] * 4  # 20 rows, newest last before reversal
    rows = [_row(f"2026-{(i % 12) + 1:02d}-01T00:00:00.000", v) for i, v in enumerate(values)]
    rows = list(reversed(rows))
    with patch("requests.get", return_value=_cftc_response(rows)):
        read = get_cot_positioning_read()

    assert read is not None
    assert read.is_crowded is None  # mid-range, not extreme
    print("PASS\n")


def test_malformed_date_returns_none():
    print("=== get_cot_positioning_read: a missing/unparseable report_date field returns None, never raises ===")
    # Missing report_date_as_yyyy_mm_dd entirely (KeyError inside the parse).
    rows_missing_key = [_row(f"2026-{(i % 12) + 1:02d}-01T00:00:00.000", 1000 * (i + 1)) for i in range(20)]
    rows_missing_key = list(reversed(rows_missing_key))
    del rows_missing_key[0]["report_date_as_yyyy_mm_dd"]
    with patch("requests.get", return_value=_cftc_response(rows_missing_key)):
        assert get_cot_positioning_read() is None

    cot_positioning._cache_date = None
    cot_positioning._cache_read = None

    # Unparseable date string (ValueError inside dt.date.fromisoformat).
    rows_bad_date = [_row(f"2026-{(i % 12) + 1:02d}-01T00:00:00.000", 1000 * (i + 1)) for i in range(20)]
    rows_bad_date = list(reversed(rows_bad_date))
    rows_bad_date[0]["report_date_as_yyyy_mm_dd"] = "not-a-date"
    with patch("requests.get", return_value=_cftc_response(rows_bad_date)):
        assert get_cot_positioning_read() is None
    print("PASS\n")


def test_dict_response_returns_none():
    print("=== get_cot_positioning_read: a Socrata-style dict error response (HTTP 200) returns None, never raises ===")
    # A truthy dict passes the `if not rows:` check, then iterating it
    # yields string keys, whose .get(...) call would raise AttributeError
    # if not caught by the widened exception handling.
    error_response = {"error": True, "message": "simulated Socrata error payload"}
    with patch("requests.get", return_value=_cftc_response(error_response)):
        assert get_cot_positioning_read() is None
    print("PASS\n")


def test_daily_cache_avoids_refetching_same_day():
    print("=== get_cot_positioning_read: a second call the same day reuses the cached read, doesn't re-fetch ===")
    rows = [_row(f"2026-{(i % 12) + 1:02d}-01T00:00:00.000", 1000 * (i + 1)) for i in range(20)]
    rows = list(reversed(rows))
    now = dt.datetime(2026, 9, 2, 10, 0, tzinfo=dt.timezone.utc)
    with patch("requests.get", return_value=_cftc_response(rows)) as mock_get:
        first = get_cot_positioning_read(now=now)
        second = get_cot_positioning_read(now=now + dt.timedelta(hours=2))  # same calendar day
    assert mock_get.call_count == 1  # only fetched once
    assert first == second
    print("PASS\n")


if __name__ == "__main__":
    test_fetch_failure_returns_none()
    test_empty_response_returns_none()
    test_real_data_computes_percentile_and_is_crowded()
    test_mid_range_positioning_is_not_crowded()
    test_malformed_date_returns_none()
    test_dict_response_returns_none()
    test_daily_cache_avoids_refetching_same_day()
    print("All cot_positioning tests passed.")
