"""
How old a story was when we caught it (B2 K7). Shown on every shock alert;
age never suppresses an alert. Band edges are owner decisions of 2026-10-21
(config.settings SHOCK_*_MAX_MINUTES).
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from config.settings import (
    LOCAL_TZ, SHOCK_DELAYED_MAX_MINUTES, SHOCK_FRESH_MAX_MINUTES, SHOCK_STALE_MAX_MINUTES,
)


def _as_utc(value: dt.datetime) -> dt.datetime:
    """A naive timestamp is UTC by convention everywhere in this engine."""
    return value.replace(tzinfo=dt.timezone.utc) if value.tzinfo is None else value


def age_minutes(first_published_utc: Optional[dt.datetime], detected_at_utc: dt.datetime) -> Optional[int]:
    """
    Whole minutes (floored) between first publication and detection, or None
    if the publication time is unknown. Clamped at 0: a feed clock ahead of
    ours must read "+0 min", never a negative age.
    """
    if first_published_utc is None:
        return None
    seconds = (_as_utc(detected_at_utc) - _as_utc(first_published_utc)).total_seconds()
    return max(0, int(seconds // 60))


def freshness_band(age: Optional[int]) -> Optional[str]:
    """Fresh / Delayed / Stale / Very stale by the configured edges; None for an unknown age."""
    if age is None:
        return None
    if age <= SHOCK_FRESH_MAX_MINUTES:
        return "Fresh"
    if age <= SHOCK_DELAYED_MAX_MINUTES:
        return "Delayed"
    if age <= SHOCK_STALE_MAX_MINUTES:
        return "Stale"
    return "Very stale"


def freshness_line(first_published_utc: Optional[dt.datetime], detected_at_utc: dt.datetime) -> Optional[str]:
    """
    e.g. "Published 14:42 SAST · +2 min · Fresh". The date is added only when
    the story's SAST calendar day differs from the detection's SAST day.
    None when the publication time is unknown.
    """
    age = age_minutes(first_published_utc, detected_at_utc)
    if age is None:
        return None
    published = _as_utc(first_published_utc).astimezone(LOCAL_TZ)
    detected = _as_utc(detected_at_utc).astimezone(LOCAL_TZ)
    stamp = published.strftime("%H:%M")
    if published.date() != detected.date():
        stamp = f"{published.day} {published.strftime('%b')} {stamp}"
    return f"Published {stamp} SAST · +{age} min · {freshness_band(age)}"
