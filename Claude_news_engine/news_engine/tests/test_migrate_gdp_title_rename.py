"""
Tests for scripts/migrate_gdp_title_rename.py — a one-off data migration
re-pointing historical rows stored under the old, wrong event_title
'Advance GDP q/q' to the corrected 'Prelim GDP q/q'. No network needed.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
import webapp.store as store
import scoring.backtest_store as backtest_store
import scripts.migrate_gdp_title_rename as migrate
from data_layer.calendar_feed import EconomicEvent


OLD_TITLE = migrate.OLD_TITLE
NEW_TITLE = migrate.NEW_TITLE


def test_migration_renames_rows_in_dashboard_db():
    print("=== migrate_gdp_title_rename: dashboard DB rows (event_history, macro_calendar) are renamed to the new title ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 26, 12, 0, tzinfo=UTC_TZ)

        event = EconomicEvent(
            title=OLD_TITLE, country="USD", impact="High", event_time_utc=now,
            forecast="2.1%", previous="2.0%", actual="2.3%",
        )
        store.upsert_event_history(conn, event, "higher_bullish", now)
        store.upsert_macro_calendar_event(conn, OLD_TITLE, "2026-08-26", None, "unconfirmed", now)

        migrate.run(conn, migrate.DASHBOARD_TABLES)

        assert store.get_event_history(conn, NEW_TITLE)
        assert store.get_event_history(conn, OLD_TITLE) == []
        macro_rows = store.get_macro_calendar_events(conn, "2026-01-01", "2026-12-31")
        assert any(r.event_title == NEW_TITLE for r in macro_rows)
        assert not any(r.event_title == OLD_TITLE for r in macro_rows)
        conn.close()
    print("PASS\n")


def test_migration_renames_rows_in_backtest_db():
    print("=== migrate_gdp_title_rename: backtest DB rows (predictions, print_predictions, kalshi_reads) are renamed to the new title ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "backtest.db"
        conn = backtest_store.get_connection(db_path)
        now = dt.datetime(2026, 8, 26, 12, 0, tzinfo=UTC_TZ)

        backtest_store.record_prediction(
            conn, OLD_TITLE, "XAUUSD", now, 0.6, "bullish", 0.5, 40, False, scored_at_utc=now,
        )

        migrate.run(conn, migrate.BACKTEST_TABLES)

        rows = conn.execute("SELECT event_title FROM predictions").fetchall()
        assert all(r["event_title"] == NEW_TITLE for r in rows)
        conn.close()
    print("PASS\n")


def test_migration_handles_unique_constraint_collision_without_aborting():
    print("=== migrate_gdp_title_rename: a row that would collide under the new title (UNIQUE constraint) is skipped with a warning, not silently dropped or crashing ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "backtest.db"
        conn = backtest_store.get_connection(db_path)
        now = dt.datetime(2026, 8, 26, 12, 0, tzinfo=UTC_TZ)
        other_time = dt.datetime(2026, 5, 26, 12, 0, tzinfo=UTC_TZ)

        # A row already exists under NEW_TITLE for (instrument, event_time_utc).
        backtest_store.record_outcome(conn, NEW_TITLE, "XAUUSD", now, "bullish", "colliding row")
        # An old-title row for the SAME (instrument, event_time_utc) -- migrating
        # this one would violate outcomes' UNIQUE(event_title, instrument, event_time_utc).
        backtest_store.record_outcome(conn, OLD_TITLE, "XAUUSD", now, "bearish", "should be skipped")
        # An old-title row for a DIFFERENT event_time_utc -- no collision, must still migrate.
        backtest_store.record_outcome(conn, OLD_TITLE, "XAUUSD", other_time, "bullish", "should migrate fine")

        migrate.run(conn, migrate.BACKTEST_TABLES)

        rows = conn.execute("SELECT event_title, event_time_utc, actual_move_note FROM outcomes").fetchall()
        by_note = {r["actual_move_note"]: r["event_title"] for r in rows}
        assert by_note["colliding row"] == NEW_TITLE
        assert by_note["should be skipped"] == OLD_TITLE  # left untouched, not dropped
        assert by_note["should migrate fine"] == NEW_TITLE
        conn.close()
    print("PASS\n")


def test_migration_is_a_safe_no_op_when_run_a_second_time():
    print("=== migrate_gdp_title_rename: running the migration twice migrates 0 rows the second time ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 26, 12, 0, tzinfo=UTC_TZ)
        event = EconomicEvent(
            title=OLD_TITLE, country="USD", impact="High", event_time_utc=now,
            forecast="2.1%", previous="2.0%", actual="2.3%",
        )
        store.upsert_event_history(conn, event, "higher_bullish", now)

        first_migrated, _ = migrate._migrate_table(conn, "event_history", None)
        second_migrated, _ = migrate._migrate_table(conn, "event_history", None)

        assert first_migrated == 1
        assert second_migrated == 0
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_migration_renames_rows_in_dashboard_db()
    test_migration_renames_rows_in_backtest_db()
    test_migration_handles_unique_constraint_collision_without_aborting()
    test_migration_is_a_safe_no_op_when_run_a_second_time()
    print("All migrate_gdp_title_rename tests passed.")
