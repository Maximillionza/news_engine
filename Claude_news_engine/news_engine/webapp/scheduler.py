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
# for no benefit — and Forex Factory's free feed has a real rate limit
# (observed live: repeated 429s from polling too often) — so the interval
# tightens only as a relevant event actually approaches. Shared by the
# scheduler loop below AND webapp/app.py's calendar cache TTL — same "how
# urgent is this right now" question, answered once.
FAR_INTERVAL_SECONDS = 12 * 60 * 60     # baseline: event isn't "today" yet (or no events at all)
RAMP_INTERVAL_SECONDS = 60 * 60         # event IS today, but still more than 1h out
FINAL_INTERVAL_SECONDS = 5 * 60         # final hour before the event, through the post-release grace window
SENSE_CHECK_INTERVAL_SECONDS = 60       # extra-tight check for a just-rescheduled event within its final 15 minutes

RAMP_WINDOW_HOURS = 24              # "ramp up on the day of the event" — approximated as the last 24h
FINAL_WINDOW_HOURS = 1              # "final check 1 hour before the event"
SENSE_CHECK_WINDOW_MINUTES = 15     # "a final sense check 15 min before" — only for a JUST-rescheduled event
POST_RELEASE_GRACE_MINUTES = 30     # keep polling tightly briefly after the scheduled time, in case the release is delayed

SCHEDULER_INTERVAL_SECONDS = RAMP_INTERVAL_SECONDS  # fallback used when a cycle's fetch fails and there's no fresh event list to reason from


def compute_adaptive_interval_seconds(
    events: Optional[list[EconomicEvent]],
    now: Optional[dt.datetime] = None,
    previous_events: Optional[list[EconomicEvent]] = None,
) -> int:
    """
    Tightest interval any still-unresolved event demands, or
    FAR_INTERVAL_SECONDS if nothing needs urgency (including when
    `events` is None, e.g. after a failed fetch — SCHEDULER_INTERVAL_SECONDS
    is used by callers directly in that case instead). An event with
    `actual` already set is resolved and no longer forces a tight
    interval, regardless of how recently it printed.

    `previous_events` (the prior successful fetch, matched by title) lets
    a just-detected reschedule — this event's event_time_utc shifted
    since it was last seen — trigger SENSE_CHECK_INTERVAL_SECONDS
    specifically in the final SENSE_CHECK_WINDOW_MINUTES before the NEW
    (adjusted) time: tighter than the standard final-hour cadence, since a
    just-moved event deserves closer attention than a stable one. Without
    `previous_events`, reschedule detection is simply skipped — no crash,
    just no extra tightening.
    """
    if not events:
        return FAR_INTERVAL_SECONDS

    now = now or dt.datetime.now(dt.timezone.utc)
    previous_time_by_title = {e.title: e.event_time_utc for e in (previous_events or [])}

    tightest = FAR_INTERVAL_SECONDS
    for event in events:
        if event.actual:
            continue  # already resolved — doesn't need tight polling anymore
        hours_until = (event.event_time_utc - now).total_seconds() / 3600.0

        previous_time = previous_time_by_title.get(event.title)
        was_just_rescheduled = previous_time is not None and previous_time != event.event_time_utc
        if was_just_rescheduled and 0 <= hours_until <= SENSE_CHECK_WINDOW_MINUTES / 60.0:
            return SENSE_CHECK_INTERVAL_SECONDS  # tightest possible — stop scanning, nothing beats it

        if -POST_RELEASE_GRACE_MINUTES / 60.0 <= hours_until <= FINAL_WINDOW_HOURS:
            tightest = min(tightest, FINAL_INTERVAL_SECONDS)
            continue

        if hours_until <= RAMP_WINDOW_HOURS:
            tightest = min(tightest, RAMP_INTERVAL_SECONDS)
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
        previous_events: Optional[list[EconomicEvent]] = None
        while True:
            try:
                events = run_scoring_cycle(tracked_symbols_provider())
                if events is None:
                    # fetch failed — retry at the moderate default, not too
                    # aggressive against a possibly-down feed, not too sparse
                    # either. previous_events is deliberately left as-is (not
                    # cleared) so a reschedule detected before this failure
                    # is still comparable against once a fetch succeeds again.
                    interval = SCHEDULER_INTERVAL_SECONDS
                else:
                    interval = compute_adaptive_interval_seconds(events, previous_events=previous_events)
                    previous_events = events
            except Exception as exc:  # noqa: BLE001 — the loop must survive any unhandled error
                print(f"[scheduler] ERROR: scoring cycle failed, will retry next interval: {exc}")
                interval = SCHEDULER_INTERVAL_SECONDS
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
