"""
Tests for data_layer.fred_history (B8 Task 1) — ALFRED release-day vintage
reader. A fake `requests.get` is patched on the module; no network, no key.
"""
from __future__ import annotations

import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer import fred_history as fh
from data_layer.calendar_feed import tick_of

D = dt.date
SECRET = "SECRETKEY123"


class FakeResp:
    def __init__(self, payload=None, status=200, text=None):
        self._payload = payload if payload is not None else {}
        self.status_code = status
        self.text = text if text is not None else "{}"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code} for url with api_key={SECRET}")

    def json(self):
        return self._payload


class FakeRequests:
    """Routes on output_type / realtime_start; records every call's params."""

    def __init__(self, initial=None, vintages=None, latest=None):
        self.initial = initial or {}      # series_id -> list of observation dicts
        self.vintages = vintages or {}    # (series_id, "YYYY-MM-DD") -> {date: value}
        self.latest = latest or {}        # series_id -> {date: value} (never wanted)
        self.calls: list[dict] = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params))
        sid = params["series_id"]
        if params.get("output_type") == 4:
            return FakeResp({"observations": self.initial.get(sid, [])})
        key = (sid, params["realtime_start"])
        if params["realtime_start"] == params["realtime_end"] and key in self.vintages:
            obs = self.vintages[key]
        else:
            obs = self.latest.get(sid, {})
        return FakeResp({"observations": [{"date": d.isoformat(), "value": str(v)} for d, v in sorted(obs.items())]})


def _client(fake, monkeypatch):
    monkeypatch.setattr(fh, "requests", fake)
    return fh.FredClient(SECRET, pace_seconds=0)


def _init_obs(period, vintage):
    return {"date": period.isoformat(), "realtime_start": vintage.isoformat(), "realtime_end": "9999-12-31", "value": "1"}


def test_tick_of():
    assert tick_of("0.3%") == pytest.approx(0.1)
    assert tick_of("225K") == pytest.approx(1000.0)
    assert tick_of("7.23M") == pytest.approx(10000.0)
    assert tick_of("-78.3B") == pytest.approx(1e8)
    assert tick_of("52") == pytest.approx(1.0)
    assert tick_of(None) is None
    assert tick_of("N/A") is None


def test_initial_releases_parses_output_type_4(monkeypatch):
    fake = FakeRequests(initial={"CPIAUCSL": [_init_obs(D(2026, 9, 1), D(2026, 10, 14))]})
    client = _client(fake, monkeypatch)
    out = client.initial_releases("CPIAUCSL", D(2026, 1, 1), D(2026, 10, 27))
    assert out == [fh.InitialRelease(period=D(2026, 9, 1), vintage_date=D(2026, 10, 14))]
    assert fake.calls[0]["output_type"] == 4
    assert fake.calls[0]["realtime_start"] == "2026-01-01"
    assert fake.calls[0]["realtime_end"] == "2026-10-27"
    # Cached: same request again makes no new call.
    client.initial_releases("CPIAUCSL", D(2026, 1, 1), D(2026, 10, 27))
    assert len(fake.calls) == 1


def test_reading_uses_release_day_vintage_not_latest(monkeypatch):
    # CPI: release-day vintage says Sep 324.938; the latest vintage (also served) says 326.000.
    fake = FakeRequests(
        vintages={("CPIAUCSL", "2026-10-14"): {D(2026, 7, 1): 321.0, D(2026, 8, 1): 323.000, D(2026, 9, 1): 324.938}},
        latest={"CPIAUCSL": {D(2026, 8, 1): 323.0, D(2026, 9, 1): 326.000}},
    )
    client = _client(fake, monkeypatch)
    rel = fh.InitialRelease(period=D(2026, 9, 1), vintage_date=D(2026, 10, 14))
    reading = fh.reading_for_release(client, "CPI m/m", rel, None)
    assert reading.actual == "0.6%"
    assert reading.previous == "0.6%"          # Aug m/m in the same vintage: 323/321 - 1
    assert reading.previous_first_print is None
    assert reading.vintage_date == D(2026, 10, 14)
    call = fake.calls[0]
    assert call["realtime_start"] == call["realtime_end"] == "2026-10-14"

    # NFP: headline is the level change inside the release-day vintage.
    fake2 = FakeRequests(vintages={
        ("PAYEMS", "2026-10-02"): {D(2026, 7, 1): 160000.0, D(2026, 8, 1): 160130.0, D(2026, 9, 1): 160260.0},
        ("PAYEMS", "2026-09-04"): {D(2026, 7, 1): 160010.0, D(2026, 8, 1): 160130.0},
    })
    client2 = _client(fake2, monkeypatch)
    prior = fh.InitialRelease(period=D(2026, 8, 1), vintage_date=D(2026, 9, 4))
    rel2 = fh.InitialRelease(period=D(2026, 9, 1), vintage_date=D(2026, 10, 2))
    r2 = fh.reading_for_release(client2, "Non-Farm Employment Change", rel2, prior)
    assert r2.actual == "130K"
    assert r2.previous == "130K"                # Aug revised inside the Oct vintage
    assert r2.previous_first_print == "120K"    # Aug as first published on 2026-09-04


def test_transforms():
    levels = [(D(2025 + (m // 12), m % 12 + 1, 1), 100.0 + m) for m in range(13)]  # 2025-01 .. 2026-01
    last = levels[-1][0]
    assert fh.transform_at(levels, last, "pc1") == pytest.approx((112.0 / 100.0 - 1) * 100)
    assert fh.transform_at(levels, last, "pch") == pytest.approx((112.0 / 111.0 - 1) * 100)
    assert fh.transform_at(levels, last, "chg") == pytest.approx(1.0)
    assert fh.transform_at(levels, last, "lin") == pytest.approx(112.0)
    # Missing prior point -> None (first observation has no predecessor; no 12m-ago point).
    assert fh.transform_at(levels, levels[0][0], "pch") is None
    assert fh.transform_at(levels, levels[3][0], "pc1") is None
    assert fh.transform_at(levels, D(2030, 1, 1), "lin") is None


def test_format_values():
    pct = fh.FredSeriesSpec("X", "pch", "pct1")
    assert fh.format_value(0.6, pct) == "0.6%"
    assert fh.format_value(-0.04, pct) == "0.0%"
    assert fh.format_value(130.0, fh.FredSeriesSpec("PAYEMS", "chg", "k0")) == "130K"
    assert fh.format_value(219000, fh.FredSeriesSpec("ICSA", "lin", "k0", scale=0.001)) == "219K"
    assert fh.format_value(7230, fh.FredSeriesSpec("JTSJOL", "lin", "m2", scale=0.001)) == "7.23M"
    assert fh.format_value(-78312, fh.FredSeriesSpec("BOPGSTB", "lin", "b1", scale=0.001)) == "-78.3B"
    assert fh.format_value(-0.3, fh.FredSeriesSpec("GACDFSA066MSFRBPHI", "lin", "num1")) == "-0.3"


def test_maintenance_page_raises(monkeypatch):
    class Maint(FakeRequests):
        def get(self, url, params=None, timeout=None):
            return FakeResp(status=200, text="<html><body>FRED is down for maintenance</body></html>")

    client = _client(Maint(), monkeypatch)
    with pytest.raises(fh.FredMaintenanceError) as exc:
        client.initial_releases("CPIAUCSL", D(2026, 1, 1), D(2026, 2, 1))
    assert SECRET not in str(exc.value)

    class Err(FakeRequests):
        def get(self, url, params=None, timeout=None):
            return FakeResp(status=500, text="boom")

    client = _client(Err(), monkeypatch)
    with pytest.raises(fh.FredFetchError) as exc2:
        client.vintage_levels("CPIAUCSL", D(2026, 10, 14), D(2025, 9, 1))
    assert SECRET not in str(exc2.value)
    assert not isinstance(exc2.value, fh.FredMaintenanceError)


def test_values_match_and_checks():
    assert fh.values_match("0.4%", "0.4%")
    assert not fh.values_match("0.4%", "0.5%")
    assert fh.values_match("7.2M", "7.23M")
    assert not fh.values_match(None, "0.4%")
    reading = fh.VintageReading("CPI m/m", D(2026, 9, 1), D(2026, 10, 14), actual="0.6%", previous="0.5%", previous_first_print="0.4%")
    assert fh.actual_check(reading, "0.6%") == "match"
    assert fh.actual_check(reading, "0.7%") == "mismatch"
    assert fh.actual_check(reading, None) == "no_reference"
    assert fh.previous_check(reading, "0.5%") == "match"
    assert fh.previous_check(reading, "0.4%") == "match"      # first-print candidate
    assert fh.previous_check(reading, "0.9%") == "mismatch"
    assert fh.previous_check(reading, None) == "no_reference"


def test_releases_between_and_event_date_lookup(monkeypatch):
    fake = FakeRequests(
        initial={"CPIAUCSL": [_init_obs(D(2026, 8, 1), D(2026, 9, 11)), _init_obs(D(2026, 9, 1), D(2026, 10, 14))]},
        vintages={
            ("CPIAUCSL", "2026-09-11"): {D(2026, 6, 1): 320.0, D(2026, 7, 1): 321.0, D(2026, 8, 1): 322.0},
            ("CPIAUCSL", "2026-10-14"): {D(2026, 7, 1): 321.0, D(2026, 8, 1): 323.0, D(2026, 9, 1): 324.938},
        },
    )
    client = _client(fake, monkeypatch)
    out = fh.releases_between(client, "CPI m/m", D(2026, 10, 1), D(2026, 10, 27))
    assert [r.vintage_date for r in out] == [D(2026, 10, 14)]
    assert out[0].actual == "0.6%"
    assert out[0].previous_first_print == "0.3%"   # Aug as first published 2026-09-11: 322/321 - 1
    hit = fh.reading_for_event_date(client, "CPI m/m", D(2026, 10, 13))
    assert hit is not None and hit.vintage_date == D(2026, 10, 14)
    assert fh.reading_for_event_date(client, "CPI m/m", D(2026, 10, 1)) is None
    assert fh.reading_for_event_date(client, "Not A Title", D(2026, 10, 13)) is None


def test_specs_are_complete():
    assert fh.FRED_HISTORY_SPECS["Non-Farm Employment Change"].seed
    for title, spec in fh.FRED_HISTORY_SPECS.items():
        assert title == title.strip()
        if spec.seed:
            assert spec.release_time_et is not None, title
        assert spec.transform in {"pch", "pc1", "chg", "lin"}
        assert spec.fmt in {"pct1", "k0", "m2", "b1", "num1"}
    assert fh.FRED_HISTORY_SPECS["Unemployment Claims"].frequency == "weekly"
    assert not fh.FRED_HISTORY_SPECS["JOLTS Job Openings"].seed
    assert fh.FRED_HISTORY_SPECS["ADP Non-Farm Employment Change"].release_time_et == dt.time(8, 15)
