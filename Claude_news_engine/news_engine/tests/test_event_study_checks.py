"""Pure-helper tests for scripts/archive/event_study_checks.py (chain E2 and Tier 1 dipstick E3; no network, no DB)."""
import csv
import datetime as dt

import pytest

from scripts import cleveland_nowcast_to_csv as cn
from scripts.archive import event_study_checks as c

UTC = dt.timezone.utc
RELEASE = dt.datetime(2026, 3, 11, 12, 30, 0, tzinfo=UTC)


def _pt(text: str, value: float) -> c.NowcastPoint:
    return c.NowcastPoint(as_of_utc=dt.datetime.fromisoformat(text.replace("Z", "+00:00")), value=value)


def test_bps() -> None:
    assert c.bps(0.03, 100.0) == pytest.approx(3.0)
    assert c.bps(None, 100.0) is None
    assert c.bps(0.03, None) is None
    assert c.bps(0.03, 0.0) is None


def test_event_usd_agreement_thresholds() -> None:
    rows = [(1, 0.01, 100.0), (1, 0.03, 100.0), (-1, 0.03, 100.0), (0, 0.05, 100.0), (1, None, 100.0)]
    at_two = c.event_usd_agreement(rows, 2.0)
    assert at_two == {"threshold_bps": 2.0, "n": 2, "n_match": 1, "share": 0.5}
    assert c.event_usd_agreement(rows, 0.0)["n"] == 3
    empty = c.event_usd_agreement([], 2.0)
    assert empty["n"] == 0 and empty["share"] is None


def test_usd_instrument_agreement_inverse() -> None:
    rows = [(0.03, 100.0, -2.0), (0.03, 100.0, 1.0), (0.03, 100.0, 0.0), (0.03, 100.0, None)]
    out = c.usd_instrument_agreement(rows, -1, 2.0)
    assert out == {"threshold_bps": 2.0, "n": 2, "n_agree": 1, "share": 0.5}


def test_ols_exact_and_degenerate() -> None:
    fit = c.ols([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])
    assert fit is not None
    assert fit["slope"] == pytest.approx(2.0)
    assert fit["intercept"] == pytest.approx(0.0)
    assert fit["r"] == pytest.approx(1.0)
    assert fit["n"] == 3
    assert c.ols([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None
    assert c.ols([1.0, 2.0], [1.0, 2.0]) is None


def test_dipstick_row_reference_fixture() -> None:
    points = [
        _pt("2026-02-09T23:59:59Z", 0.20),
        _pt("2026-02-14T23:59:59Z", 0.25),
        _pt("2026-03-01T23:59:59Z", 0.30),
        _pt("2026-03-10T23:59:59Z", 0.31),
    ]
    row = c.dipstick_row("CPI m/m", RELEASE, points, "0.3", "0.3", 25)
    assert tuple(row) == c.DIPSTICK_KEYS
    assert row["early"] == pytest.approx(0.20)
    assert row["final"] == pytest.approx(0.31)
    assert row["closer"] == "final"
    assert (row["early_side"], row["final_side"], row["actual_side"]) == (-1, 0, 0)
    assert row["side_changed"] is True
    assert row["early_hit"] is False and row["final_hit"] is True
    assert row["release_sast"] == "2026-03-11 14:30 SAST"
    assert row["early_equals_final"] is False


def test_dipstick_tie_when_early_equals_final() -> None:
    points = [_pt("2026-03-01T23:59:59Z", 0.30), _pt("2026-03-10T23:59:59Z", 0.30)]
    row = c.dipstick_row("CPI m/m", RELEASE, points, "0.3", "0.4", 5)
    assert row["early"] == pytest.approx(0.30) and row["final"] == pytest.approx(0.30)
    assert row["closer"] == "tie"
    assert row["early_equals_final"] is True


def test_dipstick_missing_value_has_no_verdict() -> None:
    row = c.dipstick_row("CPI m/m", RELEASE, [_pt("2026-03-10T23:59:59Z", 0.3)], "0.3", "0.3", 25)
    assert row["early"] is None
    assert row["closer"] is None
    assert row["early_side"] is None and row["early_hit"] is None


def test_final_value_excludes_release_day_stamp() -> None:
    points = [_pt("2026-03-10T23:59:59Z", 0.31), c.NowcastPoint(as_of_utc=RELEASE, value=0.99)]
    assert c.final_value(points, RELEASE) == pytest.approx(0.31)
    assert c.final_value([c.NowcastPoint(as_of_utc=RELEASE, value=0.99)], RELEASE) is None
    assert c.value_as_of(points, RELEASE) == pytest.approx(0.99)


def test_summarize_dipstick_counts() -> None:
    points = [_pt("2026-02-09T23:59:59Z", 0.20), _pt("2026-03-10T23:59:59Z", 0.31)]
    a = c.dipstick_row("CPI m/m", RELEASE, points, "0.3", "0.3", 25)
    missing = c.dipstick_row("CPI m/m", RELEASE, [], "0.3", "0.3", 25)
    out = c.summarize_dipstick([a, missing])
    assert out == {"n": 1, "final_closer": 1, "early_closer": 0, "ties": 0, "early_equals_final": 0,
                   "side_changed": 1, "early_hits": 0, "final_hits": 1}


def test_load_nowcast_csv_round_trip(tmp_path) -> None:
    path = tmp_path / "nowcasts.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=cn.CSV_COLUMNS)
        writer.writeheader()
        writer.writerow({"event_title": "CPI m/m", "release_utc": "2026-03-11T12:30:00+00:00",
                         "as_of_utc": "2026-03-10T23:59:59+00:00", "value": "0.31", "source": "x"})
        writer.writerow({"event_title": "CPI m/m", "release_utc": "2026-03-11T12:30:00+00:00",
                         "as_of_utc": "2026-02-09T23:59:59+00:00", "value": "0.20", "source": "x"})
        writer.writerow({"event_title": "Core CPI m/m", "release_utc": "2026-03-11T12:30:00+00:00",
                         "as_of_utc": "2026-03-10T23:59:59+00:00", "value": "0.28", "source": "x"})
    data = c.load_nowcast_csv(path)
    assert set(data) == {("CPI m/m", RELEASE), ("Core CPI m/m", RELEASE)}
    pts = data[("CPI m/m", RELEASE)]
    assert [p.value for p in pts] == [0.20, 0.31]
    assert pts[0].as_of_utc < pts[1].as_of_utc
