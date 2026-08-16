"""
Read-only verification tool: fetches FRED's month-lookahead release
schedule (data_layer/fred_calendar_feed.py) for every event title
config.settings.FRED_RELEASE_ID_BY_EVENT_TITLE maps, compares it against
whatever Forex Factory calendar snapshot webapp/scheduler.py's background
loop has currently persisted (webapp/store.py), and prints a report.

This is exactly the verification loop requested when this source was
picked: FRED can see further ahead than FF's "thisweek"-only feed, so run
this periodically (manually, on demand — NOT a background loop, NOT wired
into scoring or the dashboard) and watch 'fred_only' rows for a given
title turn into 'match' rows as FF's own feed populates the same date
over the following days/weeks. A persistent 'ff_only' or a FRED/FF date
disagreement is worth a human look — see LookaheadComparisonRow's
docstring in data_layer/fred_calendar_feed.py for what each status means.

Usage:
    python scripts/compare_fred_lookahead.py [--days N]

Requires FRED_API_KEY set in the environment (see .env.example) — prints
a clear message and exits if it's missing, same fail-open contract as
every other optional data source in this project.
"""
from __future__ import annotations

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import FRED_API_KEY, FRED_RELEASE_ID_BY_EVENT_TITLE
from data_layer.fred_calendar_feed import get_upcoming_release_dates, compare_fred_to_ff
import webapp.store as store


def run(days_ahead: int = 35) -> None:
    if not FRED_API_KEY:
        print("[compare_fred_lookahead] FRED_API_KEY not set — add it to .env first (see .env.example). Nothing to compare.")
        return

    conn = store.get_connection()
    try:
        snapshot = store.get_calendar_snapshot(conn)
    finally:
        conn.close()

    if snapshot is None:
        print("[compare_fred_lookahead] No Forex Factory calendar snapshot persisted yet — "
              "run the dashboard (webapp/scheduler.py) at least once first.")
        return

    fred_dates_by_title = {}
    for title, release_id in FRED_RELEASE_ID_BY_EVENT_TITLE.items():
        fred_dates_by_title[title] = get_upcoming_release_dates(release_id, days_ahead=days_ahead)

    rows = compare_fred_to_ff(fred_dates_by_title, snapshot.events)
    rows.sort(key=lambda r: (r.event_title, r.fred_date or r.ff_date))

    matches = [r for r in rows if r.status == "match"]
    fred_only = [r for r in rows if r.status == "fred_only"]
    ff_only = [r for r in rows if r.status == "ff_only"]

    print(f"[compare_fred_lookahead] {len(matches)} match, {len(fred_only)} FRED-only "
          f"(expected — FF hasn't populated yet), {len(ff_only)} FF-only (worth reviewing)\n")

    for r in rows:
        if r.status == "match":
            print(f"  MATCH      {r.event_title}: {r.fred_date} (FF: {r.ff_date})")
        elif r.status == "fred_only":
            print(f"  fred_only  {r.event_title}: {r.fred_date} — not yet in FF's window")
        else:
            print(f"  FF_ONLY    {r.event_title}: {r.ff_date} — FRED had no date within tolerance, review this one")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=35, help="How many days ahead to pull from FRED (default 35)")
    args = parser.parse_args()
    run(days_ahead=args.days)
