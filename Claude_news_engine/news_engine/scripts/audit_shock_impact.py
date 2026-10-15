"""
Shock-alert impact audit (run by hand; read-only, writes nothing to the alerts DB).

Question: do the alerts we send coincide with unusual moves in the symbols we watch
(XAUUSD, US30), compared with ordinary half-hours at the same time of day?

Method: 1-minute Dukascopy bars for the alert period. For each alert, the absolute
price change over the 30 minutes after detection is ranked against every other
30-minute window starting in the same UTC hour on other weekdays (the "baseline").
A rank of 0.5 means "typical"; the null expectation for the share of alerts above
the 75th / 90th percentile is 25% / 10%. Direction (alerts carrying a buy/sell lean)
is scored separately. Small samples: read the counts, not just the percentages.

Usage:  python scripts/audit_shock_impact.py [path/to/shock_alerts.db]   (default: this checkout's DB)
"""
from __future__ import annotations

import bisect
import datetime as dt
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Optional

import json
import sys

import dukascopy_python as dk
import pandas as pd

from alerting.store import DB_PATH
from data_layer.dukascopy_feed import _resolve_dukascopy_instrument

SYMBOLS = ("XAUUSD", "US30")
WINDOW_MIN = 30
UTC = dt.timezone.utc


def load_bars(symbol: str, start: dt.datetime, end: dt.datetime) -> pd.Series:
    """Open price per minute, indexed by UTC timestamp."""
    df = dk.fetch(_resolve_dukascopy_instrument(symbol), dk.INTERVAL_MIN_1, dk.OFFER_SIDE_BID, start, end)
    return df["open"].sort_index()


def price_at(bars: pd.Series, when: dt.datetime) -> Optional[float]:
    """Open of the first bar at or after `when` (no lookahead), None if the gap is > 5 min."""
    target = pd.Timestamp(when).ceil("min").as_unit(bars.index.unit)  # next whole minute: nothing before detection is used
    idx = bars.index.searchsorted(target)
    if idx >= len(bars):
        return None
    if bars.index[idx] - target > pd.Timedelta(minutes=5):
        return None
    return float(bars.iloc[idx])


def abs_move(bars: pd.Series, when: dt.datetime) -> Optional[float]:
    a, b = price_at(bars, when), price_at(bars, when + dt.timedelta(minutes=WINDOW_MIN))
    return None if a is None or b is None else abs(b - a)


def signed_move(bars: pd.Series, when: dt.datetime) -> Optional[float]:
    a, b = price_at(bars, when), price_at(bars, when + dt.timedelta(minutes=WINDOW_MIN))
    return None if a is None or b is None else b - a


def baseline_moves(bars: pd.Series, hour: int, exclude_day: dt.date) -> list[float]:
    """|30-min move| for windows starting at hh:00/15/30/45 in `hour`, other weekdays."""
    out: list[float] = []
    for day in sorted({ts.date() for ts in bars.index}):
        if day == exclude_day or day.weekday() >= 5:
            continue
        for minute in (0, 15, 30, 45):
            m = abs_move(bars, dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC))
            if m is not None:
                out.append(m)
    return sorted(out)


def percentile_rank(sorted_values: list[float], x: float) -> float:
    return bisect.bisect_left(sorted_values, x) / len(sorted_values)


def main() -> None:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT id, detected_at_utc, severity, category, classification_method, affected_symbols_json, headline "
        "FROM shock_alerts ORDER BY id").fetchall()
    alerts = [(i, dt.datetime.fromisoformat(t), sev, cat, meth, json.loads(aff or "[]"), h)
              for i, t, sev, cat, meth, aff, h in rows]
    start = min(a[1] for a in alerts) - dt.timedelta(days=1)
    end = max(a[1] for a in alerts) + dt.timedelta(hours=2)
    bars = {s: load_bars(s, start, end) for s in SYMBOLS}

    ranks: dict[str, list[tuple[int, str, str, float]]] = {s: [] for s in SYMBOLS}  # (id, sev, cat, rank)
    hits: list[tuple[int, str, str, str, float]] = []  # (id, symbol, lean, ..., signed move)
    for i, when, sev, cat, meth, aff, headline in alerts:
        for s in SYMBOLS:
            m = abs_move(bars[s], when)
            if m is None:
                continue
            base = baseline_moves(bars[s], when.hour, when.date())
            if len(base) < 20:
                continue
            ranks[s].append((i, sev, cat, percentile_rank(base, m)))
        for imp in aff:
            if imp.get("lean") in ("buy", "sell") and imp["symbol"] in SYMBOLS:
                sm = signed_move(bars[imp["symbol"]], when)
                if sm is not None:
                    hits.append((i, imp["symbol"], imp["lean"], headline[:60], sm))

    def summarize(label: str, items: list[float]) -> str:
        n = len(items)
        if n == 0:
            return f"{label:<34} n=0"
        return (f"{label:<34} n={n:<3} mean_rank={sum(items)/n:.2f}  >75th={sum(r > .75 for r in items)/n:4.0%}  "
                f">90th={sum(r > .90 for r in items)/n:4.0%}")

    print("== Magnitude vs same-hour baseline (null: mean 0.50, >75th 25%, >90th 10%) ==")
    for s in SYMBOLS:
        print(f"-- {s}")
        print(summarize("all alerts", [r[3] for r in ranks[s]]))
        for key, pos in (("severity", 1), ("category", 2)):
            groups: dict[str, list[float]] = defaultdict(list)
            for r in ranks[s]:
                groups[r[pos]].append(r[3])
            for g, vals in sorted(groups.items()):
                print(summarize(f"{key}={g}", vals))

    print("\n== Direction: alerts with a buy/sell lean (30 min move in the lean's direction) ==")
    ok = tot = 0
    for i, s, lean, h, sm in hits:
        right = (sm > 0) == (lean == "buy")
        ok += right
        tot += 1
        print(f"#{i:<3} {s:<7} lean={lean:<4} move={sm:+9.2f}  {'HIT ' if right else 'MISS'}  {h}")
    print(f"direction hit rate: {ok}/{tot}" + (f" = {ok/tot:.0%} (coin flip = 50%)" if tot else ""))


if __name__ == "__main__":
    main()
