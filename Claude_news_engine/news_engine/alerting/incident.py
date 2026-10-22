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
   similar (difflib ratio >= dedup.SIMILARITY_THRESHOLD). The same test decides
   whether the article inherits the older first-publication time (K9).
2. Entity rule, scoped to the INCIDENT, not to every recent alert (final
   review fix, 2026-10-22). The candidate is compared only with incident ROOTS
   detected in the last 24 h (never a follow-up or update row, so links cannot
   chain), and links only when ALL of these hold:
   a. the root and the headline share a named place or actor
      (data_layer/entities.py);
   b. they also share at least ENTITY_RULE_MIN_EVENT_WORDS "event words":
      significant headline words that are not gazetteer names, not the
      everyday vocabulary of an ongoing war (attack, strike, drone, missile,
      ...) and not market vocabulary (oil, prices, ...). A country or strait
      names a theatre, not an incident; the event words say WHAT happened
      (#54/#55 share "blast" + "airport");
   c. violent-event veto (controller ruling 2026-10-22, owner rule: never bury
      a genuine escalation): if the headline reports a violent event (struck,
      sinks, killed, blast, seize, ...) the entity rule NEVER links it, whether
      or not the root also reports one. A second ship sunk, a repeat missile
      attack or a second blast is a new escalation, not a follow-up, and the
      entity rule cannot tell a repeat from a rewording. Such a candidate can
      link only through the URL rule (same URL, same story); otherwise it
      becomes a new incident and is pushed. The rule is conservative on
      purpose and errs toward pushing. (This subsumes the earlier new-attack
      veto: #36 "More tankers struck ... as Iran reiterates conditions" is not
      a follow-up of #35 "Iran says Hormuz will not reopen until conditions
      are met");
   d. the classification did not fail: a failed classification's severity is
      a fallback guess, so it keeps its pre-B7 push guarantee (UNCLASSIFIED)
      instead of being linked silently on a shared place name.
   Opposite direction is allowed here: it becomes an update push.
   Replayed over all 78 live alerts (tests/test_alerting_incident_replay.py)
   the only incidents with more than one alert are #12/#13, #33/#39, #54/#55
   and #71/#72.

Limits, stated plainly: entities are read from headlines only, through a small
gazetteer (an unlisted place links nothing, i.e. today's behaviour); event
words are plain headline words, so a follow-up reworded with no word in
common with its root is not linked by the entity rule (it alerts as before
B7; the URL rule still catches re-coverage on a remembered URL); direction is
the classifier's polarity, falling back to the headline's price verb; there is
no LLM call. This module reads the store and never writes.
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
from data_layer.entities import incident_entities, strip_entities

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

# Entity rule (b): shared event words needed on top of a shared entity. 2, not 1: one shared word
# is routine in one theatre ("reopen" joined #9 and #12, two different Iranian offers 19 h apart).
ENTITY_RULE_MIN_EVENT_WORDS = 2


def _word_set(words: str) -> frozenset[str]:
    """The given words in dedup.significant_words form (lower-case, 6-char stems), so lists match tokens."""
    return frozenset(dedup.significant_words(words))


# Words that name the war or the market rather than one incident: in an active war two different
# attacks share "drone attack" (#56 Yandex data centre vs #60 Zelenskyy on the ceasefire).
_GENERIC_EVENT_WORDS = _word_set(
    "attack attacks attacked strike strikes struck drone drones missile missiles war wars conflict "
    "tension tensions threat threats threaten escalate escalates escalation military "
    "oil price prices crude brent wti barrel barrels market markets "
    # the generic actors data_layer/entities.py leaves out of the gazetteer for the same reason
    "trump us american americans washington white house fed federal reserve fomc"
)
# Words that report a violent event; rule (c) vetoes a link when only the candidate has one.
_VIOLENT_EVENT_WORDS = _word_set(
    "attack attacks attacked strike strikes struck airstrike airstrikes drone drones missile missiles "
    "rocket rockets blast blasts explosion explosions explode explodes exploded bomb bombs bombing "
    "sink sinks sank sunk seize seizes seized seizure killed kills dead injured wounded shot shooting"
)
# " - Reuters" / " - Bloomberg": a publisher suffix is not an event word.
_PUBLISHER_SUFFIX = re.compile(r"\s+-\s+[\w.' ]{1,40}$")


def event_words(headline: str) -> frozenset[str]:
    """Significant headline words with publisher suffix and gazetteer names removed (rule b and c input)."""
    words = _word_set(strip_entities(_PUBLISHER_SUFFIX.sub("", headline or "")))
    return frozenset(w for w in words if len(w) > 1)  # a stripped "Russia's" leaves a bare "'s" -> ""


def entity_rule_links(headline: str, root_headline: str) -> Optional[frozenset[str]]:
    """
    Entity rule (a)-(c) for one headline against one incident root: the shared entities when
    they link, else None. Family, window, root-only and failed-classification checks are
    find_incident's.
    """
    shared_entities = incident_entities(headline) & incident_entities(root_headline)
    if not shared_entities:
        return None
    words, root_words = event_words(headline), event_words(root_headline)
    if len((words & root_words) - _GENERIC_EVENT_WORDS) < ENTITY_RULE_MIN_EVENT_WORDS:
        return None
    if words & _VIOLENT_EVENT_WORDS:  # violent-event headlines never link by entity (rule c): errs toward pushing
        return None
    return shared_entities


@dataclass(frozen=True)
class IncidentCandidate:
    """The new article as the linking rules see it, before anything is stored."""
    headline: str
    category: str
    polarity: Optional[str]
    url: str
    published_utc: dt.datetime
    detected_at_utc: dt.datetime
    classification_failed: bool = False  # every LLM provider failed: the entity rule never applies (push guarantee)


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


def _same_story_on_url(cand: IncidentCandidate, cand_entities: frozenset[str], row: ShockAlertRow) -> bool:
    """
    The ONE same-story test for a URL sighting, used by both find_incident (URL rule) and
    effective_first_published (inherited age), so a candidate inherits an older age exactly
    when it links by URL. Not vetoed, not opposite in direction, AND a shared entity or a
    similar headline: a live-blog URL carries unrelated stories (#41/#43, #76/#77), so the
    URL alone is not enough.
    """
    if _vetoed(cand, row) or opposite_direction(cand.polarity, cand.headline, row.polarity, row.headline):
        return False
    if cand_entities & incident_entities(row.headline):
        return True
    return difflib.SequenceMatcher(None, cand.headline.lower(), row.headline.lower()).ratio() >= dedup.SIMILARITY_THRESHOLD


def _entity_rule_roots(conn: sqlite3.Connection, cand: IncidentCandidate) -> list[ShockAlertRow]:
    """
    Incident ROOTS (incident_role NULL) of the candidate's family detected in the last 24 h,
    newest first. Only the root is compared, never a follow-up or update row: a follow-up
    headline drifts (#69, an update on Hormuz incident #68, also names "Russian refineries"),
    and matching it chained #71 "Trump waives Russia sanctions" onto a Hormuz sinking. The
    most recent member is deliberately NOT used either, for the same reason. So an incident's
    entity reach is its root headline for 24 h after the root, then it closes.
    """
    since = cand.detected_at_utc - dt.timedelta(hours=INCIDENT_ENTITY_WINDOW_HOURS)
    return [row for row in store.list_recent_alerts(conn, since) if row.incident_role is None and not _vetoed(cand, row)]


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

    # URL rule (K9 memory, 72 h): the sighting's row may be any member; it links to that row's incident.
    for _seen, row in _url_sightings(conn, cand):
        if _same_story_on_url(cand, cand_entities, row):
            return IncidentLink(incident_id=row.incident_id, alert_id=row.id, rule="url")

    # Entity rule, incident-scoped (module docstring, rules 2a-2d). Never for a failed classification
    # (2d): its severity is a fallback guess, so a link would make it silent with no way to know the
    # severity did not rise; it goes down the new-alert path and is pushed UNCLASSIFIED, as before B7.
    if cand.classification_failed or not cand_entities:
        return None
    for root in _entity_rule_roots(conn, cand):
        shared = entity_rule_links(cand.headline, root.headline)
        if shared:
            return IncidentLink(incident_id=root.incident_id, alert_id=root.id, rule="entity:" + ",".join(sorted(shared)))
    return None


def effective_first_published(conn: sqlite3.Connection, cand: IncidentCandidate) -> dt.datetime:
    """
    K9: a URL seen on an alert in the last 72 h keeps that sighting's first publication time (a
    re-stamp must look old: #39 gets #33's 3 Oct) only when the sighting passes the URL rule's own
    same-story test (_same_story_on_url): so an older age is inherited exactly when find_incident
    links by URL. A new story on a reused URL keeps its own time (#43, #52, and #77 on #76's
    CNBC live-blog URL).
    """
    cand_entities = incident_entities(cand.headline)
    times = [cand.published_utc]
    for seen, row in _url_sightings(conn, cand):
        if _same_story_on_url(cand, cand_entities, row):
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
