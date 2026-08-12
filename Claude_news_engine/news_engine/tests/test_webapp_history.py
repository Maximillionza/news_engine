"""
Tests for webapp/history.py — the History tab's read-only cross-pipeline
join between webapp.store's event_history and scoring.backtest_store's
print_predictions (numeric events) / predictions+outcomes (text-only
events). No network needed.
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
from scoring.print_direction import PrintCall
import webapp.history as history
import webapp.store as store
import scoring.backtest_store as backtest_store


def _resolved_event(title, event_time, forecast, previous, actual):
    return EconomicEvent(
        title=title, country="USD", impact="High", event_time_utc=event_time,
        forecast=forecast, previous=previous, actual=actual,
    )


# --- Numeric-event rows ---

def test_resolved_event_with_real_call_is_judged():
    print("=== build_print_call_history: a resolved numeric event with a real (non-shrug) call is Confirmed or Missed ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Core CPI m/m", event_time, "0.2%", "0.0%", "0.2%"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "Core CPI m/m", event_time,
            PrintCall(direction="lower", confidence=0.51, article_count=89), now=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].instrument is None
        assert rows[0].ne_prediction == "lower"
        assert rows[0].outcome == "Missed"  # predicted lower, actual was in_line
    print("PASS\n")


def test_resolved_event_with_shrug_call_excluded_from_judging():
    print("=== build_print_call_history: a shrug call (confidence <= NO_HIT_CONFIDENCE) is shown but not judged ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.1%"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", event_time,
            PrintCall(direction="in_line", confidence=0.15, article_count=89), now=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].outcome is None
    print("PASS\n")


def test_unresolved_numeric_event_excluded_entirely():
    print("=== build_print_call_history: a numeric event with no actual yet is excluded entirely ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("PPI m/m", event_time, "0.2%", "-0.3%", None),
            None, now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "PPI m/m", event_time,
            PrintCall(direction="in_line", confidence=0.15, article_count=93), now=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows == []
    print("PASS\n")


def test_resolved_numeric_event_with_no_print_call_excluded_entirely():
    print("=== build_print_call_history: a resolved numeric event with NO print_predictions row is excluded entirely ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Building Permits m/m", event_time, "0.8%", "-1.7%", "0.9%"),
            "higher", now=event_time,
        )
        dash_conn.close()

        backtest_store.get_connection(backtest_db).close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows == []
    print("PASS\n")


def test_unchanged_vs_previous_badge_does_not_affect_outcome():
    print("=== build_print_call_history: unchanged_vs_previous is a pure display flag on numeric rows, zero effect on outcome ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        unchanged_time = dt.datetime(2026, 7, 12, 12, 30, tzinfo=UTC_TZ)
        changed_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", unchanged_time, "0.2%", "0.2%", "0.2%"),
            "in_line", now=unchanged_time,
        )
        store.upsert_event_history(
            dash_conn, _resolved_event("PPI m/m", changed_time, "0.2%", "-0.3%", "0.2%"),
            "higher", now=changed_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", unchanged_time,
            PrintCall(direction="in_line", confidence=0.4, article_count=50), now=unchanged_time,
        )
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "PPI m/m", changed_time,
            PrintCall(direction="higher", confidence=0.4, article_count=50), now=changed_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        unchanged_row = next(r for r in rows if r.event_title == "CPI m/m")
        changed_row = next(r for r in rows if r.event_title == "PPI m/m")
        assert unchanged_row.unchanged_vs_previous is True
        assert changed_row.unchanged_vs_previous is False
        assert unchanged_row.outcome == "Confirmed"
        assert changed_row.outcome == "Confirmed"
    print("PASS\n")


# --- Text-event fallback rows ---

def test_text_only_event_with_prediction_produces_fallback_row():
    print("=== build_print_call_history: a text-only event (no forecast/actual) with a real prediction produces one row per instrument ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 17, 18, 0, tzinfo=UTC_TZ)
        now = event_time + dt.timedelta(hours=1)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("FOMC Statement", event_time, None, None, None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", event_time,
            0.62, "bullish", 0.5, 40, False, scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert len(rows) == 1
        assert rows[0].event_title == "FOMC Statement"
        assert rows[0].instrument == "XAUUSD"
        assert rows[0].previous is None
        assert rows[0].forecast is None
        assert rows[0].actual is None
        assert rows[0].unchanged_vs_previous is False
        assert rows[0].ne_prediction == "bullish"
        assert rows[0].outcome is None  # not confirmed yet — "Awaiting confirmation"
    print("PASS\n")


def test_text_only_event_confirmed_outcome_judged_correctly():
    print("=== build_print_call_history: a confirmed outcome for a text-only event judges Confirmed/Missed correctly ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 17, 18, 0, tzinfo=UTC_TZ)
        now = event_time + dt.timedelta(hours=1)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("FOMC Statement", event_time, None, None, None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", event_time,
            0.62, "bullish", 0.5, 40, False, scored_at_utc=event_time,
        )
        backtest_store.record_outcome(bt_conn, "FOMC Statement", "XAUUSD", event_time, "bearish", "gold sold off on hawkish tone")
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert rows[0].outcome == "Missed"  # predicted bullish, actual was bearish
    print("PASS\n")


def test_text_only_event_missing_prediction_for_one_instrument_produces_no_row_for_it():
    print("=== build_print_call_history: an instrument with no prediction for a text-only occurrence gets no row ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 17, 18, 0, tzinfo=UTC_TZ)
        now = event_time + dt.timedelta(hours=1)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("FOMC Statement", event_time, None, None, None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", event_time,
            0.62, "bullish", 0.5, 40, False, scored_at_utc=event_time,
        )
        # No prediction recorded for US30 for this occurrence.
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert len(rows) == 1
        assert rows[0].instrument == "XAUUSD"
    print("PASS\n")


def test_future_text_only_event_excluded():
    print("=== build_print_call_history: a text-only event that hasn't happened yet is excluded, even with a prediction ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        now = dt.datetime(2026, 9, 1, 12, 0, tzinfo=UTC_TZ)
        future_event_time = now + dt.timedelta(hours=48)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("FOMC Statement", future_event_time, None, None, None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", future_event_time,
            0.62, "bullish", 0.5, 40, False, scored_at_utc=now,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert rows == []
    print("PASS\n")


def test_partially_numeric_event_not_misclassified_as_text_only():
    print("=== build_print_call_history: an event with a forecast but no actual yet is NOT treated as text-only ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        now = dt.datetime(2026, 9, 1, 12, 0, tzinfo=UTC_TZ)
        event_time = now - dt.timedelta(hours=2)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Advance GDP q/q", event_time, "2.1%", "2.0%", None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "Advance GDP q/q", "XAUUSD", event_time,
            0.55, "bullish", 0.4, 30, False, scored_at_utc=now,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert rows == []  # not resolved numerically (no actual), and NOT text-only (has a forecast)
    print("PASS\n")


def test_cross_pipeline_read_failure_fails_open_to_empty_list():
    print("=== build_print_call_history: an unreachable backtest DB fails open to an empty list, does not raise ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.1%"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        unreachable_backtest_db = Path(tmp) / "nonexistent_subdir" / "backtest.db"

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", unreachable_backtest_db):
            rows = history.build_print_call_history()

        assert rows == []
    print("PASS\n")


def test_pre_filter_limit_does_not_starve_rare_row_type():
    print("=== build_print_call_history: a rare row type is not starved out by the display limit being applied to the pre-filter ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        base_time = dt.datetime(2026, 8, 1, 12, 0, tzinfo=UTC_TZ)
        now = base_time + dt.timedelta(days=60)

        dash_conn = store.get_connection(dash_db)
        bt_conn = backtest_store.get_connection(backtest_db)

        # 60 common numeric events, all more recent than the one FOMC event below —
        # with a naive limit=50 pre-filter on get_resolved_event_history, these
        # alone would already exceed the display limit and could crowd out
        # anything queried with the SAME limit in a separate, unrelated source.
        for i in range(60):
            event_time = base_time + dt.timedelta(days=i)
            common_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
                forecast="0.1%", previous="0.1%", actual="0.1%",
            )
            store.upsert_event_history(dash_conn, common_event, "in_line", now=event_time)

        # One old, rare text-only event (FOMC-style) — must still survive the merge.
        fomc_time = base_time - dt.timedelta(days=5)
        fomc_event = EconomicEvent(
            title="FOMC Statement", country="USD", impact="High", event_time_utc=fomc_time,
            forecast=None, previous=None, actual=None,
        )
        store.upsert_event_history(dash_conn, fomc_event, None, now=fomc_time)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", fomc_time,
            0.6, "bullish", 0.5, 40, False, scored_at_utc=fomc_time,
        )
        dash_conn.close()
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(limit=50, now=now)

        assert any(r.event_title == "FOMC Statement" for r in rows), (
            "the rare text-only row was starved out of the pre-filter by the unrelated numeric rows sharing the same limit"
        )
    print("PASS\n")


def test_null_surprise_direction_is_not_judged_as_missed():
    print("=== build_print_call_history: a resolved event with surprise_direction=None is NOT judged Missed, stays unjudged ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        # actual is set (resolved) but surprise_direction is None — e.g. classify_surprise()
        # failed to parse it, or the title fell out of EVENT_SURPRISE_DIRECTION coverage.
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "<0.1%"),
            None, now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", event_time,
            PrintCall(direction="higher", confidence=0.6, article_count=50), now=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].outcome is None  # NOT "Missed" — surprise_direction was never known
    print("PASS\n")


def test_text_only_low_confidence_prediction_not_judged():
    print("=== build_print_call_history: a text-only event's low-confidence prediction is not judged, even with a confirmed outcome ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 17, 18, 0, tzinfo=UTC_TZ)
        now = event_time + dt.timedelta(hours=1)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("FOMC Statement", event_time, None, None, None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", event_time,
            0.51, "neutral", 0.009, 40, False, scored_at_utc=event_time,  # confidence=0.9%, well below the floor
        )
        backtest_store.record_outcome(bt_conn, "FOMC Statement", "XAUUSD", event_time, "neutral", "muted reaction")
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert len(rows) == 1
        assert rows[0].outcome is None  # NOT judged, despite a confirmed outcome existing and technically matching
    print("PASS\n")


def test_empty_result_when_nothing_resolved():
    print("=== build_print_call_history: no resolved history at all returns an empty list, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        store.get_connection(dash_db).close()
        backtest_store.get_connection(backtest_db).close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows == []
    print("PASS\n")


if __name__ == "__main__":
    test_resolved_event_with_real_call_is_judged()
    test_resolved_event_with_shrug_call_excluded_from_judging()
    test_unresolved_numeric_event_excluded_entirely()
    test_resolved_numeric_event_with_no_print_call_excluded_entirely()
    test_unchanged_vs_previous_badge_does_not_affect_outcome()
    test_text_only_event_with_prediction_produces_fallback_row()
    test_text_only_event_confirmed_outcome_judged_correctly()
    test_text_only_event_missing_prediction_for_one_instrument_produces_no_row_for_it()
    test_future_text_only_event_excluded()
    test_partially_numeric_event_not_misclassified_as_text_only()
    test_cross_pipeline_read_failure_fails_open_to_empty_list()
    test_pre_filter_limit_does_not_starve_rare_row_type()
    test_null_surprise_direction_is_not_judged_as_missed()
    test_text_only_low_confidence_prediction_not_judged()
    test_empty_result_when_nothing_resolved()
    print("All webapp_history tests passed.")
