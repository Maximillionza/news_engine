"""
Tests for alerting/incident.py -- B7 (2026-10-22) incident linking (K10) and
re-stamped URL age (K9).

The live pairs are copied verbatim (read-only) from the live shock_alerts.db
into tests/fixtures/b7_live_alert_pairs.json. Owner acceptance: #54/#55,
#71/#72, #33/#39 and #12/#13 link as one incident; #41/#43 (one CNBC
live-blog URL, opposite stories) and #46/#52 (two hurricanes sharing a
Google News URL) do not.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Optional

import pytest

from alerting import freshness, incident, store
from alerting.incident import (
    IncidentCandidate, effective_first_published, find_incident, headline_move, opposite_direction, update_reason,
)

UTC = dt.timezone.utc
_MODULE_PATH = Path(__file__).resolve().parent.parent / "alerting" / "incident.py"
_FIXTURES = Path(__file__).resolve().parent / "fixtures"
# Every live alert (read-only copy, final-review fix) overlaid with the original pair fixture (identical rows).
_LIVE = {
    **{str(a["id"]): a for a in json.loads((_FIXTURES / "b7_live_alerts_all.json").read_text(encoding="utf-8"))["alerts"]},
    **json.loads((_FIXTURES / "b7_live_alert_pairs.json").read_text(encoding="utf-8")),
}


def _ts(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value)


def _seed(conn, n: int, polarity: Optional[str] = None, severity: Optional[str] = None,
          incident_id: Optional[int] = None, role: Optional[str] = None) -> int:
    """Stores live alert #n as it was: sources[0] at detection, later sources appended, every URL remembered."""
    alert = _LIVE[str(n)]
    detected = _ts(alert["detected_at_utc"])
    first = alert["sources"][0]
    alert_id = store.record_alert(
        conn, headline=alert["headline"], source=first["source"], url=first["url"],
        published_utc=_ts(first["published_utc"]), detected_at_utc=detected, category=alert["category"],
        severity=severity or "Medium", classification_method="llm_ollama", rationale=None, affected_symbols=[],
        polarity=polarity, incident_id=incident_id,
        incident_role=role or (None if incident_id is None else "follow_up"),
    )
    for source in alert["sources"][1:]:
        store.append_source(conn, alert_id, source["source"], source["url"], _ts(source["published_utc"]))
    for index, source in enumerate(alert["sources"]):
        published = _ts(source["published_utc"])
        store.remember_url(conn, source["url"], alert_id, detected if index == 0 else published, published)
    return alert_id


def _cand(n: int, polarity: Optional[str] = None, failed: bool = False, url: Optional[str] = None) -> IncidentCandidate:
    alert = _LIVE[str(n)]
    first = alert["sources"][0]
    return IncidentCandidate(
        headline=alert["headline"], category=alert["category"], polarity=polarity, url=url or first["url"],
        published_utc=_ts(first["published_utc"]), detected_at_utc=_ts(alert["detected_at_utc"]),
        classification_failed=failed,
    )


def _other(headline: str, category: str, at: dt.datetime, url: str = "https://example.com/other-story",
           failed: bool = False) -> IncidentCandidate:
    return IncidentCandidate(headline=headline, category=category, polarity=None, url=url,
                             published_utc=at, detected_at_utc=at, classification_failed=failed)


@pytest.mark.parametrize("first,second", [(12, 13), (54, 55), (71, 72), (33, 39)],
                         ids=["12-13", "54-55", "71-72", "33-39"])
def test_live_pairs_link(first, second):
    conn = store.get_connection(":memory:")
    first_id = _seed(conn, first)
    link = find_incident(conn, _cand(second))
    assert link is not None
    assert link.incident_id == first_id
    assert link.alert_id == first_id
    assert link.rule == "url"


@pytest.mark.parametrize("seed_polarity,cand_polarity", [(None, None), ("escalation", "relief")],
                         ids=["41-43-unclear", "41-43-polarity"])
def test_live_pairs_that_must_not_link(seed_polarity, cand_polarity):
    conn = store.get_connection(":memory:")
    _seed(conn, 41, polarity=seed_polarity)
    assert find_incident(conn, _cand(43, cand_polarity)) is None


def test_storm_pair_does_not_link():
    conn = store.get_connection(":memory:")
    _seed(conn, 46)
    # #46 carries #52's URL (the Simon article was merged into Isaias by similarity on 2026-10-09).
    assert store.lookup_seen_url(conn, _LIVE["52"]["sources"][0]["url"], _ts(_LIVE["46"]["detected_at_utc"]))
    assert find_incident(conn, _cand(52)) is None


def test_entity_rule_window_is_24h():
    conn = store.get_connection(":memory:")
    id54 = _seed(conn, 54)
    detected54 = _ts(_LIVE["54"]["detected_at_utc"])
    headline = "Second blast reported at Riyadh airport terminal"
    link = find_incident(conn, _other(headline, "geopolitical_conflict", detected54 + dt.timedelta(hours=23)))
    assert link is not None
    assert link.incident_id == id54
    assert link.rule == "entity:saudi arabia"
    assert find_incident(conn, _other(headline, "geopolitical_conflict", detected54 + dt.timedelta(hours=25))) is None


def test_family_is_respected():
    conn = store.get_connection(":memory:")
    id54 = _seed(conn, 54)
    at = _ts(_LIVE["54"]["detected_at_utc"]) + dt.timedelta(hours=2)
    headline = "Riyadh airport blast halts Saudi jet fuel deliveries"
    link = find_incident(conn, _other(headline, "energy", at))
    assert link is not None and link.incident_id == id54
    assert find_incident(conn, _other(headline, "central_bank", at)) is None


def test_trump_only_overlap_does_not_link():
    conn = store.get_connection(":memory:")
    _seed(conn, 71)
    at = _ts(_LIVE["71"]["detected_at_utc"]) + dt.timedelta(hours=2)
    assert find_incident(conn, _other("Trump threatens new tariffs on Iran", "geopolitical_conflict", at)) is None


def test_url_rule_needs_entity_or_similar_headline():
    conn = store.get_connection(":memory:")
    _seed(conn, 12)
    at = _ts(_LIVE["12"]["detected_at_utc"]) + dt.timedelta(hours=2)
    cand = _other("Crude traders brace for volatile week", "energy", at, url=_LIVE["12"]["sources"][0]["url"])
    assert find_incident(conn, cand) is None


def test_follow_up_links_to_the_incident_root_not_the_matched_row():
    conn = store.get_connection(":memory:")
    root = _seed(conn, 33)
    follow_up = _seed(conn, 39, incident_id=root)
    at = _ts(_LIVE["39"]["detected_at_utc"]) + dt.timedelta(hours=1)
    cand = _other("Zelenskiy says Ukraine will strike Russian refineries", "geopolitical_conflict", at,
                  url=_LIVE["39"]["sources"][0]["url"])
    link = find_incident(conn, cand)
    assert link is not None
    assert link.incident_id == root
    assert link.alert_id == follow_up  # newest sighting of the URL


def test_restamped_url_keeps_first_publication():
    conn = store.get_connection(":memory:")
    _seed(conn, 33)
    first = effective_first_published(conn, _cand(39))
    assert first == dt.datetime(2026, 10, 3, 20, 17, 10, tzinfo=UTC)
    age = freshness.age_minutes(first, _ts(_LIVE["39"]["detected_at_utc"]))
    assert age == 3715
    assert freshness.freshness_band(age) == "Very stale"


def test_new_story_on_reused_url_keeps_own_age():
    conn = store.get_connection(":memory:")
    _seed(conn, 41, polarity="escalation")
    assert effective_first_published(conn, _cand(43, "relief")) == dt.datetime(2026, 10, 7, 18, 18, 47, tzinfo=UTC)

    conn = store.get_connection(":memory:")
    _seed(conn, 46)
    assert effective_first_published(conn, _cand(52)) == dt.datetime(2026, 10, 9, 21, 49, 43, tzinfo=UTC)


def test_unseen_url_keeps_own_age():
    conn = store.get_connection(":memory:")
    cand = _other("Brand new story", "energy", dt.datetime(2026, 10, 20, 8, 0, tzinfo=UTC))
    assert effective_first_published(conn, cand) == cand.published_utc


def test_headline_move_and_opposite_direction():
    h41, h43 = _LIVE["41"]["headline"], _LIVE["43"]["headline"]
    assert headline_move(h41) == "up"
    assert headline_move(h43) == "down"
    assert headline_move("Oil rises as stocks fall") is None
    assert headline_move("Iran floats conditions for Hormuz reopening") is None
    assert opposite_direction("escalation", "", "relief", "") is True
    assert opposite_direction("hawkish", "", "escalation", "") is False
    assert opposite_direction(None, h41, "unclear", h43) is True
    assert opposite_direction("escalation", h41, "escalation", h43) is False  # known polarities win over the headline


def test_storm_conflict_and_family():
    assert incident.storm_conflict("Hurricane Isaias nears Florida", "Hurricane Simon hits Mexico") is True
    assert incident.storm_conflict("Hurricane Isaias nears Florida", "Hurricane Isaias makes landfall") is False
    assert incident.storm_conflict("Hurricane Isaias nears Florida", "Gulf ports close") is False
    assert incident.category_family("energy") == incident.category_family("geopolitical_conflict")
    assert incident.category_family("central_bank") == "central_bank"


def _rows(conn, specs: list[tuple[str, Optional[str], str]]) -> list[store.ShockAlertRow]:
    """specs: (severity, polarity, headline) in detection order; all on the first row's incident."""
    t0 = dt.datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
    root: Optional[int] = None
    for i, (severity, polarity, headline) in enumerate(specs):
        at = t0 + dt.timedelta(hours=i)
        alert_id = store.record_alert(
            conn, headline=headline, source="s", url=f"https://example.com/{i}", published_utc=at,
            detected_at_utc=at, category="energy", severity=severity, classification_method="llm_ollama",
            rationale=None, affected_symbols=[], polarity=polarity, incident_id=root,
            incident_role=None if root is None else "follow_up",
        )
        root = root or alert_id
    return store.list_incident_alerts(conn, root)


def test_update_reason_cases():
    conn = store.get_connection(":memory:")
    rows = _rows(conn, [("Medium", "escalation", "Oil rises after tanker attack")])
    h = "Tanker attack follow-up"
    assert update_reason(rows, "High", "escalation", h, False) == "severity rose: Medium -> High"
    assert update_reason(rows, "Medium", "escalation", h, False) is None
    assert update_reason(rows, "Medium", "relief", h, False) == "direction changed: escalation -> relief"
    assert update_reason(rows, "High", "escalation", h, True) is None

    conn = store.get_connection(":memory:")
    rows = _rows(conn, [("Medium", None, "Oil rises after tanker attack")])
    assert update_reason(rows, "Medium", "unclear", "Oil prices fall as tanker is freed", False) == "direction changed: up -> down"

    conn = store.get_connection(":memory:")
    rows = _rows(conn, [("High", "escalation", "Strait closed"), ("Medium", "escalation", "Strait still closed")])
    assert incident.incident_max_severity(rows) == "High"
    assert update_reason(rows, "High", "escalation", h, False) is None


# --- Final-review fixes (2026-10-22): incident-scoped entity rule, push guarantee, one same-story test ---


def test_entity_rule_links_54_55_without_the_shared_url():
    conn = store.get_connection(":memory:")
    id54 = _seed(conn, 54)
    link = find_incident(conn, _cand(55, url="https://example.com/riyadh-airport-eyewitnesses"))
    assert link is not None
    assert link.incident_id == id54
    assert link.rule == "entity:saudi arabia"  # shares "blast" + "airport" as well as Riyadh


@pytest.mark.parametrize("root,cand", [(78, 79), (56, 60), (64, 65), (68, 69), (6, 7), (48, 50)],
                         ids=["78-79", "56-60", "64-65", "68-69", "6-7", "48-50"])
def test_shared_theatre_name_alone_does_not_link(root, cand):
    """Classified on purpose (failed=False): the review's wrong links must fail on the rule itself, not on 2d."""
    conn = store.get_connection(":memory:")
    _seed(conn, root)
    assert find_incident(conn, _cand(cand)) is None
    assert incident.entity_rule_links(_LIVE[str(cand)]["headline"], _LIVE[str(root)]["headline"]) is None


def test_new_attack_is_not_a_follow_up_of_talk():
    """#36 "More tankers struck ... as Iran reiterates conditions" vs #35 "Iran says Hormuz will not reopen until conditions"."""
    h35, h36 = _LIVE["35"]["headline"], _LIVE["36"]["headline"]
    shared_words = (incident.event_words(h35) & incident.event_words(h36)) - incident._GENERIC_EVENT_WORDS
    assert len(shared_words) >= incident.ENTITY_RULE_MIN_EVENT_WORDS  # only the new-attack veto keeps them apart
    conn = store.get_connection(":memory:")
    _seed(conn, 35)
    assert find_incident(conn, _cand(36)) is None


def test_entity_rule_compares_incident_roots_only():
    """#69 (an update on Hormuz incident #68) names Russian refineries; a Russia story must not chain onto #68 through it."""
    conn = store.get_connection(":memory:")
    id68 = _seed(conn, 68)
    _seed(conn, 69, incident_id=id68, role="update")
    at = _ts(_LIVE["69"]["detected_at_utc"]) + dt.timedelta(hours=1)
    headline = "Ukraine vows to hit more Russian refineries after drone raid"
    assert incident.entity_rule_links(headline, _LIVE["69"]["headline"])  # would link to the update row itself
    assert find_incident(conn, _other(headline, "geopolitical_conflict", at)) is None


def test_entity_window_runs_from_the_root_not_the_latest_follow_up():
    conn = store.get_connection(":memory:")
    id54 = _seed(conn, 54)
    detected54 = _ts(_LIVE["54"]["detected_at_utc"])
    store.record_alert(
        conn, headline="Second blast at Riyadh airport", source="s", url="https://example.com/second-blast",
        published_utc=detected54 + dt.timedelta(hours=20), detected_at_utc=detected54 + dt.timedelta(hours=20),
        category="geopolitical_conflict", severity="High", classification_method="llm_ollama", rationale=None,
        affected_symbols=[], incident_id=id54, incident_role="follow_up", incident_rule="entity:saudi arabia",
    )
    late = _other("Third blast at Riyadh airport", "geopolitical_conflict", detected54 + dt.timedelta(hours=25))
    assert find_incident(conn, late) is None


def test_failed_classification_is_never_linked_by_the_entity_rule():
    conn = store.get_connection(":memory:")
    id54 = _seed(conn, 54)
    at = _ts(_LIVE["54"]["detected_at_utc"]) + dt.timedelta(hours=1)
    headline = "Second blast reported at Riyadh airport terminal"
    assert find_incident(conn, _other(headline, "geopolitical_conflict", at, failed=True)) is None
    classified = find_incident(conn, _other(headline, "geopolitical_conflict", at))
    assert classified is not None and classified.incident_id == id54  # the rule itself would link it


def test_failed_classification_still_links_by_url():
    conn = store.get_connection(":memory:")
    id54 = _seed(conn, 54)
    link = find_incident(conn, _cand(55, failed=True))
    assert link is not None and link.incident_id == id54 and link.rule == "url"


def test_live_blog_new_story_keeps_its_own_age():
    """#77 is 2 min fresh on the CNBC 10/21 live-blog URL #76 absorbed; no shared entity, low similarity."""
    conn = store.get_connection(":memory:")
    _seed(conn, 76)
    cand = _cand(77, polarity="escalation")
    assert store.lookup_seen_url(conn, cand.url, cand.detected_at_utc - dt.timedelta(hours=72))
    assert find_incident(conn, cand) is None
    assert effective_first_published(conn, cand) == dt.datetime(2026, 10, 21, 12, 48, 55, tzinfo=UTC)


def test_inherited_age_uses_the_url_rule_test():
    """A URL sighting with no shared entity and no similar headline neither links nor ages the candidate."""
    conn = store.get_connection(":memory:")
    _seed(conn, 12)
    at = _ts(_LIVE["12"]["detected_at_utc"]) + dt.timedelta(hours=2)
    cand = _other("Crude traders brace for volatile week", "energy", at, url=_LIVE["12"]["sources"][0]["url"])
    assert find_incident(conn, cand) is None
    assert effective_first_published(conn, cand) == at


def test_event_words_drop_entities_publisher_and_generic_words():
    words = incident.event_words("Loud blast at Riyadh airport as travellers evacuated - Reuters")
    assert "blast" in words and "airpor" in words
    assert not {"riyadh", "reuters"} & words
    assert incident.event_words("Strait of Hormuz") == frozenset()  # no leftover "strait"
    assert incident.event_words("Russia's drones") == frozenset({"drones"})  # no bare "'s" token
    assert incident.entity_rule_links("Drone attack on Russia", "Russia says drone attack hit depot") is None


def test_deploy_runbook_states_verify_condition_and_backfill_rerun():
    runbook = (_MODULE_PATH.parent.parent / "docs" / "b7-deploy.md").read_text(encoding="utf-8")
    assert "if any alert was detected in the last 72 h" in runbook
    assert "DROP TABLE seen_urls" in runbook


def test_source_has_no_backspace_bytes():
    assert b"\x08" not in _MODULE_PATH.read_bytes()
