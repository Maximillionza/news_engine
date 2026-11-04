"""
Tier 1 releases that Forex Factory has not listed yet (FIX Task 6, T1 problem 4).

event_history only holds a release once FF's feed reaches it, so a Tier 1 capture run a few days early finds
nothing and the release goes uncovered. macro_calendar (FRED's release schedule, date only) knows the day
earlier; this module turns an unconfirmed macro_calendar row into a release time using the official New York
release time (data_layer.official_actuals.registry), NOT the row's stored estimate, which is derived from the
last release's UTC time-of-day and is an hour wrong across a daylight-saving change.

Such a release is "unconfirmed": the date comes from FRED, not FF. The captures log it, marked, but its forecast
is unknown (event_history holds none), so it only ever produces a pending line, never a Tier 1 call.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from typing import Optional
from zoneinfo import ZoneInfo

from data_layer.official_actuals.registry import OFFICIAL_SPECS

UTC = dt.timezone.utc
_NY = ZoneInfo("America/New_York")

# An event_history row of the same title this close to the macro date is the same occurrence (FF may shift the
# day by one or two), so the macro row is not a separate release.
EXISTING_ROW_WINDOW = dt.timedelta(days=3)

# BEA publishes the second estimate of a quarter's GDP in the 2nd month after it ends. FRED's schedule also lists
# the advance (and third) estimate dates under the GDP release, which are not "Prelim GDP q/q".
_PRELIM_GDP_MONTHS = (2, 5, 8, 11)


@dataclass(frozen=True)
class UnconfirmedRelease:
    title: str
    release_utc: dt.datetime


def on_official_schedule(title: str, event_date: dt.date) -> bool:
    """False for a macro_calendar date that cannot be this title's release; True for everything else."""
    if title == "Prelim GDP q/q":
        return event_date.month in _PRELIM_GDP_MONTHS
    return True


def release_utc_from_et(title: str, event_date: dt.date) -> Optional[dt.datetime]:
    """The title's official New York release time on `event_date`, in UTC; None for a title with no spec."""
    spec = OFFICIAL_SPECS.get(title)
    if spec is None:
        return None
    local = dt.datetime.combine(event_date, spec.release_time_et, tzinfo=_NY)
    return local.astimezone(UTC)


def unconfirmed_releases(dash_conn: sqlite3.Connection, titles: list[str], start_utc: dt.datetime,
                         end_utc: dt.datetime) -> list[UnconfirmedRelease]:
    """
    macro_calendar rows (confirmed = 0) of `titles` whose official release time is strictly after start_utc and
    at or before end_utc, on the official schedule, with no event_history USD row of that title within
    EXISTING_ROW_WINDOW. Sorted by time, then title.
    """
    if not titles:
        return []
    marks = ",".join("?" for _ in titles)
    low = (start_utc - dt.timedelta(days=1)).date().isoformat()
    high = (end_utc + dt.timedelta(days=1)).date().isoformat()
    rows = dash_conn.execute(
        f"SELECT event_title, event_date FROM macro_calendar WHERE confirmed = 0 AND event_title IN ({marks}) "
        f"AND event_date BETWEEN ? AND ?", [*titles, low, high]).fetchall()
    found = []
    for row in rows:
        title = row[0]
        try:
            event_date = dt.date.fromisoformat(row[1])
        except (TypeError, ValueError):
            continue
        release = release_utc_from_et(title, event_date)
        if release is None or not start_utc < release <= end_utc or not on_official_schedule(title, event_date):
            continue
        near = dash_conn.execute(
            "SELECT 1 FROM event_history WHERE country = 'USD' AND event_title = ? "
            "AND julianday(event_time_utc) BETWEEN julianday(?) AND julianday(?) LIMIT 1",
            (title, (release - EXISTING_ROW_WINDOW).isoformat(), (release + EXISTING_ROW_WINDOW).isoformat()),
        ).fetchone()
        if near is None:
            found.append(UnconfirmedRelease(title, release))
    return sorted(found, key=lambda item: (item.release_utc, item.title))
