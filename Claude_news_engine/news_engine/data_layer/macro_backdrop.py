"""
Real macro-backdrop cross-check (R5, docs/fundamental-analysis-swot-2026-08-14.md /
"biggest remaining design gap" — the engine previously had no signal
independent of headline text or the tracked event's own forecast-vs-
actual surprise; nothing checked where the dollar and rates market were
already positioned).

Two FRED series, both live-verified 2026-08-16:
  - DTWEXBGS — Trade Weighted U.S. Dollar Index: Broad, Goods and
    Services. The Fed's own broad dollar index — the free equivalent of
    a proprietary DXY feed (which this project has no free access to).
  - DFII10 — 10-Year Treasury Inflation-Indexed Security, Constant
    Maturity (the real yield). Textbook FX relationship, not a novel
    claim: rising real yields attract dollar-denominated capital and are
    dollar-supportive — unlike the oil-price/gasoline/inflation chain
    explicitly flagged as unproven when this cross-check was requested,
    rate-differential support for the dollar is standard, well-
    established macro/FX theory, safe to encode directly.

Both series publish with a real lag (DTWEXBGS ~1 week, DFII10 a few
days) — get_macro_backdrop_read() reads whatever's the latest available,
never fabricates a "today" value.

READ-ONLY, same fail-open contract as every other data_layer module:
returns None on a missing key, a failed request, or too few
observations to compute a trend — never raises, never invents a value.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import requests

from config.settings import FRED_API_KEY

FRED_BASE_URL = "https://api.stlouisfed.org/fred"

DOLLAR_INDEX_SERIES_ID = "DTWEXBGS"
REAL_YIELD_SERIES_ID = "DFII10"

# Minimum real move before a trend counts as a genuine lean rather than
# noise — untuned starting values, same honesty as every other threshold
# constant in this codebase (needs revisiting once real backtest data
# exists). Dollar index: a broad trade-weighted index, ~0.3% over the
# lookback window is a real, not noise-level, move. Real yield: 5bps is
# a standard "did the market actually move" threshold for a 10yr real
# rate.
DOLLAR_INDEX_LEAN_THRESHOLD_PCT = 0.3
REAL_YIELD_LEAN_THRESHOLD_BPS = 5.0

# How far back to look for the trend — a pre-event-window-scale lookback
# (roughly matches PRE_EVENT_WINDOW_HOURS' 48h in spirit, widened because
# both series publish with a real reporting lag and a 2-day raw window
# would often return only 1 usable observation).
DEFAULT_LOOKBACK_DAYS = 10


@dataclass
class MacroBackdropRead:
    dollar_index_trend_pct: Optional[float]   # % change over the window; positive = dollar strengthening
    dollar_index_latest_date: Optional[dt.date]
    real_yield_trend_bps: Optional[float]      # change in basis points over the window; positive = yields rising
    real_yield_latest_date: Optional[dt.date]
    lookback_days: int

    @property
    def lean(self) -> Optional[int]:
        """
        +1 = macro backdrop leans USD-bullish, -1 = USD-bearish, None =
        no clear lean (below threshold on both measures, or no data at
        all). Dollar index is the primary read (it's the more direct
        USD-strength measure); real yield is the fallback when the
        dollar index itself shows no clear move — real yields moving
        while the index is flat is still a genuine, if secondary,
        USD-supportive/undermining signal.
        """
        if self.dollar_index_trend_pct is not None and abs(self.dollar_index_trend_pct) >= DOLLAR_INDEX_LEAN_THRESHOLD_PCT:
            return 1 if self.dollar_index_trend_pct > 0 else -1
        if self.real_yield_trend_bps is not None and abs(self.real_yield_trend_bps) >= REAL_YIELD_LEAN_THRESHOLD_BPS:
            return 1 if self.real_yield_trend_bps > 0 else -1
        return None


def _fetch_trend(series_id: str, days_back: int) -> tuple[Optional[float], Optional[dt.date]]:
    """
    Returns (pct_or_point_change, latest_observation_date) from the
    oldest to the newest REAL observation within the lookback window —
    not calendar days, since both series skip weekends/holidays. Returns
    (None, None) on any failure or if fewer than 2 real observations
    exist in the window (can't compute a trend from one point).
    """
    if not FRED_API_KEY:
        return None, None
    try:
        resp = requests.get(
            f"{FRED_BASE_URL}/series/observations",
            params={
                "series_id": series_id, "file_type": "json", "api_key": FRED_API_KEY,
                "sort_order": "desc", "limit": days_back,
            },
            timeout=15,
        )
        resp.raise_for_status()
        rows = resp.json().get("observations", [])
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the caller
        print(f"[macro_backdrop] WARNING: fetch failed for {series_id}: {exc}")
        return None, None

    # FRED marks a missing/not-yet-published observation with the literal
    # string "." — filter those out rather than crashing on float(".").
    usable = [r for r in rows if r.get("value") not in (None, ".")]
    if len(usable) < 2:
        return None, None

    newest, oldest = usable[0], usable[-1]
    newest_value, oldest_value = float(newest["value"]), float(oldest["value"])
    latest_date = dt.date.fromisoformat(newest["date"])

    if series_id == DOLLAR_INDEX_SERIES_ID:
        if oldest_value == 0:
            return None, latest_date  # avoid a division by zero on a degenerate value
        change = (newest_value - oldest_value) / oldest_value * 100.0
    else:  # real yield — a level, so the "change" is already in percentage points; x100 for basis points
        change = (newest_value - oldest_value) * 100.0

    return change, latest_date


def get_macro_backdrop_read(days_back: int = DEFAULT_LOOKBACK_DAYS) -> Optional[MacroBackdropRead]:
    """
    Returns None only if BOTH series are entirely unavailable (no key,
    or both fetches failed) — a partial read (one series available, the
    other not) still returns a real MacroBackdropRead with one field
    None, since .lean already handles a partial read via its fallback.
    """
    dollar_trend, dollar_date = _fetch_trend(DOLLAR_INDEX_SERIES_ID, days_back)
    yield_trend, yield_date = _fetch_trend(REAL_YIELD_SERIES_ID, days_back)

    if dollar_trend is None and yield_trend is None:
        return None

    return MacroBackdropRead(
        dollar_index_trend_pct=dollar_trend, dollar_index_latest_date=dollar_date,
        real_yield_trend_bps=yield_trend, real_yield_latest_date=yield_date,
        lookback_days=days_back,
    )
