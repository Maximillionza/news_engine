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
    INSTRUMENT_FX_METALS_XAG_USD,
    INSTRUMENT_IDX_AMERICA_E_D_J_IND,
    INSTRUMENT_IDX_AMERICA_E_SANDP_500,
    INSTRUMENT_IDX_AMERICA_E_NQ_100,
)

# Hand-verified against dukascopy_python's real ~1380-entry catalog
# (2026-09-13) — metals and indices have NO derivable relationship
# between their ticker and Dukascopy's own name at all (nothing about
# "US30" predicts "E_D&J-Ind"), so unlike the FX-pair resolver below,
# these must stay a real, explicit, individually-verified dict. Matches
# webapp/symbols.py's classify_symbol()'s METALS/INDICES sets exactly —
# extend this dict alongside that set if either ever grows.
_INSTRUMENT_MAP = {
    "XAUUSD": INSTRUMENT_FX_METALS_XAU_USD,
    "XAGUSD": INSTRUMENT_FX_METALS_XAG_USD,
    "US30": INSTRUMENT_IDX_AMERICA_E_D_J_IND,
    "US500": INSTRUMENT_IDX_AMERICA_E_SANDP_500,
    "NAS100": INSTRUMENT_IDX_AMERICA_E_NQ_100,
}

# A short window is enough to catch the next real tick without pulling a
# large range. BID consistently (not ASK, not a mid) — an arbitrary but fixed
# choice, avoids spread noise from mixing sides across two measurement points.
_FETCH_WINDOW_MINUTES = 5


@dataclass
class PricePoint:
    price: float


def _resolve_dukascopy_instrument(instrument: str) -> Optional[str]:
    """
    _INSTRUMENT_MAP first (real, hand-verified metals/indices). If that
    misses, tries a real, verified USD-legged-FX-pair naming convention
    (2026-09-13): dukascopy_python names every major/cross pair
    INSTRUMENT_FX_{MAJORS|CROSSES}_<BASE>_<QUOTE>, using the same 3-letter
    codes webapp/symbols.py's classify_symbol() regexes already extract
    for its fx_usd_base/fx_usd_quote classes. Tried dynamically against
    the real installed dukascopy_python.instruments module via getattr()
    — never a blind guess — so any USD-legged pair the library actually
    covers resolves correctly with zero code change, while a genuinely
    exotic/uncovered pair still returns None honestly rather than
    fabricating an instrument identifier that doesn't exist.

    A 6-letter ticker with no USD leg at all (fx_cross, e.g. GBPAUD) is
    deliberately never resolved here — it never enters the article-based
    backtest/outcome pipeline in the first place (scoring/backtest_accumulator.py's
    per-instrument loop already skips it, 2026-09-13), so there is nothing
    for this module to ever be asked to grade for one.
    """
    if instrument in _INSTRUMENT_MAP:
        return _INSTRUMENT_MAP[instrument]

    if len(instrument) == 6:
        base = quote = None
        if instrument.startswith("USD"):
            base, quote = "USD", instrument[3:]
        elif instrument.endswith("USD"):
            base, quote = instrument[:3], "USD"
        if base and quote:
            for prefix in ("INSTRUMENT_FX_MAJORS_", "INSTRUMENT_FX_CROSSES_"):
                resolved = getattr(dukascopy_python.instruments, f"{prefix}{base}_{quote}", None)
                if resolved is not None:
                    return resolved
    return None


def get_price_at(instrument: str, when_utc: dt.datetime) -> Optional[PricePoint]:
    """
    Returns the price of the first tick AT OR AFTER when_utc — same
    no-lookahead discipline event_context.py already enforces on the
    prediction side, applied here on the confirmation side. Returns None on
    any fetch failure, or if the window contains no ticks at all (market
    closed, data gap) — never raises out to the caller for a data-
    availability reason, matching every other feed module in this codebase.
    Raises ValueError for an instrument this module doesn't know how to map
    (see _resolve_dukascopy_instrument()) — that's a caller bug, not a
    data-availability issue, so it's not swallowed into None like the
    data-availability cases above.
    """
    dukascopy_instrument = _resolve_dukascopy_instrument(instrument)
    if dukascopy_instrument is None:
        raise ValueError(
            f"instrument={instrument!r} has no Dukascopy mapping — "
            f"known instruments: {sorted(_INSTRUMENT_MAP)}, plus any real USD-legged FX pair "
            f"dukascopy_python covers under INSTRUMENT_FX_MAJORS_*/INSTRUMENT_FX_CROSSES_*"
        )
    window_end = when_utc + dt.timedelta(minutes=_FETCH_WINDOW_MINUTES)
    try:
        df = dukascopy_python.fetch(
            dukascopy_instrument,
            dukascopy_python.INTERVAL_TICK,
            dukascopy_python.OFFER_SIDE_BID,
            when_utc,
            window_end,
        )
        if df is None or df.empty:
            return None
        return PricePoint(price=float(df.iloc[0]["bidPrice"]))
    except Exception as exc:  # noqa: BLE001 — a failed fetch/parse must degrade to None, never crash the caller
        print(f"[dukascopy_feed] WARNING: fetch failed for {instrument} at {when_utc.isoformat()}: {exc}")
        return None
