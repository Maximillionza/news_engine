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


def _fake_multi_events_response(*event_tickers):
    return {"events": [{"event_ticker": t} for t in event_tickers]}


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


def test_get_market_read_returns_none_when_open_interest_below_floor():
    print("=== kalshi_feed: get_market_read returns None when the nearest strike's open_interest_fp is below MIN_KALSHI_OPEN_INTEREST ===")
    strikes_response = _fake_markets_response([
        (0.2, "0.60", "0.70", str(kalshi_feed.MIN_KALSHI_OPEN_INTEREST - 1)),  # below the floor
    ])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXCPI-26AUG")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.2)
        assert result is None
    print("PASS\n")


def test_get_market_read_uses_strike_exactly_at_open_interest_floor():
    print("=== kalshi_feed: get_market_read uses the nearest strike when open_interest_fp is exactly AT MIN_KALSHI_OPEN_INTEREST (at/above floor -> used) ===")
    strikes_response = _fake_markets_response([
        (0.2, "0.60", "0.70", str(kalshi_feed.MIN_KALSHI_OPEN_INTEREST)),  # exactly at the floor
    ])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXCPI-26AUG")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.2)
        assert result is not None
        assert result.open_interest == kalshi_feed.MIN_KALSHI_OPEN_INTEREST
    print("PASS\n")


def test_get_market_read_selects_event_matching_event_month_among_multiple():
    print("=== kalshi_feed: get_market_read selects the event whose ticker matches event_month when multiple events are open at once ===")
    strikes_response = _fake_markets_response([
        (0.2, "0.60", "0.70", "80"),
    ])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_multi_events_response("KXCPI-26AUG", "KXCPI-26SEP")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.2)
        assert result is not None
        markets_call_params = mock_get.call_args_list[1].kwargs["params"]
        assert markets_call_params["event_ticker"] == "KXCPI-26AUG"
    print("PASS\n")


def test_get_market_read_returns_none_when_no_event_matches_event_month():
    print("=== kalshi_feed: get_market_read returns None when no open event matches the requested event_month ===")
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_multi_events_response("KXCPI-26SEP", "KXCPI-26OCT")),
        ]
        result = kalshi_feed.get_market_read("KXCPI", dt.date(2026, 8, 1), target_strike=0.2)
        assert result is None
        # Only the /events call should have happened — no /markets fetch
        # for a month that was never resolved to an event ticker.
        assert mock_get.call_count == 1
    print("PASS\n")


def test_get_market_read_returns_none_on_strike_unit_mismatch():
    print("=== kalshi_feed: get_market_read returns None when target_strike is wildly outside all floor_strike values (simulated units mismatch) ===")
    # Simulates a K-suffix forecast (e.g. "175K" -> 175000.0) hitting a
    # market whose floor_strike values are actually already in thousands.
    strikes_response = _fake_markets_response([
        (100, "0.40", "0.50", "50"),
        (200, "0.40", "0.50", "50"),
        (300, "0.40", "0.50", "50"),
    ])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXPAYROLLS-26AUG")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXPAYROLLS", dt.date(2026, 8, 1), target_strike=175000.0)
        assert result is None
    print("PASS\n")


def test_get_market_read_does_not_reject_target_strike_near_ladder_edge():
    print("=== kalshi_feed: get_market_read does NOT falsely reject a target_strike near the edge of a realistically-spaced strike ladder ===")
    # Realistic NFP-style strike ladder (25K spacing), forecast landing
    # right at the top edge of the ladder — must still produce a real read.
    strikes_response = _fake_markets_response([
        (100000, "0.40", "0.50", "50"),
        (125000, "0.40", "0.50", "50"),
        (150000, "0.40", "0.50", "50"),
        (175000, "0.60", "0.70", "80"),  # top of the ladder, nearest to target
    ])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXPAYROLLS-26AUG")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read("KXPAYROLLS", dt.date(2026, 8, 1), target_strike=175000.0)
        assert result is not None
        assert result.strike == 175000.0
    print("PASS\n")


def test_get_market_read_fetches_events_with_series_ticker_as_query_param():
    print("=== kalshi_feed: get_market_read fetches /events with series_ticker as a query param, not a /series/{ticker}/events path ===")
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
        # Verify the first call (events fetch) hits the plain /events endpoint
        # with series_ticker passed as a query param, not baked into the path.
        events_call = mock_get.call_args_list[0]
        events_call_url = events_call.args[0] if events_call.args else events_call.kwargs.get("url")
        assert events_call_url == f"{kalshi_feed.KALSHI_BASE_URL}/events"
        assert "/series/" not in events_call_url
        events_call_params = events_call.kwargs["params"]
        assert events_call_params == {"series_ticker": "KXCPI"}
    print("PASS\n")


def test_resolve_event_ticker_by_date_matches_exact_date():
    print("=== R4: get_market_read_by_date resolves a date-ticketed event on an exact date match ===")
    strikes_response = _fake_markets_response([(0.2, "0.60", "0.70", "80")])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_multi_events_response("KXUSRETAIL-26JUL16", "KXUSRETAIL-26AUG14")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read_by_date("KXUSRETAIL", dt.date(2026, 8, 14), target_strike=0.2)
        assert result is not None
        markets_call_params = mock_get.call_args_list[1].kwargs["params"]
        assert markets_call_params["event_ticker"] == "KXUSRETAIL-26AUG14"
    print("PASS\n")


def test_resolve_event_ticker_by_date_falls_back_to_one_day_tolerance():
    print("=== R4: get_market_read_by_date falls back to +/-1 day when no event matches the exact date ===")
    strikes_response = _fake_markets_response([(0.2, "0.60", "0.70", "80")])
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        # Ticket dated one day AFTER the requested date — the exact-date
        # pass finds nothing, the tolerance pass should still resolve it.
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXUSRETAIL-26AUG15")),
            _fake_response(strikes_response),
        ]
        result = kalshi_feed.get_market_read_by_date("KXUSRETAIL", dt.date(2026, 8, 14), target_strike=0.2)
        assert result is not None
        markets_call_params = mock_get.call_args_list[1].kwargs["params"]
        assert markets_call_params["event_ticker"] == "KXUSRETAIL-26AUG15"
    print("PASS\n")


def test_resolve_event_ticker_by_date_fails_closed_with_no_match():
    print("=== R4: get_market_read_by_date returns None (fail closed) when nothing matches within tolerance ===")
    with patch.object(kalshi_feed.requests, "get") as mock_get:
        mock_get.side_effect = [
            _fake_response(_fake_events_response("KXUSRETAIL-26SEP16")),  # far outside +/-1 day
        ]
        result = kalshi_feed.get_market_read_by_date("KXUSRETAIL", dt.date(2026, 8, 14), target_strike=0.2)
        assert result is None
        assert mock_get.call_count == 1  # never reached the /markets fetch
    print("PASS\n")


if __name__ == "__main__":
    test_get_market_read_picks_nearest_strike_and_computes_midpoint()
    test_get_market_read_discretizes_higher_lower_in_line()
    test_get_market_read_tie_break_picks_lower_strike()
    test_get_market_read_returns_none_when_no_events()
    test_get_market_read_returns_none_when_no_markets()
    test_get_market_read_returns_none_on_request_failure()
    test_get_market_read_filters_markets_by_event_ticker_not_series_ticker()
    test_get_market_read_returns_none_when_open_interest_below_floor()
    test_get_market_read_uses_strike_exactly_at_open_interest_floor()
    test_get_market_read_selects_event_matching_event_month_among_multiple()
    test_get_market_read_returns_none_when_no_event_matches_event_month()
    test_get_market_read_returns_none_on_strike_unit_mismatch()
    test_get_market_read_does_not_reject_target_strike_near_ladder_edge()
    test_get_market_read_fetches_events_with_series_ticker_as_query_param()
    test_resolve_event_ticker_by_date_matches_exact_date()
    test_resolve_event_ticker_by_date_falls_back_to_one_day_tolerance()
    test_resolve_event_ticker_by_date_fails_closed_with_no_match()
    print("All kalshi_feed tests passed.")
