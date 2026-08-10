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
    record_dismissal,
)


def test_record_and_count_predictions():
    print("=== backtest_store: record_prediction + count_predictions round-trip ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=dt.timezone.utc)

        assert count_predictions(conn, "CPI m/m", "XAUUSD", event_time) == 0
        record_prediction(conn, "CPI m/m", "XAUUSD", event_time, 0.71, "bullish", 0.55, 12, False)
        assert count_predictions(conn, "CPI m/m", "XAUUSD", event_time) == 1
        record_prediction(conn, "CPI m/m", "XAUUSD", event_time, 0.68, "bullish", 0.60, 15, False)
        assert count_predictions(conn, "CPI m/m", "XAUUSD", event_time) == 2
        conn.close()
    print("PASS\n")


def test_count_predictions_scoped_to_event_occurrence_not_just_title():
    print("=== backtest_store: count_predictions is scoped to (title, instrument, event_time_utc), not title alone ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        august_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
        september_time = dt.datetime(2026, 9, 4, 12, 30, tzinfo=dt.timezone.utc)

        # August occurrence of a recurring title consumes its full 2-snapshot budget.
        record_prediction(conn, "Non-Farm Employment Change", "XAUUSD", august_time, 0.71, "bullish", 0.55, 12, False)
        record_prediction(conn, "Non-Farm Employment Change", "XAUUSD", august_time, 0.68, "bullish", 0.60, 15, False)
        assert count_predictions(conn, "Non-Farm Employment Change", "XAUUSD", august_time) == 2

        # September's occurrence of the SAME title/instrument must start fresh at 0 —
        # this is the exact scenario that was broken when the query only filtered on
        # (event_title, instrument) and ignored event_time_utc.
        assert count_predictions(conn, "Non-Farm Employment Change", "XAUUSD", september_time) == 0
        record_prediction(conn, "Non-Farm Employment Change", "XAUUSD", september_time, 0.65, "bearish", 0.50, 9, False)
        assert count_predictions(conn, "Non-Farm Employment Change", "XAUUSD", september_time) == 1
        # August's count must remain unaffected by September's new row.
        assert count_predictions(conn, "Non-Farm Employment Change", "XAUUSD", august_time) == 2
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


def test_record_outcome_rejects_invalid_actual_direction():
    print("=== backtest_store: record_outcome validates actual_direction at the data layer ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        record_prediction(conn, "NFP", "XAUUSD", event_time, 0.7, "bullish", 0.4, 8, False)

        # A capitalization typo — exactly the case the interactive CLI's own
        # lowercase-then-check catches, but nothing stopped a non-CLI caller
        # (or a future script) from persisting it straight into the DB, where
        # it would later crash build_real_backtest_report()'s Direction(...).
        try:
            record_outcome(conn, "NFP", "XAUUSD", event_time, "Bullish", "typo'd case")
            raise AssertionError("expected ValueError for invalid actual_direction, none raised")
        except ValueError as e:
            assert "Bullish" in str(e), f"error message should name the bad value, got: {e}"

        # Nothing should have been persisted by the rejected call.
        awaiting = get_predictions_awaiting_outcome(conn, now=dt.datetime(2026, 8, 10, tzinfo=dt.timezone.utc))
        assert len(awaiting) == 1, "rejected outcome must not be recorded — prediction should still be awaiting"
        conn.close()
    print("PASS\n")


def test_dismissed_prediction_stops_appearing_in_awaiting_outcome():
    print("=== backtest_store: a dismissed prediction (rescheduled/canceled event) leaves the awaiting-outcome queue for good ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        past_event = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        now = dt.datetime(2026, 8, 10, tzinfo=dt.timezone.utc)
        record_prediction(conn, "CPI m/m", "XAUUSD", past_event, 0.7, "bullish", 0.4, 8, False)

        awaiting = get_predictions_awaiting_outcome(conn, now=now)
        assert len(awaiting) == 1, "prediction should be awaiting an outcome before any dismissal"

        # The event never actually happened at this time — Forex Factory
        # rescheduled/canceled it — so a real outcome will never arrive.
        # Without dismissal this row would surface on every single future
        # --list / interactive run, forever.
        record_dismissal(conn, "CPI m/m", "XAUUSD", past_event, "rescheduled to next week per FF calendar")

        awaiting_after = get_predictions_awaiting_outcome(conn, now=now)
        assert len(awaiting_after) == 0, "dismissed prediction must no longer appear as awaiting outcome"

        # A dismissed pair must not show up as a confirmed case either — it
        # was never actually resolved, never fabricate a result for it.
        cases = get_all_confirmed_cases(conn)
        assert len(cases) == 0, "a dismissed (not confirmed) pair must not appear in confirmed cases"
        conn.close()
    print("PASS\n")


def test_dismissing_an_already_confirmed_pair_is_rejected():
    print("=== backtest_store: record_dismissal refuses a pair that already has a real confirmed outcome ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        record_prediction(conn, "CPI m/m", "XAUUSD", event_time, 0.7, "bullish", 0.4, 8, False)
        record_outcome(conn, "CPI m/m", "XAUUSD", event_time, "bullish", "confirmed real move")

        try:
            record_dismissal(conn, "CPI m/m", "XAUUSD", event_time, "mistaken dismissal attempt")
            raise AssertionError("expected a ValueError, dismissing an already-confirmed pair silently succeeded")
        except ValueError:
            pass

        # The real confirmed outcome must be untouched by the rejected dismissal.
        cases = get_all_confirmed_cases(conn)
        assert len(cases) == 1
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
    test_count_predictions_scoped_to_event_occurrence_not_just_title()
    test_awaiting_outcome_uses_latest_snapshot_and_excludes_confirmed()
    test_record_outcome_rejects_invalid_actual_direction()
    test_dismissed_prediction_stops_appearing_in_awaiting_outcome()
    test_dismissing_an_already_confirmed_pair_is_rejected()
    test_confirmed_cases_joins_latest_prediction_with_outcome()
    print("All backtest_store tests passed.")
