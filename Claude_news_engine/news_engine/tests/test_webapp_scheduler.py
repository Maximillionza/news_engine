"""
Tests for webapp.scheduler — no live network, fetch_calendar is patched.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
import webapp.store as store
import webapp.scheduler as scheduler


def _fake_events():
    return [
        EconomicEvent(
            title="Non-Farm Employment Change", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            forecast="75K", actual="44K",
        )
    ]


def _fake_pending_event():
    return [
        EconomicEvent(
            title="Non-Farm Employment Change", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            forecast="75K", actual=None,
        )
    ]


def test_scoring_cycle_writes_new_rows_and_skips_duplicates():
    print("=== scheduler: writes a row on first cycle, skips an identical second cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            conn = store.get_connection(db_path)
            runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
            assert len(runs) == 1, "first cycle should write exactly one row"

            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
            assert len(runs) == 1, "second identical cycle should NOT write a duplicate row"
            conn.close()
    print("PASS\n")


def test_unrecognized_symbol_skipped_not_crashed():
    print("=== scheduler: an unrecognized tracked symbol is skipped, not a crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):
            scheduler.run_scoring_cycle(["NOTREAL123"], db_path=db_path)  # must not raise
    print("PASS\n")


def test_failed_calendar_fetch_does_not_crash_or_wipe_data():
    print("=== scheduler: a failed calendar fetch does not crash the loop or wipe existing data ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"

        # pre-populate the DB with one existing row so there's something to wipe
        conn = store.get_connection(db_path)
        store.record_run(
            conn, "XAUUSD", "Non-Farm Employment Change",
            dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            0.62, "up", 1.5,
        )
        conn.close()

        with patch.object(scheduler, "fetch_calendar", side_effect=Exception("network down")):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)  # must not raise

        conn = store.get_connection(db_path)
        runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
        assert len(runs) == 1, "existing row must survive a failed calendar fetch"
        conn.close()
    print("PASS\n")


def test_pending_then_released_event_produces_two_row_lifecycle():
    print("=== scheduler: pending cycle then released cycle for the SAME event yields 2 rows (pending + real) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"

        # Cycle 1: event hasn't printed an actual yet — must still be persisted as pending.
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_pending_event()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        # Cycle 2: same event, now released with a real actual value.
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        conn = store.get_connection(db_path)
        runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
        conn.close()

        assert len(runs) == 2, f"expected 2 rows (pending + real), got {len(runs)}"
        newer, older = runs[0], runs[1]
        assert older.direction == "pending", f"older row should be pending, got {older.direction!r}"
        assert older.probability is None, f"older row's probability should be None, got {older.probability!r}"
        assert newer.direction != "pending", f"newer row should have a real direction, got {newer.direction!r}"
        assert newer.probability is not None, "newer row should have a real probability"
        print(f"  older: direction={older.direction} probability={older.probability}")
        print(f"  newer: direction={newer.direction} probability={newer.probability}")
    print("PASS\n")


if __name__ == "__main__":
    test_scoring_cycle_writes_new_rows_and_skips_duplicates()
    test_unrecognized_symbol_skipped_not_crashed()
    test_failed_calendar_fetch_does_not_crash_or_wipe_data()
    test_pending_then_released_event_produces_two_row_lifecycle()
    print("All scheduler tests passed.")
