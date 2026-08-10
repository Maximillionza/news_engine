"""
Tests for scoring/backtest_store.py — uses a temp SQLite file, no network needed.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import (
    get_connection, record_prediction, count_predictions,
    get_predictions_awaiting_outcome, record_outcome, get_all_confirmed_cases,
)


def test_record_and_count_predictions():
    print("=== backtest_store: record_prediction + count_predictions round-trip ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=dt.timezone.utc)

        assert count_predictions(conn, "CPI m/m", "XAUUSD") == 0
        record_prediction(conn, "CPI m/m", "XAUUSD", event_time, 0.71, "bullish", 0.55, 12, False)
        assert count_predictions(conn, "CPI m/m", "XAUUSD") == 1
        record_prediction(conn, "CPI m/m", "XAUUSD", event_time, 0.68, "bullish", 0.60, 15, False)
        assert count_predictions(conn, "CPI m/m", "XAUUSD") == 2
        conn.close()
    print("PASS\n")


def test_awaiting_outcome_uses_latest_snapshot_and_excludes_confirmed():
    print("=== backtest_store: awaiting-outcome list uses latest snapshot, excludes already-confirmed pairs ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        past_event = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)   # already passed
        future_event = dt.datetime(2026, 8, 20, 12, 30, tzinfo=dt.timezone.utc)  # not yet
        now = dt.datetime(2026, 8, 10, tzinfo=dt.timezone.utc)

        t1 = dt.datetime(2026, 7, 30, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2026, 7, 31, tzinfo=dt.timezone.utc)
        record_prediction(conn, "NFP", "XAUUSD", past_event, 0.5, "neutral", 0.1, 3, False, scored_at_utc=t1)
        record_prediction(conn, "NFP", "XAUUSD", past_event, 0.7, "bullish", 0.4, 8, False, scored_at_utc=t2)
        record_prediction(conn, "CPI", "US30", future_event, 0.6, "bullish", 0.3, 5, False)

        awaiting = get_predictions_awaiting_outcome(conn, now=now)
        assert len(awaiting) == 1, f"expected only the past NFP event, got {len(awaiting)}"
        assert awaiting[0].event_title == "NFP"
        assert awaiting[0].probability == 0.7, "should surface the LATEST snapshot, not the first"

        record_outcome(conn, "NFP", "XAUUSD", past_event, "bullish", "real outcome confirmed")
        awaiting_after = get_predictions_awaiting_outcome(conn, now=now)
        assert len(awaiting_after) == 0, "confirmed pair should no longer be awaiting"
        conn.close()
    print("PASS\n")


def test_confirmed_cases_joins_latest_prediction_with_outcome():
    print("=== backtest_store: get_all_confirmed_cases joins the latest snapshot with its outcome ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        t1 = dt.datetime(2026, 7, 30, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2026, 7, 31, tzinfo=dt.timezone.utc)
        record_prediction(conn, "NFP", "XAUUSD", event_time, 0.5, "neutral", 0.1, 3, False, scored_at_utc=t1)
        record_prediction(conn, "NFP", "XAUUSD", event_time, 0.7, "bullish", 0.4, 8, False, scored_at_utc=t2)
        record_prediction(conn, "CPI", "US30", event_time, 0.6, "bullish", 0.3, 5, True)  # never confirmed

        record_outcome(conn, "NFP", "XAUUSD", event_time, "bullish", "confirmed real move")

        cases = get_all_confirmed_cases(conn)
        assert len(cases) == 1, "only the confirmed NFP/XAUUSD pair should appear, not the unconfirmed CPI/US30 one"
        prediction, outcome = cases[0]
        assert prediction.probability == 0.7, "should join the LATEST prediction snapshot"
        assert outcome.actual_direction == "bullish"
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_record_and_count_predictions()
    test_awaiting_outcome_uses_latest_snapshot_and_excludes_confirmed()
    test_confirmed_cases_joins_latest_prediction_with_outcome()
    print("All backtest_store tests passed.")
