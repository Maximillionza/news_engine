"""
Thin wrapper around the dukascopy-python library (see
requirements-dukascopy.txt — opt-in, not a core dependency) for fetching a
single real historical price at a given UTC instant. Used by
scoring/outcome_classifier.py to auto-confirm backtest accumulator
predictions instead of manual research — see
docs/superpowers/specs/2026-08-10-dukascopy-outcome-confirmation-design.md.

Contains the third-party dependency's response shape (a pandas DataFrame) to
this one file — callers only ever see PricePoint, same pattern
data_layer/news_feed.py already uses to contain Alpha Vantage's response shape.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import dukascopy_python
from dukascopy_python.instruments import (
    INSTRUMENT_FX_METALS_XAU_USD,
    INSTRUMENT_IDX_AMERICA_E_D_J_IND,
)

# Tracked instrument (config.settings.INSTRUMENTS key) -> Dukascopy's own
# instrument identifier. Deliberately not reusing INSTRUMENTS directly here —
# its values are UI labels/relationships, not Dukascopy identifiers.
_INSTRUMENT_MAP = {
    "XAUUSD": INSTRUMENT_FX_METALS_XAU_USD,
    "US30": INSTRUMENT_IDX_AMERICA_E_D_J_IND,
}

# A short window is enough to catch the next real tick without pulling a
# large range. BID consistently (not ASK, not a mid) — an arbitrary but fixed
# choice, avoids spread noise from mixing sides across two measurement points.
_FETCH_WINDOW_MINUTES = 5


@dataclass
class PricePoint:
    price: float


def get_price_at(instrument: str, when_utc: dt.datetime) -> Optional[PricePoint]:
    """
    Returns the price of the first tick AT OR AFTER when_utc — same
    no-lookahead discipline event_context.py already enforces on the
    prediction side, applied here on the confirmation side. Returns None on
    any fetch failure, or if the window contains no ticks at all (market
    closed, data gap) — never raises out to the caller for a data-
    availability reason, matching every other feed module in this codebase.
    Raises ValueError for an instrument this module doesn't know how to map
    — that's a caller bug, not a data-availability issue, so it's not
    swallowed into None like the data-availability cases above.
    """
    if instrument not in _INSTRUMENT_MAP:
        raise ValueError(
            f"instrument={instrument!r} has no Dukascopy mapping — "
            f"known instruments: {sorted(_INSTRUMENT_MAP)}"
        )

    dukascopy_instrument = _INSTRUMENT_MAP[instrument]
    window_end = when_utc + dt.timedelta(minutes=_FETCH_WINDOW_MINUTES)
    try:
        df = dukascopy_python.fetch(
            dukascopy_instrument,
            dukascopy_python.INTERVAL_TICK,
            dukascopy_python.OFFER_SIDE_BID,
            when_utc,
            window_end,
        )
    except Exception as exc:  # noqa: BLE001 — a failed fetch must degrade to None, never crash the caller
        print(f"[dukascopy_feed] WARNING: fetch failed for {instrument} at {when_utc.isoformat()}: {exc}")
        return None

    if df is None or df.empty:
        return None

    return PricePoint(price=float(df.iloc[0]["bidPrice"]))
