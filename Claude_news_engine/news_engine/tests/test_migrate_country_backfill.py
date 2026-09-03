"""
Tests for scripts/migrate_country_backfill.py — a one-off data migration
backfilling event_history.country = 'USD' for rows whose source guarantees
they are genuine US releases by construction (seeded, live_web_fallback,
fred). No network needed.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
import webapp.store as store
import scripts.migrate_country_backfill as migrate


def _insert_row(conn, title, event_time, source, country=None):
    conn.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, "
        "surprise_direction, recorded_at_utc, updated_at_utc, source, country) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (title, event_time.isoformat(), "1.0", "0.9", "1.1", "higher", event_time.isoformat(), event_time.isoformat(), source, country),
    )
    conn.commit()


def test_backfills_country_for_guaranteed_usd_sources():
    print("=== migrate_country_backfill: seeded/live_web_fallback/fred rows with country still NULL are backfilled to 'USD' ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "dashboard.db")
        now = dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ)
        _insert_row(conn, "Seeded Event", now, "seeded")
        _insert_row(conn, "Web Fallback Event", now, "live_web_fallback")
        _insert_row(conn, "Fred Event", now, "fred")

        migrated = migrate.run(conn)

        assert migrated == 3
        rows = {r.event_title: r.country for r in [
            store.get_event_history(conn, "Seeded Event")[0],
            store.get_event_history(conn, "Web Fallback Event")[0],
            store.get_event_history(conn, "Fred Event")[0],
        ]}
        assert rows == {"Seeded Event": "USD", "Web Fallback Event": "USD", "Fred Event": "USD"}
        conn.close()
    print("PASS\n")


def test_does_not_touch_live_source_rows():
    print("=== migrate_country_backfill: 'live' rows are left untouched — country can't be safely reconstructed for them ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "dashboard.db")
        now = dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ)
        _insert_row(conn, "Live Event", now, "live")

        migrated = migrate.run(conn)

        assert migrated == 0
        assert store.get_event_history(conn, "Live Event")[0].country is None
        conn.close()
    print("PASS\n")


def test_does_not_overwrite_an_already_known_country():
    print("=== migrate_country_backfill: a row with a real (non-USD) country already set is never overwritten ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "dashboard.db")
        now = dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ)
        _insert_row(conn, "Already Known", now, "seeded", country="EUR")

        migrated = migrate.run(conn)

        assert migrated == 0
        assert store.get_event_history(conn, "Already Known")[0].country == "EUR"
        conn.close()
    print("PASS\n")


def test_is_a_safe_no_op_when_run_a_second_time():
    print("=== migrate_country_backfill: running the migration twice backfills 0 rows the second time ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = store.get_connection(Path(tmp) / "dashboard.db")
        now = dt.datetime(2026, 9, 3, 12, 0, tzinfo=UTC_TZ)
        _insert_row(conn, "Seeded Event", now, "seeded")

        first_migrated = migrate.run(conn)
        second_migrated = migrate.run(conn)

        assert first_migrated == 1
        assert second_migrated == 0
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_backfills_country_for_guaranteed_usd_sources()
    test_does_not_touch_live_source_rows()
    test_does_not_overwrite_an_already_known_country()
    test_is_a_safe_no_op_when_run_a_second_time()
    print("All migrate_country_backfill tests passed.")
