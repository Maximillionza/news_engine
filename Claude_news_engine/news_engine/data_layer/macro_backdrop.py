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

A third FRED series was added 2026-08-19:
  - DCOILWTICO — WTI crude, USD-denominated (not Brent — WTI is the
    benchmark that actually feeds US CPI/PCE energy components). This is
    NOT the "oil -> gasoline -> cost of living -> inflation -> hike"
    causal chain that was explicitly flagged as unproven when R5 was
    first scoped — that chain stays out. What's encoded here is the one
    step of it with textbook standing: rising oil is a standard leading
    indicator for CPI energy-component forecasts, i.e. an
    inflation-expectations proxy, which feeds the same hawkish-lean/
    USD-bullish axis as the other two series. A supply-shock oil move
    (OPEC cut) reads identically to a demand-driven one here — price
    alone can't tell them apart, and no further data-layer fix removes
    that ambiguity, so oil is deliberately the lowest-priority fallback
    in .lean: it only fills a gap when both direct USD measures (dollar
    index, real yield) are silent, and it never overrides them.

A fourth FRED series was added 2026-09-02:
  - SP500 — S&P 500 daily close, live-verified 2026-09-02 (HTTP 200, real
    values). Used two ways: a 10-day trend (equity_index_trend_pct) as a
    risk-on/risk-off proxy, read independently of the USD-lean fallback
    chain above — it answers a different question (risk sentiment, not
    dollar direction) and is consumed by its own dedicated check
    (_check_equity_risk_sentiment in scoring/probability_engine.py).

Also added 2026-09-02: oil_daily_change_pct, a single most-recent-SESSION
% change for DCOILWTICO, distinct from oil_trend_pct's 10-day window —
used for shock detection (_check_oil_shock) where a sharp one-day move
matters differently than a multi-day drift.

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
OIL_SERIES_ID = "DCOILWTICO"
EQUITY_INDEX_SERIES_ID = "SP500"

# Minimum real move before a trend counts as a genuine lean rather than
# noise — untuned starting values, same honesty as every other threshold
# constant in this codebase (needs revisiting once real backtest data
# exists). Dollar index: a broad trade-weighted index, ~0.3% over the
# lookback window is a real, not noise-level, move. Real yield: 5bps is
# a standard "did the market actually move" threshold for a 10yr real
# rate.
DOLLAR_INDEX_LEAN_THRESHOLD_PCT = 0.3
REAL_YIELD_LEAN_THRESHOLD_BPS = 5.0

# Oil (WTI) is a raw commodity price, far more volatile than a broad
# trade-weighted index — single-session moves of 2-5% on inventory data
# or OPEC headlines alone are routine. Copying the dollar index's
# 0.3%-scale threshold would make oil fire a "lean" on pure noise most
# days. This is itself an untuned starting value, same honesty as the
# other two thresholds — wide enough to filter routine noise, needs
# revisiting once real backtest data exists.
OIL_LEAN_THRESHOLD_PCT = 5.0

# Same reasoning as OIL_LEAN_THRESHOLD_PCT's comment — an untuned starting
# value. The S&P 500 is a broad index like the dollar index, not a raw
# commodity like oil, so this uses a threshold in the dollar index's
# scale (0.3%) rather than oil's wider 5% — tightened somewhat since
# risk-sentiment moves worth flagging tend to be larger single moves than
# routine dollar-index drift. Needs revisiting once real backtest data
# exists.
EQUITY_INDEX_LEAN_THRESHOLD_PCT = 1.0

# A single most-recent-DAY oil move, deliberately distinct from
# OIL_LEAN_THRESHOLD_PCT's 10-day trend — a "shock" is a sharp one-session
# move, not a multi-day drift, and re-using the 10-day trend's threshold
# would conflate the two. Tighter than OIL_LEAN_THRESHOLD_PCT=5.0 because
# this is measuring ONE session's move, not a 10-day window's worth.
# Untuned starting value.
OIL_SHOCK_DAILY_THRESHOLD_PCT = 4.0

# Series reported as a raw price level, where "trend" is a % change
# (dollar index, oil, equity index) — vs. a series already in
# percentage-point units, where "trend" is a change measured in basis
# points (real yield). _fetch_trend uses this to pick the right unit of
# change.
PERCENT_CHANGE_SERIES_IDS = {DOLLAR_INDEX_SERIES_ID, OIL_SERIES_ID, EQUITY_INDEX_SERIES_ID}

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
    oil_trend_pct: Optional[float]             # % change over the window; positive = WTI strengthening (inflation-expectations proxy)
    oil_latest_date: Optional[dt.date]
    equity_index_trend_pct: Optional[float]    # % change over the window; positive = equities strengthening (risk-on proxy)
    equity_index_latest_date: Optional[dt.date]
    oil_daily_change_pct: Optional[float]      # % change over the single most recent session ONLY — distinct from oil_trend_pct's 10-day window; used for shock detection, not the .lean fallback chain
    lookback_days: int

    @property
    def lean(self) -> Optional[int]:
        """
        +1 = macro backdrop leans USD-bullish, -1 = USD-bearish, None =
        no clear lean (below threshold on every measure, or no data at
        all). Dollar index is the primary read (it's the more direct
        USD-strength measure); real yield is the first fallback when the
        dollar index itself shows no clear move — real yields moving
        while the index is flat is still a genuine, if secondary,
        USD-supportive/undermining signal. Oil is the lowest-priority
        fallback: it's one causal step further removed (a leading
        inflation-expectations proxy, not a direct USD measure — see
        module docstring), so it only fills a gap when BOTH direct USD
        measures are silent, and never overrides them.

        equity_index_trend_pct and oil_daily_change_pct are deliberately
        NOT part of this fallback chain — they answer different
        questions (risk-on/off, single-day shock) than "does the dollar
        backdrop lean bullish or bearish," and are consumed directly by
        their own dedicated checks in scoring/probability_engine.py
        instead (_check_equity_risk_sentiment, _check_oil_shock).
        """
        if self.dollar_index_trend_pct is not None and abs(self.dollar_index_trend_pct) >= DOLLAR_INDEX_LEAN_THRESHOLD_PCT:
            return 1 if self.dollar_index_trend_pct > 0 else -1
        if self.real_yield_trend_bps is not None and abs(self.real_yield_trend_bps) >= REAL_YIELD_LEAN_THRESHOLD_BPS:
            return 1 if self.real_yield_trend_bps > 0 else -1
        if self.oil_trend_pct is not None and abs(self.oil_trend_pct) >= OIL_LEAN_THRESHOLD_PCT:
            return 1 if self.oil_trend_pct > 0 else -1
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

    if series_id in PERCENT_CHANGE_SERIES_IDS:
        if oldest_value == 0:
            return None, latest_date  # avoid a division by zero on a degenerate value
        change = (newest_value - oldest_value) / oldest_value * 100.0
    else:  # real yield — a level, so the "change" is already in percentage points; x100 for basis points
        change = (newest_value - oldest_value) * 100.0

    return change, latest_date


def _fetch_daily_change(series_id: str) -> Optional[float]:
    """
    Returns the % change between the two most recent REAL observations
    (newest vs. second-newest) — deliberately NOT the same as
    _fetch_trend()'s window-based change, which compares newest vs.
    OLDEST across the whole lookback. Used for shock detection: a
    "shock" is defined as one session's move, not a multi-day drift.
    Returns None on any failure, missing key, or fewer than 2 usable
    observations — same fail-open contract as _fetch_trend().
    """
    if not FRED_API_KEY:
        return None
    try:
        resp = requests.get(
            f"{FRED_BASE_URL}/series/observations",
            params={
                "series_id": series_id, "file_type": "json", "api_key": FRED_API_KEY,
                "sort_order": "desc", "limit": 5,  # a handful of recent obs is enough to find 2 usable ones past weekends/holidays
            },
            timeout=15,
        )
        resp.raise_for_status()
        rows = resp.json().get("observations", [])
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the caller
        print(f"[macro_backdrop] WARNING: daily-change fetch failed for {series_id}: {exc}")
        return None

    usable = [r for r in rows if r.get("value") not in (None, ".")]
    if len(usable) < 2:
        return None

    newest_value, second_newest_value = float(usable[0]["value"]), float(usable[1]["value"])
    if second_newest_value == 0:
        return None
    return (newest_value - second_newest_value) / second_newest_value * 100.0


def get_macro_backdrop_read(days_back: int = DEFAULT_LOOKBACK_DAYS) -> Optional[MacroBackdropRead]:
    """
    Returns None only if ALL FOUR series are entirely unavailable (no
    key, or every fetch failed) — a partial read (some series available,
    others not) still returns a real MacroBackdropRead with the missing
    fields None, since .lean already handles a partial read via its
    fallback chain, and equity_index_trend_pct/oil_daily_change_pct are
    read independently of .lean by their own dedicated checks.
    """
    dollar_trend, dollar_date = _fetch_trend(DOLLAR_INDEX_SERIES_ID, days_back)
    yield_trend, yield_date = _fetch_trend(REAL_YIELD_SERIES_ID, days_back)
    oil_trend, oil_date = _fetch_trend(OIL_SERIES_ID, days_back)
    equity_trend, equity_date = _fetch_trend(EQUITY_INDEX_SERIES_ID, days_back)
    oil_daily_change = _fetch_daily_change(OIL_SERIES_ID)

    if dollar_trend is None and yield_trend is None and oil_trend is None and equity_trend is None:
        return None

    return MacroBackdropRead(
        dollar_index_trend_pct=dollar_trend, dollar_index_latest_date=dollar_date,
        real_yield_trend_bps=yield_trend, real_yield_latest_date=yield_date,
        oil_trend_pct=oil_trend, oil_latest_date=oil_date,
        equity_index_trend_pct=equity_trend, equity_index_latest_date=equity_date,
        oil_daily_change_pct=oil_daily_change,
        lookback_days=days_back,
    )
