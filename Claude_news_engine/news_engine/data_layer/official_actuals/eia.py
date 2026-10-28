"""
Energy Information Administration API v2 adapter, weekly series (ACT Task 1).

GET https://api.eia.gov/v2/<route>/data/ with api_key, frequency=weekly,
data[0]=value, facets[series][]=<id>, sorted by period descending.
Result: {week-ending date: level} in the series' own units (crude stocks in
thousand barrels, natural-gas storage in Bcf); the weekly change FF prints
is computed later by the registry transform.

An invalid or missing key comes back as HTTP 403 with
`{"error": {"code": "API_KEY_INVALID" | "API_KEY_MISSING"}}`: that body is read
before the status check so it raises KeyInactiveError, not a plain 4xx.
"""
from __future__ import annotations

import datetime as dt
import json

from data_layer.official_actuals.http import Fetcher, KeyInactiveError, SourceError, call, check_status

EIA_URL = "https://api.eia.gov/v2/{route}/data/"


def _key_error(text: str) -> bool:
    try:
        payload = json.loads(text)
    except ValueError:
        return False
    err = payload.get("error") if isinstance(payload, dict) else None
    code = str(err.get("code", "")) if isinstance(err, dict) else str(err or "")
    return code.upper().startswith("API_KEY")


def parse_eia_weekly(body: str) -> dict[dt.date, float]:
    try:
        payload = json.loads(body)
        rows = payload["response"]["data"]
    except (ValueError, KeyError, TypeError):
        raise SourceError("eia: unparseable body") from None
    out: dict[dt.date, float] = {}
    for row in rows or []:
        try:
            out[dt.date.fromisoformat(str(row["period"])[:10])] = float(row["value"])
        except (KeyError, TypeError, ValueError):
            continue                                  # null value = not published
    return out


def fetch_eia_weekly(route: str, series_id: str, key: str, fetcher: Fetcher, length: int = 60) -> dict[dt.date, float]:
    """The latest `length` weekly points of one series."""
    if not key:
        raise KeyInactiveError("eia: no key configured")
    params = {
        "api_key": key, "frequency": "weekly", "data[0]": "value", "facets[series][]": series_id,
        "sort[0][column]": "period", "sort[0][direction]": "desc", "length": length,
    }
    resp = call(fetcher, "eia", "GET", EIA_URL.format(route=route.strip("/")), params, check=False)
    if resp.status >= 400 and _key_error(resp.text):
        raise KeyInactiveError("eia: api key rejected")
    check_status(resp, "eia")
    return parse_eia_weekly(resp.text)
