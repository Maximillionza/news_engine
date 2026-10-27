"""
ALFRED release-day vintage reader (B8 U4, 2026-10-27).

For a Forex Factory event title mapped to a FRED series, reads the value AS
PUBLISHED on release day (an ALFRED vintage: realtime_start = realtime_end =
the first-print date), never FRED's latest revised number. That first print
is what the market reacted to, so it is what a surprise must be measured
against. FRED has no consensus forecasts: readings carry actual + previous
only.

READ-ONLY and side-effect free apart from HTTP GETs to api.stlouisfed.org.
Unlike the fail-open data_layer modules (fred_actuals) this one RAISES
(FredMaintenanceError / FredFetchError): its callers (seed script, hourly
backfill) must be able to tell "FRED is down" from "nothing to write" and
abort a run rather than write half a picture. The API key is never printed
or placed in an error message.

Headline definitions, computed inside the release-day vintage exactly as the
statistical agencies publish them: NFP/ADP = level change vs the prior month's
level in that vintage (so the prior month's revision is already in `previous`),
CPI/PPI/Retail m/m = percent change vs the prior month's level, y/y (pc1) vs
the same month a year earlier.
"""
from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from typing import Callable, Optional

import requests

from data_layer.calendar_feed import _parse_numeric, tick_of
from data_layer.fred_calendar_feed import is_maintenance_page

FRED_BASE_URL = "https://api.stlouisfed.org/fred"
_REQUEST_TIMEOUT_SECONDS = 20
# Levels fetched before the release period so the prior month and the
# 12-month-ago point (y/y) are always inside the vintage window.
_OBSERVATION_LOOKBACK_DAYS = 400


class FredMaintenanceError(RuntimeError):
    """FRED served its HTML maintenance page (HTTP 200) instead of JSON."""


class FredFetchError(RuntimeError):
    """Any other FRED failure: HTTP error, network error, unparseable body."""


class FredTransportError(FredFetchError):
    """The request never got an HTTP answer (timeout, connection error). FRED as a
    whole is unreachable, so a multi-title pass should stop rather than wait out
    the timeout once per title."""


@dataclass(frozen=True)
class FredSeriesSpec:
    series_id: str
    transform: str                     # "pch" | "pc1" | "chg" | "lin"
    fmt: str                           # "pct1" | "k0" | "m2" | "b1" | "num1"
    scale: float = 1.0                 # multiplies the FRED value before formatting
    frequency: str = "monthly"         # "monthly" | "weekly"
    seed: bool = False                 # U1 High-impact seed title
    release_time_et: Optional[dt.time] = None  # New York release time; required when seed


_ET_0830 = dt.time(8, 30)

# Exact FF titles -> FRED series. A title dropped here is never read or written.
FRED_HISTORY_SPECS: dict[str, FredSeriesSpec] = {
    "Non-Farm Employment Change": FredSeriesSpec("PAYEMS", "chg", "k0", 1.0, seed=True, release_time_et=_ET_0830),
    "Unemployment Rate": FredSeriesSpec("UNRATE", "lin", "pct1", seed=True, release_time_et=_ET_0830),
    "Average Hourly Earnings m/m": FredSeriesSpec("CES0500000003", "pch", "pct1", seed=True, release_time_et=_ET_0830),
    "CPI m/m": FredSeriesSpec("CPIAUCSL", "pch", "pct1", seed=True, release_time_et=_ET_0830),
    "CPI y/y": FredSeriesSpec("CPIAUCSL", "pc1", "pct1", seed=True, release_time_et=_ET_0830),
    "Core CPI m/m": FredSeriesSpec("CPILFESL", "pch", "pct1", seed=True, release_time_et=_ET_0830),
    "Core CPI y/y": FredSeriesSpec("CPILFESL", "pc1", "pct1", seed=True, release_time_et=_ET_0830),
    "PPI m/m": FredSeriesSpec("PPIFIS", "pch", "pct1", seed=True, release_time_et=_ET_0830),
    "Core PPI m/m": FredSeriesSpec("PPIFES", "pch", "pct1", seed=True, release_time_et=_ET_0830),
    "Retail Sales m/m": FredSeriesSpec("RSAFS", "pch", "pct1", seed=True, release_time_et=_ET_0830),
    "Core Retail Sales m/m": FredSeriesSpec("RSFSXMV", "pch", "pct1", seed=True, release_time_et=_ET_0830),
    "Core PCE Price Index m/m": FredSeriesSpec("PCEPILFE", "pch", "pct1", seed=True, release_time_et=_ET_0830),
    "Import Prices m/m": FredSeriesSpec("IR", "pch", "pct1", seed=True, release_time_et=_ET_0830),
    "Unemployment Claims": FredSeriesSpec("ICSA", "lin", "k0", 0.001, frequency="weekly", seed=True, release_time_et=_ET_0830),
    "ADP Non-Farm Employment Change": FredSeriesSpec("ADPMNUSNERSA", "chg", "k0", 0.001, seed=True, release_time_et=dt.time(8, 15)),
    # Medium/Low titles: kept filled by the hourly backfill, never seeded.
    "JOLTS Job Openings": FredSeriesSpec("JTSJOL", "lin", "m2", 0.001),
    "Industrial Production m/m": FredSeriesSpec("INDPRO", "pch", "pct1"),
    "Capacity Utilization Rate": FredSeriesSpec("TCU", "lin", "pct1"),
    "Housing Starts": FredSeriesSpec("HOUST", "lin", "m2", 0.001),
    "Building Permits": FredSeriesSpec("PERMIT", "lin", "m2", 0.001),
    "Durable Goods Orders m/m": FredSeriesSpec("DGORDER", "pch", "pct1"),
    "Core Durable Goods Orders m/m": FredSeriesSpec("ADXTNO", "pch", "pct1"),
    "Factory Orders m/m": FredSeriesSpec("AMTMNO", "pch", "pct1"),
    "Personal Income m/m": FredSeriesSpec("PI", "pch", "pct1"),
    "Personal Spending m/m": FredSeriesSpec("PCE", "pch", "pct1"),
    "Business Inventories m/m": FredSeriesSpec("BUSINV", "pch", "pct1"),
    "Final Wholesale Inventories m/m": FredSeriesSpec("WHLSLRIMSA", "pch", "pct1"),
    "Construction Spending m/m": FredSeriesSpec("TTLCONS", "pch", "pct1"),
    "New Home Sales": FredSeriesSpec("HSN1F", "lin", "k0", 1.0),
    "Existing Home Sales": FredSeriesSpec("EXHOSLUSM495S", "lin", "m2", 1e-6),
    "Trade Balance": FredSeriesSpec("BOPGSTB", "lin", "b1", 0.001),
    "Federal Budget Balance": FredSeriesSpec("MTSDS133FMS", "lin", "b1", 0.001),
    "Consumer Credit m/m": FredSeriesSpec("TOTALSL", "chg", "b1", 1.0),
    "HPI m/m": FredSeriesSpec("HPIPONM226S", "pch", "pct1"),
    "S&P/CS Composite-20 HPI y/y": FredSeriesSpec("SPCS20RNSA", "pc1", "pct1"),
    "Philly Fed Manufacturing Index": FredSeriesSpec("GACDFSA066MSFRBPHI", "lin", "num1"),
    "Empire State Manufacturing Index": FredSeriesSpec("GACDINA066MSFRBNY", "lin", "num1"),
}


@dataclass(frozen=True)
class InitialRelease:
    period: dt.date          # the reference period (FRED `date`)
    vintage_date: dt.date    # the day it was first published (realtime_start)


@dataclass(frozen=True)
class VintageReading:
    title: str
    period: dt.date
    vintage_date: dt.date
    actual: str                              # first print, formatted like FF
    previous: Optional[str]                  # prior period as published in the same vintage
    previous_first_print: Optional[str]      # prior period's own first print


class FredClient:
    """Small caching ALFRED client. Pace between requests is the caller's choice."""

    def __init__(self, api_key: str, pace_seconds: float = 0.0, sleep: Callable[[float], None] = time.sleep) -> None:
        self._api_key = api_key
        self._pace_seconds = pace_seconds
        self._sleep = sleep
        self._initial_cache: dict[tuple[str, dt.date, dt.date], list[InitialRelease]] = {}
        self._vintage_cache: dict[tuple[str, dt.date, dt.date], list[tuple[dt.date, float]]] = {}

    def _get_observations(self, params: dict) -> list[dict]:
        if self._pace_seconds > 0:
            self._sleep(self._pace_seconds)
        full = {**params, "api_key": self._api_key, "file_type": "json"}
        try:
            resp = requests.get(f"{FRED_BASE_URL}/series/observations", params=full, timeout=_REQUEST_TIMEOUT_SECONDS)
        except Exception as exc:  # noqa: BLE001 — message carries only the class name: a requests error embeds the URL (and key)
            raise FredTransportError(f"FRED request failed for {params.get('series_id')}: {type(exc).__name__}") from None
        # Maintenance HTML arrives as HTTP 200, so test for it BEFORE the status check.
        if is_maintenance_page(getattr(resp, "text", "")):
            raise FredMaintenanceError("FRED is under maintenance")
        try:
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise FredFetchError(f"FRED HTTP error for {params.get('series_id')}: {type(exc).__name__}") from None
        try:
            return list(resp.json().get("observations", []))
        except Exception as exc:  # noqa: BLE001
            raise FredFetchError(f"FRED returned an unparseable body for {params.get('series_id')}") from None

    def initial_releases(self, series_id: str, start: dt.date, end: dt.date) -> list[InitialRelease]:
        """First prints whose release (vintage) date falls in [start, end], ascending by vintage."""
        key = (series_id, start, end)
        if key not in self._initial_cache:
            obs = self._get_observations({
                "series_id": series_id, "output_type": 4,
                "realtime_start": start.isoformat(), "realtime_end": end.isoformat(),
            })
            out: list[InitialRelease] = []
            for o in obs:
                try:
                    out.append(InitialRelease(dt.date.fromisoformat(o["date"]), dt.date.fromisoformat(o["realtime_start"])))
                except (KeyError, TypeError, ValueError):
                    continue
            out.sort(key=lambda r: (r.vintage_date, r.period))
            self._initial_cache[key] = out
        return self._initial_cache[key]

    def vintage_levels(self, series_id: str, vintage_date: dt.date, observation_start: dt.date) -> list[tuple[dt.date, float]]:
        """Levels as they stood on `vintage_date` (ascending); FRED's "." gaps skipped."""
        key = (series_id, vintage_date, observation_start)
        if key not in self._vintage_cache:
            obs = self._get_observations({
                "series_id": series_id, "units": "lin",
                "realtime_start": vintage_date.isoformat(), "realtime_end": vintage_date.isoformat(),
                "observation_start": observation_start.isoformat(),
            })
            levels: list[tuple[dt.date, float]] = []
            for o in obs:
                try:
                    if o["value"] in (None, "."):
                        continue
                    levels.append((dt.date.fromisoformat(o["date"]), float(o["value"])))
                except (KeyError, TypeError, ValueError):
                    continue
            levels.sort()
            self._vintage_cache[key] = levels
        return self._vintage_cache[key]


def _same_month_prior_year(period: dt.date) -> dt.date:
    return period.replace(year=period.year - 1)


def transform_at(levels: list[tuple[dt.date, float]], period: dt.date, transform: str) -> Optional[float]:
    """The transformed value for `period` inside one vintage's levels; None if a needed point is missing."""
    by_date = dict(levels)
    if period not in by_date:
        return None
    current = by_date[period]
    if transform == "lin":
        return current
    if transform == "pc1":
        base = by_date.get(_same_month_prior_year(period))
        return None if not base else (current / base - 1.0) * 100.0
    earlier = [d for d, _ in levels if d < period]
    if not earlier:
        return None
    prev = by_date[max(earlier)]
    if transform == "chg":
        return current - prev
    if transform == "pch":
        return None if not prev else (current / prev - 1.0) * 100.0
    raise ValueError(f"unknown transform {transform!r}")


def format_value(value: float, spec: FredSeriesSpec) -> str:
    """Scale then format like Forex Factory prints it; a value that rounds to zero carries no minus sign."""
    v = value * spec.scale
    if spec.fmt == "pct1":
        text, suffix, digits = f"{v:.1f}", "%", 1
    elif spec.fmt == "k0":
        text, suffix, digits = f"{v:.0f}", "K", 0
    elif spec.fmt == "m2":
        text, suffix, digits = f"{v:.2f}", "M", 2
    elif spec.fmt == "b1":
        text, suffix, digits = f"{v:.1f}", "B", 1
    elif spec.fmt == "num1":
        text, suffix, digits = f"{v:.1f}", "", 1
    else:
        raise ValueError(f"unknown format {spec.fmt!r}")
    if float(text) == 0.0:
        text = f"{0.0:.{digits}f}"
    return text + suffix


def _spec_for(title: str) -> Optional[FredSeriesSpec]:
    return FRED_HISTORY_SPECS.get(title)


def reading_for_release(
    client: FredClient, title: str, release: InitialRelease, prior: Optional[InitialRelease]
) -> Optional[VintageReading]:
    """
    The release-day reading for one first print, or None for an unmapped
    title / a vintage that lacks the needed points. `previous` is the prior
    period inside the SAME vintage (revised as of that day);
    `previous_first_print` is that prior period's own first print, taken from
    its release's vintage (a cache hit when releases are walked in order).
    """
    spec = _spec_for(title)
    if spec is None:
        return None
    obs_start = release.period - dt.timedelta(days=_OBSERVATION_LOOKBACK_DAYS)
    levels = client.vintage_levels(spec.series_id, release.vintage_date, obs_start)
    value = transform_at(levels, release.period, spec.transform)
    if value is None:
        return None
    earlier = [d for d, _ in levels if d < release.period]
    prev_period = max(earlier) if earlier else None
    previous = None
    if prev_period is not None:
        pv = transform_at(levels, prev_period, spec.transform)
        previous = format_value(pv, spec) if pv is not None else None
    first_print = None
    if prior is not None and prior.period == prev_period:
        p_levels = client.vintage_levels(spec.series_id, prior.vintage_date, prior.period - dt.timedelta(days=_OBSERVATION_LOOKBACK_DAYS))
        fv = transform_at(p_levels, prior.period, spec.transform)
        first_print = format_value(fv, spec) if fv is not None else None
    return VintageReading(
        title=title, period=release.period, vintage_date=release.vintage_date,
        actual=format_value(value, spec), previous=previous, previous_first_print=first_print,
    )


def releases_between(client: FredClient, title: str, start: dt.date, end: dt.date) -> list[VintageReading]:
    """Readings for every first print released in [start, end], ascending by release date."""
    spec = _spec_for(title)
    if spec is None:
        return []
    # Reach back one cycle so the first release in range still has its prior release.
    reach = 14 if spec.frequency == "weekly" else 60
    releases = client.initial_releases(spec.series_id, start - dt.timedelta(days=reach), end)
    out: list[VintageReading] = []
    prior: Optional[InitialRelease] = None
    for rel in releases:
        if start <= rel.vintage_date <= end:
            reading = reading_for_release(client, title, rel, prior)
            if reading is not None:
                out.append(reading)
        prior = rel
    return out


def reading_for_event_date(
    client: FredClient, title: str, event_date: dt.date, max_lag_days: int = 3
) -> Optional[VintageReading]:
    """The release whose vintage date is in [event_date, event_date + max_lag_days], else None."""
    found = releases_between(client, title, event_date, event_date + dt.timedelta(days=max_lag_days))
    return found[0] if found else None


def values_match(stored: Optional[str], candidate: Optional[str]) -> bool:
    """Both parse and differ by at most half of the stored value's rounding step."""
    a, b, tick = _parse_numeric(stored), _parse_numeric(candidate), tick_of(stored)
    if a is None or b is None or tick is None:
        return False
    return abs(a - b) <= tick / 2.0 + 1e-9


def actual_check(reading: VintageReading, row_actual: Optional[str]) -> str:
    """"match" | "mismatch" | "no_reference" for the stored first-print actual."""
    if _parse_numeric(row_actual) is None:
        return "no_reference"
    return "match" if values_match(row_actual, reading.actual) else "mismatch"


def previous_check(reading: VintageReading, row_previous: Optional[str]) -> str:
    """Stored `previous` matches either the revised prior or the prior's first print."""
    if _parse_numeric(row_previous) is None:
        return "no_reference"
    for candidate in (reading.previous, reading.previous_first_print):
        if candidate is not None and values_match(row_previous, candidate):
            return "match"
    return "mismatch"
