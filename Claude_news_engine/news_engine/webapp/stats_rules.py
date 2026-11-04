# webapp/stats_rules.py
"""
Pure scoring rules for the Stats tab (docs/superpowers/specs/2026-10-15-stats-tab-design.md §4).
Right/Wrong is decided by DIRECTION against the Forecast, never by closeness of the number.
"""
from __future__ import annotations

from typing import Optional

# The in-line rule lives in data_layer/surprise_side.py (FIX task 2) so calendar_feed shares it.
from data_layer.surprise_side import decimals_of, parse_number, side, tolerance  # noqa: F401


def judge(predicted_side: Optional[int], actual_side: Optional[int]) -> Optional[str]:
    if predicted_side is None or actual_side is None:
        return None
    return "right" if predicted_side == actual_side else "wrong"


def miss_size(predicted: Optional[float], actual: Optional[float]) -> Optional[float]:
    if predicted is None or actual is None:
        return None
    return abs(predicted - actual)
