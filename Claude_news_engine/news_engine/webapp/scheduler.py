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


def run_scoring_cycle(tracked_symbols: list[str], db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    try:
        all_events = fetch_calendar("thisweek")
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop or wipe existing data
        print(f"[scheduler] WARNING: calendar fetch failed, keeping existing data: {exc}")
        conn.close()
        return

    events = filter_relevant_events(all_events)

    for ticker in tracked_symbols:
        try:
            symbol_class = classify_symbol(ticker)
        except UnrecognizedSymbolError as exc:
            print(f"[scheduler] WARNING: skipping unrecognized symbol {ticker!r}: {exc}")
            continue

        for event in events:
            result = score_event_for_symbol(event, symbol_class)
            if not result.applicable or result.pending:
                continue

            existing = get_latest_two(conn, ticker, event.title)
            if existing and abs(existing[0].probability - result.probability) < 1e-6:
                continue  # unchanged since last cycle, don't write a duplicate row

            record_run(
                conn, ticker, event.title, event.event_time_utc,
                result.probability, result.direction.value, result.raw_score,
            )
            print(f"[scheduler] recorded {ticker} / {event.title}: {result.probability:.0%} {result.direction.value}")

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
