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
