"""
Tests for data_layer/macro_backdrop.py — no live network, requests.get is
mocked with synthetic FRED /series/observations responses.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.macro_backdrop as macro_backdrop
from data_layer.macro_backdrop import MacroBackdropRead


def _fake_response(observations, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = {"observations": observations}
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


def _obs(date_str, value):
    return {"date": date_str, "value": value}


def test_get_macro_backdrop_read_returns_none_without_api_key():
    print("=== macro_backdrop: get_macro_backdrop_read returns None (not a crash) when FRED_API_KEY is unset ===")
    with patch.object(macro_backdrop, "FRED_API_KEY", ""):
        assert macro_backdrop.get_macro_backdrop_read() is None
    print("PASS\n")


def test_get_macro_backdrop_read_computes_dollar_index_pct_change():
    print("=== macro_backdrop: dollar index trend is a real % change from oldest to newest observation ===")
    dollar_obs = [_obs("2026-08-14", "121.0"), _obs("2026-08-13", "120.5"), _obs("2026-08-04", "120.0")]
    yield_obs = [_obs("2026-08-13", "2.40"), _obs("2026-08-04", "2.40")]
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get") as mock_get:
        mock_get.side_effect = [_fake_response(dollar_obs), _fake_response(yield_obs)]
        result = macro_backdrop.get_macro_backdrop_read()
        assert result is not None
        expected_pct = (121.0 - 120.0) / 120.0 * 100.0
        assert abs(result.dollar_index_trend_pct - expected_pct) < 1e-9
        assert result.dollar_index_latest_date == dt.date(2026, 8, 14)
    print("PASS\n")


def test_get_macro_backdrop_read_computes_real_yield_bps_change():
    print("=== macro_backdrop: real yield trend is a basis-point change, not a percent change ===")
    dollar_obs = [_obs("2026-08-14", "120.0"), _obs("2026-08-04", "120.0")]
    yield_obs = [_obs("2026-08-13", "2.45"), _obs("2026-08-04", "2.40")]
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get") as mock_get:
        mock_get.side_effect = [_fake_response(dollar_obs), _fake_response(yield_obs)]
        result = macro_backdrop.get_macro_backdrop_read()
        assert result is not None
        assert abs(result.real_yield_trend_bps - 5.0) < 1e-9  # 2.45 - 2.40 = 0.05 points = 5 bps
    print("PASS\n")


def test_get_macro_backdrop_read_skips_missing_observation_marker():
    print("=== macro_backdrop: a FRED '.' (not-yet-published) observation is skipped, not treated as 0.0 ===")
    dollar_obs = [_obs("2026-08-14", "."), _obs("2026-08-13", "121.0"), _obs("2026-08-04", "120.0")]
    yield_obs = [_obs("2026-08-13", "2.40"), _obs("2026-08-04", "2.40")]
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get") as mock_get:
        mock_get.side_effect = [_fake_response(dollar_obs), _fake_response(yield_obs)]
        result = macro_backdrop.get_macro_backdrop_read()
        assert result.dollar_index_latest_date == dt.date(2026, 8, 13)  # the "." row is skipped, not used as latest
        expected_pct = (121.0 - 120.0) / 120.0 * 100.0
        assert abs(result.dollar_index_trend_pct - expected_pct) < 1e-9
    print("PASS\n")


def test_get_macro_backdrop_read_returns_none_when_both_series_unavailable():
    print("=== macro_backdrop: get_macro_backdrop_read returns None only when BOTH series fail ===")
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get", side_effect=Exception("network down")):
        assert macro_backdrop.get_macro_backdrop_read() is None
    print("PASS\n")


def test_get_macro_backdrop_read_returns_partial_when_one_series_available():
    print("=== macro_backdrop: a partial read (one series fails) still returns a real MacroBackdropRead, not None ===")
    dollar_obs = [_obs("2026-08-14", "121.0"), _obs("2026-08-04", "120.0")]
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get") as mock_get:
        mock_get.side_effect = [_fake_response(dollar_obs), Exception("network down")]
        result = macro_backdrop.get_macro_backdrop_read()
        assert result is not None
        assert result.dollar_index_trend_pct is not None
        assert result.real_yield_trend_bps is None
    print("PASS\n")


def test_lean_returns_one_when_dollar_index_rises_past_threshold():
    print("=== macro_backdrop: .lean is +1 (USD-bullish) when the dollar index rises past the threshold ===")
    read = MacroBackdropRead(dollar_index_trend_pct=0.5, dollar_index_latest_date=None,
                              real_yield_trend_bps=None, real_yield_latest_date=None, lookback_days=10)
    assert read.lean == 1
    print("PASS\n")


def test_lean_returns_minus_one_when_dollar_index_falls_past_threshold():
    print("=== macro_backdrop: .lean is -1 (USD-bearish) when the dollar index falls past the threshold ===")
    read = MacroBackdropRead(dollar_index_trend_pct=-0.5, dollar_index_latest_date=None,
                              real_yield_trend_bps=None, real_yield_latest_date=None, lookback_days=10)
    assert read.lean == -1
    print("PASS\n")


def test_lean_falls_back_to_real_yield_when_dollar_index_is_flat():
    print("=== macro_backdrop: .lean falls back to the real yield trend when the dollar index shows no clear move ===")
    read = MacroBackdropRead(dollar_index_trend_pct=0.05, dollar_index_latest_date=None,
                              real_yield_trend_bps=8.0, real_yield_latest_date=None, lookback_days=10)
    assert read.lean == 1  # dollar index below its 0.3% threshold, real yield's +8bps above its 5bps threshold
    print("PASS\n")


def test_lean_is_none_when_both_measures_are_below_threshold():
    print("=== macro_backdrop: .lean is None (no claim) when neither measure clears its threshold ===")
    read = MacroBackdropRead(dollar_index_trend_pct=0.05, dollar_index_latest_date=None,
                              real_yield_trend_bps=1.0, real_yield_latest_date=None, lookback_days=10)
    assert read.lean is None
    print("PASS\n")


def test_lean_is_none_with_no_data_at_all():
    print("=== macro_backdrop: .lean is None (not fabricated) when both measures are None ===")
    read = MacroBackdropRead(dollar_index_trend_pct=None, dollar_index_latest_date=None,
                              real_yield_trend_bps=None, real_yield_latest_date=None, lookback_days=10)
    assert read.lean is None
    print("PASS\n")


if __name__ == "__main__":
    test_get_macro_backdrop_read_returns_none_without_api_key()
    test_get_macro_backdrop_read_computes_dollar_index_pct_change()
    test_get_macro_backdrop_read_computes_real_yield_bps_change()
    test_get_macro_backdrop_read_skips_missing_observation_marker()
    test_get_macro_backdrop_read_returns_none_when_both_series_unavailable()
    test_get_macro_backdrop_read_returns_partial_when_one_series_available()
    test_lean_returns_one_when_dollar_index_rises_past_threshold()
    test_lean_returns_minus_one_when_dollar_index_falls_past_threshold()
    test_lean_falls_back_to_real_yield_when_dollar_index_is_flat()
    test_lean_is_none_when_both_measures_are_below_threshold()
    test_lean_is_none_with_no_data_at_all()
    print("All macro_backdrop tests passed.")
