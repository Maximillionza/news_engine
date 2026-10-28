"""
Shared 1-minute bar helpers (B10 C4, 2026-10-28).

Moved out of the one-off scripts/archive/market_reaction_phase0.py and scripts/compute_release_reactions.py so the
hourly reaction job and the shock-alert lean grading (alerting/lean_grading.py) read bars and baselines the
same way. Behaviour is unchanged by the move (tests/test_minute_bars.py::test_reaction_job_output_unchanged_by_c4).

Contents:
  * Dukascopy 1-minute BID bar fetch with a per-symbol-month pickle cache in the OS temp dir (completed
    months only), the only code that touches the network;
  * bar normalisation (`to_opens`), exact-minute lookup (`price_at_minute`, never a neighbouring bar);
  * the spec baseline-window moves (`spec_baseline_moves`) and `quantile` (numpy 'linear' interpolation);
  * USD event reading from dashboard.db's event_history (`read_usd_events`).
"""
from __future__ import annotations

import datetime as dt
import math
import pickle
import sqlite3
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Callable, Optional, Union

import pandas as pd

UTC = dt.timezone.utc
WINDOW_MIN = 5                                    # the 5-minute reaction window (spec R1)
# Same directory the one-off script used, so month pickles already on disk are reused.
CACHE_DIR = Path(tempfile.gettempdir()) / "market_reaction_phase0_cache"

Bars = Union[pd.Series, Mapping]
FetchBars = Callable[[str, dt.datetime, dt.datetime], Bars]


# =============================================================================================
# Pure helpers
# =============================================================================================

def aware_utc(value: dt.datetime, name: str) -> dt.datetime:
    """A naive datetime is ambiguous (local or UTC?), so it is refused rather than guessed."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware, got naive {value!r}")
    return value.astimezone(UTC)


def parse_utc(text: str) -> dt.datetime:
    """ISO text to an aware UTC datetime; a naive stamp is taken as UTC (event_history stores UTC)."""
    parsed = dt.datetime.fromisoformat(text)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


class _Opens(dict):
    """A {aware UTC minute: open} dict already validated by to_opens (so it is not re-checked per call)."""


def to_opens(bars: Bars) -> dict[dt.datetime, float]:
    """
    {aware UTC minute start: open} from a pandas Series (UTC DatetimeIndex -> open) or a mapping.
    Non-finite opens are dropped (a NaN bar is a missing bar). A naive timestamp raises.
    """
    if isinstance(bars, pd.Series):
        index = bars.index
        if len(index) and getattr(index, "tz", None) is None:
            raise ValueError("bar index must be timezone-aware UTC, got a naive index")
        stamps = [ts.replace(tzinfo=UTC) for ts in index.tz_convert(UTC).to_pydatetime()] if len(index) else []
        pairs = zip(stamps, bars.to_numpy())
    elif isinstance(bars, Mapping):
        pairs = ((aware_utc(ts, "bar timestamp"), value) for ts, value in bars.items())
    else:
        raise TypeError(f"bars must be a pandas Series or a mapping, got {type(bars).__name__}")
    opens = _Opens()
    for when, value in pairs:
        if value is None:
            continue
        price = float(value)
        if math.isfinite(price):
            opens[when] = price
    return opens


def _as_opens(bars: Bars) -> dict[dt.datetime, float]:
    """Only to_opens output skips validation; any other dict or Series is normalised (naive keys raise)."""
    return bars if isinstance(bars, _Opens) else to_opens(bars)


def price_at_minute(bars: Bars, when: dt.datetime) -> Optional[float]:
    """Open of the 1-minute bar starting exactly at `when`, or None. Never a neighbouring bar."""
    return _as_opens(bars).get(aware_utc(when, "when"))


def quantile(values: list[float], q: float) -> Optional[float]:
    """
    The q-quantile with linear interpolation between order statistics (numpy's default 'linear' method):
    h = (n - 1) * q, value = x[floor(h)] + (h - floor(h)) * (x[floor(h) + 1] - x[floor(h)]). None if empty.
    """
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def weekdays(opens: dict) -> list[dt.date]:
    """Sorted distinct Monday-Friday UTC dates that have at least one bar."""
    return sorted({ts.date() for ts in opens if ts.weekday() < 5})


def spec_baseline_moves(opens: dict, hour: int, release_minutes: set,
                        window_min: int = WINDOW_MIN, grid: Optional[tuple] = None) -> list[float]:
    """
    Spec section 4 `typical` input: |open(t+5) - open(t)| for every window starting on a 5-minute boundary
    inside `hour` (UTC) on weekdays, skipping windows whose start minute is a USD release minute and any
    window missing either bar (strict: exact minute, no gap tolerance). `grid` limits the start minutes
    (default every `window_min` minutes) so the method can be compared like-for-like with the audit grid.
    """
    horizon = dt.timedelta(minutes=window_min)
    out = []
    for day in weekdays(opens):
        for minute in (grid if grid is not None else range(0, 60, window_min)):
            start = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)
            if start in release_minutes:
                continue
            a, b = opens.get(start), opens.get(start + horizon)
            if a is not None and b is not None:
                out.append(abs(b - a))
    return out


# =============================================================================================
# I/O (network and the dashboard DB; not unit-tested against live data)
# =============================================================================================

def read_usd_events(conn: sqlite3.Connection) -> list[tuple]:
    """(title, event_time_utc, forecast, actual) for every USD row, via an already-open connection."""
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, actual FROM event_history "
        "WHERE country = 'USD' ORDER BY event_time_utc").fetchall()
    return [(r[0], parse_utc(r[1]), r[2], r[3]) for r in rows]


def month_chunks(start: dt.datetime, end: dt.datetime) -> list[tuple[dt.datetime, dt.datetime]]:
    """[(first of month, first of next month)] covering [start, end), UTC."""
    chunks = []
    cur = dt.datetime(start.year, start.month, 1, tzinfo=UTC)
    while cur < end:
        nxt = dt.datetime(cur.year + (cur.month == 12), cur.month % 12 + 1, 1, tzinfo=UTC)
        chunks.append((cur, nxt))
        cur = nxt
    return chunks


def fetch_bars(symbol: str, start: dt.datetime, end: dt.datetime, pause_s: float = 2.0) -> dict[dt.datetime, float]:
    """{minute_start_utc: open} from Dukascopy 1-minute BID bars, fetched per calendar month and cached."""
    import dukascopy_python as dk
    from data_layer.dukascopy_feed import _resolve_dukascopy_instrument

    instrument = _resolve_dukascopy_instrument(symbol)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(UTC)
    opens: dict = {}
    for lo, hi in month_chunks(start, end):
        cache = CACHE_DIR / f"{symbol}_{lo:%Y-%m}.pkl"
        complete = hi <= now - dt.timedelta(hours=1)           # only finished months are cached
        if complete and cache.exists():
            opens.update(pickle.loads(cache.read_bytes()))
            continue
        fetch_to = min(hi, now) + dt.timedelta(minutes=10)     # a little slack so a month-end t+5 is included
        df = dk.fetch(instrument, dk.INTERVAL_MIN_1, dk.OFFER_SIDE_BID, lo, fetch_to)
        chunk = {ts.to_pydatetime().astimezone(UTC): float(v) for ts, v in df["open"].sort_index().items()}
        if complete:
            cache.write_bytes(pickle.dumps(chunk))
        opens.update(chunk)
        print(f"  fetched {symbol} {lo:%Y-%m}: {len(chunk)} bars", file=sys.stderr)
        time.sleep(pause_s)                                    # do not hammer the service
    return opens
