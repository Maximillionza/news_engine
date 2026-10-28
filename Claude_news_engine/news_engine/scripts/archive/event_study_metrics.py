"""
B5 event study - per-window price measures from OHLC bars (pure; no I/O, no network, no DB).

Plan: docs/superpowers/plans/2026-10-21-b5-event-study.md (Task 1). Used by
scripts/archive/event_study_groups.py and scripts/archive/event_study_once.py; unit-tested in
tests/test_event_study_metrics.py.

Bar rules (the reason every lookup here is "first at/after" or "last before", never "the bar at"):
  * Dukascopy 1-second bars are SPARSE: a second with no tick has no bar (probe 2026-10-14 12:28Z:
    DXY 972 bars in 33 min). Prices are never interpolated; a missing bar is missing.
  * p0 = open of the first bar starting at or after t, and only if that bar starts less than
    P0_MAX_LAG after t (so the p0 bar always lies inside the shortest horizon window).
  * Peaks use highs and lows (never opens) of the bars starting in the half-open window
    [t, t + k): pre-release bars and the bar starting at t + k are excluded.
  * Net at k = close of the last bar starting before t + k, minus p0, and only if that bar starts
    at most NET_MAX_GAP before t + k (a stale close is no close).
  * Time to peak = seconds from t to the START of the first bar reaching the larger extreme, so it
    is resolution-bound: whole seconds on 1-second bars, multiples of 60 on the 1-minute fallback.

All timestamps are aware UTC. Prices are in the instrument's quote ($ for XAUUSD, points for US30,
index points for DXY); `owner_units` converts to the owner's terms ($1 of gold = 100 pips).
"""
from __future__ import annotations

import datetime as dt
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# Make `python scripts/...` work from the app dir (repo root on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

UTC = dt.timezone.utc

HORIZONS_MIN: tuple[int, ...] = (1, 5, 30)          # peak / time-to-peak windows [t, t + k)
NET_HORIZONS_MIN: tuple[int, ...] = (5, 30)         # net move horizons
P0_MAX_LAG = dt.timedelta(seconds=60)               # p0 bar must start within this of t (exclusive)
NET_MAX_GAP = dt.timedelta(seconds=120)             # net close bar may be at most this stale
PIPS_PER_DOLLAR_XAU = 100                           # owner's gold pips: 4080 -> 4090 = 1000 pips
RETRACE_LIMIT = 0.5                                 # retrace above this = "spike then pull back"

METRIC_KEYS: tuple[str, ...] = (
    "status", "bar_source", "resolution_s", "p0", "p0_lag_s",
    "up_1", "down_1", "peak_1", "ttp_1_s", "side_1",
    "up_5", "down_5", "peak_5", "ttp_5_s", "side_5",
    "up_30", "down_30", "peak_30", "ttp_30_s", "side_30",
    "net_5", "net_30", "first_min_dir", "first_min_peak",
    "retrace_5", "retrace_30", "spike_pullback_5", "spike_pullback_30",
)


@dataclass(frozen=True)
class Bar:
    """One OHLC bar; `ts` is the aware UTC bar START."""
    ts: dt.datetime
    open: float
    high: float
    low: float
    close: float


def bars_from_frame(df: pd.DataFrame) -> list[Bar]:
    """Dukascopy frame (tz-aware DatetimeIndex, columns open/high/low/close) -> bars sorted by ts.

    Rows with any non-finite OHLC value are dropped. A naive index raises ValueError (we will not
    guess the timezone of a price series). An empty frame gives [].
    """
    if df is None or len(df) == 0:
        return []
    index = df.index
    if not isinstance(index, pd.DatetimeIndex):
        raise ValueError("bars_from_frame: index must be a DatetimeIndex")
    if index.tz is None:
        raise ValueError("bars_from_frame: naive DatetimeIndex (timezone unknown)")
    stamps = index.tz_convert("UTC").to_pydatetime()
    bars: list[Bar] = []
    for ts, o, h, lo, c in zip(stamps, df["open"], df["high"], df["low"], df["close"]):
        values = (float(o), float(h), float(lo), float(c))
        if not all(math.isfinite(v) for v in values):
            continue
        bars.append(Bar(ts.astimezone(UTC), *values))
    bars.sort(key=lambda b: b.ts)
    return bars


def first_open_at_or_after(bars: list[Bar], t: dt.datetime,
                           max_lag: dt.timedelta = P0_MAX_LAG) -> Optional[tuple[float, int]]:
    """(open, lag seconds) of the first bar with ts >= t; None if it starts max_lag or more after t."""
    first: Optional[Bar] = None
    for b in bars:
        if b.ts >= t and (first is None or b.ts < first.ts):
            first = b
    if first is None or first.ts - t >= max_lag:
        return None
    return first.open, int((first.ts - t).total_seconds())


def close_before(bars: list[Bar], when: dt.datetime,
                 max_gap: dt.timedelta = NET_MAX_GAP) -> Optional[float]:
    """Close of the last bar with ts < when; None if none, or if it starts before when - max_gap."""
    last: Optional[Bar] = None
    for b in bars:
        if b.ts < when and (last is None or b.ts > last.ts):
            last = b
    if last is None or last.ts < when - max_gap:
        return None
    return last.close


def excursion(bars: list[Bar], t: dt.datetime, p0: float,
              k_min: int) -> tuple[float, float, Optional[int], int]:
    """(up, down, time-to-peak s, peak side) over the bars starting in [t, t + k_min).

    up = max(high) - p0, down = p0 - min(low). Side +1 when up > down, -1 when down > up, 0 on a
    tie. Time to peak = seconds from t to the start of the first bar reaching the larger extreme
    (on a non-zero tie, the earlier of the two); None on a tie of zeros or an empty window.
    """
    end = t + dt.timedelta(minutes=k_min)
    window = sorted((b for b in bars if t <= b.ts < end), key=lambda b: b.ts)
    if not window:
        return 0.0, 0.0, None, 0
    hi = max(b.high for b in window)
    lo = min(b.low for b in window)
    up = hi - p0
    down = p0 - lo
    if up > down:
        side = 1
    elif down > up:
        side = -1
    else:
        side = 0
    if side == 0 and up == 0.0:
        return up, down, None, 0
    for b in window:
        if (side >= 0 and b.high == hi) or (side <= 0 and b.low == lo):
            return up, down, int((b.ts - t).total_seconds()), side
    return up, down, None, side   # unreachable: the extremes come from the window itself


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def measure_window(bars: list[Bar], t: dt.datetime, bar_source: str,
                   resolution_s: int) -> dict[str, Any]:
    """Every measure of one release window; keys exactly METRIC_KEYS.

    status "no_data" (no p0 within P0_MAX_LAG) leaves every measure None. first_min_dir/peak are
    the 1-minute side/peak. Retrace at k = 1 - first_min_dir * net_k / first_min_peak; spike then
    pull back at k = net_k's sign opposite the first-minute direction, or retrace > RETRACE_LIMIT.
    Both are None when the first minute has no direction or peak, or net_k is missing.
    """
    out: dict[str, Any] = {key: None for key in METRIC_KEYS}
    out["bar_source"] = bar_source
    out["resolution_s"] = resolution_s
    first = first_open_at_or_after(bars, t)
    if first is None:
        out["status"] = "no_data"
        return out
    p0, lag = first
    out.update(status="ok", p0=p0, p0_lag_s=lag)

    for k in HORIZONS_MIN:
        up, down, ttp, side = excursion(bars, t, p0, k)
        out[f"up_{k}"] = up
        out[f"down_{k}"] = down
        out[f"peak_{k}"] = max(up, down)
        out[f"ttp_{k}_s"] = ttp
        out[f"side_{k}"] = side
    first_dir = out["side_1"]
    first_peak = out["peak_1"]
    out["first_min_dir"] = first_dir
    out["first_min_peak"] = first_peak

    for k in NET_HORIZONS_MIN:
        close = close_before(bars, t + dt.timedelta(minutes=k))
        net = None if close is None else close - p0
        out[f"net_{k}"] = net
        if net is None or first_dir == 0 or not first_peak:
            continue
        retrace = 1.0 - first_dir * net / first_peak
        out[f"retrace_{k}"] = retrace
        out[f"spike_pullback_{k}"] = bool(_sign(net) == -first_dir or retrace > RETRACE_LIMIT)
    return out


def _has_full_window(bars: list[Bar], t: dt.datetime) -> bool:
    """A p0 and a fresh close before t + 30 min (the longest net horizon)."""
    longest = dt.timedelta(minutes=max(NET_HORIZONS_MIN))
    return first_open_at_or_after(bars, t) is not None and close_before(bars, t + longest) is not None


def choose_bars(sec_bars: list[Bar], min_bars: list[Bar],
                t: dt.datetime) -> tuple[str, int, list[Bar]]:
    """Pick the bar series for a window: (source tag, resolution s, bars).

    1-second bars when they give p0 and a fresh 30-minute close; else 1-minute bars under the same
    test; else whichever has p0 (seconds first); else ("none", 0, []).
    """
    if _has_full_window(sec_bars, t):
        return "sec1", 1, sec_bars
    if _has_full_window(min_bars, t):
        return "min1", 60, min_bars
    if first_open_at_or_after(sec_bars, t) is not None:
        return "sec1", 1, sec_bars
    if first_open_at_or_after(min_bars, t) is not None:
        return "min1", 60, min_bars
    return "none", 0, []


def owner_units(symbol: str, delta: float) -> tuple[float, str]:
    """A price difference in the owner's units: gold pips ($1 = 100), US30 points, DXY index points."""
    if symbol == "XAUUSD":
        return float(delta) * PIPS_PER_DOLLAR_XAU, "pips"
    if symbol == "US30":
        return float(delta), "points"
    if symbol == "DXY":
        return float(delta), "index points"
    raise ValueError(f"owner_units: unsupported symbol {symbol!r}")


def baseline_multiple(value: Optional[float], baseline: Optional[float]) -> Optional[float]:
    """value / baseline (the hourly typical |5-min move|); None when either is missing or baseline <= 0."""
    if value is None or baseline is None or baseline <= 0:
        return None
    return value / baseline
