"""
Background poll loop — every SCHEDULER_INTERVAL_SECONDS, re-fetches the
calendar and re-scores every tracked symbol against every applicable
high-impact USD event, persisting a new row only when the score actually
changed from the last stored run (avoids writing identical rows every
cycle when nothing new has printed).
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable, Optional

from data_layer.calendar_feed import fetch_calendar, filter_relevant_events
from webapp.scoring_service import score_event_for_symbol
from webapp.store import get_connection, record_run, get_latest_two
from webapp.symbols import classify_symbol, UnrecognizedSymbolError

SCHEDULER_INTERVAL_SECONDS = 15 * 60


def _scores_equal(prob_a: Optional[float], dir_a: str, prob_b: Optional[float], dir_b: str) -> bool:
    """
    True when a newly-computed score is indistinguishable from the most
    recently persisted one, so scheduler cycles don't write duplicate rows.
    Direction must match, and probabilities must either both be None
    (pending == pending) or both be present and within float tolerance —
    a None vs. a real number (pending -> released) is always a change.
    """
    if dir_a != dir_b:
        return False
    if prob_a is None or prob_b is None:
        return prob_a is None and prob_b is None
    return abs(prob_a - prob_b) < 1e-6


def run_scoring_cycle(tracked_symbols: list[str], db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    try:
        all_events = fetch_calendar("thisweek")
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop or wipe existing data
        print(f"[scheduler] WARNING: calendar fetch failed, keeping existing data: {exc}")
        conn.close()
        return

    # Medium (not just High) so precursor-style events (ADP, PPI m/m, Import
    # Prices, Challenger Job Cuts) reach scoring — see PRECURSOR_EVENTS /
    # EVENT_SURPRISE_DIRECTION in config/settings.py.
    events = filter_relevant_events(all_events, min_impact="Medium")

    try:
        for ticker in tracked_symbols:
            try:
                symbol_class = classify_symbol(ticker)
            except UnrecognizedSymbolError as exc:
                print(f"[scheduler] WARNING: skipping unrecognized symbol {ticker!r}: {exc}")
                continue

            for event in events:
                result = score_event_for_symbol(event, symbol_class)
                if not result.applicable:
                    continue  # fx_cross — no USD exposure, never scored at all

                if result.pending:
                    new_probability: Optional[float] = None
                    new_direction = "pending"
                    new_raw_score: Optional[float] = None
                else:
                    new_probability = result.probability
                    new_direction = result.direction.value
                    new_raw_score = result.raw_score

                existing = get_latest_two(conn, ticker, event.title)
                if existing and _scores_equal(existing[0].probability, existing[0].direction, new_probability, new_direction):
                    continue  # unchanged since last cycle, don't write a duplicate row

                record_run(
                    conn, ticker, event.title, event.event_time_utc,
                    new_probability, new_direction, new_raw_score,
                )
                if result.pending:
                    print(f"[scheduler] recorded {ticker} / {event.title}: pending")
                else:
                    print(f"[scheduler] recorded {ticker} / {event.title}: {new_probability:.0%} {new_direction}")
    finally:
        conn.close()


def start_scheduler(tracked_symbols_provider: Callable[[], list[str]]) -> None:
    """
    tracked_symbols_provider: a zero-arg callable returning the current
    list of tracked tickers (called fresh each cycle, so symbols added/
    removed via the API take effect without restarting the scheduler).
    """
    def _loop():
        while True:
            run_scoring_cycle(tracked_symbols_provider())
            time.sleep(SCHEDULER_INTERVAL_SECONDS)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
