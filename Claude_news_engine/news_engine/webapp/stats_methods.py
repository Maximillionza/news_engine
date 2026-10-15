"""
Method maths for the Stats tab (spec §4.1). Pure except for reading two existing mapping tables.
Combined = 70% Tier 1 + 30% News; the weight is fixed in advance and revisited on 2027-01-15.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional

from config.settings import EVENT_SURPRISE_DIRECTION
from webapp.history import _implied_surprise_direction
from webapp.symbols import UnrecognizedSymbolError, classify_symbol

TIER1_WEIGHT = 0.70
NEWS_WEIGHT = 0.30
MIN_HISTORY_FOR_SCALE = 3


def news_scale(prior_abs_surprises: list[float]) -> Optional[float]:
    """Median |actual - forecast| over occurrences BEFORE this one (no lookahead). Assumption: labelled on the chart."""
    if len(prior_abs_surprises) < MIN_HISTORY_FOR_SCALE:
        return None
    return statistics.median(prior_abs_surprises)


def tier1_surprise(nowcast: Optional[float], forecast: Optional[float]) -> Optional[float]:
    return None if nowcast is None or forecast is None else nowcast - forecast


def news_surprise(lean: Optional[float], scale: Optional[float]) -> Optional[float]:
    return None if lean is None or scale is None else lean * scale


@dataclass(frozen=True)
class CombinedResult:
    surprise: float
    news_missing: bool


def combine(s1: Optional[float], sn: Optional[float]) -> Optional[CombinedResult]:
    """No Tier 1 -> None (Combined is n/a). No news -> Tier 1 only, flagged. Never a 'conflicting' state."""
    if s1 is None:
        return None
    if sn is None:
        return CombinedResult(surprise=s1, news_missing=True)
    return CombinedResult(surprise=TIER1_WEIGHT * s1 + NEWS_WEIGHT * sn, news_missing=False)


def news_lean(
    event_title: str, print_side: Optional[str], print_confidence: Optional[float],
    acc_direction: Optional[str], acc_probability: Optional[float],
) -> Optional[float]:
    """
    Lean in [-1, +1]; + means 'hotter/higher than forecast'. Rule R3, fixed before results are viewed:
    1) a print call that takes a side wins (strength = its confidence);
    2) otherwise the XAUUSD accumulator prediction, mapped to a surprise side, strength |2p-1|.
    A strength of exactly 0 (print confidence 0, or accumulator p == 0.5) is no lean: None, never 0.0/-0.0.
    """
    if print_side in ("higher", "lower") and print_confidence is not None:
        strength = max(0.0, min(1.0, float(print_confidence)))
        return _signed(strength, print_side == "higher")
    if acc_direction in ("bullish", "bearish") and acc_probability is not None:
        implied = _implied_surprise_direction(event_title, "XAUUSD", acc_direction)
        if implied is None:
            return None
        strength = abs(2 * float(acc_probability) - 1)
        return _signed(strength, implied == "higher")
    return None


def _signed(strength: float, hotter: bool) -> Optional[float]:
    if strength == 0:
        return None
    return strength if hotter else -strength


def market_lean(event_title: str, surprise_side: int, symbol: str) -> str:
    """'buy' | 'sell' | 'mixed' for one symbol given the surprise side (+1 higher, -1 lower, 0 in line)."""
    surprise_map = EVENT_SURPRISE_DIRECTION.get(event_title)
    if surprise_map is None or surprise_side == 0:
        return "mixed"
    usd_bullish = (surprise_side > 0) == (surprise_map == "higher_bullish")
    try:
        relationship = classify_symbol(symbol).usd_relationship
    except UnrecognizedSymbolError:
        return "mixed"
    if relationship is None:
        return "mixed"
    if relationship == "direct":
        return "buy" if usd_bullish else "sell"
    return "sell" if usd_bullish else "buy"   # inverse and risk_sentiment flip against USD
