"""
Bureau of Labor Statistics adapter (public API v2) (ACT Task 1).

One POST per 50 series (the v2 per-query limit) with `calculations: true`,
so BLS itself returns the 1- and 12-month percent changes it publishes
(`pct_changes["1"]`, `["12"]`): CPI/PPI m/m and y/y are then exactly the
published figures, not a recomputation from rounded index levels.

Periods: M01..M12 -> first of that month; Q01..Q04 -> first month of the
quarter (Q02 -> April). M13 / Q05 (annual averages) and "-" values (not
available) are skipped. Footnote code "R" ("revised") marks a value the
latest release changed; those periods are kept in `revised`, the proof that a
re-estimate (Revised Productivity) is out. A daily-quota message raises
SourceRateLimited, an invalid key KeyInactiveError, any other refusal
SourceError.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from typing import Optional, Sequence

from data_layer.official_actuals.http import Fetcher, KeyInactiveError, SourceError, SourceRateLimited, call

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_MAX_SERIES_PER_QUERY = 50


@dataclass(frozen=True)
class BlsSeries:
    levels: dict[dt.date, float] = field(default_factory=dict)
    pct1: dict[dt.date, float] = field(default_factory=dict)
    pct12: dict[dt.date, float] = field(default_factory=dict)
    revised: set[dt.date] = field(default_factory=set)        # periods footnoted "R" (revised)


def _period(year: str, period: str) -> Optional[dt.date]:
    try:
        y, kind, n = int(year), period[:1], int(period[1:])
    except (TypeError, ValueError):
        return None
    if kind == "M" and 1 <= n <= 12:
        return dt.date(y, n, 1)
    if kind == "Q" and 1 <= n <= 4:
        return dt.date(y, 3 * (n - 1) + 1, 1)
    return None


def _number(text: object) -> Optional[float]:
    try:
        return float(str(text).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _raise_for_refusal(payload: dict) -> None:
    status = payload.get("status")
    if status == "REQUEST_SUCCEEDED":
        return
    messages = " ".join(str(m) for m in (payload.get("message") or [])).lower()
    if "threshold" in messages:
        raise SourceRateLimited("bls: daily request threshold reached")
    if "key" in messages and ("invalid" in messages or "not valid" in messages or "inactive" in messages):
        raise KeyInactiveError("bls: registration key rejected")
    raise SourceError(f"bls: request not processed ({status or 'no status'})")


def parse_bls(body: str) -> dict[str, BlsSeries]:
    """Parse one v2 answer into {series id: BlsSeries}."""
    try:
        payload = json.loads(body)
    except ValueError:
        raise SourceError("bls: unparseable body") from None
    if not isinstance(payload, dict):
        raise SourceError("bls: unparseable body")
    _raise_for_refusal(payload)
    out: dict[str, BlsSeries] = {}
    for series in (payload.get("Results") or {}).get("series") or []:
        parsed = BlsSeries()
        for point in series.get("data") or []:
            period = _period(point.get("year"), str(point.get("period", "")))
            if period is None:
                continue
            level = _number(point.get("value"))
            if level is not None:
                parsed.levels[period] = level
            pct = (point.get("calculations") or {}).get("pct_changes") or {}
            for months, target in (("1", parsed.pct1), ("12", parsed.pct12)):
                value = _number(pct.get(months))
                if value is not None:
                    target[period] = value
            if any(isinstance(f, dict) and str(f.get("code", "")).upper() == "R" for f in point.get("footnotes") or []):
                parsed.revised.add(period)
        out[str(series.get("seriesID"))] = parsed
    return out


def fetch_bls(series_ids: Sequence[str], key: str, fetcher: Fetcher, start_year: int, end_year: int) -> dict[str, BlsSeries]:
    """Levels and BLS-computed 1/12-month percent changes for every id, 50 ids per POST."""
    if not key:
        # Unregistered (v1-level) access silently drops `calculations`: m/m and y/y would never appear.
        raise KeyInactiveError("bls: no key configured")
    ids = list(dict.fromkeys(series_ids))
    out: dict[str, BlsSeries] = {}
    for i in range(0, len(ids), BLS_MAX_SERIES_PER_QUERY):
        body = {
            "seriesid": ids[i:i + BLS_MAX_SERIES_PER_QUERY],
            "startyear": str(start_year), "endyear": str(end_year),
            "calculations": True, "registrationkey": key,
        }
        resp = call(fetcher, "bls", "POST", BLS_URL, None, body)
        out.update(parse_bls(resp.text))
    return out
