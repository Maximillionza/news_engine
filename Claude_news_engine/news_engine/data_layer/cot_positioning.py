"""
Free, no-token CFTC "Traders in Financial Futures" (TFF) Commitments of
Traders data — data_layer/cot_positioning.py, part of the fundamental
signals batch (docs/superpowers/specs/2026-09-02-fundamental-signals-batch-design.md).

Used for ONE thing only: a confidence-only "is USD positioning already
crowded" dampener in scoring/probability_engine.py's
_check_cot_crowding() — deliberately NEVER a directional lean (see the
spec's Decisions section: explicitly deferred, revisit only if the
dampener-only design proves insufficient).

Data source: CFTC's Socrata Open Data API, publicreporting.cftc.gov,
resource gpe5-46if ("TFF - Futures Only") — real weekly rows for the
USD Index futures contract (cftc_contract_market_code "098662") with
lev_money_positions_long/lev_money_positions_short fields (the
"Leveraged Funds" trader category — the standard "smart money crowding"
read in COT-based fundamental analysis, as opposed to Dealers/Asset
Managers/Other Reportables, which are hedging-driven).

Published weekly (Fridays, covering the prior Tuesday's positions) —
fetched at most once per calendar day via a simple in-process cache,
never re-fetched every scoring cycle.

READ-ONLY, same fail-open contract as every other data_layer module:
returns None on a missing/empty response, a failed request, or any
exception — never raises, never invents a value.

CORRECTION (live-verified 2026-09-02, this task): the plan's original
brainstorm recorded the market_and_exchange_names value as
"U.S. DOLLAR INDEX - ICE FUTURES U.S." — that string is stale. CFTC
renamed it (same cftc_contract_market_code "098662") to
"USD INDEX - ICE FUTURES U.S." starting with the 2022-02-08 report; the
old string returns nothing newer than 2022-02-01. Independently
re-confirmed live twice (once during implementation, once by the
controller) before landing — USD_INDEX_MARKET_NAME below uses the
current, correct name.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import requests

CFTC_TFF_RESOURCE_URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
USD_INDEX_MARKET_NAME = "USD INDEX - ICE FUTURES U.S."

# How far back to look for the trailing percentile window — a standard
# one-year COT lookback. Untuned starting value.
COT_CROWDING_LOOKBACK_WEEKS = 52

# Top/bottom this-many-percent of the trailing window counts as
# "crowded." Untuned starting value, needs revisiting once real backtest
# data exists.
COT_CROWDING_PERCENTILE_THRESHOLD = 15.0


@dataclass
class CotPositioningRead:
    net_leveraged_funds_position: Optional[int]     # contracts, net long(+)/short(-); None if unavailable
    percentile_in_trailing_window: Optional[float]   # 0-100, this reading's rank within the trailing window
    report_date: Optional[dt.date]
    lookback_weeks: int

    @property
    def is_crowded(self) -> Optional[int]:
        """
        +1 = net-long crowding (extreme long positioning), -1 = net-short
        crowding, None = not extreme (within the normal range) or no
        data. "Extreme" = top/bottom COT_CROWDING_PERCENTILE_THRESHOLD of
        the trailing window.
        """
        if self.percentile_in_trailing_window is None or self.net_leveraged_funds_position is None:
            return None
        if self.percentile_in_trailing_window >= (100.0 - COT_CROWDING_PERCENTILE_THRESHOLD):
            return 1
        if self.percentile_in_trailing_window <= COT_CROWDING_PERCENTILE_THRESHOLD:
            return -1
        return None


_cache_date: Optional[dt.date] = None
_cache_read: Optional[CotPositioningRead] = None


def _fetch_rows(limit: int) -> list[dict]:
    resp = requests.get(
        CFTC_TFF_RESOURCE_URL,
        params={
            "$where": f"market_and_exchange_names = '{USD_INDEX_MARKET_NAME}'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": limit,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_cot_positioning_read(now: Optional[dt.datetime] = None) -> Optional[CotPositioningRead]:
    """
    Returns None on any failure, an empty result, or fewer than 2 usable
    rows (can't compute a percentile from one point). Cached per
    calendar day (UTC) — a second call the same day reuses the first
    call's result rather than re-fetching, matching this data's real
    weekly-at-best freshness.
    """
    global _cache_date, _cache_read

    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.date()
    if _cache_date == today:
        return _cache_read

    try:
        rows = _fetch_rows(COT_CROWDING_LOOKBACK_WEEKS)
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the caller
        print(f"[cot_positioning] WARNING: fetch failed: {exc}")
        _cache_date, _cache_read = today, None
        return None

    if not rows:
        _cache_date, _cache_read = today, None
        return None

    try:
        net_positions = []
        for row in rows:
            net_long = float(row.get("lev_money_positions_long", 0) or 0)
            net_short = float(row.get("lev_money_positions_short", 0) or 0)
            net_positions.append(net_long - net_short)

        if len(net_positions) < 2:
            _cache_date, _cache_read = today, None
            return None

        newest_net = net_positions[0]
        # Percentile rank of the newest reading within the whole window
        # (including itself) — what fraction of the window's values are at
        # or below the newest reading.
        at_or_below = sum(1 for v in net_positions if v <= newest_net)
        percentile = at_or_below / len(net_positions) * 100.0

        newest_date = dt.date.fromisoformat(rows[0]["report_date_as_yyyy_mm_dd"].split("T")[0])

        read = CotPositioningRead(
            net_leveraged_funds_position=int(newest_net),
            percentile_in_trailing_window=percentile,
            report_date=newest_date,
            lookback_weeks=COT_CROWDING_LOOKBACK_WEEKS,
        )
    except Exception as exc:  # noqa: BLE001 — malformed rows must not crash the caller
        print(f"[cot_positioning] WARNING: unexpected row shape: {exc}")
        _cache_date, _cache_read = today, None
        return None

    _cache_date, _cache_read = today, read
    return read
