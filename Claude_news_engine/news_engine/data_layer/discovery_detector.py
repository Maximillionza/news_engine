"""
Discovery_Detector_Spec implementation (docs/News_Engine_Causation_Matrix_v2.xlsx):
a statistical anomaly detector over 4 market-wide series, flagging a
real, unexplained daily move so a Tier 1 CPI/PPI prediction's DISPLAYED
confidence (never its stored value, never its direction) can be
downgraded on the live dashboard. See
docs/superpowers/specs/2026-09-11-tier2-tier3-exogenous-context-design.md
for the full design and rationale.
"""
from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass
from typing import Optional

import dukascopy_python
from dukascopy_python.instruments import (
    INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD,
    INSTRUMENT_BND_CFD_USTBOND_TR_USD,
    INSTRUMENT_FX_METALS_XAU_USD,
    INSTRUMENT_IDX_AMERICA_E_D_J_IND,
)

from data_layer.calendar_feed import EconomicEvent, IMPACT_RANK

# Verified 2026-09-11 against dukascopy_python's real instrument catalog
# (1380 entries): 10Y and 30Y Treasury yields do NOT exist as separate
# Dukascopy instruments -- only one generic US T-Bond CFD does. Per
# explicit user decision, merged into one UST_BOND series rather than
# forcing an unsupported 10Y/30Y split. This map is intentionally
# SEPARATE from data_layer/dukascopy_feed.py's own _INSTRUMENT_MAP (that
# one is keyed by this project's tracked-symbol names for the outcome-
# confirmation pipeline; DXY/UST_BOND are not tracked symbols in that sense).
DETECTOR_SERIES = ["DXY", "UST_BOND", "XAUUSD", "US30"]

_DETECTOR_INSTRUMENT_MAP = {
    "DXY": INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD,
    "UST_BOND": INSTRUMENT_BND_CFD_USTBOND_TR_USD,
    "XAUUSD": INSTRUMENT_FX_METALS_XAU_USD,
    "US30": INSTRUMENT_IDX_AMERICA_E_D_J_IND,
}


def compute_daily_move(series: str, date: dt.date) -> Optional[float]:
    """
    Real percentage move from session open to session close for `date`,
    using the same get_price_at() Dukascopy tick fetch
    scoring/outcome_classifier.py already relies on -- no new fetch
    mechanism, just a new instrument map. Session open is UTC 00:00 for
    `date` -- a coarse but real and consistent definition, matching this
    project's existing "before/after" tick convention rather than
    inventing a market-hours-aware session boundary this codebase
    doesn't otherwise track. Session close is resolved by
    _fetch_session_close_tick() below, NOT a fixed 23:59:59 instant (see
    its own docstring for why).

    Returns None -- never fabricated -- if either tick fetch fails for
    any reason (market closed, feed gap, bad tick). Raises ValueError
    for a `series` with no instrument mapping -- that's a caller bug,
    not a data-availability issue, same distinction get_price_at()
    itself already draws for an unmapped tracked-symbol instrument.
    """
    if series not in _DETECTOR_INSTRUMENT_MAP:
        raise ValueError(
            f"series={series!r} has no Dukascopy instrument mapping — "
            f"known series: {DETECTOR_SERIES}"
        )
    instrument = _DETECTOR_INSTRUMENT_MAP[series]
    session_start = dt.datetime.combine(date, dt.time(0, 0), tzinfo=dt.timezone.utc)

    open_price = _fetch_tick(instrument, session_start)
    close_price = _fetch_session_close_tick(instrument, date)
    if open_price is None or close_price is None:
        return None
    return (close_price - open_price) / open_price * 100


# How many 1-hour steps _fetch_session_close_tick walks backward from
# 23:59:59 before giving up. 8 steps reaches 15:59:59 UTC -- comfortable
# margin below the real, documented FX/metals/index-CFD Friday close
# (~21:00-22:00 UTC) while never crossing into the previous calendar day.
_SESSION_CLOSE_BACKWARD_STEPS = 8


def _fetch_session_close_tick(instrument: str, date: dt.date) -> Optional[float]:
    """
    Real fix (2026-09-11, final whole-branch review's Important finding):
    a fixed 23:59:59 UTC close instant assumes the market is still open
    at midnight, which FX/metals/index CFDs are not on a Friday -- they
    close around 21:00-22:00 UTC and don't reopen until Sunday evening.
    Verified live: XAUUSD/DXY on multiple real Friday dates both returned
    None under the old fixed-instant fetch, when a real Friday session
    (and a real close price) genuinely existed.

    Walks backward from 23:59:59 in 1-hour steps, within `date`'s own
    calendar day only (never reaching into the previous day), and
    returns the first real tick found -- the same "coarse but real"
    session-boundary philosophy already used for session open, just no
    longer assuming every market is still open at midnight UTC. A
    genuinely closed day (weekend, market holiday) still correctly
    returns None once every step in the budget has been tried -- this
    never fabricates a close price for a day with no real trading.
    """
    for step in range(_SESSION_CLOSE_BACKWARD_STEPS + 1):
        candidate = dt.datetime.combine(date, dt.time(23, 59, 59), tzinfo=dt.timezone.utc) - dt.timedelta(hours=step)
        price = _fetch_tick(instrument, candidate)
        if price is not None:
            return price
    return None


def _fetch_tick(instrument: str, when_utc: dt.datetime) -> Optional[float]:
    """
    Thin wrapper around dukascopy_python.fetch(), same BID-consistent,
    first-tick-at-or-after convention data_layer/dukascopy_feed.py's
    get_price_at() uses -- duplicated here rather than imported because
    that function's instrument map is keyed by different names (this
    project's tracked symbols, not DETECTOR_SERIES); the fetch mechanics
    themselves are copied verbatim, not reinvented.
    """
    try:
        df = dukascopy_python.fetch(
            instrument, dukascopy_python.INTERVAL_TICK, dukascopy_python.OFFER_SIDE_BID,
            when_utc, when_utc + dt.timedelta(minutes=5),
        )
        if df is None or df.empty:
            return None
        return float(df.iloc[0]["bidPrice"])
    except Exception as exc:  # noqa: BLE001 — a failed fetch/parse must degrade to None, never crash the caller
        print(f"[discovery_detector] WARNING: fetch failed for {when_utc.isoformat()}: {exc}")
        return None


@dataclass
class AnomalyResult:
    """
    Encapsulates the result of anomaly detection for a single market series
    on a given date: the raw move percentage, the rolling baseline mean and
    stdev, and the standardized move (how many baseline stdevs away from
    baseline mean the actual move landed).
    """
    series: str
    move_pct: float
    baseline_mean: float
    baseline_stdev: float
    stdev_move: float  # (move_pct - baseline_mean) / baseline_stdev
    date: dt.date


def rolling_baseline(
    series: str, as_of_date: dt.date, window_days: int = 20,
) -> Optional[tuple[float, float]]:
    """
    Mean and stdev of the `window_days` daily moves immediately BEFORE
    as_of_date -- as_of_date itself is never included, same no-lookahead
    discipline data_layer/event_context.py's build_event_news_bundle()
    already enforces elsewhere in this codebase (a prediction must never
    see data from after the instant it's supposed to represent).

    Returns None -- never a fabricated partial baseline -- if fewer than
    `window_days` real moves are available in that lookback (a market
    holiday, a data gap, or simply too early in this feature's own life
    for 20 real trading days to exist yet).
    """
    moves = []
    check_date = as_of_date - dt.timedelta(days=1)
    days_checked = 0
    # Walks back one calendar day at a time (skipping weekends implicitly
    # via compute_daily_move returning None for a non-trading day) until
    # window_days REAL moves are collected or a reasonable calendar-day
    # budget is exhausted -- 2x window_days covers weekends without
    # risking an unbounded loop on a genuinely broken feed.
    while len(moves) < window_days and days_checked < window_days * 2:
        move = compute_daily_move(series, check_date)
        if move is not None:
            moves.append(move)
        check_date -= dt.timedelta(days=1)
        days_checked += 1
    if len(moves) < window_days:
        return None
    return statistics.mean(moves), statistics.stdev(moves)


ANOMALY_STDEV_THRESHOLD = 2.0  # Discovery_Detector_Spec's own number, verbatim


def detect_anomaly(
    series: str, date: dt.date, calendar_events: list[EconomicEvent],
) -> Optional[AnomalyResult]:
    """
    None -- the overwhelmingly common, expected result -- if: today's
    move or the rolling baseline itself has no real data (never
    guessed), the move is within ANOMALY_STDEV_THRESHOLD standard
    deviations of the baseline, OR a real USD Medium+ impact calendar
    event already covers `date` (an expected move from a known release
    is not an anomaly -- same "the calendar already explains this" gate
    Discovery_Detector_Spec itself specifies). `calendar_events` is the
    caller's responsibility to fetch and filter to `date` and
    country == "USD" -- this function does no fetching of its own, kept
    a pure function of its inputs like every other function in this
    module.
    """
    move = compute_daily_move(series, date)
    if move is None:
        return None
    baseline = rolling_baseline(series, date)
    if baseline is None:
        return None
    mean, stdev = baseline
    if stdev == 0:
        return None  # a real but degenerate (zero-variance) baseline can't produce a meaningful stdev_move
    stdev_move = (move - mean) / stdev
    if abs(stdev_move) < ANOMALY_STDEV_THRESHOLD:
        return None

    has_explaining_event = any(
        e.country == "USD" and IMPACT_RANK.get(e.impact, 0) >= IMPACT_RANK["Medium"]
        and e.event_time_utc.date() == date
        for e in calendar_events
    )
    if has_explaining_event:
        return None

    return AnomalyResult(
        series=series, move_pct=move, baseline_mean=mean, baseline_stdev=stdev,
        stdev_move=stdev_move, date=date,
    )
