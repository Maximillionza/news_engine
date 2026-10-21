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

        # Within 3 days of the ambiguous event, so it is left for review, not finalised (B4 O3).
        now = ambiguous_time + dt.timedelta(days=1)
        with patch.object(scoring.outcome_classifier, "classify", side_effect=fake_classify):
            summary = confirm_cli.run_auto_confirm_phase(conn, now=now)

        assert summary["auto_confirmed"] == 1
        assert summary["final_no_reaction"] == 0
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
        assert summary == {"auto_confirmed": 0, "final_no_reaction": 0, "left_for_review": 0, "suggestions": {}}
        conn.close()
    print("PASS\n")


# --- B4 O3: final "no reaction" outcome after 3 days ---

NOW = dt.datetime(2026, 10, 21, 9, 0, tzinfo=dt.timezone.utc)
BELOW_NOTE = "Dukascopy: +0.05% in 30min, below 0.15% threshold"


def _below_threshold(instrument, event_time_utc):
    return ClassificationResult(direction=None, move_pct=0.05, note=BELOW_NOTE)


def test_below_threshold_older_than_3_days_is_recorded_final_neutral():
    print("=== confirm_backtest_outcomes --auto: a below-threshold move more than 3 days old is recorded as a final neutral outcome ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = get_connection(Path(tmp) / "test.db")
        event_time = dt.datetime(2026, 8, 20, 12, 30, tzinfo=dt.timezone.utc)
        record_prediction(conn, "CPI", "US30", event_time, 0.6, "bearish", 0.3, 5, False)

        with patch.object(scoring.outcome_classifier, "classify", side_effect=_below_threshold):
            summary = confirm_cli.run_auto_confirm_phase(conn, now=NOW)

        cases = get_all_confirmed_cases(conn)
        assert len(cases) == 1
        outcome = cases[0][1]
        assert outcome.actual_direction == "neutral"
        assert outcome.actual_move_note == (
            "Dukascopy: +0.05% in 30min, below 0.15% threshold; no reaction after 3 days, final (auto)"
        )
        assert summary["auto_confirmed"] == 0
        assert summary["final_no_reaction"] == 1
        assert summary["left_for_review"] == 0
        assert ("CPI", "US30", event_time.isoformat()) not in summary["suggestions"]
        conn.close()
    print("PASS\n")


def test_below_threshold_within_3_days_stays_awaiting():
    print("=== confirm_backtest_outcomes --auto: a below-threshold move 3 days old or younger stays awaiting ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = get_connection(Path(tmp) / "test.db")
        younger = NOW - dt.timedelta(days=2, hours=23)
        exactly_3_days = NOW - dt.timedelta(days=3)
        record_prediction(conn, "CPI", "US30", younger, 0.6, "bearish", 0.3, 5, False)
        record_prediction(conn, "NFP", "XAUUSD", exactly_3_days, 0.6, "bullish", 0.3, 5, False)

        with patch.object(scoring.outcome_classifier, "classify", side_effect=_below_threshold):
            summary = confirm_cli.run_auto_confirm_phase(conn, now=NOW)

        assert get_all_confirmed_cases(conn) == []
        assert ("CPI", "US30", younger.isoformat()) in summary["suggestions"]
        assert ("NFP", "XAUUSD", exactly_3_days.isoformat()) in summary["suggestions"]
        assert summary["final_no_reaction"] == 0
        assert summary["left_for_review"] == 2
        conn.close()
    print("PASS\n")


def test_fetch_failure_older_than_3_days_is_not_finalised():
    print("=== confirm_backtest_outcomes --auto: a fetch failure (no price data) is never finalised, however old ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = get_connection(Path(tmp) / "test.db")
        event_time = NOW - dt.timedelta(days=10)
        record_prediction(conn, "CPI", "US30", event_time, 0.6, "bearish", 0.3, 5, False)

        def fetch_failed(instrument, event_time_utc):
            return ClassificationResult(direction=None, move_pct=None, note="Dukascopy fetch failed: no data")

        with patch.object(scoring.outcome_classifier, "classify", side_effect=fetch_failed):
            summary = confirm_cli.run_auto_confirm_phase(conn, now=NOW)

        assert get_all_confirmed_cases(conn) == []
        assert summary["final_no_reaction"] == 0
        assert summary["left_for_review"] == 1
        conn.close()
    print("PASS\n")


def test_final_rows_are_never_re_polled():
    print("=== confirm_backtest_outcomes --auto: a finalised row leaves the queue and is never classified again ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = get_connection(Path(tmp) / "test.db")
        event_time = NOW - dt.timedelta(days=10)
        record_prediction(conn, "CPI", "US30", event_time, 0.6, "bearish", 0.3, 5, False)

        with patch.object(scoring.outcome_classifier, "classify", side_effect=_below_threshold) as fake:
            first = confirm_cli.run_auto_confirm_phase(conn, now=NOW)
            second = confirm_cli.run_auto_confirm_phase(conn, now=NOW)

        assert fake.call_count == 1
        assert first["final_no_reaction"] == 1
        assert second == {"auto_confirmed": 0, "final_no_reaction": 0, "left_for_review": 0, "suggestions": {}}
        assert len(get_all_confirmed_cases(conn)) == 1
        conn.close()
    print("PASS\n")


def test_clear_move_is_still_auto_confirmed_regardless_of_age():
    print("=== confirm_backtest_outcomes --auto: a clear move is auto-confirmed as before, whatever its age ===")
    with tempfile.TemporaryDirectory() as tmp:
        conn = get_connection(Path(tmp) / "test.db")
        event_time = NOW - dt.timedelta(days=10)
        record_prediction(conn, "NFP", "XAUUSD", event_time, 0.7, "bullish", 0.4, 8, False)

        def clear_move(instrument, event_time_utc):
            return ClassificationResult(direction=Direction.BULLISH, move_pct=0.34, note="Dukascopy: +0.34% in 30min (auto)")

        with patch.object(scoring.outcome_classifier, "classify", side_effect=clear_move):
            summary = confirm_cli.run_auto_confirm_phase(conn, now=NOW)

        cases = get_all_confirmed_cases(conn)
        assert len(cases) == 1
        assert cases[0][1].actual_direction == "bullish"
        assert cases[0][1].actual_move_note == "Dukascopy: +0.34% in 30min (auto)"
        assert summary["auto_confirmed"] == 1
        assert summary["final_no_reaction"] == 0
        conn.close()
    print("PASS\n")


# --- B4 O6: the outcome job also triggers the once-per-UTC-day health notice ---

def _run_main(argv, db_path):
    with patch.object(sys, "argv", argv), \
         patch.object(confirm_cli, "get_connection", lambda: get_connection(db_path)), \
         patch.object(confirm_cli, "maybe_send_health_notice", return_value=False) as notice:
        confirm_cli.main()
    return notice


def test_auto_run_triggers_the_health_notice_even_with_nothing_awaiting(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        notice = _run_main(["confirm_backtest_outcomes.py", "--auto", "--list"], Path(tmp) / "test.db")
    assert notice.call_count == 1
    out = capsys.readouterr().out
    assert "Auto-confirm: 0 confirmed, 0 final no-reaction, 0 left for review." in out
    assert "Nothing awaiting confirmation" in out


def test_manual_run_does_not_send_the_health_notice():
    with tempfile.TemporaryDirectory() as tmp:
        notice = _run_main(["confirm_backtest_outcomes.py", "--list"], Path(tmp) / "test.db")
    notice.assert_not_called()


if __name__ == "__main__":
    test_auto_confirms_clear_classifications_and_leaves_ambiguous_ones()
    test_auto_confirm_skips_a_row_that_raises_and_continues()
    test_auto_confirm_on_empty_queue_does_nothing()
    test_below_threshold_older_than_3_days_is_recorded_final_neutral()
    test_below_threshold_within_3_days_stays_awaiting()
    test_fetch_failure_older_than_3_days_is_not_finalised()
    test_final_rows_are_never_re_polled()
    test_clear_move_is_still_auto_confirmed_regardless_of_age()
    print("All confirm_backtest_outcomes tests passed.")
