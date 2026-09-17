from __future__ import annotations

import datetime as dt

from alerting import store

UTC = dt.timezone.utc


def test_record_and_get_alert_round_trip():
    conn = store.get_connection(":memory:")
    alert_id = store.record_alert(
        conn,
        headline="Strait of Hormuz closed after naval incident",
        source="reuters_business",
        url="https://example.com/hormuz",
        published_utc=dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC),
        detected_at_utc=dt.datetime(2026, 9, 14, 8, 1, tzinfo=UTC),
        category="energy",
        severity="High",
        classification_method="rule_tier",
        rationale=None,
        affected_symbols=[{"symbol": "XAUUSD", "channel": "safe_haven"}],
    )
    row = store.get_alert(conn, alert_id)
    assert row is not None
    assert row.headline == "Strait of Hormuz closed after naval incident"
    assert row.category == "energy"
    assert row.severity == "High"
    assert row.classification_method == "rule_tier"
    assert row.sources == [{
        "source": "reuters_business", "url": "https://example.com/hormuz",
        "published_utc": "2026-09-14T08:00:00+00:00",
    }]
    assert row.affected_symbols == [{"symbol": "XAUUSD", "channel": "safe_haven"}]
    assert row.delivery_status is None
    assert row.reality_mismatch is None


def test_append_source_adds_corroboration_not_new_row():
    conn = store.get_connection(":memory:")
    alert_id = store.record_alert(
        conn, headline="Headline", source="reuters_business", url="https://a",
        published_utc=dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC),
        detected_at_utc=dt.datetime(2026, 9, 14, 8, 1, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier",
        rationale=None, affected_symbols=[],
    )
    store.append_source(conn, alert_id, "cnbc_top_news", "https://b", dt.datetime(2026, 9, 14, 8, 3, tzinfo=UTC))
    row = store.get_alert(conn, alert_id)
    assert len(row.sources) == 2
    assert row.sources[1]["source"] == "cnbc_top_news"


def test_cursor_round_trip_and_default_none():
    conn = store.get_connection(":memory:")
    assert store.get_cursor(conn, "reuters_business") is None
    store.set_cursor(conn, "reuters_business", dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC))
    assert store.get_cursor(conn, "reuters_business") == dt.datetime(2026, 9, 14, 8, 0, tzinfo=UTC)
    # setting again overwrites, doesn't duplicate (PRIMARY KEY on source)
    store.set_cursor(conn, "reuters_business", dt.datetime(2026, 9, 14, 8, 2, tzinfo=UTC))
    assert store.get_cursor(conn, "reuters_business") == dt.datetime(2026, 9, 14, 8, 2, tzinfo=UTC)


def test_record_near_miss():
    conn = store.get_connection(":memory:")
    near_miss_id = store.record_near_miss(conn, "Oil prices tick up slightly", "energy", 0.31)
    assert isinstance(near_miss_id, int)


def test_list_recent_alerts_in_category_and_overall():
    conn = store.get_connection(":memory:")
    old = store.record_alert(
        conn, headline="Old energy alert", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 1, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 1, tzinfo=UTC),
        category="energy", severity="Low", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    recent = store.record_alert(
        conn, headline="Recent energy alert", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 14, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    since = dt.datetime(2026, 9, 10, tzinfo=UTC)
    in_category = store.list_recent_alerts_in_category(conn, "energy", since)
    assert [r.id for r in in_category] == [recent]
    overall = store.list_recent_alerts(conn, since)
    assert [r.id for r in overall] == [recent]


def test_set_severity_upgrades_stored_value():
    conn = store.get_connection(":memory:")
    alert_id = store.record_alert(
        conn, headline="H", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 17, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 17, tzinfo=UTC),
        category="energy", severity="Medium", classification_method="llm", rationale=None, affected_symbols=[],
    )
    store.set_severity(conn, alert_id, "High")
    row = store.get_alert(conn, alert_id)
    assert row.severity == "High"


def test_record_reality_check_writes_result():
    conn = store.get_connection(":memory:")
    alert_id = store.record_alert(
        conn, headline="H", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 14, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    store.record_reality_check(
        conn, alert_id,
        move_5min={"XAUUSD": 12.5}, move_secondary={"XAUUSD": 15.0},
        mismatch=False, checked_at_utc=dt.datetime(2026, 9, 21, tzinfo=UTC),
    )
    row = store.get_alert(conn, alert_id)
    assert row.reality_move_5min == {"XAUUSD": 12.5}
    assert row.reality_mismatch is False
    assert row.reality_check_at_utc == dt.datetime(2026, 9, 21, tzinfo=UTC)


def test_get_alerts_needing_reality_check_excludes_already_checked():
    conn = store.get_connection(":memory:")
    unchecked = store.record_alert(
        conn, headline="H1", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 14, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    checked = store.record_alert(
        conn, headline="H2", source="s", url="u",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), detected_at_utc=dt.datetime(2026, 9, 14, tzinfo=UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )
    store.record_reality_check(conn, checked, move_5min=None, move_secondary=None, mismatch=None,
                                checked_at_utc=dt.datetime(2026, 9, 15, tzinfo=UTC))
    pending = store.get_alerts_needing_reality_check(conn, dt.datetime(2026, 9, 1, tzinfo=UTC))
    assert [r.id for r in pending] == [unchecked]
