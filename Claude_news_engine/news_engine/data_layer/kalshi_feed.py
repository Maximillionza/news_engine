"""
Thin, read-only HTTP client for Kalshi's free, unauthenticated public
market-data API (external-api.kalshi.com/trade-api/v2) — confirmed live
this session: no API key needed for GET /events, /markets. Mirrors
data_layer/dukascopy_feed.py's shape: contains the third-party API's
response structure to this one file, callers only ever see KalshiRead
(or, for B12's market-implied Tier 1, a whole KalshiLadder).

READ-ONLY. This module never authenticates, never places or cancels an
order, never touches Kalshi's trading endpoints — only the public market-
data reads (GET /events?series_ticker=..., GET /markets).
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


class KalshiFetchError(RuntimeError):
    """get_ladder could not read Kalshi (HTTP, JSON or response-shape error) - a skip, not a 'no market'."""


@dataclass(frozen=True)
class KalshiStrike:
    strike: float          # floor_strike as Kalshi lists it (KXPAYROLLS in jobs, the rest in the print's unit)
    yes_bid: float         # 0.0-1.0
    yes_ask: float         # 0.0-1.0; 0 means nobody is offering
    open_interest: float


@dataclass(frozen=True)
class KalshiLadder:
    event_ticker: str
    strikes: tuple[KalshiStrike, ...]   # ascending by strike


# How a series tickets its events (live-verified 2026-10-28, see get_ladder).
LADDER_TICKETING: tuple[str, ...] = ("reference_month", "meeting_month", "release_date")


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
    resp = requests.get(f"{KALSHI_BASE_URL}/events", params={"series_ticker": series_ticker}, timeout=15)
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


def _resolve_event_ticker_by_date(series_ticker: str, event_date: dt.date) -> Optional[str]:
    """
    R4 (docs/fundamental-analysis-swot-2026-08-14.md): companion to
    _resolve_event_ticker() for the series that ticket a specific
    RELEASE DATE rather than a month — live-verified 2026-08-14:
    KXUSRETAIL, KXJOBLESSCLAIMS, KXGDP, KXCHCUTS, KXUSPPI, KXUSMICHCSP all
    genuinely use a `-{yy}{MON}{DD}` suffix (e.g. "KXUSRETAIL-26AUG14"),
    unlike KXFED which this same live check showed is actually
    MONTH-ticketed (see _resolve_event_ticker() instead — config.settings'
    prior "KXFED is date-ticketed" claim was wrong).

    Matches the exact date first; if nothing matches, retries at ±1 day —
    a defensive tolerance for any release-date/ticket-date edge (e.g. a
    late-in-day UTC release landing on the "wrong" calendar date relative
    to Kalshi's own date anchor). Logs which one matched. Returns None —
    fail closed, never guess — if neither the exact date nor either
    adjacent day has a matching event.
    """
    resp = requests.get(f"{KALSHI_BASE_URL}/events", params={"series_ticker": series_ticker}, timeout=15)
    resp.raise_for_status()
    events = resp.json().get("events", [])
    if not events:
        return None

    def _suffix_for(d: dt.date) -> str:
        return f"-{d.strftime('%y').upper()}{_MONTH_ABBREVIATIONS[d.month - 1]}{d.day:02d}"

    for candidate_date, note in (
        (event_date, "exact date"),
        (event_date - dt.timedelta(days=1), "1-day-back tolerance"),
        (event_date + dt.timedelta(days=1), "1-day-forward tolerance"),
    ):
        expected_suffix = _suffix_for(candidate_date)
        for event in events:
            ticker = event.get("event_ticker", "")
            if ticker.upper().endswith(expected_suffix):
                if note != "exact date":
                    print(f"[kalshi_feed] NOTE: {series_ticker} matched via {note} ({ticker})")
                return ticker
    return None


def _read_market_for_event_ticker(event_ticker: str, target_strike: float) -> Optional[KalshiRead]:
    """
    Shared tail of get_market_read()/get_market_read_by_date(): given an
    already-resolved event_ticker, fetches its markets, finds the strike
    closest to target_strike, reads that market's yes_bid/yes_ask midpoint
    and open_interest. Returns None — never fabricated — if the market
    list is empty or the request fails for any reason.

    Tie-break: when target_strike is exactly equidistant between two
    strikes, the LOWER strike wins, deterministically.
    """
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
            f"the strike range [{strike_min}, {strike_max}] for event {event_ticker} "
            f"— likely a units mismatch, refusing to guess"
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


def get_market_read(series_ticker: str, event_month: dt.date, target_strike: float) -> Optional[KalshiRead]:
    """
    Fetches the series' current MONTH-ticketed event (see
    _resolve_event_ticker()) and reads the nearest-strike market. Returns
    None — never fabricated — if the series/event/market doesn't exist,
    or the request fails for any reason (network error, malformed
    response, unexpected shape).
    """
    try:
        event_ticker = _resolve_event_ticker(series_ticker, event_month)
        if event_ticker is None:
            return None
        return _read_market_for_event_ticker(event_ticker, target_strike)
    except Exception as exc:  # noqa: BLE001 — a failed fetch/parse must degrade to None, never crash the caller
        print(f"[kalshi_feed] WARNING: fetch failed for {series_ticker}: {exc}")
        return None


def get_market_read_by_date(series_ticker: str, event_date: dt.date, target_strike: float) -> Optional[KalshiRead]:
    """
    R4: same contract as get_market_read(), for the DATE-ticketed series
    (see _resolve_event_ticker_by_date()'s docstring for which ones those
    are and why they're a separate resolution path from the month-ticketed
    ones).
    """
    try:
        event_ticker = _resolve_event_ticker_by_date(series_ticker, event_date)
        if event_ticker is None:
            return None
        return _read_market_for_event_ticker(event_ticker, target_strike)
    except Exception as exc:  # noqa: BLE001 — a failed fetch/parse must degrade to None, never crash the caller
        print(f"[kalshi_feed] WARNING: date-ticketed fetch failed for {series_ticker}: {exc}")
        return None


def _month_before(release_utc: dt.datetime) -> dt.date:
    """First day of the month before the release's (UTC) month: the reference month of a monthly print."""
    first = release_utc.date().replace(day=1)
    return (first - dt.timedelta(days=1)).replace(day=1)


def get_ladder(series_ticker: str, ticketing: str, release_utc: dt.datetime) -> Optional[KalshiLadder]:
    """
    B12 (T10): the whole open strike ladder of the event that resolves on this release, for the
    market-implied Tier 1 rule (webapp/tier1_market.py). How the event is found depends on how the
    series tickets it (live-verified 2026-10-28):
      reference_month - the month the print measures, i.e. the month before the release
                        (KXPAYROLLS-26OCT settles on the Oct jobs report released 2026-11-06; KXISMPMI);
      meeting_month   - the release's own month (KXFED-26DEC is the 2026-12-09 FOMC decision);
      release_date    - the release date, with _resolve_event_ticker_by_date's +/-1 day tolerance
                        (KXGDP-26OCT30 for a 2026-10-29 release; KXUSPPI, KXUSRETAIL).
    Then GET /markets {event_ticker, status=open}.

    Returns None when no event matches or the event has no open markets (no market = no call). Unlike
    get_market_read it does NOT swallow failures: an HTTP, JSON or response-shape error raises
    KalshiFetchError, because the capture reports an unreadable source as a skip, not as "no market".
    """
    if ticketing not in LADDER_TICKETING:
        raise ValueError(f"ticketing={ticketing!r} is not valid -- must be one of: {', '.join(LADDER_TICKETING)}")
    try:
        if ticketing == "reference_month":
            event_ticker = _resolve_event_ticker(series_ticker, _month_before(release_utc))
        elif ticketing == "meeting_month":
            event_ticker = _resolve_event_ticker(series_ticker, release_utc.date())
        else:
            event_ticker = _resolve_event_ticker_by_date(series_ticker, release_utc.date())
        if event_ticker is None:
            return None
        resp = requests.get(
            f"{KALSHI_BASE_URL}/markets",
            params={"event_ticker": event_ticker, "status": "open"},
            timeout=15,
        )
        resp.raise_for_status()
        markets = resp.json().get("markets", [])
        strikes = [
            KalshiStrike(
                strike=float(m["floor_strike"]),
                yes_bid=float(m["yes_bid_dollars"]),
                yes_ask=float(m["yes_ask_dollars"]),
                open_interest=float(m["open_interest_fp"]),
            )
            for m in markets
        ]
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as exc:
        # ValueError covers unparseable JSON and non-numeric fields; Key/Type/AttributeError a changed shape.
        raise KalshiFetchError(f"{series_ticker} ({ticketing}) ladder read failed: {exc}") from exc
    if not strikes:
        return None
    return KalshiLadder(event_ticker=event_ticker, strikes=tuple(sorted(strikes, key=lambda s: s.strike)))
