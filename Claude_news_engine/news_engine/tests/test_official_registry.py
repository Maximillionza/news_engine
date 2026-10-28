"""
Tests for the ACT title registry, fill rule, fetch grouping and coverage
lists (data_layer/official_actuals/registry.py, fetch.py, coverage.py;
ACT Task 2). Recorded fixtures, temp DBs and fake fetchers only: no network.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.official_actuals import bea, bls, coverage, eia, registry
from data_layer.official_actuals.fetch import FetchOutcome, fetch_for_specs, series_key
from data_layer.official_actuals.http import HttpResponse, SourceRateLimited
from data_layer.official_actuals.keys import Keys
from data_layer.official_actuals.registry import OFFICIAL_SPECS, decide_fill, expected_period, format_like
from tests.test_official_adapters import FakeFetcher, _fixture, _ok, _url_has
from webapp import store as ws

D = dt.date
UTC = dt.timezone.utc
KEYS = Keys(bls="K", bea="K", census="K", eia="K", fred="K")


def _spec(title: str) -> registry.OfficialSpec:
    return OFFICIAL_SPECS[title]


# ---------------------------------------------------------------- period rule

def test_expected_period_rules():
    assert expected_period(_spec("CPI m/m"), D(2026, 10, 14)) == D(2026, 9, 1)
    assert expected_period(_spec("Non-Farm Employment Change"), D(2026, 9, 4)) == D(2026, 8, 1)
    assert expected_period(_spec("JOLTS Job Openings"), D(2026, 9, 1)) == D(2026, 7, 1)
    assert expected_period(_spec("JOLTS Job Openings"), D(2026, 9, 29)) == D(2026, 8, 1)
    assert expected_period(_spec("Core PCE Price Index m/m"), D(2026, 9, 30)) == D(2026, 8, 1)
    assert expected_period(_spec("Business Inventories m/m"), D(2026, 10, 15)) == D(2026, 8, 1)
    assert expected_period(_spec("Construction Spending m/m"), D(2026, 10, 1)) == D(2026, 8, 1)
    assert expected_period(_spec("Advance GDP q/q"), D(2026, 10, 29)) == D(2026, 7, 1)
    assert expected_period(_spec("Final GDP q/q"), D(2026, 9, 30)) == D(2026, 4, 1)
    assert expected_period(_spec("Revised Nonfarm Productivity q/q"), D(2026, 9, 3)) == D(2026, 4, 1)
    assert expected_period(_spec("Unemployment Claims"), D(2026, 10, 29)) == D(2026, 10, 24)      # Thu -> Sat
    assert expected_period(_spec("Crude Oil Inventories"), D(2026, 10, 28)) == D(2026, 10, 23)    # Wed -> Fri
    assert expected_period(_spec("Natural Gas Storage"), D(2026, 10, 29)) == D(2026, 10, 23)      # Thu -> Fri
    assert expected_period(_spec("Federal Funds Rate"), D(2026, 10, 28)) == D(2026, 10, 28)


def test_prior_period_steps_and_event_lookup():
    assert registry.prior_period(_spec("CPI m/m"), D(2026, 1, 1), [D(2025, 12, 1)]) == D(2025, 12, 1)
    assert registry.prior_period(_spec("CPI m/m"), D(2026, 1, 1), []) is None            # not published -> None
    assert registry.prior_period(_spec("Advance GDP q/q"), D(2026, 7, 1), [D(2026, 4, 1)]) == D(2026, 4, 1)
    assert registry.prior_period(_spec("Crude Oil Inventories"), D(2026, 10, 23), [D(2026, 10, 16)]) == D(2026, 10, 16)
    fomc = [D(2026, 7, 29), D(2026, 9, 16), D(2026, 10, 28)]
    assert registry.prior_period(_spec("Federal Funds Rate"), D(2026, 10, 28), fomc) == D(2026, 9, 16)


def test_value_for_transforms():
    crude = {D(2026, 10, 16): 412517.0, D(2026, 10, 23): 410625.0}
    assert registry.value_for(_spec("Crude Oil Inventories"), crude, D(2026, 10, 23)) == -1892.0
    assert registry.value_for(_spec("Crude Oil Inventories"), crude, D(2026, 10, 16)) is None   # prior week missing
    income = {D(2026, 7, 1): 100.0, D(2026, 8, 1): 100.5}
    assert abs(registry.value_for(_spec("Personal Income m/m"), income, D(2026, 8, 1)) - 0.5) < 1e-9
    auctions = {D(2026, 10, 7): (5.3, 2.77)}
    assert registry.value_for(_spec("10-y Bond Auction"), auctions, D(2026, 10, 7)) == (5.3, 2.77)
    assert registry.value_for(_spec("CPI m/m"), {}, D(2026, 9, 1)) is None


# ---------------------------------------------------------------- formatting

def test_format_like_matches_ff_strings():
    assert format_like(29.0, "89K", _spec("Non-Farm Employment Change")) == "29K"
    assert format_like(7079.0, "7.23M", _spec("JOLTS Job Openings")) == "7.08M"
    assert format_like(-1892.0, "0.1M", _spec("Crude Oil Inventories")) == "-1.9M"
    assert format_like(77.0, "75B", _spec("Natural Gas Storage")) == "77B"
    assert format_like(4.0, "4.00%", _spec("Federal Funds Rate")) == "4.00%"
    assert format_like((5.3, 2.77), "4.83|2.7", _spec("10-y Bond Auction")) == "5.30|2.8"
    assert format_like(-0.04, "0.2%", _spec("CPI m/m")) == "0.0%"
    # No template: the spec's own decimals and suffix.
    assert format_like(0.61, None, _spec("CPI m/m")) == "0.6%"
    assert format_like(7079.0, None, _spec("JOLTS Job Openings")) == "7.08M"
    assert format_like((5.3, 2.77), None, _spec("10-y Bond Auction")) == "5.30|2.8"
    # A template whose suffix differs from the spec's is ignored (spec defaults used).
    assert format_like(7079.0, "7079K", _spec("JOLTS Job Openings")) == "7.08M"
    assert format_like(0.61, "1.234", _spec("CPI m/m")) == "0.6%"
    assert format_like(-1892.0, "-1,234.5M", _spec("Crude Oil Inventories")) == "-1.9M"


def test_ff_values_match_handles_auction_pairs():
    assert registry.ff_values_match("4.83|2.7", "4.834|2.71") is True
    assert registry.ff_values_match("4.83|2.7", "4.83|2.9") is False
    assert registry.ff_values_match("0.6%", "0.6%") is True
    assert registry.ff_values_match("0.6%", "0.7%") is False
    assert registry.ff_values_match("4.83|2.7", "4.83") is False
    assert registry.ff_values_match(None, "0.6%") is False


# ---------------------------------------------------------------- fill rule

def _cpi_pct1() -> dict:
    return bls.parse_bls(_fixture("bls_timeseries.json"))["CUSR0000SA0"].pct1


CPI_ROW_TIME = dt.datetime(2026, 10, 14, 12, 30, tzinfo=UTC)


def test_decide_fill_writes_expected_period():
    d = decide_fill(_spec("CPI m/m"), CPI_ROW_TIME, "0.6%", "0.4%", _cpi_pct1(), False, None)
    assert d == registry.FillDecision("0.6%", "fill")


def test_decide_fill_waits_when_expected_period_absent():
    series = {p: v for p, v in _cpi_pct1().items() if p < D(2026, 9, 1)}     # API still shows August
    d = decide_fill(_spec("CPI m/m"), CPI_ROW_TIME, "0.6%", "0.4%", series, False, None)
    assert d.actual is None
    assert d.reason == "awaiting publication"


def test_decide_fill_skips_older_row_of_revised_series():
    d = decide_fill(_spec("CPI m/m"), CPI_ROW_TIME, "0.6%", "0.4%", _cpi_pct1(), True, "0.6%")
    assert d.actual is None
    assert d.reason.startswith("revised since release")
    assert "bls" in d.reason


def test_decide_fill_older_unrevised_row_needs_ff_previous_agreement():
    crude = eia.parse_eia_weekly(_fixture("eia_crude.json"))
    row_time = dt.datetime(2026, 10, 21, 14, 30, tzinfo=UTC)                    # week ending 2026-10-16
    spec = _spec("Crude Oil Inventories")
    assert spec.revises is False
    d = decide_fill(spec, row_time, "-0.1M", "-8.6M", crude, True, "-3.1M")
    assert d == registry.FillDecision("-3.1M", "fill")
    d = decide_fill(spec, row_time, "-0.1M", "-8.6M", crude, True, "-2.0M")
    assert d.actual is None
    assert d.reason == "disagrees with FF previous on the next release"


def test_decide_fill_uses_previous_as_template_when_forecast_missing():
    auctions = {D(2026, 10, 7): (5.3, 2.77)}
    row_time = dt.datetime(2026, 10, 7, 17, 1, tzinfo=UTC)
    d = decide_fill(_spec("10-y Bond Auction"), row_time, None, "4.83|2.7", auctions, False, None)
    assert d == registry.FillDecision("5.30|2.8", "fill")


# ---------------------------------------------------------------- registry shape

def test_registry_titles_sources_and_unresolved_census_left_out():
    for title in ("Final Wholesale Inventories m/m", "Prelim Wholesale Inventories m/m", "Goods Trade Balance"):
        assert title not in OFFICIAL_SPECS
    for title, spec in OFFICIAL_SPECS.items():
        assert spec.source in registry.PUBLISHER_SOURCES + ("fred",), title
        assert spec.transform in ("lin", "chg", "pch", "pc1", "auction"), title
        assert spec.frequency in ("monthly", "quarterly", "weekly", "event"), title
    assert _spec("Unemployment Claims").source == "fred"
    assert series_key(_spec("Advance GDP q/q")) == series_key(_spec("Final GDP q/q"))
    assert _spec("Federal Funds Rate").revises is False
    reestimates = {t for t, s in OFFICIAL_SPECS.items() if s.reestimate}
    assert reestimates == {"Prelim GDP q/q", "Final GDP q/q", "Prelim GDP Price Index q/q",
                           "Final GDP Price Index q/q", "Revised Nonfarm Productivity q/q",
                           "Revised Unit Labor Costs q/q"}


def test_decide_fill_reestimate_never_writes_the_stale_earlier_estimate():
    # Final GDP (third estimate of Q2) on release day: before BEA publishes, the API still holds
    # the second estimate, which FF shows as `previous`. Equal -> no write; different -> the new print.
    spec = _spec("Final GDP q/q")
    row_time = dt.datetime(2026, 9, 30, 12, 30, tzinfo=UTC)
    stale = {D(2026, 1, 1): 2.5, D(2026, 4, 1): 1.5}
    d = decide_fill(spec, row_time, "1.5%", "1.5%", stale, False, None)
    assert d.actual is None and d.reason.startswith("re-estimate")
    published = {D(2026, 1, 1): 2.5, D(2026, 4, 1): 2.2}
    assert decide_fill(spec, row_time, "1.5%", "1.5%", published, False, None) == registry.FillDecision("2.2%", "fill")
    assert decide_fill(spec, row_time, "1.5%", None, published, False, None).actual is None   # nothing to compare
    # The first estimate (Advance) needs no such check: its quarter is absent until publication.
    advance = dt.datetime(2026, 7, 30, 12, 30, tzinfo=UTC)
    assert decide_fill(_spec("Advance GDP q/q"), advance, "1.0%", "2.5%", published, False, None).actual == "2.2%"


def test_decide_fill_unchanged_reestimate_written_once_published():
    # Live: Prelim GDP q/q 2026-08-26 printed 1.5% with previous (Advance) 1.5%. BEA's table note
    # "LastRevised: <date>" proves the second estimate is out, so the unchanged value is written.
    spec = _spec("Prelim GDP q/q")
    row_time = dt.datetime(2026, 8, 26, 12, 30, tzinfo=UTC)
    series = {D(2026, 1, 1): 2.5, D(2026, 4, 1): 1.5}
    before = registry.ReestimateEvidence(last_revised=D(2026, 7, 30))           # still the Advance table
    after = registry.ReestimateEvidence(last_revised=D(2026, 8, 26))
    d = decide_fill(spec, row_time, "1.5%", "1.5%", series, False, None, reestimate_evidence=before)
    assert d == registry.FillDecision(None, "awaiting publication")
    d = decide_fill(spec, row_time, "1.5%", "1.5%", series, False, None, reestimate_evidence=after)
    assert d == registry.FillDecision("1.5%", "fill")
    # Evidence decides on its own: a value that differs from `previous` is not written before publication.
    changed = {D(2026, 1, 1): 2.5, D(2026, 4, 1): 1.7}
    d = decide_fill(spec, row_time, "1.5%", "1.5%", changed, False, None, reestimate_evidence=before)
    assert d.actual is None and d.reason == "awaiting publication"
    # No evidence at all (note missing): only a changed value is provably new.
    d = decide_fill(spec, row_time, "1.5%", "1.5%", series, False, None)
    assert d.actual is None and d.reason == "re-estimate not distinguishable (no revision evidence from bea)"
    # An older re-estimate row still never takes today's revised number.
    d = decide_fill(spec, row_time, "1.5%", "1.5%", series, True, "1.5%", reestimate_evidence=after)
    assert d.reason.startswith("revised since release")


def test_decide_fill_unchanged_revised_productivity_from_bls_footnotes():
    # Live: Revised Nonfarm Productivity 2026-09-03, previous 1.4%; BLS still shows Q2 1.4 with no
    # footnote, but Unit Labor Costs (same release) carry "R": the revised estimate is out.
    spec = _spec("Revised Nonfarm Productivity q/q")
    row_time = dt.datetime(2026, 9, 3, 12, 30, tzinfo=UTC)
    fake = FakeFetcher([(_url_has("api.bls.gov"), _ok(_fixture("bls_timeseries.json")))])
    out = fetch_for_specs([spec], D(2026, 9, 1), fake, KEYS)
    posted = set(fake.calls[0][3]["seriesid"])
    assert set(registry._PRODUCTIVITY_FAMILY) <= posted                         # one POST, family included
    evidence = out.evidence[series_key(spec)]
    assert D(2026, 4, 1) in evidence.revised_periods
    series = out.data[series_key(spec)]
    assert series[D(2026, 4, 1)] == 1.4
    d = decide_fill(spec, row_time, "1.4%", "1.4%", series, False, None, reestimate_evidence=evidence)
    assert d == registry.FillDecision("1.4%", "fill")
    # Before the Revised release no series of the release has "R" on Q2.
    d = decide_fill(spec, row_time, "1.4%", "1.4%", series, False, None,
                    reestimate_evidence=registry.ReestimateEvidence())
    assert d == registry.FillDecision(None, "awaiting publication")


def test_bls_parse_keeps_revised_footnotes():
    parsed = bls.parse_bls(_fixture("bls_timeseries.json"))
    assert D(2026, 4, 1) in parsed["PRS85006112"].revised                       # {"code": "R", "text": "revised"}
    assert D(2026, 4, 1) not in parsed["PRS85006092"].revised                   # unchanged: no footnote


def test_bea_last_revised_from_table_note():
    assert bea.parse_last_revised(_fixture("bea_T10101_Q.json"), "T10101") == D(2026, 9, 30)
    assert bea.parse_last_revised(_fixture("bea_T10107_Q.json"), "T10107") == D(2026, 9, 30)
    assert bea.parse_last_revised(_fixture("bea_T10101_Q.json"), "T10107") is None   # another table's note
    assert bea.parse_last_revised('{"BEAAPI": {"Results": {"Data": []}}}', "T10101") is None
    assert bea.parse_last_revised("not json", "T10101") is None
    body = json.dumps({"BEAAPI": {"Results": {"Notes": [
        {"NoteRef": "T10101", "NoteText": "Table 1.1.1. ... - LastRevised: August 26,2026"}]}}})
    assert bea.parse_last_revised(body, "T10101") == D(2026, 8, 26)


def test_fetch_for_specs_bea_evidence_per_table():
    fake = FakeFetcher([(_url_has("apps.bea.gov"), _ok(_fixture("bea_T10101_Q.json")))])
    specs = [_spec("Advance GDP q/q"), _spec("Final GDP q/q")]
    out = fetch_for_specs(specs, D(2026, 9, 1), fake, KEYS)
    assert len(fake.calls) == 1
    assert out.evidence[series_key(_spec("Final GDP q/q"))] == registry.ReestimateEvidence(last_revised=D(2026, 9, 30))
    # FetchOutcome built without evidence (older callers, test fakes) still works.
    assert FetchOutcome({}, {}).evidence == {}


# ---------------------------------------------------------------- coverage

def test_coverage_lists():
    for title in ("FOMC Member Waller Speaks", "Beige Book", "FOMC Press Conference", "FOMC Statement",
                  "Fed Monetary Policy Report", "President Trump Speaks", "FOMC Meeting Minutes"):
        assert coverage.coverage_for(title) == "no_actual_expected", title
    for title in ("ISM Services PMI", "Prelim UoM Consumer Sentiment", "CB Consumer Confidence",
                  "Philly Fed Manufacturing Index", "Richmond Manufacturing Index", "ADP Weekly Employment Change"):
        assert coverage.coverage_for(title) == "proprietary", title
    for title in ("Industrial Production m/m", "Goods Trade Balance", "Some Unknown Title"):
        assert coverage.coverage_for(title) == "not_mapped", title
    assert coverage.coverage_for("CPI m/m") == "official"
    assert "Industrial Production m/m" in coverage.NOT_MAPPED


def _row(conn, title, when, forecast=None, previous=None, actual=None, country="USD", source="live"):
    conn.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, surprise_direction, "
        "recorded_at_utc, updated_at_utc, source, impact, country) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (title, when.isoformat(), forecast, previous, actual, None, when.isoformat(), when.isoformat(),
         source, "High", country),
    )
    conn.commit()


def test_missing_numeric_rows_excludes_speeches_and_text_only_and_non_usd(tmp_path):
    conn = ws.get_connection(tmp_path / "d.db")
    t = dt.datetime(2026, 10, 20, 12, 30, tzinfo=UTC)
    _row(conn, "CPI m/m", t, "0.3%", "0.4%")                                    # kept
    _row(conn, "10-y Bond Auction", t + dt.timedelta(hours=1), None, "4.83|2.7")  # kept: auction pair is numeric
    _row(conn, "ISM Services PMI", t + dt.timedelta(hours=2), None, "52.1")      # kept: proprietary still listed
    _row(conn, "FOMC Member Waller Speaks", t, None, None)                       # no actual expected
    _row(conn, "Federal Funds Rate", t - dt.timedelta(hours=3), "4.00%", "4.00%", country="EUR")   # non-USD
    _row(conn, "Fed Text Thing", t + dt.timedelta(hours=3), None, None)          # text-only
    _row(conn, "Beige Book", t + dt.timedelta(hours=4), "1.0", "1.0")             # no actual expected even if numeric
    _row(conn, "PPI m/m", t + dt.timedelta(hours=5), "0.2%", "0.1%", actual="0.2%")   # filled
    _row(conn, "Core PPI m/m", t + dt.timedelta(days=3), "0.2%", "0.1%")          # out of range
    rows = coverage.missing_numeric_rows(conn, t - dt.timedelta(days=1), t + dt.timedelta(days=1))
    assert [r["event_title"] for r in rows] == ["CPI m/m", "10-y Bond Auction", "ISM Services PMI"]


def test_load_gate_results_missing_or_corrupt_is_empty(tmp_path):
    assert coverage.load_gate_results(tmp_path / "absent.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert coverage.load_gate_results(bad) == {}
    wrong_shape = tmp_path / "list.json"
    wrong_shape.write_text("[1, 2]", encoding="utf-8")
    assert coverage.load_gate_results(wrong_shape) == {}
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"titles": {
        "CPI m/m": {"status": "verified", "matches": 9, "comparisons": 10, "revision_explained": 1,
                    "identity": "ok", "mismatches": []},
        "Broken": {"status": "verified"},
    }}), encoding="utf-8")
    loaded = coverage.load_gate_results(good)
    assert loaded == {"CPI m/m": coverage.GateResult("verified", 9, 10, "ok")}


def test_enabled_titles_only_verified():
    gate = {
        "CPI m/m": coverage.GateResult("verified", 9, 10, "ok"),
        "PPI m/m": coverage.GateResult("suspect", 1, 10, "ok"),
        "Retail Sales m/m": coverage.GateResult("key_inactive", 0, 0, "none"),
        "Not A Registry Title": coverage.GateResult("verified", 5, 5, "ok"),
    }
    assert coverage.enabled_titles(gate) == frozenset({"CPI m/m"})


def test_gate_results_path_is_the_committed_file():
    assert coverage.GATE_RESULTS_PATH == Path(registry.__file__).resolve().parent / "gate_results.json"


# ---------------------------------------------------------------- fetch grouping

def test_fetch_for_specs_one_bls_call_for_many_titles_and_errors_per_source():
    fake = FakeFetcher([
        (_url_has("api.bls.gov"), _ok(_fixture("bls_timeseries.json"))),
        (_url_has("api.eia.gov"), HttpResponse(429, "", {"Retry-After": "30"})),
    ])
    specs = [_spec(t) for t in ("CPI m/m", "CPI y/y", "Core CPI m/m", "Non-Farm Employment Change",
                                "Crude Oil Inventories")]
    out = fetch_for_specs(specs, D(2026, 9, 1), fake, KEYS)
    assert isinstance(out, FetchOutcome)
    bls_posts = [c for c in fake.calls if "api.bls.gov" in c[1]]
    assert len(bls_posts) == 1
    assert set(bls_posts[0][3]["seriesid"]) == {"CUSR0000SA0", "CUUR0000SA0", "CUSR0000SA0L1E", "CES0000000001"}
    assert out.data[series_key(_spec("CPI m/m"))][D(2026, 9, 1)] == 0.6
    assert out.data[series_key(_spec("CPI y/y"))][D(2026, 9, 1)] == 3.7
    assert out.data[series_key(_spec("Non-Farm Employment Change"))][D(2026, 9, 1)] == 159044
    assert isinstance(out.errors["eia"], SourceRateLimited)
    assert "bls" not in out.errors
    assert series_key(_spec("Crude Oil Inventories")) not in out.data


def test_series_key_distinguishes_field():
    assert series_key(_spec("CPI m/m")) != series_key(dataclasses.replace(_spec("CPI m/m"), field="pct12"))
    assert series_key(_spec("Advance GDP q/q")) == series_key(_spec("Final GDP q/q"))


def test_fetch_for_specs_census_bea_fed_treasury_fred_routes():
    fake = FakeFetcher([
        (_url_has("eits/marts"), _ok(_fixture("census_marts.json"))),
        (_url_has("apps.bea.gov"), _ok(_fixture("bea_T20807_M.json"))),
        (_url_has("press_monetary.xml"), _ok(_fixture("fed_press_monetary.xml"))),
        (_url_has("monetary20261028a"), _ok(_fixture("fed_monetary20261028a.html"))),
        (_url_has("monetary2026"), _ok(_fixture("fed_monetary20260916a.html"))),
        (_url_has("treasurydirect"), _ok(_fixture("treasury_note.json"))),
        (_url_has("stlouisfed"), _ok(_fixture("fred_ICSA.json"))),
    ])
    specs = [_spec(t) for t in ("Retail Sales m/m", "Core Retail Sales m/m", "Core PCE Price Index m/m",
                                "Federal Funds Rate", "10-y Bond Auction", "Unemployment Claims")]
    out = fetch_for_specs(specs, D(2026, 9, 1), fake, KEYS)
    assert out.errors == {}
    assert len([c for c in fake.calls if "eits/marts" in c[1]]) == 1
    assert out.data[series_key(_spec("Core PCE Price Index m/m"))][D(2026, 8, 1)] == 0.2
    assert out.data[series_key(_spec("Federal Funds Rate"))][D(2026, 10, 28)] == 4.0
    assert out.data[series_key(_spec("10-y Bond Auction"))][D(2026, 10, 7)] == (5.3, 2.77)
    assert out.data[series_key(_spec("Unemployment Claims"))][D(2026, 10, 17)] == 194000.0
    assert D(2026, 8, 1) in out.data[series_key(_spec("Retail Sales m/m"))]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
