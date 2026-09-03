"""
Read-only cross-pipeline join for the dashboard's History tab —
webapp.store's event_history (resolved occurrences, this dashboard's own
DB) joined with scoring.backtest_store's print_predictions (numeric
events, when a qualifying article scored one), predictions+outcomes
(numeric events with NO print-call, and every text-only event with no
forecast at all, e.g. FOMC Statement), producing a Confirmed/Missed track
record.

Mirrors the read-only cross-pipeline pattern already established twice in
this codebase: webapp/app.py reads scoring.backtest_store's DB read-only
for the print-call badge; scoring/backtest_accumulator.py reads
webapp.store's DB read-only for the trend signal. This module is the
third instance, dashboard-side, display-only — it writes nothing to
either DB.

Not every resolved numeric event has a print-direction call — that needs
real article text matching PRINT_SURPRISE_LEXICON, which may never
arrive (quota exhausted, no coverage, or just too soon). Those events
fall back to the accumulator's own main prediction (predictions table),
which precursor/trend/Kalshi signals alone can drive with zero
qualifying articles — compared directly against the real
surprise_direction already sitting in event_history, the same
number-vs-call comparison the print-call path uses, not against
outcomes/price-move confirmation (2026-09-02 fix — see
_implied_surprise_direction()). Not every High-impact USD event has a
number to compare against at all — FOMC Statement/Press Conference
publish no forecast/actual whatsoever, but the accumulator's prediction
still scores them (score_bundle()'s core article-sentiment path requires
no numeric forecast). Those genuinely-numberless events get a separate
row per instrument using outcomes/price-move confirmation instead, since
there's no real surprise_direction to compare against at all.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from config.settings import EVENT_SURPRISE_DIRECTION, INSTRUMENTS
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


def _implied_surprise_direction(event_title: str, instrument: str, direction: str) -> Optional[str]:
    """
    Reverses score_bundle()'s instrument-mapping (see
    scoring/probability_engine.py's _map_to_instrument_score()) to recover
    the 'higher'/'lower' surprise-direction call this instrument's
    recorded prediction implies about the underlying NUMBER — so it can
    be compared directly against event_history.surprise_direction, the
    same equality check the numeric print-call path below already uses.
    `direction` must be 'bullish' or 'bearish' (never 'neutral' — callers
    gate that separately, since 'neutral' has no directional call to
    invert). Returns None if this title has no EVENT_SURPRISE_DIRECTION
    entry — should not happen in practice (a resolved row's
    surprise_direction can only be non-None when classify_surprise()
    found one), but never fabricates a guess if it somehow does.
    """
    surprise_map = EVENT_SURPRISE_DIRECTION.get(event_title)
    if surprise_map is None:
        return None
    relationship = INSTRUMENTS[instrument]["usd_relationship"]
    # 'inverse' and 'risk_sentiment' both flip sign relative to direct USD
    # sentiment (see _map_to_instrument_score()'s own comment on
    # risk_sentiment's simplification) — only 'direct' passes through
    # unflipped.
    usd_direction = direction if relationship == "direct" else ("bearish" if direction == "bullish" else "bullish")
    higher_bullish = surprise_map == "higher_bullish"
    return "higher" if (usd_direction == "bullish") == higher_bullish else "lower"


@dataclass
class HistoryRow:
    event_title: str
    event_time_utc: str
    instrument: Optional[str]       # None for a print-call-backed numeric row; 'XAUUSD'/'US30' for a numeric-fallback or text-event row
    previous: Optional[str]
    forecast: Optional[str]
    actual: Optional[str]
    unchanged_vs_previous: bool
    ne_prediction: str
    ne_confidence: float
    outcome: Optional[str]          # 'Confirmed' | 'Missed' | None
    unjudged_reason: Optional[str]  # None when outcome is a real verdict; else 'shrug' | 'unknown_surprise' | 'pending'
    source: str                     # 'live' | 'seeded' | 'live_web_fallback' | 'fred' — for numeric rows, 'seeded' wins if either side of the join disagrees, else 'live_web_fallback' wins if either side is 'live_web_fallback', else 'fred' wins if either side is 'fred', else 'live'


def build_print_call_history(limit: int = DEFAULT_HISTORY_LIMIT, now: Optional[dt.datetime] = None) -> list[HistoryRow]:
    """
    Resolved event_history occurrences (actual IS NOT NULL) become numeric
    rows via a print_predictions match when one exists (one row, instrument
    None), or — when no print-call was ever recorded — via a fallback to
    the accumulator's main predictions row, one per instrument (2026-09-02
    fix: this used to skip the occurrence entirely, hiding a real recorded
    prediction from History whenever no qualifying article ever showed up).
    An occurrence with NEITHER a print-call NOR a predictions row for a
    given instrument is still excluded for that instrument — never shown
    with blanks. Text-only occurrences (forecast AND actual both NULL)
    with a real predictions row appear as one fallback row per instrument,
    same as before. Fails open to an empty list if the backtest DB is
    unreachable for any reason — never crashes the /api/history route
    over a cross-pipeline read error.
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
                # No print-direction call (needs real article text matching
                # PRINT_SURPRISE_LEXICON) — fall back to the accumulator's
                # own main prediction (predictions table), which precursor/
                # trend/Kalshi signals alone can drive without any
                # qualifying article at all. Compared directly against
                # event.surprise_direction (the same equality check the
                # numeric print-call path above uses), not against
                # outcomes/price-move confirmation — that stays the
                # text-only path's job below, since a numeric event's own
                # real surprise is already known the instant it resolves,
                # no price data or Dukascopy fetch required.
                for instrument in INSTRUMENTS.keys():
                    try:
                        prediction = get_latest_prediction_for_occurrence(bt_conn, event.event_title, instrument, event_time)
                    except Exception as exc:  # noqa: BLE001 — one bad lookup must not crash the whole build
                        print(f"[webapp.history] WARNING: could not read fallback prediction for {event.event_title}/{instrument}: {exc}")
                        continue
                    if prediction is None:
                        continue  # never scored for this instrument at this occurrence — no row, not shown with blanks

                    fallback_outcome: Optional[str] = None
                    fallback_unjudged_reason: Optional[str] = None
                    if prediction.confidence <= NO_HIT_CONFIDENCE:
                        fallback_unjudged_reason = "shrug"
                    elif prediction.direction == "neutral":
                        fallback_unjudged_reason = "shrug"  # no directional call made — nothing to invert or compare
                    elif event.surprise_direction is None:
                        fallback_unjudged_reason = "unknown_surprise"
                    else:
                        implied_surprise = _implied_surprise_direction(event.event_title, instrument, prediction.direction)
                        fallback_outcome = "Confirmed" if implied_surprise == event.surprise_direction else "Missed"

                    rows.append(HistoryRow(
                        event_title=event.event_title,
                        event_time_utc=event.event_time_utc,
                        instrument=instrument,
                        previous=event.previous,
                        forecast=event.forecast,
                        actual=event.actual,
                        unchanged_vs_previous=(event.actual == event.previous),
                        ne_prediction=prediction.direction,
                        ne_confidence=prediction.confidence,
                        outcome=fallback_outcome,
                        unjudged_reason=fallback_unjudged_reason,
                        source=(
                            "seeded" if "seeded" in (event.source, prediction.source)
                            else "live_web_fallback" if "live_web_fallback" in (event.source, prediction.source)
                            else "cloud_web_fallback" if "cloud_web_fallback" in (event.source, prediction.source)
                            else "fred" if "fred" in (event.source, prediction.source)
                            else "live"
                        ),
                    ))
                continue  # resolved event, no print-direction call — either shown via the fallback above or excluded per-instrument, never with blanks

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
                # falling back to 'live'. 'fred' (data_layer/fred_actuals.py's
                # live actual-value fallback, landed 2026-08-26) follows the
                # same reasoning as 'live_web_fallback' — it only ever lands
                # in event_history, never in call.source, but checking both
                # sides costs nothing and keeps this resilient to a future
                # write path. 'cloud_web_fallback' follows the same reasoning:
                # checked before 'fred' to respect its priority in the fallback
                # chain (see task-1-brief.md). Must genuinely distinguish all five
                # values — never collapse to a live/seeded boolean.
                source=(
                    "seeded" if "seeded" in (event.source, call.source)
                    else "live_web_fallback" if "live_web_fallback" in (event.source, call.source)
                    else "cloud_web_fallback" if "cloud_web_fallback" in (event.source, call.source)
                    else "fred" if "fred" in (event.source, call.source)
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
