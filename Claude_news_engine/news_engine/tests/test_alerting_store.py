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
_B7_COLUMN_COUNT = 3  # incident_id, incident_role, incident_rule (B7 2026-10-22)


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
    assert len(names) == len(_PRE_B2_COLUMNS) + len(_B2_COLUMNS) + _B7_COLUMN_COUNT

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
        self.alters: list[str] = []

    def execute(self, sql, *args):
        if sql.startswith("PRAGMA table_info"):
            return _FakeCursor([{"name": name} for name in _PRE_B2_COLUMNS])
        if sql.startswith("ALTER TABLE"):
            self.alters.append(sql)
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
    # B7: the three incident columns are migrated through the same swallow-duplicate path
    assert any("incident_id" in s for s in racing.alters)
    assert any("incident_role" in s for s in racing.alters)
    assert any("incident_rule" in s for s in racing.alters)

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


def test_source_failure_streak_and_reset():
    conn = store.get_connection(":memory:")
    t0 = dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC)
    assert store.get_source_health(conn, "feed_a") is None

    first = store.record_source_failure(conn, "feed_a", t0, "boom", None)
    second = store.record_source_failure(conn, "feed_a", t0 + dt.timedelta(minutes=2), "boom2", None)
    assert first.consecutive_failures == 1
    assert second.consecutive_failures == 2
    assert second.failing_since_utc == t0  # first failure of the streak is kept
    assert second.last_failure_utc == t0 + dt.timedelta(minutes=2)
    assert second.last_error == "boom2"

    prev = store.record_source_success(conn, "feed_a", t0 + dt.timedelta(minutes=4))
    assert prev is not None and prev.consecutive_failures == 2
    after = store.get_source_health(conn, "feed_a")
    assert after.consecutive_failures == 0
    assert after.failing_since_utc is None and after.backoff_until_utc is None
    assert after.last_success_utc == t0 + dt.timedelta(minutes=4)

    # A success on an already-clean row (or a brand-new feed) reports nothing to recover from.
    assert store.record_source_success(conn, "feed_a", t0 + dt.timedelta(minutes=6)) is None
    assert store.record_source_success(conn, "feed_new", t0) is None
    assert [h.source for h in store.list_source_health(conn)] == ["feed_a", "feed_new"]


def test_near_miss_repeat_within_24h_is_skipped():
    conn = store.get_connection(":memory:")
    t0 = dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC)
    assert isinstance(store.record_near_miss(conn, "Oil edges up", "energy", 0.5, t0), int)
    assert store.record_near_miss(conn, "Oil edges up", "energy", 0.5, t0 + dt.timedelta(hours=23)) is None
    assert isinstance(store.record_near_miss(conn, "Oil edges up", "energy", 0.5, t0 + dt.timedelta(hours=25)), int)
    assert isinstance(store.record_near_miss(conn, "Other headline", "energy", 0.5, t0 + dt.timedelta(minutes=1)), int)
    assert conn.execute("SELECT COUNT(*) FROM shock_near_misses").fetchone()[0] == 3


def test_prune_near_misses_keeps_30_days_and_is_bounded():
    conn = store.get_connection(":memory:")
    now = dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC)
    for i in range(3):
        store.record_near_miss(conn, f"old {i}", "energy", 0.5, now - dt.timedelta(days=31))
    store.record_near_miss(conn, "recent", "energy", 0.5, now - dt.timedelta(days=29))

    assert store.prune_near_misses(conn, now, max_rows=2) == 2
    assert store.prune_near_misses(conn, now, max_rows=2) == 1
    assert store.prune_near_misses(conn, now, max_rows=2) == 0
    left = [r["headline"] for r in conn.execute("SELECT headline FROM shock_near_misses")]
    assert left == ["recent"]


# --- B7 K9/K10 storage: incident columns and 72 h URL memory ----------------

_B7_COLUMNS = ("incident_id", "incident_role", "incident_rule")


def _make_old_db(path, rows=()):
    """File DB in the B2 shape (no incident columns, no seen_urls) holding `rows` of (headline, sources, detected)."""
    import json
    import sqlite3

    raw = sqlite3.connect(path)
    raw.executescript(_PRE_B2_SHOCK_ALERTS)
    for column, sql_type in store._SHOCK_ALERT_ADDED_COLUMNS:
        if column in _B2_COLUMNS:
            raw.execute(f"ALTER TABLE shock_alerts ADD COLUMN {column} {sql_type}")
    for headline, sources, detected in rows:
        raw.execute(
            "INSERT INTO shock_alerts (headline, sources_json, detected_at_utc, category, severity, "
            "classification_method, rationale, affected_symbols_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (headline, json.dumps(sources), detected.isoformat(), "energy", "High", "rule_tier", None, "[]"),
        )
    raw.commit()
    raw.close()


def test_b7_migration_is_idempotent_on_an_old_db(tmp_path):
    db_path = tmp_path / "b2_shock_alerts.db"
    _make_old_db(db_path, [("Old row", [{"source": "s", "url": "u", "published_utc": "2026-10-06T10:07:00+00:00"}],
                            dt.datetime(2026, 10, 6, 10, 9, tzinfo=UTC))])

    store._schema_ready_paths.clear()
    store.get_connection(db_path).close()
    store._schema_ready_paths.clear()
    conn = store.get_connection(db_path)
    store._migrate_shock_alert_columns(conn)

    names = [r["name"] for r in conn.execute("PRAGMA table_info(shock_alerts)").fetchall()]
    for column in _B7_COLUMNS:
        assert names.count(column) == 1
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    assert "seen_urls" in tables
    conn.close()
    store._schema_ready_paths.clear()


def test_null_incident_id_reads_as_own_incident():
    conn = store.get_connection(":memory:")
    cur = conn.execute(
        "INSERT INTO shock_alerts (headline, sources_json, detected_at_utc, category, severity, "
        "classification_method, rationale, affected_symbols_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("Legacy", "[]", "2026-10-01T10:00:00+00:00", "energy", "High", "rule_tier", None, "[]"),
    )
    conn.commit()
    alert_id = cur.lastrowid
    row = store.get_alert(conn, alert_id)
    assert row.incident_id == alert_id
    assert row.incident_role is None
    assert row.incident_rule is None
    assert [r.id for r in store.list_incident_alerts(conn, alert_id)] == [alert_id]


def test_record_alert_defaults_incident_to_own_id():
    conn = store.get_connection(":memory:")
    first = _record(conn)
    assert store.get_alert(conn, first).incident_id == first
    assert store.get_alert(conn, first).incident_role is None

    t0 = dt.datetime(2026, 10, 19, 6, 0, tzinfo=UTC)
    follow = _record(conn, incident_id=first, incident_role="follow_up", incident_rule="url", first_published_utc=t0)
    row = store.get_alert(conn, follow)
    assert row.incident_id == first
    assert row.incident_role == "follow_up"
    assert row.incident_rule == "url"
    assert row.first_published_utc == t0
    assert row.sources[0]["published_utc"] == "2026-10-21T09:58:00+00:00"
    assert store.INCIDENT_ROLES == ("follow_up", "update")


def test_list_incident_alerts_orders_by_detection():
    conn = store.get_connection(":memory:")

    def rec(detected, **extra):
        return store.record_alert(
            conn, headline="H", source="s", url="u", published_utc=detected, detected_at_utc=detected,
            category="energy", severity="High", classification_method="llm", rationale=None,
            affected_symbols=[], **extra,
        )

    root = rec(dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC))
    late = rec(dt.datetime(2026, 10, 21, 12, 0, tzinfo=UTC), incident_id=root, incident_role="update")
    early = rec(dt.datetime(2026, 10, 21, 10, 0, tzinfo=UTC), incident_id=root, incident_role="follow_up")
    other = rec(dt.datetime(2026, 10, 21, 9, 0, tzinfo=UTC))
    assert [r.id for r in store.list_incident_alerts(conn, root)] == [root, early, late]
    assert other not in [r.id for r in store.list_incident_alerts(conn, root)]


def test_remember_url_keeps_first_sighting():
    conn = store.get_connection(":memory:")
    t1 = dt.datetime(2026, 10, 21, 10, 0, tzinfo=UTC)
    t2 = t1 + dt.timedelta(hours=1)
    p1 = dt.datetime(2026, 10, 21, 9, 30, tzinfo=UTC)
    store.remember_url(conn, "https://X.com/a/?utm_source=t#frag", 5, t1, p1)
    store.remember_url(conn, "https://x.com/a", 5, t2, t2)
    rows = conn.execute("SELECT * FROM seen_urls").fetchall()
    assert len(rows) == 1
    assert rows[0]["url"] == "https://x.com/a"
    assert rows[0]["first_seen_utc"] == t1.isoformat()
    assert rows[0]["first_published_utc"] == p1.isoformat()

    store.remember_url(conn, "https://x.com/a", 6, t2, None)
    assert conn.execute("SELECT COUNT(*) FROM seen_urls").fetchone()[0] == 2
    store.remember_url(conn, "   ", 7, t2, None)
    assert conn.execute("SELECT COUNT(*) FROM seen_urls").fetchone()[0] == 2


def test_lookup_seen_url_respects_window():
    conn = store.get_connection(":memory:")
    now = dt.datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    store.remember_url(conn, "https://x.com/a", 1, now - dt.timedelta(hours=73), None)
    store.remember_url(conn, "https://x.com/a", 2, now - dt.timedelta(hours=71), now - dt.timedelta(hours=72))
    since = now - store.SEEN_URL_RETENTION
    hits = store.lookup_seen_url(conn, "https://x.com/a/", since)
    assert [h.alert_id for h in hits] == [2]
    assert hits[0].first_seen_utc == now - dt.timedelta(hours=71)
    assert hits[0].first_published_utc == now - dt.timedelta(hours=72)
    assert store.lookup_seen_url(conn, "https://x.com/other", since) == []

    store.remember_url(conn, "https://x.com/a", 3, now - dt.timedelta(hours=10), None)
    hits = store.lookup_seen_url(conn, "https://x.com/a", since)
    assert [h.alert_id for h in hits] == [3, 2]
    assert hits[0].first_published_utc is None


def test_prune_seen_urls_is_bounded():
    conn = store.get_connection(":memory:")
    now = dt.datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    old = now - dt.timedelta(hours=80)
    conn.executemany(
        "INSERT INTO seen_urls (url, alert_id, first_seen_utc, first_published_utc) VALUES (?, ?, ?, NULL)",
        [(f"https://x.com/{i}", i, old.isoformat()) for i in range(600)],
    )
    for i in range(3):
        store.remember_url(conn, f"https://x.com/new{i}", 1000 + i, now - dt.timedelta(hours=1), None)
    assert store.prune_seen_urls(conn, now) == 500
    assert store.prune_seen_urls(conn, now) == 100
    assert store.prune_seen_urls(conn, now) == 0
    assert conn.execute("SELECT COUNT(*) FROM seen_urls").fetchone()[0] == 3


def test_seen_urls_backfill_runs_once_from_last_72h(tmp_path):
    now = dt.datetime.now(UTC)
    detected_a = now - dt.timedelta(hours=10)
    published_b = detected_a + dt.timedelta(hours=2)
    db_path = tmp_path / "old.db"
    _make_old_db(db_path, [
        ("A", [{"source": "s1", "url": "https://x.com/a/?utm_x=1", "published_utc": (detected_a - dt.timedelta(minutes=5)).isoformat()},
               {"source": "s2", "url": "https://y.com/b", "published_utc": published_b.isoformat()}], detected_a),
        ("B", [{"source": "s1", "url": "https://x.com/old", "published_utc": (now - dt.timedelta(hours=101)).isoformat()}],
         now - dt.timedelta(hours=100)),
    ])

    store._schema_ready_paths.clear()
    conn = store.get_connection(db_path)
    rows = {r["url"]: r for r in conn.execute("SELECT * FROM seen_urls").fetchall()}
    assert set(rows) == {"https://x.com/a", "https://y.com/b"}
    assert rows["https://x.com/a"]["first_seen_utc"] == detected_a.isoformat()
    assert rows["https://x.com/a"]["first_published_utc"] == (detected_a - dt.timedelta(minutes=5)).isoformat()
    assert rows["https://y.com/b"]["first_seen_utc"] == published_b.isoformat()
    assert rows["https://y.com/b"]["first_published_utc"] == published_b.isoformat()

    conn.execute("DELETE FROM seen_urls WHERE url = ?", ("https://y.com/b",))
    conn.commit()
    conn.close()
    store._schema_ready_paths.clear()
    conn = store.get_connection(db_path)
    assert conn.execute("SELECT COUNT(*) FROM seen_urls WHERE url = ?", ("https://y.com/b",)).fetchone()[0] == 0
    conn.close()
    store._schema_ready_paths.clear()
