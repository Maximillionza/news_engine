"""
Tests for data_layer/macro_backdrop.py — no live network, requests.get is
mocked with synthetic FRED /series/observations responses.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import data_layer.macro_backdrop as macro_backdrop
from data_layer.macro_backdrop import MacroBackdropRead, EQUITY_INDEX_SERIES_ID


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
    oil_obs = [_obs("2026-08-13", "80.0"), _obs("2026-08-04", "80.0")]
    equity_obs = [_obs("2026-08-13", "5000.0"), _obs("2026-08-04", "5000.0")]
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(dollar_obs), _fake_response(yield_obs), _fake_response(oil_obs),
            _fake_response(equity_obs), _fake_response(oil_obs),
        ]
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
    oil_obs = [_obs("2026-08-13", "80.0"), _obs("2026-08-04", "80.0")]
    equity_obs = [_obs("2026-08-13", "5000.0"), _obs("2026-08-04", "5000.0")]
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(dollar_obs), _fake_response(yield_obs), _fake_response(oil_obs),
            _fake_response(equity_obs), _fake_response(oil_obs),
        ]
        result = macro_backdrop.get_macro_backdrop_read()
        assert result is not None
        assert abs(result.real_yield_trend_bps - 5.0) < 1e-9  # 2.45 - 2.40 = 0.05 points = 5 bps
    print("PASS\n")


def test_get_macro_backdrop_read_skips_missing_observation_marker():
    print("=== macro_backdrop: a FRED '.' (not-yet-published) observation is skipped, not treated as 0.0 ===")
    dollar_obs = [_obs("2026-08-14", "."), _obs("2026-08-13", "121.0"), _obs("2026-08-04", "120.0")]
    yield_obs = [_obs("2026-08-13", "2.40"), _obs("2026-08-04", "2.40")]
    oil_obs = [_obs("2026-08-13", "80.0"), _obs("2026-08-04", "80.0")]
    equity_obs = [_obs("2026-08-13", "5000.0"), _obs("2026-08-04", "5000.0")]
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(dollar_obs), _fake_response(yield_obs), _fake_response(oil_obs),
            _fake_response(equity_obs), _fake_response(oil_obs),
        ]
        result = macro_backdrop.get_macro_backdrop_read()
        assert result.dollar_index_latest_date == dt.date(2026, 8, 13)  # the "." row is skipped, not used as latest
        expected_pct = (121.0 - 120.0) / 120.0 * 100.0
        assert abs(result.dollar_index_trend_pct - expected_pct) < 1e-9
    print("PASS\n")


def test_get_macro_backdrop_read_returns_none_when_all_series_unavailable():
    print("=== macro_backdrop: get_macro_backdrop_read returns None only when ALL FOUR series fail ===")
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get", side_effect=Exception("network down")):
        assert macro_backdrop.get_macro_backdrop_read() is None
    print("PASS\n")


def test_get_macro_backdrop_read_returns_partial_when_one_series_available():
    print("=== macro_backdrop: a partial read (two series fail) still returns a real MacroBackdropRead, not None ===")
    dollar_obs = [_obs("2026-08-14", "121.0"), _obs("2026-08-04", "120.0")]
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(dollar_obs), Exception("network down"), Exception("network down"),
            Exception("network down"), Exception("network down"),
        ]
        result = macro_backdrop.get_macro_backdrop_read()
        assert result is not None
        assert result.dollar_index_trend_pct is not None
        assert result.real_yield_trend_bps is None
        assert result.oil_trend_pct is None
        assert result.equity_index_trend_pct is None
        assert result.oil_daily_change_pct is None
    print("PASS\n")


def test_get_macro_backdrop_read_computes_oil_pct_change():
    print("=== macro_backdrop: WTI oil trend is a real % change from oldest to newest observation, same as dollar index ===")
    dollar_obs = [_obs("2026-08-14", "120.0"), _obs("2026-08-04", "120.0")]
    yield_obs = [_obs("2026-08-13", "2.40"), _obs("2026-08-04", "2.40")]
    oil_obs = [_obs("2026-08-13", "84.0"), _obs("2026-08-04", "80.0")]
    equity_obs = [_obs("2026-08-13", "5000.0"), _obs("2026-08-04", "5000.0")]
    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(dollar_obs), _fake_response(yield_obs), _fake_response(oil_obs),
            _fake_response(equity_obs), _fake_response(oil_obs),
        ]
        result = macro_backdrop.get_macro_backdrop_read()
        assert result is not None
        expected_pct = (84.0 - 80.0) / 80.0 * 100.0  # 5.0%
        assert abs(result.oil_trend_pct - expected_pct) < 1e-9
        assert result.oil_latest_date == dt.date(2026, 8, 13)
    print("PASS\n")


def test_get_macro_backdrop_read_includes_equity_index_trend():
    print("=== get_macro_backdrop_read: SP500 equity trend is fetched alongside dollar/yield/oil ===")

    def _side_effect(*args, **kwargs):
        series_id = kwargs["params"]["series_id"]
        if series_id == EQUITY_INDEX_SERIES_ID:
            return _fake_response([_obs("2026-08-31", "5100.00"), _obs("2026-08-20", "5000.00")])
        return _fake_response([_obs("2026-08-13", "120.0"), _obs("2026-08-04", "120.0")])

    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get", side_effect=_side_effect):
        result = macro_backdrop.get_macro_backdrop_read()

    assert result is not None
    assert abs(result.equity_index_trend_pct - 2.0) < 0.01  # (5100-5000)/5000*100
    assert result.equity_index_latest_date == dt.date(2026, 8, 31)
    print("PASS\n")


def test_get_macro_backdrop_read_includes_oil_daily_change():
    print("=== get_macro_backdrop_read: oil's single most-recent-day change is captured separately from its 10-day trend ===")

    def _side_effect(*args, **kwargs):
        series_id = kwargs["params"]["series_id"]
        if series_id == macro_backdrop.OIL_SERIES_ID:
            return _fake_response([
                _obs("2026-08-31", "75.00"),  # the newest observation
                _obs("2026-08-29", "70.50"),
                _obs("2026-08-28", "70.00"),
            ])
        return _fake_response([_obs("2026-08-13", "120.0"), _obs("2026-08-04", "120.0")])

    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get", side_effect=_side_effect):
        result = macro_backdrop.get_macro_backdrop_read()

    assert result is not None
    # Daily change = newest vs. SECOND-newest observation only (70.50 -> 75.00),
    # not the full window (70.00 -> 75.00) — a shock is a one-session move.
    expected_pct = (75.00 - 70.50) / 70.50 * 100.0
    assert abs(result.oil_daily_change_pct - expected_pct) < 0.01
    print("PASS\n")


def test_get_macro_backdrop_read_returns_none_only_when_all_four_series_fail():
    print("=== get_macro_backdrop_read: a real equity-only read is NOT discarded as \"no data\" ===")

    def _side_effect(*args, **kwargs):
        series_id = kwargs["params"]["series_id"]
        if series_id == EQUITY_INDEX_SERIES_ID:
            return _fake_response([_obs("2026-08-31", "5100.00"), _obs("2026-08-20", "5000.00")])
        raise requests.exceptions.RequestException("simulated failure")

    with patch.object(macro_backdrop, "FRED_API_KEY", "test-key"), \
         patch.object(macro_backdrop.requests, "get", side_effect=_side_effect):
        result = macro_backdrop.get_macro_backdrop_read()

    assert result is not None  # NOT None, even though dollar/yield/oil all failed
    assert abs(result.equity_index_trend_pct - 2.0) < 0.01
    assert result.dollar_index_trend_pct is None
    assert result.real_yield_trend_bps is None
    assert result.oil_trend_pct is None
    assert result.oil_daily_change_pct is None
    print("PASS\n")


def test_lean_returns_one_when_dollar_index_rises_past_threshold():
    print("=== macro_backdrop: .lean is +1 (USD-bullish) when the dollar index rises past the threshold ===")
    read = MacroBackdropRead(equity_index_trend_pct=None, equity_index_latest_date=None,
                              oil_daily_change_pct=None, dollar_index_trend_pct=0.5, dollar_index_latest_date=None,
                              real_yield_trend_bps=None, real_yield_latest_date=None,
                              oil_trend_pct=None, oil_latest_date=None, lookback_days=10)
    assert read.lean == 1
    print("PASS\n")


def test_lean_returns_minus_one_when_dollar_index_falls_past_threshold():
    print("=== macro_backdrop: .lean is -1 (USD-bearish) when the dollar index falls past the threshold ===")
    read = MacroBackdropRead(equity_index_trend_pct=None, equity_index_latest_date=None,
                              oil_daily_change_pct=None, dollar_index_trend_pct=-0.5, dollar_index_latest_date=None,
                              real_yield_trend_bps=None, real_yield_latest_date=None,
                              oil_trend_pct=None, oil_latest_date=None, lookback_days=10)
    assert read.lean == -1
    print("PASS\n")


def test_lean_falls_back_to_real_yield_when_dollar_index_is_flat():
    print("=== macro_backdrop: .lean falls back to the real yield trend when the dollar index shows no clear move ===")
    read = MacroBackdropRead(equity_index_trend_pct=None, equity_index_latest_date=None,
                              oil_daily_change_pct=None, dollar_index_trend_pct=0.05, dollar_index_latest_date=None,
                              real_yield_trend_bps=8.0, real_yield_latest_date=None,
                              oil_trend_pct=None, oil_latest_date=None, lookback_days=10)
    assert read.lean == 1  # dollar index below its 0.3% threshold, real yield's +8bps above its 5bps threshold
    print("PASS\n")


def test_lean_falls_back_to_oil_when_dollar_index_and_real_yield_are_flat():
    print("=== macro_backdrop: .lean falls back to oil (leading inflation-expectations proxy) when both direct USD measures are silent ===")
    read = MacroBackdropRead(equity_index_trend_pct=None, equity_index_latest_date=None,
                              oil_daily_change_pct=None, dollar_index_trend_pct=0.05, dollar_index_latest_date=None,
                              real_yield_trend_bps=1.0, real_yield_latest_date=None,
                              oil_trend_pct=6.0, oil_latest_date=None, lookback_days=10)
    assert read.lean == 1  # rising oil past its 5% threshold -> inflation-supportive -> hawkish/USD-bullish lean
    print("PASS\n")


def test_lean_oil_never_overrides_dollar_index():
    print("=== macro_backdrop: oil is the lowest-priority fallback -- it never overrides a clear dollar-index lean, even pointing the opposite way ===")
    read = MacroBackdropRead(equity_index_trend_pct=None, equity_index_latest_date=None,
                              oil_daily_change_pct=None, dollar_index_trend_pct=0.5, dollar_index_latest_date=None,
                              real_yield_trend_bps=None, real_yield_latest_date=None,
                              oil_trend_pct=-8.0, oil_latest_date=None, lookback_days=10)
    assert read.lean == 1  # dollar index says +1; oil's -8% would say -1 alone, but dollar index wins
    print("PASS\n")


def test_lean_oil_below_its_own_threshold_is_ignored():
    print("=== macro_backdrop: an oil move below its (wider, noise-aware) threshold does not produce a lean ===")
    read = MacroBackdropRead(equity_index_trend_pct=None, equity_index_latest_date=None,
                              oil_daily_change_pct=None, dollar_index_trend_pct=0.05, dollar_index_latest_date=None,
                              real_yield_trend_bps=1.0, real_yield_latest_date=None,
                              oil_trend_pct=3.0, oil_latest_date=None, lookback_days=10)
    assert read.lean is None  # 3% is real movement for oil but below the 5% noise-aware threshold
    print("PASS\n")


def test_lean_is_none_when_all_measures_are_below_threshold():
    print("=== macro_backdrop: .lean is None (no claim) when no measure clears its threshold ===")
    read = MacroBackdropRead(equity_index_trend_pct=None, equity_index_latest_date=None,
                              oil_daily_change_pct=None, dollar_index_trend_pct=0.05, dollar_index_latest_date=None,
                              real_yield_trend_bps=1.0, real_yield_latest_date=None,
                              oil_trend_pct=1.0, oil_latest_date=None, lookback_days=10)
    assert read.lean is None
    print("PASS\n")


def test_lean_is_none_with_no_data_at_all():
    print("=== macro_backdrop: .lean is None (not fabricated) when all measures are None ===")
    read = MacroBackdropRead(equity_index_trend_pct=None, equity_index_latest_date=None,
                              oil_daily_change_pct=None, dollar_index_trend_pct=None, dollar_index_latest_date=None,
                              real_yield_trend_bps=None, real_yield_latest_date=None,
                              oil_trend_pct=None, oil_latest_date=None, lookback_days=10)
    assert read.lean is None
    print("PASS\n")


if __name__ == "__main__":
    test_get_macro_backdrop_read_returns_none_without_api_key()
    test_get_macro_backdrop_read_computes_dollar_index_pct_change()
    test_get_macro_backdrop_read_computes_real_yield_bps_change()
    test_get_macro_backdrop_read_skips_missing_observation_marker()
    test_get_macro_backdrop_read_returns_none_when_all_series_unavailable()
    test_get_macro_backdrop_read_returns_partial_when_one_series_available()
    test_get_macro_backdrop_read_computes_oil_pct_change()
    test_get_macro_backdrop_read_includes_equity_index_trend()
    test_get_macro_backdrop_read_includes_oil_daily_change()
    test_get_macro_backdrop_read_returns_none_only_when_all_four_series_fail()
    test_lean_returns_one_when_dollar_index_rises_past_threshold()
    test_lean_returns_minus_one_when_dollar_index_falls_past_threshold()
    test_lean_falls_back_to_real_yield_when_dollar_index_is_flat()
    test_lean_falls_back_to_oil_when_dollar_index_and_real_yield_are_flat()
    test_lean_oil_never_overrides_dollar_index()
    test_lean_oil_below_its_own_threshold_is_ignored()
    test_lean_is_none_when_all_measures_are_below_threshold()
    test_lean_is_none_with_no_data_at_all()
    print("All macro_backdrop tests passed.")
