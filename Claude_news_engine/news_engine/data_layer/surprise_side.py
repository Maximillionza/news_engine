# data_layer/surprise_side.py
"""
The one definition of "in line" for an actual versus its consensus forecast
(FIX task 2, owner ruling R2, 2026-11-03). Zero project imports on purpose, so
data_layer.calendar_feed (classify_surprise, the stored event_history label)
and webapp.stats_rules (Stats grading) both use it without a circular import.

A print is "in line" only when it equals the forecast at the forecast's own
published precision: the tolerance is ONE rounding step of the forecast's
decimals (0.3% -> 0.1, 89K -> 1). Any one-tick deviation (4.1% vs 4.2%) is a
beat or a miss. The old 5%-of-forecast band is retired.
"""
from __future__ import annotations

import re
from typing import Optional

_NUMBER = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(?:[KMBT]|%)?\s*$", re.IGNORECASE)
_EPS = 1e-9


def parse_number(text: Optional[str]) -> Optional[float]:
    """'0.6%' -> 0.6, '89K' -> 89.0 (unit kept as published, not rescaled). Unreadable -> None."""
    if text is None:
        return None
    match = _NUMBER.match(str(text))
    return float(match.group(1)) if match else None


def decimals_of(text: Optional[str]) -> Optional[int]:
    if parse_number(text) is None:
        return None
    number = re.search(r"-?\d+(?:\.(\d+))?", str(text))
    return len(number.group(1)) if number and number.group(1) else 0


def tolerance(forecast_text: Optional[str]) -> Optional[float]:
    """One rounding step of the forecast's own published precision (0.3% -> 0.1, 89K -> 1)."""
    decimals = decimals_of(forecast_text)
    return None if decimals is None else 10.0 ** (-decimals)


def side(value: float, forecast: float, tol: float) -> int:
    """-1 below, 0 in line (less than one step away), +1 above. _EPS absorbs float noise (0.4-0.3)."""
    if abs(value - forecast) < tol - _EPS:
        return 0
    return 1 if value > forecast else -1
