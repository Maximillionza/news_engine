"""
Tests for scripts/backfill_official_actuals.py (ACT Task 5): the dry-run-by-default
backlog backfill. Temp DBs, recorded fixtures and a fake fetch only: no network.
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from data_layer.calendar_feed import EconomicEvent, classify_surprise
from data_layer.official_actuals import bls, eia
from data_layer.official_actuals.coverage import GateResult
from data_layer.official_actuals.fetch import FetchOutcome, series_key
from data_layer.official_actuals.http import KeyInactiveError, SourceRateLimited
from data_layer.official_actuals.registry import OFFICIAL_SPECS
from scripts import backfill_official_actuals as bf
from tests.test_official_adapters import _fixture
from webapp import store as ws

UTC = dt.timezone.utc
D = dt.date
NOW = dt.datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
CPI = "CPI m/m"
FED = "Federal Funds Rate"
JOLTS = "JOLTS Job Openings"
CRUDE = "Crude Oil Inventories"
CPI_TIME = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
FED_TIME = dt.datetime(2026, 10, 28, 18, 0, tzinfo=UTC)


def _gate(*verified: str, **other: str) -> dict[str, GateResult]:
    gate = {t: GateResult("verified", 5, 5, "ok") for t in verified}
    gate.update({t: GateResult(status, 1, 5, "ok") for t, status in other.items()})
    return gate


@pytest.fixture
def conn(tmp_path):
    handle = ws.get_connection(tmp_path / "dash.db")
    yield handle
    handle.close()


def _row(conn, title: str, when: dt.datetime, forecast: Optional[str] = None, previous: Optional[str] = None,
         actual: Optional[str] = None, source: str = "live", country: str = "USD") -> int:
    stamp = when.isoformat()
    cur = conn.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, stamp, forecast, previous, actual, None, stamp, stamp, source, "High", country))
    conn.commit()
    return cur.lastrowid


def _get(conn, row_id: int):
    return conn.execute("SELECT * FROM event_history WHERE id = ?", (row_id,)).fetchone()


def _data(**series) -> dict:
    return {series_key(OFFICIAL_SPECS[title]): data for title, data in series.items()}


def _fetch(data: dict, errors: Optional[dict] = None):
    calls: list = []

    def fetch(specs, since):
        calls.append((list(specs), since))
        return FetchOutcome(dict(data), dict(errors or {}))

    fetch.calls = calls    # type: ignore[attr-defined]
    return fetch


def _cpi_data() -> dict:
    return bls.parse_bls(_fixture("bls_timeseries.json"))["CUSR0000SA0"].pct1


def _counts(report: bf.BacklogReport, title: str) -> dict[str, int]:
    return {k: v for k, v in report.per_title[title].items() if v}


def _snapshot(conn) -> list[tuple]:
    return [tuple(r) for r in conn.execute("SELECT * FROM event_history ORDER BY id").fetchall()]


def _seed_mixed(conn) -> None:
    _row(conn, CPI, CPI_TIME, "0.6%", "0.4%")
    _row(conn, FED, FED_TIME, "4.00%", "4.00%")
    _row(conn, "FOMC Member Barkin Speaks", CPI_TIME)
    _row(conn, "ISM Services PMI", CPI_TIME, "51.0", "50.0")
    _row(conn, "Industrial Production m/m", CPI_TIME, "0.1%", "0.0%")
    _row(conn, "Unemployment Rate", CPI_TIME, "4.3%", "4.3%")
    _row(conn, "Non-Farm Employment Change", CPI_TIME, "80K", "89K", actual="29K")


def _mixed_fetch():
    return _fetch(_data(**{CPI: _cpi_data(), FED: {D(2026, 10, 28): 4.0}}))


def test_dry_run_writes_nothing_and_reports_per_title(conn):
    _seed_mixed(conn)
    before = _snapshot(conn)
    report = bf.run_backlog(conn, NOW, _mixed_fetch(), _gate(CPI, FED, "Non-Farm Employment Change",
                                                              **{"Unemployment Rate": "suspect"}))
    assert _counts(report, CPI) == {"would fill": 1}
    assert _counts(report, FED) == {"would fill": 1}
    assert _counts(report, "FOMC Member Barkin Speaks") == {"no actual expected": 1}
    assert _counts(report, "ISM Services PMI") == {"proprietary": 1}
    assert _counts(report, "Industrial Production m/m") == {"not mapped": 1}
    assert _counts(report, "Unemployment Rate") == {"gate disabled": 1}
    assert _counts(report, "Non-Farm Employment Change") == {"already filled": 1}
    totals = report.totals()
    assert totals["would fill"] == 2 and totals["filled"] == 0
    assert _snapshot(conn) == before


def test_apply_fills_first_writer_wins_and_rerun_writes_zero(conn):
    cpi_id = _row(conn, CPI, CPI_TIME, "0.6%", "0.4%")
    fed_id = _row(conn, FED, FED_TIME, "4.00%", "4.00%")
    gate = _gate(CPI, FED)
    report = bf.run_backlog(conn, NOW, _mixed_fetch(), gate, apply=True)
    assert report.totals()["filled"] == 2
    cpi, fed = _get(conn, cpi_id), _get(conn, fed_id)
    assert (cpi["actual"], cpi["source"]) == ("0.6%", "bls")
    assert (fed["actual"], fed["source"]) == ("4.00%", "fed")
    for row, title, release in ((cpi, CPI, CPI_TIME), (fed, FED, FED_TIME)):
        event = EconomicEvent(title, "USD", "High", release, forecast=row["forecast"], previous=row["previous"],
                              actual=row["actual"])
        assert row["surprise_direction"] == classify_surprise(event)
    again = bf.run_backlog(conn, NOW, _mixed_fetch(), gate, apply=True)
    assert again.totals()["filled"] == 0
    assert again.totals()["already filled"] == 2
    assert _get(conn, cpi_id)["actual"] == "0.6%"


def test_apply_never_overwrites_an_existing_actual(conn):
    row_id = _row(conn, CPI, CPI_TIME, "0.6%", "0.4%", actual="0.9%", source="live")
    bf.run_backlog(conn, NOW, _mixed_fetch(), _gate(CPI), apply=True)
    row = _get(conn, row_id)
    assert (row["actual"], row["source"]) == ("0.9%", "live")


def test_backlog_reports_revised_since_release(conn):
    old = _row(conn, JOLTS, dt.datetime(2026, 9, 1, 14, 0, tzinfo=UTC), "7.20M", "7.10M")
    new = _row(conn, JOLTS, dt.datetime(2026, 9, 29, 14, 0, tzinfo=UTC), "7.20M", "7.10M")
    fetch = _fetch(_data(**{JOLTS: {D(2026, 7, 1): 7000.0, D(2026, 8, 1): 7230.0}}))
    report = bf.run_backlog(conn, NOW, fetch, _gate(JOLTS), apply=True)
    assert _counts(report, JOLTS) == {"revised since release": 1, "filled": 1}
    assert _get(conn, old)["actual"] is None
    assert _get(conn, new)["actual"] == "7.23M"


def _crude_rows(conn, later_previous: str) -> None:
    _row(conn, CRUDE, dt.datetime(2026, 10, 14, 14, 30, tzinfo=UTC), "-0.1M", "-3.0M")
    _row(conn, CRUDE, dt.datetime(2026, 10, 21, 14, 30, tzinfo=UTC), "-0.1M", "-8.6M")
    _row(conn, CRUDE, dt.datetime(2026, 10, 28, 14, 30, tzinfo=UTC), "-0.1M", later_previous)


def test_unrevised_series_fills_older_rows_when_ff_previous_agrees(conn):
    crude = eia.parse_eia_weekly(_fixture("eia_crude.json"))
    _crude_rows(conn, "-3.1M")
    report = bf.run_backlog(conn, NOW, _fetch(_data(**{CRUDE: crude})), _gate(CRUDE))
    assert _counts(report, CRUDE) == {"would fill": 3}


def test_unrevised_series_disagreeing_ff_previous_is_not_filled(conn):
    crude = eia.parse_eia_weekly(_fixture("eia_crude.json"))
    _crude_rows(conn, "-2.0M")
    report = bf.run_backlog(conn, NOW, _fetch(_data(**{CRUDE: crude})), _gate(CRUDE))
    assert _counts(report, CRUDE) == {"would fill": 2, "disagrees with FF previous": 1}


def test_awaiting_publication_when_period_missing(conn):
    _row(conn, CPI, CPI_TIME, "0.6%", "0.4%")
    stale = {p: v for p, v in _cpi_data().items() if p < D(2026, 9, 1)}
    report = bf.run_backlog(conn, NOW, _fetch(_data(**{CPI: stale})), _gate(CPI))
    assert _counts(report, CPI) == {"awaiting publication": 1}


def test_source_error_and_key_inactive_outcomes(conn):
    _row(conn, CPI, CPI_TIME, "0.6%", "0.4%")
    _row(conn, "Retail Sales m/m", CPI_TIME, "0.4%", "0.3%")
    _row(conn, "Prelim UoM Consumer Sentiment", CPI_TIME, "55.0", "54.0")
    gate = _gate(CPI, "Retail Sales m/m", **{"Housing Starts": "key_inactive"})
    _row(conn, "Housing Starts", CPI_TIME, "1.30M", "1.31M")
    errors = {"bls": SourceRateLimited("x"), "census": KeyInactiveError("x")}
    report = bf.run_backlog(conn, NOW, _fetch({}, errors), gate)
    assert _counts(report, CPI) == {"source error": 1}
    assert _counts(report, "Retail Sales m/m") == {"key inactive": 1}     # the census fetch raised KeyInactiveError
    assert _counts(report, "Housing Starts") == {"key inactive": 1}       # gate said key_inactive


def test_fetch_exception_is_a_source_error_without_writes(conn):
    row_id = _row(conn, CPI, CPI_TIME, "0.6%", "0.4%")

    def boom(specs, since):
        raise RuntimeError("https://example.invalid/?key=SECRET")

    report = bf.run_backlog(conn, NOW, boom, _gate(CPI), apply=True)
    assert _counts(report, CPI) == {"source error": 1}
    assert _get(conn, row_id)["actual"] is None


def test_title_filter_and_since(conn):
    _seed_mixed(conn)
    report = bf.run_backlog(conn, NOW, _mixed_fetch(), _gate(CPI, FED), titles=[CPI])
    assert set(report.per_title) == {CPI}
    report = bf.run_backlog(conn, NOW, _mixed_fetch(), _gate(CPI, FED), since=D(2026, 10, 20))
    assert FED in report.per_title and CPI not in report.per_title


def test_rows_inside_the_sla_window_are_not_touched(conn):
    _row(conn, FED, NOW - dt.timedelta(minutes=5), "4.00%", "4.00%")
    report = bf.run_backlog(conn, NOW, _mixed_fetch(), _gate(FED))
    assert report.per_title == {}


# ---------------------------------------------------------------- report and main

def test_report_shows_sast_and_totals(conn):
    _seed_mixed(conn)
    report = bf.run_backlog(conn, NOW, _mixed_fetch(), _gate(CPI, FED))
    text = bf.format_report(report, apply=False)
    assert "DRY RUN" in text
    assert "2026-10-14 14:30 SAST (stored 2026-10-14T12:30:00+00:00)" in text     # SAST = UTC+2
    assert "totals: would fill 2" in text
    assert bf.LIMITATION in text
    assert "totals: filled 0" in bf.format_report(bf.BacklogReport(), apply=True)


def _main_env(tmp_path, monkeypatch):
    db = tmp_path / "dash.db"
    handle = ws.get_connection(db)
    row_id = _row(handle, CPI, CPI_TIME, "0.6%", "0.4%")
    handle.close()
    monkeypatch.setattr(bf, "_default_fetch", lambda env_file: _fetch(_data(**{CPI: _cpi_data()})))
    monkeypatch.setattr(bf, "load_gate_results", lambda: _gate(CPI))
    uris: list[str] = []
    real = sqlite3.connect

    def spy(target, *args, **kwargs):
        uris.append(str(target))
        return real(target, *args, **kwargs)

    monkeypatch.setattr(bf.sqlite3, "connect", spy)
    return db, row_id, uris


def _actual(db, row_id) -> Optional[str]:
    check = sqlite3.connect(db)
    try:
        return check.execute("SELECT actual FROM event_history WHERE id = ?", (row_id,)).fetchone()[0]
    finally:
        check.close()


def test_main_dry_run_opens_db_read_only(tmp_path, monkeypatch, capsys):
    db, row_id, uris = _main_env(tmp_path, monkeypatch)
    assert bf.main(["--db", str(db)]) == 0
    assert uris and all(u.endswith("mode=ro") for u in uris)
    assert _actual(db, row_id) is None
    assert "would fill 1" in capsys.readouterr().out


def test_main_apply_writes_and_report_file(tmp_path, monkeypatch, capsys):
    db, row_id, uris = _main_env(tmp_path, monkeypatch)
    report_path = tmp_path / "report.txt"
    assert bf.main(["--db", str(db), "--apply", "--report", str(report_path)]) == 0
    assert uris and all(u.endswith("mode=rw") for u in uris)
    assert _actual(db, row_id) == "0.6%"
    assert "totals: filled 1" in report_path.read_text(encoding="utf-8")


def test_main_exit_codes(tmp_path, monkeypatch, capsys):
    assert bf.main(["--db", str(tmp_path / "missing.db")]) == 2
    db, _, _ = _main_env(tmp_path, monkeypatch)
    assert bf.main(["--db", str(db), "--report", str(tmp_path / "nope" / "r.txt")]) == 4
    assert bf.main(["--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "database not found" in out and "report folder not found" in out
