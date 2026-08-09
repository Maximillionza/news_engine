"""
Background poll loop — re-fetches the calendar and re-scores every
tracked symbol against every applicable high-impact USD event on an
ADAPTIVE interval (see compute_adaptive_interval_seconds), persisting a
new row only when the score actually changed from the last stored run
(avoids writing identical rows every cycle when nothing new has printed).
"""
from __future__ import annotations

import datetime as dt
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from config.settings import EVENT_SURPRISE_DIRECTION
from data_layer.calendar_feed import EconomicEvent, fetch_calendar, filter_relevant_events
from webapp.scoring_service import score_event_for_symbol
from webapp.store import get_connection, record_run, get_latest_two
from webapp.symbols import classify_symbol, UnrecognizedSymbolError

# Event dates/forecasts are published well ahead of time — nothing
# meaningful changes until close to release (or briefly after, in case
# a release is delayed). Polling flat-interval all week wastes cycles
# for no benefit, so the interval tightens only when a relevant event is
# actually close. Shared by the scheduler loop below AND webapp/app.py's
# calendar cache TTL — same "how urgent is this right now" question,
# answered once.
FAR_INTERVAL_SECONDS = 60 * 60      # >48h from the nearest unresolved event (or no events at all)
NORMAL_INTERVAL_SECONDS = 15 * 60   # 48h -> 4h out — the old flat default, now just the middle tier
NEAR_INTERVAL_SECONDS = 5 * 60      # final 4h, or within the post-release grace window

NEAR_WINDOW_HOURS = 4
FAR_THRESHOLD_HOURS = 48
POST_RELEASE_GRACE_MINUTES = 30     # keep polling tightly briefly after the scheduled time, in case the release is delayed

SCHEDULER_INTERVAL_SECONDS = NORMAL_INTERVAL_SECONDS  # fallback used when a cycle's fetch fails and there's no fresh event list to reason from


def compute_adaptive_interval_seconds(
    events: Optional[list[EconomicEvent]],
    now: Optional[dt.datetime] = None,
) -> int:
    """
    Tightest interval any still-unresolved event demands, or
    FAR_INTERVAL_SECONDS if nothing needs urgency (including when
    `events` is None, e.g. after a failed fetch — NORMAL_INTERVAL_SECONDS
    is used by callers directly in that case instead, see SCHEDULER_INTERVAL_SECONDS).
    An event with `actual` already set is resolved and no longer forces
    a tight interval, regardless of how recently it printed.
    """
    if not events:
        return FAR_INTERVAL_SECONDS

    now = now or dt.datetime.now(dt.timezone.utc)
    tightest = FAR_INTERVAL_SECONDS
    for event in events:
        if event.actual:
            continue  # already resolved — doesn't need tight polling anymore
        hours_until = (event.event_time_utc - now).total_seconds() / 3600.0
        if -POST_RELEASE_GRACE_MINUTES / 60.0 <= hours_until <= NEAR_WINDOW_HOURS:
            return NEAR_INTERVAL_SECONDS  # tightest possible — stop scanning, nothing beats it
        if hours_until <= FAR_THRESHOLD_HOURS:
            tightest = min(tightest, NORMAL_INTERVAL_SECONDS)
    return tightest


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


def run_scoring_cycle(tracked_symbols: list[str], db_path: Optional[Path] = None) -> Optional[list[EconomicEvent]]:
    """
    Returns the fetched (Medium+ impact) events on success, or None if
    the calendar fetch failed — the caller (start_scheduler's loop) uses
    this to pick the next adaptive poll interval; a failed fetch means
    "no fresh info to reason from," not "nothing is urgent."
    """
    conn = get_connection(db_path)
    try:
        all_events = fetch_calendar("thisweek")
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop or wipe existing data
        print(f"[scheduler] WARNING: calendar fetch failed, keeping existing data: {exc}")
        conn.close()
        return None

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
                    # pending=True fires for two different reasons: (a) the event
                    # genuinely hasn't printed an actual yet (will resolve later), or
                    # (b) the event's title isn't in EVENT_SURPRISE_DIRECTION at all
                    # (will NEVER resolve). Only persist+track (a) — persisting (b)
                    # would create a dashboard card stuck on "Awaiting next tracked
                    # event" forever, since events[0] in /api/predictions picks
                    # whichever event is soonest and this one can never score.
                    if event.title not in EVENT_SURPRISE_DIRECTION:
                        continue
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

    return events


def start_scheduler(tracked_symbols_provider: Callable[[], list[str]]) -> None:
    """
    tracked_symbols_provider: a zero-arg callable returning the current
    list of tracked tickers (called fresh each cycle, so symbols added/
    removed via the API take effect without restarting the scheduler).
    """
    def _loop():
        while True:
            try:
                events = run_scoring_cycle(tracked_symbols_provider())
                interval = (
                    SCHEDULER_INTERVAL_SECONDS if events is None  # fetch failed — retry at the moderate default, not too aggressive against a possibly-down feed, not too sparse either
                    else compute_adaptive_interval_seconds(events)
                )
            except Exception as exc:  # noqa: BLE001 — the loop must survive any unhandled error
                print(f"[scheduler] ERROR: scoring cycle failed, will retry next interval: {exc}")
                interval = SCHEDULER_INTERVAL_SECONDS
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
