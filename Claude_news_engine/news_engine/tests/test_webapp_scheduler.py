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


def test_scoring_cycle_writes_new_rows_and_skips_duplicates():
    print("=== scheduler: writes a row on first cycle, skips an identical second cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events: events):

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
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events: events):
            scheduler.run_scoring_cycle(["NOTREAL123"], db_path=db_path)  # must not raise
    print("PASS\n")


if __name__ == "__main__":
    test_scoring_cycle_writes_new_rows_and_skips_duplicates()
    test_unrecognized_symbol_skipped_not_crashed()
    print("All scheduler tests passed.")
