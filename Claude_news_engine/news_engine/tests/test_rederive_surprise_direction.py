"""FIX task 2: scripts/rederive_surprise_direction.py re-labels event_history only."""
import datetime as dt
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from scripts import rederive_surprise_direction as rederive_script
import webapp.store as store

OLD_STAMP = "2026-08-12T12:35:00+00:00"
NOW = dt.datetime(2026, 11, 4, 8, 0, tzinfo=UTC_TZ)


def _seed(db_path: Path) -> None:
    """Rows: 4.1 vs 4.2 stored in_line (old 5% band), an exact hit, an untracked title, an unparsable pair, a NULL-labelled row."""
    conn = store.get_connection(db_path)
    rows = [
        ("CPI m/m", "2026-08-12T12:30:00+00:00", "4.2%", "4.0%", "4.1%", "in_line", "bls"),
        ("CPI m/m", "2026-09-12T12:30:00+00:00", "0.3%", "0.3%", "0.3%", "in_line", "live"),
        ("Some Untracked Indicator", "2026-08-12T12:30:00+00:00", "0.3%", "0.3%", "0.5%", None, "live"),
        ("CPI m/m", "2026-07-12T12:30:00+00:00", "n/a", "0.3%", "0.4%", "higher", "live"),
        ("Unemployment Claims", "2026-08-13T12:30:00+00:00", "194K", "190K", "200K", None, "live"),
        ("CPI m/m", "2026-10-12T12:30:00+00:00", "0.3%", "0.3%", None, None, "live"),
    ]
    for title, when, forecast, previous, actual, label, source in rows:
        conn.execute(
            "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
            "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (title, when, forecast, previous, actual, label, OLD_STAMP, OLD_STAMP, source, "High", "USD"),
        )
    conn.commit()
    conn.close()


def _dump(db_path: Path) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT id, event_title, event_time_utc, forecast, previous, actual, surprise_direction, source, updated_at_utc "
            "FROM event_history ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


def test_rederive_changes_only_the_label() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "dashboard.db"
        _seed(db)
        before = _dump(db)
        assert rederive_script.main(["--db", str(db), "--apply"]) == 0
        after = _dump(db)
        assert len(before) == len(after)
        for old, new in zip(before, after):
            # id, title, time, forecast, previous, actual and source never change
            assert old[:6] == new[:6] and old[7] == new[7]
            if old[6] != new[6]:
                assert new[8] != OLD_STAMP
            else:
                assert new[8] == OLD_STAMP
        labels = {(row[1], row[2][:7]): row[6] for row in after}
        assert labels[("CPI m/m", "2026-08")] == "lower"        # 4.1 vs 4.2: one tick
        assert labels[("CPI m/m", "2026-09")] == "in_line"      # exact hit stays in line
        assert labels[("Unemployment Claims", "2026-08")] == "higher"   # NULL -> higher


def test_rederive_dry_run_opens_read_only(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "dashboard.db"
        _seed(db)
        before = _dump(db)
        assert rederive_script.main(["--db", str(db)]) == 0
        assert _dump(db) == before
        out = capsys.readouterr().out
        assert "CPI m/m" in out and "in_line -> lower: 1" in out
        assert "dry run" in out and "SAST" in out
        # The dry-run connection really is read-only.
        conn = rederive_script._open(db, read_only=True)
        try:
            try:
                conn.execute("UPDATE event_history SET actual = '9'")
                raise AssertionError("write succeeded on a read-only connection")
            except sqlite3.OperationalError:
                pass
        finally:
            conn.close()


def test_rederive_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "dashboard.db"
        _seed(db)
        conn = rederive_script._open(db, read_only=False)
        first = rederive_script.rederive(conn, NOW, apply=True)
        second = rederive_script.rederive(conn, NOW, apply=True)
        conn.close()
        assert first.writes == 2 and first.changed == 2
        assert second.writes == 0 and second.changed == 0


def test_rederive_leaves_untracked_and_unparsable_rows_null() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "dashboard.db"
        _seed(db)
        rederive_script.main(["--db", str(db), "--apply"])
        labels = {(row[1], row[2][:7]): row[6] for row in _dump(db)}
        assert labels[("Some Untracked Indicator", "2026-08")] is None
        assert labels[("CPI m/m", "2026-07")] == "higher"      # unparsable forecast: label kept, not blanked
        assert labels[("CPI m/m", "2026-10")] is None          # no actual yet


def test_rederive_exit_codes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert rederive_script.main(["--db", str(Path(tmp) / "missing.db")]) == 2
        db = Path(tmp) / "dashboard.db"
        _seed(db)
        assert rederive_script.main(["--db", str(db), "--report", str(Path(tmp) / "nope")]) == 4
        assert rederive_script.main(["--apply"]) == 2
        report_dir = Path(tmp) / "reports"
        report_dir.mkdir()
        assert rederive_script.main(["--db", str(db), "--report", str(report_dir)]) == 0
        assert len(list(report_dir.glob("rederive_surprise_direction_*.txt"))) == 1
