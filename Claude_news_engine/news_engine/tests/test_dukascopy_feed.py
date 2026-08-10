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


def test_get_price_at_rejects_unmapped_instrument():
    print("=== dukascopy_feed: get_price_at raises a clear ValueError for an instrument with no Dukascopy mapping ===")
    when = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
    try:
        dukascopy_feed.get_price_at("EURUSD", when)
        raise AssertionError("expected ValueError for an unmapped instrument")
    except ValueError as e:
        assert "EURUSD" in str(e)
    print("PASS\n")


if __name__ == "__main__":
    test_get_price_at_returns_first_tick_price()
    test_get_price_at_returns_none_on_empty_window()
    test_get_price_at_returns_none_on_fetch_exception()
    test_get_price_at_rejects_unmapped_instrument()
    print("All dukascopy_feed tests passed.")
