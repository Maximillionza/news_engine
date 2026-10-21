"""Tests for scripts/event_study_once.py (B5 study runner): temp DBs, fake Dukascopy fetch and fake sleep only.

No network, no live path: the DBs are built in tmp_path, the fetch and the sleep are injected.
"""
import csv
import datetime as dt
import json
import sqlite3

import pandas as pd
import pytest

from scoring import backtest_store as bs
from scripts import event_study_once as once
from scripts.event_study_groups import RELEASE_ROW_KEYS
from webapp import store as ws
from webapp.reaction_rules import REACTION_BASELINE_QUANTILE as Q

UTC = dt.timezone.utc
T1 = dt.datetime(2026, 3, 11, 12, 30, tzinfo=UTC)       # CPI + Claims (conflict cluster)
T2 = dt.datetime(2026, 4, 15, 12, 30, tzinfo=UTC)       # Retail Sales (single)
NOW = dt.datetime(2026, 6, 1, 12, 0, tzinfo=UTC)        # long after both windows: cacheable and studyable


# ---- fixtures ----------------------------------------------------------------------------------

def _insert(dash, title, when, forecast, actual, impact="High", country="USD"):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), forecast, None, actual, None, when.isoformat(), when.isoformat(), "t",
         impact, country))


def _make_dash(folder):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "dashboard.db"
    dash = ws.get_connection(path)
    _insert(dash, "CPI m/m", T1, "0.3", "0.4")
    _insert(dash, "CPI m/m", T1 + dt.timedelta(minutes=2), "0.3", None)        # calendar re-stamp: collapses
    _insert(dash, "Unemployment Claims", T1, "220K", "230K", impact="Medium")  # USD down vs CPI USD up
    _insert(dash, "Retail Sales m/m", T2, "0.3", "0.6")
    _insert(dash, "German Ifo", T1, "1", "2", country="EUR")                   # not USD: ignored
    _insert(dash, "CPI m/m", dt.datetime(2025, 12, 30, 12, 30, tzinfo=UTC), "0.3", "0.4")   # before START
    dash.commit()
    dash.close()
    return path


def _make_bt(folder, baselines=None):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "backtest_log.db"
    bt = bs.get_connection(path)
    for symbol in ("XAUUSD", "US30"):
        for hour, value in (baselines or {12: 2.0}).items():
            bs.record_reaction_baseline(
                bt, symbol, hour, value, 100, dt.datetime(2026, 1, 1, tzinfo=UTC),
                dt.datetime(2026, 5, 1, tzinfo=UTC), quantile=Q)
    bt.close()
    return path


def _frame(lo, hi, step_s, base):
    """OHLC bars every step_s from lo up to hi (exclusive), price rising 0.01 per bar from base."""
    stamps, rows = [], []
    ts, i = lo, 0
    while ts < hi:
        price = base + 0.01 * i
        stamps.append(ts)
        rows.append((price, price + 0.05, price - 0.05, price + 0.01))
        ts += dt.timedelta(seconds=step_s)
        i += 1
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=pd.DatetimeIndex(stamps, tz="UTC"))


class FakeFetch:
    """(instrument, interval tag, lo, hi) -> frame; counts calls; `empty` interval tags return no bars."""

    def __init__(self, empty=(), fail=False):
        self.calls, self.empty, self.fail = [], set(empty), fail

    def __call__(self, instrument, interval, lo, hi):
        self.calls.append((instrument, interval, lo, hi))
        if self.fail:
            raise RuntimeError("dukascopy down")
        if interval in self.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close"],
                                index=pd.DatetimeIndex([], tz="UTC"))
        step = 5 if interval == "sec1" else 60
        base = {"XAUUSD": 4000.0, "US30": 40000.0, "DXY": 100.0}.get(_series_of(instrument), 1.0)
        return _frame(lo, hi, step, base)


def _series_of(instrument):
    for series in once.SERIES:
        if once.dukascopy_instrument(series) == instrument:
            return series
    return "?"


def _cache(tmp_path, fetch=None, now=NOW, sleeps=None, **kw):
    return once.BarCache(tmp_path / "out", fetch or FakeFetch(), now,
                         sleep=(sleeps.append if sleeps is not None else (lambda s: None)), **kw)


def _run(tmp_path, fetch=None, nowcast=None, **kw):
    dash_path = _make_dash(tmp_path / "dbs")
    bt_path = _make_bt(tmp_path / "dbs")
    dash, bt = once.open_readonly(dash_path), once.open_readonly(bt_path)
    try:
        cache = _cache(tmp_path, fetch)
        return once.run_study(
            dash, bt, cache, nowcast or (tmp_path / "missing_nowcasts.csv"), tmp_path / "out",
            dt.datetime(2026, 1, 1, tzinfo=UTC), NOW, **kw), cache
    finally:
        dash.close()
        bt.close()


def _read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


# ---- read-only guarantees ----------------------------------------------------------------------

def test_open_readonly_refuses_writes(tmp_path):
    path = _make_dash(tmp_path)
    conn = once.open_readonly(path)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM event_history")
    assert conn.execute("SELECT COUNT(*) FROM event_history").fetchone()[0] == 6
    conn.close()
    missing = tmp_path / "nope" / "x.db"
    with pytest.raises(FileNotFoundError):
        once.open_readonly(missing)
    assert not missing.exists() and not missing.parent.exists()


def test_out_dir_inside_repo_refused(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        once.assert_outside_repo(once.REPO_ROOT / "tmp")
    with pytest.raises(ValueError):
        once.assert_outside_repo(once.REPO_ROOT)
    once.assert_outside_repo(tmp_path / "ok")        # outside the repo: fine

    def boom(path):
        raise AssertionError("a database was opened")

    monkeypatch.setattr(once, "open_readonly", boom)
    target = once.REPO_ROOT / "x_event_study_test"
    assert once.main(["--out-dir", str(target)]) == 2
    assert not target.exists()


def test_main_missing_db_exits_2(tmp_path):
    code = once.main(["--dash-db", str(tmp_path / "no.db"), "--bt-db", str(tmp_path / "no2.db"),
                      "--out-dir", str(tmp_path / "out")])
    assert code == 2


# ---- bar cache ---------------------------------------------------------------------------------

def test_cache_hit_skips_network_and_pause(tmp_path):
    fetch, sleeps = FakeFetch(), []
    cache = _cache(tmp_path, fetch, sleeps=sleeps, pause_s=1.5)
    first = cache.get("XAUUSD", "sec1", T1)
    second = cache.get("XAUUSD", "sec1", T1)
    assert first and first == second
    assert len(fetch.calls) == 1 and sleeps == [1.5]
    assert cache.cache_hits == 1 and cache.network_requests == 1
    assert (tmp_path / "out" / "bars" / "XAUUSD_20260311T1230Z_sec1.csv").exists()
    lo, hi = fetch.calls[0][2], fetch.calls[0][3]
    assert lo == T1 - once.BEFORE and hi == T1 + once.AFTER


def test_recent_window_not_cached(tmp_path):
    fetch = FakeFetch()
    cache = _cache(tmp_path, fetch, now=T1 + dt.timedelta(minutes=40))
    assert cache.get("XAUUSD", "sec1", T1)
    assert cache.get("XAUUSD", "sec1", T1)
    assert len(fetch.calls) == 2 and cache.cache_hits == 0
    assert not (tmp_path / "out" / "bars").exists() or not list((tmp_path / "out" / "bars").iterdir())


def test_fetch_error_not_cached_and_counted(tmp_path):
    cache = _cache(tmp_path, FakeFetch(fail=True))
    assert cache.get("XAUUSD", "sec1", T1) is None
    assert cache.errors == 1
    assert not (tmp_path / "out" / "bars").exists() or not list((tmp_path / "out" / "bars").iterdir())


def test_empty_frame_is_cached_as_no_data(tmp_path):
    fetch = FakeFetch(empty=("sec1",))
    cache = _cache(tmp_path, fetch)
    assert cache.get("DXY", "sec1", T1) == []
    assert cache.get("DXY", "sec1", T1) == []
    assert len(fetch.calls) == 1
    path = tmp_path / "out" / "bars" / "DXY_20260311T1230Z_sec1.csv"
    assert _read_csv(path) == [["ts", "open", "high", "low", "close"]]


def test_offline_returns_none_on_a_miss_without_fetching(tmp_path):
    fetch = FakeFetch()
    cache = _cache(tmp_path, fetch, offline=True)
    assert cache.get("XAUUSD", "sec1", T1) is None
    assert fetch.calls == []


# ---- measuring ---------------------------------------------------------------------------------

def test_sec1_missing_falls_back_to_min1_and_records_source(tmp_path):
    fetch = FakeFetch(empty=("sec1",))
    cache = _cache(tmp_path, fetch)
    result = once.measure_series(cache, "XAUUSD", T1)
    assert result["status"] == "ok"
    assert result["bar_source"] == "min1" and result["resolution_s"] == 60
    assert [c[1] for c in fetch.calls] == ["sec1", "min1"]


def test_min1_not_fetched_when_sec1_is_enough(tmp_path):
    fetch = FakeFetch()
    cache = _cache(tmp_path, fetch)
    result = once.measure_series(cache, "US30", T1)
    assert result["bar_source"] == "sec1" and result["resolution_s"] == 1
    assert [c[1] for c in fetch.calls] == ["sec1"]


def test_no_bars_at_all_is_no_data(tmp_path):
    cache = _cache(tmp_path, FakeFetch(empty=("sec1", "min1")))
    result = once.measure_series(cache, "XAUUSD", T1)
    assert result["status"] == "no_data" and result["bar_source"] == "none"


def test_baseline_uses_utc_hour():
    baselines = {12: 2.0, 14: 9.0}                      # 14:30 SAST is 12:30 UTC
    assert once.baseline_for(baselines, T1) == 2.0
    assert once.baseline_for({}, T1) is None
    sast = T1.astimezone(dt.timezone(dt.timedelta(hours=2)))
    assert once.baseline_for(baselines, sast) == 2.0


def test_read_baselines_missing_table_is_empty(tmp_path):
    path = tmp_path / "bare.db"
    sqlite3.connect(path).close()
    conn = once.open_readonly(path)
    assert once.read_baselines(conn, "XAUUSD") == {}
    conn.close()
    bt = once.open_readonly(_make_bt(tmp_path / "bt", {12: 2.0, 13: 3.0}))
    assert once.read_baselines(bt, "US30") == {12: 2.0, 13: 3.0}
    bt.close()


def test_read_members_collapses_then_filters(tmp_path):
    conn = once.open_readonly(_make_dash(tmp_path))
    members = once.read_members(conn, dt.datetime(2026, 1, 1, tzinfo=UTC), NOW)
    conn.close()
    assert [(m.title, m.when_utc) for m in members] == [
        ("CPI m/m", T1), ("Unemployment Claims", T1), ("Retail Sales m/m", T2)]


def test_dukascopy_instrument_maps_all_series():
    for series in once.SERIES:
        assert once.dukascopy_instrument(series)


# ---- the study ---------------------------------------------------------------------------------

def test_run_study_end_to_end_on_fixture_dbs(tmp_path):
    summary, cache = _run(tmp_path)
    out = tmp_path / "out"
    releases = _read_csv(out / "releases.csv")
    assert tuple(releases[0]) == RELEASE_ROW_KEYS
    assert len(releases) == 1 + 4                                   # 2 minutes x 2 symbols
    assert len(_read_csv(out / "members.csv")) == 1 + 3
    assert len(_read_csv(out / "conflicts.csv")) == 1 + 2           # 1 conflict cluster x 2 symbols
    assert len(_read_csv(out / "dipstick.csv")) >= 1                # header at least
    assert set(summary) == {"run_at_utc", "sources", "sample", "coverage", "magnitudes", "pullbacks",
                            "conflicts", "peaks", "chain", "dipstick", "fetch"}
    sample = summary["sample"]
    assert sample["minutes"] == 2 and sample["minutes_multi"] == 1
    assert sample["classes"]["conflict"] == 1 and sample["classes"]["single_directional"] == 1
    assert sample["fully_computable_multi"] == {"agree": 0, "conflict": 1, "all_in_line": 0}
    assert sample["high_minutes"] == 2
    assert len(summary["conflicts"]) == 2
    first = dict(zip(releases[0], releases[1]))
    assert first["symbol"] == "XAUUSD" and first["status"] == "ok" and first["bar_source"] == "sec1"
    assert float(first["baseline"]) == 2.0
    assert first["t_sast"] == "2026-03-11 14:30 SAST"
    assert json.loads((out / "summary.json").read_text(encoding="utf-8"))["sample"]["minutes"] == 2
    assert (out / "summary.md").read_text(encoding="utf-8").strip()
    assert summary["coverage"]["XAUUSD"]["ok"] == 2 and summary["coverage"]["DXY"]["sec1"] == 2
    assert summary["fetch"]["network_requests"] == cache.network_requests == 6


def test_run_study_limit_studies_the_first_minutes_only(tmp_path):
    summary, _ = _run(tmp_path, limit=1)
    assert summary["sample"]["minutes"] == 1
    assert len(_read_csv(tmp_path / "out" / "releases.csv")) == 1 + 2


def test_unstudyable_recent_minute_is_pending(tmp_path):
    dash = once.open_readonly(_make_dash(tmp_path / "dbs"))
    bt = once.open_readonly(_make_bt(tmp_path / "dbs"))
    cache = _cache(tmp_path, now=T2 + dt.timedelta(minutes=20))     # T2 + 31 + 10 min is still ahead
    summary = once.run_study(dash, bt, cache, tmp_path / "none.csv", tmp_path / "out",
                             dt.datetime(2026, 1, 1, tzinfo=UTC), NOW)
    dash.close()
    bt.close()
    assert summary["sample"]["minutes"] == 1 and summary["sample"]["pending_minutes"] == 1


def test_run_study_writes_only_under_out_dir(tmp_path):
    dash_path = _make_dash(tmp_path / "dbs")
    bt_path = _make_bt(tmp_path / "dbs")
    before = {p for p in tmp_path.rglob("*")}
    dbs_before = sorted(p.name for p in (tmp_path / "dbs").iterdir())
    dash, bt = once.open_readonly(dash_path), once.open_readonly(bt_path)
    once.run_study(dash, bt, _cache(tmp_path), tmp_path / "none.csv", tmp_path / "out",
                   dt.datetime(2026, 1, 1, tzinfo=UTC), NOW)
    dash.close()
    bt.close()
    created = {p for p in tmp_path.rglob("*")} - before
    assert created and all((tmp_path / "out") in p.parents or p == tmp_path / "out" for p in created)
    assert sorted(p.name for p in (tmp_path / "dbs").iterdir()) == dbs_before


def test_dry_run_makes_no_fetch(tmp_path):
    fetch = FakeFetch(fail=True)
    summary, _ = _run(tmp_path, fetch=fetch, dry_run=True)
    assert fetch.calls == []
    assert summary["sample"]["minutes"] == 2
    assert not (tmp_path / "out").exists()


def test_missing_nowcast_csv_reports_regeneration(tmp_path):
    summary, _ = _run(tmp_path)
    dip = summary["dipstick"]
    assert dip["status"] == "missing"
    assert "cleveland_nowcast_to_csv.py" in dip["regenerate"] and "--dash-db" in dip["regenerate"]
    assert (tmp_path / "out" / "releases.csv").exists()
    assert "missing" in once.render_markdown(summary)


def test_dipstick_with_nowcast_csv_and_snapshot_cross_check(tmp_path):
    nowcast = tmp_path / "nowcasts.csv"
    with nowcast.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event_title", "release_utc", "as_of_utc", "value", "source"])
        for as_of, value in (("2026-02-09T23:59:59+00:00", 0.2), ("2026-03-01T23:59:59+00:00", 0.3), ("2026-03-10T23:59:59+00:00", 0.3)):
            writer.writerow(["CPI m/m", T1.isoformat(), as_of, value, "t"])
    dash_path = _make_dash(tmp_path / "dbs")
    bt_path = _make_bt(tmp_path / "dbs")
    writer_conn = bs.get_connection(bt_path)
    bs.record_nowcast_snapshot(writer_conn, "CPI m/m", T1, 0.3, dt.datetime(2026, 3, 10, 23, 59, 59, tzinfo=UTC),
                               "t", "reconstructed", "v1")
    writer_conn.close()
    dash, btc = once.open_readonly(dash_path), once.open_readonly(bt_path)
    summary = once.run_study(dash, btc, _cache(tmp_path), nowcast, tmp_path / "out",
                             dt.datetime(2026, 1, 1, tzinfo=UTC), NOW)
    dash.close()
    btc.close()
    dip = summary["dipstick"]
    assert dip["status"] == "ok"
    assert dip["per_lag"]["25"]["n"] == 1 and dip["per_lag"]["25"]["final_closer"] == 1
    assert dip["t5_equals_final"] == {"n": 1, "equal": 1}
    assert dip["snapshot_check"] == {"n": 1, "equal": 1}
    assert len(_read_csv(tmp_path / "out" / "dipstick.csv")) == 1 + len(once.LAGS_DAYS)


def test_render_markdown_has_n_columns(tmp_path):
    summary, _ = _run(tmp_path)
    text = once.render_markdown(summary)
    lines = text.splitlines()
    headers = [lines[i] for i in range(len(lines) - 1)
               if lines[i].startswith("|") and lines[i + 1].startswith("|") and set(lines[i + 1]) <= set("|-: ")]
    assert headers
    for header in headers:
        assert "n" in [cell.strip() for cell in header.strip("|").split("|")], header
    assert "SAST" in text


def test_render_markdown_dry_run_summary(tmp_path):
    summary, _ = _run(tmp_path, dry_run=True)
    assert "minutes" in once.render_markdown(summary)
