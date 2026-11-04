"""
Tests for scripts/tier1_research.py (B3 Task 4): the research task's plan / record-call / record-late-check CLI.
Temp DB files under tmp_path, `now` injected, no network.
"""
import datetime as dt
import json
from unittest.mock import MagicMock

import pytest

from ops import state as ops_state
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


def _setup(tmp_path, events=(("ISM Services PMI", RELEASE),), foreign=()):
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


def _call_args(paths, title="ISM Services PMI", release=RELEASE, instrument="XAUUSD", direction="bullish"):
    return [*_db(paths), "--event", title, "--release", release.isoformat(), "--instrument", instrument,
            "--value", "ISM Services expected soft", "--confidence", "Likely", "--source", "BLS/consensus",
            "--direction", direction]


def _log_call(paths, logged_at, direction="bullish", title="ISM Services PMI", release=RELEASE, instrument="XAUUSD"):
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
        [("CPI m/m", RELEASE), ("Core CPI m/m", RELEASE), ("ISM Services PMI", RELEASE),
         ("Final GDP q/q", RELEASE + dt.timedelta(hours=1)), ("Unemployment Claims", RELEASE)],
        foreign=[("ISM Services PMI", RELEASE + dt.timedelta(days=1))])
    out = _plan(paths, capsys)
    assert [e["event_title"] for e in out] == ["ISM Services PMI", "Final GDP q/q"]
    assert out[0]["tier"] == "judgment" and out[0]["event_time_sast"] == "2026-11-12 15:30 SAST"
    assert set(out[0]["instruments"]) == {"XAUUSD", "US30"}


def test_plan_window_is_8_days_and_excludes_past_events(tmp_path, capsys):
    events = [("ISM Services PMI", NOW + dt.timedelta(hours=191)), ("Final GDP q/q", NOW + dt.timedelta(hours=193)),
              ("FOMC Statement", NOW - dt.timedelta(minutes=1))]
    out = _plan(_setup(tmp_path, events), capsys)
    assert [e["event_title"] for e in out] == ["ISM Services PMI"]


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


def test_plan_excludes_market_implied_titles(tmp_path, capsys):
    # B12: the Kalshi capture writes these; the research task must not even see them.
    paths = _setup(tmp_path, [("Non-Farm Employment Change", RELEASE), ("PPI m/m", RELEASE),
                              ("Federal Funds Rate", RELEASE), ("ISM Services PMI", RELEASE)])
    assert [e["event_title"] for e in _plan(paths, capsys)] == ["ISM Services PMI"]


def test_record_call_refuses_a_market_implied_title(tmp_path, capsys):
    paths = _setup(tmp_path, [("Non-Farm Employment Change", RELEASE)])
    assert cli.main(["record-call", *_call_args(paths, title="Non-Farm Employment Change")], now=NOW) == 2
    assert ("'Non-Farm Employment Change' is a market-implied event: the Kalshi capture (capture_tier1.py) "
            "writes its call, do not log one by hand") in capsys.readouterr().err
    assert _count(paths) == 0


def test_record_call_writes_the_first_call(tmp_path, capsys):
    paths = _setup(tmp_path)
    assert cli.main(["record-call", *_call_args(paths)], now=NOW) == 0
    assert capsys.readouterr().out.strip().isdigit() and _count(paths) == 1
    conn = bs.get_connection(paths[1])
    row = bs.get_latest_tier1_prediction_for_occurrence(conn, "ISM Services PMI", "XAUUSD", RELEASE)
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


def test_non_utc_release_offset_is_normalised_to_utc(tmp_path, capsys):
    """+02:00 spelling must store the +00:00 key, so it is found and a +00:00 repeat is refused as a second call."""
    paths = _setup(tmp_path)
    args = _call_args(paths)
    args[args.index("--release") + 1] = "2026-11-12T15:30:00+02:00"
    assert cli.main(["record-call", *args], now=NOW) == 0
    capsys.readouterr()
    conn = bs.get_connection(paths[1])
    try:
        stored = conn.execute("SELECT event_time_utc FROM tier1_predictions").fetchone()[0]
    finally:
        conn.close()
    assert stored == "2026-11-12T13:30:00+00:00"
    assert cli.main(["record-call", *_call_args(paths, direction="bearish")], now=NOW) == 2
    assert "first pre-release call stands" in capsys.readouterr().err
    assert _count(paths) == 1


def test_plan_includes_unconfirmed_judgment_release(tmp_path, capsys):
    paths = _setup(tmp_path, [("ISM Services PMI", dt.datetime(2026, 11, 24, 15, 0, tzinfo=UTC))])
    dash = ws.get_connection(str(paths[0]))
    ws.upsert_macro_calendar_event(dash, "Prelim GDP q/q", "2026-11-25", "2026-11-25T12:30:00+00:00",
                                   "history_derived", NOW)
    ws.upsert_macro_calendar_event(dash, "Prelim GDP q/q", "2026-10-29", "2026-10-29T12:30:00+00:00",
                                   "history_derived", NOW)               # phantom: October is the advance estimate
    dash.close()
    out = _plan(paths, capsys, now=dt.datetime(2026, 11, 20, 6, 0, tzinfo=UTC))
    assert [e["event_title"] for e in out] == ["ISM Services PMI", "Prelim GDP q/q"]
    gdp = out[1]
    assert gdp["unconfirmed"] is True and gdp["event_time_utc"] == "2026-11-25T13:30:00+00:00"
    assert gdp["event_time_sast"] == "2026-11-25 15:30 SAST" and gdp["tier"] == "judgment"
    assert gdp["instruments"] == {"XAUUSD": {"status": "needs_call"}, "US30": {"status": "needs_call"}}
    assert "unconfirmed" not in out[0]


# ---------------------------------------------------------------------------
# FIX Task 7: research heartbeat on plan, and the alert command
# ---------------------------------------------------------------------------
def _ops(tmp_path):
    return ["--ops-db", str(tmp_path / "ops.db")]


def _alert_args(tmp_path, kind="security", event="ISM Services PMI", message="page asked for a login: https://x.example"):
    return ["alert", "--kind", kind, "--event", event, "--message", message, *_ops(tmp_path)]


def _alert_rows(tmp_path):
    conn = ops_state.get_connection(tmp_path / "ops.db")
    try:
        return conn.execute("SELECT kind, event, message, telegram_sent FROM research_alerts ORDER BY id").fetchall()
    finally:
        conn.close()


def test_plan_records_the_heartbeat(tmp_path, capsys):
    paths = _setup(tmp_path)
    assert cli.main(["plan", *_db(paths), *_ops(tmp_path)], now=NOW) == 0
    json.loads(capsys.readouterr().out)
    conn = ops_state.get_connection(tmp_path / "ops.db")
    try:
        run = ops_state.get_job_runs(conn)["tier1_research"]
    finally:
        conn.close()
    assert run.last_success_utc == NOW and run.last_exit_code == 0


def test_plan_succeeds_when_heartbeat_write_fails(tmp_path, capsys):
    paths = _setup(tmp_path)
    broken = tmp_path / "no_such_dir" / "ops.db"              # sqlite cannot create the file: the write fails
    assert cli.main(["plan", *_db(paths), "--ops-db", str(broken)], now=NOW) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)[0]["event_title"] == "ISM Services PMI"     # stdout stays pure JSON
    assert "WARNING" in captured.err


def test_alert_sends_one_prefixed_message(tmp_path, monkeypatch, capsys):
    send = MagicMock(return_value=True)
    monkeypatch.setattr(cli.notify_telegram, "send_notice", send)
    assert cli.main(_alert_args(tmp_path), now=NOW) == 0
    send.assert_called_once_with(
        "Tier 1 research: SECURITY ALERT - ISM Services PMI: page asked for a login: https://x.example")
    assert [tuple(r) for r in _alert_rows(tmp_path)] == [
        ("security", "ISM Services PMI", "page asked for a login: https://x.example", 1)]


def test_alert_dedupes_identical_within_24h(tmp_path, monkeypatch, capsys):
    send = MagicMock(return_value=True)
    monkeypatch.setattr(cli.notify_telegram, "send_notice", send)
    assert cli.main(_alert_args(tmp_path), now=NOW) == 0
    capsys.readouterr()
    assert cli.main(_alert_args(tmp_path), now=NOW + dt.timedelta(hours=23)) == 0
    assert "duplicate, not sent" in capsys.readouterr().out
    assert send.call_count == 1 and len(_alert_rows(tmp_path)) == 1


def test_alert_sends_again_after_24h_or_with_new_text(tmp_path, monkeypatch):
    send = MagicMock(return_value=True)
    monkeypatch.setattr(cli.notify_telegram, "send_notice", send)
    assert cli.main(_alert_args(tmp_path), now=NOW) == 0
    assert cli.main(_alert_args(tmp_path), now=NOW + dt.timedelta(hours=25)) == 0
    assert cli.main(_alert_args(tmp_path, message="another page"), now=NOW + dt.timedelta(hours=26)) == 0
    assert send.call_count == 3 and len(_alert_rows(tmp_path)) == 3


def test_alert_retry_after_failed_send(tmp_path, monkeypatch):
    send = MagicMock(side_effect=[False, True])
    monkeypatch.setattr(cli.notify_telegram, "send_notice", send)
    assert cli.main(_alert_args(tmp_path), now=NOW) == 3
    assert [r["telegram_sent"] for r in _alert_rows(tmp_path)] == [0]       # recorded, so health still shows it
    assert cli.main(_alert_args(tmp_path), now=NOW + dt.timedelta(minutes=5)) == 0
    assert send.call_count == 2
    assert [r["telegram_sent"] for r in _alert_rows(tmp_path)] == [0, 1]


def test_alert_cuts_long_text(tmp_path, monkeypatch):
    send = MagicMock(return_value=True)
    monkeypatch.setattr(cli.notify_telegram, "send_notice", send)
    assert cli.main(_alert_args(tmp_path, message="x" * 5000), now=NOW) == 0
    assert len(send.call_args.args[0]) == cli.ALERT_MAX_CHARS


def test_alert_rejects_unknown_kind(tmp_path, monkeypatch):
    send = MagicMock(return_value=True)
    monkeypatch.setattr(cli.notify_telegram, "send_notice", send)
    with pytest.raises(SystemExit) as exc:
        cli.main(_alert_args(tmp_path, kind="panic"), now=NOW)
    assert exc.value.code == 2
    send.assert_not_called()


def test_alert_runs_without_dash_db(tmp_path, monkeypatch):
    """A broken or missing dash / backtest DB must not silence an alert: main never opens them for `alert`."""
    send = MagicMock(return_value=True)
    monkeypatch.setattr(cli.notify_telegram, "send_notice", send)
    monkeypatch.setattr(cli, "open_dash_readonly", MagicMock(side_effect=RuntimeError("dash db is gone")))
    monkeypatch.setattr(cli.backtest_store, "get_connection", MagicMock(side_effect=RuntimeError("bt db is gone")))
    assert cli.main(_alert_args(tmp_path, kind="blocked", event="run"), now=NOW) == 0
    assert send.call_args.args[0].startswith("Tier 1 research: RUN BLOCKED - run: ")
