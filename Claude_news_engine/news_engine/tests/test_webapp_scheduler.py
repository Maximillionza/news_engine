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


def test_run_scoring_cycle_records_event_history_for_every_usd_event():
    print("=== scheduler: run_scoring_cycle records event_history for every USD event, not just tracked-symbol matches ===")
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


def test_run_scoring_cycle_confirms_a_matching_macro_calendar_row():
    print("=== scheduler: run_scoring_cycle confirms a macro_calendar row with FF's real exact time (the 'micro lens') ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 9, 11, 12, 30, tzinfo=UTC_TZ),
            forecast="0.3%", previous="0.4%", actual=None,
        )
        with patch.object(store, "DB_PATH", db_path):
            conn = store.get_connection(db_path)
            now = dt.datetime.now(dt.timezone.utc)
            store.upsert_macro_calendar_event(conn, "CPI m/m", "2026-09-11", None, "unconfirmed", now)
            conn.close()

            with patch.object(scheduler, "fetch_calendar", return_value=[event]):
                scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        conn = store.get_connection(db_path)
        rows = store.get_macro_calendar_events(conn, "2026-09-01", "2026-09-30")
        assert len(rows) == 1
        assert rows[0].confirmed is True
        assert rows[0].confirmed_event_time_utc == event.event_time_utc.isoformat()
        conn.close()
    print("PASS\n")


def test_run_scoring_cycle_fills_actual_from_fred_when_ff_has_none():
    print("=== scheduler: run_scoring_cycle fills event_history.actual from FRED when FF's own actual is still None ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        past_event = EconomicEvent(
            title="Core PCE Price Index m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2), forecast="0.2%", previous="0.1%", actual=None,
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[past_event]), \
             patch.object(scheduler, "get_actual_from_fred", return_value="0.2%") as mock_fred, \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        mock_fred.assert_called_once_with("Core PCE Price Index m/m", past_event.event_time_utc)
        conn = store.get_connection(db_path)
        rows = store.get_event_history(conn, "Core PCE Price Index m/m")
        assert len(rows) == 1
        assert rows[0].actual == "0.2%"
        assert rows[0].source == "fred"
        conn.close()
    print("PASS\n")


def test_run_scoring_cycle_does_not_call_fred_when_ff_already_has_actual():
    print("=== scheduler: run_scoring_cycle does not call FRED at all when FF's own actual is already present ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        resolved_event = EconomicEvent(
            title="Core PCE Price Index m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2), forecast="0.2%", previous="0.1%", actual="0.2%",
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[resolved_event]), \
             patch.object(scheduler, "get_actual_from_fred") as mock_fred, \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        mock_fred.assert_not_called()
    print("PASS\n")


def test_run_scoring_cycle_does_not_call_fred_for_a_future_event():
    print("=== scheduler: run_scoring_cycle does not call FRED for an event that hasn't released yet ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        future_event = EconomicEvent(
            title="Core PCE Price Index m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=2), forecast="0.2%", previous="0.1%", actual=None,
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[future_event]), \
             patch.object(scheduler, "get_actual_from_fred") as mock_fred, \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        mock_fred.assert_not_called()
    print("PASS\n")


def test_run_scoring_cycle_does_not_write_when_fred_also_has_nothing():
    print("=== scheduler: run_scoring_cycle leaves the event pending when FRED returns None too ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime.now(dt.timezone.utc)
        past_event = EconomicEvent(
            title="Core PCE Price Index m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2), forecast="0.2%", previous="0.1%", actual=None,
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[past_event]), \
             patch.object(scheduler, "get_actual_from_fred", return_value=None), \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        conn = store.get_connection(db_path)
        rows = store.get_event_history(conn, "Core PCE Price Index m/m")
        assert len(rows) == 1
        assert rows[0].actual is None
        conn.close()
    print("PASS\n")


def test_run_scoring_cycle_writes_history_for_low_impact_usd_event_but_does_not_score_it():
    print("=== run_scoring_cycle: a Low-impact USD event gets an event_history row but is NEVER passed to score_event_for_symbol ===")
    low_event = EconomicEvent(
        title="Housing Starts", country="USD", impact="Low",
        event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ),
        forecast="1.35M", previous="1.32M", actual=None,
    )
    with patch.object(scheduler, "fetch_calendar", return_value=[low_event]), \
         patch.object(scheduler, "save_calendar_snapshot_if_changed") as mock_save, \
         patch.object(scheduler, "upsert_event_history") as mock_history, \
         patch.object(scheduler, "confirm_macro_calendar_event"), \
         patch.object(scheduler, "get_actual_from_fred", return_value=None), \
         patch.object(scheduler, "get_connection"), \
         patch.object(scheduler, "get_latest_two", return_value=[]), \
         patch.object(scheduler, "record_run") as mock_record, \
         patch.object(scheduler, "classify_symbol") as mock_classify:
        mock_classify.return_value.symbol_class = "gold"
        result = scheduler.run_scoring_cycle(["XAUUSD"])

    # History IS written for the Low-impact event...
    mock_history.assert_called_once()
    assert mock_history.call_args.args[1] is low_event
    # ...but it's never scored (record_run never called), and it's not
    # part of the returned scoring-relevant event list either.
    mock_record.assert_not_called()
    assert result == []
    print("PASS\n")


def test_run_scoring_cycle_never_writes_history_for_a_non_usd_event():
    print("=== run_scoring_cycle: a non-USD event (e.g. EUR) never gets an event_history row — calendar_events is USD-only, not all_events ===")
    eur_event = EconomicEvent(
        title="German Bond Auction", country="EUR", impact="High",
        event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ),
        forecast="1.5%", previous="1.4%", actual=None,
    )
    with patch.object(scheduler, "fetch_calendar", return_value=[eur_event]), \
         patch.object(scheduler, "save_calendar_snapshot_if_changed") as mock_save, \
         patch.object(scheduler, "upsert_event_history") as mock_history, \
         patch.object(scheduler, "confirm_macro_calendar_event"), \
         patch.object(scheduler, "get_actual_from_fred", return_value=None), \
         patch.object(scheduler, "get_connection"), \
         patch.object(scheduler, "get_latest_two", return_value=[]), \
         patch.object(scheduler, "record_run") as mock_record, \
         patch.object(scheduler, "classify_symbol") as mock_classify:
        mock_classify.return_value.symbol_class = "gold"
        result = scheduler.run_scoring_cycle(["XAUUSD"])

    # calendar_events is filter_relevant_events(all_events, min_impact="Low")
    # — filter_relevant_events also enforces country == "USD" — so a
    # foreign-country event never reaches the history-writing loop at all,
    # regardless of impact tier.
    mock_history.assert_not_called()
    mock_save.assert_called_once()
    assert eur_event not in mock_save.call_args.args[1]
    mock_record.assert_not_called()
    assert result == []
    print("PASS\n")


def test_run_scoring_cycle_calendar_snapshot_includes_low_impact_but_scoring_stays_medium_plus():
    print("=== run_scoring_cycle: the persisted calendar snapshot includes Low-impact events; the returned/scored event list does not ===")
    low_event = EconomicEvent(
        title="Housing Starts", country="USD", impact="Low",
        event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ),
        forecast="1.35M", previous="1.32M", actual=None,
    )
    high_event = EconomicEvent(
        title="ISM Manufacturing PMI", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 9, 2, 14, 0, tzinfo=UTC_TZ),
        forecast="55.2", previous="55.6", actual=None,
    )
    with patch.object(scheduler, "fetch_calendar", return_value=[low_event, high_event]), \
         patch.object(scheduler, "save_calendar_snapshot_if_changed") as mock_save, \
         patch.object(scheduler, "upsert_event_history"), \
         patch.object(scheduler, "confirm_macro_calendar_event"), \
         patch.object(scheduler, "get_actual_from_fred", return_value=None), \
         patch.object(scheduler, "get_connection"), \
         patch.object(scheduler, "get_latest_two", return_value=[]), \
         patch.object(scheduler, "record_run"), \
         patch.object(scheduler, "classify_symbol") as mock_classify:
        mock_classify.return_value.symbol_class = "gold"
        result = scheduler.run_scoring_cycle(["XAUUSD"])

    snapshot_events = mock_save.call_args.args[1]
    assert low_event in snapshot_events and high_event in snapshot_events
    assert result == [high_event]  # scoring-relevant list excludes the Low-impact event
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
    test_run_scoring_cycle_records_event_history_for_every_usd_event()
    test_run_scoring_cycle_confirms_a_matching_macro_calendar_row()
    test_run_scoring_cycle_fills_actual_from_fred_when_ff_has_none()
    test_run_scoring_cycle_does_not_call_fred_when_ff_already_has_actual()
    test_run_scoring_cycle_does_not_call_fred_for_a_future_event()
    test_run_scoring_cycle_does_not_write_when_fred_also_has_nothing()
    test_run_scoring_cycle_writes_history_for_low_impact_usd_event_but_does_not_score_it()
    test_run_scoring_cycle_never_writes_history_for_a_non_usd_event()
    test_run_scoring_cycle_calendar_snapshot_includes_low_impact_but_scoring_stays_medium_plus()
    print("All scheduler tests passed.")


# --- B4 Task 4: macro calendar refresh + heartbeat in the scheduler iteration ---

def test_iteration_heartbeats_and_refreshes_macro_on_success():
    with patch.object(scheduler, "run_scoring_cycle", return_value=[]), \
         patch.object(scheduler, "touch_heartbeat") as hb, \
         patch.object(scheduler, "maybe_refresh_macro_calendar") as macro:
        interval, prev = scheduler.run_scheduler_iteration(lambda: ["XAUUSD"], None)
    hb.assert_called_once_with("calendar_refresh")
    macro.assert_called_once()
    assert interval == scheduler.FAR_INTERVAL_SECONDS
    assert prev == []


def test_iteration_on_failed_fetch_refreshes_macro_but_does_not_heartbeat():
    sentinel = [object()]
    with patch.object(scheduler, "run_scoring_cycle", return_value=None), \
         patch.object(scheduler, "touch_heartbeat") as hb, \
         patch.object(scheduler, "maybe_refresh_macro_calendar") as macro:
        interval, prev = scheduler.run_scheduler_iteration(lambda: ["XAUUSD"], sentinel)
    assert interval == scheduler.SCHEDULER_INTERVAL_SECONDS
    hb.assert_not_called()
    macro.assert_called_once()
    assert prev is sentinel  # previous_events kept across a failed fetch


def test_macro_refresh_exception_never_breaks_the_iteration():
    with patch.object(scheduler, "run_scoring_cycle", return_value=[]), \
         patch.object(scheduler, "touch_heartbeat"), \
         patch.object(scheduler, "maybe_refresh_macro_calendar", side_effect=RuntimeError("boom")):
        interval, prev = scheduler.run_scheduler_iteration(lambda: ["XAUUSD"], None)
    assert interval == scheduler.FAR_INTERVAL_SECONDS


def test_macro_refresh_retries_after_6_hours_not_every_cycle(monkeypatch):
    import scripts.refresh_macro_calendar as refresh
    t0 = dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC_TZ)
    monkeypatch.setattr(scheduler, "_macro_retry_not_before", None)
    monkeypatch.setattr(refresh, "is_due", lambda *a, **k: True)
    with patch.object(refresh, "run", return_value=0) as run:
        assert scheduler.maybe_refresh_macro_calendar(now=t0) == 0
        assert scheduler.maybe_refresh_macro_calendar(now=t0 + dt.timedelta(hours=1)) is None
        assert run.call_count == 1
        assert scheduler.maybe_refresh_macro_calendar(now=t0 + dt.timedelta(hours=6)) == 0
        assert run.call_count == 2
    # a successful run (rows written) is called every iteration; run() self-gates on is_due
    monkeypatch.setattr(scheduler, "_macro_retry_not_before", None)
    with patch.object(refresh, "run", return_value=21) as run:
        for i in range(3):
            assert scheduler.maybe_refresh_macro_calendar(now=t0 + dt.timedelta(minutes=i)) == 21
        assert run.call_count == 3
    # not due / no key (-1) leaves the retry gate alone
    with patch.object(refresh, "run", return_value=-1):
        scheduler.maybe_refresh_macro_calendar(now=t0)
    assert scheduler._macro_retry_not_before is None
    # an exception sets the gate and returns None
    with patch.object(refresh, "run", side_effect=RuntimeError("fred down")):
        assert scheduler.maybe_refresh_macro_calendar(now=t0) is None
    assert scheduler._macro_retry_not_before == t0 + dt.timedelta(hours=6)


def test_macro_refresh_prints_nothing_and_skips_run_when_not_due(capsys):
    import scripts.refresh_macro_calendar as refresh
    scheduler._macro_retry_not_before = None
    with patch.object(refresh, "is_due", return_value=False), \
         patch.object(refresh, "run") as run:
        assert scheduler.maybe_refresh_macro_calendar(
            now=dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC_TZ)) is None
    run.assert_not_called()
    assert capsys.readouterr().out == ""
    assert scheduler._macro_retry_not_before is None


def test_scheduler_backfill_runs_after_scoring():
    print("=== scheduler: actuals backfill runs after scoring, not before ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        order = []
        real_record_run = scheduler.record_run

        def spy_record_run(*a, **k):
            order.append("record_run")
            return real_record_run(*a, **k)

        def spy_backfill(*a, **k):
            order.append("backfill")
            return None

        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(scheduler, "record_run", side_effect=spy_record_run), \
             patch.object(scheduler, "start_backfill_thread", side_effect=spy_backfill):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
        assert "record_run" in order and "backfill" in order
        assert order.index("record_run") < order.index("backfill"), order
    print("PASS\n")


def _events_at(offset: dt.timedelta, actual=None):
    return [
        EconomicEvent(
            title="Non-Farm Employment Change", country="USD", impact="High",
            event_time_utc=dt.datetime.now(UTC_TZ) + offset, forecast="75K", actual=actual,
        )
    ]


def test_release_window_near_bounds():
    now = dt.datetime(2026, 10, 27, 12, 0, tzinfo=UTC_TZ)

    def near(offset, actual=None):
        event = EconomicEvent("Non-Farm Employment Change", "USD", "High", now + offset, forecast="75K", actual=actual)
        return scheduler.release_window_near([event], now)

    budget = dt.timedelta(seconds=scheduler.BACKFILL_BUDGET_SECONDS)
    assert near(dt.timedelta(minutes=30))                                  # FINAL window
    assert near(dt.timedelta(hours=1) + budget)                            # a pass started now would overrun into FINAL
    assert not near(dt.timedelta(hours=1) + budget + dt.timedelta(seconds=1))
    assert near(-dt.timedelta(minutes=scheduler.POST_RELEASE_GRACE_MINUTES))  # post-release grace cycles
    assert not near(-dt.timedelta(minutes=scheduler.POST_RELEASE_GRACE_MINUTES + 1))
    assert not near(dt.timedelta(minutes=30), actual="44K")                # resolved: nothing to protect
    assert not scheduler.release_window_near([], now) and not scheduler.release_window_near(None, now)


def test_scheduler_backfill_not_started_near_release():
    print("=== scheduler: actuals backfill is not started inside a release window ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        for offset, expect_start in ((dt.timedelta(minutes=4), False), (dt.timedelta(hours=3), True)):
            with patch.object(scheduler, "fetch_calendar", return_value=_events_at(offset)), \
                 patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
                 patch.object(scheduler, "start_backfill_thread") as start:
                scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            assert start.called is expect_start, (offset, start.called)
    print("PASS\n")


def test_scheduler_cycle_not_blocked_by_hanging_backfill():
    print("=== scheduler: a hanging FRED backfill never delays the scoring cycle ===")
    import threading
    import time
    import webapp.actuals_backfill as ab
    from data_layer.fred_history import FredClient

    started, release = threading.Event(), threading.Event()
    threads = []

    def hanging_pass(conn, client, now, **kwargs):
        started.set()
        release.wait(30)
        return ab.FillReport()

    def spy_start(*a, **k):
        thread = ab.start_backfill_thread(*a, **k)
        threads.append(thread)
        return thread

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        try:
            with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
                 patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
                 patch.object(scheduler, "start_backfill_thread", side_effect=spy_start), \
                 patch.object(ab, "default_client", return_value=FredClient("K", pace_seconds=0)), \
                 patch.object(ab, "backfill_missing_actuals", side_effect=hanging_pass):
                t0 = time.monotonic()
                events = scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
                elapsed = time.monotonic() - t0
                assert started.wait(5), "the backfill pass should have started"
                assert threads and threads[0] is not None and threads[0].is_alive()
            assert [e.title for e in events] == ["Non-Farm Employment Change"]
            assert elapsed < 5.0, f"cycle waited on the backfill ({elapsed:.1f}s)"
        finally:
            release.set()
            for thread in threads:
                if thread is not None:
                    thread.join(5)
    print("PASS\n")


def test_scheduler_cycle_survives_backfill_error():
    print("=== scheduler: a raising actuals backfill never costs the scoring cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(scheduler, "fetch_calendar", return_value=_fake_events()), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(scheduler, "start_backfill_thread", side_effect=RuntimeError("boom")):
            events = scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
            assert [e.title for e in events] == ["Non-Farm Employment Change"]
            conn = store.get_connection(db_path)
            assert store.get_event_history(conn, "Non-Farm Employment Change"), "event_history must still be written"
            assert store.get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change"), "scoring must still run"
            conn.close()
    print("PASS\n")


def test_scoring_cycle_scores_with_sigma():
    print("=== B8: the scoring cycle scores a release against the sigma of its own prior surprises ===")
    import pytest
    event_time = dt.datetime(2026, 10, 22, 12, 30, tzinfo=UTC_TZ)
    claims = EconomicEvent(
        title="Unemployment Claims", country="USD", impact="Medium",
        event_time_utc=event_time, forecast="225K", previous="210K", actual="219K",
    )
    priors = [("225K", "215K"), ("220K", "215K"), ("202K", "209K"), ("210K", "206K"), ("208K", "203K"), ("205K", "206K")]
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        for k, (forecast, actual) in enumerate(priors, start=1):
            when = event_time - dt.timedelta(days=7 * k)
            store.insert_event_history_if_absent(conn, "Unemployment Claims", when, forecast, "210K", actual, None, "live", "Medium", "USD", when)
        with patch.object(scheduler, "fetch_calendar", return_value=[claims]), \
             patch.object(scheduler, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(scheduler, "start_backfill_thread"):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)
        runs = store.get_latest_two(conn, "XAUUSD", "Unemployment Claims")
        conn.close()
    assert len(runs) == 1
    # USD +0.469575 (z-based) times XAUUSD's inverse sign; today's percent method would give -0.079830.
    assert runs[0].raw_score == pytest.approx(-0.469575, abs=1e-6)
    print("PASS\n")


def test_start_scheduler_starts_release_poller_once(monkeypatch):
    import webapp.release_poller as release_poller

    class _NoThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    calls = []
    monkeypatch.setattr(scheduler.threading, "Thread", _NoThread)        # the scoring loop must not run
    monkeypatch.setattr(release_poller, "start_release_poller", lambda *a, **k: calls.append(1))
    scheduler.start_scheduler(lambda: ["XAUUSD"])
    assert calls == [1]
