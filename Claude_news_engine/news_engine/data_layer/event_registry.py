"""
Cadence-derived next-occurrence resolution for the recurring event
registry (config.settings.EVENT_REGISTRY). Internal bookkeeping only —
never surfaced on the Calendar tab UI or any webapp route; that's
webapp/store.py's macro_calendar table's job for the titles it already
covers (see get_macro_calendar_events()).
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from config.settings import EVENT_REGISTRY

AVG_DAYS_PER_MONTH = 30.4368  # average Gregorian month length


def _next_from_ff_snapshot(title: str, conn, now: dt.date) -> Optional[dt.date]:
    """
    Tier 1: a real upcoming occurrence of `title` already sitting in the
    current Forex Factory calendar snapshot. Returns the earliest future
    event_time_utc's date for this title, or None if nothing has been
    fetched yet or no matching future row exists.
    """
    from webapp.store import get_calendar_snapshot  # local import: scoring/data_layer -> webapp, avoid a module-level cycle
    snapshot = get_calendar_snapshot(conn)
    if snapshot is None:
        return None
    candidates = []
    for raw in snapshot.events:
        if raw.get("title") != title:
            continue
        try:
            event_time = dt.datetime.fromisoformat(raw["event_time_utc"])
        except (KeyError, ValueError):
            continue
        if event_time.date() >= now:
            candidates.append(event_time.date())
    return min(candidates) if candidates else None


def _next_from_macro_calendar(title: str, conn, now: dt.date) -> Optional[dt.date]:
    """
    Tier 2: macro_calendar's existing FRED-release-schedule estimate, for
    the subset of titles it already covers. Looks ~13 months ahead — wide
    enough to catch even a quarterly (GDP) or FOMC-cadence (~1.6-month)
    title's next date. Returns the earliest matching event_date, or None.
    """
    from webapp.store import get_macro_calendar_events  # local import: avoid a module-level cycle
    end = now + dt.timedelta(days=395)
    rows = get_macro_calendar_events(conn, now.isoformat(), end.isoformat())
    matching = [r for r in rows if r.event_title == title]
    if not matching:
        return None
    return dt.date.fromisoformat(min(r.event_date for r in matching))


def _last_confirmed_occurrence(title: str, conn) -> Optional[dt.date]:
    """
    The most recent CONFIRMED (actual IS NOT NULL) event_history date for
    `title` — real, resolved data only, never guessed. None if this title
    has no resolved occurrence recorded yet.
    """
    from webapp.store import get_event_history  # local import: avoid a module-level cycle
    rows = get_event_history(conn, title, limit=6)
    resolved = [r for r in rows if r.actual is not None]
    if not resolved:
        return None
    return dt.datetime.fromisoformat(resolved[0].event_time_utc).date()  # rows are DESC by event_time_utc


def get_approximate_next_occurrence(
    title: str,
    conn,
    now: Optional[dt.date] = None,
) -> Optional[dt.date]:
    """
    Fallback chain, real data always wins over the estimate:
      1. A real upcoming occurrence already in the current FF calendar
         snapshot.
      2. macro_calendar's existing FRED-derived estimate, for the subset
         of titles it already covers.
      3. EVENT_REGISTRY[title]['avg_interval_months'] added to the most
         recent CONFIRMED event_history occurrence (rounded to the
         nearest day) — deliberately month-level approximate, never a
         fabricated exact date.

    Returns None if `title` isn't in EVENT_REGISTRY, or if none of the
    three sources have an answer.
    """
    if title not in EVENT_REGISTRY:
        return None
    now = now or dt.datetime.now(dt.timezone.utc).date()

    real = _next_from_ff_snapshot(title, conn, now)
    if real is not None:
        return real

    macro = _next_from_macro_calendar(title, conn, now)
    if macro is not None:
        return macro

    last_confirmed = _last_confirmed_occurrence(title, conn)
    if last_confirmed is None:
        return None
    interval_days = EVENT_REGISTRY[title]["avg_interval_months"] * AVG_DAYS_PER_MONTH
    return last_confirmed + dt.timedelta(days=round(interval_days))
