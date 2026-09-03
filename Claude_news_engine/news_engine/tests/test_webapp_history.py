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


def test_resolved_event_with_shrug_print_call_and_no_accumulator_prediction_excluded_entirely():
    print("=== build_print_call_history: a shrug print call (confidence <= NO_HIT_CONFIDENCE) is treated as no call — excluded when there's no accumulator prediction either (2026-09-04 fix) ===")
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

        assert rows == []
    print("PASS\n")


def test_resolved_event_with_shrug_print_call_falls_back_to_real_accumulator_prediction():
    print("=== build_print_call_history: a shrug print call (confidence <= NO_HIT_CONFIDENCE) no longer masks a real, higher-confidence accumulator prediction — falls back to it instead of reporting a false 'no strong call' (2026-09-04 fix) ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.2%", "0.0%", "0.5%"),
            "higher", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        # An 8-article batch that matched none of PRINT_SURPRISE_LEXICON's
        # phrases — a real, contentless stub (not None).
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", event_time,
            PrintCall(direction="in_line", confidence=0.15, article_count=8), now=event_time,
        )
        # XAUUSD is inverse-mapped and CPI m/m is higher_bullish, so a
        # 'bearish' gold call implies a 'higher' surprise (same math the
        # existing test_resolved_numeric_event_falls_back_to_accumulator_
        # prediction_when_no_print_call test above already relies on).
        backtest_store.record_prediction(
            bt_conn, "CPI m/m", "XAUUSD", event_time,
            0.7, "bearish", 0.6, 40, False, scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].instrument == "XAUUSD"
        assert rows[0].ne_prediction == "bearish"
        assert rows[0].outcome == "Confirmed"
        assert rows[0].unjudged_reason is None
    print("PASS\n")


def test_resolved_event_in_line_surprise_graded_against_real_outcome_not_the_number():
    print("=== build_print_call_history: an in_line surprise_direction is graded against the real Dukascopy-confirmed outcome, not a false Missed (2026-09-04 fix) ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 3, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Unemployment Claims", event_time, "205K", "203K", "206K"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        # 8 articles, zero phrase hits -> contentless print-call stub.
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "Unemployment Claims", event_time,
            PrintCall(direction="in_line", confidence=0.15, article_count=8), now=event_time,
        )
        backtest_store.record_prediction(
            bt_conn, "Unemployment Claims", "XAUUSD", event_time,
            0.56, "bullish", 0.21, 92, False, scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].outcome is None
        assert rows[0].unjudged_reason == "pending"  # no outcomes row recorded yet — not a false Missed

        # Now record the real Dukascopy-confirmed move (matches the bullish call).
        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_outcome(bt_conn, "Unemployment Claims", "XAUUSD", event_time, "bullish", "Dukascopy: +1.07% in 30min (auto)")
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].outcome == "Confirmed"
        assert rows[0].unjudged_reason is None
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


def test_resolved_numeric_event_with_neither_print_call_nor_prediction_excluded_entirely():
    print("=== build_print_call_history: a resolved numeric event with NEITHER a print_predictions row NOR a predictions row is excluded entirely ===")
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


def test_resolved_numeric_event_falls_back_to_accumulator_prediction_when_no_print_call():
    print("=== build_print_call_history: a resolved numeric event with NO print-call but a real accumulator prediction falls back to it, one row per instrument, Confirmed when the call matches the real surprise ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        # "CPI m/m" is higher_bullish. Actual beat forecast -> surprise_direction='higher'.
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.4%"),
            "higher", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        # No print_predictions row at all (never mocked/seeded) — only the
        # accumulator's own main prediction. XAUUSD is inverse-mapped, so a
        # higher_bullish surprise implies a BEARISH call for gold.
        backtest_store.record_prediction(
            bt_conn, "CPI m/m", "XAUUSD", event_time,
            0.7, "bearish", 0.6, 40, False, scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].instrument == "XAUUSD"
        assert rows[0].ne_prediction == "bearish"
        assert rows[0].previous == "-0.4%"
        assert rows[0].forecast == "0.1%"
        assert rows[0].actual == "0.4%"
        assert rows[0].outcome == "Confirmed"
    print("PASS\n")


def test_resolved_numeric_event_fallback_missed_when_direction_mismatches():
    print("=== build_print_call_history: the accumulator-prediction fallback judges Missed when the call disagrees with the real surprise ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.4%"),
            "higher", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        # Same higher_bullish surprise as above, but this time the recorded
        # call is BULLISH for gold (inverse-mapped) -- the wrong sign.
        backtest_store.record_prediction(
            bt_conn, "CPI m/m", "XAUUSD", event_time,
            0.7, "bullish", 0.6, 40, False, scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].outcome == "Missed"
    print("PASS\n")


def test_resolved_numeric_event_fallback_neutral_direction_not_judged():
    print("=== build_print_call_history: the accumulator-prediction fallback treats a 'neutral' call as unjudged (shrug), never inverted ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.4%"),
            "higher", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "CPI m/m", "XAUUSD", event_time,
            0.5, "neutral", 0.6, 40, False, scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].outcome is None
        assert rows[0].unjudged_reason == "shrug"
    print("PASS\n")


def test_resolved_numeric_event_fallback_produces_one_row_per_instrument():
    print("=== build_print_call_history: the accumulator-prediction fallback produces one row per instrument with its own recorded prediction ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.4%"),
            "higher", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "CPI m/m", "XAUUSD", event_time,
            0.7, "bearish", 0.6, 40, False, scored_at_utc=event_time,
        )
        # No US30 prediction recorded for this occurrence — must not produce a row.
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].instrument == "XAUUSD"
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


def test_history_row_carries_source_and_prefers_seeded_when_mixed():
    print("=== webapp/history: HistoryRow.source reflects the underlying row's provenance ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Core CPI m/m", event_time, "0.2%", "0.0%", "0.2%"),
            "in_line", now=event_time, source="seeded",
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "Core CPI m/m", event_time,
            PrintCall(direction="lower", confidence=0.51, article_count=89), now=event_time, source="live",
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows[0].source == "seeded"
    print("PASS\n")


def test_history_row_carries_live_web_fallback_source_intact():
    print("=== webapp/history: HistoryRow.source preserves 'live_web_fallback' — not collapsed to 'live' ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Core CPI m/m", event_time, "0.2%", "0.0%", "0.2%"),
            "in_line", now=event_time, source="live_web_fallback",
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "Core CPI m/m", event_time,
            PrintCall(direction="lower", confidence=0.51, article_count=89), now=event_time, source="live",
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows[0].source == "live_web_fallback"
    print("PASS\n")


def test_history_row_carries_fred_source_intact():
    print("=== webapp/history: HistoryRow.source preserves 'fred' — not collapsed to 'live' ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Core CPI m/m", event_time, "0.2%", "0.0%", "0.2%"),
            "in_line", now=event_time, source="fred",
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "Core CPI m/m", event_time,
            PrintCall(direction="lower", confidence=0.51, article_count=89), now=event_time, source="live",
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows[0].source == "fred"
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
        assert rows[0].unjudged_reason == "pending"
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
            dash_conn, _resolved_event("Prelim GDP q/q", event_time, "2.1%", "2.0%", None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "Prelim GDP q/q", "XAUUSD", event_time,
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
    print("=== build_print_call_history: a rare numeric row is not starved out of the SAME query's pre-filter by more recent numeric rows ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        base_time = dt.datetime(2026, 8, 1, 12, 0, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        bt_conn = backtest_store.get_connection(backtest_db)

        # 60 recent, resolved numeric events, more recent than the target
        # below — enough to fill get_resolved_event_history()'s pre-filter
        # budget on their own at limit=50, which is exactly what starves
        # the older target row out BEFORE any merge or print_predictions
        # lookup happens. Deliberately given NEITHER a print_predictions
        # NOR a predictions row (2026-09-02: the latter now produces its
        # own fallback output row, per build_print_call_history()'s
        # accumulator-prediction fallback) — these rows exist purely to
        # inflate the row COUNT for the SQL pre-filter check and must
        # contribute nothing to the final output either way, so this test
        # isolates the pre-filter concern from the separate final
        # display-limit truncation.
        for i in range(60):
            event_time = base_time + dt.timedelta(days=i + 1)
            crowding_event = EconomicEvent(
                title="Retail Sales m/m", country="USD", impact="High", event_time_utc=event_time,
                forecast="0.1%", previous="0.1%", actual="0.1%",
            )
            store.upsert_event_history(dash_conn, crowding_event, "in_line", now=event_time)

        # One OLDER, rare numeric event, also with a real print call — with
        # limit=50 pushed into the pre-filter (the bug), this is pushed
        # past position 50 by the 60 more-recent crowding rows and dropped
        # BEFORE the merge/sort/truncate step ever runs.
        target_time = base_time
        target_event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High", event_time_utc=target_time,
            forecast="0.1%", previous="-0.4%", actual="0.1%",
        )
        store.upsert_event_history(dash_conn, target_event, "in_line", now=target_time)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", target_time,
            PrintCall(direction="in_line", confidence=0.6, article_count=50), now=target_time,
        )
        dash_conn.close()
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(limit=50)

        assert any(r.event_title == "CPI m/m" for r in rows), (
            "the older, rare row was starved out of the pre-filter by more-recent rows sharing the same query and limit"
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
        assert rows[0].unjudged_reason == "unknown_surprise"
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
        assert rows[0].unjudged_reason == "shrug"
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


def test_numeric_row_recognizes_cloud_web_fallback_source():
    print("=== webapp/history: HistoryRow.source recognizes 'cloud_web_fallback' on the numeric print-call path, never collapsed to 'live' ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Core CPI m/m", event_time, "0.2%", "0.0%", "0.2%"),
            "in_line", now=event_time, source="cloud_web_fallback",
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "Core CPI m/m", event_time,
            PrintCall(direction="lower", confidence=0.51, article_count=89), now=event_time, source="live",
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows[0].source == "cloud_web_fallback"
    print("PASS\n")


def test_fallback_row_recognizes_cloud_web_fallback_source():
    print("=== webapp/history: HistoryRow.source recognizes 'cloud_web_fallback' on the accumulator-prediction fallback path too ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.4%"),
            "higher", now=event_time, source="cloud_web_fallback",
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        # No print_predictions row at all -- exercises the fallback branch.
        backtest_store.record_prediction(
            bt_conn, "CPI m/m", "XAUUSD", event_time,
            0.7, "bearish", 0.6, 40, False, scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].source == "cloud_web_fallback"
    print("PASS\n")


if __name__ == "__main__":
    test_resolved_event_with_real_call_is_judged()
    test_resolved_event_with_shrug_call_excluded_from_judging()
    test_unresolved_numeric_event_excluded_entirely()
    test_resolved_numeric_event_with_neither_print_call_nor_prediction_excluded_entirely()
    test_resolved_numeric_event_falls_back_to_accumulator_prediction_when_no_print_call()
    test_resolved_numeric_event_fallback_missed_when_direction_mismatches()
    test_resolved_numeric_event_fallback_neutral_direction_not_judged()
    test_resolved_numeric_event_fallback_produces_one_row_per_instrument()
    test_history_row_carries_source_and_prefers_seeded_when_mixed()
    test_history_row_carries_live_web_fallback_source_intact()
    test_history_row_carries_fred_source_intact()
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
    test_numeric_row_recognizes_cloud_web_fallback_source()
    test_fallback_row_recognizes_cloud_web_fallback_source()
    print("All webapp_history tests passed.")
