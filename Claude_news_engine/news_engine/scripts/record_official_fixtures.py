"""
Record the official-actuals test fixtures (ACT Task 1, 2026-10-28).

READ-ONLY: one GET (BLS: one POST) per endpoint against the official
publishers, nothing written except the fixture files under
tests/fixtures/official_actuals/. Every key value is replaced with
"REDACTED" in each response body BEFORE it is saved (BEA echoes the key as
USERID), and the console shows only the fixture name, the HTTP status and
the latest period found. Keys are never printed.

With `--resolve-census DB` it instead reads the recorded Census fixtures
and the given dashboard DB (opened mode=ro) and lists, for each Census
title, (a) the (category, data type) codes whose value equals the latest
stored FF actual (else previous) of that title, and, when `--env-file` is
also given, (b) the codes equal to the title's FRED twin (current values,
last 6 periods; read-only FRED GETs). A code is resolved when (a) or (b)
names it unambiguously; a title with neither is reported unresolved and must
stay out of the registry (never guess a code).

Usage:
    python scripts/record_official_fixtures.py --env-file <live .env>
    python scripts/record_official_fixtures.py --resolve-census <dashboard.db> [--env-file <live .env>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.official_actuals.http import Fetcher, HttpResponse, SourceError, requests_fetcher
from data_layer.official_actuals.keys import Keys, load_keys

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "official_actuals"
REDACTED = "REDACTED"

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BEA_URL = "https://apps.bea.gov/api/data"
CENSUS_URL = "https://api.census.gov/data/timeseries/eits/{program}"
EIA_URL = "https://api.eia.gov/v2/{route}/data/"
FED_RSS_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"
FED_PAGE_URL = "https://www.federalreserve.gov/newsevents/pressreleases/{name}"
TREASURY_URL = "https://www.treasurydirect.gov/TA_WS/securities/auctioned"
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

BLS_SERIES = (
    "CES0000000001", "LNS14000000", "CES0500000003", "CUSR0000SA0", "CUUR0000SA0",
    "CUSR0000SA0L1E", "CUUR0000SA0L1E", "WPSFD4", "WPSFD49104", "EIUIR",
    "JTS000000000000000JOL", "CIS1010000000000Q", "PRS85006092", "PRS85006112",
)
BEA_TABLES = (("T10101", "Q"), ("T10107", "Q"), ("T20807", "M"), ("T20600", "M"))
CENSUS_PROGRAMS = ("marts", "advm3", "m3", "resconst", "ressales", "vip", "mtis", "mwts", "mwtsadv", "ftdadv", "ftd")
CENSUS_GET = "cell_value,data_type_code,category_code,seasonally_adj,time_slot_id,geo_level_code"
CENSUS_SINCE = "2026-01"          # keeps the recorded files small; 9+ months is enough for tests and resolution
EIA_SERIES = (("crude", "petroleum/stoc/wstk", "WCESTUS1"), ("natgas", "natural-gas/stor/wkly", "NW2_EPG0_SWO_R48_BCF"))
FED_PAGES = ("monetary20261028a.htm", "monetary20260916a.htm")


def scrub(text: str, keys: Keys) -> str:
    """Every key value -> REDACTED (longest first, so a key containing another is fully replaced)."""
    for value in sorted(keys.values(), key=len, reverse=True):
        text = text.replace(value, REDACTED)
    return text


def _save(name: str, resp: HttpResponse, keys: Keys) -> str:
    body = scrub(resp.text, keys)
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    (FIXTURE_DIR / name).write_text(body, encoding="utf-8", newline="\n")
    return body


def _latest(pattern: str, body: str) -> str:
    found = re.findall(pattern, body)
    return max(found) if found else "-"


def _record(name: str, call: Callable[[], HttpResponse], keys: Keys, period_pattern: str) -> None:
    try:
        resp = call()
    except SourceError as exc:
        print(f"{name:32s} ERROR {type(exc).__name__}")
        return
    body = _save(name, resp, keys)
    print(f"{name:32s} HTTP {resp.status}  latest {_latest(period_pattern, body)}")


def record_all(fetcher: Fetcher, keys: Keys) -> None:
    year = dt.date.today().year
    _record("bls_timeseries.json", lambda: fetcher("POST", BLS_URL, None, {
        "seriesid": list(BLS_SERIES), "startyear": str(year - 1), "endyear": str(year),
        "calculations": True, "registrationkey": keys.bls,
    }), keys, r'"year":"(\d{4})","period":"(?:M|Q)\d\d"')
    for table, freq in BEA_TABLES:
        _record(f"bea_{table}_{freq}.json", lambda t=table, f=freq: fetcher("GET", BEA_URL, {
            "UserID": keys.bea, "method": "GetData", "datasetname": "NIPA", "TableName": t,
            "Frequency": f, "Year": f"{year - 1},{year}", "ResultFormat": "JSON",
        }, None), keys, r'"TimePeriod":"(\d{4}[QM]\d+)"')
    for program in CENSUS_PROGRAMS:
        params = {"get": CENSUS_GET, "time": f"from {CENSUS_SINCE}", "key": keys.census}
        if program in ("advm3", "m3"):
            params["for"] = "us:*"
        _record(f"census_{program}.json", lambda p=program, q=params: fetcher("GET", CENSUS_URL.format(program=p), q, None),
                keys, r'"(\d{4}-\d\d)"')
    _record("census_missing_key.html", lambda: fetcher("GET", CENSUS_URL.format(program="marts"),
            {"get": CENSUS_GET, "time": f"from {CENSUS_SINCE}"}, None), keys, r"<title>([^<]*)</title>")
    for name, route, series in EIA_SERIES:
        _record(f"eia_{name}.json", lambda r=route, s=series: fetcher("GET", EIA_URL.format(route=r), {
            "api_key": keys.eia, "frequency": "weekly", "data[0]": "value", "facets[series][]": s,
            "sort[0][column]": "period", "sort[0][direction]": "desc", "length": 60,
        }, None), keys, r'"period":"(\d{4}-\d\d-\d\d)"')
    _record("fed_press_monetary.xml", lambda: fetcher("GET", FED_RSS_URL, None, None), keys, r"<pubDate>([^<]*)</pubDate>")
    for page in FED_PAGES:
        _record(f"fed_{page.replace('.htm', '')}.html", lambda p=page: fetcher("GET", FED_PAGE_URL.format(name=p), None, None),
                keys, r"(target range)")
    for sec_type in ("Note", "Bond"):
        _record(f"treasury_{sec_type.lower()}.json", lambda t=sec_type: fetcher("GET", TREASURY_URL, {
            "format": "json", "type": t, "days": 120,     # fixture size; the adapter default is 400
        }, None), keys, r'"competitiveAuctionCloseDate":"(\d{4}-\d\d-\d\d)')
    _record("fred_ICSA.json", lambda: fetcher("GET", FRED_URL, {
        "series_id": "ICSA", "api_key": keys.fred, "file_type": "json", "observation_start": f"{year - 1}-01-01",
    }, None), keys, r'"date":"(\d{4}-\d\d-\d\d)"')


# ---- Census code resolution (recorded fixtures + DB mode=ro; FRED GETs only with --env-file) ----

# title -> (program, scale Census units -> FF units, FRED twin, twin transform). A twin of None = none known.
CENSUS_TITLES: dict[str, tuple[str, float, Optional[str], str]] = {
    "Retail Sales m/m": ("marts", 1.0, "RSAFS", "pch"),
    "Core Retail Sales m/m": ("marts", 1.0, "RSFSXMV", "pch"),
    "Durable Goods Orders m/m": ("advm3", 1.0, "DGORDER", "pch"),
    "Core Durable Goods Orders m/m": ("advm3", 1.0, "ADXTNO", "pch"),
    "Housing Starts": ("resconst", 0.001, "HOUST", "lin"),
    "Building Permits": ("resconst", 0.001, "PERMIT", "lin"),
    "New Home Sales": ("ressales", 1.0, "HSN1F", "lin"),
    "Construction Spending m/m": ("vip", 1.0, "TTLCONS", "pch"),
    "Business Inventories m/m": ("mtis", 1.0, "BUSINV", "pch"),
    "Final Wholesale Inventories m/m": ("mwts", 1.0, "WHLSLRIMSA", "pch"),
    "Prelim Wholesale Inventories m/m": ("mwtsadv", 1.0, None, "pch"),
    "Goods Trade Balance": ("ftdadv", 0.001, None, "lin"),
    "Trade Balance": ("ftd", 0.001, "BOPGSTB", "lin"),
    "Factory Orders m/m": ("m3", 1.0, "AMTMNO", "pch"),
}
IDENTITY_PERIODS = 6


def _fmt_like(value: float, template: str) -> Optional[str]:
    """`value` with the template's decimals and K/M/B/% suffix; a value rounding to zero carries no minus sign."""
    m = re.fullmatch(r"-?[\d,]*\.?(\d*)([%KMB]?)", template.strip())
    if not m:
        return None
    text = f"{value:.{len(m.group(1))}f}"
    if float(text) == 0.0:
        text = text.lstrip("-")
    return text + m.group(2)


def _months_back(period: dt.date, n: int) -> dt.date:
    for _ in range(n):
        period = (period - dt.timedelta(days=1)).replace(day=1)
    return period


def _ff_equality_codes(data: dict, rows: list[tuple[str, Optional[str], Optional[str]]], scale: float) -> list[str]:
    """Codes whose value equals the LATEST row's stored actual (else its previous), the release
    covering the month 1 or 2 months before the release month."""
    for event_time, actual, previous in rows:
        if not (actual or previous):
            continue
        release_month = dt.date.fromisoformat(event_time[:10]).replace(day=1)
        hits = []
        for code, series in data.items():
            for lag in (1, 2):
                period = _months_back(release_month, lag)
                ref, ref_period = (actual, period) if actual else (previous, _months_back(period, 1))
                if ref_period in series and _fmt_like(series[ref_period] * scale, ref) == ref.strip():
                    hits.append(f"{code[0]}:{code[1]} (lag {lag})")
        return sorted(set(hits))
    return []


def _identity_codes(data: dict, twin: dict[dt.date, float], transform: str) -> list[str]:
    """Codes equal to the FRED twin's current values over the last IDENTITY_PERIODS twin periods."""
    last = sorted(twin)[-IDENTITY_PERIODS:]
    hits = []
    for code, series in data.items():
        if not last or any(p not in series for p in last):
            continue
        if transform == "lin":
            same = all(abs(series[p] - twin[p]) <= 0.5 for p in last)          # integer-rounded levels
        else:
            same = all(abs(series[p] - twin[p]) <= 0.05 + 1e-9 for p in last)  # Census prints 1 decimal
        if same:
            hits.append(f"{code[0]}:{code[1]}")
    return sorted(hits)


def resolve_census(db_path: Path, keys: Optional[Keys], fetcher: Optional[Fetcher]) -> None:
    from data_layer.fred_history import transform_at
    from data_layer.official_actuals.census import parse_eits
    from data_layer.official_actuals.fred_current import fetch_fred_current

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    cache: dict[str, dict] = {}
    for title, (program, scale, twin_id, transform) in CENSUS_TITLES.items():
        if program not in cache:
            cache[program] = parse_eits((FIXTURE_DIR / f"census_{program}.json").read_text(encoding="utf-8"), program)
        data = cache[program]
        rows = conn.execute(
            "SELECT event_time_utc, actual, previous FROM event_history WHERE event_title = ? AND country = 'USD' "
            "ORDER BY event_time_utc DESC LIMIT 3", (title,)).fetchall()
        ff_hits = _ff_equality_codes(data, rows, scale)
        identity_hits: list[str] = []
        if twin_id and keys is not None and fetcher is not None and keys.fred:
            try:
                levels = sorted(fetch_fred_current(twin_id, keys.fred, fetcher, dt.date(dt.date.today().year - 1, 1, 1)).items())
                twin = {d: v for d, v in ((d, transform_at(levels, d, transform)) for d, _ in levels) if v is not None}
                identity_hits = _identity_codes(data, twin, transform)
            except SourceError as exc:
                identity_hits = [f"FRED {type(exc).__name__}"]
        # m/m percentages match FF by chance for many codes, so a twin identity decides; FF equality
        # alone resolves only when it names exactly one code.
        ff_codes = sorted({h.split(" ")[0] for h in ff_hits})
        if len(identity_hits) == 1 and not identity_hits[0].startswith("FRED "):
            verdict = f"RESOLVED {identity_hits[0]}" + (" (FF-equal too)" if identity_hits[0] in ff_codes else "")
        elif not identity_hits and len(ff_codes) == 1:
            verdict = f"RESOLVED {ff_codes[0]} (FF-equal only)"
        else:
            verdict = "UNRESOLVED"
        print(f"{title:34s} {program:8s} {verdict}\n    FF-equal: {', '.join(ff_hits[:6]) or '-'}  |  "
              f"{twin_id or 'no twin'} identity: {', '.join(identity_hits) or '-'}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, help="the .env holding BLS/BEA/CENSUS/EIA/FRED keys")
    parser.add_argument("--resolve-census", type=Path, metavar="DB", help="resolve Census codes against this DB (read-only)")
    args = parser.parse_args(argv)
    if args.resolve_census:
        if not args.resolve_census.is_file():
            print("DB not found")
            return 2
        keys = load_keys(args.env_file) if args.env_file else None
        resolve_census(args.resolve_census, keys, requests_fetcher() if keys else None)
        return 0
    keys = load_keys(args.env_file)
    record_all(requests_fetcher(), keys)
    return 0


if __name__ == "__main__":
    sys.exit(main())
