# webapp/tier1_market.py
"""
Market-implied Tier 1 calls (B12 T10): for NFP, Retail Sales, PPI, ISM Manufacturing, Advance GDP and the Fed
Funds decision the pre-release call is a fixed rule on Kalshi's public "above strike" ladder, not researched by
hand. The rule, fixed in advance:
  1. Liquid strikes only: open interest >= MIN_OPEN_INTEREST, a quoted ask, ask - bid <= MAX_SPREAD.
  2. Each strike's yes midpoint is P(print above strike); a running minimum makes it non-increasing in the strike.
  3. The implied median is where that survival curve crosses 50%: linear between the two strikes around the
     crossing, or the first strike at or below 50% for the discrete Fed Funds ladder (rates move in 25 bp steps,
     so interpolating a priced hike lands between two possible outcomes). No crossing = no call.
  4. The median vs the forecast with the Stats tab's tolerance (one rounding step of the forecast's precision)
     -> hotter / in line / cooler, then per instrument through stats_methods.market_lean (buy -> bullish,
     sell -> bearish, mixed -> neutral).
A forecast far outside the liquid strikes (a units mismatch) or no readable forecast is also no call.

Everything here is pure except record_market_calls, which appends to tier1_predictions, at most one row per
(title, release, instrument) per distinct implied median (mirrors webapp/tier1_formula.py).
"""
from __future__ import annotations

import datetime as dt
import re
import sqlite3
from dataclasses import dataclass
from typing import Optional

from config.settings import LOCAL_TZ, MIN_KALSHI_OPEN_INTEREST
from data_layer.kalshi_feed import KalshiLadder
from data_layer.tier1_events import TIER1_MARKET_IMPLIED_CONFIDENCE, TIER1_MARKET_IMPLIED_SOURCE
from scoring.backtest_store import get_latest_tier1_prediction_for_occurrence, record_tier1_prediction
from webapp.stats_methods import market_lean
from webapp.stats_rules import parse_number, side, tolerance
from webapp.tier1_formula import SIDE_LABELS


@dataclass(frozen=True)
class MarketSeries:
    series_ticker: str
    ticketing: str             # kalshi_feed.get_ladder: reference_month | meeting_month | release_date
    strike_divisor: float      # strike / divisor = the forecast's unit (KXPAYROLLS lists jobs, FF prints "50K")
    discrete: bool             # median = first strike at or below 50% instead of interpolating
    surprise_direction: str    # higher_bullish | higher_bearish, passed to market_lean


# Live-verified 2026-10-28 (docs/superpowers/plans/2026-10-28-b12-tier1-expansion.md). Federal Funds Rate and
# Advance GDP q/q have no EVENT_SURPRISE_DIRECTION entry: higher = USD-bullish is the accumulator's own Fed
# convention and Prelim GDP's mapped sign. KXFED is the upper bound of the target range.
MARKET_SERIES: dict[str, MarketSeries] = {
    "Non-Farm Employment Change": MarketSeries("KXPAYROLLS", "reference_month", 1000.0, False, "higher_bullish"),
    "Retail Sales m/m": MarketSeries("KXUSRETAIL", "release_date", 1.0, False, "higher_bullish"),
    "PPI m/m": MarketSeries("KXUSPPI", "release_date", 1.0, False, "higher_bullish"),
    "ISM Manufacturing PMI": MarketSeries("KXISMPMI", "reference_month", 1.0, False, "higher_bullish"),
    "Advance GDP q/q": MarketSeries("KXGDP", "release_date", 1.0, False, "higher_bullish"),
    "Federal Funds Rate": MarketSeries("KXFED", "meeting_month", 1.0, True, "higher_bullish"),
}

MIN_OPEN_INTEREST = MIN_KALSHI_OPEN_INTEREST   # 10.0, the same floor get_market_read uses
MAX_SPREAD = 0.25                              # dollars (= probability points) between yes bid and yes ask
NO_FORECAST = "no readable forecast yet"
NO_CROSSING = "no 50% crossing among liquid strikes"
_EPS = 1e-9   # float noise in bid/ask differences (0.60 - 0.35)

_LEAN_TO_DIRECTION = {"buy": "bullish", "sell": "bearish", "mixed": "neutral"}
# The stored value text opens with the event ticker and the median at 4 decimals; this reads it back for the dedupe.
_IMPLIED_IN_TEXT = re.compile(r"^Kalshi \S+ implied median (-?\d+\.\d{4}) vs forecast ")


@dataclass(frozen=True)
class MarketCall:
    event_ticker: str
    implied_value: float   # in the forecast's unit
    side: int              # +1 hotter, 0 in line, -1 cooler vs the forecast
    liquid_strikes: int


def survival_points(ladder: KalshiLadder, divisor: float) -> list[tuple[float, float]]:
    """
    (strike / divisor, P(above)) for the liquid strikes, ascending, forced non-increasing. KXISMPMI's
    greater_or_equal markets are read as "above": its outcomes step 0.1, so the difference is immaterial.
    """
    liquid = sorted(
        (s.strike / divisor, (s.yes_bid + s.yes_ask) / 2.0)
        for s in ladder.strikes
        if s.open_interest >= MIN_OPEN_INTEREST and s.yes_ask > 0 and s.yes_ask - s.yes_bid <= MAX_SPREAD + _EPS
    )
    points: list[tuple[float, float]] = []
    for strike, prob in liquid:
        # P(above) cannot rise with the strike; a crossed quote is noise, so the lower neighbour's value wins.
        points.append((strike, min(prob, points[-1][1]) if points else prob))
    return points


def implied_median(points: list[tuple[float, float]], discrete: bool) -> Optional[float]:
    """The 50% crossing of the survival curve; None with < 2 points or when the curve never crosses 50%."""
    if len(points) < 2 or points[0][1] <= 0.5 or points[-1][1] > 0.5:
        return None
    for (s0, p0), (s1, p1) in zip(points, points[1:]):
        if p0 > 0.5 >= p1:
            if discrete:
                return s1
            return s0 + (s1 - s0) * (p0 - 0.5) / (p0 - p1)
    return None


def market_call(title: str, ladder: KalshiLadder,
                forecast_text: Optional[str]) -> tuple[Optional[MarketCall], Optional[str]]:
    """(call, None) or (None, reason): no readable forecast, a units mismatch, or no 50% crossing."""
    series = MARKET_SERIES[title]
    forecast = parse_number(forecast_text)
    tol = tolerance(forecast_text)
    if forecast is None or tol is None:
        return None, NO_FORECAST
    points = survival_points(ladder, series.strike_divisor)
    if points:
        # Same guard as get_market_read: a forecast far outside the ladder is a scale mismatch, not a view.
        low, high = points[0][0], points[-1][0]
        span = high - low
        if forecast < low - span / 2 or forecast > high + span / 2:
            return None, (f"forecast {forecast_text} is far outside the liquid strikes [{low:g}, {high:g}] of "
                          f"{ladder.event_ticker}: likely a units mismatch")
    median = implied_median(points, series.discrete)
    if median is None:
        return None, NO_CROSSING
    return MarketCall(ladder.event_ticker, median, side(median, forecast, tol), len(points)), None


def market_direction(title: str, side: int, symbol: str) -> str:
    """bullish / bearish / neutral for one instrument, with the series' own surprise sign."""
    lean = market_lean(title, side, symbol, surprise_direction=MARKET_SERIES[title].surprise_direction)
    return _LEAN_TO_DIRECTION[lean]


def market_value_text(call: MarketCall, forecast_text: str, captured_at_utc: dt.datetime) -> str:
    """The stored Tier 1 value: what the rule read, its verdict, and when (SAST) - readable on the dashboard."""
    return (f"Kalshi {call.event_ticker} implied median {call.implied_value:.4f} vs forecast {forecast_text}: "
            f"{SIDE_LABELS[call.side]} ({call.liquid_strikes} liquid strikes, "
            f"read {captured_at_utc.astimezone(LOCAL_TZ):%Y-%m-%d %H:%M} SAST)")


def implied_in_value_text(text: str) -> Optional[float]:
    """The median a market-implied row was written from; None for any other text (e.g. a FedWatch row)."""
    match = _IMPLIED_IN_TEXT.match(text or "")
    return float(match.group(1)) if match else None


def record_market_calls(bt_conn: Optional[sqlite3.Connection], event_title: str, release_utc: dt.datetime,
                        call: MarketCall, forecast_text: str, symbols: list[str], now_utc: dt.datetime,
                        dry_run: bool = False) -> dict:
    """
    Write the market-implied Tier 1 call for each tracked symbol, stamped logged_at_utc = now_utc.
    Returns {"written": [(symbol, direction)], "unchanged": [symbol]}. A symbol is "unchanged" when its latest
    pre-release Kalshi row already carries this median (at the 4 decimals the text stores); a judgment or
    FedWatch row for the same occurrence does not count. With dry_run every symbol is reported as would-write
    and nothing is read or written (bt_conn may be None).
    """
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise ValueError(f"now_utc must be timezone-aware, got naive {now_utc!r}")
    if now_utc > release_utc:
        # Same rule as record_formula_calls: a call stamped after the print is hindsight.
        raise ValueError(f"now_utc {now_utc.isoformat()} is after the release {release_utc.isoformat()}")
    result: dict = {"written": [], "unchanged": []}
    value = market_value_text(call, forecast_text, now_utc)
    for symbol in symbols:
        direction = market_direction(event_title, call.side, symbol)
        if dry_run:
            result["written"].append((symbol, direction))
            continue
        latest = get_latest_tier1_prediction_for_occurrence(
            bt_conn, event_title, symbol, release_utc, source=TIER1_MARKET_IMPLIED_SOURCE)
        if latest is not None and implied_in_value_text(latest.value) == round(call.implied_value, 4):
            result["unchanged"].append(symbol)
            continue
        record_tier1_prediction(
            bt_conn, event_title, symbol, release_utc, value,
            confidence=TIER1_MARKET_IMPLIED_CONFIDENCE, source=TIER1_MARKET_IMPLIED_SOURCE,
            predicted_direction=direction, logged_at_utc=now_utc,
        )
        result["written"].append((symbol, direction))
    return result
