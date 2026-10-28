"""
B10 (2026-10-28) K11/K12: grading each shock alert's stored lean against the 5-minute move after first
publication and after detection, judged against the Market reaction hourly baselines (no fixed-dollar fallback).
Synthetic bars and a fake fetch only -- nothing here touches the network or a live DB.
"""
from __future__ import annotations

import datetime as dt
import sqlite3

import pytest

from alerting import lean_grading as lg
from alerting import store

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 3, 4, 9, 0, tzinfo=UTC)          # well after every test bar
BASELINES = {"XAUUSD": {12: 1.0, 13: 2.0}, "US30": {12: 10.0, 13: 10.0}}


def _t(hour: int, minute: int, second: int = 0, day: int = 3) -> dt.datetime:
    return dt.datetime(2026, 3, day, hour, minute, second, tzinfo=UTC)


class FakeFetch:
    """fetch_bars stand-in: {symbol: {minute: open}}; records every call; `fail` symbols raise."""

    def __init__(self, bars: dict[str, dict[dt.datetime, float]], fail: tuple[str, ...] = ()) -> None:
        self.bars = bars
        self.fail = fail
        self.calls: list[tuple[str, dt.datetime, dt.datetime]] = []

    def __call__(self, symbol: str, start: dt.datetime, end: dt.datetime) -> dict[dt.datetime, float]:
        self.calls.append((symbol, start, end))
        if symbol in self.fail:
            raise ConnectionError("feed down")
        return dict(self.bars.get(symbol, {}))


def _resolve(symbol: str) -> str:
    return f"DK_{symbol}"


def _flat_bars(start: dt.datetime, end: dt.datetime, price: float = 100.0) -> dict[dt.datetime, float]:
    """One bar per minute from start to end inclusive, all at `price`."""
    out = {}
    when = start
    while when <= end:
        out[when] = price
        when += dt.timedelta(minutes=1)
    return out


def _alert(conn: sqlite3.Connection, detected: dt.datetime, published: dt.datetime,
           affected: list[dict], severity: str = "High", incident_id: int | None = None,
           headline: str = "H") -> int:
    return store.record_alert(
        conn, headline=headline, source="s", url="https://example.com/a",
        published_utc=published, detected_at_utc=detected, category="geopolitical", severity=severity,
        classification_method="llm", rationale=None, affected_symbols=affected,
        first_published_utc=published, incident_id=incident_id,
    )


def _rows(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM shock_alert_grades ORDER BY alert_id, symbol, anchor").fetchall()]


# --- anchors and timing --------------------------------------------------------------------

def test_anchor_minute_rounds_up():
    assert lg.anchor_minute(_t(12, 30, 40)) == _t(12, 31)
    assert lg.anchor_minute(_t(12, 30, 0)) == _t(12, 30)
    assert lg.anchor_minute(_t(12, 30, 0) + dt.timedelta(microseconds=1)) == _t(12, 31)


def test_baseline_hour_is_hour_of_rounded_minute():
    # detected 12:59:30 -> minute 13:00, hour 13 (baseline 2.0): a 1.5 move is no_move there
    bars = {_t(13, 0): 100.0, _t(13, 5): 101.5}
    late = lg.grade_cell(1, "XAUUSD", "detected", _t(12, 59, 30), "buy", bars, BASELINES["XAUUSD"])
    assert late.anchor_utc == _t(13, 0)
    assert late.baseline == 2.0
    assert late.verdict == "no_move"
    # detected 12:58:30 -> minute 12:59, hour 12 (baseline 1.0)
    bars = {_t(12, 59): 100.0, _t(13, 4): 101.5}
    early = lg.grade_cell(1, "XAUUSD", "detected", _t(12, 58, 30), "buy", bars, BASELINES["XAUUSD"])
    assert early.baseline == 1.0
    assert early.verdict == "right"


def test_right_wrong_by_sign():
    bars = {_t(12, 31): 100.0, _t(12, 36): 101.5}
    right = lg.grade_cell(7, "XAUUSD", "detected", _t(12, 30, 40), "buy", bars, BASELINES["XAUUSD"])
    assert right.verdict == "right"
    assert right.move == 1.5
    assert right.moved is True
    assert (right.p0, right.p_end) == (100.0, 101.5)
    assert right.window_minutes == lg.GRADE_WINDOW_MINUTES == 5
    assert right.baseline_multiple == 1.0
    wrong = lg.grade_cell(7, "XAUUSD", "detected", _t(12, 30, 40), "sell", bars, BASELINES["XAUUSD"])
    assert wrong.verdict == "wrong"
    assert wrong.moved is True


def test_move_equal_to_baseline_is_no_move():
    bars = {_t(12, 31): 100.0, _t(12, 36): 101.0}
    grade = lg.grade_cell(1, "XAUUSD", "detected", _t(12, 30, 40), "buy", bars, BASELINES["XAUUSD"])
    assert grade.move == 1.0
    assert grade.verdict == "no_move"
    assert grade.moved is False


def test_missing_bar_is_no_data_never_neighbour():
    bars = {_t(12, 31): 100.0, _t(12, 37): 105.0}
    grade = lg.grade_cell(1, "XAUUSD", "detected", _t(12, 30, 40), "buy", bars, BASELINES["XAUUSD"])
    assert grade.verdict == "no_data"
    assert grade.p_end is None
    assert grade.move is None
    assert grade.moved is None


def test_no_baseline_for_hour():
    bars = {_t(15, 1): 100.0, _t(15, 6): 150.0}             # a huge move, but no hour-15 baseline
    grade = lg.grade_cell(1, "XAUUSD", "detected", _t(15, 0, 30), "buy", bars, BASELINES["XAUUSD"])
    assert grade.verdict == "no_baseline"
    assert grade.baseline is None
    assert grade.move == 50.0
    assert grade.moved is None


def test_mixed_and_absent_leans_are_no_lean_with_move():
    bars = {_t(12, 31): 100.0, _t(12, 36): 101.5}
    for lean in ("mixed", None, "none"):
        grade = lg.grade_cell(1, "XAUUSD", "detected", _t(12, 30, 40), lean, bars, BASELINES["XAUUSD"])
        assert grade.verdict == "no_lean"
        assert grade.lean == lean
        assert grade.move == 1.5
        assert grade.moved is True

    conn = store.get_connection(":memory:")
    alert_id = _alert(conn, _t(12, 30, 40), _t(12, 30),
                      [{"symbol": "US30", "lean": "sell"}, {"symbol": "XAUUSD", "lean": "mixed"}])
    alert = store.get_alert(conn, alert_id)
    assert lg.stored_lean(alert, "XAUUSD") == "mixed"
    assert lg.stored_lean(alert, "US30") == "sell"
    assert lg.stored_lean(alert, "EURUSD") is None
    no_key = store.get_alert(conn, _alert(conn, _t(12, 30, 40), _t(12, 30), [{"symbol": "XAUUSD"}]))
    assert lg.stored_lean(no_key, "XAUUSD") is None

    # A symbol absent from affected_symbols is still graded (no_lean) with its measured move.
    fetch = FakeFetch({"XAUUSD": bars, "US30": {}})
    lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, fetch, NOW, resolve=_resolve)
    assert {g["verdict"] for g in _rows(conn) if g["alert_id"] == alert_id} == {"no_lean"}
    absent_id = store.record_alert(
        conn, headline="X", source="s", url="u", published_utc=_t(12, 30), detected_at_utc=_t(12, 30, 40),
        category="energy", severity="Low", classification_method="llm", rationale=None,
        affected_symbols=[{"symbol": "US30", "lean": "sell"}],
    )
    lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, fetch, NOW, resolve=_resolve)
    grades = {(g["alert_id"], g["anchor"]): g for g in _rows(conn)}
    absent = grades[(absent_id, "detected")]
    assert absent["verdict"] == "no_lean"
    assert absent["lean"] is None
    assert absent["move"] == 1.5


def test_published_and_detected_anchors_graded_separately():
    conn = store.get_connection(":memory:")
    alert_id = _alert(conn, _t(12, 30, 40), _t(12, 20, 10), [{"symbol": "XAUUSD", "lean": "buy"}])
    bars = {_t(12, 21): 100.0, _t(12, 26): 100.5, _t(12, 31): 100.0, _t(12, 36): 101.5}
    lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, FakeFetch({"XAUUSD": bars}), NOW, resolve=_resolve)
    rows = {r["anchor"]: r for r in _rows(conn) if r["alert_id"] == alert_id}
    assert rows["published"]["anchor_utc"] == _t(12, 21).isoformat()
    assert rows["detected"]["anchor_utc"] == _t(12, 31).isoformat()
    assert rows["published"]["move"] == 0.5
    assert rows["published"]["verdict"] == "no_move"
    assert rows["detected"]["move"] == 1.5
    assert rows["detected"]["verdict"] == "right"

    # A publication time over 7 days before detection is treated as unknown.
    stale_id = _alert(conn, _t(12, 30, 40), _t(12, 30, 40) - dt.timedelta(days=8), [{"symbol": "XAUUSD", "lean": "buy"}])
    stale = store.get_alert(conn, stale_id)
    assert lg.anchor_time(stale, "published") is None
    assert lg.anchor_time(stale, "detected") == _t(12, 30, 40)
    lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, FakeFetch({"XAUUSD": bars}), NOW, resolve=_resolve)
    rows = {r["anchor"]: r for r in _rows(conn) if r["alert_id"] == stale_id}
    assert rows["published"]["verdict"] == "no_data"
    assert rows["published"]["anchor_utc"] is None
    assert rows["detected"]["verdict"] == "right"


# --- the batch job -------------------------------------------------------------------------

def test_pending_cells_are_not_written():
    conn = store.get_connection(":memory:")
    _alert(conn, _t(12, 30, 40), _t(12, 30, 40), [{"symbol": "XAUUSD", "lean": "buy"}])
    bars = {_t(12, 31): 100.0, _t(12, 34): 100.2}           # feed has not reached 12:36 yet
    fetch = FakeFetch({"XAUUSD": bars})
    first = lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, fetch, NOW, resolve=_resolve)
    assert first["written"] == 0
    assert first["pending"] == 2                             # both anchors are the same minute here
    assert _rows(conn) == []

    fetch.bars["XAUUSD"][_t(12, 36)] = 101.5
    second = lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, fetch, NOW, resolve=_resolve)
    assert second["written"] == 2
    assert second["pending"] == 0
    assert {r["verdict"] for r in _rows(conn)} == {"right"}


def test_recent_cells_wait_for_the_pending_margin():
    conn = store.get_connection(":memory:")
    detected = _t(12, 30, 40)
    _alert(conn, detected, detected, [{"symbol": "XAUUSD", "lean": "buy"}])
    bars = _flat_bars(_t(12, 0), _t(12, 50))
    now = _t(12, 36) + lg.PENDING_MARGIN - dt.timedelta(seconds=1)   # m+5 is later than now - 10 min
    fetch = FakeFetch({"XAUUSD": bars})
    result = lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, fetch, now, resolve=_resolve)
    assert result["written"] == 0
    assert result["pending"] == 2
    assert fetch.calls == []                                 # nothing due, so no fetch at all
    assert lg.is_pending(detected, _t(12, 50), now) is True
    assert lg.is_pending(detected, _t(12, 50), _t(12, 46)) is False
    assert lg.is_pending(detected, _t(12, 35), _t(12, 46)) is True
    assert lg.is_pending(None, None, now) is False


def test_rerun_writes_zero():
    conn = store.get_connection(":memory:")
    _alert(conn, _t(12, 30, 40), _t(12, 20, 10), [{"symbol": "XAUUSD", "lean": "buy"}])
    fetch = FakeFetch({"XAUUSD": _flat_bars(_t(12, 0), _t(13, 0))})
    first = lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, fetch, NOW, resolve=_resolve)
    assert first["written"] == 2
    count = conn.execute("SELECT COUNT(*) FROM shock_alert_grades").fetchone()[0]
    calls = len(fetch.calls)
    second = lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, fetch, NOW, resolve=_resolve)
    assert second["written"] == 0
    assert second["already_present"] == 2
    assert conn.execute("SELECT COUNT(*) FROM shock_alert_grades").fetchone()[0] == count
    assert len(fetch.calls) == calls                         # nothing to do: no fetch


def test_every_alert_gets_every_symbol_and_anchor():
    conn = store.get_connection(":memory:")
    _alert(conn, _t(12, 30, 40), _t(12, 20, 10), [{"symbol": "XAUUSD", "lean": "buy"}, {"symbol": "US30", "lean": "sell"}], "High")
    _alert(conn, _t(12, 40, 5), _t(12, 39), [{"symbol": "XAUUSD", "lean": "mixed"}, {"symbol": "US30", "lean": "mixed"}], "Medium")
    _alert(conn, _t(13, 2, 0), _t(13, 0), [{"symbol": "US30", "lean": "sell"}], "Low")
    bars = _flat_bars(_t(12, 0), _t(13, 30))
    fetch = FakeFetch({"XAUUSD": bars, "US30": bars})
    result = lg.grade_pending_alerts(conn, ["US30", "XAUUSD"], BASELINES, fetch, NOW, resolve=_resolve)
    assert result["written"] == 12
    keys = {(r["alert_id"], r["symbol"], r["anchor"]) for r in _rows(conn)}
    assert len(keys) == 12
    assert {r["window_minutes"] for r in _rows(conn)} == {5}
    # one fetch per symbol, from the earliest todo anchor minute to now
    assert sorted(call[0] for call in fetch.calls) == ["US30", "XAUUSD"]
    assert all(call[1] == _t(12, 21) and call[2] == NOW for call in fetch.calls)


def test_fetch_failure_writes_nothing_for_that_symbol():
    conn = store.get_connection(":memory:")
    _alert(conn, _t(12, 30, 40), _t(12, 20, 10), [{"symbol": "XAUUSD", "lean": "buy"}, {"symbol": "US30", "lean": "sell"}])
    bars = _flat_bars(_t(12, 0), _t(13, 0))
    fetch = FakeFetch({"XAUUSD": bars, "US30": bars}, fail=("XAUUSD",))
    result = lg.grade_pending_alerts(conn, ["US30", "XAUUSD"], BASELINES, fetch, NOW, resolve=_resolve)
    assert set(result["fetch_failed"]) == {"XAUUSD"}
    assert "feed down" in result["fetch_failed"]["XAUUSD"]
    assert {r["symbol"] for r in _rows(conn)} == {"US30"}
    assert result["written"] == 2

    # An empty result counts as a failure too.
    conn2 = store.get_connection(":memory:")
    _alert(conn2, _t(12, 30, 40), _t(12, 20, 10), [{"symbol": "XAUUSD", "lean": "buy"}])
    empty = lg.grade_pending_alerts(conn2, ["XAUUSD"], BASELINES, FakeFetch({"XAUUSD": {}}), NOW, resolve=_resolve)
    assert set(empty["fetch_failed"]) == {"XAUUSD"}
    assert _rows(conn2) == []


def test_unresolvable_symbol_is_no_data():
    conn = store.get_connection(":memory:")
    leaned = _alert(conn, _t(12, 30, 40), _t(12, 20, 10), [{"symbol": "XAUUSD", "lean": "buy"}])
    unleaned = _alert(conn, _t(12, 40, 40), _t(12, 40), [{"symbol": "US30", "lean": "sell"}])
    fetch = FakeFetch({"XAUUSD": _flat_bars(_t(12, 0), _t(13, 0))})
    result = lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, fetch, NOW, resolve=lambda symbol: None)
    assert fetch.calls == []
    assert result["written"] == 4
    verdicts = {(r["alert_id"], r["anchor"]): r["verdict"] for r in _rows(conn)}
    assert verdicts[(leaned, "published")] == verdicts[(leaned, "detected")] == "no_data"
    assert verdicts[(unleaned, "published")] == verdicts[(unleaned, "detected")] == "no_lean"


def test_grading_never_writes_alert_rows():
    conn = store.get_connection(":memory:")
    _alert(conn, _t(12, 30, 40), _t(12, 20, 10), [{"symbol": "XAUUSD", "lean": "buy"}])
    _alert(conn, _t(12, 40, 40), _t(12, 40), [{"symbol": "US30", "lean": "mixed"}], "Medium")
    before = [tuple(r) for r in conn.execute("SELECT * FROM shock_alerts ORDER BY id").fetchall()]
    bars = _flat_bars(_t(12, 0), _t(13, 0))
    lg.grade_pending_alerts(conn, ["US30", "XAUUSD"], BASELINES, FakeFetch({"XAUUSD": bars, "US30": bars}),
                            NOW, resolve=_resolve)
    after = [tuple(r) for r in conn.execute("SELECT * FROM shock_alerts ORDER BY id").fetchall()]
    assert after == before


def test_dry_run_counts_without_writing():
    conn = store.get_connection(":memory:")
    _alert(conn, _t(12, 30, 40), _t(12, 20, 10), [{"symbol": "XAUUSD", "lean": "buy"}])
    bars = {_t(12, 21): 100.0, _t(12, 26): 100.0, _t(12, 31): 100.0, _t(12, 36): 101.5}
    result = lg.grade_pending_alerts(conn, ["XAUUSD"], BASELINES, FakeFetch({"XAUUSD": bars}), NOW,
                                     dry_run=True, resolve=_resolve)
    assert result["written"] == 2
    assert result["counts"]["overall"]["detected"]["right"] == 1
    assert result["counts"]["overall"]["published"]["no_move"] == 1
    assert _rows(conn) == []


# --- summaries -----------------------------------------------------------------------------

def _grade(verdict: str, anchor: str = "detected", symbol: str = "XAUUSD") -> dict:
    return {"symbol": symbol, "anchor": anchor, "window_minutes": 5, "verdict": verdict}


def test_summary_counts_only_right_wrong_in_n():
    grades = ([_grade("right")] * 5 + [_grade("wrong")] * 3 + [_grade("no_move")] * 4
              + [_grade("no_lean")] * 6 + [_grade("no_data")])
    summary = lg.summarize_grades(grades)
    detected = summary["overall"]["detected"]
    assert detected == {"n": 8, "right": 5, "wrong": 3, "hit_rate": 0.625, "no_move": 4, "no_lean": 6,
                        "no_data": 1, "no_baseline": 0}
    assert summary["overall"]["published"] == lg.empty_counts()
    assert summary["overall"]["published"]["n"] == 0
    assert summary["overall"]["published"]["hit_rate"] is None
    assert summary["by_symbol"]["XAUUSD"]["detected"]["n"] == 8
    assert set(lg.empty_counts()) == {"n", "right", "wrong", "hit_rate", "no_move", "no_lean", "no_data", "no_baseline"}

    as_grade = lg.Grade(alert_id=1, symbol="US30", anchor="published", window_minutes=5, lean="sell",
                        anchor_utc=None, p0=None, p_end=None, move=None, baseline=None,
                        baseline_multiple=1.0, moved=None, verdict="right")
    mixed = lg.summarize_grades([as_grade, _grade("wrong", "published", "US30"), _grade("right", "published", "US30")])
    assert mixed["by_symbol"]["US30"]["published"]["hit_rate"] == 0.6667


def test_incident_summary_groups_by_incident_id():
    conn = store.get_connection(":memory:")
    root = _alert(conn, _t(12, 30, 40), _t(12, 30), [{"symbol": "XAUUSD", "lean": "buy"}], headline="Root")
    follow = _alert(conn, _t(12, 50, 0), _t(12, 49), [{"symbol": "XAUUSD", "lean": "mixed"}],
                    incident_id=root, headline="Follow-up")
    solo = _alert(conn, _t(9, 0, 0, day=4), _t(8, 59, day=4), [{"symbol": "XAUUSD", "lean": "sell"}], headline="Solo")
    alerts = [store.get_alert(conn, i) for i in (solo, follow, root)]          # newest first, as the route lists
    grades = {
        root: [_grade("right"), _grade("wrong", "published")],
        follow: [_grade("right"), _grade("no_lean", "published")],
        solo: [_grade("wrong")],
    }
    incidents = lg.summarize_incidents(alerts, grades)
    assert [i["incident_id"] for i in incidents] == [solo, root]
    first = incidents[1]
    assert set(first) == {"incident_id", "headline", "first_detected_utc", "alerts", "published", "detected"}
    assert first["headline"] == "Root"
    assert first["first_detected_utc"] == _t(12, 30, 40).isoformat()
    assert first["alerts"] == 2
    assert first["detected"]["right"] == 2
    assert first["detected"]["n"] == 2
    assert first["published"]["wrong"] == 1
    assert first["published"]["no_lean"] == 1
    assert incidents[0]["detected"]["wrong"] == 1


def test_format_summary_line_exact():
    grades = ([_grade("right")] * 5 + [_grade("wrong")] * 3 + [_grade("no_move")] * 4
              + [_grade("right", "published")] * 2 + [_grade("no_lean", "published")] * 6
              + [_grade("no_data", "published")] + [_grade("no_baseline", "published")])
    result = {"written": 22, "pending": 3, "already_present": 0, "fetch_failed": {},
              "counts": lg.summarize_grades(grades)}
    assert lg.format_summary_line(result) == (
        "graded 22: right 7, wrong 3, no_move 4, no_lean 6, no_data 1, no_baseline 1; "
        "hit rate 70.0% (7 of 10); detected 62.5% (5 of 8); pending 3"
    )
    empty = {"written": 0, "pending": 0, "already_present": 4, "fetch_failed": {"XAUUSD": "boom", "US30": "x"},
             "counts": lg.summarize_grades([])}
    assert lg.format_summary_line(empty) == (
        "graded 0: right 0, wrong 0, no_move 0, no_lean 0, no_data 0, no_baseline 0; "
        "hit rate n/a (0 of 0); detected n/a (0 of 0); pending 0; fetch failed: US30, XAUUSD"
    )


# --- read-only loaders ---------------------------------------------------------------------

def test_baselines_and_symbols_read_only(tmp_path):
    from scoring import backtest_store
    from webapp import store as web_store

    bt_path = tmp_path / "backtest_log.db"
    bt = backtest_store.get_connection(bt_path)
    for hour, value in ((12, 1.0), (13, 2.0)):
        backtest_store.record_reaction_baseline(bt, "XAUUSD", hour, value, 40, _t(0, 0, day=1), _t(0, 0, day=2),
                                                quantile=0.75)
    backtest_store.record_reaction_baseline(bt, "XAUUSD", 12, 9.0, 40, _t(0, 0, day=1), _t(0, 0, day=2),
                                            quantile=0.5)                    # another quantile: ignored
    bt.close()
    dash_path = tmp_path / "dashboard.db"
    dash = web_store.get_connection(dash_path)
    for symbol in ("XAUUSD", "US30"):
        web_store.add_tracked_symbol(dash, symbol)
    dash.close()
    empty_path = tmp_path / "empty.db"
    sqlite3.connect(empty_path).close()

    before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in (bt_path, dash_path, empty_path)}
    assert lg.load_baselines(bt_path, ["XAUUSD", "US30"]) == {"XAUUSD": {12: 1.0, 13: 2.0}, "US30": {}}
    assert lg.load_baselines(empty_path, ["XAUUSD"]) == {"XAUUSD": {}}       # table absent
    assert lg.load_tracked_symbols(dash_path) == ["US30", "XAUUSD"]
    after = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in (bt_path, dash_path, empty_path)}
    assert after == before

    ro = lg.open_readonly(bt_path)
    assert isinstance(ro.execute("SELECT 1 AS one").fetchone(), sqlite3.Row)
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("DELETE FROM reaction_baselines")
    ro.close()


def test_dry_run_on_readonly_pre_b10_db_works(tmp_path):
    """A read-only dry run against an alerts DB that has no grade table yet sees no graded keys."""
    path = tmp_path / "alerts.db"
    raw = sqlite3.connect(path)
    raw.executescript(store._SCHEMA.split("CREATE TABLE IF NOT EXISTS shock_alert_grades")[0])
    raw.commit()
    raw.close()
    store._schema_ready_paths.clear()
    ro = lg.open_readonly(path)
    assert store.graded_keys(ro) == set()
    assert store.latest_grading_run(ro) is None
    result = lg.grade_pending_alerts(ro, ["XAUUSD"], BASELINES, FakeFetch({}), NOW, dry_run=True, resolve=_resolve)
    assert result["written"] == 0
    ro.close()


def test_verdicts_and_constants():
    assert lg.ANCHORS == ("published", "detected")
    assert lg.VERDICTS == ("right", "wrong", "no_move", "no_lean", "no_data", "no_baseline")
    assert lg.PENDING_MARGIN == dt.timedelta(minutes=10)
    assert lg.MAX_PUBLICATION_LAG == dt.timedelta(days=7)
