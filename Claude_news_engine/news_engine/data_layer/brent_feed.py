"""
Daily Brent crude (FRED series DCOILBRENTEU, EIA daily Brent, USD/bbl) for the Stats tab's information-only
"Brent crude" line next to the Cleveland Fed nowcast. It carries 0% weight: Brent is already an input to the
nowcast, so it is shown, never scored.

READ-ONLY, same fail-open contract as data_layer/macro_backdrop.py and the same request pattern (FRED
/series/observations with the FRED_API_KEY from config.settings, requests.get, 15 s timeout or less): a
missing key, an HTTP error, a network error or bad data returns None. It never raises and never invents a
value. FRED marks a day without a price with the literal "." (holidays, not-yet-published days); those are
skipped.

Pure helpers: parse_observations() and brent_on_or_before(). IO: get_brent_series(), with a 6-hour in-process
cache. The HTTP getter, the API key and the clock are injectable so tests never touch the network.
"""
from __future__ import annotations

import datetime as dt
import math
import threading
import time
from typing import Callable, Optional

import requests

from config.settings import FRED_API_KEY

FRED_BASE_URL = "https://api.stlouisfed.org/fred"
BRENT_SERIES_ID = "DCOILBRENTEU"
SOURCE_LABEL = "FRED DCOILBRENTEU (EIA daily Brent)"

# The Stats tab's history starts 2026-01-01; start a little earlier so the first snapshots still find a
# prior trading day. FRED returns ascending by default and the whole span is only a few hundred rows.
OBSERVATION_START = "2025-12-01"
REQUEST_TIMEOUT_SECONDS = 10

CACHE_TTL_SECONDS = 6 * 60 * 60     # a fresh series is reused for six hours
FAILURE_RETRY_SECONDS = 5 * 60      # after a failed fetch, wait this long before asking FRED again

Series = list[tuple[dt.date, float]]

# state: the last good series and when it was fetched, plus when a fetch last failed (monotonic seconds)
_cache: dict = {"series": None, "fetched_at": None, "failed_at": None}
# Held across the whole cache check + fetch, so callers that arrive together (the Stats page loads several
# endpoints at once) share ONE request: the first fetches, the rest wait and then read the cache.
_lock = threading.Lock()


def clear_cache() -> None:
    _cache.update(series=None, fetched_at=None, failed_at=None)


def parse_observations(observations) -> Series:
    """
    FRED observation rows -> [(date, price)] ascending by date. Skips FRED's "." marker, missing or
    non-numeric values, non-positive or non-finite prices and malformed rows. Never raises.
    """
    if not isinstance(observations, list):
        return []
    parsed: Series = []
    for row in observations:
        if not isinstance(row, dict):
            continue
        value = row.get("value")
        if value is None or value == ".":
            continue
        try:
            day = dt.date.fromisoformat(str(row.get("date")))
            price = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(price) or price <= 0:
            continue
        parsed.append((day, price))
    parsed.sort(key=lambda item: item[0])
    return parsed


def brent_on_or_before(series: Optional[Series], day) -> Optional[tuple[dt.date, float]]:
    """
    (date, price) of the latest observation dated on or before `day`; None if there is none. Never looks
    at a later observation, so a caller that passes the day before a release cannot see the release day.
    """
    if not series:
        return None
    cutoff = day.date() if isinstance(day, dt.datetime) else day
    best: Optional[tuple[dt.date, float]] = None
    for obs_day, price in series:
        if obs_day <= cutoff and (best is None or obs_day > best[0]):
            best = (obs_day, price)
    return best


def _fetch(api_key: str, http_get: Callable) -> Optional[Series]:
    try:
        resp = http_get(
            f"{FRED_BASE_URL}/series/observations",
            params={"series_id": BRENT_SERIES_ID, "file_type": "json", "api_key": api_key,
                    "observation_start": OBSERVATION_START},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        series = parse_observations(resp.json().get("observations", []))
    except Exception as exc:  # noqa: BLE001 -- a failed fetch must not crash the caller
        # Only the exception type and HTTP status: str(exc) from requests can embed the full URL, api_key included.
        status = getattr(getattr(exc, "response", None), "status_code", None)
        detail = type(exc).__name__ + (f" (HTTP {status})" if status else "")
        print(f"[brent_feed] WARNING: fetch failed for {BRENT_SERIES_ID}: {detail}")
        return None
    return series or None


def get_brent_series(api_key: Optional[str] = None, http_get: Callable = requests.get,
                     clock: Callable[[], float] = time.monotonic) -> Optional[Series]:
    """
    The daily Brent series (ascending), or None when it is unavailable. Cached for CACHE_TTL_SECONDS. If a
    refresh fails, the last good series keeps being served (an old price with its own date is still
    truthful) and FRED is not asked again for FAILURE_RETRY_SECONDS. Returns a copy, so a caller cannot
    alter the cache.
    """
    key = FRED_API_KEY if api_key is None else api_key
    if not key:
        return None
    with _lock:
        now = clock()
        cached = _cache["series"]
        if cached is not None and now - _cache["fetched_at"] < CACHE_TTL_SECONDS:
            return list(cached)
        if _cache["failed_at"] is not None and now - _cache["failed_at"] < FAILURE_RETRY_SECONDS:
            return None if cached is None else list(cached)
        fetched = _fetch(key, http_get)
        if fetched is None:
            _cache["failed_at"] = now
            return None if cached is None else list(cached)
        _cache.update(series=fetched, fetched_at=now, failed_at=None)
        return list(fetched)
