"""
Symbol classification for the essence-only (no-articles) scoring path.

Every tracked symbol is auto-classified from its ticker into a
SymbolClass, which decides two things: whether a USD economic event
applies to it at all, and if so, which direction a USD-bullish surprise
pushes it. This extends the same usd_relationship concept already used in
config.settings.INSTRUMENTS for XAUUSD/US30, but derives it from the
ticker pattern instead of requiring a hand-entered config line per symbol.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

METALS = {"XAUUSD", "XAGUSD"}
INDICES = {"US30", "US500", "NAS100"}

_USD_BASE_PATTERN = re.compile(r"^USD([A-Z]{3})$")   # USDJPY, USDCHF, USDCAD
_USD_QUOTE_PATTERN = re.compile(r"^([A-Z]{3})USD$")  # EURUSD, GBPUSD, AUDUSD, NZDUSD
_FX_PATTERN = re.compile(r"^[A-Z]{6}$")               # any 6 uppercase letters, e.g. GBPAUD


class UnrecognizedSymbolError(ValueError):
    """Raised when a ticker doesn't match any known symbol shape."""


@dataclass(frozen=True)
class SymbolClass:
    symbol: str
    symbol_class: str                 # "metal" | "fx_usd_base" | "fx_usd_quote" | "index_risk" | "fx_cross"
    usd_relationship: Optional[str]   # "inverse" | "direct" | "risk_sentiment" | None (fx_cross: not applicable)


def classify_symbol(ticker: str) -> SymbolClass:
    """
    Raises UnrecognizedSymbolError for anything that isn't a known metal,
    a known index, or a 6-letter FX-shaped ticker — never silently
    misclassifies.
    """
    ticker = ticker.strip().upper()

    if ticker in METALS:
        return SymbolClass(symbol=ticker, symbol_class="metal", usd_relationship="inverse")

    if ticker in INDICES:
        return SymbolClass(symbol=ticker, symbol_class="index_risk", usd_relationship="risk_sentiment")

    if _USD_BASE_PATTERN.match(ticker):
        return SymbolClass(symbol=ticker, symbol_class="fx_usd_base", usd_relationship="direct")

    if _USD_QUOTE_PATTERN.match(ticker):
        return SymbolClass(symbol=ticker, symbol_class="fx_usd_quote", usd_relationship="inverse")

    if _FX_PATTERN.match(ticker):
        return SymbolClass(symbol=ticker, symbol_class="fx_cross", usd_relationship=None)

    raise UnrecognizedSymbolError(
        f"{ticker!r} doesn't match a known metal, index, or 6-letter FX pair shape"
    )
