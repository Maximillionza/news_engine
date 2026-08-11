"""
Tests for webapp.scheduler — no live network, fetch_calendar is patched.
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
import webapp.store as store
import webapp.scheduler as scheduler


def _fake_events():
    return [
        EconomicEvent(
            title="Non-Farm Employment Change", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            forecast="75K", actual="44K",
        )
    ]


def _fake_pending_event():
    return [
        EconomicEvent(
            title="Non-Farm Employment Change", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            forecast="75K", actual=None,
        )
    ]


def _fake_untracked_pending_event():
    return [
        EconomicEvent(
            title="Some Untracked Indicator No One Mapped", country="USD", impact="Medium",
            event_time_utc=dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            forecast="1.0%", actual=None,
        )
    ]


def test_scoring_cycle_writes_new_rows_and_skips_duplicates():
    print("=== scheduler: writes a row on first cycle, skips an identical second cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            conn = store.get_connection(db_path)
            runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
            assert len(runs) == 1, "first cycle should write exactly one row"

            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
            assert len(runs) == 1, "second identical cycle should NOT write a duplicate row"
            conn.close()
    print("PASS\n")


def test_scoring_cycle_persists_calendar_snapshot_on_success():
    print("=== scheduler: run_scoring_cycle persists the calendar snapshot on a successful fetch, no-ops when unchanged ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):

            conn = store.get_connection(db_path)
            assert store.get_calendar_snapshot(conn) is None, "nothing persisted before the first cycle"

            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            snapshot = store.get_calendar_snapshot(conn)
            assert snapshot is not None
            assert len(snapshot.events) == 1
            first_fetched_at = snapshot.fetched_at_utc

            # Second cycle, identical event data — must NOT touch the stored
            # timestamp (webapp/store.py's save_calendar_snapshot_if_changed
            # is a no-op on unchanged data — this is the caller-side check
            # that the scheduler actually calls it with real fetched data,
            # not just that the function itself works in isolation).
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            snapshot_after = store.get_calendar_snapshot(conn)
            assert snapshot_after.fetched_at_utc == first_fetched_at, \
                "an unchanged second fetch must not bump the persisted snapshot's timestamp"
            conn.close()
    print("PASS\n")


def test_unrecognized_symbol_skipped_not_crashed():
    print("=== scheduler: an unrecognized tracked symbol is skipped, not a crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):
            scheduler.run_scoring_cycle(["NOTREAL123"], db_path=db_path)  # must not raise
    print("PASS\n")


def test_failed_calendar_fetch_does_not_crash_or_wipe_data():
    print("=== scheduler: a failed calendar fetch does not crash the loop or wipe existing data ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"

        # pre-populate the DB with one existing row + a calendar snapshot,
        # so there's something to wipe.
        conn = store.get_connection(db_path)
        store.record_run(
            conn, "XAUUSD", "Non-Farm Employment Change",
            dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ),
            0.62, "up", 1.5,
        )
        stale_fetched_at = dt.datetime(2026, 8, 9, 12, 0, tzinfo=UTC_TZ)
        store.save_calendar_snapshot_if_changed(conn, _fake_events(), stale_fetched_at)
        conn.close()

        with patch.object(scheduler, "fetch_calendar", side_effect=Exception("network down")):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)  # must not raise

        conn = store.get_connection(db_path)
        runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
        assert len(runs) == 1, "existing row must survive a failed calendar fetch"
        # A failed fetch never reaches save_calendar_snapshot_if_changed at
        # all (that call sits after the fetch_calendar try/except) — the
        # previously-persisted snapshot (however stale) must stay exactly
        # as it was, "store and use as current until new information
        # supersedes this" — a failure is not new information.
        snapshot = store.get_calendar_snapshot(conn)
        assert snapshot.fetched_at_utc == stale_fetched_at.isoformat(), \
            "a failed fetch must not touch the persisted calendar snapshot"
        conn.close()
    print("PASS\n")


def test_pending_then_released_event_produces_two_row_lifecycle():
    print("=== scheduler: pending cycle then released cycle for the SAME event yields 2 rows (pending + real) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"

        # Cycle 1: event hasn't printed an actual yet — must still be persisted as pending.
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_pending_event()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        # Cycle 2: same event, now released with a real actual value.
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        conn = store.get_connection(db_path)
        runs = store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
        conn.close()

        assert len(runs) == 2, f"expected 2 rows (pending + real), got {len(runs)}"
        newer, older = runs[0], runs[1]
        assert older.direction == "pending", f"older row should be pending, got {older.direction!r}"
        assert older.probability is None, f"older row's probability should be None, got {older.probability!r}"
        assert newer.direction != "pending", f"newer row should have a real direction, got {newer.direction!r}"
        assert newer.probability is not None, "newer row should have a real probability"
        print(f"  older: direction={older.direction} probability={older.probability}")
        print(f"  newer: direction={newer.direction} probability={newer.probability}")
    print("PASS\n")


def test_untracked_pending_event_does_not_persist_a_stuck_row():
    print("=== scheduler: a pending event whose title isn't in EVENT_SURPRISE_DIRECTION is skipped, not persisted ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_untracked_pending_event()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        conn = store.get_connection(db_path)
        runs = store.get_latest_two(conn, "XAUUSD", "Some Untracked Indicator No One Mapped")
        conn.close()
        assert len(runs) == 0, f"an untracked-title pending event must NOT be persisted, got {len(runs)} row(s)"
    print("PASS\n")


def _event_at(hours_from_now, actual=None, now=None):
    now = now or dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    return EconomicEvent(
        title="Test Event", country="USD", impact="High",
        event_time_utc=now + dt.timedelta(hours=hours_from_now),
        forecast="1.0%", actual=actual,
    )


def test_adaptive_interval_far_when_no_events_or_event_not_today():
    print("=== adaptive interval: FAR (12h baseline) when no events, or nearest is beyond RAMP_WINDOW_HOURS ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    assert scheduler.compute_adaptive_interval_seconds(None, now=now) == scheduler.FAR_INTERVAL_SECONDS
    assert scheduler.compute_adaptive_interval_seconds([], now=now) == scheduler.FAR_INTERVAL_SECONDS
    far_event = _event_at(72, now=now)  # 72h out, beyond the 24h ramp-up threshold
    assert scheduler.compute_adaptive_interval_seconds([far_event], now=now) == scheduler.FAR_INTERVAL_SECONDS
    print("PASS\n")


def test_adaptive_interval_ramps_to_hourly_on_the_day_of_the_event():
    print("=== adaptive interval: RAMP (hourly) once the event is within 24h, still more than 1h out ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    same_day_event = _event_at(20, now=now)  # inside 24h, outside the 1h final window
    assert scheduler.compute_adaptive_interval_seconds([same_day_event], now=now) == scheduler.RAMP_INTERVAL_SECONDS
    print("PASS\n")


def test_adaptive_interval_final_within_1h_or_post_release_grace():
    print("=== adaptive interval: FINAL (5min) within the final 1h, and briefly after a scheduled release ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    soon_event = _event_at(0.5, now=now)  # 30 min out, inside FINAL_WINDOW_HOURS
    assert scheduler.compute_adaptive_interval_seconds([soon_event], now=now) == scheduler.FINAL_INTERVAL_SECONDS

    just_passed_event = _event_at(-0.25, now=now)  # 15 min ago, inside the post-release grace window, no actual yet (delayed release)
    assert scheduler.compute_adaptive_interval_seconds([just_passed_event], now=now) == scheduler.FINAL_INTERVAL_SECONDS
    print("PASS\n")


def test_adaptive_interval_ignores_resolved_events():
    print("=== adaptive interval: a resolved event (actual already printed) no longer forces urgency ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    resolved_but_close = _event_at(1, actual="1.2%", now=now)  # 1h out but ALREADY has an actual — done, not urgent
    assert scheduler.compute_adaptive_interval_seconds([resolved_but_close], now=now) == scheduler.FAR_INTERVAL_SECONDS
    print("PASS\n")


def test_adaptive_interval_tightest_wins_across_multiple_events():
    print("=== adaptive interval: the tightest-demanding event across the whole list wins ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    far_event = _event_at(72, now=now)
    near_event = _event_at(0.5, now=now)
    assert scheduler.compute_adaptive_interval_seconds([far_event, near_event], now=now) == scheduler.FINAL_INTERVAL_SECONDS
    print("PASS\n")


def test_adaptive_interval_sense_check_for_a_just_rescheduled_event():
    print("=== adaptive interval: a just-rescheduled event gets an extra-tight sense check in its final 15 minutes ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    previous_time = now + dt.timedelta(hours=1)  # last seen 1h out...
    rescheduled_event = EconomicEvent(
        title="Core CPI m/m", country="USD", impact="High",
        event_time_utc=now + dt.timedelta(minutes=10),  # ...now only 10 min out — a real reschedule
        forecast="0.2%", actual=None,
    )
    previous_events = [EconomicEvent(
        title="Core CPI m/m", country="USD", impact="High",
        event_time_utc=previous_time, forecast="0.2%", actual=None,
    )]
    interval = scheduler.compute_adaptive_interval_seconds([rescheduled_event], now=now, previous_events=previous_events)
    assert interval == scheduler.SENSE_CHECK_INTERVAL_SECONDS, (
        f"a just-rescheduled event inside its final 15 minutes should get the tightest possible check, got {interval}"
    )
    print("PASS\n")


def test_adaptive_interval_no_sense_check_without_a_reschedule():
    print("=== adaptive interval: no sense check for an event that's simply close — only for a DETECTED reschedule ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    stable_event = _event_at(10 / 60, now=now)  # 10 min out, same as the rescheduled case above, but never moved
    previous_events = [EconomicEvent(
        title="Test Event", country="USD", impact="High",
        event_time_utc=stable_event.event_time_utc,  # identical to the current fetch — no reschedule
        forecast="1.0%", actual=None,
    )]
    interval = scheduler.compute_adaptive_interval_seconds([stable_event], now=now, previous_events=previous_events)
    assert interval == scheduler.FINAL_INTERVAL_SECONDS, (
        f"an event that's merely close (not rescheduled) should get the standard final-hour cadence, not the sense check, got {interval}"
    )
    print("PASS\n")


def test_adaptive_interval_reschedule_detection_is_optional():
    print("=== adaptive interval: omitting previous_events entirely just skips reschedule detection, no crash ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    soon_event = _event_at(10 / 60, now=now)
    interval = scheduler.compute_adaptive_interval_seconds([soon_event], now=now)  # no previous_events arg at all
    assert interval == scheduler.FINAL_INTERVAL_SECONDS
    print("PASS\n")


def test_run_scoring_cycle_records_event_history_for_every_event():
    print("=== scheduler: run_scoring_cycle records event_history for every fetched event, not just tracked-symbol matches ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
            forecast="0.3%", previous="0.4%", actual=None,
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[event]), \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        conn = store.get_connection(db_path)
        rows = store.get_event_history(conn, "CPI m/m")
        assert len(rows) == 1
        assert rows[0].forecast == "0.3%"
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_scoring_cycle_writes_new_rows_and_skips_duplicates()
    test_scoring_cycle_persists_calendar_snapshot_on_success()
    test_unrecognized_symbol_skipped_not_crashed()
    test_failed_calendar_fetch_does_not_crash_or_wipe_data()
    test_pending_then_released_event_produces_two_row_lifecycle()
    test_untracked_pending_event_does_not_persist_a_stuck_row()
    test_adaptive_interval_far_when_no_events_or_event_not_today()
    test_adaptive_interval_ramps_to_hourly_on_the_day_of_the_event()
    test_adaptive_interval_final_within_1h_or_post_release_grace()
    test_adaptive_interval_ignores_resolved_events()
    test_adaptive_interval_tightest_wins_across_multiple_events()
    test_adaptive_interval_sense_check_for_a_just_rescheduled_event()
    test_adaptive_interval_no_sense_check_without_a_reschedule()
    test_adaptive_interval_reschedule_detection_is_optional()
    test_run_scoring_cycle_records_event_history_for_every_event()
    print("All scheduler tests passed.")
