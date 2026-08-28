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
    except (KeyError, ValueError):
        return None
    if realtime_start < event_time_utc.date():
        return None

    try:
        value = float(newest["value"])
    except (TypeError, ValueError):
        return None

    return f"{value:.1f}%"
