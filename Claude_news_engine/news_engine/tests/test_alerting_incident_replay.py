"""
B7 final-review regression: replay EVERY stored live shock alert through the incident rules.

tests/fixtures/b7_live_alerts_all.json is a verbatim, read-only (sqlite mode=ro) copy of all 78
rows of the live shock_alerts.db on 2026-10-22 (ids 1..79; #2 was never stored). Each alert is
replayed in detection order the way alerting/poll_once.py handles a non-dedup article: its first
source is the candidate (classification_failed when classification_method is
llm_failed_fallback), effective_first_published + find_incident decide age and incident,
update_reason decides follow-up vs update, the row is stored, and every source URL is
remembered (later sources at their own published time, as a dedup merge would).

The first B7 build's entity rule compared each candidate with EVERY alert of the last 24 h on
one shared place name: over this sequence it silenced pushed alerts #60, #65, #71 and #79,
chained #71/#72 onto Hormuz incident #68 through update row #69, buried "More tankers struck"
(#36) under Hormuz talks (#35), and gave #77 an inherited stale age from #76's live-blog URL.

Expected grouping, in full -- every other alert is its own incident:
  #12/#13  URL rule: same Reuters URL; both name Iran + Hormuz and share "floats conditions
           for reopening". Same-severity follow-up: stored, no push.
  #33/#39  URL rule: #39 is #33's Reuters URL re-stamped 62 h later. #39 was High against
           #33's Medium: pushed once as an update, with #33's 3 Oct first publication.
  #54/#55  URL rule: same URL; blast at Riyadh airport. Follow-up, no push.
  #71/#72  URL rule: same URL; "Trump waives broad new Russia sanctions". Follow-up, no push.
Pairs that must stay apart: #41/#43 (CNBC live blog, opposite direction), #46/#52 (Isaias vs
Simon on one Google News URL), and the review's wrongly linked set #35/#36, #56/#60,
#64/#65, #68/#69, #69/#71, #78/#79, #48/#50, #6/#7, #76/#77.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest

from alerting import incident, store
from alerting.poll_once import _should_push

UTC = dt.timezone.utc
_FIXTURE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "b7_live_alerts_all.json").read_text(encoding="utf-8"))
_ALERTS: list[dict] = _FIXTURE["alerts"]

# incident root (live id) -> every live id on it, in detection order. Only multi-alert incidents.
EXPECTED_MULTI_ALERT_INCIDENTS: dict[int, list[int]] = {
    12: [12, 13],
    33: [33, 39],
    54: [54, 55],
    71: [71, 72],
}
EXPECTED_ROLES: dict[int, str] = {13: "follow_up", 39: "update", 55: "follow_up", 72: "follow_up"}


def _ts(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


@dataclass
class _Replayed:
    live_id: int
    root_live_id: int
    rule: Optional[str]
    role: Optional[str]
    reason: Optional[str]
    pushed: bool
    own_published: dt.datetime
    first_published: dt.datetime


def _replay() -> dict[int, _Replayed]:
    conn = store.get_connection(":memory:")
    live_of: dict[int, int] = {}
    out: dict[int, _Replayed] = {}
    for alert in _ALERTS:
        first = alert["sources"][0]
        failed = alert["classification_method"] == "llm_failed_fallback"
        detected, published = _ts(alert["detected_at_utc"]), _ts(first["published_utc"])
        cand = incident.IncidentCandidate(
            headline=alert["headline"], category=alert["category"], polarity=alert["polarity"], url=first["url"],
            published_utc=published, detected_at_utc=detected, classification_failed=failed,
        )
        first_published = incident.effective_first_published(conn, cand)
        link = incident.find_incident(conn, cand)
        role = reason = None
        if link is not None:
            reason = incident.update_reason(store.list_incident_alerts(conn, link.incident_id), alert["severity"],
                                            alert["polarity"], alert["headline"], failed)
            role = "update" if reason else "follow_up"
        new_id = store.record_alert(
            conn, headline=alert["headline"], source=first["source"], url=first["url"], published_utc=published,
            detected_at_utc=detected, category=alert["category"], severity=alert["severity"],
            classification_method=alert["classification_method"], rationale=None, affected_symbols=[],
            polarity=alert["polarity"], incident_id=link.incident_id if link else None, incident_role=role,
            incident_rule=link.rule if link else None, first_published_utc=first_published,
        )
        live_of[new_id] = alert["id"]
        for index, source in enumerate(alert["sources"]):
            source_published = _ts(source["published_utc"])
            if index == 0:
                store.remember_url(conn, source["url"], new_id, detected, first_published)
            else:
                store.remember_url(conn, source["url"], new_id, source_published, source_published)
        # poll_once: a new incident pushes per _should_push; a follow-up only with an update reason.
        pushed = _should_push(alert["severity"], failed) if link is None else bool(reason)
        out[alert["id"]] = _Replayed(
            live_id=alert["id"], root_live_id=live_of[link.incident_id] if link else alert["id"],
            rule=link.rule if link else None, role=role, reason=reason, pushed=pushed,
            own_published=published, first_published=first_published,
        )
    return out


@pytest.fixture(scope="module")
def replay() -> dict[int, _Replayed]:
    return _replay()


def test_fixture_is_the_whole_live_table():
    assert len(_ALERTS) == 78
    assert [a["id"] for a in _ALERTS] == sorted(a["id"] for a in _ALERTS)  # detection order == id order here


def test_exact_incident_grouping(replay):
    groups: dict[int, list[int]] = {}
    for row in replay.values():
        groups.setdefault(row.root_live_id, []).append(row.live_id)
    multi = {root: ids for root, ids in groups.items() if len(ids) > 1}
    assert multi == EXPECTED_MULTI_ALERT_INCIDENTS
    singletons = {root for root, ids in groups.items() if len(ids) == 1}
    assert len(singletons) == len(_ALERTS) - sum(len(ids) for ids in EXPECTED_MULTI_ALERT_INCIDENTS.values())


def test_acceptance_pairs_link_by_url_with_expected_roles(replay):
    for live_id, role in EXPECTED_ROLES.items():
        assert replay[live_id].rule == "url", live_id
        assert replay[live_id].role == role, live_id
    assert replay[39].reason == "severity rose: Medium -> High"


@pytest.mark.parametrize("first,second", [
    (41, 43), (46, 52), (35, 36), (35, 38), (56, 60), (64, 65), (68, 69), (69, 71), (78, 79), (48, 50), (6, 7),
    (76, 77), (9, 12),
])
def test_pairs_that_must_stay_apart(replay, first, second):
    assert replay[second].root_live_id != replay[first].root_live_id


def test_only_the_three_same_severity_follow_ups_are_silent(replay):
    silent = sorted(r.live_id for r in replay.values() if r.role == "follow_up")
    assert silent == [13, 55, 72]
    # Every alert the live system pushed is still pushed, except those three follow-ups.
    live_sent = {a["id"] for a in _ALERTS if a["delivery_status"] == "sent"}
    assert {i for i in live_sent if not replay[i].pushed} == {55, 72}  # #13 was not pushed live either


def test_review_buried_alerts_push_again(replay):
    for live_id in (36, 38, 60, 65, 71, 79):
        assert replay[live_id].role is None and replay[live_id].pushed, live_id


def test_failed_classifications_are_never_linked_by_entity(replay):
    failed = [a["id"] for a in _ALERTS if a["classification_method"] == "llm_failed_fallback"]
    for live_id in failed:
        rule = replay[live_id].rule
        assert rule is None or rule == "url", live_id


def test_inherited_age_iff_url_link(replay):
    for row in replay.values():
        inherited = row.first_published != row.own_published
        assert inherited == (row.rule == "url"), row.live_id
    # #77 is fresh on #76's live-blog URL (no shared entity, low similarity): it keeps its own time.
    assert replay[77].first_published == dt.datetime(2026, 10, 21, 12, 48, 55, tzinfo=UTC)
    assert replay[39].first_published == dt.datetime(2026, 10, 3, 20, 17, 10, tzinfo=UTC)


if __name__ == "__main__":
    for item in _replay().values():
        if item.rule:
            print(f"#{item.live_id} -> incident #{item.root_live_id} ({item.rule}) {item.role} {item.reason or ''}")
