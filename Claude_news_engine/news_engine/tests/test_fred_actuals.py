"""
Tests for data_layer/fred_actuals.py — no live network, requests.get is
mocked with synthetic FRED /series/observations responses, same pattern
as tests/test_macro_backdrop.py.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.fred_actuals as fred_actuals
from config.settings import UTC_TZ


def _fake_response(observations, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = {"observations": observations}
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


def _obs(date_str, value, realtime_start):
    return {"date": date_str, "value": value, "realtime_start": realtime_start}


def test_get_actual_from_fred_returns_none_without_api_key():
    print("=== fred_actuals: get_actual_from_fred returns None (not a crash) when FRED_API_KEY is unset ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", ""):
        assert fred_actuals.get_actual_from_fred("CPI m/m", event_time) is None
    print("PASS\n")


def test_get_actual_from_fred_returns_none_for_untracked_title():
    print("=== fred_actuals: an event title with no FRED_SERIES_ID_BY_EVENT_TITLE entry returns None, no request made ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        result = fred_actuals.get_actual_from_fred("Some Untracked Title", event_time)
        assert result is None
        mock_get.assert_not_called()
    print("PASS\n")


def test_get_actual_from_fred_returns_formatted_value_when_fresh():
    print("=== fred_actuals: a fresh observation (realtime_start on/after the release date) returns a formatted percentage ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([_obs("2026-07-01", "0.24552", "2026-08-26")])
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result == "0.2%"
    print("PASS\n")


def test_get_actual_from_fred_uses_pc1_units_for_a_yy_title():
    print("=== fred_actuals: a y/y title requests units=pc1, not pch ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([_obs("2026-07-01", "3.30386", "2026-08-26")])
        result = fred_actuals.get_actual_from_fred("CPI y/y", event_time)
        assert result == "3.3%"
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["series_id"] == "CPIAUCSL"
        assert kwargs["params"]["units"] == "pc1"
    print("PASS\n")


def test_get_actual_from_fred_returns_none_when_observation_is_stale():
    print("=== fred_actuals: an observation whose realtime_start predates the release is treated as not-yet-available ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([_obs("2026-06-01", "0.14676", "2026-07-30")])
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result is None
    print("PASS\n")


def test_get_actual_from_fred_returns_none_on_missing_value_marker():
    print("=== fred_actuals: a FRED '.' (not-yet-published) observation returns None, not a fabricated 0.0 ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([_obs("2026-07-01", ".", "2026-08-26")])
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result is None
    print("PASS\n")


def test_get_actual_from_fred_returns_none_on_request_failure():
    print("=== fred_actuals: a failed request fails open to None, never raises ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get", side_effect=Exception("network down")):
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result is None
    print("PASS\n")


def test_get_actual_from_fred_returns_none_on_empty_observations():
    print("=== fred_actuals: no observations returned at all -> None, not an index-error crash ===")
    event_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC_TZ)
    with patch.object(fred_actuals, "FRED_API_KEY", "test-key"), \
         patch.object(fred_actuals.requests, "get") as mock_get:
        mock_get.return_value = _fake_response([])
        result = fred_actuals.get_actual_from_fred("Core PCE Price Index m/m", event_time)
        assert result is None
    print("PASS\n")


if __name__ == "__main__":
    test_get_actual_from_fred_returns_none_without_api_key()
    test_get_actual_from_fred_returns_none_for_untracked_title()
    test_get_actual_from_fred_returns_formatted_value_when_fresh()
    test_get_actual_from_fred_uses_pc1_units_for_a_yy_title()
    test_get_actual_from_fred_returns_none_when_observation_is_stale()
    test_get_actual_from_fred_returns_none_on_missing_value_marker()
    test_get_actual_from_fred_returns_none_on_request_failure()
    test_get_actual_from_fred_returns_none_on_empty_observations()
    print("All fred_actuals tests passed.")
