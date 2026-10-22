from __future__ import annotations

import datetime as dt

from alerting import store
from alerting.dedup import find_existing_alert

UTC = dt.timezone.utc


def _seed_alert(conn, headline: str, category: str, detected_at_utc: dt.datetime) -> int:
    return store.record_alert(
        conn, headline=headline, source="s", url="u", published_utc=detected_at_utc,
        detected_at_utc=detected_at_utc, category=category, severity="High",
        classification_method="rule_tier", rationale=None, affected_symbols=[],
    )


def test_similar_headline_same_category_within_window_matches():
    conn = store.get_connection(":memory:")
    now = dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC)
    existing_id = _seed_alert(conn, "Strait of Hormuz closed after naval clash", "energy", now)
    match = find_existing_alert("Strait of Hormuz closed following naval clash", "energy", conn, now_utc=now)
    assert match == existing_id


def test_different_category_never_matches():
    conn = store.get_connection(":memory:")
    now = dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC)
    _seed_alert(conn, "Strait of Hormuz closed after naval clash", "energy", now)
    match = find_existing_alert("Strait of Hormuz closed after naval clash", "geopolitical_conflict", conn, now_utc=now)
    assert match is None


def test_dissimilar_headline_does_not_match():
    conn = store.get_connection(":memory:")
    now = dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC)
    _seed_alert(conn, "OPEC+ agrees to cut oil output", "energy", now)
    match = find_existing_alert("Refinery strike halts production in Texas", "energy", conn, now_utc=now)
    assert match is None


def test_outside_window_does_not_match():
    conn = store.get_connection(":memory:")
    old = dt.datetime(2026, 9, 14, 0, 0, tzinfo=UTC)
    _seed_alert(conn, "Strait of Hormuz closed after naval clash", "energy", old)
    match = find_existing_alert("Strait of Hormuz closed following naval clash", "energy", conn, window_hours=6.0)
    assert match is None


def test_default_window_catches_a_story_recovered_six_hours_later():
    """
    Regression test for a real production duplicate alert (2026-09-17):
    the same Hormuz pipeline-attack story was re-covered by CNBC under a
    reworded headline 6h06m after the original alert (real similarity
    ratio 0.877), missing the old 6.0-hour default window by minutes and
    firing a second Telegram push for the same event. Default widened to
    24.0 hours -- this same gap must now match using the DEFAULT window
    (no explicit window_hours override), matching how poll_once.py
    actually calls this function in production.
    """
    conn = store.get_connection(":memory:")
    original_time = dt.datetime(2026, 9, 17, 12, 46, 23, tzinfo=UTC)
    existing_id = _seed_alert(
        conn,
        "U.S. oil falls below $100 as Saudi Arabia reportedly offers more crude via Hormuz after pipeline attack",
        "energy", original_time,
    )
    now = original_time + dt.timedelta(hours=6, minutes=6)
    match = find_existing_alert(
        "Oil prices fall as Saudi Arabia reportedly offers more crude via Hormuz after pipeline attack",
        "energy", conn, now_utc=now,
    )
    assert match == existing_id


# --- story-level dedup for ongoing sagas (impact audit 2026-10-15: 11 diesel-ban alerts, 5 for one hurricane) ---

def _hours_ago(h: float) -> dt.datetime:
    return dt.datetime.now(UTC) - dt.timedelta(hours=h)


def test_trade_policy_saga_headlines_sharing_a_topic_phrase_merge_across_days():
    conn = store.get_connection(":memory:")
    first = _seed_alert(conn, "Trump administration is examining whether a diesel export ban is feasible", "trade_policy", _hours_ago(40))
    assert find_existing_alert("Trump 'thinking about' diesel export ban, but says it could hurt gasoline", "trade_policy", conn) == first


def test_trade_policy_headlines_on_different_topics_do_not_merge():
    conn = store.get_connection(":memory:")
    _seed_alert(conn, "Trump administration is examining whether a diesel export ban is feasible", "trade_policy", _hours_ago(2))
    assert find_existing_alert("Retaliatory tariffs announced on Chinese steel imports", "trade_policy", conn) is None


def test_topic_merge_has_a_72_hour_limit():
    conn = store.get_connection(":memory:")
    _seed_alert(conn, "Trump administration is examining whether a diesel export ban is feasible", "trade_policy", _hours_ago(80))
    assert find_existing_alert("Oil industry warns a diesel export ban will raise fuel prices", "trade_policy", conn) is None


def test_same_named_storm_merges_but_a_different_storm_does_not():
    conn = store.get_connection(":memory:")
    polo = _seed_alert(conn, "Category 4 Hurricane Polo threatens Mexico's coast, landfall expected Monday", "natural_disaster_supply_chain", _hours_ago(30))
    assert find_existing_alert("Hurricane Polo hits northwest Mexico's Sonora state", "natural_disaster_supply_chain", conn) == polo
    assert find_existing_alert("Hurricane Simon rapidly strengthens off Mexico's Pacific coast", "natural_disaster_supply_chain", conn) is None


def test_energy_and_geopolitical_get_no_topic_merge_so_a_new_attack_is_never_buried():
    conn = store.get_connection(":memory:")
    _seed_alert(conn, "Iran says Strait of Hormuz will not reopen until conditions are met", "energy", _hours_ago(2))
    assert find_existing_alert("More tankers struck in the Middle East as Iran reiterates conditions for reopening the Strait of Hormuz", "energy", conn) is None


# --- B7 (2026-10-22): storm veto on the similarity path too ---

def test_similar_headline_different_storm_does_not_merge():
    """
    Live 2026-10-09: the Hurricane Simon article was merged into alert #46 (Isaias) by
    similarity (ratio 0.954), which is how #46 came to carry Simon's URL. Two headlines
    naming different storms never merge; the same storm still does.
    """
    conn = store.get_connection(":memory:")
    isaias = _seed_alert(
        conn, "Hurricane Isaias strengthens as US Gulf Coast prepares for landfall - Reuters",
        "natural_disaster_supply_chain", _hours_ago(1),
    )
    assert find_existing_alert(
        "Hurricane Simon strengthens as US Gulf Coast prepares for landfall - Reuters", "natural_disaster_supply_chain", conn,
    ) is None
    assert find_existing_alert(
        "Hurricane Isaias strengthens further as US Gulf Coast braces for landfall - Reuters", "natural_disaster_supply_chain", conn,
    ) == isaias
