"""
Agent-run enrichment pass: fills in real, cited `actual` values for
events Forex Factory's feed has left blank past a grace period.

This is NOT a live-service feature — WebSearch is only callable by an
agent session, not by webapp/scheduler.py's background loop. The
workflow is:
  1. An agent runs `python scripts/fill_missing_actuals.py --list` to
     see stale-missing-actual candidates (webapp.store's
     get_events_with_stale_missing_actual()).
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

from config.settings import UTC_TZ
from data_layer.calendar_feed import classify_surprise, EconomicEvent
import webapp.store as store

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


if __name__ == "__main__":
    conn = store.get_connection()
    now = dt.datetime.now(UTC_TZ)

    if "--list" in sys.argv:
        stale = store.get_events_with_stale_missing_actual(conn, now)
        print(f"[fill_missing_actuals] {len(stale)} event(s) with a stale missing actual:")
        for r in stale:
            print(f"  {r.event_title} @ {r.event_time_utc} (forecast={r.forecast}, previous={r.previous})")
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
