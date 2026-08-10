"""
Manual outcome confirmation for the article-based backtest accumulator.
Lists every prediction whose event has passed with no recorded outcome
yet, and prompts for the real result — same research rigor as this
project's reconstructed backtest cases (tests/run_historical_backtest.py),
just applied to real predictions made blind (before the event actually
happened), not reconstructed after the fact.

Usage:
    python scripts/confirm_backtest_outcomes.py          # interactive
    python scripts/confirm_backtest_outcomes.py --list   # list only, no prompts
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import get_connection, get_predictions_awaiting_outcome, record_outcome


def main():
    list_only = "--list" in sys.argv
    conn = get_connection()
    awaiting = get_predictions_awaiting_outcome(conn)

    if not awaiting:
        print("Nothing awaiting confirmation — every past prediction already has a recorded outcome.")
        conn.close()
        return

    print(f"{len(awaiting)} prediction(s) awaiting outcome confirmation:\n")
    for p in awaiting:
        print(f"  {p.instrument} / {p.event_title} ({p.event_time_utc}) — "
              f"predicted {p.direction.upper()} {p.probability:.0%}, "
              f"{p.confidence:.0%} confidence, {p.article_count} articles")

    if list_only:
        conn.close()
        return

    print("\nFor each, research the real outcome and enter it below (blank direction to skip):\n")
    for p in awaiting:
        print(f"--- {p.instrument} / {p.event_title} ({p.event_time_utc}) ---")
        print(f"    predicted: {p.direction.upper()} {p.probability:.0%}")
        direction = input("    actual direction (bullish/bearish/neutral, blank to skip): ").strip().lower()
        if not direction:
            print("    skipped.\n")
            continue
        if direction not in {"bullish", "bearish", "neutral"}:
            print(f"    {direction!r} is not bullish/bearish/neutral — skipped.\n")
            continue
        note = input("    real outcome note (what actually happened, with source): ").strip()
        event_time = dt.datetime.fromisoformat(p.event_time_utc)
        record_outcome(conn, p.event_title, p.instrument, event_time, direction, note)
        print("    recorded.\n")

    conn.close()


if __name__ == "__main__":
    main()
