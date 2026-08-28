"""
Live fallback for Forex Factory's `actual` field going missing or posting
hours late — confirmed recurring, not a one-off (docs/superpowers/specs/
2026-08-26-fred-actuals-fallback-design.md): Core PCE Price Index m/m and
Prelim GDP q/q both released 2026-08-26 12:30 UTC and still showed
actual=None in FF's feed 45+ minutes later.

get_actual_from_fred() pulls the real released value directly from FRED
for the subset of tracked titles that are FRED-published percent-change
price/level indices (config.settings.FRED_SERIES_ID_BY_EVENT_TITLE) —
live-verified 2026-08-26 to post SAME DAY as release (PCEPILFE's newest
point carried realtime_start == the release date), independently
corroborated against Investing.com's real print the same day.

READ-ONLY, same fail-open contract as every other data_layer module:
returns None on a missing key, an untracked title, a failed request, a
missing/stale observation, or FRED's "not yet published" marker ('.') —
never raises, never invents a value.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import requests

from config.settings import FRED_API_KEY, FRED_SERIES_ID_BY_EVENT_TITLE

FRED_BASE_URL = "https://api.stlouisfed.org/fred"


def get_actual_from_fred(event_title: str, event_time_utc: dt.datetime) -> Optional[str]:
    """
    Returns a formatted percentage string (e.g. "0.2%") for event_title's
    most recent FRED-published value, or None if this title has no FRED
    mapping, no FRED_API_KEY is configured, the request fails, or the
    newest observation isn't fresh enough to plausibly BE this release
    (see the realtime_start freshness check below).
    """
    mapping = FRED_SERIES_ID_BY_EVENT_TITLE.get(event_title)
    if mapping is None:
        return None
    if not FRED_API_KEY:
        return None

    series_id, units = mapping
    try:
        resp = requests.get(
            f"{FRED_BASE_URL}/series/observations",
            params={
                "series_id": series_id, "file_type": "json", "api_key": FRED_API_KEY,
                "sort_order": "desc", "limit": 1, "units": units,
            },
            timeout=15,
        )
        resp.raise_for_status()
        observations = resp.json().get("observations", [])
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the caller
        print(f"[fred_actuals] WARNING: fetch failed for {event_title!r} ({series_id}): {exc}")
        return None

    if not observations:
        return None

    newest = observations[0]
    # FRED marks a missing/not-yet-published observation with the literal
    # string "." — treat exactly like macro_backdrop.py already does.
    if newest.get("value") in (None, "."):
        return None

    # Freshness check, not period-matching (see module docstring / spec):
    # realtime_start is the date FRED itself published this observation —
    # if that's on or after the release date, this is a genuine fresh
    # figure for THIS release, not a stale prior-period value FRED simply
    # hasn't updated yet.
    try:
        realtime_start = dt.date.fromisoformat(newest["realtime_start"])
    except (KeyError, TypeError, ValueError):
        return None
    if realtime_start < event_time_utc.date():
        return None

    # Period-plausibility check, alongside the freshness check above: FRED
    # can publish a same-day revision to an OLDER reference period (routine
    # around seasonal-factor revisions) before it ingests the new period's
    # point. sort_order=desc&limit=1 would return that older revision, and
    # it would pass the realtime_start check above (it WAS published today)
    # while actually being the wrong period's value. All 10 currently-
    # mapped series (config.settings.FRED_SERIES_ID_BY_EVENT_TITLE) are
    # monthly — no quarterly series, GDP is explicitly excluded. FRED's
    # `date` for a monthly series is the FIRST of the covered month, and
    # this project's own genuine same-month releases land up to ~56 days
    # after that (e.g. July's reading, date=2026-07-01, released 2026-08-26
    # — see the "fresh"/"pc1 units" fixtures in tests/test_fred_actuals.py).
    # 60 days gives that real lag a small margin while still rejecting a
    # revision to a PRIOR period, which would land roughly one more
    # monthly cycle back (~90 days) — comfortably past this tolerance.
    try:
        obs_date = dt.date.fromisoformat(newest["date"])
    except (KeyError, TypeError, ValueError):
        return None
    if (event_time_utc.date() - obs_date).days > 60:
        return None

    try:
        value = float(newest["value"])
    except (TypeError, ValueError):
        return None

    return f"{value:.1f}%"
