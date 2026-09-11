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


def _fetch_tick(instrument, when_utc: dt.datetime) -> Optional[float]:
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
