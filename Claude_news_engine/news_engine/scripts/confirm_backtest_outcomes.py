"""
Manual outcome confirmation for the article-based backtest accumulator.
Lists every prediction whose event has passed with no recorded outcome
yet, and prompts for the real result — same research rigor as this
project's reconstructed backtest cases (tests/run_historical_backtest.py),
just applied to real predictions made blind (before the event actually
happened), not reconstructed after the fact.

--auto runs a Dukascopy-based auto-confirm pass first (see
scoring/outcome_classifier.py and
docs/superpowers/specs/2026-08-10-dukascopy-outcome-confirmation-design.md):
clear post-event price moves get recorded automatically, everything
ambiguous or fetch-failed is left exactly where it already was — the
existing awaiting-outcome queue, unchanged — with its computed
classification shown alongside the manual prompt as a suggestion.

Usage:
    python scripts/confirm_backtest_outcomes.py          # interactive
    python scripts/confirm_backtest_outcomes.py --list   # list only, no prompts
    python scripts/confirm_backtest_outcomes.py --auto   # auto-confirm phase, then interactive for what's left
    python scripts/confirm_backtest_outcomes.py --auto --list   # auto-confirm phase, then list what's left, no prompts
"""
import sys
import os
import datetime as dt
from contextlib import closing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import (
    get_connection, get_predictions_awaiting_outcome, record_outcome, record_dismissal,
)
from scoring.outcome_classifier import classify


def run_auto_confirm_phase(conn) -> dict:
    """
    Runs the Dukascopy auto-confirm pass over everything currently awaiting
    outcome. Returns {"auto_confirmed": int, "left_for_review": int,
    "suggestions": dict} — suggestions maps (event_title, instrument,
    event_time_utc) to the ClassificationResult computed for that row, so
    the interactive loop can show a leftover row's already-computed
    classification instead of re-fetching it.
    """
    awaiting = get_predictions_awaiting_outcome(conn)
    auto_confirmed = 0
    suggestions = {}
    for p in awaiting:
        event_time = dt.datetime.fromisoformat(p.event_time_utc)
        result = classify(p.instrument, event_time)
        if result.direction is not None:
            record_outcome(conn, p.event_title, p.instrument, event_time, result.direction.value, result.note)
            auto_confirmed += 1
            print(f"  [auto] {p.instrument} / {p.event_title}: {result.note}")
        else:
            suggestions[(p.event_title, p.instrument, p.event_time_utc)] = result
    left_for_review = len(awaiting) - auto_confirmed
    return {"auto_confirmed": auto_confirmed, "left_for_review": left_for_review, "suggestions": suggestions}


def main():
    list_only = "--list" in sys.argv
    auto = "--auto" in sys.argv

    with closing(get_connection()) as conn:
        suggestions = {}
        if auto:
            summary = run_auto_confirm_phase(conn)
            suggestions = summary["suggestions"]
            print(f"\nAuto-confirm: {summary['auto_confirmed']} confirmed, {summary['left_for_review']} left for review.\n")

        awaiting = get_predictions_awaiting_outcome(conn)

        if not awaiting:
            print("Nothing awaiting confirmation — every past prediction already has a recorded outcome.")
            return

        print(f"{len(awaiting)} prediction(s) awaiting outcome confirmation:\n")
        for p in awaiting:
            print(f"  {p.instrument} / {p.event_title} ({p.event_time_utc}) — "
                  f"predicted {p.direction.upper()} {p.probability:.0%}, "
                  f"{p.confidence:.0%} confidence, {p.article_count} articles")

        if list_only:
            return

        print("\nFor each, research the real outcome and enter it below.")
        print("Blank to skip for now (asked again next run). 'd' to dismiss for good — use this")
        print("when the event was rescheduled or canceled and a real outcome will never arrive;")
        print("otherwise a stale prediction sits in this queue forever.\n")
        for p in awaiting:
            print(f"--- {p.instrument} / {p.event_title} ({p.event_time_utc}) ---")
            print(f"    predicted: {p.direction.upper()} {p.probability:.0%}")
            suggestion = suggestions.get((p.event_title, p.instrument, p.event_time_utc))
            if suggestion is not None:
                print(f"    {suggestion.note}")
            direction = input("    actual direction (bullish/bearish/neutral, 'd' to dismiss, blank to skip): ").strip().lower()
            event_time = dt.datetime.fromisoformat(p.event_time_utc)
            if not direction:
                print("    skipped — will be asked again next run.\n")
                continue
            if direction == "d":
                reason = input("    dismissal reason (e.g. 'rescheduled', 'canceled', with source): ").strip()
                if not reason:
                    print("    dismissal needs a reason — skipped.\n")
                    continue
                record_dismissal(conn, p.event_title, p.instrument, event_time, reason)
                print("    dismissed — will not be asked again.\n")
                continue
            if direction not in {"bullish", "bearish", "neutral"}:
                print(f"    {direction!r} is not bullish/bearish/neutral/d — skipped.\n")
                continue
            note = input("    real outcome note (what actually happened, with source): ").strip()
            record_outcome(conn, p.event_title, p.instrument, event_time, direction, note)
            print("    recorded.\n")


if __name__ == "__main__":
    main()
