"""
Tests for data_layer/dukascopy_feed.py — no live network, dukascopy_python.fetch
is mocked with synthetic pandas DataFrames.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import data_layer.dukascopy_feed as dukascopy_feed


def test_get_price_at_returns_first_tick_price():
    print("=== dukascopy_feed: get_price_at returns the first tick's bid price ===")
    when = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    fake_df = pd.DataFrame({
        "bidPrice": [2415.32, 2415.40],
        "askPrice": [2415.50, 2415.58],
    })
    with patch.object(dukascopy_feed.dukascopy_python, "fetch", return_value=fake_df) as mock_fetch:
        result = dukascopy_feed.get_price_at("XAUUSD", when)
        assert result is not None
        assert result.price == 2415.32, "should use the FIRST row's bidPrice, not e.g. the last"
        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        assert args[3] == when, "fetch window must start exactly at when_utc — no lookahead"
    print("PASS\n")


def test_get_price_at_returns_none_on_empty_window():
    print("=== dukascopy_feed: get_price_at returns None when the fetch window has no ticks (market closed/gap) ===")
    when = dt.datetime(2026, 8, 8, 3, 0, tzinfo=dt.timezone.utc)  # a Saturday — market closed
    fake_df = pd.DataFrame({"bidPrice": [], "askPrice": []})
    with patch.object(dukascopy_feed.dukascopy_python, "fetch", return_value=fake_df):
        result = dukascopy_feed.get_price_at("XAUUSD", when)
        assert result is None
    print("PASS\n")


def test_get_price_at_returns_none_on_fetch_exception():
    print("=== dukascopy_feed: get_price_at returns None (not a crash) when fetch() raises ===")
    when = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    with patch.object(dukascopy_feed.dukascopy_python, "fetch", side_effect=Exception("network down")):
        result = dukascopy_feed.get_price_at("US30", when)
        assert result is None
    print("PASS\n")


def test_get_price_at_rejects_a_genuinely_unmapped_instrument():
    print("=== dukascopy_feed: get_price_at raises a clear ValueError for a ticker with no real Dukascopy coverage at all (not even under FX_MAJORS/FX_CROSSES) ===")
    when = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    try:
        dukascopy_feed.get_price_at("ZZZUSD", when)  # matches the USD-quote shape but no real currency code
        raise AssertionError("expected ValueError for a genuinely unmapped instrument")
    except ValueError as e:
        assert "ZZZUSD" in str(e)
    print("PASS\n")


def test_resolve_dukascopy_instrument_hits_the_static_map_first():
    print("=== _resolve_dukascopy_instrument: the hand-verified metals/indices map (XAUUSD/XAGUSD/US30/US500/NAS100) resolves without going near the FX-pair fallback ===")
    assert dukascopy_feed._resolve_dukascopy_instrument("XAUUSD") == dukascopy_feed._INSTRUMENT_MAP["XAUUSD"]
    assert dukascopy_feed._resolve_dukascopy_instrument("XAGUSD") == dukascopy_feed._INSTRUMENT_MAP["XAGUSD"]
    assert dukascopy_feed._resolve_dukascopy_instrument("US500") == dukascopy_feed._INSTRUMENT_MAP["US500"]
    assert dukascopy_feed._resolve_dukascopy_instrument("NAS100") == dukascopy_feed._INSTRUMENT_MAP["NAS100"]
    print("PASS\n")


def test_resolve_dukascopy_instrument_derives_a_real_usd_legged_fx_pair_never_hand_entered():
    print("=== _resolve_dukascopy_instrument: a real USD-legged FX pair NEVER added to the static map resolves via the real, verified naming convention ===")
    import dukascopy_python.instruments as inst
    assert dukascopy_feed._resolve_dukascopy_instrument("EURUSD") == inst.INSTRUMENT_FX_MAJORS_EUR_USD
    assert dukascopy_feed._resolve_dukascopy_instrument("USDJPY") == inst.INSTRUMENT_FX_MAJORS_USD_JPY
    # USD/BRL exists only under FX_CROSSES, not FX_MAJORS -- proves the
    # fallback-to-crosses step is real, not dead code.
    assert dukascopy_feed._resolve_dukascopy_instrument("USDBRL") == inst.INSTRUMENT_FX_CROSSES_USD_BRL
    print("PASS\n")


def test_resolve_dukascopy_instrument_returns_none_for_a_real_fx_cross_no_usd_leg():
    print("=== _resolve_dukascopy_instrument: a real fx_cross pair with no USD leg (e.g. GBPAUD) returns None -- it never enters the backtest/outcome pipeline in the first place, nothing to grade ===")
    assert dukascopy_feed._resolve_dukascopy_instrument("GBPAUD") is None
    print("PASS\n")


def test_resolve_dukascopy_instrument_returns_none_for_a_genuinely_uncovered_pair():
    print("=== _resolve_dukascopy_instrument: a USD-shaped ticker with no real currency backing it (neither FX_MAJORS nor FX_CROSSES) honestly returns None, never fabricates an instrument identifier ===")
    assert dukascopy_feed._resolve_dukascopy_instrument("ZZZUSD") is None
    print("PASS\n")


if __name__ == "__main__":
    test_get_price_at_returns_first_tick_price()
    test_get_price_at_returns_none_on_empty_window()
    test_get_price_at_returns_none_on_fetch_exception()
    test_get_price_at_rejects_a_genuinely_unmapped_instrument()
    test_resolve_dukascopy_instrument_hits_the_static_map_first()
    test_resolve_dukascopy_instrument_derives_a_real_usd_legged_fx_pair_never_hand_entered()
    test_resolve_dukascopy_instrument_returns_none_for_a_real_fx_cross_no_usd_leg()
    test_resolve_dukascopy_instrument_returns_none_for_a_genuinely_uncovered_pair()
    print("All dukascopy_feed tests passed.")
