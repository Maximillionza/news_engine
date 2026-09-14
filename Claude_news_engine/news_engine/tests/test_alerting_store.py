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
