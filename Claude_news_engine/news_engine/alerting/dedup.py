"""Content-similarity + time-window deduplication for poll_once.py."""
from __future__ import annotations

import datetime as dt
import difflib
import re
import sqlite3
from typing import Optional

from alerting import store
from config.settings import TOPIC_DEDUP_WINDOW_HOURS

# Story-level ("saga") merge, added 2026-10-15 after the alert audit: one diesel-export-ban
# debate produced 11 alerts and one hurricane 5, because the headlines are reworded too much
# for the similarity ratio. It is deliberately limited to the two categories where that
# pattern showed up AND a repeat is safe to fold in. energy / geopolitical_conflict stay on
# similarity only: tested on the real alerts, a looser rule merged a tanker strike into
# Hormuz reopening talks, i.e. it buried a new event.
_TOPIC_CATEGORIES = ("trade_policy", "natural_disaster_supply_chain")
_STOPWORDS = frozenset(
    "the a an and or of to in on at for by with from as is are was be it its that this after over amid "
    "says say said sources reuters exclusive new more than into about will could would not but has have "
    "had their they them you what how why who when out up down off per via vs".split()
)
_STORM_NAME = re.compile(r"\b(?:hurricane|typhoon|cyclone|tropical storm)\s+([a-z]+)")
_NOT_A_STORM_NAME = frozenset({"season", "warning", "watch", "center", "centre", "category", "forecast", "tracker"})


def _significant_words(headline: str) -> list[str]:
    text = re.sub(r"[^a-z0-9' ]", " ", headline.lower().replace("’", "'"))
    return [re.sub(r"'s$", "", w)[:6] for w in text.split() if w not in _STOPWORDS and len(w) > 1]


def _trigrams(headline: str) -> set[tuple[str, ...]]:
    words = _significant_words(headline)
    return {tuple(words[i:i + 3]) for i in range(len(words) - 2)}


def _storm_names(headline: str) -> set[str]:
    return {m.group(1) for m in _STORM_NAME.finditer(headline.lower()) if m.group(1) not in _NOT_A_STORM_NAME}


def same_story(category: str, candidate: str, existing: str) -> bool:
    """True when two same-category headlines are the same ongoing story (topic rule only)."""
    if category == "trade_policy":
        return bool(_trigrams(candidate) & _trigrams(existing))
    if category == "natural_disaster_supply_chain":
        return bool(_storm_names(candidate) & _storm_names(existing))
    return False

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
    topic_window = max(window_hours, TOPIC_DEDUP_WINDOW_HOURS) if category in _TOPIC_CATEGORIES else window_hours
    similarity_cutoff = now_utc - dt.timedelta(hours=window_hours)
    for existing in store.list_recent_alerts_in_category(conn, category, now_utc - dt.timedelta(hours=topic_window)):
        if existing.detected_at_utc >= similarity_cutoff:
            ratio = difflib.SequenceMatcher(None, candidate_headline.lower(), existing.headline.lower()).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                return existing.id
        if same_story(category, candidate_headline, existing.headline):
            return existing.id
    return None
