"""
Tests for scripts/refresh_macro_calendar.py — no live network; FRED calls
and webapp.store's DB path are mocked/patched.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.refresh_macro_calendar as refresh_macro_calendar
import webapp.store as store
import data_layer.fred_calendar_feed as fred_calendar_feed
from data_layer.fred_calendar_feed import FredReleaseDate


@pytest.fixture(autouse=True)
def _tmp_failure_marker(tmp_path, monkeypatch):
    """Never let run() touch the real data_layer/ failure marker; also reset the module flag."""
    path = tmp_path / ".last_macro_calendar_refresh_failure"
    monkeypatch.setattr(refresh_macro_calendar, "_LAST_MACRO_FAILURE_FILE", path)
    monkeypatch.setattr(fred_calendar_feed, "last_failure_reason", None)
    return path


def test_is_due_true_when_never_run_before():
    print("=== refresh_macro_calendar: is_due() is True the first time (no cooldown file yet) ===")
    with tempfile.TemporaryDirectory() as tmp:
        fake_path = Path(tmp) / ".last_macro_calendar_refresh_at"
        with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", fake_path):
            assert refresh_macro_calendar.is_due() is True
    print("PASS\n")


def test_is_due_false_before_the_29_day_interval_elapses():
    print("=== refresh_macro_calendar: is_due() is False if the last run was less than 29 days ago ===")
    with tempfile.TemporaryDirectory() as tmp:
        fake_path = Path(tmp) / ".last_macro_calendar_refresh_at"
        with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", fake_path):
            ten_days_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=10)
            refresh_macro_calendar._record_refresh(ten_days_ago)
            assert refresh_macro_calendar.is_due() is False
    print("PASS\n")


def test_is_due_true_once_29_days_have_elapsed_since_last_run():
    print("=== refresh_macro_calendar: is_due() is True once 29 days have elapsed since the LAST run, not a fixed calendar day ===")
    with tempfile.TemporaryDirectory() as tmp:
        fake_path = Path(tmp) / ".last_macro_calendar_refresh_at"
        with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", fake_path):
            thirty_days_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
            refresh_macro_calendar._record_refresh(thirty_days_ago)
            assert refresh_macro_calendar.is_due() is True
    print("PASS\n")


def test_is_due_true_when_forced_regardless_of_cooldown():
    print("=== refresh_macro_calendar: is_due(force=True) is True even immediately after a real run ===")
    with tempfile.TemporaryDirectory() as tmp:
        fake_path = Path(tmp) / ".last_macro_calendar_refresh_at"
        with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", fake_path):
            refresh_macro_calendar._record_refresh(dt.datetime.now(dt.timezone.utc))
            assert refresh_macro_calendar.is_due(force=True) is True
    print("PASS\n")


def test_run_skips_and_returns_negative_one_when_not_due():
    print("=== refresh_macro_calendar: run() skips (returns -1) and writes nothing when not due ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        fake_cooldown = Path(tmp) / ".last_macro_calendar_refresh_at"
        with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", fake_cooldown), \
             patch.object(store, "DB_PATH", db_path), \
             patch.object(refresh_macro_calendar, "FRED_API_KEY", "test-key"), \
             patch.object(refresh_macro_calendar, "get_upcoming_release_dates") as mock_fetch:
            refresh_macro_calendar._record_refresh(dt.datetime.now(dt.timezone.utc))
            result = refresh_macro_calendar.run()
            assert result == -1
            mock_fetch.assert_not_called()
    print("PASS\n")


def test_run_returns_negative_one_without_api_key():
    print("=== refresh_macro_calendar: run(force=True) returns -1 (not a crash) when FRED_API_KEY is unset ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        fake_cooldown = Path(tmp) / ".last_macro_calendar_refresh_at"
        with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", fake_cooldown), \
             patch.object(store, "DB_PATH", db_path), \
             patch.object(refresh_macro_calendar, "FRED_API_KEY", ""):
            result = refresh_macro_calendar.run(force=True)
            assert result == -1
    print("PASS\n")


def test_run_writes_macro_calendar_rows_with_history_derived_time():
    print("=== refresh_macro_calendar: run() writes a history-derived estimated_time_utc when resolved history exists ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        fake_cooldown = Path(tmp) / ".last_macro_calendar_refresh_at"
        with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", fake_cooldown), \
             patch.object(store, "DB_PATH", db_path), \
             patch.object(refresh_macro_calendar, "FRED_API_KEY", "test-key"), \
             patch.object(
                 refresh_macro_calendar, "FRED_RELEASE_ID_BY_EVENT_TITLE", {"CPI m/m": 10},
             ), \
             patch.object(
                 refresh_macro_calendar, "get_upcoming_release_dates",
                 return_value=[FredReleaseDate(release_id=10, release_date=dt.date(2026, 9, 11))],
             ):
            conn = store.get_connection(db_path)
            from data_layer.calendar_feed import EconomicEvent
            from config.settings import UTC_TZ
            resolved = EconomicEvent(title="CPI m/m", country="USD", impact="High",
                                      event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ), forecast="0.2%", actual="0.3%")
            store.upsert_event_history(conn, resolved, "higher", dt.datetime.now(dt.timezone.utc))
            conn.close()

            result = refresh_macro_calendar.run(force=True)
            assert result == 1

            conn = store.get_connection(db_path)
            rows = store.get_macro_calendar_events(conn, "2026-09-01", "2026-09-30")
            assert len(rows) == 1
            assert rows[0].event_date == "2026-09-11"
            assert rows[0].estimated_time_utc == "2026-09-11T12:30:00+00:00"  # 12:30 inferred from the resolved history row
            assert rows[0].time_source == "history_derived"
            conn.close()
    print("PASS\n")


def test_run_writes_unconfirmed_time_source_without_any_history():
    print("=== refresh_macro_calendar: run() writes time_source='unconfirmed' and no estimated_time_utc when no history exists yet ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        fake_cooldown = Path(tmp) / ".last_macro_calendar_refresh_at"
        with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", fake_cooldown), \
             patch.object(store, "DB_PATH", db_path), \
             patch.object(refresh_macro_calendar, "FRED_API_KEY", "test-key"), \
             patch.object(
                 refresh_macro_calendar, "FRED_RELEASE_ID_BY_EVENT_TITLE", {"CPI m/m": 10},
             ), \
             patch.object(
                 refresh_macro_calendar, "get_upcoming_release_dates",
                 return_value=[FredReleaseDate(release_id=10, release_date=dt.date(2026, 9, 11))],
             ):
            result = refresh_macro_calendar.run(force=True)
            assert result == 1

            conn = store.get_connection(db_path)
            rows = store.get_macro_calendar_events(conn, "2026-09-01", "2026-09-30")
            assert rows[0].estimated_time_utc is None
            assert rows[0].time_source == "unconfirmed"
            conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_is_due_true_when_never_run_before()
    test_is_due_false_before_the_29_day_interval_elapses()
    test_is_due_true_once_29_days_have_elapsed_since_last_run()
    test_is_due_true_when_forced_regardless_of_cooldown()
    test_run_skips_and_returns_negative_one_when_not_due()
    test_run_returns_negative_one_without_api_key()
    test_run_writes_macro_calendar_rows_with_history_derived_time()
    test_run_writes_unconfirmed_time_source_without_any_history()
    print("All refresh_macro_calendar tests passed.")


def test_run_does_not_mark_refreshed_when_fred_returns_nothing(capsys):
    print("=== refresh_macro_calendar: a run that writes zero rows does NOT mark itself done (retries) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        fake_cooldown = Path(tmp) / ".last_macro_calendar_refresh_at"
        with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", fake_cooldown), \
             patch.object(store, "DB_PATH", db_path), \
             patch.object(refresh_macro_calendar, "FRED_API_KEY", "test-key"), \
             patch.object(refresh_macro_calendar, "FRED_RELEASE_ID_BY_EVENT_TITLE", {"CPI m/m": 10}), \
             patch.object(refresh_macro_calendar, "get_upcoming_release_dates", return_value=[]):
            assert refresh_macro_calendar.run(force=True) == 0
            assert not fake_cooldown.exists()
            assert refresh_macro_calendar.is_due() is True
    assert "not marking the refresh done" in capsys.readouterr().out
    print("PASS\n")


def _run_with(tmp_path, fetch_effect):
    """run(force=True) against a tmp DB/cooldown with one mapped title; returns (result, cooldown path)."""
    cooldown = tmp_path / ".last_macro_calendar_refresh_at"
    with patch.object(refresh_macro_calendar, "_LAST_MACRO_REFRESH_FILE", cooldown), \
         patch.object(store, "DB_PATH", tmp_path / "dashboard.db"), \
         patch.object(refresh_macro_calendar, "FRED_API_KEY", "test-key"), \
         patch.object(refresh_macro_calendar, "FRED_RELEASE_ID_BY_EVENT_TITLE", {"CPI m/m": 10}), \
         patch.object(refresh_macro_calendar, "get_upcoming_release_dates", **fetch_effect):
        return refresh_macro_calendar.run(force=True), cooldown


def test_run_records_fred_maintenance_failure(tmp_path, _tmp_failure_marker, capsys):
    def maintenance(*args, **kwargs):
        fred_calendar_feed.last_failure_reason = fred_calendar_feed.FRED_MAINTENANCE
        return []

    result, cooldown = _run_with(tmp_path, {"side_effect": maintenance})
    assert result == 0
    assert _tmp_failure_marker.exists()
    assert dt.datetime.fromisoformat(_tmp_failure_marker.read_text().strip()).tzinfo is not None
    assert not cooldown.exists()
    assert "FRED under maintenance" in capsys.readouterr().out


def test_run_zero_rows_without_maintenance_clears_failure_marker(tmp_path, _tmp_failure_marker):
    _tmp_failure_marker.write_text("2026-10-01T00:00:00+00:00")
    result, _ = _run_with(tmp_path, {"return_value": []})
    assert result == 0
    assert not _tmp_failure_marker.exists()


def test_run_success_clears_failure_marker(tmp_path, _tmp_failure_marker):
    _tmp_failure_marker.write_text("2026-10-01T00:00:00+00:00")
    result, _ = _run_with(
        tmp_path, {"return_value": [FredReleaseDate(release_id=10, release_date=dt.date(2026, 9, 11))]})
    assert result == 1
    assert not _tmp_failure_marker.exists()
