"""
Background accumulator for the article-based backtest log — periodically
checks the calendar for high-impact USD events, and for tracked
instruments, runs the REAL article-based scoring pipeline
(scoring/probability_engine.py, not the essence-only dashboard path) and
persists each prediction to scoring/backtest_store.py's log — a genuine,
growing record of real predictions made blind, before the event, to be
confirmed against real outcomes later via scripts/confirm_backtest_outcomes.py.

Also blends in structured precursor data: already-released leading
indicators (e.g. PPI before CPI, ADP before NFP — see config.settings'
PRECURSOR_EVENTS and data_layer.calendar_feed.find_precursor_events())
get passed into score_bundle() alongside article sentiment, found
against the FULL unfiltered calendar since precursors are typically
Medium impact. Not every event has a configured precursor, and a
precursor with nothing released yet in the target's pre-event window
contributes nothing — both are normal, not a bug.

Deliberately NOT wired into webapp/ — the dashboard is essence-only by
design (no article fetching at all); this accumulator is article-based
and a distinct concern, run as its own standalone process.

CHECKS every instrument for every active (pre-event-window) event on
EVERY cycle — no separate per-pair check budget. Cadence is governed
entirely by the accumulator's own outer loop (compute_adaptive_interval_seconds,
imported below): 12h baseline days out, hourly once an event is within
24h, 5min in the final hour. Whether a check actually gets WRITTEN to
scoring/backtest_store.py's log is a completely separate decision, gated
purely by _is_material_change() — a direction flip (contradicts), or a
same-direction move of at least MATERIAL_CHANGE_THRESHOLD_PROBABILITY (a
stronger indication). Supporting articles that just reinforce the
existing read are checked, scored, and discarded without a write —
"current sentiment is the truth until articles are found to contradict
or change it," per explicit product decision.

**Revised 2026-08-11, correcting a real gap**: the original design only
checked twice total per pair (window entry + a narrow final-30min
stretch), which meant a genuine news shift building over most of a
multi-day pre-event window was never picked up — observed live, CPI
predictions sat unchanged with an identical scored_at_utc for a full 24
hours despite the accumulator process running the whole time. Checking
every cycle instead of twice is a REAL, DELIBERATE increase in article-
fetch volume (RSS + Alpha Vantage) — roughly an order of magnitude more
calls per event over its full pre-event lifetime than the old design.
Alpha Vantage's free tier is 25 requests/day; watch it. If this becomes
a problem in practice, the fix is re-introducing a check-frequency cap
(NOT reverting to a recorded-snapshot budget — that's what caused the
original gap).
"""
from __future__ import annotations

import datetime as dt
import threading
import time
from pathlib import Path
from typing import Optional

from data_layer.calendar_feed import fetch_calendar, filter_relevant_events, events_in_pre_window, find_precursor_events
from data_layer.event_context import build_event_news_bundle
from data_layer.rss_sources import build_all_preview_sources
from scoring.probability_engine import score_bundle
from scoring.backtest_store import get_connection, record_prediction, get_latest_prediction
from webapp.scheduler import compute_adaptive_interval_seconds

# A same-direction probability move smaller than this is "supporting" the
# current sentiment, not changing it — no write. 0.10 = 10 percentage
# points (e.g. stored BULLISH 65% -> new read BULLISH 71% is NOT material;
# BULLISH 65% -> BULLISH 76% IS). A direction flip is always material,
# regardless of this threshold — see _is_material_change().
MATERIAL_CHANGE_THRESHOLD_PROBABILITY = 0.10
# Used when a calendar fetch fails and there's no fresh event list to
# reason an adaptive interval from — same fallback pattern as
# webapp/scheduler.py's SCHEDULER_INTERVAL_SECONDS.
ACCUMULATOR_FALLBACK_INTERVAL_SECONDS = 15 * 60


def _is_material_change(new_direction: str, new_probability: float, current_direction: str, current_probability: float) -> bool:
    """
    True if a freshly-scored read is different ENOUGH from the current
    latest recorded prediction to be worth writing a new snapshot for —
    "current sentiment is the truth until articles are found to contradict
    or change it." A direction flip (including into/out of neutral) is
    always material, regardless of magnitude — that's a contradiction of
    the current read, not a matter of degree. Within the same direction,
    only a move of at least MATERIAL_CHANGE_THRESHOLD_PROBABILITY counts —
    supporting articles that just reinforce the existing call add to its
    validity without triggering a rewrite.
    """
    if new_direction != current_direction:
        return True
    # 1e-9 tolerance for float imprecision — e.g. 0.75 - 0.65 == 0.09999999999999998
    # in IEEE754, which would otherwise fail an exact-boundary >= comparison
    # for what's really a value AT the threshold.
    return abs(new_probability - current_probability) >= MATERIAL_CHANGE_THRESHOLD_PROBABILITY - 1e-9


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

        sources = None  # lazily built, only if at least one event is actually active this cycle
        for event in active:
            # Every tracked instrument is checked for every active event on
            # every cycle — no per-pair check budget (see module docstring
            # for why, and the real fetch-volume cost of this). The article
            # bundle is still fetched at most once per EVENT, not once per
            # instrument — identical across instruments for a given event.
            if sources is None:
                sources = build_all_preview_sources()

            try:
                bundle = build_event_news_bundle(event, sources, query="", mode="live")
            except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop
                print(f"[backtest_accumulator] WARNING: article fetch failed for {event.title}: {exc}")
                continue

            # Against the FULL unfiltered calendar (all_events), not the
            # High-impact-only `events` list above — precursors like ADP,
            # PPI m/m are typically Medium impact and would be silently
            # excluded if this searched the filtered list instead. Same
            # per-event, once-not-per-instrument reasoning as the article
            # bundle above: precursor relationships are about the EVENT,
            # not which instrument is being scored.
            precursors = find_precursor_events(event, all_events)
            if precursors:
                print(f"[backtest_accumulator] precursors for {event.title}: {[p.title for p in precursors]}")

            for instrument in instruments:
                try:
                    result = score_bundle(bundle, instrument, precursor_events=precursors)
                except Exception as exc:  # noqa: BLE001 — one pair's failure must not stop the others
                    print(f"[backtest_accumulator] WARNING: scoring failed for {instrument}/{event.title}: {exc}")
                    continue

                latest = get_latest_prediction(conn, event.title, instrument)
                if latest is not None and not _is_material_change(
                    result.direction.value, result.probability, latest.direction, latest.probability,
                ):
                    print(
                        f"[backtest_accumulator] checked {instrument} / {event.title}: "
                        f"{result.summary()} — unchanged from current, not recorded"
                    )
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
