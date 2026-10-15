# webapp/stats_rules.py
"""
Pure scoring rules for the Stats tab (docs/superpowers/specs/2026-10-15-stats-tab-design.md §4).
Right/Wrong is decided by DIRECTION against the Forecast, never by closeness of the number.
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


def judge(predicted_side: Optional[int], actual_side: Optional[int]) -> Optional[str]:
    if predicted_side is None or actual_side is None:
        return None
    return "right" if predicted_side == actual_side else "wrong"


def miss_size(predicted: Optional[float], actual: Optional[float]) -> Optional[float]:
    if predicted is None or actual is None:
        return None
    return abs(predicted - actual)
