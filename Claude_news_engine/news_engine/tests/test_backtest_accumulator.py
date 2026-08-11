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
             patch.object(accumulator, "score_bundle", side_effect=[
                 _fake_result(probability=0.7, direction=Direction.BULLISH),   # cycle 1
                 _fake_result(probability=0.85, direction=Direction.BULLISH),  # cycle 4 — materially stronger, must record
             ]):

            # Cycle 1: 20h out, first snapshot should be taken (nothing to compare against yet).
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1

            # Cycle 2: still 20h out (not near window) — second check must NOT even happen yet.
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1, "should not check again outside the near window"

            # Cycle 3: 2h out — outside the accumulator's own, much tighter
            # FINAL_SNAPSHOT_WINDOW_HOURS (30 min) — the final check must
            # NOT fire this early (this is the exact gap the old
            # shared-with-webapp.scheduler-threshold behavior had).
            still_too_early = event.event_time_utc - dt.timedelta(hours=2)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=still_too_early)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1, \
                "must not check merely for being inside a wider scheduler-style window"

            # Cycle 4: now genuinely close to the event, and the score moved
            # materially (0.7 -> 0.85, +15pp) — second snapshot recorded.
            near_now = event.event_time_utc - dt.timedelta(minutes=20)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 2

            # Cycle 5: budget exhausted (2 RECORDED snapshots reached), must
            # not take a 3rd even still in the final window.
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 2, "budget cap must hold"
            conn.close()
    print("PASS\n")


def test_unchanged_score_is_checked_but_not_recorded():
    print("=== accumulator: a re-check within the final window that finds NO material change is not recorded, but still checked ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", side_effect=[
                 _fake_result(probability=0.70, direction=Direction.BULLISH),  # cycle 1
                 _fake_result(probability=0.74, direction=Direction.BULLISH),  # cycle 2 — same direction, only +4pp, below threshold
             ]) as mock_score:

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1

            near_now = event.event_time_utc - dt.timedelta(minutes=20)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert mock_score.call_count == 2, "the second cycle must still fetch+score — supporting articles are checked, not skipped"
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1, \
                "a sub-threshold same-direction move is supporting, not material — must not be recorded"

            latest = store.get_latest_prediction(conn, "Test Event", "XAUUSD")
            assert latest.probability == 0.70, "the stored prediction must remain the ORIGINAL, unreplaced by the unrecorded check"
            conn.close()
    print("PASS\n")


def test_direction_flip_is_always_recorded_regardless_of_magnitude():
    print("=== accumulator: a direction flip is always material, even with a tiny probability change ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", side_effect=[
                 _fake_result(probability=0.55, direction=Direction.BULLISH),  # cycle 1
                 _fake_result(probability=0.56, direction=Direction.BEARISH),  # cycle 2 — tiny probability move, but direction FLIPPED
             ]):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)

            near_now = event.event_time_utc - dt.timedelta(minutes=20)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 2, \
                "a direction flip must always be recorded, regardless of how small the probability move is"
            latest = store.get_latest_prediction(conn, "Test Event", "XAUUSD")
            assert latest.direction == "bearish"
            conn.close()
    print("PASS\n")


def test_is_material_change_threshold_boundary():
    print("=== accumulator: _is_material_change — same-direction moves at/above 10pp are material, below are not ===")
    # Exactly at the threshold — material (>= , not strictly >).
    assert accumulator._is_material_change("bullish", 0.75, "bullish", 0.65) is True
    # Just under the threshold — not material.
    assert accumulator._is_material_change("bullish", 0.7499, "bullish", 0.65) is False
    # A direction flip is material regardless of magnitude, even a near-zero move.
    assert accumulator._is_material_change("bearish", 0.6501, "bullish", 0.65) is True
    # Identical direction and probability — not material.
    assert accumulator._is_material_change("bullish", 0.65, "bullish", 0.65) is False
    print("PASS\n")


def test_precursor_events_found_and_passed_to_score_bundle():
    print("=== accumulator: an already-released precursor event (e.g. PPI before CPI) is found and blended into scoring ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        # "CPI m/m" is a real key in config.settings.PRECURSOR_EVENTS,
        # mapped to ["PPI m/m", "Core PPI m/m", "Import Prices m/m"] —
        # using a real title so find_precursor_events()'s real config
        # lookup actually matches, not a mocked stand-in.
        target = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=20), forecast="0.2%", actual=None,
        )
        precursor = EconomicEvent(
            title="Core PPI m/m", country="USD", impact="Medium",
            event_time_utc=now - dt.timedelta(hours=5), forecast="0.2%", actual="0.4%",  # already released
        )
        unrelated = EconomicEvent(
            title="Some Unrelated Report", country="USD", impact="Low",
            event_time_utc=now - dt.timedelta(hours=3), forecast="1.0%", actual="1.0%",
        )

        with patch.object(accumulator, "fetch_calendar", return_value=[target, precursor, unrelated]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: [e for e in events if e.impact == "High"]), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=target, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()) as mock_score:

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            mock_score.assert_called_once()
            _, kwargs = mock_score.call_args
            assert "precursor_events" in kwargs, "score_bundle must be called with precursor_events, not left at its None default"
            precursors_passed = kwargs["precursor_events"]
            assert len(precursors_passed) == 1, f"expected exactly the PPI precursor (Medium impact, real actual, before target), got {precursors_passed}"
            assert precursors_passed[0].title == "Core PPI m/m"
    print("PASS\n")


def test_precursor_events_uses_unfiltered_calendar_not_high_impact_only():
    print("=== accumulator: precursor lookup uses the FULL unfiltered calendar, not the High-impact-only filtered list ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        target = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=20), forecast="0.2%", actual=None,
        )
        # Medium impact — filter_relevant_events() (High-only) would drop
        # this from the SCORING candidate list, but it must still be found
        # as a precursor, since find_precursor_events() is explicitly
        # supposed to search the full calendar (precursors are typically
        # Medium impact, per the module's own established convention).
        precursor = EconomicEvent(
            title="PPI m/m", country="USD", impact="Medium",
            event_time_utc=now - dt.timedelta(hours=5), forecast="0.2%", actual="0.5%",
        )

        with patch.object(accumulator, "fetch_calendar", return_value=[target, precursor]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: [e for e in events if e.impact == "High"]), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=target, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()) as mock_score:

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            _, kwargs = mock_score.call_args
            titles_passed = [e.title for e in kwargs["precursor_events"]]
            assert "PPI m/m" in titles_passed, "Medium-impact precursor must still be found via the full unfiltered calendar"
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

        def flaky_score_bundle(bundle, instrument, precursor_events=None):
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
    test_unchanged_score_is_checked_but_not_recorded()
    test_direction_flip_is_always_recorded_regardless_of_magnitude()
    test_is_material_change_threshold_boundary()
    test_precursor_events_found_and_passed_to_score_bundle()
    test_precursor_events_uses_unfiltered_calendar_not_high_impact_only()
    test_high_impact_only_no_medium_widening()
    test_failed_scoring_for_one_pair_does_not_stop_others()
    test_article_bundle_fetched_once_per_event_not_per_instrument()
    test_failed_calendar_fetch_returns_none_without_crashing()
    print("All backtest_accumulator tests passed.")
