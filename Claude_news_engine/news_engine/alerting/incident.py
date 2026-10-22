"""
Incident linking for shock alerts: is a new headline a follow-up of an alert
we already sent? (B7 K10, plus the K9 re-stamped age.)

B7 (2026-10-22), audit SA-04. The similarity dedup (alerting/dedup.py) only
catches reworded headlines; follow-up coverage of one event arrives under a
new headline or a re-stamped URL and used to alert, push and add lean again.
Live pairs that were one incident: #54/#55 (blast at Riyadh airport), #71/#72
(Russia sanctions waiver), #33/#39 (Ukraine to hit Russian refineries; #39 is
the same Reuters URL re-stamped 62 h later), #12/#13 (Iran's Hormuz
conditions). Pairs that must stay apart: #41/#43 (one CNBC live-blog URL,
"Oil rises ..." then "Oil prices fall ...") and #46/#52 (Hurricanes Isaias and
Simon on one Google News URL, after a similarity merge).

Owner decision: a follow-up is LINKED AND LABELLED, never suppressed in a way
that could bury an escalation. This module only decides; alerting/poll_once.py
stores the row on its incident and pushes only when update_reason() says the
severity rose or the direction flipped.

Rules, in order (any veto -- other category family, or two different named
storms -- stops a link):
1. URL rule: the article's URL was attached to an alert in the last 72 h, the
   direction is not opposite, and the headlines share a named entity or are
   similar (difflib ratio >= dedup.SIMILARITY_THRESHOLD).
2. Entity rule: an alert of the same family in the last 24 h names a place or
   actor this headline names (data_layer/entities.py). Opposite direction is
   allowed here: it becomes an update push.

Limits, stated plainly: entities are read from headlines only, through a small
gazetteer (an unlisted place links nothing, i.e. today's behaviour); direction
is the classifier's polarity, falling back to the headline's price verb; there
is no LLM call. This module reads the store and never writes.
"""
from __future__ import annotations

import datetime as dt
import difflib
import re
import sqlite3
from dataclasses import dataclass
from typing import Optional

from alerting import dedup, store
from alerting.store import ShockAlertRow
from config.settings import INCIDENT_ENTITY_WINDOW_HOURS, INCIDENT_URL_WINDOW_HOURS
from data_layer.entities import incident_entities

# energy and geopolitical_conflict cover the same stories (a tanker strike is filed under
# either), so they are one family; every other category is its own family.
CATEGORY_FAMILY: dict[str, str] = {"energy": "energy_geopolitical", "geopolitical_conflict": "energy_geopolitical"}
OPPOSITE_POLARITY: dict[str, str] = {"escalation": "relief", "relief": "escalation", "hawkish": "dovish", "dovish": "hawkish"}

_SEVERITY_RANK = {"Low": 0, "Medium": 1, "High": 2}  # same ranks as poll_once.py / us_link.py

# Headline price verbs, whole words: the direction fallback when a polarity is unknown
# (pre-B2 rows are NULL, failed classifications are "unclear").
_UP_MOVE = re.compile(
    r"\b(?:rise|rises|rose|rising|jump(?:s|ed)?|surge(?:s|d)?|climb(?:s|ed)?|gain(?:s|ed)?"
    r"|rall(?:y|ies|ied)|soar(?:s|ed)?|spike(?:s|d)?)\b"
)
_DOWN_MOVE = re.compile(
    r"\b(?:fall(?:s|ing)?|fell|drop(?:s|ped)?|slide(?:s)?|slid|slump(?:s|ed)?|tumble(?:s|d)?"
    r"|plunge(?:s|d)?|sink(?:s)?|sank|ease(?:s|d)?|decline(?:s|d)?|retreat(?:s|ed)?)\b"
)


@dataclass(frozen=True)
class IncidentCandidate:
    """The new article as the linking rules see it, before anything is stored."""
    headline: str
    category: str
    polarity: Optional[str]
    url: str
    published_utc: dt.datetime
    detected_at_utc: dt.datetime


@dataclass(frozen=True)
class IncidentLink:
    incident_id: int  # the incident root the follow-up joins
    alert_id: int     # the stored alert that matched (may itself be a follow-up)
    rule: str         # "url" | "entity:<sorted comma list>"


def category_family(category: str) -> str:
    return CATEGORY_FAMILY.get(category, category)


def headline_move(headline: str) -> Optional[str]:
    """"up" | "down" from the headline's price verb; None when it has neither or both."""
    text = (headline or "").lower()
    up, down = bool(_UP_MOVE.search(text)), bool(_DOWN_MOVE.search(text))
    if up == down:
        return None
    return "up" if up else "down"


def _known(polarity: Optional[str]) -> bool:
    return polarity in OPPOSITE_POLARITY  # None and "unclear" are unknown


def opposite_direction(polarity_a: Optional[str], headline_a: str, polarity_b: Optional[str], headline_b: str) -> bool:
    """Known polarities decide; otherwise both headline moves must be known and differ."""
    if _known(polarity_a) and _known(polarity_b):
        return OPPOSITE_POLARITY.get(polarity_a) == polarity_b
    move_a, move_b = headline_move(headline_a), headline_move(headline_b)
    return move_a is not None and move_b is not None and move_a != move_b


def storm_conflict(headline_a: str, headline_b: str) -> bool:
    """Both headlines name storms and no storm is shared (Isaias vs Simon)."""
    storms_a, storms_b = dedup.storm_names(headline_a), dedup.storm_names(headline_b)
    return bool(storms_a) and bool(storms_b) and not (storms_a & storms_b)


def _vetoed(cand: IncidentCandidate, row: ShockAlertRow) -> bool:
    return category_family(cand.category) != category_family(row.category) or storm_conflict(cand.headline, row.headline)


def _same_story_on_url(cand: IncidentCandidate, row: ShockAlertRow) -> bool:
    """A sighting of the candidate's URL is the same story unless positively different (veto or opposite direction)."""
    return not _vetoed(cand, row) and not opposite_direction(cand.polarity, cand.headline, row.polarity, row.headline)


def _url_sightings(conn: sqlite3.Connection, cand: IncidentCandidate) -> list[tuple[store.SeenUrl, ShockAlertRow]]:
    """(sighting, its alert) for the candidate's URL in the last 72 h, newest first; a sighting whose alert is gone is skipped."""
    since = cand.detected_at_utc - dt.timedelta(hours=INCIDENT_URL_WINDOW_HOURS)
    pairs: list[tuple[store.SeenUrl, ShockAlertRow]] = []
    for seen in store.lookup_seen_url(conn, cand.url, since):
        row = store.get_alert(conn, seen.alert_id)
        if row is not None:
            pairs.append((seen, row))
    return pairs


def find_incident(conn: sqlite3.Connection, cand: IncidentCandidate) -> Optional[IncidentLink]:
    """The incident this candidate follows up, or None (a new incident). URL rule first, then entity rule."""
    cand_entities = incident_entities(cand.headline)

    # URL rule (K9 memory, 72 h). Also needs a shared entity or a similar headline: a live-blog
    # URL carries unrelated stories (#41/#43), so the URL alone is not enough.
    for _seen, row in _url_sightings(conn, cand):
        if not _same_story_on_url(cand, row):
            continue
        shares_entity = bool(cand_entities & incident_entities(row.headline))
        similar = difflib.SequenceMatcher(None, cand.headline.lower(), row.headline.lower()).ratio() >= dedup.SIMILARITY_THRESHOLD
        if shares_entity or similar:
            return IncidentLink(incident_id=row.incident_id, alert_id=row.id, rule="url")

    # Entity rule (24 h, tighter end of the owner's range: a looser energy/geopolitical rule once
    # buried a tanker strike under Hormuz talks). Opposite direction links here and becomes an update.
    if not cand_entities:
        return None
    since = cand.detected_at_utc - dt.timedelta(hours=INCIDENT_ENTITY_WINDOW_HOURS)
    for row in store.list_recent_alerts(conn, since):
        if _vetoed(cand, row):
            continue
        overlap = cand_entities & incident_entities(row.headline)
        if overlap:
            return IncidentLink(incident_id=row.incident_id, alert_id=row.id, rule="entity:" + ",".join(sorted(overlap)))
    return None


def effective_first_published(conn: sqlite3.Connection, cand: IncidentCandidate) -> dt.datetime:
    """
    K9: a URL seen on an alert in the last 72 h keeps that sighting's first publication time (a
    re-stamp must look old: #39 gets #33's 3 Oct), unless the story is positively different (other
    family, storm conflict, opposite direction): then the article's own time stands (#43, #52).
    """
    times = [cand.published_utc]
    for seen, row in _url_sightings(conn, cand):
        if _same_story_on_url(cand, row):
            times.append(seen.first_published_utc or seen.first_seen_utc)
    return min(times)


def incident_max_severity(rows: list[ShockAlertRow]) -> str:
    """Highest stored severity on the incident ("Low" for no rows)."""
    return max((r.severity for r in rows), key=lambda s: _SEVERITY_RANK.get(s, -1), default="Low")


def update_reason(rows: list[ShockAlertRow], severity: str, polarity: Optional[str], headline: str,
                  classification_failed: bool) -> Optional[str]:
    """
    Why a follow-up is pushed as "Update to incident #N", or None (stored silently).
    `rows` is the incident in detection order. A failed classification never pushes: its
    severity is a fallback guess (same rule as poll_once._maybe_escalate). Severity is
    compared with the incident MAXIMUM, so a Medium follow-up row cannot make a later High
    look like a rise the incident already pushed.
    """
    if classification_failed:
        return None
    highest = incident_max_severity(rows)
    if _SEVERITY_RANK.get(severity, -1) > _SEVERITY_RANK.get(highest, -1):
        return f"severity rose: {highest} -> {severity}"

    old_polarity = next((r.polarity for r in reversed(rows) if _known(r.polarity)), None)
    if old_polarity is not None and _known(polarity):
        if OPPOSITE_POLARITY[old_polarity] == polarity:
            return f"direction changed: {old_polarity} -> {polarity}"
        return None

    # Either polarity unknown: fall back to the headlines' price verbs.
    new_move = headline_move(headline)
    old_move = next((m for m in (headline_move(r.headline) for r in reversed(rows)) if m is not None), None)
    if new_move is not None and old_move is not None and new_move != old_move:
        return f"direction changed: {old_move} -> {new_move}"
    return None
