"""
Tests for scripts/compute_release_reactions.py (spec 2026-10-16-market-reaction-design.md §4, §6).

Synthetic 1-minute bar series, a fake fetch_bars and in-memory / tmp_path databases only: no network,
never the live DBs.
"""
import datetime as dt
import sqlite3

import numpy as np
import pandas as pd
import pytest

from scoring import backtest_store as bs
from scripts import compute_release_reactions as crr
from webapp import store as ws
from webapp.reaction_rules import REACTION_BASELINE_QUANTILE as Q

UTC = dt.timezone.utc
MON, TUE, SAT = 2, 3, 7          # 2026-03-02 is a Monday, 2026-03-07 a Saturday
REL_1230 = dt.datetime(2026, 3, TUE, 12, 30, tzinfo=UTC)
REL_1330 = dt.datetime(2026, 3, TUE, 13, 30, tzinfo=UTC)
SINCE = dt.datetime(2026, 1, 1, tzinfo=UTC)
NOW = dt.datetime(2026, 3, 4, 9, 0, tzinfo=UTC)


def _t(day: int, hour: int, minute: int) -> dt.datetime:
    return dt.datetime(2026, 3, day, hour, minute, tzinfo=UTC)


def _ramp(day: int, start_hour: int = 12, minutes: int = 131, step: float = 0.1) -> dict:
    """One bar per minute from start_hour:00, open rising by `step` per minute (every 5-min move = 5*step)."""
    first = _t(day, start_hour, 0)
    return {first + dt.timedelta(minutes=i): 100.0 + step * i for i in range(minutes)}


def _series(opens: dict) -> pd.Series:
    ordered = sorted(opens)
    return pd.Series([opens[k] for k in ordered], index=pd.DatetimeIndex(ordered), name="open")


def _scenario_bars() -> dict:
    """
    Mon and Tue 12:00-14:10 ramps (5-min move 0.5). Tue 12:30 release jumps +5 by 12:35 (a buy reaction);
    Tue 13:35 bar is removed so the 13:30 release has no end bar while later bars exist (genuine gap).
    """
    opens = _ramp(MON)
    opens.update(_ramp(TUE))
    opens[_t(TUE, 12, 35)] = opens[_t(TUE, 12, 30)] + 5.0
    del opens[_t(TUE, 13, 35)]
    return opens


def _insert_event(dash, title, when, country="USD"):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), None, None, None, None, when.isoformat(), when.isoformat(), "t", "High", country))
    dash.commit()


def _dash_with_events():
    dash = ws.get_connection(":memory:")
    _insert_event(dash, "CPI m/m", REL_1230)
    _insert_event(dash, "Core CPI m/m", REL_1230)                # same minute: one release minute
    _insert_event(dash, "ISM Services PMI", REL_1330)
    _insert_event(dash, "German Ifo", _t(TUE, 12, 45), country="EUR")   # non-USD: ignored
    return dash


class FakeFetch:
    def __init__(self, bars_by_symbol: dict, fail: tuple = ()):
        self.bars_by_symbol, self.fail, self.calls = bars_by_symbol, set(fail), []

    def __call__(self, symbol, start, end):
        self.calls.append((symbol, start, end))
        if symbol in self.fail:
            raise RuntimeError(f"dukascopy down for {symbol}")
        return _series(self.bars_by_symbol[symbol])


def _fetch_both():
    return FakeFetch({"XAUUSD": _scenario_bars(), "US30": _scenario_bars()})


def _rows(bt, table):
    return bt.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---- price_at_minute ------------------------------------------------------------------------------

def test_price_at_minute_is_the_exact_minute_open_or_none():
    bars = _series({_t(MON, 12, 0): 100.0, _t(MON, 12, 2): 101.0, _t(MON, 12, 3): float("nan")})
    assert crr.price_at_minute(bars, _t(MON, 12, 0)) == 100.0
    assert crr.price_at_minute(bars, _t(MON, 12, 1)) is None        # never the neighbouring bar
    assert crr.price_at_minute(bars, _t(MON, 12, 3)) is None        # NaN open counts as missing


def test_naive_bar_index_is_refused_not_guessed():
    naive = pd.Series([1.0], index=pd.DatetimeIndex([dt.datetime(2026, 3, 2, 12, 0)]))
    with pytest.raises(ValueError):
        crr.price_at_minute(naive, _t(MON, 12, 0))


# ---- compute_baselines ----------------------------------------------------------------------------

def test_baseline_excludes_release_windows_uses_5min_grid_and_ignores_weekends():
    opens = _ramp(MON, minutes=66)                     # 12:00-13:05, every grid window moves 0.5
    opens.update(_ramp(SAT, minutes=66, step=9.0))     # weekend: must be ignored
    opens[_t(MON, 12, 30)] = 1000.0                    # release minute: distorts the 12:25 and 12:30 windows
    opens[_t(MON, 12, 31)] = 5000.0                    # off-grid minute: belongs to no window
    baselines = crr.compute_baselines(_series(opens), {_t(MON, 12, 30)})
    assert set(baselines) == {12, 13}
    median, n = baselines[12]
    assert n == 11                                     # 12 grid windows minus the release-minute window
    assert median == pytest.approx(0.5)
    assert baselines[13] == (pytest.approx(0.5), 1)    # 13:00 -> 13:05 only
    assert all(isinstance(hour, int) for hour in baselines)


def test_baseline_without_the_release_exclusion_would_differ():
    opens = _ramp(MON, minutes=66)
    opens[_t(MON, 12, 30)] = 1000.0
    with_exclusion = crr.compute_baselines(_series(opens), {_t(MON, 12, 30)})[12][1]
    without = crr.compute_baselines(_series(opens), set())[12][1]
    assert (with_exclusion, without) == (11, 12)


def test_baseline_skips_windows_missing_an_end_bar_and_respects_the_period():
    opens = _ramp(MON, minutes=66)
    opens.update(_ramp(TUE, minutes=66))
    del opens[_t(MON, 12, 20)]                         # kills the Mon 12:15 (end) and 12:20 (start) windows
    period = (_t(MON, 12, 0), _t(MON, 23, 0))          # Tuesday is outside the period
    assert crr.compute_baselines(_series(opens), set(), period=period)[12][1] == 10


# ---- reaction_for --------------------------------------------------------------------------------

@pytest.mark.parametrize("p5, expected", [(103.0, "buy"), (97.0, "sell"), (102.0, "none"), (101.0, "none")])
def test_reaction_for_labels(p5, expected):
    bars = _series({_t(TUE, 12, 30): 100.0, _t(TUE, 12, 35): p5})
    out = crr.reaction_for(bars, _t(TUE, 12, 30), 2.0)
    assert out["status"] == "ok" and out["reaction"] == expected
    assert (out["p0"], out["p5"]) == (100.0, p5)


def test_reaction_for_missing_end_bar_is_no_data_and_never_uses_a_nearby_bar():
    bars = _series({_t(TUE, 12, 30): 100.0, _t(TUE, 12, 34): 103.0, _t(TUE, 12, 36): 103.0})
    out = crr.reaction_for(bars, _t(TUE, 12, 30), 2.0)
    assert out == {"status": "no_data", "p0": None, "p5": None, "reaction": None, "typical": 2.0}


def test_reaction_for_without_a_baseline_is_no_data():
    bars = _series({_t(TUE, 12, 30): 100.0, _t(TUE, 12, 35): 110.0})
    assert crr.reaction_for(bars, _t(TUE, 12, 30), None)["status"] == "no_data"


# ---- release minutes: same-title duplicate collapse ------------------------------------------------

def test_same_title_rows_within_3_minutes_collapse_to_the_earliest_but_9_minutes_do_not():
    dash = ws.get_connection(":memory:")
    for minute in (14, 15, 16):
        _insert_event(dash, "ADP Weekly Employment Change", _t(TUE, 12, minute))
    _insert_event(dash, "Federal Budget Balance", _t(TUE, 17, 58))
    _insert_event(dash, "Federal Budget Balance", _t(TUE, 18, 0))
    _insert_event(dash, "RCM/TIPP Economic Optimism", _t(TUE, 14, 1))
    _insert_event(dash, "RCM/TIPP Economic Optimism", _t(TUE, 14, 10))
    _insert_event(dash, "Other title", _t(TUE, 12, 15))          # different title 1 min away: kept
    assert crr.usd_release_minutes(dash) == {
        _t(TUE, 12, 14), _t(TUE, 12, 15), _t(TUE, 17, 58), _t(TUE, 14, 1), _t(TUE, 14, 10)}


def test_collapse_is_anchored_on_the_earliest_row_of_a_run():
    events = [("A", _t(TUE, 12, 0)), ("A", _t(TUE, 12, 2)), ("A", _t(TUE, 12, 4)), ("A", _t(TUE, 12, 3))]
    # 12:02 and 12:03 are within 3 minutes of 12:00; 12:04 is 4 minutes after the kept 12:00 row.
    assert crr.collapse_same_title_duplicates(events) == [("A", _t(TUE, 12, 0)), ("A", _t(TUE, 12, 4))]


# ---- run(): backfill -----------------------------------------------------------------------------

def test_backfill_writes_one_row_per_release_and_symbol_with_no_data_for_a_missing_bar():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    result = crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD", "US30"], SINCE)
    assert (result["written"], result["no_data"], result["skipped_recent"]) == (4, 2, 0)
    assert result["fetch_failed"] == {}
    rows = bs.get_release_reactions(bt, "XAUUSD", Q)
    ok, gap = rows[REL_1230.isoformat()], rows[REL_1330.isoformat()]
    assert (ok["status"], ok["reaction"], ok["p0"], ok["move"]) == ("ok", "buy", 103.0, pytest.approx(5.0))
    assert ok["typical_abs_move"] == pytest.approx(0.5)
    assert (gap["status"], gap["p0"], gap["p5"], gap["reaction"]) == ("no_data", None, None, None)
    assert gap["typical_abs_move"] == pytest.approx(0.5)


def test_backfill_baselines_one_row_per_hour_with_period_and_counts():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    result = crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD"], SINCE)
    rows = bt.execute("SELECT utc_hour, median_abs_move, n_windows, period_start_utc, period_end_utc "
                      "FROM reaction_baselines WHERE instrument='XAUUSD' ORDER BY utc_hour").fetchall()
    # Hour 12: Mon 12 + Tue 11 (release window out). Hour 13: Mon 12 + Tue 13:00-13:25 (6; later starts are
    # after period_end = the last release minute). Hour 14: Mon 14:00 and 14:05 only.
    assert [(r[0], r[2]) for r in rows] == [(12, 23), (13, 18), (14, 2)]
    assert all(r[1] == pytest.approx(0.5) for r in rows)
    assert {(r[3], r[4]) for r in rows} == {(_t(MON, 12, 0).isoformat(), REL_1330.isoformat())}
    assert result["baselines"] == 3


def test_rerunning_backfill_adds_nothing_and_reports_rows_already_present():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD", "US30"], SINCE)
    before = (_rows(bt, "release_reactions"), _rows(bt, "reaction_baselines"))
    again = crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD", "US30"], SINCE)
    assert (_rows(bt, "release_reactions"), _rows(bt, "reaction_baselines")) == before == (4, 6)
    assert (again["written"], again["already_present"], again["baselines_new"]) == (0, 4, 0)


def test_a_release_younger_than_10_minutes_is_skipped():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    now = REL_1330 + dt.timedelta(minutes=8)
    result = crr.run(dash, bt, _fetch_both(), "backfill", now, ["XAUUSD"], SINCE)
    assert (result["written"], result["skipped_recent"]) == (1, 1)
    assert set(bs.get_release_reactions(bt, "XAUUSD", Q)) == {REL_1230.isoformat()}


def test_a_release_whose_end_bar_is_not_published_yet_is_left_for_a_later_run():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    opens = {k: v for k, v in _scenario_bars().items() if k <= _t(TUE, 13, 33)}   # feed stops before 13:35
    result = crr.run(dash, bt, FakeFetch({"XAUUSD": opens}), "backfill", NOW, ["XAUUSD"], SINCE)
    assert (result["written"], result["skipped_pending"], result["no_data"]) == (1, 1, 0)
    assert REL_1330.isoformat() not in bs.get_release_reactions(bt, "XAUUSD", Q)


def test_a_fetch_exception_writes_nothing_for_that_symbol_and_the_other_still_runs():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    fetch = FakeFetch({"XAUUSD": _scenario_bars()}, fail=("US30",))
    result = crr.run(dash, bt, fetch, "backfill", NOW, ["US30", "XAUUSD"], SINCE)
    assert "US30" in result["fetch_failed"] and "dukascopy down" in result["fetch_failed"]["US30"]
    assert bs.get_release_reactions(bt, "US30", Q) == {}
    assert bt.execute("SELECT COUNT(*) FROM reaction_baselines WHERE instrument='US30'").fetchone()[0] == 0
    assert len(bs.get_release_reactions(bt, "XAUUSD", Q)) == 2


def test_an_empty_bar_series_counts_as_a_failed_fetch_not_as_no_data():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    result = crr.run(dash, bt, FakeFetch({"XAUUSD": {}}), "backfill", NOW, ["XAUUSD"], SINCE)
    assert "XAUUSD" in result["fetch_failed"] and _rows(bt, "release_reactions") == 0


def test_dry_run_writes_nothing_but_reports_what_it_would_write():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    result = crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD", "US30"], SINCE, dry_run=True)
    assert (result["written"], result["no_data"], result["baselines"]) == (4, 2, 6)
    assert (_rows(bt, "release_reactions"), _rows(bt, "reaction_baselines")) == (0, 0)


def test_unresolvable_symbols_are_reported_and_skipped():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    fetch = _fetch_both()
    result = crr.run(dash, bt, fetch, "backfill", NOW, ["XAUUSD", "NOPE"], SINCE)
    assert result["unresolved"] == ["NOPE"]
    assert {c[0] for c in fetch.calls} == {"XAUUSD"}


def test_numpy_hour_keys_are_stored_as_plain_ints(monkeypatch):
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    monkeypatch.setattr(crr, "compute_baselines",
                        lambda *args, **kwargs: {np.int64(12): (np.float64(0.5), np.int64(23)),
                                                            np.int64(13): (np.float64(0.5), np.int64(18))})
    result = crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD"], SINCE)
    assert result["baselines"] == 2
    assert bs.get_latest_reaction_baselines(bt, "XAUUSD", Q) == {12: 0.5, 13: 0.5}
    assert bs.get_release_reactions(bt, "XAUUSD", Q)[REL_1230.isoformat()]["reaction"] == "buy"


# ---- run(): incremental --------------------------------------------------------------------------

def test_incremental_skips_minutes_with_rows_and_uses_the_stored_baselines():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    bs.record_release_reaction(bt, REL_1230, "XAUUSD", "no_data", baseline_quantile=Q)   # already present
    bs.record_reaction_baseline(bt, "XAUUSD", 13, 0.25, 50, _t(MON, 0, 0), _t(MON, 23, 0), quantile=Q)
    opens = _scenario_bars()
    opens[_t(TUE, 13, 35)] = opens[_t(TUE, 13, 30)] + 0.3                    # 13:30 now has its end bar
    result = crr.run(dash, bt, FakeFetch({"XAUUSD": opens}), "incremental", NOW, ["XAUUSD"], SINCE)
    assert (result["written"], result["already_present"], result["baselines"]) == (1, 1, 0)
    rows = bs.get_release_reactions(bt, "XAUUSD", Q)
    assert rows[REL_1230.isoformat()]["status"] == "no_data"                  # untouched
    new = rows[REL_1330.isoformat()]
    assert new["typical_abs_move"] == pytest.approx(0.25) and new["reaction"] == "buy"   # 0.3 > stored 0.25
    assert _rows(bt, "reaction_baselines") == 1                                # nothing recomputed


def test_incremental_with_no_stored_baselines_computes_them():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    result = crr.run(dash, bt, _fetch_both(), "incremental", NOW, ["XAUUSD"], SINCE)
    assert result["written"] == 2 and result["baselines"] == 3
    assert _rows(bt, "reaction_baselines") == 3


def test_incremental_with_nothing_missing_does_not_fetch():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD"], SINCE)
    fetch = _fetch_both()
    result = crr.run(dash, bt, fetch, "incremental", NOW, ["XAUUSD"], SINCE)
    assert fetch.calls == [] and result["written"] == 0 and result["already_present"] == 2


# ---- CLI -------------------------------------------------------------------------------------------

def _make_dash_file(path):
    conn = ws.get_connection(path)
    _insert_event(conn, "CPI m/m", REL_1230)
    _insert_event(conn, "ISM Services PMI", REL_1330)
    ws.add_tracked_symbol(conn, "XAUUSD")
    conn.close()


def test_cli_refuses_the_default_live_db_before_opening_anything(monkeypatch, capsys):
    monkeypatch.delenv(crr.LIVE_ENV_VAR, raising=False)
    opened = []
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: opened.append(a) or pytest.fail("opened a DB"))
    monkeypatch.setattr(bs, "get_connection", lambda *a, **k: opened.append(a) or pytest.fail("opened bt DB"))
    assert crr.main(["--backfill"]) == 2
    assert opened == []
    assert "REFUSING" in capsys.readouterr().err


def test_cli_backfill_reads_dashboard_read_only_and_writes_only_the_two_tables(tmp_path, monkeypatch):
    dash_path, bt_path = tmp_path / "dashboard.db", tmp_path / "bt.db"
    _make_dash_file(dash_path)
    monkeypatch.setattr(crr, "default_fetch_bars", FakeFetch({"XAUUSD": _scenario_bars()}))
    real_connect, seen = sqlite3.connect, []

    def spy(database, *args, **kwargs):
        seen.append((str(database), kwargs.get("uri", False)))
        return real_connect(database, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", spy)
    code = crr.main(["--backfill", "--bt-db", str(bt_path), "--dash-db", str(dash_path), "--since", "2026-01-01"])
    assert code == 0
    dash_opens = [s for s in seen if "dashboard.db" in s[0]]
    assert dash_opens and all(uri and s.endswith("?mode=ro") for s, uri in dash_opens)
    bt = real_connect(bt_path)
    assert bt.execute("SELECT COUNT(*) FROM release_reactions").fetchone()[0] == 2
    tables = [r[0] for r in bt.execute("SELECT name FROM sqlite_master WHERE type='table' "
                                       "AND name NOT LIKE 'sqlite_%'").fetchall()]
    touched = {t for t in tables if bt.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]}
    assert touched == {"release_reactions", "reaction_baselines"}


def test_cli_dry_run_leaves_the_backtest_db_untouched(tmp_path, monkeypatch):
    dash_path, bt_path = tmp_path / "dashboard.db", tmp_path / "bt.db"
    _make_dash_file(dash_path)
    sqlite3.connect(bt_path).close()                                  # empty pre-existing file, no tables
    monkeypatch.setattr(crr, "default_fetch_bars", FakeFetch({"XAUUSD": _scenario_bars()}))
    code = crr.main(["--backfill", "--dry-run", "--bt-db", str(bt_path), "--dash-db", str(dash_path)])
    assert code == 0
    bt = sqlite3.connect(bt_path)
    assert bt.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0   # not even the schema


def test_cli_exits_non_zero_when_a_fetch_failed(tmp_path, monkeypatch):
    dash_path, bt_path = tmp_path / "dashboard.db", tmp_path / "bt.db"
    _make_dash_file(dash_path)
    monkeypatch.setattr(crr, "default_fetch_bars", FakeFetch({}, fail=("XAUUSD",)))
    assert crr.main(["--incremental", "--bt-db", str(bt_path), "--dash-db", str(dash_path)]) == 1


def test_open_dash_readonly_cannot_write(tmp_path):
    dash_path = tmp_path / "dashboard.db"
    _make_dash_file(dash_path)
    conn = crr.open_dash_readonly(dash_path)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO tracked_symbols (symbol) VALUES ('US30')")


# ---- 75th-percentile baseline (owner ruling 2026-10-16) ------------------------------------------

@pytest.mark.parametrize("values, q, expected", [
    ([1.0, 2.0, 3.0, 4.0, 5.0], 0.75, 4.0),          # h = 4 * 0.75 = 3 -> x[3]
    ([1.0, 2.0, 3.0, 4.0], 0.75, 3.25),              # h = 2.25 -> 3 + 0.25 * (4 - 3)
    ([4.0, 1.0, 3.0, 2.0], 0.5, 2.5),                # unsorted input, median
    ([7.0], 0.75, 7.0),
])
def test_quantile_is_linear_interpolation_like_numpy(values, q, expected):
    assert crr.quantile(values, q) == pytest.approx(expected)
    assert crr.quantile(values, q) == pytest.approx(float(np.quantile(values, q)))


def test_quantile_of_nothing_is_none():
    assert crr.quantile([], 0.75) is None


def _ladder_monday() -> dict:
    """Grid bars 12:00..13:00 on Monday whose 12 consecutive 5-minute moves are +1, -2, +3, ... (|move| 1..12)."""
    opens, price = {}, 100.0
    for k in range(13):
        opens[_t(MON, 12, 0) + dt.timedelta(minutes=5 * k)] = price
        price += (k + 1) * (1 if k % 2 == 0 else -1)
    return opens


def test_baseline_is_the_hand_computed_75th_percentile_not_the_median():
    baselines = crr.compute_baselines(_series(_ladder_monday()), set())
    # |moves| 1..12: h = 11 * 0.75 = 8.25 -> 9 + 0.25 * (10 - 9) = 9.25 (the median would be 6.5).
    assert baselines == {12: (pytest.approx(9.25), 12)}


@pytest.mark.parametrize("move, expected", [(9.25, "none"), (9.26, "buy"), (-9.26, "sell"), (6.6, "none")])
def test_reaction_flips_at_the_quantile_threshold(move, expected):
    typical = crr.compute_baselines(_series(_ladder_monday()), set())[12][0]
    bars = _series({_t(TUE, 12, 30): 100.0, _t(TUE, 12, 35): 100.0 + move})
    assert crr.reaction_for(bars, _t(TUE, 12, 30), typical)["reaction"] == expected


def test_rows_store_the_quantile_and_multiple():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD"], SINCE)
    assert {tuple(r) for r in bt.execute("SELECT DISTINCT baseline_quantile, reaction_multiple FROM release_reactions")} \
        == {(0.75, 1.0)}
    assert {r[0] for r in bt.execute("SELECT DISTINCT quantile FROM reaction_baselines")} == {0.75}


def test_rows_under_the_old_median_quantile_are_untouched_by_a_075_run():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    bs.record_release_reaction(bt, REL_1230, "XAUUSD", "ok", p0=1.0, p5=2.0, typical_abs_move=0.9,
                               reaction="buy", baseline_quantile=0.5)
    bs.record_reaction_baseline(bt, "XAUUSD", 12, 99.0, 5, _t(MON, 0, 0), _t(MON, 23, 0), quantile=0.5)
    result = crr.run(dash, bt, _fetch_both(), "incremental", NOW, ["XAUUSD"], SINCE)
    assert result["written"] == 2 and result["already_present"] == 0      # the 0.5 row does not count
    old = bs.get_release_reactions(bt, "XAUUSD", 0.5)
    assert list(old) == [REL_1230.isoformat()] and old[REL_1230.isoformat()]["p5"] == 2.0
    new = bs.get_release_reactions(bt, "XAUUSD", Q)[REL_1230.isoformat()]
    assert new["typical_abs_move"] == pytest.approx(0.5)                   # the stored 0.5-quantile 99.0 is ignored
    assert bs.get_latest_reaction_baselines(bt, "XAUUSD", 0.5) == {12: 99.0}


# ---- raw duplicate minutes stay out of the baseline (controller ruling 5) ----------------------------

def test_raw_duplicate_minutes_are_excluded_from_the_baseline_but_judged_once():
    dash = ws.get_connection(":memory:")
    for minute in (14, 15, 16):
        _insert_event(dash, "ADP Weekly Employment Change", _t(TUE, 12, minute))
    _insert_event(dash, "ISM Services PMI", REL_1330)                  # keeps the period open past 12:15
    judged, excluded = crr.release_minute_sets(dash)
    assert judged == {_t(TUE, 12, 14), REL_1330}
    assert excluded == {_t(TUE, 12, 14), _t(TUE, 12, 15), _t(TUE, 12, 16), REL_1330}
    bt = bs.get_connection(":memory:")
    result = crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD"], SINCE)
    assert result["written"] == 2
    assert set(bs.get_release_reactions(bt, "XAUUSD", Q)) == {_t(TUE, 12, 14).isoformat(), REL_1330.isoformat()}
    # Hour 12: Mon 12 + Tue 12 grid windows, minus the Tue 12:15 start (a raw release minute); 12:14 and 12:16
    # are off the 5-minute grid. Without the raw exclusion this would be 24.
    assert bt.execute("SELECT n_windows FROM reaction_baselines WHERE utc_hour = 12").fetchone()[0] == 23


# ---- naive dict keys (controller ruling 6) -----------------------------------------------------------

def test_naive_dict_keys_are_refused_not_guessed():
    naive = {dt.datetime(2026, 3, 2, 12, 0): 100.0, dt.datetime(2026, 3, 2, 12, 5): 101.0}
    with pytest.raises(ValueError):
        crr.price_at_minute(naive, _t(MON, 12, 0))
    with pytest.raises(ValueError):
        crr.compute_baselines(naive, set())
    with pytest.raises(ValueError):
        crr.reaction_for(naive, _t(MON, 12, 0), 0.5)


# ---- per-symbol failure isolation beyond the fetch (controller ruling 7) -----------------------------

def test_a_record_error_for_one_symbol_is_reported_and_the_other_symbol_still_runs(monkeypatch):
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    real = bs.record_reaction_baseline

    def flaky(conn, instrument, *args, **kwargs):
        if instrument == "US30":
            raise sqlite3.OperationalError("disk I/O error")
        return real(conn, instrument, *args, **kwargs)

    monkeypatch.setattr(bs, "record_reaction_baseline", flaky)
    result = crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["US30", "XAUUSD"], SINCE)
    assert "disk I/O error" in result["errors"]["US30"]
    assert bs.get_release_reactions(bt, "US30", Q) == {}
    assert len(bs.get_release_reactions(bt, "XAUUSD", Q)) == 2


def test_a_compute_error_for_one_symbol_is_reported_and_the_other_symbol_still_runs(monkeypatch):
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    real, calls = crr.compute_baselines, []

    def flaky(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:                                   # the first symbol processed: US30
            raise RuntimeError("bad bars")
        return real(*args, **kwargs)

    monkeypatch.setattr(crr, "compute_baselines", flaky)
    result = crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["US30", "XAUUSD"], SINCE)
    assert "bad bars" in result["errors"]["US30"] and "XAUUSD" not in result["errors"]
    assert len(bs.get_release_reactions(bt, "XAUUSD", Q)) == 2


def test_cli_exits_non_zero_on_a_symbol_error(tmp_path, monkeypatch):
    dash_path, bt_path = tmp_path / "dashboard.db", tmp_path / "bt.db"
    _make_dash_file(dash_path)
    monkeypatch.setattr(crr, "default_fetch_bars", FakeFetch({"XAUUSD": _scenario_bars()}))
    monkeypatch.setattr(crr, "compute_baselines", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert crr.main(["--backfill", "--bt-db", str(bt_path), "--dash-db", str(dash_path)]) == 1


# ---- --refresh-baselines (controller ruling 8) -------------------------------------------------------

def _baseline_rows(bt):
    return [tuple(r) for r in bt.execute(
        "SELECT id, utc_hour, median_abs_move, n_windows, period_end_utc FROM reaction_baselines ORDER BY id")]


def test_refresh_baselines_appends_rows_for_the_new_period_and_keeps_the_old_ones():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD"], SINCE)
    old = _baseline_rows(bt)
    _insert_event(dash, "Fed Chair Speaks", _t(TUE, 14, 0))
    crr.run(dash, bt, _fetch_both(), "incremental", NOW, ["XAUUSD"], SINCE)     # no flag: stored baselines
    assert _baseline_rows(bt) == old
    fetch = _fetch_both()
    result = crr.run(dash, bt, fetch, "incremental", NOW, ["XAUUSD"], SINCE, refresh_baselines=True)
    assert fetch.calls and result["written"] == 0 and result["baselines_new"] == 3
    rows = _baseline_rows(bt)
    assert rows[:3] == old                                                     # old rows untouched
    assert {r[4] for r in rows[3:]} == {_t(TUE, 14, 0).isoformat()}            # new period_end
    assert bs.get_latest_reaction_baselines(bt, "XAUUSD", Q) == {r[1]: r[2] for r in rows[3:]}


def test_refresh_with_an_unchanged_period_adds_nothing():
    dash, bt = _dash_with_events(), bs.get_connection(":memory:")
    crr.run(dash, bt, _fetch_both(), "backfill", NOW, ["XAUUSD"], SINCE)
    result = crr.run(dash, bt, _fetch_both(), "incremental", NOW, ["XAUUSD"], SINCE, refresh_baselines=True)
    assert (result["baselines"], result["baselines_new"]) == (3, 0) and _rows(bt, "reaction_baselines") == 3


def test_cli_passes_refresh_baselines_through(tmp_path, monkeypatch):
    dash_path, bt_path = tmp_path / "dashboard.db", tmp_path / "bt.db"
    _make_dash_file(dash_path)
    seen = {}

    def fake_run(*args, **kwargs):
        seen.update(kwargs)
        return {"fetch_failed": {}, "errors": {}, "dry_run": False, "mode": "incremental", "unresolved": [],
                "per_symbol": {}, "baselines_by_symbol": {}, **{key: 0 for key in crr._COUNTERS}}

    monkeypatch.setattr(crr, "run", fake_run)
    assert crr.main(["--incremental", "--refresh-baselines", "--bt-db", str(bt_path), "--dash-db", str(dash_path)]) == 0
    assert seen["refresh_baselines"] is True
