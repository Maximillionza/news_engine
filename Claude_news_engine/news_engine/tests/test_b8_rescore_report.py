"""
Tests for scripts/b8_rescore_report.py -- B8 (2026-10-27) read-only re-score
report: which recorded essence calls would change direction under the
standardized surprise. Temp DB files only, no network.
"""
import sys
import os
import datetime as dt
import sqlite3
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import b8_rescore_report as report
import webapp.store as store

UTC = dt.timezone.utc
RELEASE = dt.datetime(2026, 10, 22, 12, 30, tzinfo=UTC)
CLAIMS_PRIORS = [("225K", "215K"), ("220K", "215K"), ("202K", "209K"), ("210K", "206K"), ("208K", "203K"), ("205K", "206K")]


def _row(conn, title, when, forecast, actual, country="USD") -> None:
    store.insert_event_history_if_absent(conn, title, when, forecast, None, actual, None, "live", "Medium", country, when)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "d.db"
    conn = store.get_connection(path)
    for k, (f, a) in enumerate(CLAIMS_PRIORS, start=1):
        _row(conn, "Unemployment Claims", RELEASE - dt.timedelta(days=7 * k), f, a)
    _row(conn, "Unemployment Claims", RELEASE, "225K", "226K")
    # Rows that must never be reported: non-USD, and a title with no surprise direction.
    _row(conn, "Unemployment Claims", RELEASE, "225K", "300K", country="GBP")
    _row(conn, "CPI m/m", RELEASE, "0.3%", "0.9%", country="GBP")
    _row(conn, "JOLTS Job Openings", RELEASE, "7.2M", "7.6M")
    conn.close()
    return path


def _rescore(path: Path):
    conn = report.open_readonly(path)
    try:
        return report.rescore_rows(conn)
    finally:
        conn.close()


def test_small_claims_miss_changes_direction(db_path):
    rows = {r.event_time_utc: r for r in _rescore(db_path) if r.title == "Unemployment Claims"}
    row = rows[RELEASE.isoformat()]
    assert row.old_dirs == {"XAUUSD": "neutral", "US30": "neutral"}
    assert row.old_score == pytest.approx(-0.013333, abs=1e-6)  # USD score; XAUUSD (inverse) is +0.013333
    assert row.new_dirs == {"XAUUSD": "bullish", "US30": "bullish"}
    assert row.new_score == pytest.approx(-0.084718, abs=1e-6)
    assert row.method == "z"
    assert row.z == pytest.approx(0.169842, abs=1e-5)
    assert row.n_prior == 6
    assert row.changed is True


def test_early_rows_use_fallback_and_do_not_change(db_path):
    rows = [r for r in _rescore(db_path) if r.title == "Unemployment Claims" and r.event_time_utc != RELEASE.isoformat()]
    assert len(rows) == 6
    assert all(r.method == "fallback" and r.sigma is None and r.z is None for r in rows)
    assert all(not r.changed and r.old_dirs == r.new_dirs for r in rows)


def test_report_lists_direction_changes(db_path):
    rows = _rescore(db_path)
    generated = dt.datetime(2026, 10, 27, 10, 0, tzinfo=UTC)
    text = report.render_report(rows, generated, "d.db")
    assert "Direction changes" in text
    section = text.split("Direction changes", 1)[1]
    assert "Unemployment Claims" in section
    assert "2026-10-22 14:30 SAST" in text and "2026-10-22T12:30" in text
    assert "read-only" in text
    # With no changes the section says so.
    unchanged = [r for r in rows if not r.changed]
    assert "No direction changes." in report.render_report(unchanged, generated, "d.db")


def test_report_opens_read_only(db_path, tmp_path):
    conn = report.open_readonly(db_path)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute(
            "INSERT INTO event_history (event_title, event_time_utc, recorded_at_utc, updated_at_utc) "
            "VALUES ('x', 'y', 'z', 'z')"
        )
    conn.close()
    before = db_path.read_bytes()
    out = tmp_path / "out.md"
    assert report.main(["--db", str(db_path), "--out", str(out)]) == 0
    assert db_path.read_bytes() == before
    assert out.read_bytes().count(b"\r\n") > 0 and b"\n" not in out.read_bytes().replace(b"\r\n", b"")


def test_non_usd_and_unmapped_rows_excluded(db_path):
    rows = _rescore(db_path)
    titles = {r.title for r in rows}
    assert titles == {"Unemployment Claims"}
    assert len(rows) == 7  # 6 priors + the 226K row; neither the GBP claims row nor the GBP CPI row
    text = report.render_report(rows, dt.datetime(2026, 10, 27, 10, 0, tzinfo=UTC), "d.db")
    assert "JOLTS" not in text and "CPI m/m" not in text
    assert b"\x08" not in Path(report.__file__).read_bytes()
