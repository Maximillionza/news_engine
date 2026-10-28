"""
Tests for data_layer.official_actuals adapters (ACT Task 1). Every adapter
runs on a fake `Fetcher` backed by the recorded, key-scrubbed fixtures in
tests/fixtures/official_actuals/ (scripts/record_official_fixtures.py); no
network, no real key.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.official_actuals import bea, bls, census, eia, fed, fred_current, treasury
from data_layer.official_actuals.http import (
    HttpResponse, KeyInactiveError, SourceError, SourceRateLimited, SourceTransportError,
    USER_AGENT, check_status, requests_fetcher,
)
from data_layer.official_actuals.keys import Keys, load_keys

D = dt.date
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "official_actuals"
SECRET = "SECRETKEY123"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _ok(text: str, status: int = 200, headers: Optional[dict] = None) -> HttpResponse:
    return HttpResponse(status, text, headers or {})


class FakeFetcher:
    """Answers from a list of (predicate, response) routes; records every call."""

    def __init__(self, routes):
        self.routes = routes
        self.calls: list[tuple[str, str, Optional[dict], Optional[dict]]] = []

    def __call__(self, method, url, params, json_body):
        self.calls.append((method, url, params, json_body))
        for predicate, response in self.routes:
            if predicate(method, url, params, json_body):
                return response(method, url, params, json_body) if callable(response) else response
        raise AssertionError(f"unexpected request {method} {url}")


def _url_has(fragment: str):
    return lambda method, url, params, body: fragment in url


# ---------------------------------------------------------------- BLS

def test_bls_parses_levels_and_pct_changes():
    fake = FakeFetcher([(_url_has("api.bls.gov"), _ok(_fixture("bls_timeseries.json")))])
    out = bls.fetch_bls(["CES0000000001", "CUSR0000SA0", "CUUR0000SA0", "CIS1010000000000Q"], SECRET, fake, 2025, 2026)
    assert out["CES0000000001"].levels[D(2026, 9, 1)] == 159044
    assert out["CES0000000001"].levels[D(2026, 8, 1)] == 159015
    assert out["CUSR0000SA0"].pct1[D(2026, 9, 1)] == 0.6
    assert out["CUUR0000SA0"].pct12[D(2026, 9, 1)] == 3.7
    assert out["CIS1010000000000Q"].levels[D(2026, 4, 1)] == 0.9          # Q02 -> April
    # M13 (annual average) rows never become a period.
    assert all(p.day == 1 for s in out.values() for p in s.levels)
    body = json.loads(_fixture("bls_timeseries.json"))
    m13 = {"year": "2025", "period": "M13", "value": "999"}
    body["Results"]["series"][0]["data"].append(m13)
    fake = FakeFetcher([(_url_has("api.bls.gov"), _ok(json.dumps(body)))])
    out = bls.fetch_bls(["CES0000000001"], SECRET, fake, 2025, 2026)
    assert 999.0 not in out["CES0000000001"].levels.values()


def test_bls_batches_fifty_series_per_post():
    def answer(method, url, params, body):
        series = [{"seriesID": sid, "data": []} for sid in body["seriesid"]]
        return _ok(json.dumps({"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": series}}))

    fake = FakeFetcher([(_url_has("api.bls.gov"), answer)])
    ids = [f"SERIES{i:03d}" for i in range(51)]
    out = bls.fetch_bls(ids, SECRET, fake, 2025, 2026)
    assert bls.BLS_MAX_SERIES_PER_QUERY == 50
    assert len(fake.calls) == 2
    assert [len(c[3]["seriesid"]) for c in fake.calls] == [50, 1]
    for method, _, _, body in fake.calls:
        assert method == "POST"
        assert body["registrationkey"] == SECRET
        assert body["calculations"] is True
        assert (body["startyear"], body["endyear"]) == ("2025", "2026")
    assert set(out) == set(ids)


def test_bls_daily_threshold_raises_rate_limited():
    body = {"status": "REQUEST_NOT_PROCESSED", "responseTime": 10, "message": [
        "Request could not be serviced, as the daily threshold for total number of requests allocated to the user has been reached."],
        "Results": {}}
    fake = FakeFetcher([(_url_has("api.bls.gov"), _ok(json.dumps(body)))])
    with pytest.raises(SourceRateLimited):
        bls.fetch_bls(["CUSR0000SA0"], SECRET, fake, 2025, 2026)


def test_bls_invalid_key_raises_key_inactive_and_other_failures_raise():
    body = {"status": "REQUEST_NOT_PROCESSED", "message": ["The key provided by the User is invalid."], "Results": {}}
    fake = FakeFetcher([(_url_has("api.bls.gov"), _ok(json.dumps(body)))])
    with pytest.raises(KeyInactiveError):
        bls.fetch_bls(["CUSR0000SA0"], SECRET, fake, 2025, 2026)
    fake = FakeFetcher([(_url_has("api.bls.gov"), _ok("<html>oops</html>"))])
    with pytest.raises(SourceError):
        bls.fetch_bls(["CUSR0000SA0"], SECRET, fake, 2025, 2026)
    fake = FakeFetcher([])
    with pytest.raises(KeyInactiveError):
        bls.fetch_bls(["CUSR0000SA0"], "", fake, 2025, 2026)
    assert fake.calls == []


# ---------------------------------------------------------------- BEA

def _bea_route():
    def answer(method, url, params, body):
        return _ok(_fixture(f"bea_{params['TableName']}_{params['Frequency']}.json"))
    return [(_url_has("apps.bea.gov"), answer)]


def test_bea_parses_quarter_and_month_periods_and_commas():
    fake = FakeFetcher(_bea_route())
    q = bea.fetch_nipa("T10101", "Q", [2025, 2026], SECRET, fake)
    assert q["A191RL"][D(2026, 4, 1)] == 2.2
    m = bea.fetch_nipa("T20807", "M", [2025, 2026], SECRET, fake)
    assert m["DPCCRGM"][D(2026, 8, 1)] == 0.2
    income = bea.fetch_nipa("T20600", "M", [2025, 2026], SECRET, fake)
    assert income["A065RC"][D(2026, 8, 1)] == 27626933.0
    params = fake.calls[0][2]
    assert params["UserID"] == SECRET and params["Year"] == "2025,2026"
    assert params["method"] == "GetData" and params["datasetname"] == "NIPA" and params["ResultFormat"] == "JSON"


def test_bea_invalid_key_raises_key_inactive():
    body = {"BEAAPI": {"Request": {"RequestParam": []}, "Results": {"Error": {
        "APIErrorCode": "3", "APIErrorDescription": "The UserId provided is invalid."}}}}
    fake = FakeFetcher([(_url_has("apps.bea.gov"), _ok(json.dumps(body)))])
    with pytest.raises(KeyInactiveError):
        bea.fetch_nipa("T10101", "Q", [2026], SECRET, fake)
    body["BEAAPI"]["Results"]["Error"]["APIErrorCode"] = "40"
    fake = FakeFetcher([(_url_has("apps.bea.gov"), _ok(json.dumps(body)))])
    with pytest.raises(SourceError) as info:
        bea.fetch_nipa("T10101", "Q", [2026], SECRET, fake)
    assert not isinstance(info.value, KeyInactiveError)
    fake = FakeFetcher([])
    with pytest.raises(KeyInactiveError):
        bea.fetch_nipa("T10101", "Q", [2026], "", fake)
    assert fake.calls == []


# ---------------------------------------------------------------- Census

def test_census_missing_key_page_raises_key_inactive():
    fake = FakeFetcher([(_url_has("api.census.gov"), _ok(_fixture("census_missing_key.html")))])
    with pytest.raises(KeyInactiveError):
        census.fetch_eits("marts", SECRET, fake, D(2025, 6, 1))

    def answer(method, url, params, body):
        return _ok(_fixture(f"census_{url.rsplit('/', 1)[1]}.json"))

    fake = FakeFetcher([(_url_has("api.census.gov"), answer)])
    census.fetch_eits("advm3", SECRET, fake, D(2025, 6, 1))
    params = fake.calls[-1][2]
    assert params["for"] == "us:*"
    assert params["time"] == "from 2025-06" and params["key"] == SECRET
    marts = census.fetch_eits("marts", SECRET, fake, D(2025, 6, 1))
    assert "for" not in fake.calls[-1][2]
    assert marts[("44X72", "MPCSM")][D(2026, 9, 1)] == 0.8
    # resconst carries Northeast/Midwest/South/West rows: only US-level, SA rows survive.
    starts = census.fetch_eits("resconst", SECRET, fake, D(2025, 6, 1))
    assert starts[("ASTARTS", "TOTAL")][D(2026, 9, 1)] == 1221.0
    raw = json.loads(_fixture("census_resconst.json"))
    header = raw[0]
    regional = [r for r in raw[1:] if r[header.index("geo_level_code")] != "US"]
    assert regional, "fixture must carry non-US rows for this test to mean anything"
    us_sa_values = {(r[header.index("category_code")], r[header.index("data_type_code")], r[header.index("time")])
                    for r in raw[1:] if r[header.index("geo_level_code")] == "US" and r[header.index("seasonally_adj")] == "yes"}
    parsed = {(c, t, p.strftime("%Y-%m")) for (c, t), series in starts.items() for p in series}
    assert parsed == us_sa_values


def test_census_no_key_and_invalid_key_page():
    fake = FakeFetcher([])
    with pytest.raises(KeyInactiveError):
        census.fetch_eits("marts", "", fake, D(2026, 1, 1))
    assert fake.calls == []
    page = "<html><head><title>Invalid Key</title></head><body>x</body></html>"
    fake = FakeFetcher([(_url_has("api.census.gov"), _ok(page))])
    with pytest.raises(KeyInactiveError):
        census.fetch_eits("marts", SECRET, fake, D(2026, 1, 1))


# ---------------------------------------------------------------- EIA

def test_eia_weekly_returns_levels_by_week_end():
    def answer(method, url, params, body):
        name = "crude" if "petroleum" in url else "natgas"
        return _ok(_fixture(f"eia_{name}.json"))

    fake = FakeFetcher([(_url_has("api.eia.gov"), answer)])
    crude = eia.fetch_eia_weekly("petroleum/stoc/wstk", "WCESTUS1", SECRET, fake)
    assert crude[D(2026, 10, 23)] == 410625
    assert crude[D(2026, 10, 16)] == 412517
    gas = eia.fetch_eia_weekly("natural-gas/stor/wkly", "NW2_EPG0_SWO_R48_BCF", SECRET, fake)
    assert gas[D(2026, 10, 16)] == 3644
    params = fake.calls[0][2]
    assert params["api_key"] == SECRET and params["facets[series][]"] == "WCESTUS1"
    assert params["frequency"] == "weekly" and params["sort[0][direction]"] == "desc"
    assert fake.calls[0][1] == "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"


def test_eia_invalid_key_raises_key_inactive():
    body = json.dumps({"error": {"code": "API_KEY_INVALID", "message": "An invalid api_key was supplied."}})
    fake = FakeFetcher([(_url_has("api.eia.gov"), _ok(body, status=403))])
    with pytest.raises(KeyInactiveError):
        eia.fetch_eia_weekly("petroleum/stoc/wstk", "WCESTUS1", SECRET, fake)


# ---------------------------------------------------------------- Fed

def _fed_routes():
    return [
        (_url_has("press_monetary.xml"), _ok(_fixture("fed_press_monetary.xml"))),
        (_url_has("monetary20261028a.htm"), _ok(_fixture("fed_monetary20261028a.html"))),
        (_url_has("monetary20260916a.htm"), _ok(_fixture("fed_monetary20260916a.html"))),
    ]


def test_fed_parses_upper_bound_with_tags_and_fractions():
    assert fed.parse_target_range(_fixture("fed_monetary20261028a.html")) == (3.75, 4.0)
    page = _fixture("fed_monetary20260916a.html")
    assert "<strong> </strong>to 3-3/4" in page
    assert fed.parse_target_range(page) == (3.75, 4.0)
    assert fed.parse_target_range("<p>target range for the federal funds rate at 0 to 1/4 percent.</p>") == (0.0, 0.25)
    assert fed.parse_target_range("<p>No decision here.</p>") is None

    fake = FakeFetcher(_fed_routes())
    out = fed.fetch_fomc_upper_bounds(fake, D(2026, 9, 1))
    assert out == {D(2026, 10, 28): 4.0, D(2026, 9, 16): 4.0}
    fetched = [c[1] for c in fake.calls]
    # Only FOMC statements: minutes and discount-rate items are never fetched.
    assert not any("monetary20261013a" in u for u in fetched)
    assert len(fetched) == 3


def test_fed_never_follows_links_off_the_fed_site():
    rss = """<?xml version="1.0"?><rss><channel><item><title>Federal Reserve issues FOMC statement</title>
    <link>https://evil.example.com/monetary20261028a.htm</link><pubDate>Wed, 28 Oct 2026 18:00:00 GMT</pubDate></item>
    </channel></rss>"""
    fake = FakeFetcher([(_url_has("press_monetary.xml"), _ok(rss))])
    assert fed.fetch_fomc_upper_bounds(fake, D(2026, 9, 1)) == {}
    assert len(fake.calls) == 1


# ---------------------------------------------------------------- TreasuryDirect

def test_treasury_includes_reopenings_and_excludes_tips():
    rows = json.loads(_fixture("treasury_note.json"))
    reopening = [r for r in rows if r["originalSecurityTerm"] == "10-Year" and r["securityTerm"] != "10-Year"]
    assert reopening, "fixture must carry a 10-year reopening"
    tips = dict(rows[0], type="TIPS", originalSecurityTerm="10-Year", highYield="1.900",
                bidToCoverRatio="2.40", competitiveAuctionCloseDate="2026-09-18T00:00:00")
    body = json.dumps(rows + [tips])

    fake = FakeFetcher([(_url_has("treasurydirect.gov"), _ok(body))])
    out = treasury.fetch_auctions("10-Year", "Note", fake)
    assert out[D(2026, 10, 7)] == (5.3, 2.77)
    assert out[D(2026, 9, 9)] == (4.834, 2.71)
    assert D(2026, 9, 18) not in out
    assert fake.calls[0][2] == {"format": "json", "type": "Note", "days": 400}

    fake = FakeFetcher([(_url_has("treasurydirect.gov"), _ok(_fixture("treasury_bond.json")))])
    bonds = treasury.fetch_auctions("30-Year", "Bond", fake)
    assert bonds and all(isinstance(v, tuple) and len(v) == 2 for v in bonds.values())


# ---------------------------------------------------------------- FRED (claims)

def test_fred_current_reads_latest_values_and_maps_errors():
    fake = FakeFetcher([(_url_has("api.stlouisfed.org"), _ok(_fixture("fred_ICSA.json")))])
    out = fred_current.fetch_fred_current("ICSA", SECRET, fake, D(2026, 1, 1))
    assert out[D(2026, 10, 17)] == 194000.0
    params = fake.calls[0][2]
    assert params["series_id"] == "ICSA" and params["api_key"] == SECRET and params["observation_start"] == "2026-01-01"
    fake = FakeFetcher([(_url_has("api.stlouisfed.org"), _ok("<html>FRED is down for maintenance</html>"))])
    with pytest.raises(SourceError):
        fred_current.fetch_fred_current("ICSA", SECRET, fake, D(2026, 1, 1))
    bad_key = json.dumps({"error_code": 400, "error_message": "Bad Request.  The value for variable api_key is not registered."})
    fake = FakeFetcher([(_url_has("api.stlouisfed.org"), _ok(bad_key, status=400))])
    with pytest.raises(KeyInactiveError):
        fred_current.fetch_fred_current("ICSA", SECRET, fake, D(2026, 1, 1))


# ---------------------------------------------------------------- HTTP seam

def test_check_status_maps_429_and_5xx_with_retry_after():
    with pytest.raises(SourceRateLimited) as info:
        check_status(_ok("", 429, {"Retry-After": "30"}), "bls")
    assert info.value.retry_after_seconds == 30.0
    with pytest.raises(SourceRateLimited) as info:
        check_status(_ok("", 503, {"retry-after": "Wed, 28 Oct 2099 18:00:00 GMT"}), "bea")
    assert info.value.retry_after_seconds and info.value.retry_after_seconds > 0
    with pytest.raises(SourceRateLimited) as info:
        check_status(_ok("", 503), "bea")
    assert info.value.retry_after_seconds is None
    with pytest.raises(SourceError) as info:
        check_status(_ok("", 404), "census")
    assert not isinstance(info.value, SourceRateLimited)
    check_status(_ok("", 200), "eia")      # no raise


def test_errors_never_carry_url_or_key(monkeypatch: pytest.MonkeyPatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError(f"https://x?api_key={SECRET}")

    # A custom fetcher raising a requests error straight into an adapter ...
    with pytest.raises(SourceTransportError) as info:
        eia.fetch_eia_weekly("petroleum/stoc/wstk", "WCESTUS1", SECRET, boom)
    assert SECRET not in str(info.value) and "http" not in str(info.value)
    assert info.value.__cause__ is None and info.value.__suppress_context__
    # ... and the production fetcher.
    monkeypatch.setattr(requests, "request", boom)
    fetch = requests_fetcher()
    with pytest.raises(SourceTransportError) as info:
        fetch("GET", f"https://api.eia.gov/v2/x?api_key={SECRET}", {"api_key": SECRET}, None)
    assert SECRET not in str(info.value) and "http" not in str(info.value)
    # HTTP errors carry the status only.
    for status in (400, 429, 500):
        fake = FakeFetcher([(_url_has("api.bls.gov"), _ok(f"error for registrationkey={SECRET}", status))])
        with pytest.raises(SourceError) as info:
            bls.fetch_bls(["CUSR0000SA0"], SECRET, fake, 2025, 2026)
        assert SECRET not in str(info.value) and "http" not in str(info.value).lower().replace("http ", "")


def test_requests_fetcher_sends_user_agent(monkeypatch: pytest.MonkeyPatch):
    seen: dict = {}

    class Resp:
        status_code = 200
        text = "{}"
        headers = {"Content-Type": "application/json"}
        encoding = "utf-8"

    def fake_request(method, url, **kwargs):
        seen.update(kwargs, method=method, url=url)
        return Resp()

    monkeypatch.setattr(requests, "request", fake_request)
    resp = requests_fetcher(timeout_seconds=5)("GET", "https://api.bls.gov/x", {"a": "1"}, None)
    assert resp == HttpResponse(200, "{}", {"Content-Type": "application/json"})
    assert seen["headers"]["User-Agent"] == USER_AGENT and seen["timeout"] == 5


# ---------------------------------------------------------------- fixtures and keys

def test_fixtures_carry_no_key_material():
    files = sorted(FIXTURES.iterdir())
    assert len(files) >= 20
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "api_key=" not in text, path.name
        for m in re.finditer(r'registrationkey"?\s*[:=]\s*"?([^"&,}\s]*)', text, re.I):
            assert m.group(1) == "REDACTED", path.name
        for m in re.finditer(r'"ParameterName"\s*:\s*"USERID"\s*,\s*"ParameterValue"\s*:\s*"([^"]*)"', text, re.I):
            assert m.group(1) == "REDACTED", path.name
        for m in re.finditer(r'[?&](?:api_key|key|UserID)=([^&"\s<]+)', text):
            assert m.group(1) == "REDACTED", path.name
    bea_files = [p for p in files if p.name.startswith("bea_")]
    assert bea_files and all('"USERID","ParameterValue":"REDACTED"' in p.read_text(encoding="utf-8") for p in bea_files)


def test_load_keys_reads_env_file_without_exporting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for name in ("BLS_API_KEY", "BEA_API_KEY", "CENSUS_API_KEY", "EIA_API_KEY", "FRED_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    env = tmp_path / ".env"
    env.write_text("BLS_API_KEY=b1\nBEA_API_KEY=b2\nCENSUS_API_KEY=c3\nEIA_API_KEY=e4\nFRED_API_KEY=f5\nOTHER=x\n", encoding="utf-8")
    before = dict(os.environ)
    keys = load_keys(env)
    assert keys == Keys(bls="b1", bea="b2", census="c3", eia="e4", fred="f5")
    assert dict(os.environ) == before
    assert "b1" not in repr(keys) and "f5" not in repr(keys)
    with pytest.raises(FileNotFoundError):
        load_keys(tmp_path / "missing.env")
