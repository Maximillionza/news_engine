"""
Tests for scripts/fill_missing_actuals.py — an agent-run enrichment pass,
not a live-service feature (WebSearch is only callable by an agent
session). `run()` takes agent-supplied, already-researched facts and
writes them; it never does any research itself.
"""
import sys
import os
import datetime as dt
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
import webapp.store as store
import scripts.fill_missing_actuals as fill


def _fake_event(title, event_time_utc):
    from data_layer.calendar_feed import EconomicEvent
    return EconomicEvent(title, "USD", "High", event_time_utc)


def test_run_writes_a_real_supplied_actual_with_web_fallback_source():
    print("=== fill_missing_actuals: run() writes an agent-supplied actual with source='live_web_fallback' ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 14, 12, 0, tzinfo=UTC_TZ)
        stale_event = _fake_event("PPI m/m", now - dt.timedelta(hours=48))
        store.upsert_event_history(conn, stale_event, None, now)

        facts = [("PPI m/m", now - dt.timedelta(hours=48), "0.3%", "BLS PPI report, bls.gov, released 2026-08-12")]
        report = fill.run(facts, conn, now=now)

        rows = store.get_event_history(conn, "PPI m/m")
        assert rows[0].actual == "0.3%"
        assert rows[0].source == "live_web_fallback"
        assert report.written == 1
        conn.close()
    print("PASS\n")


def test_run_skips_an_occurrence_that_already_has_a_real_actual():
    print("=== fill_missing_actuals: run() never overwrites an occurrence that already has a real actual ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 14, 12, 0, tzinfo=UTC_TZ)
        resolved_event = _fake_event("CPI m/m", now - dt.timedelta(hours=48))
        resolved_event.actual = "0.2%"
        store.upsert_event_history(conn, resolved_event, "higher_bullish", now, source="live")

        facts = [("CPI m/m", now - dt.timedelta(hours=48), "999%", "should never be written")]
        report = fill.run(facts, conn, now=now)

        rows = store.get_event_history(conn, "CPI m/m")
        assert rows[0].actual == "0.2%"  # unchanged
        assert rows[0].source == "live"  # unchanged, never relabeled
        assert report.skipped == 1
        conn.close()
    print("PASS\n")


def test_run_skips_an_occurrence_with_no_matching_event_history_row():
    print("=== fill_missing_actuals: a fact for an occurrence never recorded in event_history at all is skipped, not inserted ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 14, 12, 0, tzinfo=UTC_TZ)
        facts = [("Nonexistent Event", now - dt.timedelta(hours=48), "1.0%", "should never be written")]
        report = fill.run(facts, conn, now=now)
        assert report.skipped == 1
        assert report.written == 0
        rows = store.get_event_history(conn, "Nonexistent Event")
        assert rows == []
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_run_writes_a_real_supplied_actual_with_web_fallback_source()
    test_run_skips_an_occurrence_that_already_has_a_real_actual()
    test_run_skips_an_occurrence_with_no_matching_event_history_row()
    print("All fill_missing_actuals tests passed.")
