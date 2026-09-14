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
