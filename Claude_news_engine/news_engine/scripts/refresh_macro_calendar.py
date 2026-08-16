"""
Populates webapp.store's macro_calendar table (the "macro view") from
FRED's month-ahead release schedule — the actual data source behind the
Dashboard's Calendar tab showing events beyond Forex Factory's
"thisweek"-only window. See docs/macro-calendar-design-2026-08-16.md for
the full macro/micro design.

Cadence: runs once, then self-gates to roughly every
MACRO_REFRESH_INTERVAL_DAYS (29) days, measured from the last time it
actually ran — NOT a fixed calendar day, so "run whenever, it just skips
itself if not due" is always the correct way to invoke this (e.g. from a
cron/scheduled task, or by hand). Uses the same persisted, file-backed
"last run" pattern data_layer/calendar_feed.py's FF cooldown already
established (data_layer/.last_macro_calendar_refresh_at, gitignored) —
survives process restarts, same reasoning as that file's own comment.

Usage:
    python scripts/refresh_macro_calendar.py            # runs only if due
    python scripts/refresh_macro_calendar.py --force     # runs regardless (e.g. the first, once-off run)
    python scripts/refresh_macro_calendar.py --days 40   # override the lookahead window (default 35)

This is display-only, feeding webapp.store's macro_calendar table for
the Calendar tab — it never touches prediction_runs, event_history, or
anything scoring reads. Requires FRED_API_KEY (see .env.example);
prints a clear message and exits if missing, same fail-open contract as
every other optional data source in this project.
"""
from __future__ import annotations

import sys
import os
import argparse
import datetime as dt
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import FRED_API_KEY, FRED_RELEASE_ID_BY_EVENT_TITLE, UTC_TZ
from data_layer.fred_calendar_feed import get_upcoming_release_dates
import webapp.store as store

MACRO_REFRESH_INTERVAL_DAYS = 29
_LAST_MACRO_REFRESH_FILE = Path(__file__).parent.parent / "data_layer" / ".last_macro_calendar_refresh_at"


def _seconds_since_last_refresh() -> Optional[float]:
    """None if this has never run before (fresh install, or the file was cleared) — same contract as calendar_feed._seconds_since_last_fetch()."""
    if not _LAST_MACRO_REFRESH_FILE.exists():
        return None
    try:
        last = dt.datetime.fromisoformat(_LAST_MACRO_REFRESH_FILE.read_text().strip())
    except (ValueError, OSError):
        return None  # corrupt/unreadable — fail open to "never run", not a crash
    return (dt.datetime.now(dt.timezone.utc) - last).total_seconds()


def _record_refresh(now: dt.datetime) -> None:
    _LAST_MACRO_REFRESH_FILE.write_text(now.isoformat())


def is_due(force: bool = False) -> bool:
    """True if this should actually run: never run before, forced, or MACRO_REFRESH_INTERVAL_DAYS have elapsed since the last real run."""
    if force:
        return True
    age_seconds = _seconds_since_last_refresh()
    if age_seconds is None:
        return True  # the "once off" first run
    return age_seconds >= MACRO_REFRESH_INTERVAL_DAYS * 86400


def run(days_ahead: int = 35, force: bool = False, now: Optional[dt.datetime] = None) -> int:
    """
    Returns the number of macro_calendar rows written/refreshed, or -1 if
    skipped (not due, or FRED_API_KEY missing) — distinct return values
    so a caller/cron log can tell "skipped, not due yet" from "ran, wrote
    N rows" from "ran, found nothing" (0).
    """
    now = now or dt.datetime.now(UTC_TZ)

    if not is_due(force=force):
        age_days = (_seconds_since_last_refresh() or 0) / 86400
        next_due_in = MACRO_REFRESH_INTERVAL_DAYS - age_days
        print(f"[refresh_macro_calendar] skipped — last ran {age_days:.1f} day(s) ago, "
              f"next due in {next_due_in:.1f} day(s). Pass --force to run anyway.")
        return -1

    if not FRED_API_KEY:
        print("[refresh_macro_calendar] FRED_API_KEY not set — add it to .env first (see .env.example). Nothing written.")
        return -1

    conn = store.get_connection()
    written = 0
    try:
        for title, release_id in FRED_RELEASE_ID_BY_EVENT_TITLE.items():
            dates = get_upcoming_release_dates(release_id, days_ahead=days_ahead)
            if not dates:
                continue
            time_of_day = store.infer_event_time_of_day(conn, title)
            for entry in dates:
                if time_of_day is not None:
                    estimated_time_utc = dt.datetime.combine(entry.release_date, time_of_day, tzinfo=dt.timezone.utc).isoformat()
                    time_source = "history_derived"
                else:
                    estimated_time_utc = None  # never fabricate a time with no real basis
                    time_source = "unconfirmed"
                store.upsert_macro_calendar_event(
                    conn, title, entry.release_date.isoformat(), estimated_time_utc, time_source, now,
                )
                written += 1
                print(f"[refresh_macro_calendar] {title}: {entry.release_date} "
                      f"(time={'estimated ' + estimated_time_utc if estimated_time_utc else 'unconfirmed'})")
    finally:
        conn.close()

    _record_refresh(now)
    print(f"[refresh_macro_calendar] done — {written} macro-calendar row(s) written/refreshed.")
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Run even if not due yet (e.g. the first, once-off run)")
    parser.add_argument("--days", type=int, default=35, help="How many days ahead to pull from FRED (default 35)")
    args = parser.parse_args()
    run(days_ahead=args.days, force=args.force)
