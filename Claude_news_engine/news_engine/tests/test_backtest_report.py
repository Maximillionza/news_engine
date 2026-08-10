"""
Tests for scoring/backtest.py's build_real_backtest_report() — uses a
temp SQLite file, no network needed.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scoring.backtest_store as store
import scoring.backtest as backtest


def test_build_real_backtest_report_from_confirmed_cases():
    print("=== backtest: build_real_backtest_report reads confirmed cases and produces a working report ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        store.record_prediction(conn, "NFP", "XAUUSD", event_time, 0.71, "bullish", 0.55, 12, False)
        store.record_outcome(conn, "NFP", "XAUUSD", event_time, "bullish", "confirmed real move")
        conn.close()

        report = backtest.build_real_backtest_report(db_path=db_path)
        assert len(report.cases) == 1
        assert report.cases[0].predicted_correct is True
        assert report.accuracy() == 1.0
    print("PASS\n")


def test_build_real_backtest_report_marks_wrong_calls_correctly():
    print("=== backtest: a mismatched prediction/outcome direction is correctly marked wrong ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        store.record_prediction(conn, "CPI", "XAUUSD", event_time, 0.65, "bearish", 0.4, 8, False)
        store.record_outcome(conn, "CPI", "XAUUSD", event_time, "bullish", "actual move was the opposite direction")
        conn.close()

        report = backtest.build_real_backtest_report(db_path=db_path)
        assert len(report.cases) == 1
        assert report.cases[0].predicted_correct is False
        assert report.accuracy() == 0.0
    print("PASS\n")


def test_build_real_backtest_report_empty_when_nothing_confirmed():
    print("=== backtest: an empty confirmed-cases table produces an empty report, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store.get_connection(db_path).close()  # just create the schema, no rows

        report = backtest.build_real_backtest_report(db_path=db_path)
        assert len(report.cases) == 0
        assert report.accuracy() is None
    print("PASS\n")


if __name__ == "__main__":
    test_build_real_backtest_report_from_confirmed_cases()
    test_build_real_backtest_report_marks_wrong_calls_correctly()
    test_build_real_backtest_report_empty_when_nothing_confirmed()
    print("All backtest_report tests passed.")
