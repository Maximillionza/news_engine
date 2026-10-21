"""
Maps a classified shock category to the user's currently-tracked symbols
and the transmission channel, per the design spec's per-instrument-quirks
section. The (category, symbol_class) -> channel table is
alerting/transmission.py's TRANSMISSION (shared with direction.py's leans;
its provenance notes live there), layered on top of
webapp.symbols.classify_symbol()'s public usd_relationship baseline.
"""
from __future__ import annotations

from dataclasses import dataclass

from alerting.transmission import OIL_LINKED_SYMBOLS, TRANSMISSION
from webapp.symbols import classify_symbol, UnrecognizedSymbolError


@dataclass
class SymbolImpact:
    symbol: str
    channel: str
    # webapp.symbols class ("metal", "index_risk", ...), or "oil_linked_fx" for
    # the oil-linked pairs; alerting/transmission.py keys its table on it.
    symbol_class: str = ""


def affected_symbols(category: str, tracked_symbols: list[str], headline: str = "") -> list[SymbolImpact]:
    """
    tracked_symbols is expected to come from webapp.store.list_tracked_symbols()
    at call time -- live, not cached (poll_once.py's job to fetch it fresh
    each cycle). An unrecognized ticker is skipped, not raised -- a
    classify_symbol() failure for one tracked symbol must never block
    relevance mapping for the others. Returns [] if no real relevance can
    be established for any currently-tracked symbol under this category.

    headline is for channels gated on the headline's wording
    (Transmission.headline_gate, e.g. tariff_bullion): a gated entry is
    skipped unless the gate matches. The default "" means no gated channel
    applies, and keeps older callers valid.
    """
    results: list[SymbolImpact] = []
    for symbol in tracked_symbols:
        # Oil-linked pairs (USDCAD) take their own row where the category has
        # one (energy), checked before the generic symbol class -- a specific
        # transmission path, not the plain usd_relationship mapping.
        if symbol in OIL_LINKED_SYMBOLS:
            oil_linked = TRANSMISSION.get((category, "oil_linked_fx"))
            if oil_linked is not None:
                results.append(SymbolImpact(symbol=symbol, channel=oil_linked.channel, symbol_class="oil_linked_fx"))
                continue
        try:
            symbol_class = classify_symbol(symbol)
        except UnrecognizedSymbolError:
            continue
        transmission = TRANSMISSION.get((category, symbol_class.symbol_class))
        if transmission is not None:
            if transmission.headline_gate is not None and not transmission.headline_gate.search(headline):
                continue
            results.append(SymbolImpact(
                symbol=symbol, channel=transmission.channel, symbol_class=symbol_class.symbol_class))
    return results
