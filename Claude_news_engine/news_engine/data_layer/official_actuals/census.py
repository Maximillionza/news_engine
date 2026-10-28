"""
Census Bureau economic indicators (EITS time series API) adapter (ACT Task 1).

GET https://api.census.gov/data/timeseries/eits/<program> with
`get=cell_value,data_type_code,category_code,seasonally_adj,time_slot_id,geo_level_code`,
`time=from YYYY-MM` and `key`. Programs `advm3` and `m3` reject a query
without `for=us:*` (HTTP 400 "missing 'for' argument", seen live 2026-10-28),
so those two always carry it.

Kept: seasonally adjusted rows (`seasonally_adj == "yes"`) at US level only
(`resconst` and `ressales` also carry Northeast/Midwest/South/West rows).
Result: {(category_code, data_type_code): {first-of-month date: value}}.
Suppressed cells ("(S)", "(NA)", "") are skipped, never zero-filled.

Without a (valid, activated) key every program answers HTTP 200 with an HTML
page titled "Missing Key" / "Invalid Key": that raises KeyInactiveError so the
poller can report the reason instead of treating it as "not yet published".

Codes resolved 2026-10-28 (scripts/record_official_fixtures.py --resolve-census:
equal to the FRED twin's current values over the last 6 periods, and "+FF" =
also equal to the latest stored FF actual/previous in the live DB):
    Retail Sales m/m                 marts    44X72:MPCSM     +FF
    Core Retail Sales m/m            marts    44Y72:MPCSM     +FF
    Durable Goods Orders m/m         advm3    MDM:MPCNO       (FF previous 0.0% since revised to 0.1)
    Core Durable Goods Orders m/m    advm3    DXT:MPCNO       +FF
    Housing Starts                   resconst ASTARTS:TOTAL   +FF (SA annual rate; plain STARTS has no SA rows)
    Building Permits                 resconst APERMITS:TOTAL  +FF
    New Home Sales                   ressales ASOLD:TOTAL     (FF previous 684K since revised to 680)
    Construction Spending m/m        vip      XXXX:MPCT       +FF
    Business Inventories m/m         mtis     TOTBUS:MPCIM    +FF
    Trade Balance                    ftd      BOPGS:BAL       +FF
    Factory Orders m/m               m3       MTM:MPCNO       +FF
Unresolved (left out of the registry; never guess a code):
    Final Wholesale Inventories m/m  mwts 42:MPCIM matches neither the stored FF values nor
                                     FRED WHLSLRIMSA (which equals mtis WHLSLR:IM instead)
    Prelim Wholesale Inventories m/m mwtsadv 42:MPCIM: no FF match, no FRED twin
    Goods Trade Balance              ftdadv CBG:BAL: no FF match (-132.1B vs stored -132.6B), no twin
"""
from __future__ import annotations

import datetime as dt
import json
import re
from typing import Optional

from data_layer.official_actuals.http import Fetcher, KeyInactiveError, SourceError, call

CENSUS_URL = "https://api.census.gov/data/timeseries/eits/{program}"
CENSUS_GET = "cell_value,data_type_code,category_code,seasonally_adj,time_slot_id,geo_level_code"
# Programs whose endpoint requires a geography clause.
CENSUS_PROGRAMS_NEEDING_FOR = frozenset({"advm3", "m3"})

_HTML_TITLE = re.compile(r"<title>\s*([^<]*?)\s*</title>", re.I)
_KEY_PAGE_TITLES = ("missing key", "invalid key")


def _period(text: str) -> Optional[dt.date]:
    m = re.fullmatch(r"(\d{4})-(\d{2})", text.strip())
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), 1)
    except ValueError:
        return None


def parse_eits(body: str, program: str) -> dict[tuple[str, str], dict[dt.date, float]]:
    """Parse one EITS JSON answer; SA, US-level rows only."""
    stripped = body.lstrip()
    if not stripped:
        return {}                               # Census answers 204/empty when nothing matches
    if stripped.startswith("<"):
        m = _HTML_TITLE.search(stripped)
        title = (m.group(1) if m else "").lower()
        if any(t in title for t in _KEY_PAGE_TITLES):
            raise KeyInactiveError(f"census: key missing or not active ({program})")
        raise SourceError(f"census: HTML instead of JSON ({program})")
    try:
        rows = json.loads(stripped)
        header = rows[0]
        idx = {name: header.index(name) for name in
               ("cell_value", "data_type_code", "category_code", "seasonally_adj", "geo_level_code", "time")}
    except (ValueError, TypeError, IndexError, KeyError):
        raise SourceError(f"census: unparseable body ({program})") from None
    out: dict[tuple[str, str], dict[dt.date, float]] = {}
    for row in rows[1:]:
        try:
            if row[idx["seasonally_adj"]] != "yes" or row[idx["geo_level_code"]] != "US":
                continue
            period = _period(row[idx["time"]])
            value = float(str(row[idx["cell_value"]]).replace(",", ""))
        except (TypeError, ValueError, IndexError):
            continue
        if period is None:
            continue
        out.setdefault((row[idx["category_code"]], row[idx["data_type_code"]]), {})[period] = value
    return out


def fetch_eits(program: str, key: str, fetcher: Fetcher, since: dt.date) -> dict[tuple[str, str], dict[dt.date, float]]:
    """All SA, US-level series of `program` from the month of `since` on."""
    if not key:
        raise KeyInactiveError("census: no key configured")
    params = {"get": CENSUS_GET, "time": f"from {since:%Y-%m}", "key": key}
    if program in CENSUS_PROGRAMS_NEEDING_FOR:
        params["for"] = "us:*"
    resp = call(fetcher, "census", "GET", CENSUS_URL.format(program=program), params)
    if resp.status == 204:
        return {}
    return parse_eits(resp.text, program)
