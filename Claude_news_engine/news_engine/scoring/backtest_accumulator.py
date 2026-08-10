"""
Background accumulator for the article-based backtest log — periodically
checks the calendar for high-impact USD events, and for tracked
instruments, runs the REAL article-based scoring pipeline
(scoring/probability_engine.py, not the essence-only dashboard path) and
persists each prediction to scoring/backtest_store.py's log — a genuine,
growing record of real predictions made blind, before the event, to be
confirmed against real outcomes later via scripts/confirm_backtest_outcomes.py.

Deliberately NOT wired into webapp/ — the dashboard is essence-only by
design (no article fetching at all); this accumulator is article-based
and a distinct concern, run as its own standalone process.

Budget-capped, not continuous: article fetches (RSS + Alpha Vantage) are
rate-limited resources, unlike the dashboard's free essence-only scoring.
At most SNAPSHOT_BUDGET_PER_PAIR prediction snapshots per (event,
instrument) pair — one when the event enters its pre-event window, one
more only once inside the final NEAR_WINDOW_HOURS stretch (same "how
close is close" definition as webapp/scheduler.py, reused directly
rather than re-defined).
"""
from __future__ import annotations

import datetime as dt
import threading
import time
from pathlib import Path
from typing import Optional

from data_layer.calendar_feed import fetch_calendar, filter_relevant_events, events_in_pre_window
from data_layer.event_context import build_event_news_bundle
from data_layer.rss_sources import build_all_preview_sources
from scoring.probability_engine import score_bundle
from scoring.backtest_store import get_connection, record_prediction, count_predictions
from webapp.scheduler import compute_adaptive_interval_seconds, NEAR_WINDOW_HOURS

SNAPSHOT_BUDGET_PER_PAIR = 2
# Used when a calendar fetch fails and there's no fresh event list to
# reason an adaptive interval from — same fallback pattern as
# webapp/scheduler.py's SCHEDULER_INTERVAL_SECONDS.
ACCUMULATOR_FALLBACK_INTERVAL_SECONDS = 15 * 60


def run_accumulator_cycle(
    instruments: list[str],
    db_path: Optional[Path] = None,
    now: Optional[dt.datetime] = None,
) -> Optional[list]:
    """
    Returns the fetched high-impact events on success (the caller uses
    this to pick the next adaptive poll interval), or None if the
    calendar fetch failed.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    conn = get_connection(db_path)
    try:
        try:
            all_events = fetch_calendar("thisweek")
        except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop
            print(f"[backtest_accumulator] WARNING: calendar fetch failed: {exc}")
            return None

        # High-impact only (default) — article fetches are budget-limited,
        # unlike the dashboard's free essence-only scoring which widens to Medium.
        events = filter_relevant_events(all_events)
        active = events_in_pre_window(events, now_utc=now)

        sources = None  # lazily built, only if at least one pair actually needs a fetch this cycle
        for event in active:
            hours_until = (event.event_time_utc - now).total_seconds() / 3600.0

            # Figure out which instruments actually need a snapshot this
            # cycle BEFORE fetching anything — the article bundle is
            # identical across instruments for a given event, so it must
            # be fetched at most once per event, not once per instrument
            # (previously this doubled real API spend beyond the
            # intended SNAPSHOT_BUDGET_PER_PAIR budget).
            instruments_needing_snapshot = []
            for instrument in instruments:
                existing = count_predictions(conn, event.title, instrument, event.event_time_utc)
                if existing >= SNAPSHOT_BUDGET_PER_PAIR:
                    continue
                if existing == 1 and hours_until > NEAR_WINDOW_HOURS:
                    continue  # second snapshot only allowed in the final stretch
                instruments_needing_snapshot.append(instrument)

            if not instruments_needing_snapshot:
                continue

            if sources is None:
                sources = build_all_preview_sources()

            try:
                bundle = build_event_news_bundle(event, sources, query="", mode="live")
            except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop
                print(f"[backtest_accumulator] WARNING: article fetch failed for {event.title}: {exc}")
                continue

            for instrument in instruments_needing_snapshot:
                try:
                    result = score_bundle(bundle, instrument)
                except Exception as exc:  # noqa: BLE001 — one pair's failure must not stop the others
                    print(f"[backtest_accumulator] WARNING: scoring failed for {instrument}/{event.title}: {exc}")
                    continue

                record_prediction(
                    conn, event.title, instrument, event.event_time_utc,
                    result.probability, result.direction.value, result.confidence,
                    result.article_count, result.contradiction_flag,
                )
                print(f"[backtest_accumulator] recorded {instrument} / {event.title}: {result.summary()}")

        return events
    finally:
        conn.close()


def start_accumulator(instruments: list[str]) -> None:
    def _loop():
        while True:
            try:
                events = run_accumulator_cycle(instruments)
                interval = (
                    ACCUMULATOR_FALLBACK_INTERVAL_SECONDS if events is None
                    else compute_adaptive_interval_seconds(events)
                )
            except Exception as exc:  # noqa: BLE001 — the loop must survive any unhandled error
                print(f"[backtest_accumulator] ERROR: cycle failed, will retry next interval: {exc}")
                interval = ACCUMULATOR_FALLBACK_INTERVAL_SECONDS
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()


if __name__ == "__main__":
    from config.settings import INSTRUMENTS
    tracked = list(INSTRUMENTS.keys())
    print(f"Running one accumulator cycle for: {tracked}")
    run_accumulator_cycle(tracked)
    print("Done. For continuous operation, run scripts/run_accumulator.py instead.")
