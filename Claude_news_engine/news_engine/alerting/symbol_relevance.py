"""
Maps a classified shock category to the user's currently-tracked symbols
and the transmission channel, per the design spec's per-instrument-quirks
section. Built as its own lightweight category -> symbol_class table
(NOT a reuse of scoring/probability_engine.py's private _check_oil_shock,
which takes a pre-computed MacroBackdropRead object, not a category
label -- the wrong shape for this purpose) layered on top of
webapp.symbols.classify_symbol()'s public usd_relationship baseline.
"""
from __future__ import annotations

from dataclasses import dataclass

from webapp.symbols import classify_symbol, UnrecognizedSymbolError


@dataclass
class SymbolImpact:
    symbol: str
    channel: str


# category -> {symbol_class: channel} -- only combinations with a real,
# documented transmission path are listed; anything absent here means
# "no established relevance," an honest [] result, not a guess.
_CATEGORY_SYMBOL_CLASS_CHANNELS: dict[str, dict[str, str]] = {
    "energy": {
        "metal": "safe_haven",
        "index_risk": "risk_sentiment",
    },
    "geopolitical_conflict": {
        "metal": "safe_haven",
        "index_risk": "risk_sentiment",
    },
    "central_bank": {
        "metal": "usd_relationship",
        "index_risk": "risk_sentiment",
        "fx_usd_base": "usd_relationship",
        "fx_usd_quote": "usd_relationship",
    },
    "sovereign_fiscal": {
        "metal": "usd_relationship",
        "index_risk": "risk_sentiment",
        "fx_usd_base": "usd_relationship",
        "fx_usd_quote": "usd_relationship",
    },
    "trade_policy": {
        "index_risk": "risk_sentiment",
    },
    "natural_disaster_supply_chain": {
        "index_risk": "risk_sentiment",
    },
}

# Oil-linked FX pairs (design spec: "USDCAD is oil-linked... independent
# of and sometimes working against the pure USD-weakness direction") get
# their own channel regardless of category, checked before the generic
# symbol_class table above -- a real, specific transmission path, not
# the plain usd_relationship mapping.
_OIL_LINKED_SYMBOLS = {"USDCAD"}


def affected_symbols(category: str, tracked_symbols: list[str]) -> list[SymbolImpact]:
    """
    tracked_symbols is expected to come from webapp.store.list_tracked_symbols()
    at call time -- live, not cached (poll_once.py's job to fetch it fresh
    each cycle). An unrecognized ticker is skipped, not raised -- a
    classify_symbol() failure for one tracked symbol must never block
    relevance mapping for the others. Returns [] if no real relevance can
    be established for any currently-tracked symbol under this category.
    """
    channels_by_class = _CATEGORY_SYMBOL_CLASS_CHANNELS.get(category, {})
    results: list[SymbolImpact] = []
    for symbol in tracked_symbols:
        if category == "energy" and symbol in _OIL_LINKED_SYMBOLS:
            results.append(SymbolImpact(symbol=symbol, channel="oil_linkage"))
            continue
        try:
            symbol_class = classify_symbol(symbol)
        except UnrecognizedSymbolError:
            continue
        channel = channels_by_class.get(symbol_class.symbol_class)
        if channel is not None:
            results.append(SymbolImpact(symbol=symbol, channel=channel))
    return results
