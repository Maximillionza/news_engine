"""
Tests for scripts/capture_nowcast_from_cleveland.py. No network and no real DB: the Cleveland JSON is a small
synthetic file with the REAL structure (see tests/test_cleveland_nowcast_to_csv.py::_chart), fetch is injected,
and every database is in-memory or under tmp_path.
"""
import datetime as dt
from unittest.mock import MagicMock

import pytest

from scoring import backtest_store as bs
from scripts import capture_nowcast_from_cleveland as cap
from tests.test_cleveland_nowcast_to_csv import _chart
from webapp import store as ws

UTC = dt.timezone.utc
SOURCE = "Cleveland Fed Inflation Nowcasting (CC BY 4.0)"

# October 2026 CPI is released Thu 2026-11-12 13:30Z (winter time). "Now" is the morning of 11-11.
NOW = dt.datetime(2026, 11, 11, 6, 0, tzinfo=UTC)
RELEASE = dt.datetime(2026, 11, 12, 13, 30, tzinfo=UTC)
LABELS = ["10/30", "11/02", "11/03", "11/04", "11/05", "11/06", "11/09", "11/10", "11/11", "11/12"]
CPI = ["0.40", "0.41", "0.42", "0.43", "0.44", "0.45", "0.46", "0.47", "", ""]       # last real value: 11/10 = 0.47
CORE = ["0.20", "0.21", "0.22", "0.23", "", "0.24", "0.25", "0.26", "", ""]           # 11/05 blank; last: 11/10 = 0.26
OCT = _chart("2026-10", LABELS, CPI, CORE)                                             # not released: no actual
# September 2026 CPI (released 2026-10-14) already has its actual in the file.
SEP = _chart("2026-9", ["10/12", "10/13", "10/14"], ["0.5", "0.53", ""], ["0.2", "0.21", ""],
             actual_idx=2, release_marker="CPI Sep")
DATA = [SEP, OCT]


def _release_rows():
    return [("CPI m/m", RELEASE), ("Core CPI m/m", RELEASE)]


# --- pure parsing --------------------------------------------------------------------------------

def _by_title(readings):
    return {r["event_title"]: r for r in readings}


def test_latest_nowcasts_returns_the_last_non_blank_value_and_its_date_per_release():
    got = _by_title(cap.latest_nowcasts(DATA, _release_rows()))
    assert got["CPI m/m"]["value"] == pytest.approx(0.47) and got["CPI m/m"]["value_date"] == dt.date(2026, 11, 10)
    assert got["Core CPI m/m"]["value"] == pytest.approx(0.26) and got["Core CPI m/m"]["value_date"] == dt.date(2026, 11, 10)
    assert got["CPI m/m"]["reason"] is None and got["CPI m/m"]["release_utc"] == RELEASE


def test_a_blank_slot_in_the_middle_is_not_zero_filled_and_the_last_value_still_wins():
    chart = _chart("2026-10", LABELS, ["0.4", "", "", "", "", "", "", "", "", ""], CORE)
    got = _by_title(cap.latest_nowcasts([chart], _release_rows()))
    assert got["CPI m/m"]["value"] == pytest.approx(0.4) and got["CPI m/m"]["value_date"] == dt.date(2026, 10, 30)


def test_a_value_on_or_after_the_release_day_is_never_used():
    cpi = CPI[:8] + ["0.60", "0.99"]                                   # 11/11 and release-day 11/12 slots filled
    cpi_row = _by_title(cap.latest_nowcasts([_chart("2026-10", LABELS, cpi, CORE)], _release_rows()))["CPI m/m"]
    assert cpi_row["value"] == pytest.approx(0.60) and cpi_row["value_date"] == dt.date(2026, 11, 11)
    only_release_day = ["", "", "", "", "", "", "", "", "", "0.99"]                # nothing but the release-day slot
    row = _by_title(cap.latest_nowcasts([_chart("2026-10", LABELS, only_release_day, CORE)], _release_rows()))["CPI m/m"]
    assert row["value"] is None and "no nowcast" in row["reason"]


def test_year_boundary_uses_the_previous_december_chart():
    dec = _chart("2026-12", ["12/29", "12/30", "12/31", "01/04", "01/05"], ["0.3", "0.31", "0.32", "0.33", ""], ["0.2"] * 4 + [""])
    release = dt.datetime(2027, 1, 13, 13, 30, tzinfo=UTC)
    # 2027-01-13 falls in January, so the reference month is 2026-12; its labels roll into 2027.
    got = cap.latest_nowcasts([dec], [("CPI m/m", release)])[0]
    assert got["value"] == pytest.approx(0.33) and got["value_date"] == dt.date(2027, 1, 4)


def test_a_release_with_no_fed_chart_is_skipped_with_a_reason_not_guessed():
    got = cap.latest_nowcasts([SEP], _release_rows())            # no 2026-10 chart
    assert all(r["value"] is None and "2026-10" in r["reason"] for r in got)


def test_a_chart_that_already_shows_the_actual_is_not_captured():
    release = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
    got = cap.latest_nowcasts([SEP], [("CPI m/m", release)])[0]
    assert got["value"] is None and "already" in got["reason"]


def test_an_unparseable_last_value_is_skipped_with_no_fallback_to_an_earlier_one():
    chart = _chart("2026-10", LABELS, CPI[:7] + ["abc", "", ""], CORE)
    got = _by_title(cap.latest_nowcasts([chart], _release_rows()))
    assert got["CPI m/m"]["value"] is None and "parse" in got["CPI m/m"]["reason"]
    assert got["Core CPI m/m"]["value"] == pytest.approx(0.26)         # the other series is unaffected


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_non_finite_values_are_refused(bad):
    chart = _chart("2026-10", LABELS, CPI[:7] + [bad, "", ""], CORE)
    got = _by_title(cap.latest_nowcasts([chart], _release_rows()))
    assert got["CPI m/m"]["value"] is None and "parse" in got["CPI m/m"]["reason"]


def test_a_malformed_chart_is_a_skip_not_a_crash():
    broken = {"chart": {"subcaption": "2026-10"}, "categories": [{"category": [{"label": "10/30"}]}], "dataset": []}
    got = cap.latest_nowcasts([broken], _release_rows())
    assert all(r["value"] is None and r["reason"] for r in got)


def test_titles_outside_the_cpi_family_are_skipped():
    got = cap.latest_nowcasts(DATA, [("PPI m/m", RELEASE)])[0]
    assert got["value"] is None and "CPI-family" in got["reason"]


def test_a_non_list_json_document_is_rejected_loudly():
    with pytest.raises(ValueError):
        cap.latest_nowcasts({"not": "a list"}, _release_rows())


# --- run() ---------------------------------------------------------------------------------------

def _event(dash, title, when, country="USD"):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), "0.3%", "0.2%", None, None, when.isoformat(), when.isoformat(), "t", "High", country))
    dash.commit()


@pytest.fixture
def conns():
    return ws.get_connection(":memory:"), bs.get_connection(":memory:")


def _count(bt):
    return bt.execute("SELECT COUNT(*) FROM tier1_nowcast_snapshots").fetchone()[0]


def test_run_captures_a_live_snapshot_for_each_release_within_48_hours(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)
    _event(dash, "Core CPI m/m", RELEASE)
    fetch = MagicMock(return_value=DATA)
    summary = cap.run(dash, bt, NOW, fetch)
    fetch.assert_called_once_with()
    assert summary["skipped"] == []
    assert sorted(summary["captured"]) == [("CPI m/m", RELEASE.isoformat(), pytest.approx(0.47)),
                                           ("Core CPI m/m", RELEASE.isoformat(), pytest.approx(0.26))]
    rows = bt.execute("SELECT * FROM tier1_nowcast_snapshots ORDER BY event_title").fetchall()
    assert [(r["event_title"], r["nowcast_value"], r["kind"], r["source"]) for r in rows] == [
        ("CPI m/m", pytest.approx(0.47), "live", SOURCE), ("Core CPI m/m", pytest.approx(0.26), "live", SOURCE)]
    assert all(dt.datetime.fromisoformat(r["as_of_utc"]) == NOW for r in rows)         # as-of is the real fetch time
    assert bs.get_scored_nowcast_snapshot(bt, "CPI m/m", RELEASE)["nowcast_value"] == pytest.approx(0.47)


def test_run_does_nothing_and_does_not_even_fetch_when_no_release_is_within_48_hours(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", NOW + dt.timedelta(hours=48, seconds=1))        # just beyond the window
    _event(dash, "CPI m/m", NOW - dt.timedelta(days=30))                   # already released
    _event(dash, "Core CPI m/m", NOW)                                      # exactly now: not "after now"
    fetch = MagicMock(return_value=DATA)
    summary = cap.run(dash, bt, NOW, fetch)
    fetch.assert_not_called()
    assert summary["captured"] == [] and summary["skipped"] == [] and "no" in summary["message"].lower()
    assert _count(bt) == 0


def test_run_includes_a_release_exactly_48_hours_out(conns):
    dash, bt = conns
    edge = NOW + dt.timedelta(hours=48)                                   # 2026-11-13 06:00Z
    _event(dash, "CPI m/m", edge)
    chart = _chart("2026-10", LABELS + ["11/13"], CPI + [""], CORE + [""])
    summary = cap.run(dash, bt, NOW, lambda: [chart])
    assert [c[:2] for c in summary["captured"]] == [("CPI m/m", edge.isoformat())]


def test_run_ignores_non_usd_and_unattributed_rows(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE, country=None)
    _event(dash, "Core CPI m/m", RELEASE, country="EUR")
    fetch = MagicMock(return_value=DATA)
    summary = cap.run(dash, bt, NOW, fetch)
    fetch.assert_not_called()
    assert summary["captured"] == [] and _count(bt) == 0


def test_run_ignores_events_outside_the_cpi_family(conns):
    dash, bt = conns
    _event(dash, "PPI m/m", RELEASE)
    fetch = MagicMock(return_value=DATA)
    cap.run(dash, bt, NOW, fetch)
    fetch.assert_not_called()
    assert _count(bt) == 0


def test_dry_run_reports_but_writes_nothing_and_needs_no_bt_connection(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)
    summary = cap.run(dash, bt, NOW, lambda: DATA, dry_run=True)
    assert summary["dry_run"] is True and [c[0] for c in summary["captured"]] == ["CPI m/m"]
    assert _count(bt) == 0
    assert cap.run(dash, None, NOW, lambda: DATA, dry_run=True)["captured"] == summary["captured"]


def test_a_fetch_failure_raises_a_clear_error_and_writes_nothing(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)

    def down():
        raise ConnectionError("clevelandfed.org unreachable")
    with pytest.raises(cap.FetchError, match="clevelandfed.org unreachable"):
        cap.run(dash, bt, NOW, down)
    assert _count(bt) == 0


def test_a_document_of_the_wrong_shape_is_a_fetch_error_and_writes_nothing(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)
    with pytest.raises(cap.FetchError):
        cap.run(dash, bt, NOW, lambda: {"error": "maintenance"})
    assert _count(bt) == 0


def test_an_unparseable_value_is_skipped_and_never_written(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)
    _event(dash, "Core CPI m/m", RELEASE)
    bad = _chart("2026-10", LABELS, CPI[:7] + ["n/a", "", ""], CORE)
    summary = cap.run(dash, bt, NOW, lambda: [bad])
    assert [c[0] for c in summary["captured"]] == ["Core CPI m/m"]
    assert [s[0] for s in summary["skipped"]] == ["CPI m/m"] and "parse" in summary["skipped"][0][2]
    assert _count(bt) == 1


def test_a_stale_fed_value_is_skipped_rather_than_stamped_as_fetched_now(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)
    stale_now = dt.datetime(2026, 11, 11, 6, 0, tzinfo=UTC)
    old = _chart("2026-10", LABELS, ["0.40", "0.41", "", "", "", "", "", "", "", ""], CORE)    # last value 11/02
    summary = cap.run(dash, bt, stale_now, lambda: [old])
    assert summary["captured"] == [] and "stale" in summary["skipped"][0][2]
    assert _count(bt) == 0


def test_lookahead_refusal_from_capture_is_a_skip_and_writes_nothing(conns, monkeypatch):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)

    def refuse(*args, **kwargs):
        raise ValueError("as_of_utc is after the release: a snapshot taken after the print cannot be scored")
    monkeypatch.setattr(cap, "capture", refuse)
    summary = cap.run(dash, bt, NOW, lambda: DATA)
    assert summary["captured"] == [] and "after the release" in summary["skipped"][0][2]
    assert _count(bt) == 0


def test_the_real_capture_function_refuses_a_snapshot_after_the_release():
    bt = bs.get_connection(":memory:")
    with pytest.raises(ValueError, match="after the release"):
        cap.capture(bt, "CPI m/m", RELEASE, 0.47, as_of_utc=RELEASE + dt.timedelta(minutes=1), source=SOURCE)
    assert _count(bt) == 0


def test_a_later_run_adds_a_newer_snapshot_and_the_same_instant_adds_none(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)
    cap.run(dash, bt, NOW, lambda: DATA)
    cap.run(dash, bt, NOW, lambda: DATA)                                       # same instant: the store dedupes
    assert _count(bt) == 1
    later = NOW + dt.timedelta(hours=8)
    newer = _chart("2026-10", LABELS, CPI[:8] + ["0.55", ""], CORE)
    cap.run(dash, bt, later, lambda: [newer])
    assert _count(bt) == 2
    assert bs.get_scored_nowcast_snapshot(bt, "CPI m/m", RELEASE)["nowcast_value"] == pytest.approx(0.55)   # latest wins


def test_run_requires_an_aware_now(conns):
    dash, bt = conns
    with pytest.raises(ValueError):
        cap.run(dash, bt, dt.datetime(2026, 11, 11, 6, 0), lambda: DATA)


# --- default fetch and CLI -----------------------------------------------------------------------

def test_default_fetch_downloads_once_with_a_60s_timeout_and_a_descriptive_user_agent():
    resp = MagicMock()
    resp.json.return_value = DATA
    get = MagicMock(return_value=resp)
    assert cap.fetch_cleveland_json(http_get=get) == DATA
    get.assert_called_once()
    assert get.call_args.args[0] == "https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json"
    assert get.call_args.kwargs["timeout"] == 60
    assert "Cleveland" in get.call_args.kwargs["headers"]["User-Agent"] or "nowcast" in get.call_args.kwargs["headers"]["User-Agent"]
    resp.raise_for_status.assert_called_once()


def _db_files(tmp_path, with_event=True):
    dash_path, bt_path = tmp_path / "dash.db", tmp_path / "bt.db"
    dash = ws.get_connection(str(dash_path))
    if with_event:
        _event(dash, "CPI m/m", RELEASE)
    dash.close()
    return dash_path, bt_path


def _bt_rows(path):
    conn = bs.get_connection(path)
    try:
        return _count(conn)
    finally:
        conn.close()


def test_cli_dry_run_prints_what_it_would_capture_and_writes_nothing(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path)
    code = cap.main(["--dry-run", "--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda: DATA, now=NOW)
    out = capsys.readouterr().out
    assert code == 0 and "WOULD capture" in out and "CPI m/m" in out and "0.47" in out
    assert not bt_path.exists() or _bt_rows(bt_path) == 0


def test_cli_captures_into_the_given_bt_db_and_reports_it(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path)
    code = cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda: DATA, now=NOW)
    assert code == 0 and "captured" in capsys.readouterr().out.lower()
    assert _bt_rows(bt_path) == 1


def test_cli_says_so_when_nothing_is_due(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path, with_event=False)
    fetch = MagicMock()
    code = cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=fetch, now=NOW)
    assert code == 0 and "no cpi-family release within 48" in capsys.readouterr().out.lower()
    fetch.assert_not_called()


def test_cli_fetch_failure_exits_1_with_a_clear_message_and_writes_nothing(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path)

    def down():
        raise ConnectionError("timed out")
    code = cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=down, now=NOW)
    captured = capsys.readouterr()
    assert code == 1 and "timed out" in captured.err and "ERROR" in captured.err
    assert not bt_path.exists() or _bt_rows(bt_path) == 0


def test_cli_opens_the_dashboard_db_read_only(tmp_path):
    dash_path, bt_path = _db_files(tmp_path)
    conn = cap.open_dash_readonly(dash_path)
    try:
        import sqlite3
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM event_history")
    finally:
        conn.close()


def test_cli_exits_2_when_a_due_release_had_to_be_skipped(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path)
    bad = _chart("2026-10", LABELS, CPI[:7] + ["n/a", "", ""], CORE)
    code = cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda: [bad], now=NOW)
    out = capsys.readouterr().out
    assert code == 2 and "SKIPPED CPI m/m" in out and "parse" in out
    assert _bt_rows(bt_path) == 0
