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


def test_provider_cooldown_roundtrip_and_overwrite():
    import datetime as dt
    from alerting import store
    conn = store.get_connection(":memory:")
    assert store.get_provider_cooldown_until(conn, "claude") is None

    first = dt.datetime(2026, 10, 5, 12, 15, tzinfo=dt.timezone.utc)
    store.set_provider_cooldown(conn, "claude", first)
    assert store.get_provider_cooldown_until(conn, "claude") == first
    assert store.get_provider_cooldown_until(conn, "ollama") is None  # providers are independent

    later = first + dt.timedelta(minutes=30)
    store.set_provider_cooldown(conn, "claude", later)
    assert store.get_provider_cooldown_until(conn, "claude") == later


# --- B2 K1/K7/K8 storage: migration, new row fields, outage notices ---------

# The pre-B2 shock_alerts literal (14 columns), copied verbatim so the
# migration is tested against the exact shape the live DB file has today.
_PRE_B2_SHOCK_ALERTS = """
CREATE TABLE shock_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    detected_at_utc TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    classification_method TEXT NOT NULL,
    rationale TEXT,
    affected_symbols_json TEXT NOT NULL,
    delivery_status TEXT,
    reality_move_5min_json TEXT,
    reality_move_secondary_json TEXT,
    reality_check_at_utc TEXT,
    reality_mismatch INTEGER
);
"""

_PRE_B2_COLUMNS = (
    "id", "headline", "sources_json", "detected_at_utc", "category", "severity",
    "classification_method", "rationale", "affected_symbols_json", "delivery_status",
    "reality_move_5min_json", "reality_move_secondary_json", "reality_check_at_utc",
    "reality_mismatch",
)

_B2_COLUMNS = (
    "polarity", "country", "us_link", "capped_no_us_link", "original_severity", "first_published_utc",
)


def _record(conn, **extra):
    return store.record_alert(
        conn, headline="H", source="s", url="u",
        published_utc=dt.datetime(2026, 10, 21, 9, 58, tzinfo=UTC),
        detected_at_utc=dt.datetime(2026, 10, 21, 10, 0, tzinfo=UTC),
        category="geopolitical", severity="Medium", classification_method="llm",
        rationale=None, affected_symbols=[{"symbol": "XAUUSD", "channel": "safe_haven", "lean": "up"}],
        **extra,
    )


def test_migration_is_idempotent_on_an_old_schema_db_copy(tmp_path):
    import json
    import sqlite3

    db_path = tmp_path / "old_shock_alerts.db"
    raw = sqlite3.connect(db_path)
    raw.executescript(_PRE_B2_SHOCK_ALERTS)
    raw.execute(
        "INSERT INTO shock_alerts (headline, sources_json, detected_at_utc, category, severity, "
        "classification_method, rationale, affected_symbols_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("Old row", json.dumps([{"source": "s", "url": "u", "published_utc": "2026-10-06T10:07:00+00:00"}]),
         "2026-10-06T10:09:00+00:00", "energy", "High", "rule_tier", None, "[]"),
    )
    raw.commit()
    raw.close()

    store._schema_ready_paths.clear()
    conn = store.get_connection(db_path)
    conn.close()
    store._schema_ready_paths.clear()
    conn = store.get_connection(db_path)
    store._migrate_shock_alert_columns(conn)
    store._migrate_shock_alert_columns(conn)

    names = [r["name"] for r in conn.execute("PRAGMA table_info(shock_alerts)").fetchall()]
    for column in _B2_COLUMNS:
        assert names.count(column) == 1
    assert len(names) == len(_PRE_B2_COLUMNS) + len(_B2_COLUMNS)

    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    assert "classifier_outage_notices" in tables

    rows = store.list_recent_alerts(conn, dt.datetime(2026, 10, 1, tzinfo=UTC))
    assert len(rows) == 1
    old = rows[0]
    assert old.headline == "Old row"
    assert old.polarity is None
    assert old.country is None
    assert old.us_link is None
    assert old.capped_no_us_link is None
    assert old.original_severity is None
    assert old.first_published_utc == dt.datetime(2026, 10, 6, 10, 7, tzinfo=UTC)
    conn.close()
    store._schema_ready_paths.clear()


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeOldSchemaConnection:
    """
    Stands in for a second process that loses the race: PRAGMA still shows
    the old 14 columns, but by the time this process ALTERs, the other
    one already added the column.
    """

    def __init__(self, alter_error):
        self._alter_error = alter_error
        self.commits = 0

    def execute(self, sql, *args):
        if sql.startswith("PRAGMA table_info"):
            return _FakeCursor([{"name": name} for name in _PRE_B2_COLUMNS])
        if sql.startswith("ALTER TABLE"):
            raise self._alter_error
        raise AssertionError(f"unexpected SQL: {sql}")

    def commit(self):
        self.commits += 1


def test_migration_tolerates_a_concurrent_duplicate_column():
    import sqlite3

    import pytest

    racing = _FakeOldSchemaConnection(sqlite3.OperationalError("duplicate column name: polarity"))
    store._migrate_shock_alert_columns(racing)  # must not raise
    assert racing.commits == 1

    broken = _FakeOldSchemaConnection(sqlite3.OperationalError("disk I/O error"))
    with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
        store._migrate_shock_alert_columns(broken)


def test_record_alert_round_trips_country_us_link_polarity_and_cap():
    conn = store.get_connection(":memory:")
    alert_id = _record(
        conn, polarity="escalation", country="RU", us_link="none",
        capped_no_us_link=True, original_severity="High",
    )
    row = store.get_alert(conn, alert_id)
    assert row.polarity == "escalation"
    assert row.country == "RU"
    assert row.us_link == "none"
    assert row.capped_no_us_link is True
    assert row.original_severity == "High"
    assert row.first_published_utc == dt.datetime(2026, 10, 21, 9, 58, tzinfo=UTC)
    stored = conn.execute("SELECT first_published_utc FROM shock_alerts WHERE id = ?", (alert_id,)).fetchone()
    assert stored["first_published_utc"] == "2026-10-21T09:58:00+00:00"


def test_record_alert_without_new_fields_stores_unknowns_and_first_published():
    conn = store.get_connection(":memory:")
    alert_id = _record(conn)
    row = store.get_alert(conn, alert_id)
    assert row.polarity is None
    assert row.country is None
    assert row.us_link is None
    assert row.capped_no_us_link is None
    assert row.original_severity is None
    assert row.first_published_utc == dt.datetime(2026, 10, 21, 9, 58, tzinfo=UTC)

    # capped_no_us_link=False is stored as a real False, not collapsed to unknown
    uncapped = store.get_alert(conn, _record(conn, capped_no_us_link=False))
    assert uncapped.capped_no_us_link is False


def test_old_row_first_published_comes_from_first_source_or_is_none():
    import json

    conn = store.get_connection(":memory:")

    def insert(sources_json):
        cur = conn.execute(
            "INSERT INTO shock_alerts (headline, sources_json, detected_at_utc, category, severity, "
            "classification_method, rationale, affected_symbols_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("Old", sources_json, "2026-10-06T10:09:00+00:00", "energy", "High", "rule_tier", None, "[]"),
        )
        conn.commit()
        return cur.lastrowid

    # index 0 (the source present at detection), not the earliest; naive = UTC
    two_sources = insert(json.dumps([
        {"published_utc": "2026-10-06T10:07:00"},
        {"published_utc": "2026-10-06T09:00:00+00:00"},
    ]))
    assert store.get_alert(conn, two_sources).first_published_utc == dt.datetime(2026, 10, 6, 10, 7, tzinfo=UTC)

    assert store.get_alert(conn, insert("[]")).first_published_utc is None
    assert store.get_alert(conn, insert(json.dumps([{"source": "s"}]))).first_published_utc is None
    assert store.get_alert(conn, insert(json.dumps([{"published_utc": "not a date"}]))).first_published_utc is None
    assert store.get_alert(conn, insert(json.dumps([{"published_utc": None}]))).first_published_utc is None
    assert store.get_alert(conn, insert(json.dumps({"not": "a list"}))).first_published_utc is None

    assert store._first_source_published([{"published_utc": "2026-10-06T12:07:00+02:00"}]) == \
        dt.datetime(2026, 10, 6, 10, 7, tzinfo=UTC)


def test_update_alert_assessment_rewrites_cap_fields_and_leans():
    conn = store.get_connection(":memory:")
    alert_id = _record(
        conn, polarity="escalation", country="RU", us_link="none",
        capped_no_us_link=True, original_severity="High",
    )
    new_symbols = [{"symbol": "XAUUSD", "channel": "safe_haven", "lean": "up"},
                   {"symbol": "USOIL", "channel": "supply", "lean": "up"}]
    store.update_alert_assessment(
        conn, alert_id, severity="High", polarity="escalation", country="RU", us_link="global_supply",
        capped_no_us_link=False, original_severity="High", affected_symbols=new_symbols,
    )
    row = store.get_alert(conn, alert_id)
    assert row.severity == "High"
    assert row.polarity == "escalation"
    assert row.country == "RU"
    assert row.us_link == "global_supply"
    assert row.capped_no_us_link is False
    assert row.original_severity == "High"
    assert row.affected_symbols == new_symbols
    # detection-time facts are untouched
    assert row.first_published_utc == dt.datetime(2026, 10, 21, 9, 58, tzinfo=UTC)
    assert len(row.sources) == 1


def test_outage_notice_is_one_row_per_utc_day():
    conn = store.get_connection(":memory:")
    day = dt.date(2026, 10, 21)
    assert store.outage_notice_sent(conn, day) is False
    store.record_outage_notice(conn, day, dt.datetime(2026, 10, 21, 6, 0, tzinfo=UTC), "ollama: timeout")
    assert store.outage_notice_sent(conn, day) is True
    assert store.outage_notice_sent(conn, dt.date(2026, 10, 22)) is False

    store.record_outage_notice(conn, day, dt.datetime(2026, 10, 21, 7, 0, tzinfo=UTC), "second")  # ignored
    rows = conn.execute("SELECT * FROM classifier_outage_notices").fetchall()
    assert len(rows) == 1
    assert rows[0]["utc_date"] == "2026-10-21"
    assert rows[0]["sent_at_utc"] == "2026-10-21T06:00:00+00:00"
    assert rows[0]["detail"] == "ollama: timeout"


def test_guard_blanks_telegram_and_points_ollama_nowhere():
    import os

    from alerting import llm_classify, notify_telegram

    assert notify_telegram.TELEGRAM_BOT_TOKEN == ""
    assert notify_telegram.TELEGRAM_CHAT_ID == ""
    assert llm_classify.OLLAMA_BASE_URL == "http://127.0.0.1:9"
    assert llm_classify.OLLAMA_EXECUTABLE.endswith("no-ollama.exe")
    assert not os.path.exists(llm_classify.OLLAMA_EXECUTABLE)
    assert "ANTHROPIC_API_KEY" not in os.environ
