"""
Tests for scripts/run_accumulator.py — its instrument list now comes from
the dashboard's own live tracked_symbols table (2026-09-13), not
config.settings.INSTRUMENTS. Uses a temp SQLite file, no network needed.
"""
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.run_accumulator as run_accumulator
import webapp.store as store


def test_main_reads_tracked_symbols_from_the_dashboard_db_not_config_settings_instruments():
    print("=== run_accumulator.main(): reads config.settings.INSTRUMENTS' successor -- the dashboard's own tracked_symbols table -- so a symbol never hand-entered in the old config still gets scored ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAGUSD")  # silver -- never in config.settings.INSTRUMENTS
            conn.close()

            # main() proceeds past start_accumulator() into an infinite
            # `while True: time.sleep(3600)` keep-alive loop (see the
            # module's own comment on why) -- patched here to raise
            # immediately, same as a real Ctrl-C, so the test returns.
            with patch.object(run_accumulator, "start_accumulator") as mock_start, \
                 patch.object(run_accumulator.time, "sleep", side_effect=KeyboardInterrupt):
                run_accumulator.main()

        mock_start.assert_called_once_with(["XAGUSD"])
    print("PASS\n")


def test_main_reports_and_returns_early_when_no_symbols_are_tracked():
    print("=== run_accumulator.main(): an empty tracked_symbols table reports plainly and never calls start_accumulator() -- no silent hang, no crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(store, "DB_PATH", db_path):
            store.get_connection(db_path).close()  # creates the schema, zero tracked symbols

            with patch.object(run_accumulator, "start_accumulator") as mock_start:
                run_accumulator.main()

        mock_start.assert_not_called()
    print("PASS\n")


if __name__ == "__main__":
    test_main_reads_tracked_symbols_from_the_dashboard_db_not_config_settings_instruments()
    test_main_reports_and_returns_early_when_no_symbols_are_tracked()
    print("All run_accumulator tests passed.")
