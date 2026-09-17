"""Content-similarity + time-window deduplication for poll_once.py."""
from __future__ import annotations

import datetime as dt
import difflib
import sqlite3
from typing import Optional

from alerting import store

SIMILARITY_THRESHOLD = 0.6  # difflib.SequenceMatcher ratio -- tunable; conservative enough to
                             # catch reworded corroborating headlines without merging distinct events


def find_existing_alert(
    candidate_headline: str, category: str, conn: sqlite3.Connection, window_hours: float = 24.0,
    now_utc: Optional[dt.datetime] = None,
) -> Optional[int]:
    """
    Same difflib-based approach data_layer/news_feed.py already uses for
    article de-duplication. Returns the existing alert's id on a real
    similarity match within `category` and `window_hours` of now (caller
    should call store.append_source() instead of firing a new alert), or
    None (a genuinely new alert). Accepted v1 limitation: two distinct
    events with similar wording in the same window could merge -- flagged
    in the design spec, not solved here.

    window_hours widened 6.0 -> 24.0, 2026-09-17: a real Hormuz
    pipeline-attack story got re-covered by the same outlet under a
    reworded headline ~6h06m after the original alert (similarity ratio
    0.877 -- well above SIMILARITY_THRESHOLD) and duplicated into a
    second Telegram push, missing the old 6h window by minutes. A full
    day is a more realistic span for ongoing coverage of one event.
    """
    now_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    since = now_utc - dt.timedelta(hours=window_hours)
    for existing in store.list_recent_alerts_in_category(conn, category, since):
        ratio = difflib.SequenceMatcher(None, candidate_headline.lower(), existing.headline.lower()).ratio()
        if ratio >= SIMILARITY_THRESHOLD:
            return existing.id
    return None
