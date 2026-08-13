"""
Tests for data_layer/kalshi_feed.py — no live network, requests.get is
mocked with synthetic Kalshi API responses.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.kalshi_feed as kalshi_feed


def _fake_response(json_body, status_ok=True):
    resp = MagicMock()
    resp.json.return_value = json_body
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = Exception("HTTP error")
    return resp


def _fake_events_response(event_ticker):
    return {"events": [{"event_ticker": event_ticker}]}


def _fake_markets_response(strikes):
    """strikes: list of (floor_strike, yes_bid, yes_ask, open_interest_fp) tuples."""
    return {
        "markets": [
            {
                "floor_strike": s, "yes_bid_dollars": str(bid), "yes_ask_dollars": str(ask),
                "open_interest_fp": str(oi),
            }
            for s, bid, ask, oi in strikes
        ]
    }


def test_get_market_read_picks_nearest_strike_and_computes_midpoint():
    print("=== kalshi_feed: get_market_read picks the strike nearest target_strike, midpoint = (bid+ask)/2 ===")
    strikes_response = _fake_markets_response([
        (0.1, "0.30", "0.40", "50"),
        (0.2, "0.60", "0.70", "80"),  # nearest to target_strike=0.19
        (0.3, "0.10", "0.20", "60"),
    ])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXCPI-26AUG")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.19)
        assert result is not None
        assert result.strike == 0.2
        assert abs(result.implied_probability - 0.65) < 1e-9  # (0.60+0.70)/2
        assert result.open_interest == 80.0
    print("PASS\n")


def test_get_market_read_discretizes_higher_lower_in_line():
    print("=== kalshi_feed: get_market_read discretizes the midpoint into higher/lower/in_line at the 0.55/0.45 thresholds ===")
    for bid, ask, expected in [("0.60", "0.70", "higher"), ("0.20", "0.30", "lower"), ("0.48", "0.50", "in_line")]:
        strikes_response = _fake_markets_response([(0.1, bid, ask, "50")])
        with patch.object(kalshi_feed.requests, "get") as mock_get:
            mock_get.side_effect = [
                _fake_response(_fake_events_response("KXCPI-26AUG")),
                _fake_response(strikes_response),
            ]
            result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.1)
            assert result.implied_direction == expected, f"bid={bid} ask={ask} expected {expected}, got {result.implied_direction}"
    print("PASS\n")


def test_get_market_read_tie_break_picks_lower_strike():
    print("=== kalshi_feed: an exact midpoint tie between two strikes picks the LOWER one, deterministically ===")
    strikes_response = _fake_markets_response([
        (0.1, "0.40", "0.50", "50"),
        (0.3, "0.40", "0.50", "50"),
    ])  # target_strike=0.2 is exactly equidistant from 0.1 and 0.3
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXCPI-26AUG")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.2)
        assert result.strike == 0.1
    print("PASS\n")


def test_get_market_read_returns_none_when_no_events():
    print("=== kalshi_feed: get_market_read returns None when the series has no current event ===")
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [_fake_response({"events": []})]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.1)
        assert result is None
    print("PASS\n")


def test_get_market_read_returns_none_when_no_markets():
    print("=== kalshi_feed: get_market_read returns None when the event has no markets listed ===")
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXCPI-26AUG")),
            _fake_response({"markets": []}),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.1)
        assert result is None
    print("PASS\n")


def test_get_market_read_returns_none_on_request_failure():
    print("=== kalshi_feed: get_market_read returns None (not a crash) when the request fails ===")
    with patch.object(kalshi_feed.requests, "get", side_effect=Exception("network down")):
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.1)
        assert result is None
    print("PASS\n")


def test_get_market_read_filters_markets_by_event_ticker_not_series_ticker():
    print("=== kalshi_feed: get_market_read filters /markets by event_ticker, not series_ticker, to scope to exactly one event ===")
    strikes_response = _fake_markets_response([
        (0.2, "0.60", "0.70", "80"),
    ])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXCPI-26AUG")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.2)
        assert result is not None
        # Verify the second call (markets fetch) uses event_ticker, not series_ticker
        markets_call_params = mock_get.call_args_list[1].kwargs["params"]
        assert "event_ticker" in markets_call_params
        assert markets_call_params["event_ticker"] == "KXCPI-26AUG"
        assert "series_ticker" not in markets_call_params
        assert markets_call_params["status"] == "open"
    print("PASS\n")


if __name__ == "__main__":
    test_get_market_read_picks_nearest_strike_and_computes_midpoint()
    test_get_market_read_discretizes_higher_lower_in_line()
    test_get_market_read_tie_break_picks_lower_strike()
    test_get_market_read_returns_none_when_no_events()
    test_get_market_read_returns_none_when_no_markets()
    test_get_market_read_returns_none_on_request_failure()
    test_get_market_read_filters_markets_by_event_ticker_not_series_ticker()
    print("All kalshi_feed tests passed.")
