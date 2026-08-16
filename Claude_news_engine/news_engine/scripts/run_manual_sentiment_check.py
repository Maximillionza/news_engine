"""
Manual, once-off article-based sentiment check for a single event —
same real pipeline (scoring/backtest_accumulator.py's score_and_record_event())
scoring/backtest_accumulator.py's own windowed loop uses (real article
fetch, precursors, print call, trend signal, Kalshi read, score_bundle()
per instrument), run directly against a target event even if it hasn't
entered its automatic PRE_EVENT_WINDOW_HOURS window yet.

Why this exists: the accumulator only scores an event once it's within
PRE_EVENT_WINDOW_HOURS (72h) of release, on its own adaptive polling
cadence. For "what's sentiment on X looking like right now" for an event
further out than that, this script runs the exact same real pipeline
once, on demand.

Persistence: writes through scoring/backtest_store.record_prediction()
via the SAME _is_material_change() gate the normal cycle uses — a
result is only written if it's the first-ever read for this occurrence,
or a real direction flip / >=10pp probability move from what's already
stored. That's what makes the write persist across dashboard refreshes
and survive until a LATER read genuinely changes it — not a new
mechanism, the existing one, reused outside its normal trigger window.
webapp/app.py's /api/predictions already surfaces this as
`article_prediction` on the matching dashboard card.

Usage:
    python scripts/run_manual_sentiment_check.py "FOMC Meeting Minutes"

Looks the event up in webapp.store's currently-persisted calendar
snapshot (no new live Forex Factory fetch — reuses whatever's already
there) and matches by title, nearest future occurrence. Exits with a
clear message if the title isn't found. Makes REAL calls to whatever
article sources are configured (Alpha Vantage / APITube / RSS) and to
Kalshi — real API budget is spent, same as a normal accumulator cycle.
"""
from __future__ import annotations

import sys
import os
import argparse
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import INSTRUMENTS
from data_layer.calendar_feed import EconomicEvent, fetch_calendar
from data_layer.rss_sources import build_all_preview_sources
from scoring.backtest_accumulator import score_and_record_event
from scoring.backtest_store import get_connection
import webapp.store as dash_store


def _find_target_event(title: str, now: dt.datetime) -> EconomicEvent | None:
    """
    Looks up `title` in webapp.store's persisted calendar_snapshot first
    (no new live FF fetch — reuses whatever the dashboard already has),
    picking the nearest occurrence at or after `now`. Falls back to a
    fresh live fetch ONLY if the snapshot has nothing for this title at
    all — still just one fetch, respecting data_layer.calendar_feed's
    cooldown/fail-open contract like every other caller.
    """
    conn = dash_store.get_connection()
    try:
        snapshot = dash_store.get_calendar_snapshot(conn)
    finally:
        conn.close()

    candidates = []
    if snapshot is not None:
        candidates = [e for e in snapshot.events if e["title"] == title]
    if candidates:
        upcoming = [e for e in candidates if dt.datetime.fromisoformat(e["event_time_utc"]) >= now]
        chosen = min(upcoming or candidates, key=lambda e: dt.datetime.fromisoformat(e["event_time_utc"]))
        return EconomicEvent(
            title=chosen["title"], country=chosen["country"], impact=chosen["impact"],
            event_time_utc=dt.datetime.fromisoformat(chosen["event_time_utc"]),
            forecast=chosen.get("forecast"), previous=chosen.get("previous"), actual=chosen.get("actual"),
        )

    print(f"[run_manual_sentiment_check] {title!r} not in the persisted calendar snapshot — trying one live fetch.")
    try:
        all_events = fetch_calendar("thisweek")
    except Exception as exc:  # noqa: BLE001 — same fail-open contract as every other fetch_calendar() caller
        print(f"[run_manual_sentiment_check] WARNING: live fetch failed: {exc}")
        return None
    upcoming = [e for e in all_events if e.title == title and e.event_time_utc >= now]
    if not upcoming:
        return None
    return min(upcoming, key=lambda e: e.event_time_utc)


def run(title: str, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    event = _find_target_event(title, now)
    if event is None:
        print(f"[run_manual_sentiment_check] No upcoming occurrence of {title!r} found — nothing to score.")
        return {}

    print(f"[run_manual_sentiment_check] Target: {event.title} @ {event.event_time_utc.isoformat()}")

    try:
        all_events = fetch_calendar("thisweek")
    except Exception as exc:  # noqa: BLE001 — precursor lookup is best-effort; a fetch failure here shouldn't block scoring
        print(f"[run_manual_sentiment_check] WARNING: could not fetch the full calendar for precursor lookup: {exc}")
        all_events = [event]

    sources = build_all_preview_sources()
    conn = get_connection()
    try:
        results = score_and_record_event(conn, event, all_events, list(INSTRUMENTS.keys()), sources, now=now)
    finally:
        conn.close()

    for instrument, result in results.items():
        print(f"[run_manual_sentiment_check] {instrument}: {result.summary()}")
    if not results:
        print("[run_manual_sentiment_check] No instrument produced a result — see warnings above.")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="Exact event title to check, e.g. 'FOMC Meeting Minutes'")
    args = parser.parse_args()
    run(args.title)
