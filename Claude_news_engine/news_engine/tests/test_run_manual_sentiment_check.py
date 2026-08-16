"""
Tests for scripts/run_manual_sentiment_check.py — no live network;
fetch_calendar, build_all_preview_sources, and score_and_record_event
are all mocked.
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
import scripts.run_manual_sentiment_check as manual_check
import webapp.store as dash_store
import scoring.backtest_store as backtest_store


def _seed_calendar(db_path, events):
    conn = dash_store.get_connection(db_path)
    dash_store.save_calendar_snapshot_if_changed(conn, events, dt.datetime.now(dt.timezone.utc))
    conn.close()


def test_find_target_event_matches_from_persisted_snapshot_no_live_fetch():
    print("=== run_manual_sentiment_check: _find_target_event matches from the persisted snapshot, no live fetch needed ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        with patch.object(dash_store, "DB_PATH", db_path):
            event = EconomicEvent(
                title="FOMC Meeting Minutes", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 8, 19, 18, 0, tzinfo=UTC_TZ),
            )
            _seed_calendar(db_path, [event])
            now = dt.datetime(2026, 8, 16, 12, 0, tzinfo=dt.timezone.utc)
            with patch.object(manual_check, "fetch_calendar") as mock_fetch:
                result = manual_check._find_target_event("FOMC Meeting Minutes", now)
                mock_fetch.assert_not_called()
            assert result is not None
            assert result.title == "FOMC Meeting Minutes"
            assert result.event_time_utc == event.event_time_utc
    print("PASS\n")


def test_find_target_event_falls_back_to_one_live_fetch_when_not_in_snapshot():
    print("=== run_manual_sentiment_check: _find_target_event falls back to ONE live fetch when the title isn't in the snapshot ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        with patch.object(dash_store, "DB_PATH", db_path):
            _seed_calendar(db_path, [])
            now = dt.datetime(2026, 8, 16, 12, 0, tzinfo=dt.timezone.utc)
            live_event = EconomicEvent(
                title="Federal Funds Rate", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 9, 16, 18, 0, tzinfo=dt.timezone.utc),
            )
            with patch.object(manual_check, "fetch_calendar", return_value=[live_event]) as mock_fetch:
                result = manual_check._find_target_event("Federal Funds Rate", now)
                mock_fetch.assert_called_once()
            assert result is not None
            assert result.title == "Federal Funds Rate"
    print("PASS\n")


def test_find_target_event_returns_none_when_nowhere_to_be_found():
    print("=== run_manual_sentiment_check: _find_target_event returns None (not a crash) when the title exists nowhere ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        with patch.object(dash_store, "DB_PATH", db_path):
            _seed_calendar(db_path, [])
            now = dt.datetime(2026, 8, 16, 12, 0, tzinfo=dt.timezone.utc)
            with patch.object(manual_check, "fetch_calendar", return_value=[]):
                result = manual_check._find_target_event("Nonexistent Event", now)
            assert result is None
    print("PASS\n")


def test_find_target_event_picks_nearest_future_occurrence_among_duplicates():
    print("=== run_manual_sentiment_check: _find_target_event picks the NEAREST future occurrence when a title recurs ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        with patch.object(dash_store, "DB_PATH", db_path):
            now = dt.datetime(2026, 8, 16, 12, 0, tzinfo=dt.timezone.utc)
            near = EconomicEvent(title="Unemployment Claims", country="USD", impact="Medium",
                                  event_time_utc=dt.datetime(2026, 8, 20, 12, 30, tzinfo=dt.timezone.utc))
            far = EconomicEvent(title="Unemployment Claims", country="USD", impact="Medium",
                                 event_time_utc=dt.datetime(2026, 8, 27, 12, 30, tzinfo=dt.timezone.utc))
            _seed_calendar(db_path, [far, near])  # deliberately far-first, ordering must not matter
            result = manual_check._find_target_event("Unemployment Claims", now)
            assert result.event_time_utc == near.event_time_utc
    print("PASS\n")


def test_run_calls_score_and_record_event_with_every_tracked_instrument():
    print("=== run_manual_sentiment_check: run() calls score_and_record_event with the target event and every INSTRUMENTS key ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(dash_store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            event = EconomicEvent(
                title="FOMC Meeting Minutes", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, 8, 19, 18, 0, tzinfo=UTC_TZ),
            )
            _seed_calendar(db_path, [event])
            now = dt.datetime(2026, 8, 16, 12, 0, tzinfo=dt.timezone.utc)

            captured = {}
            def _fake_score_and_record(conn, ev, all_events, instruments, sources, now=None):
                captured["event"] = ev
                captured["instruments"] = list(instruments)
                return {}

            with patch.object(manual_check, "fetch_calendar", return_value=[event]), \
                 patch.object(manual_check, "build_all_preview_sources", return_value=[]), \
                 patch.object(manual_check, "score_and_record_event", side_effect=_fake_score_and_record):
                manual_check.run("FOMC Meeting Minutes", now=now)

            assert captured["event"].title == "FOMC Meeting Minutes"
            assert set(captured["instruments"]) == {"XAUUSD", "US30"}
    print("PASS\n")


def test_run_returns_empty_dict_when_target_event_not_found():
    print("=== run_manual_sentiment_check: run() returns {} (not a crash) when the target event can't be found anywhere ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        with patch.object(dash_store, "DB_PATH", db_path):
            _seed_calendar(db_path, [])
            now = dt.datetime(2026, 8, 16, 12, 0, tzinfo=dt.timezone.utc)
            with patch.object(manual_check, "fetch_calendar", return_value=[]):
                result = manual_check.run("Nonexistent Event", now=now)
            assert result == {}
    print("PASS\n")


if __name__ == "__main__":
    test_find_target_event_matches_from_persisted_snapshot_no_live_fetch()
    test_find_target_event_falls_back_to_one_live_fetch_when_not_in_snapshot()
    test_find_target_event_returns_none_when_nowhere_to_be_found()
    test_find_target_event_picks_nearest_future_occurrence_among_duplicates()
    test_run_calls_score_and_record_event_with_every_tracked_instrument()
    test_run_returns_empty_dict_when_target_event_not_found()
    print("All run_manual_sentiment_check tests passed.")
