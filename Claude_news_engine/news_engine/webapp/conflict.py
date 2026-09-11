"""
compute_tier1_sentiment_conflict() — a dependency-free leaf module.

Moved out of webapp/predictions_service.py (final whole-branch review,
2026-09-11 — Finding 1): predictions_service.py imports
scoring.backtest_store, which pulls in scoring.probability_engine ->
scoring.finbert_sentiment -> transformers/torch. webapp/history.py needs
this one function but must NOT drag in that entire chain just to compute
a shared comparison rule — measured impact was importing webapp.history
going from 0.39s to 10.73s purely from this one module-level import.
This module has zero imports of its own, so both webapp/predictions_service.py
and webapp/history.py can import it at module level with no cycle risk
and no import weight.
"""
from __future__ import annotations

from typing import Optional


def compute_tier1_sentiment_conflict(
    sentiment_direction: Optional[str], tier1_direction: Optional[str],
) -> Optional[dict]:
    """
    Shared by build_predictions_payload() (Dashboard card) and
    webapp/history.py (History tab) — the exact comparison rule
    build_predictions_payload() originally computed inline
    (fundamental-analysis-review-2026-09-11.md P0 #5), extracted so
    History can apply the identical rule instead of re-deriving it.
    "No call" on either side (None, or 'neutral') is never a conflict —
    only a REAL, opposing directional call from both sides counts, same
    convention scoring/backtest.py's BacktestCase.evaluate() already uses
    for Tier 1's own accuracy metric.
    """
    if sentiment_direction not in ("bullish", "bearish") or tier1_direction not in ("bullish", "bearish"):
        return None
    if sentiment_direction == tier1_direction:
        return None
    return {"sentiment_direction": sentiment_direction, "tier1_direction": tier1_direction}
