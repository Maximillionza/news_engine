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


def _resolve_event_ticker(series_ticker: str, event_month: dt.date) -> Optional[str]:
    """
    Finds the series' current event ticker. Kalshi's event tickers embed
    the target month (e.g. KXCPI-26AUG for August 2026's CPI print), but
    the exact naming isn't guaranteed stable across series, so this reads
    whichever event the series' /events endpoint currently returns as the
    first (most relevant) entry rather than constructing the ticker by
    hand. Returns None if the series has no current event.
    """
    resp = requests.get(f"{KALSHI_BASE_URL}/series/{series_ticker}/events", timeout=15)
    resp.raise_for_status()
    events = resp.json().get("events", [])
    if not events:
        return None
    return events[0]["event_ticker"]


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
            params={"series_ticker": series_ticker, "status": "open"},
            timeout=15,
        )
        resp.raise_for_status()
        markets = resp.json().get("markets", [])
        if not markets:
            return None

        nearest = min(
            markets,
            key=lambda m: (round(abs(float(m["floor_strike"]) - target_strike), 10), float(m["floor_strike"])),
        )
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
            open_interest=float(nearest["open_interest_fp"]),
        )
    except Exception as exc:  # noqa: BLE001 — a failed fetch/parse must degrade to None, never crash the caller
        print(f"[kalshi_feed] WARNING: fetch failed for {series_ticker}: {exc}")
        return None
