"""
Tests for scripts/tier1_research.py (B3 Task 4): the research task's plan / record-call / record-late-check CLI.
Temp DB files under tmp_path, `now` injected, no network.
"""
import datetime as dt
import json

from scoring import backtest_store as bs
from scripts import tier1_research as cli
from webapp import store as ws

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 5, 6, 0, tzinfo=UTC)
RELEASE = dt.datetime(2026, 11, 12, 13, 30, tzinfo=UTC)      # 7d 7.5h after NOW


def _event(dash, title, when, country="USD", impact="High"):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), "0.3%", "0.2%", None, None, when.isoformat(), when.isoformat(), "t", impact, country))
    dash.commit()


def _setup(tmp_path, events=(("PPI m/m", RELEASE),), foreign=()):
    """Returns (dash_path, bt_path); XAUUSD and US30 tracked, `events` are USD rows, `foreign` are EUR rows."""
    dash_path, bt_path = tmp_path / "dash.db", tmp_path / "bt.db"
    dash = ws.get_connection(str(dash_path))
    for symbol in ("XAUUSD", "US30"):
        ws.add_tracked_symbol(dash, symbol)
    for title, when in events:
        _event(dash, title, when)
    for title, when in foreign:
        _event(dash, title, when, country="EUR")
    dash.close()
    return dash_path, bt_path


def _db(paths):
    return ["--dash-db", str(paths[0]), "--bt-db", str(paths[1])]


def _plan(paths, capsys, now=NOW):
    assert cli.main(["plan", *_db(paths)], now=now) == 0
    return json.loads(capsys.readouterr().out)


def _call_args(paths, title="PPI m/m", release=RELEASE, instrument="XAUUSD", direction="bullish"):
    return [*_db(paths), "--event", title, "--release", release.isoformat(), "--instrument", instrument,
            "--value", "PPI expected soft", "--confidence", "Likely", "--source", "BLS/consensus",
            "--direction", direction]


def _log_call(paths, logged_at, direction="bullish", title="PPI m/m", release=RELEASE, instrument="XAUUSD"):
    conn = bs.get_connection(paths[1])
    try:
        bs.record_tier1_prediction(conn, title, instrument, release, "v", "Likely", "src", direction,
                                   logged_at_utc=logged_at)
    finally:
        conn.close()


def _count(paths, table="tier1_predictions"):
    conn = bs.get_connection(paths[1])
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_plan_lists_only_judgment_titles(tmp_path, capsys):
    paths = _setup(
        tmp_path,
        [("CPI m/m", RELEASE), ("Core CPI m/m", RELEASE), ("PPI m/m", RELEASE),
         ("Final GDP q/q", RELEASE + dt.timedelta(hours=1)), ("Unemployment Claims", RELEASE)],
        foreign=[("PPI m/m", RELEASE + dt.timedelta(days=1))])
    out = _plan(paths, capsys)
    assert [e["event_title"] for e in out] == ["PPI m/m", "Final GDP q/q"]
    assert out[0]["tier"] == "judgment" and out[0]["event_time_sast"] == "2026-11-12 15:30 SAST"
    assert set(out[0]["instruments"]) == {"XAUUSD", "US30"}


def test_plan_window_is_8_days_and_excludes_past_events(tmp_path, capsys):
    events = [("PPI m/m", NOW + dt.timedelta(hours=191)), ("Final GDP q/q", NOW + dt.timedelta(hours=193)),
              ("ISM Services PMI", NOW - dt.timedelta(minutes=1))]
    out = _plan(_setup(tmp_path, events), capsys)
    assert [e["event_title"] for e in out] == ["PPI m/m"]


def test_plan_status_needs_call_covered_and_late_check_due(tmp_path, capsys):
    paths = _setup(tmp_path)
    assert _plan(paths, capsys)[0]["instruments"]["XAUUSD"] == {"status": "needs_call"}
    _log_call(paths, NOW - dt.timedelta(days=3))
    inst = _plan(paths, capsys)[0]["instruments"]
    assert inst["XAUUSD"]["status"] == "covered" and inst["XAUUSD"]["call"]["predicted_direction"] == "bullish"
    assert set(inst["XAUUSD"]["call"]) == {"id", "value", "confidence", "source", "predicted_direction", "logged_at_utc"}
    assert inst["US30"] == {"status": "needs_call"}
    inst = _plan(paths, capsys, now=NOW + dt.timedelta(days=4))[0]["instruments"]      # call is now 7 days old
    assert inst["XAUUSD"]["status"] == "late_check_due" and inst["XAUUSD"]["reason"] == "stale_call"


def test_plan_flags_a_call_that_is_stale_inside_24h_of_the_release(tmp_path, capsys):
    paths = _setup(tmp_path)
    eve = RELEASE - dt.timedelta(hours=23)
    _log_call(paths, eve - dt.timedelta(days=3))
    inst = _plan(paths, capsys, now=eve)[0]["instruments"]
    assert inst["XAUUSD"]["status"] == "late_check_due" and inst["XAUUSD"]["reason"] == "release_within_24h"


def test_record_call_refuses_a_formula_title(tmp_path, capsys):
    paths = _setup(tmp_path, [("CPI m/m", RELEASE)])
    assert cli.main(["record-call", *_call_args(paths, title="CPI m/m")], now=NOW) == 2
    assert "formula" in capsys.readouterr().err.lower()
    assert _count(paths) == 0


def test_record_call_writes_the_first_call(tmp_path, capsys):
    paths = _setup(tmp_path)
    assert cli.main(["record-call", *_call_args(paths)], now=NOW) == 0
    assert capsys.readouterr().out.strip().isdigit() and _count(paths) == 1
    conn = bs.get_connection(paths[1])
    row = bs.get_latest_tier1_prediction_for_occurrence(conn, "PPI m/m", "XAUUSD", RELEASE)
    assert row.logged_at_utc == NOW.isoformat()


def test_record_call_refuses_a_second_pre_release_call_and_a_past_release(tmp_path, capsys):
    paths = _setup(tmp_path)
    assert cli.main(["record-call", *_call_args(paths)], now=NOW) == 0
    capsys.readouterr()
    assert cli.main(["record-call", *_call_args(paths, direction="bearish")], now=NOW) == 2
    assert "first pre-release call stands" in capsys.readouterr().err
    assert _count(paths) == 1
    assert cli.main(["record-call", *_call_args(paths, instrument="US30")], now=RELEASE) == 2
    assert _count(paths) == 1


def test_record_late_check_records_changed_without_touching_the_call(tmp_path, capsys):
    paths = _setup(tmp_path)
    _log_call(paths, NOW - dt.timedelta(days=2))
    now = NOW + dt.timedelta(days=4)
    assert cli.main(["record-late-check", *_call_args(paths, direction="bearish")], now=now) == 0
    assert "changed (stale_call)" in capsys.readouterr().out
    assert _count(paths) == 1 and _count(paths, "tier1_late_checks") == 1


def test_record_late_check_refuses_when_not_due(tmp_path, capsys):
    paths = _setup(tmp_path)
    _log_call(paths, NOW - dt.timedelta(days=2))
    now = NOW + dt.timedelta(days=4)
    assert cli.main(["record-late-check", *_call_args(paths)], now=now) == 0
    capsys.readouterr()
    assert cli.main(["record-late-check", *_call_args(paths)], now=now + dt.timedelta(hours=1)) == 2
    assert "not due" in capsys.readouterr().err
    assert _count(paths, "tier1_late_checks") == 1


def test_record_late_check_refuses_without_a_call_of_record(tmp_path, capsys):
    paths = _setup(tmp_path)
    assert cli.main(["record-late-check", *_call_args(paths)], now=NOW) == 2
    assert "no call of record" in capsys.readouterr().err
    assert _count(paths, "tier1_late_checks") == 0


def test_unknown_instrument_and_naive_release_are_refused(tmp_path, capsys):
    paths = _setup(tmp_path)
    assert cli.main(["record-call", *_call_args(paths, instrument="EURUSD")], now=NOW) == 2
    assert "not tracked" in capsys.readouterr().err
    naive = _call_args(paths)
    naive[naive.index("--release") + 1] = "2026-11-12T13:30:00"
    assert cli.main(["record-call", *naive], now=NOW) == 2
    assert "UTC offset" in capsys.readouterr().err
    assert _count(paths) == 0
