"""
Tests for scripts/capture_nowcast_from_cleveland.py. No network and no real DB: the Cleveland JSON is a small
synthetic file with the REAL structure (see tests/test_cleveland_nowcast_to_csv.py::_chart), fetch is injected,
and every database is in-memory or under tmp_path.
"""
import datetime as dt
from unittest.mock import MagicMock

import pytest

from data_layer.tier1_events import TIER1_FORMULA, TIER1_FORMULA_SOURCE, tier1_titles
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
SEP = _chart("2026-9", ["09/30", "10/12", "10/13", "10/14"], ["0.5", "0.52", "0.53", ""], ["0.2", "0.2", "0.21", ""],
             actual_idx=3, release_marker="CPI Sep")
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
    assert got["value"] is None and got["reason"] == "not a month-file nowcast title"


def test_a_non_list_json_document_is_rejected_loudly():
    with pytest.raises(ValueError):
        cap.latest_nowcasts({"not": "a list"}, _release_rows())


# --- run() ---------------------------------------------------------------------------------------

def _event(dash, title, when, country="USD", forecast="0.3%"):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), forecast, "0.2%", None, None, when.isoformat(), when.isoformat(), "t", "High", country))
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
    fetch.assert_called_once_with("month")
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
    summary = cap.run(dash, bt, NOW, lambda key: [chart])
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
    summary = cap.run(dash, bt, NOW, lambda key: DATA, dry_run=True)
    assert summary["dry_run"] is True and [c[0] for c in summary["captured"]] == ["CPI m/m"]
    assert _count(bt) == 0
    assert cap.run(dash, None, NOW, lambda key: DATA, dry_run=True)["captured"] == summary["captured"]


def test_a_fetch_failure_raises_a_clear_error_and_writes_nothing(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)

    def down(key):
        raise ConnectionError("clevelandfed.org unreachable")
    with pytest.raises(cap.FetchError, match="clevelandfed.org unreachable"):
        cap.run(dash, bt, NOW, down)
    assert _count(bt) == 0


def test_a_document_of_the_wrong_shape_is_a_fetch_error_and_writes_nothing(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)
    with pytest.raises(cap.FetchError):
        cap.run(dash, bt, NOW, lambda key: {"error": "maintenance"})
    assert _count(bt) == 0


def test_an_unparseable_value_is_skipped_and_never_written(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)
    _event(dash, "Core CPI m/m", RELEASE)
    bad = _chart("2026-10", LABELS, CPI[:7] + ["n/a", "", ""], CORE)
    summary = cap.run(dash, bt, NOW, lambda key: [bad])
    assert [c[0] for c in summary["captured"]] == ["Core CPI m/m"]
    assert [s[0] for s in summary["skipped"]] == ["CPI m/m"] and "parse" in summary["skipped"][0][2]
    assert _count(bt) == 1


def test_a_stale_fed_value_is_skipped_rather_than_stamped_as_fetched_now(conns):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)
    stale_now = dt.datetime(2026, 11, 11, 6, 0, tzinfo=UTC)
    old = _chart("2026-10", LABELS, ["0.40", "0.41", "", "", "", "", "", "", "", ""], CORE)    # last value 11/02
    summary = cap.run(dash, bt, stale_now, lambda key: [old])
    assert summary["captured"] == [] and "stale" in summary["skipped"][0][2]
    assert _count(bt) == 0


def test_lookahead_refusal_from_capture_is_a_skip_and_writes_nothing(conns, monkeypatch):
    dash, bt = conns
    _event(dash, "CPI m/m", RELEASE)

    def refuse(*args, **kwargs):
        raise ValueError("as_of_utc is after the release: a snapshot taken after the print cannot be scored")
    monkeypatch.setattr(cap, "capture", refuse)
    summary = cap.run(dash, bt, NOW, lambda key: DATA)
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
    cap.run(dash, bt, NOW, lambda key: DATA)
    cap.run(dash, bt, NOW, lambda key: DATA)                                       # same instant: the store dedupes
    assert _count(bt) == 1
    later = NOW + dt.timedelta(hours=8)
    newer = _chart("2026-10", LABELS, CPI[:8] + ["0.55", ""], CORE)
    cap.run(dash, bt, later, lambda key: [newer])
    assert _count(bt) == 2
    assert bs.get_scored_nowcast_snapshot(bt, "CPI m/m", RELEASE)["nowcast_value"] == pytest.approx(0.55)   # latest wins


def test_run_requires_an_aware_now(conns):
    dash, bt = conns
    with pytest.raises(ValueError):
        cap.run(dash, bt, dt.datetime(2026, 11, 11, 6, 0), lambda key: DATA)


# --- default fetch and CLI -----------------------------------------------------------------------

def test_default_fetch_uses_the_year_url_for_the_year_key():
    resp = MagicMock()
    resp.json.return_value = DATA
    get = MagicMock(return_value=resp)
    assert cap.fetch_cleveland_json("year", http_get=get) == DATA
    get.assert_called_once()
    assert get.call_args.args[0] == "https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_year.json"
    assert get.call_args.kwargs["timeout"] == 60
    assert "nowcast" in get.call_args.kwargs["headers"]["User-Agent"]
    resp.raise_for_status.assert_called_once()


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
    code = cap.main(["--dry-run", "--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda key: DATA, now=NOW)
    out = capsys.readouterr().out
    assert code == 0 and "WOULD capture" in out and "CPI m/m" in out and "0.47" in out
    assert not bt_path.exists() or _bt_rows(bt_path) == 0


def test_cli_captures_into_the_given_bt_db_and_reports_it(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path)
    code = cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda key: DATA, now=NOW)
    assert code == 0 and "captured" in capsys.readouterr().out.lower()
    assert _bt_rows(bt_path) == 1


def test_cli_says_so_when_nothing_is_due(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path, with_event=False)
    fetch = MagicMock()
    code = cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=fetch, now=NOW)
    assert code == 0 and "no formula-tier release within 48" in capsys.readouterr().out.lower()
    fetch.assert_not_called()


def test_cli_fetch_failure_exits_1_with_a_clear_message_and_writes_nothing(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path)

    def down(key):
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
    code = cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda key: [bad], now=NOW)
    out = capsys.readouterr().out
    assert code == 2 and "SKIPPED CPI m/m" in out and "parse" in out
    assert _bt_rows(bt_path) == 0


# --- review round: chart-selection hardening ------------------------------------------------------

def test_a_delayed_release_far_beyond_the_chart_is_skipped_not_matched_to_the_wrong_month():
    # The October chart ends 10/05; a release on 2026-11-25 is 51 days later, so this is not its release.
    short = _chart("2026-10", ["10/01", "10/02", "10/05"], ["0.4", "0.41", "0.42"], ["0.2", "0.21", "0.22"])
    late = dt.datetime(2026, 11, 25, 13, 30, tzinfo=UTC)
    got = cap.latest_nowcasts([short], [("CPI m/m", late)])[0]
    assert got["value"] is None and "45 days" in got["reason"]


def test_a_release_exactly_45_days_after_the_last_label_is_still_accepted():
    short = _chart("2026-10", ["10/01", "10/02", "10/05"], ["0.4", "0.41", "0.42"], ["0.2", "0.21", "0.22"])
    edge = dt.datetime(2026, 11, 19, 13, 30, tzinfo=UTC)                       # 10/05 + 45 days
    got = cap.latest_nowcasts([short], [("CPI m/m", edge)])[0]
    assert got["reason"] is None and got["value"] == pytest.approx(0.42)


def test_a_chart_that_starts_after_the_release_is_skipped(monkeypatch):
    monkeypatch.setattr(cap, "_slot_dates", lambda chart: [dt.date(2026, 11, 20), dt.date(2026, 11, 23)])
    chart = _chart("2026-10", ["10/30", "11/02"], ["0.4", "0.41"], ["0.2", "0.21"])
    got = cap.latest_nowcasts([chart], _release_rows())[0]
    assert got["value"] is None and "starts after" in got["reason"]


def test_a_chart_with_no_nowcast_values_at_all_is_skipped_with_its_own_reason():
    empty = _chart("2026-10", LABELS, [""] * 10, CORE)
    got = _by_title(cap.latest_nowcasts([empty], _release_rows()))
    assert got["CPI m/m"]["value"] is None and "no non-blank" in got["CPI m/m"]["reason"]
    assert got["Core CPI m/m"]["value"] == pytest.approx(0.26)                 # the other series is unaffected


@pytest.mark.parametrize("blank", [None, "", "None", " "])
def test_none_empty_and_the_string_none_are_all_blank_not_unparseable(blank):
    chart = _chart("2026-10", LABELS, CPI[:8] + [blank, blank], CORE[:8] + [blank, blank])
    got = _by_title(cap.latest_nowcasts([chart], _release_rows()))
    assert got["CPI m/m"]["reason"] is None and got["CPI m/m"]["value"] == pytest.approx(0.47)
    assert got["CPI m/m"]["value_date"] == dt.date(2026, 11, 10)


@pytest.mark.parametrize("blank", [None, "None"])
def test_an_all_none_series_is_all_blank(blank):
    chart = _chart("2026-10", LABELS, [blank] * 10, CORE)
    got = _by_title(cap.latest_nowcasts([chart], _release_rows()))["CPI m/m"]
    assert got["value"] is None and "no non-blank" in got["reason"]


def test_none_in_the_actual_series_does_not_count_as_released():
    chart = _chart("2026-10", LABELS, CPI, CORE)
    for series in chart["dataset"]:
        if series["seriesname"].startswith("Actual"):
            for point in series["data"]:
                point["value"] = None
    got = cap.latest_nowcasts([chart], _release_rows())[0]
    assert got["reason"] is None and got["value"] is not None


def test_a_released_chart_reports_the_release_date_the_fed_marked():
    release = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)
    got = cap.latest_nowcasts([SEP], [("CPI m/m", release)])[0]
    assert got["value"] is None and "already" in got["reason"] and "2026-10-14" in got["reason"]


# --- B3: dashboard Tier 1 formula rows and --window-hours ---------------------------------------------

def _tier1(bt):
    return bt.execute("SELECT * FROM tier1_predictions ORDER BY event_title, instrument, id").fetchall()


def _track(dash, *symbols):
    for symbol in symbols:
        ws.add_tracked_symbol(dash, symbol)


def test_capture_series_match_the_live_cleveland_files():
    assert cap.CAPTURE_SERIES == {
        "CPI m/m": ("month", "CPI Inflation", "Actual CPI Inflation"),
        "Core CPI m/m": ("month", "Core CPI Inflation", "Actual Core CPI Inflation"),
        "Core PCE Price Index m/m": ("month", "Core PCE Inflation", "Actual Core PCE Inflation"),
        "CPI y/y": ("year", "CPI Inflation", "Actual CPI Inflation"),
        "Core CPI y/y": ("year", "Core CPI Inflation", "Actual Core CPI Inflation"),
    }
    assert cap.NOWCAST_URLS["month"] == cap.NOWCAST_URL
    assert cap.NOWCAST_URLS["year"].endswith("/nowcast_year.json")


def test_formula_titles_equal_the_capture_series():
    assert (set(tier1_titles(TIER1_FORMULA)) == set(cap.CAPTURE_SERIES)
            == {"CPI m/m", "Core CPI m/m", "CPI y/y", "Core CPI y/y", "Core PCE Price Index m/m"})


def test_run_writes_dashboard_rows_per_tracked_symbol(conns):
    dash, bt = conns
    _track(dash, "XAUUSD", "US30")
    _event(dash, "CPI m/m", RELEASE)
    _event(dash, "Core CPI m/m", RELEASE)
    summary = cap.run(dash, bt, NOW, lambda key: DATA)
    # CPI 0.47 vs 0.3% is hotter (bearish gold and US30); Core 0.26 vs 0.3% is in line (neutral).
    assert [(r["event_title"], r["instrument"], r["predicted_direction"]) for r in _tier1(bt)] == [
        ("CPI m/m", "US30", "bearish"), ("CPI m/m", "XAUUSD", "bearish"),
        ("Core CPI m/m", "US30", "neutral"), ("Core CPI m/m", "XAUUSD", "neutral")]
    for row in _tier1(bt):
        logged = dt.datetime.fromisoformat(row["logged_at_utc"])
        assert logged == NOW and logged < RELEASE and row["source"] == TIER1_FORMULA_SOURCE
    assert sorted(summary["tier1_rows"]) == sorted([
        ("CPI m/m", RELEASE.isoformat(), "US30", "bearish", "written"),
        ("CPI m/m", RELEASE.isoformat(), "XAUUSD", "bearish", "written"),
        ("Core CPI m/m", RELEASE.isoformat(), "US30", "neutral", "written"),
        ("Core CPI m/m", RELEASE.isoformat(), "XAUUSD", "neutral", "written")])
    assert summary["tier1_pending"] == [] and summary["skipped"] == []


def test_run_twice_with_the_same_nowcast_adds_snapshots_but_not_tier1_rows(conns):
    dash, bt = conns
    _track(dash, "XAUUSD", "US30")
    _event(dash, "CPI m/m", RELEASE)
    _event(dash, "Core CPI m/m", RELEASE)
    cap.run(dash, bt, NOW, lambda key: DATA)
    second = cap.run(dash, bt, NOW + dt.timedelta(hours=1), lambda key: DATA)
    assert _count(bt) == 4 and len(_tier1(bt)) == 4
    assert {r[4] for r in second["tier1_rows"]} == {"unchanged"} and len(second["tier1_rows"]) == 4
    assert ("CPI m/m", RELEASE.isoformat(), "XAUUSD", "bearish", "unchanged") in second["tier1_rows"]


def test_run_without_a_forecast_writes_no_tier1_row_and_reports_it(tmp_path, capsys):
    # 31.5 h before the release: reported only (the next daily run retries). 7.5 h before: also a skip (exit 2).
    for now, expected_code in ((NOW, 0), (RELEASE - dt.timedelta(hours=7, minutes=30), 2)):
        case = tmp_path / str(expected_code)
        case.mkdir()
        dash_path, bt_path = case / "dash.db", case / "bt.db"
        dash = ws.get_connection(str(dash_path))
        _track(dash, "XAUUSD")
        _event(dash, "CPI m/m", RELEASE, forecast=None)

        summary = cap.run(dash, bs.get_connection(":memory:"), now, lambda key: DATA)
        assert [c[0] for c in summary["captured"]] == ["CPI m/m"]
        assert summary["tier1_rows"] == []
        assert summary["tier1_pending"] == [("CPI m/m", RELEASE.isoformat(), "no readable forecast yet")]
        assert [s[0] for s in summary["skipped"]] == (["CPI m/m"] if expected_code == 2 else [])
        dash.close()

        code = cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda key: DATA, now=now)
        out = capsys.readouterr().out
        assert code == expected_code and "TIER1 PENDING CPI m/m" in out and "no readable forecast" in out
        bt = bs.get_connection(bt_path)
        assert _count(bt) == 1 and _tier1(bt) == []
        bt.close()


def test_window_hours_192_includes_a_release_8_days_out_and_48_excludes_it(conns):
    dash, bt = conns
    far = NOW + dt.timedelta(hours=191)                                     # 2026-11-19 05:00Z
    _event(dash, "CPI m/m", far)
    fetch = MagicMock(return_value=DATA)
    narrow = cap.run(dash, bt, NOW, fetch, window=dt.timedelta(hours=48))
    fetch.assert_not_called()
    assert narrow["captured"] == [] and "48 hours" in narrow["message"]
    wide = cap.run(dash, bt, NOW, fetch, window=dt.timedelta(hours=192))
    fetch.assert_called_once_with("month")
    assert [c[:2] for c in wide["captured"]] == [("CPI m/m", far.isoformat())]


def test_the_no_release_message_names_the_window(conns):
    dash, bt = conns
    summary = cap.run(dash, bt, NOW, lambda key: DATA, window=dt.timedelta(hours=192))
    assert summary["message"] == "No formula-tier release within 192 hours: nothing to capture."


@pytest.mark.parametrize("bad", ["0", "-1", "240.5", "1000"])
def test_cli_rejects_a_non_positive_window(tmp_path, capsys, bad):
    dash_path, bt_path = _db_files(tmp_path)
    with pytest.raises(SystemExit) as exc:
        cap.main(["--window-hours", bad, "--dash-db", str(dash_path), "--bt-db", str(bt_path)],
                 fetch=lambda key: DATA, now=NOW)
    assert exc.value.code == 2 and "--window-hours must be" in capsys.readouterr().err
    assert not bt_path.exists()


def test_cli_window_hours_reaches_run(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path, with_event=False)
    code = cap.main(["--window-hours", "192", "--dash-db", str(dash_path), "--bt-db", str(bt_path)],
                    fetch=MagicMock(), now=NOW)
    assert code == 0 and "within 192 hours" in capsys.readouterr().out


def test_cli_dry_run_reports_tier1_rows_and_writes_nothing(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path)
    dash = ws.get_connection(str(dash_path))
    _track(dash, "XAUUSD", "USDJPY")
    dash.close()
    code = cap.main(["--dry-run", "--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda key: DATA, now=NOW)
    out = capsys.readouterr().out
    assert code == 0
    assert "TIER1 CPI m/m XAUUSD: bearish (would write)" in out
    assert "TIER1 CPI m/m USDJPY: bullish (would write)" in out
    assert not bt_path.exists()


def test_cli_prints_written_and_unchanged_tier1_rows(tmp_path, capsys):
    dash_path, bt_path = _db_files(tmp_path)
    dash = ws.get_connection(str(dash_path))
    _track(dash, "US30")
    dash.close()
    assert cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda key: DATA, now=NOW) == 0
    assert "TIER1 CPI m/m US30: bearish (written)" in capsys.readouterr().out
    later = NOW + dt.timedelta(hours=1)
    assert cap.main(["--dash-db", str(dash_path), "--bt-db", str(bt_path)], fetch=lambda key: DATA, now=later) == 0
    assert "TIER1 CPI m/m US30: bearish (unchanged)" in capsys.readouterr().out


# --- B12: Core PCE (month file) and CPI y/y / Core CPI y/y (year file) ---------------------------

PCE_RELEASE = dt.datetime(2026, 10, 29, 12, 30, tzinfo=UTC)
PCE_NOW = dt.datetime(2026, 10, 28, 5, 0, tzinfo=UTC)
YY_RELEASE = dt.datetime(2026, 11, 10, 13, 30, tzinfo=UTC)


def _chart_with(ref, labels, values):
    """A real-structure chart (blank by default) with named series overridden: {series name: [values]}."""
    n = len(labels)
    chart = _chart(ref, labels, [""] * n, [""] * n)
    for series in chart["dataset"]:
        if series["seriesname"] in values:
            series["data"] = [{"value": v, "tooltext": f"{series['seriesname']}{{br}}{labels[i]}{{br}}{v}{{br}}"}
                              for i, v in enumerate(values[series["seriesname"]])]
    return chart


PCE_MONTH = [_chart_with("2026-9", ["09/30", "10/27", "10/28", "10/29"],
                         {"Core PCE Inflation": ["0.25", "0.26", "0.27564074403495", ""]})]
CPI_YEAR = [_chart_with("2026-10", ["10/30", "11/06", "11/09", "11/10"],
                        {"CPI Inflation": ["3.60", "3.70", "3.74183045049836", ""],
                         "Core CPI Inflation": ["3.10", "3.11", "3.12", ""]})]


def test_latest_nowcasts_reads_core_pce_from_the_month_file():
    got = cap.latest_nowcasts(PCE_MONTH, [("Core PCE Price Index m/m", PCE_RELEASE)], "month")[0]
    assert got["value"] == pytest.approx(0.27564074403495) and got["value_date"] == dt.date(2026, 10, 28)
    assert got["reason"] is None


def test_latest_nowcasts_reads_cpi_yy_from_the_year_file():
    got = cap.latest_nowcasts(CPI_YEAR, [("CPI y/y", YY_RELEASE)], "year")[0]
    assert got["value"] == pytest.approx(3.74183045049836) and got["value_date"] == dt.date(2026, 11, 9)


def test_latest_nowcasts_refuses_a_title_from_the_other_file():
    got = cap.latest_nowcasts(CPI_YEAR, [("CPI y/y", YY_RELEASE)], "month")[0]
    assert got["value"] is None and got["reason"] == "not a month-file nowcast title"
    got = cap.latest_nowcasts(PCE_MONTH, [("Core PCE Price Index m/m", PCE_RELEASE)], "year")[0]
    assert got["value"] is None and got["reason"] == "not a year-file nowcast title"


def _keyed_fetch(calls):
    files = {"month": PCE_MONTH + DATA, "year": CPI_YEAR}

    def fetch(key):
        calls.append(key)
        return files[key]
    return fetch


def test_run_fetches_each_needed_file_once(conns):
    dash, bt = conns
    calls: list = []
    _event(dash, "Core PCE Price Index m/m", PCE_RELEASE)
    cap.run(dash, bt, PCE_NOW, _keyed_fetch(calls))
    assert calls == ["month"]

    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    calls = []
    now = dt.datetime(2026, 11, 9, 6, 0, tzinfo=UTC)
    for title in ("CPI m/m", "CPI y/y", "Core CPI y/y"):
        _event(dash, title, YY_RELEASE)
    cap.run(dash, bt, now, _keyed_fetch(calls))
    assert sorted(calls) == ["month", "year"]

    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    calls = []
    cap.run(dash, bt, PCE_NOW, _keyed_fetch(calls))
    assert calls == []


def test_run_writes_core_pce_formula_rows(conns):
    dash, bt = conns
    _track(dash, "XAUUSD", "US30")
    _event(dash, "Core PCE Price Index m/m", PCE_RELEASE, forecast="0.3%")
    summary = cap.run(dash, bt, PCE_NOW, lambda key: PCE_MONTH)
    snap = bt.execute("SELECT event_title, nowcast_value FROM tier1_nowcast_snapshots").fetchall()
    assert [(r["event_title"], r["nowcast_value"]) for r in snap] == [("Core PCE Price Index m/m", pytest.approx(0.27564074403495))]
    rows = _tier1(bt)
    assert [(r["instrument"], r["predicted_direction"], r["source"]) for r in rows] == [
        ("US30", "neutral", TIER1_FORMULA_SOURCE), ("XAUUSD", "neutral", TIER1_FORMULA_SOURCE)]
    assert summary["skipped"] == []


def test_run_cpi_yy_hotter_is_bearish_gold(conns):
    dash, bt = conns
    _track(dash, "XAUUSD", "US30")
    _event(dash, "CPI y/y", YY_RELEASE, forecast="3.6%")
    now = dt.datetime(2026, 11, 9, 6, 0, tzinfo=UTC)
    cap.run(dash, bt, now, lambda key: CPI_YEAR)
    assert [(r["instrument"], r["predicted_direction"]) for r in _tier1(bt)] == [
        ("US30", "bearish"), ("XAUUSD", "bearish")]
