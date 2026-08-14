"""
Tests for webapp.store — uses a temp SQLite file, no network needed.
"""
import sys
import os
import tempfile
import datetime as dt
import sqlite3
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import webapp.store as store
from webapp.store import (
    get_connection, record_run, get_latest_two, get_history,
    add_tracked_symbol, remove_tracked_symbol, list_tracked_symbols,
    get_calendar_snapshot, save_calendar_snapshot_if_changed,
)
from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent


def test_round_trip_and_diff():
    print("=== store: two runs for the same (symbol, event) round-trip and diff correctly ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)

        event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
        t1 = dt.datetime(2026, 8, 5, 10, 0, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2026, 8, 5, 10, 15, tzinfo=dt.timezone.utc)

        record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.54, "bullish", 0.20, scored_at_utc=t1)
        record_run(conn, "XAUUSD", "Non-Farm Employment Change", event_time, 0.66, "bullish", 0.35, scored_at_utc=t2)

        runs = get_latest_two(conn, "XAUUSD", "Non-Farm Employment Change")
        assert len(runs) == 2
        assert runs[0].probability == 0.66, "most recent run should come first"
        assert runs[1].probability == 0.54

        delta = runs[0].probability - runs[1].probability
        assert abs(delta - 0.12) < 1e-9
        print(f"  latest={runs[0].probability:.0%} previous={runs[1].probability:.0%} delta={delta:+.0%}")

        history = get_history(conn, "XAUUSD", "Non-Farm Employment Change")
        assert len(history) == 2
        assert history[0].probability == 0.54, "history should be oldest-first"
        conn.close()
    print("PASS\n")


def test_fewer_than_two_runs():
    print("=== store: only one run recorded returns one row, not a crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
        record_run(conn, "XAUUSD", "CPI", event_time, 0.5, "neutral", 0.0)
        runs = get_latest_two(conn, "XAUUSD", "CPI")
        assert len(runs) == 1
        conn.close()
    print("PASS\n")


def test_pending_run_round_trips_with_null_probability():
    print("=== store: a pending run (probability=None, direction='pending', raw_score=None) round-trips ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)

        record_run(conn, "XAUUSD", "Core PCE Price Index m/m", event_time, probability=None, direction="pending", raw_score=None)

        runs = get_latest_two(conn, "XAUUSD", "Core PCE Price Index m/m")
        assert len(runs) == 1
        assert runs[0].probability is None
        assert runs[0].direction == "pending"
        assert runs[0].raw_score is None
        conn.close()
    print("PASS\n")


def test_get_latest_two_breaks_identical_scored_at_ties_by_id():
    print("=== store: get_latest_two/get_history break scored_at_utc ties by insertion (id), not undefined SQLite order ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 7, 12, 30, tzinfo=dt.timezone.utc)
        # Same scored_at_utc for both rows — e.g. a scheduler cycle that
        # stamps every run with one shared "now" value. Without an id
        # tiebreaker, ORDER BY scored_at_utc DESC alone has no guaranteed
        # order among ties; which row get_latest_two() calls "most recent"
        # would be left to SQLite's whim rather than actual insertion order.
        tied_time = dt.datetime(2026, 8, 5, 10, 0, tzinfo=dt.timezone.utc)
        record_run(conn, "XAUUSD", "CPI", event_time, 0.50, "bullish", 0.10, scored_at_utc=tied_time)
        record_run(conn, "XAUUSD", "CPI", event_time, 0.60, "bullish", 0.20, scored_at_utc=tied_time)

        runs = get_latest_two(conn, "XAUUSD", "CPI")
        assert runs[0].probability == 0.60, "the LATER-inserted row must win the tie, not an arbitrary SQLite order"
        assert runs[1].probability == 0.50

        history = get_history(conn, "XAUUSD", "CPI")
        assert history[0].probability == 0.50, "history must stay oldest-inserted-first on a tie"
        assert history[1].probability == 0.60
        conn.close()
    print("PASS\n")


def test_tracked_symbols_add_remove_list():
    print("=== store: tracked symbols add/remove/list round-trip, duplicates ignored ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)

        add_tracked_symbol(conn, "XAUUSD")
        add_tracked_symbol(conn, "EURUSD")
        add_tracked_symbol(conn, "XAUUSD")  # duplicate, should not error or double-add
        assert list_tracked_symbols(conn) == ["EURUSD", "XAUUSD"]

        remove_tracked_symbol(conn, "EURUSD")
        assert list_tracked_symbols(conn) == ["XAUUSD"]
        conn.close()
    print("PASS\n")


def _fake_calendar_event(title="CPI m/m", forecast="0.2%", actual=None):
    return EconomicEvent(
        title=title, country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast=forecast, actual=actual,
    )


def _fake_event(title="CPI m/m", event_time_utc=None, forecast="0.2%", actual=None):
    """Helper for creating fake EconomicEvent with customizable title and time."""
    return EconomicEvent(
        title=title, country="USD", impact="High",
        event_time_utc=event_time_utc or dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast=forecast, actual=actual,
    )


def test_calendar_snapshot_round_trips_and_is_none_before_first_fetch():
    print("=== store: calendar_snapshot round-trips, and is None before any fetch has ever succeeded ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        assert get_calendar_snapshot(conn) is None, "nothing persisted yet — must be None, not an empty snapshot"

        fetched_at = dt.datetime(2026, 8, 10, 20, 0, tzinfo=dt.timezone.utc)
        changed = save_calendar_snapshot_if_changed(conn, [_fake_calendar_event()], fetched_at)
        assert changed is True

        snapshot = get_calendar_snapshot(conn)
        assert snapshot is not None
        assert len(snapshot.events) == 1
        assert snapshot.events[0]["title"] == "CPI m/m"
        assert snapshot.events[0]["forecast"] == "0.2%"
        assert snapshot.fetched_at_utc == fetched_at.isoformat()
        conn.close()
    print("PASS\n")


def test_calendar_snapshot_unchanged_fetch_does_not_touch_the_stored_row():
    print("=== store: a fetch returning IDENTICAL data does not update the stored snapshot, not even the timestamp ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        t1 = dt.datetime(2026, 8, 10, 20, 0, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2026, 8, 10, 21, 0, tzinfo=dt.timezone.utc)  # a later fetch, same data

        assert save_calendar_snapshot_if_changed(conn, [_fake_calendar_event()], t1) is True
        changed = save_calendar_snapshot_if_changed(conn, [_fake_calendar_event()], t2)
        assert changed is False, "identical event data is not new information — must not count as a change"

        snapshot = get_calendar_snapshot(conn)
        assert snapshot.fetched_at_utc == t1.isoformat(), "timestamp must stay at the ORIGINAL fetch, not bump on a no-op fetch"
        conn.close()
    print("PASS\n")


def test_calendar_snapshot_updates_when_data_actually_changes():
    print("=== store: a fetch returning genuinely different data DOES update the stored snapshot ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        t1 = dt.datetime(2026, 8, 10, 20, 0, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2026, 8, 10, 21, 0, tzinfo=dt.timezone.utc)

        save_calendar_snapshot_if_changed(conn, [_fake_calendar_event(forecast="0.2%")], t1)
        changed = save_calendar_snapshot_if_changed(conn, [_fake_calendar_event(forecast="0.3%")], t2)
        assert changed is True, "a real forecast revision IS new information — must update"

        snapshot = get_calendar_snapshot(conn)
        assert snapshot.events[0]["forecast"] == "0.3%"
        assert snapshot.fetched_at_utc == t2.isoformat()
        conn.close()
    print("PASS\n")


def test_upsert_event_history_creates_row_on_first_sight():
    print("=== store: upsert_event_history creates a row with forecast/previous, actual still NULL, on first sight ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
            forecast="0.3%", previous="0.4%", actual=None,
        )
        now = dt.datetime(2026, 8, 5, 9, 0, tzinfo=UTC_TZ)
        store.upsert_event_history(conn, event, surprise_direction=None, now=now)

        rows = store.get_event_history(conn, "CPI m/m")
        assert len(rows) == 1
        assert rows[0].forecast == "0.3%"
        assert rows[0].previous == "0.4%"
        assert rows[0].actual is None
        assert rows[0].surprise_direction is None
        conn.close()
    print("PASS\n")


def test_upsert_event_history_fills_actual_on_later_sight_without_clobbering_forecast():
    print("=== store: a later upsert (post-release) fills actual/surprise_direction, leaves forecast/previous untouched ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        pre_event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
            forecast="0.3%", previous="0.4%", actual=None,
        )
        store.upsert_event_history(conn, pre_event, surprise_direction=None, now=dt.datetime(2026, 8, 5, 9, 0, tzinfo=UTC_TZ))

        post_event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
            forecast="0.3%", previous="0.4%", actual="0.5%",
        )
        store.upsert_event_history(conn, post_event, surprise_direction="higher", now=dt.datetime(2026, 8, 12, 13, 0, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "CPI m/m")
        assert len(rows) == 1
        assert rows[0].forecast == "0.3%"
        assert rows[0].previous == "0.4%"
        assert rows[0].actual == "0.5%"
        assert rows[0].surprise_direction == "higher"
        conn.close()
    print("PASS\n")


def test_upsert_event_history_stale_refetch_does_not_blank_actual():
    print("=== store: a stale re-fetch with actual=None never blanks a previously-recorded actual ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        released = EconomicEvent(
            title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
            forecast="0.3%", previous="0.4%", actual="0.5%",
        )
        store.upsert_event_history(conn, released, surprise_direction="higher", now=dt.datetime(2026, 8, 12, 13, 0, tzinfo=UTC_TZ))

        stale_refetch = EconomicEvent(
            title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
            forecast="0.3%", previous="0.4%", actual=None,
        )
        store.upsert_event_history(conn, stale_refetch, surprise_direction=None, now=dt.datetime(2026, 8, 12, 13, 5, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "CPI m/m")
        assert rows[0].actual == "0.5%"
        assert rows[0].surprise_direction == "higher"
        conn.close()
    print("PASS\n")


def test_get_event_history_multiple_occurrences_most_recent_first_and_limit():
    print("=== store: get_event_history returns occurrences most-recent-first, capped at limit ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        for month, actual in [(6, "0.5%"), (7, "0.4%"), (8, "0.6%")]:
            event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                forecast="0.3%", previous="0.3%", actual=actual,
            )
            store.upsert_event_history(conn, event, surprise_direction="higher", now=dt.datetime(2026, month, 12, 13, 0, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "CPI m/m", limit=2)
        assert len(rows) == 2
        assert rows[0].event_time_utc.startswith("2026-08")
        assert rows[1].event_time_utc.startswith("2026-07")
        conn.close()
    print("PASS\n")


def test_get_event_history_unknown_title_returns_empty_list():
    print("=== store: get_event_history for a title with no history returns an empty list, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        rows = store.get_event_history(conn, "Nonexistent Event")
        assert rows == []
        conn.close()
    print("PASS\n")


def test_get_resolved_event_history_only_returns_rows_with_actual():
    print("=== store: get_resolved_event_history only returns rows where actual is set, across ALL titles ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        resolved = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
            forecast="0.1%", previous="-0.4%", actual="0.1%",
        )
        pending = EconomicEvent(
            title="Core CPI m/m", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
            forecast="0.2%", previous="0.0%", actual=None,
        )
        store.upsert_event_history(conn, resolved, "in_line", now=dt.datetime(2026, 8, 12, 13, 0, tzinfo=UTC_TZ))
        store.upsert_event_history(conn, pending, None, now=dt.datetime(2026, 8, 12, 4, 0, tzinfo=UTC_TZ))

        rows = store.get_resolved_event_history(conn)
        assert len(rows) == 1
        assert rows[0].event_title == "CPI m/m"
        conn.close()
    print("PASS\n")


def test_get_resolved_event_history_most_recent_first_and_limit():
    print("=== store: get_resolved_event_history orders most-recent-first, respects limit ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        for month, title in [(6, "CPI m/m"), (7, "PPI m/m"), (8, "NFP")]:
            event = EconomicEvent(
                title=title, country="USD", impact="High",
                event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                forecast="0.1%", previous="0.1%", actual="0.2%",
            )
            store.upsert_event_history(conn, event, "higher", now=dt.datetime(2026, month, 12, 13, 0, tzinfo=UTC_TZ))

        rows = store.get_resolved_event_history(conn, limit=2)
        assert len(rows) == 2
        assert rows[0].event_title == "NFP"
        assert rows[1].event_title == "PPI m/m"
        conn.close()
    print("PASS\n")


def test_get_text_only_resolved_events_requires_both_forecast_and_actual_null():
    print("=== store: get_text_only_resolved_events only returns rows with BOTH forecast and actual NULL, past events only ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 12, 15, 0, tzinfo=UTC_TZ)

        text_only_past = EconomicEvent(
            title="FOMC Statement", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2),
            forecast=None, previous=None, actual=None,
        )
        numeric_event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2),
            forecast="0.1%", previous="-0.4%", actual="0.1%",
        )
        text_only_future = EconomicEvent(
            title="FOMC Press Conference", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=2),
            forecast=None, previous=None, actual=None,
        )
        store.upsert_event_history(conn, text_only_past, None, now=now)
        store.upsert_event_history(conn, numeric_event, "in_line", now=now)
        store.upsert_event_history(conn, text_only_future, None, now=now)

        rows = store.get_text_only_resolved_events(conn, now=now)
        assert len(rows) == 1
        assert rows[0].event_title == "FOMC Statement"
        conn.close()
    print("PASS\n")


def test_get_text_only_resolved_events_excludes_event_missing_only_one_field():
    print("=== store: an event with forecast set but actual null is NOT text-only (partial data, not genuinely numberless) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 12, 15, 0, tzinfo=UTC_TZ)
        partial = EconomicEvent(
            title="Advance GDP q/q", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2),
            forecast="2.1%", previous="2.0%", actual=None,
        )
        store.upsert_event_history(conn, partial, None, now=now)

        rows = store.get_text_only_resolved_events(conn, now=now)
        assert rows == []
        conn.close()
    print("PASS\n")


def test_upsert_event_history_defaults_to_live_source():
    print("=== webapp/store: upsert_event_history defaults source='live' when not passed ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event = _fake_event(title="CPI m/m", event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ))
        store.upsert_event_history(conn, event, "higher_bullish", dt.datetime(2026, 8, 12, 13, 0, tzinfo=UTC_TZ))
        rows = store.get_event_history(conn, "CPI m/m")
        assert rows[0].source == "live"
        conn.close()
    print("PASS\n")


def test_upsert_event_history_accepts_explicit_seeded_source():
    print("=== webapp/store: upsert_event_history(source='seeded') is stored and read back ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event = _fake_event(title="CPI m/m", event_time_utc=dt.datetime(2026, 1, 13, 12, 30, tzinfo=UTC_TZ))
        store.upsert_event_history(conn, event, "higher_bullish", dt.datetime(2026, 1, 13, 13, 0, tzinfo=UTC_TZ), source="seeded")
        rows = store.get_event_history(conn, "CPI m/m")
        assert rows[0].source == "seeded"
        conn.close()
    print("PASS\n")


def test_get_connection_migrates_preexisting_db_missing_source_column():
    print("=== webapp/store: get_connection() adds the source column to a pre-existing DB file that predates it ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        # Simulate a pre-migration DB: create event_history WITHOUT the source column.
        raw_conn = sqlite3.connect(db_path)
        raw_conn.execute("""
            CREATE TABLE event_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_title TEXT NOT NULL,
                event_time_utc TEXT NOT NULL,
                forecast TEXT, previous TEXT, actual TEXT, surprise_direction TEXT,
                recorded_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL,
                UNIQUE(event_title, event_time_utc)
            )
        """)
        raw_conn.execute(
            "INSERT INTO event_history (event_title, event_time_utc, recorded_at_utc, updated_at_utc) "
            "VALUES ('Old Event', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        raw_conn.commit()
        raw_conn.close()

        conn = store.get_connection(db_path)  # must not raise, must add the column
        rows = store.get_event_history(conn, "Old Event")
        assert rows[0].source == "live"  # pre-existing row backfilled to 'live' via the column's DEFAULT
        conn.close()
    print("PASS\n")


def test_get_connection_fresh_db_has_source_column_no_error():
    print("=== webapp/store: get_connection() on a brand-new DB (source already in CREATE TABLE) does not error on the migration step ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)  # fresh DB, schema already has source — migration must be a safe no-op
        conn2 = store.get_connection(db_path)  # second open — must also be a safe no-op
        conn.close()
        conn2.close()
    print("PASS\n")


def test_get_events_with_stale_missing_actual_respects_grace_period():
    print("=== webapp/store: get_events_with_stale_missing_actual only returns events past the grace period with actual still None ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 14, 12, 0, tzinfo=UTC_TZ)

        recent_event = _fake_event(title="CPI m/m", event_time_utc=now - dt.timedelta(hours=2))  # too recent
        stale_event = _fake_event(title="PPI m/m", event_time_utc=now - dt.timedelta(hours=48))  # past grace period
        resolved_event = _fake_event(title="Retail Sales m/m", event_time_utc=now - dt.timedelta(hours=48))
        resolved_event.actual = "0.3%"

        store.upsert_event_history(conn, recent_event, None, now)
        store.upsert_event_history(conn, stale_event, None, now)
        store.upsert_event_history(conn, resolved_event, "higher_bullish", now)

        stale = store.get_events_with_stale_missing_actual(conn, now, grace_period_hours=6)
        titles = {r.event_title for r in stale}
        assert titles == {"PPI m/m"}  # recent_event too fresh, resolved_event already has an actual
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_round_trip_and_diff()
    test_fewer_than_two_runs()
    test_pending_run_round_trips_with_null_probability()
    test_get_latest_two_breaks_identical_scored_at_ties_by_id()
    test_tracked_symbols_add_remove_list()
    test_calendar_snapshot_round_trips_and_is_none_before_first_fetch()
    test_calendar_snapshot_unchanged_fetch_does_not_touch_the_stored_row()
    test_calendar_snapshot_updates_when_data_actually_changes()
    test_upsert_event_history_creates_row_on_first_sight()
    test_upsert_event_history_fills_actual_on_later_sight_without_clobbering_forecast()
    test_upsert_event_history_stale_refetch_does_not_blank_actual()
    test_get_event_history_multiple_occurrences_most_recent_first_and_limit()
    test_get_event_history_unknown_title_returns_empty_list()
    test_get_resolved_event_history_only_returns_rows_with_actual()
    test_get_resolved_event_history_most_recent_first_and_limit()
    test_get_text_only_resolved_events_requires_both_forecast_and_actual_null()
    test_get_text_only_resolved_events_excludes_event_missing_only_one_field()
    test_upsert_event_history_defaults_to_live_source()
    test_upsert_event_history_accepts_explicit_seeded_source()
    test_get_connection_migrates_preexisting_db_missing_source_column()
    test_get_connection_fresh_db_has_source_column_no_error()
    test_get_events_with_stale_missing_actual_respects_grace_period()
    print("All store tests passed.")
