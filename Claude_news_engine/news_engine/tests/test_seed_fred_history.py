"""
Tests for scripts/seed_fred_history.py (B8 Task 2) — FRED/ALFRED 2026 seed.
Temp DBs and a fake `requests.get` only: no network, no FRED key, no live DB.
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer import fred_history as fh
from scoring import backtest_store as bs
from scripts import seed_fred_history as seed
from tests.test_fred_history import FakeRequests, FakeResp, _init_obs
from webapp import store as ws

D = dt.date
UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _db(tmp_path):
    return ws.get_connection(tmp_path / "d.db")


def _row(conn, title, when, forecast=None, previous=None, actual=None, country="USD", impact="High", source="live"):
    conn.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), forecast, previous, actual, None, when.isoformat(), when.isoformat(), source, impact, country),
    )
    conn.commit()


def _count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM event_history").fetchone()[0]


def _cpi_fake():
    """One CPI release on 2026-10-14: Sep m/m 0.6% (Aug m/m 0.4% in the same vintage)."""
    return FakeRequests(
        initial={"CPIAUCSL": [_init_obs(D(2026, 9, 1), D(2026, 10, 14))]},
        vintages={("CPIAUCSL", "2026-10-14"): {D(2026, 7, 1): 321.713, D(2026, 8, 1): 323.000, D(2026, 9, 1): 324.938}},
    )


def _client(fake, monkeypatch):
    monkeypatch.setattr(fh, "requests", fake)
    return fh.FredClient("KEY", pace_seconds=0)


def _run(conn, client, **kw):
    kw.setdefault("titles", ["CPI m/m"])
    return seed.run_seed(conn, client, NOW, **kw)


def test_seed_dry_run_writes_nothing(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    client = _client(_cpi_fake(), monkeypatch)
    changes = conn.total_changes
    report = _run(conn, client, apply=False, allow_unverified=True)
    assert conn.total_changes == changes
    assert _count(conn) == 0
    assert report.inserted == [("CPI m/m", "2026-10-14T12:30:00+00:00")]   # planned, not written
    assert "DRY RUN" in seed.format_report(report, apply=False)
    assert "DRY RUN" not in seed.format_report(report, apply=True)


def test_seed_apply_inserts_missing_release_with_first_print(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    client = _client(_cpi_fake(), monkeypatch)
    _run(conn, client, apply=True, allow_unverified=True)
    row = conn.execute("SELECT * FROM event_history WHERE event_title = 'CPI m/m'").fetchone()
    assert row["event_time_utc"] == "2026-10-14T12:30:00+00:00"
    assert row["actual"] == "0.6%"
    assert row["previous"] == "0.4%"
    assert row["forecast"] is None
    assert row["source"] == "fred"
    assert row["country"] == "USD"
    assert row["impact"] is None
    assert row["surprise_direction"] is None


def test_seed_event_time_uses_new_york_release_time(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    fake = FakeRequests(
        initial={
            "CPIAUCSL": [_init_obs(D(2025, 12, 1), D(2026, 1, 13))],
            "ADPMNUSNERSA": [_init_obs(D(2026, 6, 1), D(2026, 7, 1))],
        },
        vintages={
            ("CPIAUCSL", "2026-01-13"): {D(2025, 11, 1): 320.0, D(2025, 12, 1): 321.0},
            ("ADPMNUSNERSA", "2026-07-01"): {D(2026, 5, 1): 130_000_000.0, D(2026, 6, 1): 130_150_000.0},
        },
    )
    client = _client(fake, monkeypatch)
    seed.run_seed(conn, client, NOW, apply=True, allow_unverified=True,
                  titles=["CPI m/m", "ADP Non-Farm Employment Change"])
    times = {r["event_title"]: r["event_time_utc"] for r in conn.execute("SELECT * FROM event_history")}
    assert times["CPI m/m"] == "2026-01-13T13:30:00+00:00"                       # EST: UTC-5
    assert times["ADP Non-Farm Employment Change"] == "2026-07-01T12:15:00+00:00"  # EDT: UTC-4


def test_seed_rerun_adds_zero_rows(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    client = _client(_cpi_fake(), monkeypatch)
    first = _run(conn, client, apply=True, allow_unverified=True)
    assert len(first.inserted) == 1
    n = _count(conn)
    # Second run: the seeded row now agrees with FRED, so the title is verified without the flag.
    second = _run(conn, client, apply=True)
    assert second.inserted == [] and second.filled == []
    assert _count(conn) == n


def test_seed_skips_release_with_row_within_3_days(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, "CPI m/m", dt.datetime(2026, 10, 15, 12, 30, tzinfo=UTC), forecast="0.3%", previous="0.4%")
    client = _client(_cpi_fake(), monkeypatch)
    report = _run(conn, client, apply=True)
    assert report.inserted == []
    assert _count(conn) == 1
    row = conn.execute("SELECT * FROM event_history").fetchone()
    assert row["actual"] == "0.6%"
    assert row["forecast"] == "0.3%" and row["previous"] == "0.4%"
    assert row["surprise_direction"] == "higher"
    assert row["source"] == "fred"
    assert report.title_status["CPI m/m"] == "verified"


def test_seed_null_country_row_is_ambiguous(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, "CPI m/m", dt.datetime(2026, 10, 14, 1, 30, tzinfo=UTC), forecast="0.3%", country=None)
    client = _client(_cpi_fake(), monkeypatch)
    report = _run(conn, client, apply=True, allow_unverified=True)
    assert report.inserted == [] and report.filled == []
    assert _count(conn) == 1
    assert conn.execute("SELECT actual FROM event_history").fetchone()[0] is None
    assert any("ambiguous existing row" in s for s in report.skipped)


def test_seed_non_usd_row_is_ignored_as_absent(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, "CPI m/m", dt.datetime(2026, 10, 14, 6, 0, tzinfo=UTC), forecast="0.3%", country="CAD")
    client = _client(_cpi_fake(), monkeypatch)
    report = _run(conn, client, apply=True, allow_unverified=True)
    assert len(report.inserted) == 1
    assert conn.execute("SELECT COUNT(*) FROM event_history WHERE country = 'USD'").fetchone()[0] == 1
    assert conn.execute("SELECT actual FROM event_history WHERE country = 'CAD'").fetchone()[0] is None


def test_seed_suspect_title_not_written(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    for when in (dt.datetime(2026, 9, 11, 12, 30, tzinfo=UTC), dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)):
        _row(conn, "CPI m/m", when, actual="0.4%")
    fake = FakeRequests(
        initial={
            "CPIAUCSL": [_init_obs(D(2026, 7, 1), D(2026, 8, 12)), _init_obs(D(2026, 8, 1), D(2026, 9, 11)),
                         _init_obs(D(2026, 9, 1), D(2026, 10, 14))],
            "UNRATE": [_init_obs(D(2026, 9, 1), D(2026, 10, 2))],
        },
        vintages={
            ("CPIAUCSL", "2026-08-12"): {D(2026, 5, 1): 319.0, D(2026, 6, 1): 320.0, D(2026, 7, 1): 321.0},
            ("CPIAUCSL", "2026-09-11"): {D(2026, 6, 1): 320.0, D(2026, 7, 1): 321.0, D(2026, 8, 1): 323.9},
            ("CPIAUCSL", "2026-10-14"): {D(2026, 7, 1): 321.0, D(2026, 8, 1): 323.9, D(2026, 9, 1): 326.8},
            ("UNRATE", "2026-10-02"): {D(2026, 8, 1): 4.2, D(2026, 9, 1): 4.3},
        },
    )
    client = _client(fake, monkeypatch)
    report = seed.run_seed(conn, client, NOW, apply=True, allow_unverified=True,
                           titles=["CPI m/m", "Unemployment Rate"])
    assert report.title_status["CPI m/m"] == "suspect"
    assert report.agreement["CPI m/m"] == (0, 2)
    assert conn.execute("SELECT COUNT(*) FROM event_history WHERE event_title = 'CPI m/m'").fetchone()[0] == 2
    assert all(t != "CPI m/m" for t, _ in report.inserted + report.filled)
    ur = conn.execute("SELECT * FROM event_history WHERE event_title = 'Unemployment Rate'").fetchone()
    assert ur["actual"] == "4.3%"          # other titles still written


def test_seed_unverified_title_needs_flag(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    client = _client(_cpi_fake(), monkeypatch)
    report = _run(conn, client, apply=True)
    assert report.title_status["CPI m/m"] == "unverified"
    assert _count(conn) == 0 and report.inserted == []
    _run(conn, client, apply=True, allow_unverified=True)
    assert _count(conn) == 1


def test_seed_fetch_error_marks_title_unavailable(tmp_path, monkeypatch):
    class Err(FakeRequests):
        def get(self, url, params=None, timeout=None):
            return FakeResp(status=500, text="boom")

    conn = _db(tmp_path)
    client = _client(Err(), monkeypatch)
    report = _run(conn, client, apply=True, allow_unverified=True)
    assert report.title_status["CPI m/m"] == "unavailable"
    assert _count(conn) == 0


def test_seed_fill_skipped_when_previous_mismatches(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, "CPI m/m", dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC), forecast="0.3%", previous="0.9%")
    client = _client(_cpi_fake(), monkeypatch)
    report = _run(conn, client, apply=True, allow_unverified=True)
    assert report.filled == []
    assert conn.execute("SELECT actual FROM event_history").fetchone()[0] is None
    assert any("previous mismatch" in s for s in report.skipped)


def test_seed_aborts_on_maintenance(tmp_path, monkeypatch, capsys):
    class Maint(FakeRequests):
        def get(self, url, params=None, timeout=None):
            return FakeResp(status=200, text="<html><body>FRED is down for maintenance</body></html>")

    conn = _db(tmp_path)
    _row(conn, "CPI m/m", dt.datetime(2026, 9, 11, 12, 30, tzinfo=UTC), forecast="0.3%")
    conn.close()
    monkeypatch.setattr(fh, "requests", Maint())
    monkeypatch.setattr(seed, "FRED_API_KEY", "KEY")
    rc = seed.main(["--db", str(tmp_path / "d.db"), "--apply", "--pace", "0"])
    assert rc == 3
    assert "FRED under maintenance" in capsys.readouterr().out
    assert _count(sqlite3.connect(tmp_path / "d.db")) == 1
    assert list(tmp_path.glob("d.db.pre_b8_*")) == []


def test_seed_missing_key_exits_without_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(seed, "FRED_API_KEY", "")
    assert seed.main(["--db", str(tmp_path / "d.db"), "--apply"]) == 2
    assert not (tmp_path / "d.db").exists()      # nothing created either


def test_seed_apply_makes_backup_first(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, "Unemployment Rate", dt.datetime(2026, 3, 6, 13, 30, tzinfo=UTC), actual="4.1%")
    client = _client(_cpi_fake(), monkeypatch)
    paths = []

    def before():
        paths.append(seed.backup_db(tmp_path / "d.db", NOW))

    _run(conn, client, apply=True, allow_unverified=True, before_first_write=before)
    backup = tmp_path / "d.db.pre_b8_2026-10-27"
    assert paths == [backup] and backup.exists()
    assert _count(sqlite3.connect(backup)) == 1          # pre-seed row count
    assert _count(conn) == 2
    # A second backup the same day never overwrites the first.
    assert seed.backup_db(tmp_path / "d.db", NOW) == tmp_path / "d.db.pre_b8_2026-10-27_2"


def test_seed_no_backup_when_nothing_to_write(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    client = _client(FakeRequests(), monkeypatch)
    called = []
    _run(conn, client, apply=True, allow_unverified=True, before_first_write=lambda: called.append(1))
    assert called == []


def test_seed_reports_new_release_minutes(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    client = _client(_cpi_fake(), monkeypatch)
    assert _run(conn, client, allow_unverified=True).new_release_minutes == 1
    # Another USD title already printed at that minute -> the reaction job already has it.
    _row(conn, "Core CPI m/m", dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC), forecast="0.3%")
    assert _run(conn, client, allow_unverified=True).new_release_minutes == 0


def test_seeded_rows_do_not_break_stats_or_trend(tmp_path, monkeypatch):
    from webapp import stats_service
    from webapp.trend import summarize_trend

    conn = _db(tmp_path)
    client = _client(_cpi_fake(), monkeypatch)
    _run(conn, client, apply=True, allow_unverified=True)
    bt = bs.get_connection(":memory:")
    rows = stats_service.build_rows(conn, bt, event_title="CPI m/m")
    assert len(rows) == 1
    assert rows[0].status == "not_scoreable"
    assert isinstance(summarize_trend(ws.get_event_history(conn, "CPI m/m")), str)
