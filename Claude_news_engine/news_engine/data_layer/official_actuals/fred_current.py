"""
FRED current-values reader for the poller (ACT Task 1): weekly jobless
claims (ICSA), because DOL's own machine-readable claims data lags by weeks.

GET https://api.stlouisfed.org/fred/series/observations with series_id,
api_key, file_type=json and observation_start, and no realtime window, which
FRED answers with today's values: the same numbers as
`FredClient(key).vintage_levels(series, today, start)` in
data_layer/fred_history.py, but through the injectable `Fetcher` (FredClient
calls requests directly, so it could not run on recorded fixtures or share
the poller's back-off). FRED's "." gaps are skipped.

Errors follow fred_history's split: no HTTP answer -> SourceTransportError
(FredTransportError there), the HTML maintenance page or any other failure ->
SourceError, and an api_key complaint -> KeyInactiveError.
"""
from __future__ import annotations

import datetime as dt
import json

from data_layer.fred_calendar_feed import is_maintenance_page
from data_layer.official_actuals.http import Fetcher, KeyInactiveError, SourceError, call, check_status

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


def parse_observations(body: str, series_id: str) -> dict[dt.date, float]:
    try:
        observations = json.loads(body)["observations"]
    except (ValueError, KeyError, TypeError):
        raise SourceError(f"fred: unparseable body for {series_id}") from None
    out: dict[dt.date, float] = {}
    for o in observations or []:
        try:
            if o["value"] in (None, "."):
                continue
            out[dt.date.fromisoformat(o["date"])] = float(o["value"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def fetch_fred_current(series_id: str, key: str, fetcher: Fetcher, observation_start: dt.date) -> dict[dt.date, float]:
    """Today's values of one FRED series from `observation_start` on."""
    if not key:
        raise KeyInactiveError("fred: no key configured")
    params = {"series_id": series_id, "api_key": key, "file_type": "json", "observation_start": observation_start.isoformat()}
    resp = call(fetcher, "fred", "GET", FRED_OBSERVATIONS_URL, params, check=False)
    # The maintenance page arrives as HTTP 200, so it is tested before the status check.
    if is_maintenance_page(resp.text):
        raise SourceError("fred: under maintenance")
    if resp.status in (400, 403) and "api_key" in resp.text:
        raise KeyInactiveError("fred: api key rejected")
    check_status(resp, "fred")
    return parse_observations(resp.text, series_id)
