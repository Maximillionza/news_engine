"""
Classifies a backtest accumulator prediction's real outcome from Dukascopy
price data — the post-event price move over MEASUREMENT_WINDOW_MINUTES
becomes an auto-confirmable bullish/bearish call above
CLEAR_MOVE_THRESHOLD_PCT, or is left ambiguous (needs manual review) below
it. Never auto-classifies neutral: a small move means "needs a human to
look," not "confidently no reaction" — those are different claims, and
conflating them would silently under-report real small moves as neutral in
the accuracy report. See
docs/superpowers/specs/2026-08-10-dukascopy-outcome-confirmation-design.md.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Optional

from data_layer.dukascopy_feed import get_price_at
from scoring.probability_engine import Direction

MEASUREMENT_WINDOW_MINUTES = 30
CLEAR_MOVE_THRESHOLD_PCT = 0.15


@dataclass
class ClassificationResult:
    direction: Optional[Direction]   # bullish/bearish, or None if ambiguous
    move_pct: Optional[float]        # None only if a fetch failed outright
    note: str                        # human-readable; becomes actual_move_note verbatim on auto-confirm


def classify(instrument: str, event_time_utc: dt.datetime) -> ClassificationResult:
    before = get_price_at(instrument, event_time_utc)
    after = get_price_at(instrument, event_time_utc + dt.timedelta(minutes=MEASUREMENT_WINDOW_MINUTES))

    if (
        before is None or after is None
        or not math.isfinite(before.price) or not math.isfinite(after.price)
        or before.price <= 0
    ):
        return ClassificationResult(
            direction=None, move_pct=None,
            note="Dukascopy: no usable price data (market closed, feed gap, or bad tick)",
        )

    move_pct = (after.price - before.price) / before.price * 100

    if abs(move_pct) < CLEAR_MOVE_THRESHOLD_PCT:
        return ClassificationResult(
            direction=None, move_pct=move_pct,
            note=f"Dukascopy: {move_pct:+.2f}% in {MEASUREMENT_WINDOW_MINUTES}min, below {CLEAR_MOVE_THRESHOLD_PCT}% threshold",
        )

    direction = Direction.BULLISH if move_pct > 0 else Direction.BEARISH
    return ClassificationResult(
        direction=direction, move_pct=move_pct,
        note=f"Dukascopy: {move_pct:+.2f}% in {MEASUREMENT_WINDOW_MINUTES}min (auto)",
    )
