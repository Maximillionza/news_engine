"""
Tests for scripts/verify_official_actuals.py (ACT Task 2): the
revision-aware verification gate. Temp DBs, recorded fixtures and a fake
FRED twin only: no network, no live DB, no real key.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import os
import sqlite3
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.fred_history import FredFetchError, InitialRelease
from data_layer.official_actuals.http import HttpResponse
from data_layer.official_actuals.keys import Keys
from data_layer.official_actuals.registry import OFFICIAL_SPECS
from scripts import seed_fred_history
from scripts import verify_official_actuals as verify
from tests.test_official_adapters import FakeFetcher, _fixture, _ok, _url_has
from webapp import store as ws

D = dt.date
UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 28, 16, 0, tzinfo=UTC)


class FakeTwin:
    """Stands in for TwinReader: fixed as-of values, current values and first prints."""

    def __init__(self, asof: Optional[dict] = None, current: Optional[dict] = None,
                 releases: Optional[dict] = None) -> None:
        self.asof = asof or {}               # (series_id, period, vintage_date) -> value
        self.current = current or {}         # series_id -> {period: value}
        self.releases = releases             # series_id -> [(period, first-print date)]; None -> FRED error
        self.asof_calls: list[tuple] = []

    def value_asof(self, series_id: str, transform: str, period: dt.date, vintage_date: dt.date) -> Optional[float]:
        self.asof_calls.append((series_id, transform, period, vintage_date))
        return self.asof.get((series_id, period, vintage_date))

    def current_values(self, series_id: str, transform: str, since: dt.date, today: dt.date) -> dict:
        return dict(self.current.get(series_id, {}))

    def first_releases(self, series_id: str, start: dt.date, end: dt.date) -> list:
        if self.releases is None:
            raise FredFetchError("FRED HTTP error")
        return [InitialRelease(p, v) for p, v in self.releases.get(series_id, []) if start <= v <= end]


def _db(tmp_path):
    return ws.get_connection(tmp_path / "d.db")


def _row(conn, title, when, forecast=None, previous=None, actual=None, source="live", country="USD"):
    conn.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), forecast, previous, actual, None, when.isoformat(), when.isoformat(),
         source, "High", country),
    )
    conn.commit()


def _rows(conn, title):
    return conn.execute(
        "SELECT * FROM event_history WHERE event_title = ? AND country = 'USD' ORDER BY event_time_utc", (title,)
    ).fetchall()


def _t(y, m, d, hh=12, mm=30):
    return dt.datetime(y, m, d, hh, mm, tzinfo=UTC)


CPI = {D(2026, 6, 1): 0.3, D(2026, 7, 1): 0.1, D(2026, 8, 1): 0.4, D(2026, 9, 1): 0.6}


def test_threshold_is_b8s():
    assert verify.VERIFY_AGREEMENT_THRESHOLD is seed_fred_history.VERIFY_AGREEMENT_THRESHOLD
    assert verify.VERIFY_AGREEMENT_THRESHOLD == 0.8
    assert verify.GATE_START == D(2026, 1, 1)
    assert verify.GATE_MIN_COMPARISONS == 2
    assert verify.GATE_IDENTITY_PERIODS == 6


def test_gate_verified_when_actuals_and_previous_agree(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "CPI m/m", _t(2026, 9, 11), "0.4%", "0.1%", "0.4%", source="fred")
    _row(conn, "CPI m/m", _t(2026, 10, 14), "0.6%", "0.4%", "0.6%", source="seeded")
    _row(conn, "CPI m/m", _t(2026, 11, 12), "0.3%", "0.6%", None)          # not released yet: ignored
    gate = verify.gate_title("CPI m/m", OFFICIAL_SPECS["CPI m/m"], _rows(conn, "CPI m/m"), CPI, None, NOW)
    assert gate.status == "verified"
    assert gate.comparisons == 4 and gate.matches == 4
    assert gate.revision_explained == 0
    assert gate.identity == "none"
    assert gate.mismatches == []


def _gdp_series() -> dict:
    return {D(2025, 1, 1): 1.0, D(2025, 4, 1): 2.0, D(2025, 7, 1): 3.0, D(2025, 10, 1): 0.2,
            D(2026, 1, 1): 2.5, D(2026, 4, 1): 2.2}


def test_gate_explains_gdp_revision_with_alfred_vintage(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "Advance GDP q/q", _t(2026, 7, 30), "1.0%", "2.5%", "1.5%")
    spec = OFFICIAL_SPECS["Advance GDP q/q"]
    twin_id = spec.fred_twin[0]
    releases = {twin_id: [(D(2026, 1, 1), D(2026, 4, 30)), (D(2026, 4, 1), D(2026, 7, 30))]}
    twin = FakeTwin(asof={(twin_id, D(2026, 4, 1), D(2026, 7, 30)): 1.5}, current={twin_id: _gdp_series()},
                    releases=releases)
    gate = verify.gate_title("Advance GDP q/q", spec, _rows(conn, "Advance GDP q/q"), _gdp_series(), twin, NOW)
    assert gate.identity == "ok"
    assert gate.period_notes == []
    assert gate.revision_explained == 1
    assert (gate.matches, gate.comparisons) == (2, 2)
    assert gate.status == "verified"

    drifted = {p: v + 1.0 for p, v in _gdp_series().items()}              # twin is not the same series
    twin = FakeTwin(asof={(twin_id, D(2026, 4, 1), D(2026, 7, 30)): 1.5}, current={twin_id: drifted},
                    releases=releases)
    gate = verify.gate_title("Advance GDP q/q", spec, _rows(conn, "Advance GDP q/q"), _gdp_series(), twin, NOW)
    assert gate.identity == "mismatch"
    assert gate.revision_explained == 0
    assert (gate.matches, gate.comparisons) == (1, 2)
    assert gate.status == "suspect"


def test_gate_prelim_and_final_previous_is_the_same_quarter(tmp_path):
    # FF's Final GDP "previous" is the Prelim estimate of the SAME quarter, not the prior quarter.
    conn = _db(tmp_path)
    _row(conn, "Final GDP q/q", _t(2026, 9, 30), "1.5%", "1.5%", "2.2%")
    spec = OFFICIAL_SPECS["Final GDP q/q"]
    twin_id = spec.fred_twin[0]
    twin = FakeTwin(asof={(twin_id, D(2026, 4, 1), D(2026, 9, 29)): 1.5}, current={twin_id: _gdp_series()},
                    releases={twin_id: [(D(2026, 1, 1), D(2026, 4, 30)), (D(2026, 4, 1), D(2026, 7, 30))]})
    gate = verify.gate_title("Final GDP q/q", spec, _rows(conn, "Final GDP q/q"), _gdp_series(), twin, NOW)
    assert (gate.matches, gate.comparisons, gate.revision_explained) == (2, 2, 1)
    assert gate.status == "verified"
    assert gate.period_notes == []


# Retail Sales m/m (MPCSM, percent) as served today: the 2025 shutdown delayed the November report to
# 2026-01-14 (live row: actual 0.6%, previous -0.1%), while expected_period assigns December.
RETAIL = {D(2025, 9, 1): 0.1, D(2025, 10, 1): -0.1, D(2025, 11, 1): 0.6, D(2025, 12, 1): 0.2, D(2026, 1, 1): 0.0}


def test_gate_compares_shutdown_delayed_release_with_the_period_first_published(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "Retail Sales m/m", _t(2026, 1, 14, 13, 30), "0.4%", "-0.1%", "0.6%", source="fred")
    _row(conn, "Retail Sales m/m", _t(2026, 2, 10, 13, 30), "0.4%", "0.6%", "0.2%", source="fred")
    spec = OFFICIAL_SPECS["Retail Sales m/m"]
    rows = _rows(conn, "Retail Sales m/m")
    blind = verify.gate_title("Retail Sales m/m", spec, rows, RETAIL, None, NOW)      # the old false negative
    assert blind.status == "suspect", blind.mismatches
    twin_id = spec.fred_twin[0]
    twin = FakeTwin(releases={twin_id: [(D(2025, 11, 1), D(2026, 1, 14)), (D(2025, 12, 1), D(2026, 2, 10))]})
    gate = verify.gate_title("Retail Sales m/m", spec, rows, RETAIL, twin, NOW)
    assert (gate.matches, gate.comparisons) == (4, 4), gate.mismatches
    assert gate.status == "verified"
    assert gate.revision_explained == 0
    assert any("2026-01-14 15:30 SAST" in n and "2025-11-01" in n for n in gate.period_notes)


def test_gate_skips_row_without_a_matching_first_print(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "Retail Sales m/m", _t(2026, 1, 14, 13, 30), "0.4%", "-0.1%", "0.6%", source="fred")
    _row(conn, "Retail Sales m/m", _t(2026, 2, 10, 13, 30), "0.4%", "0.6%", "0.2%", source="fred")
    spec = OFFICIAL_SPECS["Retail Sales m/m"]
    twin_id = spec.fred_twin[0]
    # FRED shows no first print on 2026-01-14: that row is not a reference at all.
    twin = FakeTwin(releases={twin_id: [(D(2025, 12, 1), D(2026, 2, 10))]})
    gate = verify.gate_title("Retail Sales m/m", spec, _rows(conn, "Retail Sales m/m"), RETAIL, twin, NOW)
    assert (gate.matches, gate.comparisons) == (2, 2)
    assert any("skipped" in n and "2026-01-14" in n for n in gate.period_notes)
    # FRED failing (or listing nothing) keeps expected_period: the same as no twin.
    for failing in (FakeTwin(releases=None), FakeTwin(releases={})):
        gate = verify.gate_title("Retail Sales m/m", spec, _rows(conn, "Retail Sales m/m"), RETAIL, failing, NOW)
        assert gate.status == "suspect" and gate.period_notes == []


def test_released_period_rules():
    spec = OFFICIAL_SPECS["Retail Sales m/m"]
    rel = verify.released_period
    day = D(2026, 1, 14)
    assert rel(spec, day, D(2025, 12, 1), None) == D(2025, 12, 1)                       # no twin data
    assert rel(spec, day, D(2025, 12, 1), [InitialRelease(D(2025, 12, 1), day)]) == D(2025, 12, 1)
    assert rel(spec, day, D(2025, 12, 1), [InitialRelease(D(2025, 11, 1), day)]) == D(2025, 11, 1)
    late = [InitialRelease(D(2025, 11, 1), day + dt.timedelta(days=verify.TWIN_RELEASE_LAG_DAYS))]
    assert rel(spec, day, D(2025, 12, 1), late) == D(2025, 11, 1)
    too_late = [InitialRelease(D(2025, 11, 1), day + dt.timedelta(days=verify.TWIN_RELEASE_LAG_DAYS + 1))]
    assert rel(spec, day, D(2025, 12, 1), too_late) is None
    two = [InitialRelease(D(2025, 10, 1), day), InitialRelease(D(2025, 11, 1), day)]
    assert rel(spec, day, D(2025, 12, 1), two) is None                                  # ambiguous: skipped
    assert rel(spec, day, D(2025, 11, 1), two) == D(2025, 11, 1)
    # A re-estimate re-publishes the latest period first printed BEFORE the row.
    prelim = OFFICIAL_SPECS["Prelim GDP q/q"]
    gdp = [InitialRelease(D(2026, 1, 1), D(2026, 4, 30)), InitialRelease(D(2026, 4, 1), D(2026, 7, 30))]
    assert rel(prelim, D(2026, 8, 26), D(2026, 4, 1), gdp) == D(2026, 4, 1)
    assert rel(prelim, D(2026, 7, 30), D(2026, 4, 1), gdp) == D(2026, 1, 1)
    assert rel(prelim, D(2026, 3, 1), D(2025, 10, 1), gdp) is None


def test_gate_marks_wrong_scale_suspect(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "JOLTS Job Openings", _t(2026, 9, 1, 14, 0), "7.33M", "7.36M", "7.20M", source="fred")
    _row(conn, "JOLTS Job Openings", _t(2026, 9, 29, 14, 0), "7.23M", "7.20M", "7.08M", source="fred")
    series = {D(2026, 6, 1): 7360.0, D(2026, 7, 1): 7200.0, D(2026, 8, 1): 7079.0}
    right = verify.gate_title("JOLTS Job Openings", OFFICIAL_SPECS["JOLTS Job Openings"],
                              _rows(conn, "JOLTS Job Openings"), series, None, NOW)
    assert right.status == "verified", right.mismatches
    wrong_spec = dataclasses.replace(OFFICIAL_SPECS["JOLTS Job Openings"], unit_scale=1.0)
    gate = verify.gate_title("JOLTS Job Openings", wrong_spec, _rows(conn, "JOLTS Job Openings"), series, None, NOW)
    assert gate.status == "suspect"
    assert gate.matches == 0
    assert any("2026-09-29 16:00 SAST" in line for line in gate.mismatches)
    assert any("7079.00M" in line for line in gate.mismatches)


def test_gate_unverified_below_two_comparisons(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "CPI m/m", _t(2026, 10, 14), "0.6%", None, "0.6%", source="fred")
    gate = verify.gate_title("CPI m/m", OFFICIAL_SPECS["CPI m/m"], _rows(conn, "CPI m/m"), CPI, None, NOW)
    assert (gate.matches, gate.comparisons) == (1, 1)
    assert gate.status == "unverified"


def test_gate_ignores_rows_before_gate_start(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "CPI m/m", _t(2025, 12, 10), "0.3%", "9.9%", "9.9%", source="fred")
    gate = verify.gate_title("CPI m/m", OFFICIAL_SPECS["CPI m/m"], _rows(conn, "CPI m/m"), CPI, None, NOW)
    assert gate.comparisons == 0


def test_gate_skips_rows_filled_by_publisher_sources(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "CPI m/m", _t(2026, 9, 11), "0.4%", "0.1%", "9.9%", source="bls")   # our own write: not a reference
    _row(conn, "CPI m/m", _t(2026, 10, 14), "0.6%", "0.4%", None)
    gate = verify.gate_title("CPI m/m", OFFICIAL_SPECS["CPI m/m"], _rows(conn, "CPI m/m"), CPI, None, NOW)
    assert (gate.matches, gate.comparisons) == (2, 2)              # the two `previous` references only
    assert gate.status == "verified"


def test_gate_key_inactive_and_unavailable_statuses(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "Retail Sales m/m", _t(2026, 10, 15), "0.3%", "0.6%", "0.4%", source="fred")
    _row(conn, "CPI m/m", _t(2026, 10, 14), "0.6%", "0.4%", "0.6%", source="fred")
    fake = FakeFetcher([
        (_url_has("api.census.gov"), _ok(_fixture("census_missing_key.html"))),
        (_url_has("api.bls.gov"), HttpResponse(503, "", {})),
    ])
    keys = Keys(bls="K", bea="K", census="K", eia="K", fred="K")
    results = verify.run_gate(conn, NOW, fake, keys, None, titles=["Retail Sales m/m", "CPI m/m"])
    assert results["Retail Sales m/m"].status == "key_inactive"
    assert results["CPI m/m"].status == "unavailable"
    assert results["CPI m/m"].comparisons == 0
    assert results["CPI m/m"].mismatches == ["bls: SourceRateLimited"]       # class name only, never a URL or key
    assert results["Retail Sales m/m"].mismatches == ["census: KeyInactiveError"]


def test_run_gate_verifies_from_fixtures(tmp_path):
    conn = _db(tmp_path)
    _row(conn, "Crude Oil Inventories", _t(2026, 10, 21, 14, 30), "-0.1M", "-8.6M")
    _row(conn, "Crude Oil Inventories", _t(2026, 10, 28, 14, 30), "0.1M", "-3.1M")
    fake = FakeFetcher([(_url_has("api.eia.gov"), _ok(_fixture("eia_crude.json")))])
    keys = Keys(bls="K", bea="K", census="K", eia="K", fred="K")
    results = verify.run_gate(conn, NOW, fake, keys, None, titles=["Crude Oil Inventories"])
    gate = results["Crude Oil Inventories"]
    assert gate.comparisons == 2, gate.mismatches
    assert gate.status == "verified"


def test_results_json_exact_keys():
    results = {
        "CPI m/m": verify.TitleGate("verified", 4, 4, 0, "ok", []),
        "PPI m/m": verify.TitleGate("suspect", 1, 4, 0, "none", ["x"]),
    }
    payload = verify.results_to_json(results, NOW)
    assert set(payload) == {"generated_at_utc", "threshold", "titles"}
    assert payload["generated_at_utc"] == NOW.isoformat()
    assert payload["threshold"] == 0.8
    for entry in payload["titles"].values():
        assert set(entry) == {"status", "matches", "comparisons", "revision_explained", "identity", "mismatches"}
    md = verify.coverage_markdown(results)
    assert "| CPI m/m | bls | CUSR0000SA0 | verified | 4/4 | ok |" in md


def _write_env(path):
    path.write_text("BLS_API_KEY=FAKEBLSKEY987\nBEA_API_KEY=FAKEBEAKEY987\nCENSUS_API_KEY=FAKECENSUS987\n"
                    "EIA_API_KEY=FAKEEIAKEY987\nFRED_API_KEY=FAKEFREDKEY987\n", encoding="utf-8")


class _NoFred:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def vintage_levels(self, series_id, vintage_date, observation_start):
        return []

    def initial_releases(self, series_id, start, end):
        return []


def test_main_opens_db_read_only_and_never_prints_keys(tmp_path, monkeypatch, capsys):
    db = tmp_path / "d.db"
    conn = ws.get_connection(db)
    _row(conn, "CPI m/m", _t(2026, 10, 14), "0.6%", "0.4%", "0.6%", source="fred")
    conn.close()
    before = db.read_bytes()
    env = tmp_path / ".env"
    _write_env(env)

    def fake_fetcher(*args, **kwargs):
        return FakeFetcher([(_url_has("api.bls.gov"), _ok(_fixture("bls_timeseries.json")))])

    monkeypatch.setattr(verify, "requests_fetcher", fake_fetcher)
    monkeypatch.setattr(verify, "FredClient", _NoFred)
    results_path = tmp_path / "gate_results.json"
    monkeypatch.setattr(verify, "GATE_RESULTS_PATH", results_path)
    connects: list[str] = []
    real_connect = sqlite3.connect

    def spy(target, *args, **kwargs):
        connects.append(str(target))
        return real_connect(target, *args, **kwargs)

    monkeypatch.setattr(verify.sqlite3, "connect", spy)
    md = tmp_path / "coverage.md"
    code = verify.main(["--db", str(db), "--env-file", str(env), "--title", "CPI m/m",
                        "--write-results", "--markdown", str(md)])
    assert code == 0
    assert connects and all("mode=ro" in c for c in connects)
    assert db.read_bytes() == before
    out = capsys.readouterr().out
    for secret in ("FAKEBLSKEY987", "FAKEBEAKEY987", "FAKECENSUS987", "FAKEEIAKEY987", "FAKEFREDKEY987"):
        assert secret not in out
        assert secret not in results_path.read_text(encoding="utf-8")
        assert secret not in md.read_text(encoding="utf-8")
    assert "CPI m/m" in out and "SAST" in out
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload["titles"]["CPI m/m"]["comparisons"] == 2
    assert b"\r\n" not in results_path.read_bytes()


def test_main_exit_2_when_db_missing(tmp_path, capsys):
    env = tmp_path / ".env"
    _write_env(env)
    assert verify.main(["--db", str(tmp_path / "absent.db"), "--env-file", str(env)]) == 2


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
