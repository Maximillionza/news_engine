"""
Agent-run enrichment pass: fills in real, cited `actual` values for
events that still have none. Since ACT (2026-10-28) the engine's release
poller fills every numeric release the official publishers cover; this
manual tool is what remains for proprietary releases (ISM, UoM, PMIs, ...)
and anything the poller cannot reach. The cloud web-fallback queue that
used to feed it is retired.

This is NOT a live-service feature — WebSearch is only callable by an
agent session, not by webapp/scheduler.py's background loop. The
workflow is:
  1. An agent runs `python scripts/fill_missing_actuals.py --list` to
     see the numeric USD releases of the last 92 days with no actual
     (data_layer.official_actuals.coverage.missing_numeric_rows()).
  2. The agent researches each one via WebSearch, same citation
     standard as data_layer/historical_events.py's backfill facts —
     real data or absent, never guessed.
  3. The agent edits FACTS below (or calls run() directly, e.g. from an
     interactive Python session) with the researched (title,
     event_time_utc, actual, source_note) tuples, then runs the script
     for real (no --list) to write them.

Written rows get source='live_web_fallback' — distinct from 'live'
(Forex-Factory-sourced) and 'seeded' (pre-live-start historical
backfill), so this project can always tell which of the three
supplied a given actual.
"""
from __future__ import annotations

import sys
import os
import datetime as dt
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import LOCAL_TZ, UTC_TZ
from data_layer.calendar_feed import classify_surprise, EconomicEvent
from data_layer.official_actuals.coverage import missing_numeric_rows
import webapp.store as store

LIST_LOOKBACK = dt.timedelta(days=92)   # how far back --list looks for releases with no actual

# Populated by an agent session after WebSearch research — see module
# docstring. Each tuple: (event_title, event_time_utc, actual, source_note).
FACTS: list[tuple[str, dt.datetime, str, str]] = []


@dataclass
class FillReport:
    written: int = 0
    skipped: int = 0
    skip_reasons: list[str] = field(default_factory=list)


def run(facts: list[tuple[str, dt.datetime, str, str]], conn, now: dt.datetime | None = None) -> FillReport:
    report = FillReport()
    now = now or dt.datetime.now(UTC_TZ)

    for title, event_time_utc, actual, source_note in facts:
        rows = conn.execute(
            "SELECT * FROM event_history WHERE event_title = ? AND event_time_utc = ?",
            (title, event_time_utc.isoformat()),
        ).fetchall()
        if not rows:
            report.skipped += 1
            report.skip_reasons.append(f"{title}@{event_time_utc.isoformat()}: no matching event_history row")
            continue
        existing = dict(rows[0])
        if existing["actual"] is not None:
            report.skipped += 1
            report.skip_reasons.append(f"{title}@{event_time_utc.isoformat()}: already has a real actual, not overwritten")
            continue

        event = EconomicEvent(title, "USD", "High", event_time_utc)
        event.forecast = existing["forecast"]
        event.previous = existing["previous"]
        event.actual = actual
        surprise_direction = classify_surprise(event)
        store.upsert_event_history(conn, event, surprise_direction, now, source="live_web_fallback")
        print(f"[fill_missing_actuals] wrote {title}@{event_time_utc.isoformat()}: actual={actual} ({source_note})")
        report.written += 1

    return report


def list_missing(conn, now: dt.datetime) -> int:
    """Print the numeric USD releases of the last 92 days still without an actual (SAST); returns the count."""
    rows = missing_numeric_rows(conn, now - LIST_LOOKBACK, now)
    print(f"[fill_missing_actuals] {len(rows)} numeric release(s) with no actual since {(now - LIST_LOOKBACK).date()}:")
    for r in rows:
        released = dt.datetime.fromisoformat(r["event_time_utc"]).astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M SAST")
        print(f"  {r['event_title']} @ {released} (forecast={r['forecast']}, previous={r['previous']})")
    return len(rows)


if __name__ == "__main__":
    conn = store.get_connection()
    now = dt.datetime.now(UTC_TZ)

    if "--list" in sys.argv:
        list_missing(conn, now)
    elif not FACTS:
        print("[fill_missing_actuals] FACTS is empty — nothing to write. "
              "Run with --list to see candidates, research them via WebSearch, "
              "then populate FACTS and re-run without --list.")
    else:
        report = run(FACTS, conn, now=now)
        print(f"[fill_missing_actuals] written={report.written} skipped={report.skipped}")
        for reason in report.skip_reasons:
            print(f"[fill_missing_actuals] skipped: {reason}")

    conn.close()
