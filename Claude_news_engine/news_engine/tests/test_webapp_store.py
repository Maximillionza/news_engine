"""
Tests for webapp.store — uses a temp SQLite file, no network needed.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.store import (
    get_connection, record_run, get_latest_two, get_history,
    add_tracked_symbol, remove_tracked_symbol, list_tracked_symbols,
)


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


if __name__ == "__main__":
    test_round_trip_and_diff()
    test_fewer_than_two_runs()
    test_tracked_symbols_add_remove_list()
    print("All store tests passed.")
