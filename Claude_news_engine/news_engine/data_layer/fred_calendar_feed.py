"""
Thin, read-only HTTP client for the FRED (Federal Reserve Economic Data)
API's release-dates endpoint — a free, official-source month-lookahead
calendar for scheduled US economic releases, to be cross-checked against
Forex Factory's feed (data_layer/calendar_feed.py) which only ever shows
"thisweek" and can't itself look further ahead.

See docs/calendar-lookahead-source-research-2026-08-15.md for how this
source was chosen and live-verified, and config/settings.py's
FRED_RELEASE_ID_BY_EVENT_TITLE for which event titles map to which FRED
release. NOT wired into scoring, the dashboard, or the accumulator —
scripts/compare_fred_lookahead.py is the only intended caller, and it's a
standalone, read-only comparison/logging tool, not a live pipeline
participant.

READ-ONLY. This module never writes anything — it only reads FRED's
public /fred/releases/dates endpoint.

Requires a free FRED API key (config.settings.FRED_API_KEY, from the
FRED_API_KEY environment variable — see fred.stlouisfed.org/docs/api/api_key.html
to register one). Every function here fails open (returns an empty list,
never raises) when the key is missing or the request fails for any
reason — same "absent, not fabricated, never crash the caller" contract
every other data_layer module in this project already uses.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import requests

from config.settings import FRED_API_KEY

FRED_BASE_URL = "https://api.stlouisfed.org/fred"


@dataclass
class FredReleaseDate:
    release_id: int
    release_date: dt.date


def get_upcoming_release_dates(release_id: int, days_ahead: int = 35, today: Optional[dt.date] = None) -> list[FredReleaseDate]:
    """
    Every scheduled release date for `release_id` between `today` (or the
    real current date if omitted) and `today + days_ahead` days, per
    FRED's /fred/releases/dates endpoint. Returns an empty list — never
    fabricated, never raises — if FRED_API_KEY isn't set, the request
    fails for any reason, or the release genuinely has nothing scheduled
    in that window.

    days_ahead defaults to 35 (a bit over a month) — "month lookahead"
    per this feature's own purpose, with a few days of slack so a release
    landing right at the edge of a calendar month isn't missed.
    """
    if not FRED_API_KEY:
        print("[fred_calendar_feed] WARNING: FRED_API_KEY not set — skipping FRED lookahead (see .env.example)")
        return []

    today = today or dt.date.today()
    end = today + dt.timedelta(days=days_ahead)
    try:
        # Singular "release/dates", NOT plural "releases/dates" — the
        # plural endpoint lists dates across EVERY release on FRED and
        # silently ignores release_id entirely (confirmed live 2026-08-16:
        # it returned Cass Freight Index, Coinbase, FOMC Press Release,
        # etc. all mixed together for a release_id=10-only request). The
        # singular endpoint is the one that actually filters by release_id.
        resp = requests.get(
            f"{FRED_BASE_URL}/release/dates",
            params={
                "release_id": release_id,
                "realtime_start": today.isoformat(),
                "realtime_end": end.isoformat(),
                # MUST be "true" — live-verified 2026-08-16: "false" (this
                # project's original setting) silently excludes exactly the
                # future-scheduled dates this function exists to fetch. A
                # date that hasn't happened yet obviously has no data
                # attached, so "no data" -> excluded meant every future
                # date vanished and only already-occurred dates came back
                # (a real bug that made this function return nothing but
                # the past for all 9 release IDs it was tested against).
                "include_release_dates_with_no_data": "true",
                "file_type": "json",
                "api_key": FRED_API_KEY,
            },
            timeout=15,
        )
        resp.raise_for_status()
        rows = resp.json().get("release_dates", [])
    except Exception as exc:  # noqa: BLE001 — a failed fetch/parse must degrade to an empty list, never crash the caller
        print(f"[fred_calendar_feed] WARNING: fetch failed for release_id={release_id}: {exc}")
        return []

    dates = []
    for row in rows:
        try:
            release_date = dt.date.fromisoformat(row["date"])
        except (KeyError, ValueError):
            continue  # a malformed row is skipped, not a reason to drop the whole response
        dates.append(FredReleaseDate(release_id=release_id, release_date=release_date))
    return dates


@dataclass
class LookaheadComparisonRow:
    """
    One event title x date pairing between FRED's lookahead and Forex
    Factory's currently-persisted calendar_snapshot.

    status:
      'match'      — FRED and FF agree on the date (within tolerance_days).
      'fred_only'  — FRED has this scheduled but FF's feed hasn't
                     populated it yet. EXPECTED for anything beyond
                     FF's current week — that's the whole point of using
                     FRED as a lookahead source. Not itself a red flag.
      'ff_only'    — FF has a scheduled occurrence for this title that
                     FRED's window didn't predict at all (or FRED's
                     nearest date for this title was more than
                     tolerance_days away). Worth a human looking at —
                     could be a genuine reschedule, or a mapping/parsing
                     bug in this comparison, or a title mismatch.
    """
    event_title: str
    fred_date: Optional[dt.date]
    ff_date: Optional[dt.date]
    status: str


def compare_fred_to_ff(
    fred_dates_by_title: dict[str, list[FredReleaseDate]],
    ff_events: list[dict],
    tolerance_days: int = 1,
    today: Optional[dt.date] = None,
) -> list[LookaheadComparisonRow]:
    """
    Pure comparison — no I/O, no network, same "arithmetic core, testable
    without a live call" pattern webapp/trend.py already uses.

    `fred_dates_by_title`: event title -> get_upcoming_release_dates()'s
    result for that title's mapped release_id (forward-only by
    construction — see that function's own `today`/`days_ahead` params).
    `ff_events`: plain dicts from webapp.store.get_calendar_snapshot()'s
    CalendarSnapshot.events (title, event_time_utc as an ISO string, ...).
    `tolerance_days`: how close a FF date must be to a FRED date to count
    as the same occurrence — 1 day of slack for timezone-boundary edges
    (FRED's dates are calendar dates with no time-of-day; FF's
    event_time_utc can fall on either side of midnight UTC relative to
    the "real" US release date).
    `today`: excludes already-PAST FF occurrences from 'ff_only' — live-
    verified 2026-08-16: fred_dates_by_title is forward-only, so an
    already-occurred FF event (still sitting in the persisted snapshot
    until the next week's fetch replaces it) would otherwise ALWAYS show
    as a spurious 'ff_only' "worth reviewing," which is noise, not a real
    disagreement — FRED was never even asked about a date before today.
    Defaults to the real current date if omitted.
    """
    today = today or dt.date.today()
    rows: list[LookaheadComparisonRow] = []

    for title, fred_dates in fred_dates_by_title.items():
        ff_dates_for_title = sorted({
            dt.datetime.fromisoformat(e["event_time_utc"]).date()
            for e in ff_events if e.get("title") == title
        })
        matched_ff_dates = set()

        for fred_entry in sorted(fred_dates, key=lambda d: d.release_date):
            match = next(
                (d for d in ff_dates_for_title if abs((d - fred_entry.release_date).days) <= tolerance_days),
                None,
            )
            if match is not None:
                matched_ff_dates.add(match)
                rows.append(LookaheadComparisonRow(event_title=title, fred_date=fred_entry.release_date, ff_date=match, status="match"))
            else:
                rows.append(LookaheadComparisonRow(event_title=title, fred_date=fred_entry.release_date, ff_date=None, status="fred_only"))

        for ff_date in ff_dates_for_title:
            if ff_date not in matched_ff_dates and ff_date >= today:
                rows.append(LookaheadComparisonRow(event_title=title, fred_date=None, ff_date=ff_date, status="ff_only"))

    return rows
