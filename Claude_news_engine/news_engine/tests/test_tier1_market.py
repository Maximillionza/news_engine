"""
Tests for webapp/tier1_market.py (B12 T10): the market-implied Tier 1 call from a Kalshi "above strike" ladder.
No network; the ladders copy the live 2026-10-28 shapes and the backtest DB is in-memory.
"""
import datetime as dt

import pytest

from config.settings import EVENT_SURPRISE_DIRECTION
from data_layer.kalshi_feed import KalshiLadder, KalshiStrike
from data_layer.tier1_events import TIER1_MARKET_IMPLIED_CONFIDENCE, TIER1_MARKET_IMPLIED_SOURCE
from scoring import backtest_store as bs
from webapp import tier1_market as tm

UTC = dt.timezone.utc
NFP_RELEASE = dt.datetime(2026, 11, 6, 13, 30, tzinfo=UTC)
NOW = dt.datetime(2026, 10, 28, 5, 0, tzinfo=UTC)


def _ladder(event_ticker: str, rows: list) -> KalshiLadder:
    """rows: (strike, yes_bid, yes_ask, open_interest), ascending."""
    return KalshiLadder(event_ticker, tuple(KalshiStrike(float(s), b, a, float(oi)) for s, b, a, oi in rows))


def _mid_ladder(event_ticker: str, points: list) -> KalshiLadder:
    """A liquid ladder whose midpoints are exactly the given probabilities (bid = ask = p)."""
    return _ladder(event_ticker, [(s, p, p, 100.0) for s, p in points])


# Live 2026-10-28 KXPAYROLLS-26OCT (strikes in jobs): midpoint 0.50 exactly at 70000.
PAYROLLS = _ladder("KXPAYROLLS-26OCT", [
    (-25000, 0.91, 0.94, 3784.9), (0, 0.84, 0.88, 2110.18), (10000, 0.79, 0.84, 1398.0),
    (20000, 0.71, 0.75, 11773.13), (30000, 0.63, 0.71, 21090.11), (40000, 0.57, 0.67, 10595.0),
    (50000, 0.55, 0.59, 20239.13), (60000, 0.50, 0.58, 1324.3), (70000, 0.49, 0.51, 23497.53),
    (80000, 0.38, 0.44, 13519.32), (90000, 0.32, 0.37, 2257.0), (100000, 0.24, 0.26, 2565.47),
    (125000, 0.12, 0.17, 2238.0),
])
# Live 2026-10-28 KXUSRETAIL-26NOV17: only -0.2, 0 and 0.4 are liquid and all three sit above 50%.
RETAIL = _ladder("KXUSRETAIL-26NOV17", [
    (-0.4, 0.85, 0.94, 1.02), (-0.2, 0.80, 0.89, 100.0), (0.0, 0.67, 0.76, 50.0), (0.2, 0.58, 0.66, 0.0),
    (0.4, 0.50, 0.59, 18.0), (0.6, 0.35, 0.43, 0.0), (0.8, 0.20, 0.29, 0.0), (1.0, 0.08, 0.16, 0.56),
    (1.2, 0.02, 0.11, 0.0), (1.4, 0.0, 0.08, 0.0), (1.6, 0.0, 0.07, 0.0),
])
GDP = _mid_ladder("KXGDP-26OCT30", [(2.5, 0.655), (3.0, 0.55), (3.5, 0.21), (4.0, 0.035)])


# --- the rule --------------------------------------------------------------------------------------

def test_implied_median_continuous_interpolates():
    assert tm.implied_median([(2.5, 0.655), (3.0, 0.55), (3.5, 0.21), (4.0, 0.035)], False) == pytest.approx(
        3.0735, abs=1e-4)


def test_implied_median_discrete_takes_the_first_strike_at_or_below_half():
    # A fully priced hike: interpolating would give 4.11 and a false "cooler" vs a 4.25% forecast.
    assert tm.implied_median([(3.75, 0.975), (4.0, 0.81), (4.25, 0.085), (4.5, 0.03)], True) == 4.25
    assert tm.implied_median([(3.75, 0.995), (4.0, 0.055)], True) == 4.0


def test_implied_median_none_without_a_crossing():
    assert tm.implied_median([(1.0, 0.9), (2.0, 0.7), (3.0, 0.51)], False) is None    # all above 50%
    assert tm.implied_median([(1.0, 0.5), (2.0, 0.3)], False) is None                  # all at or below
    assert tm.implied_median([(1.0, 0.9)], False) is None                              # one point
    assert tm.implied_median([], True) is None


def test_survival_points_drop_illiquid_strikes_and_force_monotone():
    ladder = _ladder("KXTEST-26OCT", [
        (0.5, 0.80, 0.80, 0.0),     # no open interest
        (1.0, 0.70, 0.70, 50.0),
        (1.5, 0.00, 0.00, 50.0),    # no ask
        (2.0, 0.40, 0.40, 50.0),
        (2.5, 0.30, 0.60, 50.0),    # spread 0.30
        (3.0, 0.60, 0.60, 50.0),    # P(above 3) > P(above 2): impossible, clipped to 0.4
        (4.0, 0.10, 0.10, 50.0),
    ])
    points = tm.survival_points(ladder, 1.0)
    assert points == [(1.0, 0.70), (2.0, 0.40), (3.0, 0.40), (4.0, 0.10)]
    assert tm.implied_median(points, False) == pytest.approx(1.6667, abs=1e-4)
    # Exactly at the liquidity floor (OI 10, spread 0.25) still counts.
    edge = _ladder("KXTEST-26OCT", [(1.0, 0.50, 0.75, 10.0)])
    assert tm.survival_points(edge, 1.0) == [(1.0, 0.625)]
    assert tm.MIN_OPEN_INTEREST == 10.0 and tm.MAX_SPREAD == 0.25


def test_market_call_divides_payroll_strikes_to_thousands():
    call, reason = tm.market_call("Non-Farm Employment Change", PAYROLLS, "50K")
    assert reason is None
    assert call == tm.MarketCall("KXPAYROLLS-26OCT", pytest.approx(70.0), 1, 13)
    text = tm.market_value_text(call, "50K", NOW)
    assert "implied median 70.0000 vs forecast 50K: hotter than forecast" in text
    assert text.startswith("Kalshi KXPAYROLLS-26OCT implied median ")
    assert "(13 liquid strikes, read 2026-10-28 07:00 SAST)" in text
    assert tm.implied_in_value_text(text) == 70.0
    assert tm.implied_in_value_text("CME FedWatch (via FXStreet): 91% hold") is None
    assert tm.implied_key_in_value_text(text) == (70.0, "50K")
    assert tm.implied_key_in_value_text("CME FedWatch (via FXStreet): 91% hold") is None


def test_market_call_continuous_gdp_and_discrete_fed():
    call, reason = tm.market_call("Advance GDP q/q", GDP, "3.2%")
    assert reason is None and call.implied_value == pytest.approx(3.0735, abs=1e-4) and call.side == -1
    fed = _mid_ladder("KXFED-26DEC", [(3.75, 0.975), (4.0, 0.81), (4.25, 0.085), (4.5, 0.03)])
    call, reason = tm.market_call("Federal Funds Rate", fed, "4.25%")
    assert reason is None and call.implied_value == 4.25 and call.side == 0


def test_market_call_refuses_a_forecast_far_outside_the_ladder():
    call, reason = tm.market_call("Retail Sales m/m", RETAIL, "40%")
    assert call is None and "units" in reason


def test_market_call_no_crossing_is_no_call():
    assert tm.market_call("Retail Sales m/m", RETAIL, "0.3%") == (None, "no 50% crossing among liquid strikes")
    assert tm.market_call("Retail Sales m/m", RETAIL, None) == (None, tm.NO_FORECAST)
    assert tm.market_call("Retail Sales m/m", RETAIL, "n/a") == (None, tm.NO_FORECAST)
    assert tm.NO_FORECAST == "no readable forecast yet"
    empty = _ladder("KXUSRETAIL-26NOV17", [(0.2, 0.58, 0.66, 0.0)])
    assert tm.market_call("Retail Sales m/m", empty, "0.3%") == (None, "no 50% crossing among liquid strikes")


def test_market_call_one_or_two_liquid_strikes_is_no_crossing_not_units():
    # B12 review: the units guard used to span the liquid strikes only; one liquid strike (span 0) refused any
    # off-strike forecast as a "units mismatch". The guard now spans every listed strike.
    one_liquid = _ladder("KXUSPPI-26NOV13", [
        (-0.2, 0.90, 0.99, 0.0), (0.0, 0.80, 0.95, 0.0), (0.2, 0.60, 0.64, 500.0), (0.4, 0.20, 0.45, 0.0),
        (0.6, 0.05, 0.30, 0.0)])
    assert tm.market_call("PPI m/m", one_liquid, "0.3%") == (None, tm.NO_CROSSING)
    # Two adjacent liquid strikes with a real crossing and a forecast just outside them: a call, not a refusal.
    narrow = _ladder("KXUSPPI-26NOV13", [
        (-0.2, 0.90, 0.99, 0.0), (0.0, 0.80, 0.95, 0.0), (0.2, 0.60, 0.62, 500.0), (0.3, 0.40, 0.42, 500.0),
        (0.6, 0.05, 0.30, 0.0)])
    call, reason = tm.market_call("PPI m/m", narrow, "0.5%")
    assert reason is None and call.implied_value == pytest.approx(0.255) and call.side == -1
    # A one-strike ladder has no span to judge units by: no crossing.
    single = _ladder("KXUSPPI-26NOV13", [(0.2, 0.60, 0.62, 500.0)])
    assert tm.market_call("PPI m/m", single, "0.3%") == (None, tm.NO_CROSSING)
    # A real units mismatch against the full ladder is still refused.
    call, reason = tm.market_call("PPI m/m", narrow, "30%")
    assert call is None and "units" in reason and "[-0.2, 0.6]" in reason


def test_market_direction():
    assert tm.market_direction("Federal Funds Rate", 1, "XAUUSD") == "bearish"
    assert tm.market_direction("Federal Funds Rate", 1, "USDJPY") == "bullish"
    assert tm.market_direction("Federal Funds Rate", 0, "XAUUSD") == "neutral"
    assert tm.market_direction("Advance GDP q/q", -1, "XAUUSD") == "bullish"


def test_market_series_signs_match_the_shared_map():
    for title in ("Non-Farm Employment Change", "Retail Sales m/m", "PPI m/m", "ISM Manufacturing PMI"):
        assert tm.MARKET_SERIES[title].surprise_direction == EVENT_SURPRISE_DIRECTION[title]
    assert set(tm.MARKET_SERIES) == {"Non-Farm Employment Change", "Retail Sales m/m", "PPI m/m",
                                     "ISM Manufacturing PMI", "Advance GDP q/q", "Federal Funds Rate"}
    assert tm.MARKET_SERIES["Federal Funds Rate"] == tm.MarketSeries("KXFED", "meeting_month", 1.0, True,
                                                                     "higher_bullish")
    assert tm.MARKET_SERIES["Non-Farm Employment Change"].strike_divisor == 1000.0
    assert {s.ticketing for s in tm.MARKET_SERIES.values()} <= {"reference_month", "meeting_month",
                                                                "release_date"}
    assert [t for t, s in tm.MARKET_SERIES.items() if s.discrete] == ["Federal Funds Rate"]


# --- record_market_calls ---------------------------------------------------------------------------

def _rows(bt) -> list:
    return bt.execute("SELECT * FROM tier1_predictions ORDER BY id").fetchall()


def test_record_market_calls_writes_once_per_median():
    bt = bs.get_connection(":memory:")
    call, _ = tm.market_call("Non-Farm Employment Change", PAYROLLS, "50K")
    first = tm.record_market_calls(bt, "Non-Farm Employment Change", NFP_RELEASE, call, "50K",
                                   ["XAUUSD", "US30"], NOW)
    assert first == {"written": [("XAUUSD", "bearish"), ("US30", "bearish")], "unchanged": []}
    rows = _rows(bt)
    assert len(rows) == 2
    for row in rows:
        assert row["source"] == TIER1_MARKET_IMPLIED_SOURCE == "Kalshi market-implied"
        assert row["confidence"] == TIER1_MARKET_IMPLIED_CONFIDENCE == "Likely"
        assert dt.datetime.fromisoformat(row["logged_at_utc"]) == NOW
        assert dt.datetime.fromisoformat(row["event_time_utc"]) == NFP_RELEASE
        assert row["predicted_direction"] == "bearish"

    again = tm.record_market_calls(bt, "Non-Farm Employment Change", NFP_RELEASE, call, "50K",
                                   ["XAUUSD", "US30"], NOW + dt.timedelta(days=1))
    assert again == {"written": [], "unchanged": ["XAUUSD", "US30"]}
    assert len(_rows(bt)) == 2

    moved = tm.MarketCall("KXPAYROLLS-26OCT", 64.5, 1, 13)
    later = tm.record_market_calls(bt, "Non-Farm Employment Change", NFP_RELEASE, moved, "50K",
                                   ["XAUUSD", "US30"], NOW + dt.timedelta(days=2))
    assert [s for s, _ in later["written"]] == ["XAUUSD", "US30"] and later["unchanged"] == []
    assert len(_rows(bt)) == 4
    latest = bs.get_latest_tier1_prediction_for_occurrence(bt, "Non-Farm Employment Change", "XAUUSD",
                                                            NFP_RELEASE)
    assert tm.implied_in_value_text(latest.value) == 64.5


def test_record_market_calls_revised_forecast_under_an_unchanged_median_writes_a_new_row():
    # Review finding (B12 T3): the Fed Funds median sits on one 25 bp step for weeks while the consensus moves;
    # keyed on the median alone, the revised forecast never reached the table and 'hotter' stayed on record.
    bt = bs.get_connection(":memory:")
    fed = _mid_ladder("KXFED-26DEC", [(3.75, 0.975), (4.0, 0.81), (4.25, 0.085), (4.5, 0.03)])
    call, reason = tm.market_call("Federal Funds Rate", fed, "4.00%")
    assert reason is None and call.implied_value == 4.25 and call.side == 1
    first = tm.record_market_calls(bt, "Federal Funds Rate", NFP_RELEASE, call, "4.00%", ["XAUUSD"], NOW)
    assert first == {"written": [("XAUUSD", "bearish")], "unchanged": []}

    revised_call, _ = tm.market_call("Federal Funds Rate", fed, "4.25%")
    assert revised_call.implied_value == call.implied_value and revised_call.side == 0
    revised = tm.record_market_calls(bt, "Federal Funds Rate", NFP_RELEASE, revised_call, "4.25%", ["XAUUSD"],
                                     NOW + dt.timedelta(days=1))
    assert revised == {"written": [("XAUUSD", "neutral")], "unchanged": []}
    assert len(_rows(bt)) == 2
    latest = bs.get_latest_tier1_prediction_for_occurrence(bt, "Federal Funds Rate", "XAUUSD", NFP_RELEASE)
    assert latest.predicted_direction == "neutral"
    assert "vs forecast 4.25%: in line with forecast" in latest.value
    assert tm.implied_key_in_value_text(latest.value) == (4.25, "4.25%")

    again = tm.record_market_calls(bt, "Federal Funds Rate", NFP_RELEASE, revised_call, "4.25%", ["XAUUSD"],
                                   NOW + dt.timedelta(days=2))
    assert again == {"written": [], "unchanged": ["XAUUSD"]}


def test_record_market_calls_ignores_a_judgment_row_for_the_dedupe():
    bt = bs.get_connection(":memory:")
    call, _ = tm.market_call("Non-Farm Employment Change", PAYROLLS, "50K")
    # A judgment row whose text happens to look like a Kalshi value must not count as the Kalshi row.
    bs.record_tier1_prediction(bt, "Non-Farm Employment Change", "XAUUSD", NFP_RELEASE,
                               tm.market_value_text(call, "50K", NOW), "Guessing", "LLM research", "bearish",
                               logged_at_utc=NOW - dt.timedelta(days=1))
    got = tm.record_market_calls(bt, "Non-Farm Employment Change", NFP_RELEASE, call, "50K", ["XAUUSD"], NOW)
    assert got == {"written": [("XAUUSD", "bearish")], "unchanged": []}


def test_record_market_calls_refuses_after_release():
    bt = bs.get_connection(":memory:")
    call, _ = tm.market_call("Non-Farm Employment Change", PAYROLLS, "50K")
    with pytest.raises(ValueError):
        tm.record_market_calls(bt, "Non-Farm Employment Change", NFP_RELEASE, call, "50K", ["XAUUSD"],
                               NFP_RELEASE + dt.timedelta(minutes=1))
    with pytest.raises(ValueError):
        tm.record_market_calls(bt, "Non-Farm Employment Change", NFP_RELEASE, call, "50K", ["XAUUSD"],
                               NOW.replace(tzinfo=None))
    assert _rows(bt) == []
    dry = tm.record_market_calls(None, "Non-Farm Employment Change", NFP_RELEASE, call, "50K",
                                 ["XAUUSD", "USDJPY"], NOW, dry_run=True)
    assert dry == {"written": [("XAUUSD", "bearish"), ("USDJPY", "bullish")], "unchanged": []}
