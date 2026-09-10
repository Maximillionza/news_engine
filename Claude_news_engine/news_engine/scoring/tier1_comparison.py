"""
Automatic Tier 1-vs-sentiment-vs-real-outcome comparison, for the moment
a real outcome lands. Turns the one-off pattern
tests/run_causation_matrix_option_a_backtest.py established (pull the
real, already-recorded sentiment prediction; pull the real, already-
logged Tier 1 prediction; evaluate both against a real confirmed
outcome) into something callable automatically, right after
record_outcome() fires -- see scripts/confirm_backtest_outcomes.py's hook.

Deliberately does nothing new on the judgment side: predicted_direction
for Tier 1 must already be logged (record_tier1_prediction(), still
manually researched -- see scoring/backtest.py's Tier1Prediction
docstring). This module only wires together three already-real, already-
recorded facts once all three exist; it never derives a call itself.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Optional

from data_layer.calendar_feed import EconomicEvent
from scoring.backtest import BacktestCase, Tier1Prediction
from scoring.backtest_store import (
    get_latest_prediction_for_occurrence,
    get_latest_tier1_prediction_for_occurrence,
    record_tier1_comparison,
)
from scoring.probability_engine import Direction, ProbabilityResult


def compute_and_record_tier1_comparison(
    conn: sqlite3.Connection,
    event_title: str,
    instrument: str,
    event_time_utc: dt.datetime,
    actual_direction: Direction,
    actual_move_note: str,
) -> Optional[int]:
    """
    Returns the new/updated tier1_comparisons row id, or None if there is
    nothing to compare -- the overwhelmingly common case (no Tier 1
    prediction was ever logged for this occurrence, which is true for
    every event except a researched CPI/PPI one) or no real sentiment
    prediction exists yet (a stale/manual-only occurrence). Both are
    normal, not errors: never raises for a missing prerequisite, matching
    the fail-open discipline the rest of this Tier 1 feature already uses.
    """
    tier1_row = get_latest_tier1_prediction_for_occurrence(conn, event_title, instrument, event_time_utc)
    if tier1_row is None:
        return None
    prediction = get_latest_prediction_for_occurrence(conn, event_title, instrument, event_time_utc)
    if prediction is None:
        return None

    event = EconomicEvent(title=event_title, country="USD", impact="High", event_time_utc=event_time_utc)
    tier1 = Tier1Prediction(
        value=tier1_row.value, confidence=tier1_row.confidence,
        source=tier1_row.source, predicted_direction=Direction(tier1_row.predicted_direction),
    )
    case = BacktestCase(
        event=event, instrument=instrument,
        actual_direction=actual_direction, actual_move_note=actual_move_note,
        tier1=tier1,
    )
    case.result = ProbabilityResult(
        instrument=instrument,
        as_of_utc=dt.datetime.fromisoformat(prediction.scored_at_utc),
        aggregate_usd_sentiment=0.0, instrument_score=0.0,
        probability=prediction.probability, direction=Direction(prediction.direction),
        confidence=prediction.confidence, article_count=prediction.article_count,
        contradiction_flag=prediction.contradiction_flag, contradiction_note=None,
    )
    case.evaluate()

    return record_tier1_comparison(
        conn, event_title, instrument, event_time_utc,
        sentiment_direction=prediction.direction,
        sentiment_correct=case.predicted_correct,
        tier1_direction=tier1_row.predicted_direction,
        tier1_confidence=tier1_row.confidence,
        tier1_correct=case.tier1_predicted_correct,
        actual_direction=actual_direction.value,
        actual_move_note=actual_move_note,
    )
