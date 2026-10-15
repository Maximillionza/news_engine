"""
Tests for the Cleveland Fed nowcast_month.json -> CSV converter. The fixture is a small synthetic file
that mimics the REAL structure observed on 2026-10-15 (FusionCharts: one chart per reference month, a
single 'category' list mixing "MM/DD" date labels with vline release markers, and eight series with one
slot per date label; the 'Actual ...' series holds a value only on the release day).
"""
import csv
import datetime as dt
import json

import pytest

from scripts import cleveland_nowcast_to_csv as c2c
from scripts.backfill_tier1_reconstructed import FileNowcastProvider, run_backfill
from scoring import backtest_store as bs
from webapp import store as ws

UTC = dt.timezone.utc
SOURCE = "Cleveland Fed Inflation Nowcasting (CC BY 4.0)"
SERIES_NAMES = ["CPI Inflation", "Core CPI Inflation", "PCE Inflation", "Core PCE Inflation",
                "Actual CPI Inflation", "Actual Core CPI Inflation", "Actual PCE Inflation", "Actual Core PCE Inflation"]


def _chart(ref, labels, cpi, core, actual_idx=None, actual_cpi="0.99", actual_core="0.88", release_marker=None):
    """
    labels: ["MM/DD", ...]; cpi/core: nowcast per label ("" = blank slot); actual_idx: slot index of the
    release day (None = not released yet). Release-day nowcast slots are blank in the real file, but a test
    can put a value there to prove it is excluded.
    """
    category = []
    for i, label in enumerate(labels):
        category.append({"label": label})
        if release_marker and actual_idx is not None and i == actual_idx:
            category.append({"label": release_marker, "labelposition": "0", "lineposition": "0",
                             "color": "666666", "vline": "true"})
    n = len(labels)

    def series(name, values):
        return {"seriesname": name, "color": "000000",
                "data": [{"value": v, "tooltext": f"{name}{{br}}{labels[i]}{{br}}{v}{{br}}"} for i, v in enumerate(values)]}

    def actual(value):
        vals = [""] * n
        if actual_idx is not None:
            vals[actual_idx] = value
        return vals

    values = {
        "CPI Inflation": cpi, "Core CPI Inflation": core,
        "PCE Inflation": [""] * n, "Core PCE Inflation": [""] * n,
        "Actual CPI Inflation": actual(actual_cpi), "Actual Core CPI Inflation": actual(actual_core),
        "Actual PCE Inflation": [""] * n, "Actual Core PCE Inflation": [""] * n,
    }
    return {"chart": {"caption": "Inflation Nowcasting", "subcaption": ref},
            "categories": [{"category": category}],
            "dataset": [series(name, values[name]) for name in SERIES_NAMES]}


# February 2026 CPI released Wed 2026-03-11 (12:30Z, US daylight time already in force).
MARCH = _chart("2026-2", ["02/27", "03/02", "03/05", "03/06", "03/09", "03/10", "03/11", "03/12"],
               cpi=["0.05", "0.08", "0.10", "0.20", "0.30", "0.40", "0.55", ""],   # 03/11 slot filled on purpose
               core=["0.20", "0.205", "0.21", "0.22", "", "0.24", "0.25", ""],       # 03/09 blank on purpose
               actual_idx=6, release_marker="CPI Feb")
# December 2025 CPI released 2026-01-13 (13:30Z, winter time); labels cross the year boundary.
DECEMBER = _chart("2025-12", ["12/30", "12/31", "01/02", "01/12", "01/13"],
                  cpi=["0.11", "0.12", "0.13", "0.14", ""], core=["0.31", "0.32", "0.33", "0.34", ""],
                  actual_idx=4, release_marker="CPI Dec")
# Current month: no actual yet, so there is no release to attach a nowcast to.
OPEN_MONTH = _chart("2026-10", ["10/01", "10/02"], cpi=["0.6", "0.61"], core=["0.2", "0.21"], actual_idx=None)

MARCH_RELEASE = dt.datetime(2026, 3, 11, 12, 30, tzinfo=UTC)
JAN_RELEASE = dt.datetime(2026, 1, 13, 13, 30, tzinfo=UTC)
KNOWN = [
    ("CPI m/m", MARCH_RELEASE),
    ("Core CPI m/m", MARCH_RELEASE),
    ("CPI m/m", JAN_RELEASE),       # no Core CPI row on this day (as in the live DB)
]
WIDE = (dt.datetime(2026, 1, 1, tzinfo=UTC), dt.datetime(2026, 12, 31, tzinfo=UTC))


def _rows(charts=(MARCH, DECEMBER, OPEN_MONTH), known=KNOWN, window=WIDE):
    return c2c.convert(list(charts), known, *window)


def _select(rows, title, release):
    return [r for r in rows if r["event_title"] == title and r["release_utc"] == release.isoformat()]


def _seed_event(dash, title, when, country="USD"):
    dash.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), "0.3%", "0.2%", "0.4%", None, when.isoformat(), when.isoformat(), "t", "High", country))
    dash.commit()


def test_release_day_slot_is_never_emitted():
    rows = _select(_rows(), "CPI m/m", MARCH_RELEASE)
    assert rows, "expected CPI m/m rows for the March release"
    assert "0.55" not in {r["value"] for r in rows}
    assert max(r["as_of_utc"] for r in rows) < "2026-03-11"          # the 03/11 slot (and 03/12) are out


def test_as_of_is_end_of_day_utc_and_strictly_before_release():
    rows = _select(_rows(), "CPI m/m", MARCH_RELEASE)
    assert [r["as_of_utc"] for r in rows] == [
        "2026-02-27T23:59:59+00:00", "2026-03-02T23:59:59+00:00", "2026-03-05T23:59:59+00:00",
        "2026-03-06T23:59:59+00:00", "2026-03-09T23:59:59+00:00", "2026-03-10T23:59:59+00:00"]
    assert all(dt.datetime.fromisoformat(r["as_of_utc"]) < MARCH_RELEASE for r in rows)


def test_every_business_day_is_emitted_and_blanks_are_skipped():
    core = _select(_rows(), "Core CPI m/m", MARCH_RELEASE)
    assert [r["value"] for r in core] == ["0.20", "0.205", "0.21", "0.22", "0.24"]      # 03/09 blank dropped, not zero-filled


def test_cpi_and_core_cpi_map_to_their_own_titles_and_values():
    rows = _rows()
    assert {r["value"] for r in _select(rows, "CPI m/m", MARCH_RELEASE)} == {"0.05", "0.08", "0.10", "0.20", "0.30", "0.40"}
    assert {r["value"] for r in _select(rows, "Core CPI m/m", MARCH_RELEASE)} == {"0.20", "0.205", "0.21", "0.22", "0.24"}
    assert {r["event_title"] for r in rows} == {"CPI m/m", "Core CPI m/m"}


def test_only_releases_present_in_known_occurrences_are_emitted():
    # Core CPI on 2026-01-13 is not in event_history, so no Core row for that release; with only the
    # January CPI row known, March emits nothing.
    rows = _rows()
    assert _select(rows, "Core CPI m/m", JAN_RELEASE) == []
    assert _select(rows, "CPI m/m", JAN_RELEASE)
    only_jan = _rows(known=[KNOWN[2]])
    assert {r["release_utc"] for r in only_jan} == {"2026-01-13T13:30:00+00:00"}


def test_release_utc_comes_from_the_known_occurrence_not_a_fixed_hour():
    rows = _rows()
    assert {r["release_utc"] for r in _select(rows, "CPI m/m", JAN_RELEASE)} == {"2026-01-13T13:30:00+00:00"}
    assert {r["release_utc"] for r in _select(rows, "CPI m/m", MARCH_RELEASE)} == {"2026-03-11T12:30:00+00:00"}


def test_year_rolls_over_inside_a_chart():
    jan = _select(_rows(), "CPI m/m", JAN_RELEASE)
    assert [r["as_of_utc"][:10] for r in jan] == ["2025-12-30", "2025-12-31", "2026-01-02", "2026-01-12"]


def test_unreleased_month_emits_nothing_even_if_listed_as_known():
    known = KNOWN + [("CPI m/m", dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC))]
    assert not [r for r in _rows(known=known) if r["as_of_utc"].startswith("2026-10")]


def test_since_until_filter_the_release_window():
    rows = _rows(window=(dt.datetime(2026, 2, 1, tzinfo=UTC), dt.datetime(2026, 4, 1, tzinfo=UTC)))
    assert {r["release_utc"] for r in rows} == {"2026-03-11T12:30:00+00:00"}


def test_source_default_is_the_cc_by_attribution():
    assert {r["source"] for r in _rows()} == {SOURCE}


def test_csv_round_trips_through_file_provider_and_backfill(tmp_path):
    path = tmp_path / "n.csv"
    c2c.write_csv(_rows(), path)
    with open(path, newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert header == ["event_title", "release_utc", "as_of_utc", "value", "source"]

    provider = FileNowcastProvider(path)
    value, as_of, source = provider.nowcast_before("CPI m/m", MARCH_RELEASE)
    assert value == 0.40 and as_of == dt.datetime(2026, 3, 10, 23, 59, 59, tzinfo=UTC) and source == SOURCE

    dash, bt = ws.get_connection(":memory:"), bs.get_connection(":memory:")
    for title, when in KNOWN:
        _seed_event(dash, title, when)
    result = run_backfill(dash, bt, provider, "v1", *WIDE)
    assert result == {"written": 3, "skipped_no_data": 0, "skipped_lookahead": 0}


def test_load_known_occurrences_reads_usd_rows_only(tmp_path):
    db = tmp_path / "dash.db"
    conn = ws.get_connection(db)
    _seed_event(conn, "CPI m/m", dt.datetime(2026, 3, 11, 12, 30, tzinfo=UTC))
    _seed_event(conn, "CPI m/m", dt.datetime(2026, 8, 26, 1, 30, tzinfo=UTC), country=None)   # unattributed print
    _seed_event(conn, "Core CPI m/m", dt.datetime(2026, 3, 11, 12, 30, tzinfo=UTC))
    _seed_event(conn, "Nonfarm Payrolls", dt.datetime(2026, 3, 6, 13, 30, tzinfo=UTC))
    conn.close()
    known = c2c.load_known_occurrences(db)
    assert sorted((t, w.isoformat()) for t, w in known) == [
        ("CPI m/m", "2026-03-11T12:30:00+00:00"), ("Core CPI m/m", "2026-03-11T12:30:00+00:00")]


def test_load_charts_accepts_a_json_file(tmp_path):
    path = tmp_path / "nowcast_month.json"
    path.write_text(json.dumps([MARCH]), encoding="utf-8")
    assert len(_rows(charts=c2c.load_charts(path))) == 11          # 6 CPI + 5 Core


def test_a_released_chart_whose_first_label_is_outside_the_reference_month_is_rejected():
    odd = _chart("2026-2", ["04/05", "04/06"], cpi=["0.1", ""], core=["0.1", ""], actual_idx=1)
    with pytest.raises(ValueError):
        c2c.convert([odd], KNOWN, *WIDE)


def test_a_series_that_does_not_line_up_with_the_date_labels_is_rejected():
    bad = _chart("2026-2", ["02/27", "03/02", "03/11"], cpi=["0.1", "0.2", ""], core=["0.1", "0.2", ""], actual_idx=2)
    bad["dataset"][0]["data"].pop()          # CPI series one slot short
    with pytest.raises(ValueError):
        c2c.convert([bad], KNOWN, *WIDE)


def test_download_refuses_a_destination_inside_the_repo():
    with pytest.raises(ValueError):
        c2c.download(c2c.APP_ROOT / "nowcast_month.json")
