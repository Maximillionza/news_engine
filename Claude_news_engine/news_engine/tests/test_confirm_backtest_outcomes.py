"""
Tests for scripts/confirm_backtest_outcomes.py's --auto phase
(run_auto_confirm_phase). classify() is mocked, no live Dukascopy calls.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import get_connection, record_prediction, get_all_confirmed_cases
from scoring.probability_engine import Direction
from scoring.outcome_classifier import ClassificationResult
import scoring.outcome_classifier
import scripts.confirm_backtest_outcomes as confirm_cli


def test_auto_confirms_clear_classifications_and_leaves_ambiguous_ones():
    print("=== confirm_backtest_outcomes --auto: clear classifications get recorded, ambiguous ones are left for review ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        clear_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        ambiguous_time = dt.datetime(2026, 8, 2, 12, 30, tzinfo=dt.timezone.utc)
        record_prediction(conn, "NFP", "XAUUSD", clear_time, 0.7, "bullish", 0.4, 8, False)
        record_prediction(conn, "CPI", "US30", ambiguous_time, 0.6, "bearish", 0.3, 5, False)

        def fake_classify(instrument, event_time_utc):
            if instrument == "XAUUSD":
                return ClassificationResult(direction=Direction.BULLISH, move_pct=0.34, note="Dukascopy: +0.34% in 30min (auto)")
            return ClassificationResult(direction=None, move_pct=0.05, note="Dukascopy: +0.05% in 30min, below 0.15% threshold")

        with patch.object(scoring.outcome_classifier, "classify", side_effect=fake_classify):
            summary = confirm_cli.run_auto_confirm_phase(conn)

        assert summary["auto_confirmed"] == 1
        assert summary["left_for_review"] == 1
        cases = get_all_confirmed_cases(conn)
        assert len(cases) == 1
        assert cases[0][1].actual_direction == "bullish"
        key = ("CPI", "US30", ambiguous_time.isoformat())
        assert key in summary["suggestions"]
        assert summary["suggestions"][key].note == "Dukascopy: +0.05% in 30min, below 0.15% threshold"
        conn.close()
    print("PASS\n")


def test_auto_confirm_skips_a_row_that_raises_and_continues():
    print("=== confirm_backtest_outcomes --auto: a row whose classify() raises is skipped with a warning, loop continues ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        bad_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        good_time = dt.datetime(2026, 8, 2, 12, 30, tzinfo=dt.timezone.utc)
        record_prediction(conn, "BadEvent", "US30", bad_time, 0.7, "bullish", 0.4, 8, False)
        record_prediction(conn, "NFP", "XAUUSD", good_time, 0.6, "bullish", 0.3, 5, False)

        def fake_classify(instrument, event_time_utc):
            if instrument == "US30":
                raise ValueError("instrument=US30 has no Dukascopy mapping")
            return ClassificationResult(direction=Direction.BULLISH, move_pct=0.34, note="Dukascopy: +0.34% in 30min (auto)")

        with patch.object(scoring.outcome_classifier, "classify", side_effect=fake_classify):
            summary = confirm_cli.run_auto_confirm_phase(conn)

        assert summary["auto_confirmed"] == 1
        cases = get_all_confirmed_cases(conn)
        assert len(cases) == 1
        assert cases[0][1].actual_direction == "bullish"
        key = ("BadEvent", "US30", bad_time.isoformat())
        assert key not in summary["suggestions"], "a row that raised must not be added to suggestions"
        conn.close()
    print("PASS\n")


def test_auto_confirm_on_empty_queue_does_nothing():
    print("=== confirm_backtest_outcomes --auto: an empty awaiting-outcome queue produces a 0/0 summary, not a crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        summary = confirm_cli.run_auto_confirm_phase(conn)
        assert summary == {"auto_confirmed": 0, "left_for_review": 0, "suggestions": {}}
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_auto_confirms_clear_classifications_and_leaves_ambiguous_ones()
    test_auto_confirm_skips_a_row_that_raises_and_continues()
    test_auto_confirm_on_empty_queue_does_nothing()
    print("All confirm_backtest_outcomes tests passed.")
