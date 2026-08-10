"""
Tests for scoring/backtest_accumulator.py — no live network, calendar/
article fetching and scoring are all mocked.
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
from data_layer.event_context import EventNewsBundle
from scoring.probability_engine import Direction, ProbabilityResult
import scoring.backtest_accumulator as accumulator
import scoring.backtest_store as store


def _fake_event(hours_from_now, now):
    return EconomicEvent(
        title="Test Event", country="USD", impact="High",
        event_time_utc=now + dt.timedelta(hours=hours_from_now),
        forecast="1.0%", actual=None,
    )


def _fake_result(probability=0.7, direction=Direction.BULLISH):
    return ProbabilityResult(
        instrument="XAUUSD", as_of_utc=dt.datetime.now(UTC_TZ),
        aggregate_usd_sentiment=0.3, instrument_score=-0.3,
        probability=probability, direction=direction, confidence=0.5,
        article_count=5, contradiction_flag=False, contradiction_note=None,
    )


def test_first_snapshot_taken_immediately_second_only_in_final_snapshot_window():
    print("=== accumulator: first snapshot on window entry, second only within FINAL_SNAPSHOT_WINDOW_HOURS, third never ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)  # inside 72h pre-window, outside FINAL_SNAPSHOT_WINDOW_HOURS

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()):

            # Cycle 1: 20h out, first snapshot should be taken.
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1

            # Cycle 2: still 20h out (not near window) — second snapshot must NOT be taken yet.
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1, "should not take a 2nd snapshot outside the near window"

            # Cycle 3: 2h out — outside the accumulator's own, much tighter
            # FINAL_SNAPSHOT_WINDOW_HOURS (30 min) — the final snapshot must
            # NOT fire this early (this is the exact gap the old
            # shared-with-webapp.scheduler-threshold behavior had).
            still_too_early = event.event_time_utc - dt.timedelta(hours=2)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=still_too_early)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1, \
                "must not take the final snapshot merely for being inside a wider scheduler-style window"

            # Cycle 4: now genuinely close to the event — second snapshot should be taken.
            near_now = event.event_time_utc - dt.timedelta(minutes=20)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 2

            # Cycle 5: budget exhausted, must not take a 3rd snapshot even still in the final window.
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 2, "budget cap must hold"
            conn.close()
    print("PASS\n")


def test_high_impact_only_no_medium_widening():
    print("=== accumulator: uses filter_relevant_events with default (High-only), not Medium widening like the dashboard ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)

        with patch.object(accumulator, "fetch_calendar", return_value=[]) as mock_fetch, \
             patch.object(accumulator, "filter_relevant_events", return_value=[]) as mock_filter:

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            mock_filter.assert_called_once_with(mock_fetch.return_value)
            # No min_impact kwarg — confirms this does NOT widen to Medium like webapp/scheduler.py does.
            assert mock_filter.call_args.kwargs == {}
    print("PASS\n")


def test_failed_scoring_for_one_pair_does_not_stop_others():
    print("=== accumulator: a scoring failure for one instrument doesn't stop the other instrument's snapshot ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)

        def flaky_score_bundle(bundle, instrument):
            if instrument == "XAUUSD":
                raise Exception("scoring blew up")
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", side_effect=flaky_score_bundle):

            accumulator.run_accumulator_cycle(["XAUUSD", "US30"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 0, "the failing instrument should not get a row"
            assert store.count_predictions(conn, "Test Event", "US30", event.event_time_utc) == 1, "the other instrument should still succeed"
            conn.close()
    print("PASS\n")


def test_article_bundle_fetched_once_per_event_not_per_instrument():
    print("=== accumulator: build_event_news_bundle is called ONCE per event, reused across all instruments needing a snapshot ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle) as mock_bundle, \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()):

            accumulator.run_accumulator_cycle(["XAUUSD", "US30"], db_path=db_path, now=now)

            assert mock_bundle.call_count == 1, (
                f"expected build_event_news_bundle to be called exactly once per event "
                f"(reused across instruments), got {mock_bundle.call_count} calls"
            )
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1
            assert store.count_predictions(conn, "Test Event", "US30", event.event_time_utc) == 1
            conn.close()
    print("PASS\n")


def test_failed_calendar_fetch_returns_none_without_crashing():
    print("=== accumulator: a failed calendar fetch returns None and does not crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(accumulator, "fetch_calendar", side_effect=Exception("network down")):
            result = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path)
            assert result is None
    print("PASS\n")


if __name__ == "__main__":
    test_first_snapshot_taken_immediately_second_only_in_final_snapshot_window()
    test_high_impact_only_no_medium_widening()
    test_failed_scoring_for_one_pair_does_not_stop_others()
    test_article_bundle_fetched_once_per_event_not_per_instrument()
    test_failed_calendar_fetch_returns_none_without_crashing()
    print("All backtest_accumulator tests passed.")
