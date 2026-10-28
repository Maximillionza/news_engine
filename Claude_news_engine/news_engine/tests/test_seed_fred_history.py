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


# --- B8 final-review fixes (2026-10-28) ---------------------------------------------------------


def _graded(conn, title, when, direction="higher"):
    conn.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), "0.3%", "0.2%", "0.4%", direction, when.isoformat(), when.isoformat(),
         "live", "High", "USD"),
    )
    conn.commit()


def test_rollback_deletes_only_this_runs_seed_inserts(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    client = _client(_cpi_fake(), monkeypatch)
    report = _run(conn, client, apply=True, allow_unverified=True)
    key = report.run_at_utc
    assert key == NOW.isoformat() and len(report.inserted) == 1

    # A Forex Factory row that appears AFTER the apply and is later relabelled source='fred' by the
    # hourly backfill (fill_actual_if_missing) -- graded, carries forecast/previous; must survive.
    later = NOW + dt.timedelta(days=2)
    _row(conn, "Unemployment Claims", later, forecast="220K", previous="215K", impact="Medium")
    claims_id = conn.execute("SELECT id FROM event_history WHERE event_title = 'Unemployment Claims'").fetchone()[0]
    assert ws.fill_actual_if_missing(conn, claims_id, "230K", "higher", "fred", later + dt.timedelta(hours=2))

    # The same-day FRED fast path (upsert_event_history, source='fred') at the very same instant as the
    # seed run key: still kept, FF rows always carry an impact.
    from data_layer.calendar_feed import EconomicEvent
    ev = EconomicEvent("Core CPI m/m", "USD", "High", dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC),
                       forecast="0.3%", previous="0.2%", actual="0.3%")
    ws.upsert_event_history(conn, ev, "in_line", NOW, source="fred")

    # A legacy row with impact and forecast NULL that a FRED fill later relabels: own recorded_at_utc.
    _row(conn, "Retail Sales m/m", dt.datetime(2026, 3, 17, 12, 30, tzinfo=UTC), impact=None, previous="0.1%")
    legacy_id = conn.execute("SELECT id FROM event_history WHERE event_title = 'Retail Sales m/m'").fetchone()[0]
    ws.fill_actual_if_missing(conn, legacy_id, "0.5%", None, "fred", NOW)

    # A second seed run (different key) inserts its own row; a rollback of the first leaves it alone.
    _row(conn, "PPI m/m", dt.datetime(2026, 5, 14, 12, 30, tzinfo=UTC), impact=None, source="fred", actual="0.2%")
    conn.execute("UPDATE event_history SET recorded_at_utc = ? WHERE event_title = 'PPI m/m'",
                 ((NOW + dt.timedelta(hours=1)).isoformat(),))
    conn.commit()

    total = _count(conn)
    changes = conn.total_changes
    assert seed.rollback_seed_inserts(conn, key) == 1                 # dry count, writes nothing
    assert conn.total_changes == changes and _count(conn) == total
    assert seed.rollback_seed_inserts(conn, key, apply=True) == 1
    left = {r["event_title"] for r in conn.execute("SELECT event_title FROM event_history")}
    assert left == {"Unemployment Claims", "Core CPI m/m", "Retail Sales m/m", "PPI m/m"}
    assert conn.execute("SELECT actual FROM event_history WHERE event_title = 'Unemployment Claims'").fetchone()[0] == "230K"
    assert seed.rollback_seed_inserts(conn, key, apply=True) == 0     # rerun is a no-op


def test_rollback_rejects_a_key_without_offset(tmp_path):
    conn = _db(tmp_path)
    with pytest.raises(ValueError):
        seed.rollback_seed_inserts(conn, "2026-10-27T12:00:00")
    with pytest.raises(ValueError):
        seed.rollback_seed_inserts(conn, "not a time")


def test_rollback_cli_counts_read_only_then_deletes(tmp_path, monkeypatch, capsys):
    conn = _db(tmp_path)
    client = _client(_cpi_fake(), monkeypatch)
    key = _run(conn, client, apply=True, allow_unverified=True).run_at_utc
    conn.close()
    monkeypatch.setattr(seed, "FRED_API_KEY", "")                     # rollback needs no FRED access
    db = str(tmp_path / "d.db")
    assert seed.main(["--db", db, "--rollback", key]) == 0
    assert "would delete (dry run): 1" in capsys.readouterr().out
    assert _count(sqlite3.connect(db)) == 1
    assert seed.main(["--db", db, "--rollback", key, "--apply"]) == 0
    assert "deleted: 1" in capsys.readouterr().out
    assert _count(sqlite3.connect(db)) == 0
    assert seed.main(["--db", db, "--rollback", "garbage"]) == 2
    assert seed.main(["--db", str(tmp_path / "missing.db"), "--rollback", key]) == 2
    assert not (tmp_path / "missing.db").exists()


def test_apply_report_prints_run_key_and_nothing_to_write_header(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    client = _client(_cpi_fake(), monkeypatch)
    first = seed.format_report(_run(conn, client, apply=True, allow_unverified=True), apply=True)
    assert first.splitlines()[0] == "APPLIED - rows written"
    assert f"seed run recorded_at_utc (rollback key for this run's inserts): {NOW.isoformat()}" in first
    second = seed.format_report(_run(conn, client, apply=True), apply=True)
    assert second.splitlines()[0] == "APPLIED - nothing to write"
    assert "inserts: 0  fills: 0" in second                           # the string the runbook's step 7 quotes


def test_missing_report_folder_exits_before_any_fetch(tmp_path, monkeypatch, capsys):
    class Boom(FakeRequests):
        def get(self, url, params=None, timeout=None):
            raise AssertionError("no FRED request may happen")

    monkeypatch.setattr(fh, "requests", Boom())
    monkeypatch.setattr(seed, "FRED_API_KEY", "KEY")
    rc = seed.main(["--db", str(tmp_path / "d.db"), "--apply", "--report", str(tmp_path / "nope" / "r.txt")])
    assert rc == 4
    assert "--report folder does not exist" in capsys.readouterr().out
    assert not (tmp_path / "d.db").exists()


def test_trend_window_insert_pushes_graded_row_out(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    for month in range(4, 10):                                          # Apr..Sep, all graded
        _graded(conn, "CPI m/m", dt.datetime(2026, month, 10, 12, 30, tzinfo=UTC))
    client = _client(_cpi_fake(), monkeypatch)
    report = _run(conn, client, allow_unverified=True)                  # dry run
    assert report.trend_window_changes == [("CPI m/m", 6, 5)]           # seeded Oct row has no direction
    assert "  CPI m/m: 6 -> 5" in seed.format_report(report, apply=False)
    assert _count(conn) == 6                                            # simulation wrote nothing


def test_trend_window_fill_adds_graded_row(tmp_path, monkeypatch):
    conn = _db(tmp_path)
    _row(conn, "CPI m/m", dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC), forecast="0.3%", previous="0.4%")
    client = _client(_cpi_fake(), monkeypatch)
    report = _run(conn, client, allow_unverified=True)
    assert report.trend_window_changes == [("CPI m/m", 0, 1)]
    assert "no title changes" in seed.format_report(seed.SeedReport(), apply=False)
