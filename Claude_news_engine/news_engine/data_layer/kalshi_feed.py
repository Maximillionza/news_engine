"""
Thin, read-only HTTP client for Kalshi's free, unauthenticated public
market-data API (external-api.kalshi.com/trade-api/v2) — confirmed live
this session: no API key needed for GET /events, /markets. Mirrors
data_layer/dukascopy_feed.py's shape: contains the third-party API's
response structure to this one file, callers only ever see KalshiRead.

READ-ONLY. This module never authenticates, never places or cancels an
order, never touches Kalshi's trading endpoints — only the public market-
data reads (GET /markets/{series_ticker}/events, GET /markets).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import requests

from config.settings import MIN_KALSHI_OPEN_INTEREST

KALSHI_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

# Discretization thresholds for the yes-price midpoint (0.0-1.0) into a
# direction call — same three-way shape scoring/print_direction.py's
# score_print_direction() already uses, just fed by a market price
# instead of a lexicon hit-count.
HIGHER_THRESHOLD = 0.55
LOWER_THRESHOLD = 0.45


@dataclass
class KalshiRead:
    strike: float
    implied_direction: str      # 'higher' | 'lower' | 'in_line'
    implied_probability: float  # 0.0-1.0, the yes-price midpoint
    open_interest: float


_MONTH_ABBREVIATIONS = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]


def _resolve_event_ticker(series_ticker: str, event_month: dt.date) -> Optional[str]:
    """
    Finds the series' event ticker for `event_month`. Kalshi's event
    tickers embed the target month (e.g. KXCPI-26AUG for August 2026's CPI
    print) as a 2-digit-year + 3-letter-month suffix after a dash. A
    series can have more than one event open at once (e.g. two months'
    CPI simultaneously) so this filters the /events response for the one
    entry whose ticker ends with the expected `-{YYMON}` suffix rather
    than trusting undocumented response ordering. Returns None if the
    series has no current event, or none of its events match
    `event_month` — fail closed, never guess which occurrence is meant.
    """
    resp = requests.get(f"{KALSHI_BASE_URL}/series/{series_ticker}/events", timeout=15)
    resp.raise_for_status()
    events = resp.json().get("events", [])
    if not events:
        return None

    expected_suffix = f"-{event_month.strftime('%y').upper()}{_MONTH_ABBREVIATIONS[event_month.month - 1]}"
    for event in events:
        ticker = event.get("event_ticker", "")
        if ticker.endswith(expected_suffix):
            return ticker
    return None


def get_market_read(series_ticker: str, event_month: dt.date, target_strike: float) -> Optional[KalshiRead]:
    """
    Fetches the series' current event, finds the strike closest to
    target_strike among its markets, reads that market's yes_bid/yes_ask
    midpoint and open_interest. Returns None — never fabricated — if the
    series/event/market doesn't exist, the market list is empty, or the
    request fails for any reason (network error, malformed response,
    unexpected shape).

    Tie-break: when target_strike is exactly equidistant between two
    strikes, the LOWER strike wins, deterministically.
    """
    try:
        event_ticker = _resolve_event_ticker(series_ticker, event_month)
        if event_ticker is None:
            return None

        resp = requests.get(
            f"{KALSHI_BASE_URL}/markets",
            params={"event_ticker": event_ticker, "status": "open"},
            timeout=15,
        )
        resp.raise_for_status()
        markets = resp.json().get("markets", [])
        if not markets:
            return None

        # Unit-mismatch sanity check: if target_strike (parsed from the FF
        # forecast string, e.g. 175000.0 for "175K") falls way outside the
        # range of floor_strike values Kalshi actually lists, the forecast
        # and the market are almost certainly on different scales (e.g.
        # thousands vs raw units). Without this, nearest-strike selection
        # would silently pick the most extreme strike every time, producing
        # a saturated (near-0/near-1) 'lower'/'higher' call at this
        # system's highest trust weight — a confidently WRONG signal
        # instead of an absent one. Tolerance: the strike range extended by
        # 50% of its own span on either side — generous enough not to
        # false-positive on a real forecast landing near either edge of a
        # normal strike ladder, tight enough to catch an actual
        # order-of-magnitude scale mismatch.
        floor_strikes = [float(m["floor_strike"]) for m in markets]
        strike_min, strike_max = min(floor_strikes), max(floor_strikes)
        span = strike_max - strike_min
        tolerance = span * 0.5
        if target_strike < strike_min - tolerance or target_strike > strike_max + tolerance:
            print(
                f"[kalshi_feed] WARNING: target_strike={target_strike} is far outside "
                f"the strike range [{strike_min}, {strike_max}] for {series_ticker} "
                f"{event_ticker} — likely a units mismatch, refusing to guess"
            )
            return None

        nearest = min(
            markets,
            key=lambda m: (round(abs(float(m["floor_strike"]) - target_strike), 10), float(m["floor_strike"])),
        )
        open_interest = float(nearest["open_interest_fp"])
        if open_interest < MIN_KALSHI_OPEN_INTEREST:
            # Liquidity gate: an illiquid, easily-skewed strike contributes
            # nothing rather than a diluted nudge — same "absent, not
            # fabricated" contract every other failure mode here uses.
            return None

        yes_bid = float(nearest["yes_bid_dollars"])
        yes_ask = float(nearest["yes_ask_dollars"])
        midpoint = (yes_bid + yes_ask) / 2.0

        if midpoint > HIGHER_THRESHOLD:
            direction = "higher"
        elif midpoint < LOWER_THRESHOLD:
            direction = "lower"
        else:
            direction = "in_line"

        return KalshiRead(
            strike=float(nearest["floor_strike"]),
            implied_direction=direction,
            implied_probability=midpoint,
            open_interest=open_interest,
        )
    except Exception as exc:  # noqa: BLE001 — a failed fetch/parse must degrade to None, never crash the caller
        print(f"[kalshi_feed] WARNING: fetch failed for {series_ticker}: {exc}")
        return None
