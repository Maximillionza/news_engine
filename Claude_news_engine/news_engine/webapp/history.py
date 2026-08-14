"""
Read-only cross-pipeline join for the dashboard's History tab —
webapp.store's event_history (resolved occurrences, this dashboard's own
DB) joined with scoring.backtest_store's print_predictions (numeric
events) or predictions+outcomes (text-only events with no forecast at
all, e.g. FOMC Statement), producing a Confirmed/Missed track record.

Mirrors the read-only cross-pipeline pattern already established twice in
this codebase: webapp/app.py reads scoring.backtest_store's DB read-only
for the print-call badge; scoring/backtest_accumulator.py reads
webapp.store's DB read-only for the trend signal. This module is the
third instance, dashboard-side, display-only — it writes nothing to
either DB.

Not every High-impact USD event has a number to compare against — FOMC
Statement/Press Conference publish no forecast/actual at all, but the
accumulator's article-based sentiment call (predictions table) already
scores them regardless (score_bundle()'s core article-sentiment path
requires no numeric forecast — only the additional structured
contributions like the print-direction lexicon do). Those events get a
separate row per instrument using that regular sentiment call instead of
a numeric surprise comparison.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from config.settings import INSTRUMENTS
from scoring.print_direction import NO_HIT_CONFIDENCE
from webapp.store import get_connection, get_resolved_event_history, get_text_only_resolved_events

DEFAULT_HISTORY_LIMIT = 50

# Wide pre-filter for both source queries — must stay decoupled from the
# display `limit` (default 50), or a rare row type (FOMC, ~8x/year) can be
# starved out before the merge even happens by far more common events
# (bond auctions, foreign central bank speeches, etc.) eating the budget.
# Matches webapp.store's own get_resolved_event_history()/
# get_text_only_resolved_events() default of 200.
PRE_FILTER_LIMIT = 200

# Text-only rows (no numeric forecast at all) get the same shrug-exclusion
# floor as numeric rows' NO_HIT_CONFIDENCE, for the same record-integrity
# reason: a near-zero-conviction prediction that happens to land right by
# chance shouldn't pad the Confirmed/Missed track record. Same numeric
# value as NO_HIT_CONFIDENCE for consistency, even though it's a different
# metric (score_bundle()'s agreement×coverage, not a lexicon hit-count).
MIN_TEXT_EVENT_CONFIDENCE = NO_HIT_CONFIDENCE


@dataclass
class HistoryRow:
    event_title: str
    event_time_utc: str
    instrument: Optional[str]       # None for numeric rows; 'XAUUSD'/'US30' for text-event fallback rows
    previous: Optional[str]
    forecast: Optional[str]
    actual: Optional[str]
    unchanged_vs_previous: bool
    ne_prediction: str
    ne_confidence: float
    outcome: Optional[str]          # 'Confirmed' | 'Missed' | None
    unjudged_reason: Optional[str]  # None when outcome is a real verdict; else 'shrug' | 'unknown_surprise' | 'pending'
    source: str                     # 'live' | 'seeded' | 'live_web_fallback' — for numeric rows, 'seeded' wins if either side of the join disagrees, else 'live_web_fallback' wins if either side is 'live_web_fallback', else 'live'


def build_print_call_history(limit: int = DEFAULT_HISTORY_LIMIT, now: Optional[dt.datetime] = None) -> list[HistoryRow]:
    """
    Only resolved event_history occurrences (actual IS NOT NULL) WITH a
    matching print_predictions row appear as numeric rows — either
    condition missing means the occurrence is skipped entirely. Text-only
    occurrences (forecast AND actual both NULL) with a real predictions
    row appear as one fallback row per instrument. Fails open to an empty
    list if the backtest DB is unreachable for any reason — never crashes
    the /api/history route over a cross-pipeline read error.
    """
    now = now or dt.datetime.now(dt.timezone.utc)

    # Imported here, not at module level, to avoid a hard import-time
    # dependency cycle risk between webapp and scoring — matches the
    # existing lazy-import style already used for cross-pipeline reads in
    # scoring/backtest_accumulator.py's _read_trend_signal().
    from scoring.backtest_store import (
        get_connection as get_backtest_connection,
        get_latest_print_prediction,
        get_latest_prediction_for_occurrence,
        get_outcome,
    )

    dash_conn = get_connection()
    try:
        numeric_resolved = get_resolved_event_history(dash_conn, limit=PRE_FILTER_LIMIT)
        text_only_resolved = get_text_only_resolved_events(dash_conn, now=now, limit=PRE_FILTER_LIMIT)
    finally:
        dash_conn.close()

    if not numeric_resolved and not text_only_resolved:
        return []

    try:
        bt_conn = get_backtest_connection()
    except Exception as exc:  # noqa: BLE001 — an unreachable backtest DB must not crash the route
        print(f"[webapp.history] WARNING: could not read backtest data: {exc}")
        return []

    rows: list[HistoryRow] = []
    try:
        for event in numeric_resolved:
            event_time = dt.datetime.fromisoformat(event.event_time_utc)
            try:
                call = get_latest_print_prediction(bt_conn, event.event_title, event_time)
            except Exception as exc:  # noqa: BLE001 — one bad lookup must not crash the whole build
                print(f"[webapp.history] WARNING: could not read print call for {event.event_title}: {exc}")
                continue
            if call is None:
                continue  # resolved event, but never scored by the accumulator — excluded, not shown with blanks

            outcome: Optional[str] = None
            unjudged_reason: Optional[str] = None
            if call.confidence <= NO_HIT_CONFIDENCE:
                unjudged_reason = "shrug"
            elif event.surprise_direction is None:
                unjudged_reason = "unknown_surprise"
            else:
                outcome = "Confirmed" if call.predicted_vs_forecast == event.surprise_direction else "Missed"

            rows.append(HistoryRow(
                event_title=event.event_title,
                event_time_utc=event.event_time_utc,
                instrument=None,
                previous=event.previous,
                forecast=event.forecast,
                actual=event.actual,
                unchanged_vs_previous=(event.actual == event.previous),
                ne_prediction=call.predicted_vs_forecast,
                ne_confidence=call.confidence,
                outcome=outcome,
                unjudged_reason=unjudged_reason,
                # A numeric row's provenance normally agrees on both sides of
                # the join (event_history + print_predictions); if it ever
                # doesn't, 'seeded' wins — a partially-reconstructed row is
                # more honestly labeled by its most-uncertain component, not
                # its most-certain one. 'live_web_fallback' only ever lands
                # in event_history (call.source can't be it in practice, but
                # checking both sides costs nothing and keeps this resilient
                # to a future write path), so it's checked next, before
                # falling back to 'live'. Must genuinely distinguish all
                # three values — never collapse to a live/seeded boolean.
                source=(
                    "seeded" if "seeded" in (event.source, call.source)
                    else "live_web_fallback" if "live_web_fallback" in (event.source, call.source)
                    else "live"
                ),
            ))

        for event in text_only_resolved:
            event_time = dt.datetime.fromisoformat(event.event_time_utc)
            for instrument in INSTRUMENTS.keys():
                try:
                    prediction = get_latest_prediction_for_occurrence(bt_conn, event.event_title, instrument, event_time)
                except Exception as exc:  # noqa: BLE001 — one bad lookup must not crash the whole build
                    print(f"[webapp.history] WARNING: could not read prediction for {event.event_title}/{instrument}: {exc}")
                    continue
                if prediction is None:
                    continue  # no real call for this instrument at this occurrence — no row, not shown with blanks

                try:
                    outcome_row = get_outcome(bt_conn, event.event_title, instrument, event_time)
                except Exception as exc:  # noqa: BLE001
                    print(f"[webapp.history] WARNING: could not read outcome for {event.event_title}/{instrument}: {exc}")
                    outcome_row = None

                text_outcome: Optional[str] = None
                text_unjudged_reason: Optional[str] = None
                if prediction.confidence <= MIN_TEXT_EVENT_CONFIDENCE:
                    text_unjudged_reason = "shrug"
                elif outcome_row is None:
                    text_unjudged_reason = "pending"
                else:
                    text_outcome = "Confirmed" if outcome_row.actual_direction == prediction.direction else "Missed"

                rows.append(HistoryRow(
                    event_title=event.event_title,
                    event_time_utc=event.event_time_utc,
                    instrument=instrument,
                    previous=None,
                    forecast=None,
                    actual=None,
                    unchanged_vs_previous=False,
                    ne_prediction=prediction.direction,
                    ne_confidence=prediction.confidence,
                    outcome=text_outcome,
                    unjudged_reason=text_unjudged_reason,
                    source=prediction.source,
                ))
    finally:
        bt_conn.close()

    rows.sort(key=lambda r: r.event_time_utc, reverse=True)
    return rows[:limit]
