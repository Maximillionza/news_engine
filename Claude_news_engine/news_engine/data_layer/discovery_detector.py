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
    mechanism, just a new instrument map. Session open/close are UTC
    00:00 and 23:59:59 for `date` -- a coarse but real and consistent
    definition, matching this project's existing "before/after" tick
    convention rather than inventing a market-hours-aware session
    boundary this codebase doesn't otherwise track.

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
    session_end = dt.datetime.combine(date, dt.time(23, 59, 59), tzinfo=dt.timezone.utc)

    open_price = _fetch_tick(instrument, session_start)
    close_price = _fetch_tick(instrument, session_end)
    if open_price is None or close_price is None:
        return None
    return (close_price - open_price) / open_price * 100


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
