"""
Market reaction - Phase 0 feasibility check (run by hand; read-only; prints to stdout only).

Spec: docs/superpowers/specs/2026-10-16-market-reaction-design.md (sections 4, 4.1, 6, 11).
Writes NOTHING to the repo or any database. The live dashboard DB is opened read-only (mode=ro).
The only thing written anywhere is a bar cache in the OS temp dir (one pickle per symbol-month,
completed months only), so a re-run does not hit Dukascopy again.

Prints:
  (a) distinct USD release minutes since START and, per tracked symbol, how many have both the
      `t` and `t+5` one-minute bars; every gap is listed;
  (b) any 5-minute window [t, t+5) that contains ANOTHER USD release minute (spec expects zero);
  (c) clusters (same exact release minute) by size 1 / 2 / 3+, with the count of events whose
      implied lean (stats_rules + stats_methods.market_lean) is not "mixed", per symbol, plus
      solo / agree / conflict cluster counts;
  (d) baseline sanity: median |5-min move| for XAUUSD at 12:00-12:59 UTC on non-release windows
      (spec method) against the Shock-alert audit method (scripts/audit_shock_impact.py baseline
      logic) over the same weekdays.

Usage:  python scripts/market_reaction_phase0.py [path/to/dashboard.db]
"""
from __future__ import annotations

import bisect
import datetime as dt
import pickle
import sqlite3
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

# Make `python scripts/market_reaction_phase0.py` work from the app dir (repo root on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

UTC = dt.timezone.utc
SYMBOLS = ("XAUUSD", "US30")
START = dt.datetime(2026, 1, 1, tzinfo=UTC)
WINDOW_MIN = 5
BASELINE_HOUR = 12
LIVE_DASHBOARD_DB = Path(
    r"C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live"
    r"\Claude_news_engine\news_engine\webapp\dashboard.db")
CACHE_DIR = Path(tempfile.gettempdir()) / "market_reaction_phase0_cache"


# =============================================================================================
# Pure helpers (unit-tested in tests/test_market_reaction_phase0.py)
# =============================================================================================

@dataclass(frozen=True)
class Gap:
    """A release minute whose 5-minute reaction cannot be measured. `missing` is a subset of ("t", "t+5")."""
    minute: dt.datetime
    missing: tuple


def find_gaps(release_minutes: Iterable[dt.datetime], bar_minutes: set, horizon_min: int = WINDOW_MIN) -> list:
    """Release minutes lacking the bar at `t` and/or at `t + horizon_min`. Never interpolated."""
    horizon = dt.timedelta(minutes=horizon_min)
    gaps = []
    for minute in sorted(set(release_minutes)):
        missing = tuple(label for label, when in (("t", minute), ("t+5", minute + horizon))
                        if when not in bar_minutes)
        if missing:
            gaps.append(Gap(minute, missing))
    return gaps


def coverage(release_minutes: Iterable[dt.datetime], gaps: list) -> tuple:
    """(minutes with both bars, total distinct minutes)."""
    total = len(set(release_minutes))
    return total - len({g.minute for g in gaps}), total


def cluster_bucket(size: int) -> str:
    """Spec 4.1 size buckets: '1', '2', '3+'."""
    return "1" if size <= 1 else "2" if size == 2 else "3+"


def group_clusters(events: Iterable[tuple]) -> dict:
    """events = (title, event_time_utc). A cluster is every event sharing the exact release minute."""
    clusters: dict = defaultdict(list)
    for title, when in events:
        clusters[when].append(title)
    return dict(clusters)


def classify_cluster(leans: list) -> str:
    """Spec 4.1 for one instrument: 'no_signal' | 'solo' | 'agree' | 'conflict' (from buy/sell/mixed leans)."""
    leaned = [lean for lean in leans if lean in ("buy", "sell")]
    if not leaned:
        return "no_signal"
    if len(leaned) == 1:
        return "solo"
    return "agree" if len(set(leaned)) == 1 else "conflict"


def overlap_windows(release_minutes: Iterable[dt.datetime], window_min: int = WINDOW_MIN) -> list:
    """For each release minute t, the OTHER release minutes o with t < o < t + window_min (window = [t, t+5))."""
    minutes = sorted(set(release_minutes))
    window = dt.timedelta(minutes=window_min)
    out = []
    for i, t in enumerate(minutes):
        inside = [o for o in minutes[i + 1:] if o < t + window]
        if inside:
            out.append((t, inside))
    return out


def median(values: list) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _weekdays(opens: dict) -> list:
    return sorted({ts.date() for ts in opens if ts.weekday() < 5})


def spec_baseline_moves(opens: dict, hour: int, release_minutes: set,
                        window_min: int = WINDOW_MIN, grid: Optional[tuple] = None) -> list:
    """
    Spec section 4 `typical` input: |open(t+5) - open(t)| for every window starting on a 5-minute boundary
    inside `hour` (UTC) on weekdays, skipping windows whose start minute is a USD release minute and any
    window missing either bar (strict: exact minute, no gap tolerance). `grid` limits the start minutes
    (default every `window_min` minutes) so the method can be compared like-for-like with the audit grid.
    """
    horizon = dt.timedelta(minutes=window_min)
    out = []
    for day in _weekdays(opens):
        for minute in (grid if grid is not None else range(0, 60, window_min)):
            start = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)
            if start in release_minutes:
                continue
            a, b = opens.get(start), opens.get(start + horizon)
            if a is not None and b is not None:
                out.append(abs(b - a))
    return out


def audit_price_at(opens: dict, when: dt.datetime, keys: Optional[list] = None) -> Optional[float]:
    """audit_shock_impact.price_at: open of the first bar at/after `when` (ceil to the minute), None if > 5 min away."""
    keys = sorted(opens) if keys is None else keys
    target = when if (when.second == 0 and when.microsecond == 0) else (
        when.replace(second=0, microsecond=0) + dt.timedelta(minutes=1))
    idx = bisect.bisect_left(keys, target)
    if idx >= len(keys) or keys[idx] - target > dt.timedelta(minutes=5):
        return None
    return opens[keys[idx]]


def audit_baseline_moves(opens: dict, hour: int, window_min: int = WINDOW_MIN,
                         grid: tuple = (0, 15, 30, 45)) -> list:
    """
    audit_shock_impact.baseline_moves logic with a configurable window: starts at hh:00/15/30/45 on weekdays,
    price_at() tolerant lookup, release minutes NOT excluded. window_min=30 is the audit's native setting.
    """
    keys = sorted(opens)
    horizon = dt.timedelta(minutes=window_min)
    out = []
    for day in _weekdays(opens):
        for minute in grid:
            start = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)
            a = audit_price_at(opens, start, keys)
            b = audit_price_at(opens, start + horizon, keys)
            if a is not None and b is not None:
                out.append(abs(b - a))
    return out


# =============================================================================================
# I/O (not unit-tested: network + the live DB)
# =============================================================================================

def _parse_utc(text: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(text)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def read_usd_events(conn: sqlite3.Connection) -> list:
    """(title, event_time_utc, forecast, actual) for every USD row, via an already-open connection."""
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, actual FROM event_history "
        "WHERE country = 'USD' ORDER BY event_time_utc").fetchall()
    return [(r[0], _parse_utc(r[1]), r[2], r[3]) for r in rows]


def load_usd_events(db_path: Path) -> list:
    """(title, event_time_utc, forecast, actual) for USD rows since START. Read-only connection."""
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        events = read_usd_events(conn)
    finally:
        conn.close()
    return [e for e in events if e[1] >= START]


def _month_chunks(start: dt.datetime, end: dt.datetime) -> list:
    chunks = []
    cur = dt.datetime(start.year, start.month, 1, tzinfo=UTC)
    while cur < end:
        nxt = dt.datetime(cur.year + (cur.month == 12), cur.month % 12 + 1, 1, tzinfo=UTC)
        chunks.append((cur, nxt))
        cur = nxt
    return chunks


def fetch_bars(symbol: str, start: dt.datetime, end: dt.datetime, pause_s: float = 2.0) -> dict:
    """{minute_start_utc: open} from Dukascopy 1-minute BID bars, fetched per calendar month and cached."""
    import dukascopy_python as dk
    from data_layer.dukascopy_feed import _resolve_dukascopy_instrument

    instrument = _resolve_dukascopy_instrument(symbol)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(UTC)
    opens: dict = {}
    for lo, hi in _month_chunks(start, end):
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


def implied_lean(title: str, forecast_text: Optional[str], actual_text: Optional[str], symbol: str) -> str:
    """Spec 4 'implied lean': side(actual vs forecast, one rounding step) -> market_lean. 'mixed' = no signal."""
    from webapp.stats_methods import market_lean
    from webapp.stats_rules import parse_number, side, tolerance

    forecast, actual, tol = parse_number(forecast_text), parse_number(actual_text), tolerance(forecast_text)
    if forecast is None or actual is None or tol is None:
        return "mixed"
    return market_lean(title, side(actual, forecast, tol), symbol)


# =============================================================================================
# Report
# =============================================================================================

def main() -> None:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else LIVE_DASHBOARD_DB
    now = dt.datetime.now(UTC)
    events = load_usd_events(db_path)
    minutes_all = sorted({e[1] for e in events})
    # A release is measurable only once its t+5 bar can exist (allow 10 minutes of vendor latency).
    measurable = [m for m in minutes_all if m + dt.timedelta(minutes=WINDOW_MIN + 10) <= now]
    pending = [m for m in minutes_all if m not in set(measurable)]
    past_events = [e for e in events if e[1] <= now]

    print(f"Run at {now:%Y-%m-%d %H:%M} UTC. Source: {db_path.name} (read-only). Window start {START:%Y-%m-%d}.")
    print(f"USD events since start: {len(events)} rows; first {events[0][1]:%Y-%m-%d %H:%M}, last {events[-1][1]:%Y-%m-%d %H:%M} UTC")
    print(f"distinct USD release minutes: {len(minutes_all)}  (measurable now: {len(measurable)}, "
          f"not yet measurable/future: {len(pending)})")

    bars = {}
    for s in SYMBOLS:
        print(f"fetching {s} ...", file=sys.stderr)
        bars[s] = fetch_bars(s, START, now)
    for s in SYMBOLS:
        keys = sorted(bars[s])
        print(f"{s}: {len(keys)} one-minute bars, {keys[0]:%Y-%m-%d %H:%M} to {keys[-1]:%Y-%m-%d %H:%M} UTC")

    # ---- (a) coverage ----------------------------------------------------------------------
    print("\n== (a) Bar coverage: release minutes with BOTH the t and t+5 bars ==")
    gaps_by_symbol = {}

    def titles_at(minute: dt.datetime) -> str:
        return ", ".join(sorted({e[0] for e in events if e[1] == minute}))

    for s in SYMBOLS:
        gaps = find_gaps(measurable, set(bars[s]))
        gaps_by_symbol[s] = gaps
        ok, total = coverage(measurable, gaps)
        print(f"{s}: {ok}/{total} covered ({ok / total:.1%}); gaps: {len(gaps)}")
    for s in SYMBOLS:
        for g in gaps_by_symbol[s]:
            n_events = sum(1 for e in events if e[1] == g.minute)
            print(f"  GAP {s} {g.minute:%Y-%m-%d %H:%M} UTC missing {' and '.join(g.missing)} ({n_events} events: {titles_at(g.minute)})")
    both_gap = {g.minute for g in gaps_by_symbol[SYMBOLS[0]]} & {g.minute for g in gaps_by_symbol[SYMBOLS[1]]}
    print(f"minutes with a gap in BOTH symbols: {len(both_gap)}")
    if pending:
        print("not yet measurable: " + ", ".join(f"{m:%m-%d %H:%M}" for m in pending[:10]) + (" ..." if len(pending) > 10 else ""))

    # ---- (b) overlaps ----------------------------------------------------------------------
    print("\n== (b) 5-minute windows [t, t+5) containing ANOTHER USD release minute (spec expects 0) ==")
    over = overlap_windows(minutes_all)
    print(f"count: {len(over)}")
    for t, others in over:
        same = any(titles_at(o) == titles_at(t) for o in others)
        kind = "SAME-TITLE duplicate/drifted calendar row" if same else "different events"
        print(f"  {t:%Y-%m-%d %H:%M} [{titles_at(t)}] overlaps " +
              "; ".join(f"{o:%H:%M} [{titles_at(o)}]" for o in others) + f"  -> {kind}")
    gaps_min = [(b - a) for a, b in zip(minutes_all, minutes_all[1:])]
    print(f"smallest spacing between consecutive release minutes: {min(gaps_min)}")

    # ---- (c) clusters ----------------------------------------------------------------------
    print("\n== (c) Clusters by size (events with the same exact minute; past events only) ==")
    clusters = group_clusters([(e[0], e[1]) for e in past_events])
    by_event = defaultdict(list)
    for e in past_events:
        by_event[e[1]].append(e)
    covered = {s: {m for m in clusters if m not in {g.minute for g in gaps_by_symbol[s]}
                   and m in set(measurable)} for s in SYMBOLS}
    table = defaultdict(lambda: defaultdict(int))
    for minute, titles in clusters.items():
        b = cluster_bucket(len(titles))
        table[b]["clusters"] += 1
        table[b]["events"] += len(titles)
        for s in SYMBOLS:
            leans = [implied_lean(e[0], e[2], e[3], s) for e in by_event[minute]]
            n_lean = sum(1 for lean in leans if lean != "mixed")
            table[b][f"lean_{s}"] += n_lean
            if minute in covered[s]:
                table[b][f"lean_cov_{s}"] += n_lean
            table[b][f"{classify_cluster(leans)}_{s}"] += 1
    header = (f"{'size':<5}{'clusters':>9}{'events':>8}  "
              + "  ".join(f"{s}:lean/covered-lean" for s in SYMBOLS))
    print(header)
    for b in ("1", "2", "3+"):
        row = table[b]
        print(f"{b:<5}{row['clusters']:>9}{row['events']:>8}  "
              + "  ".join(f"{row[f'lean_{s}']:>3}/{row[f'lean_cov_{s}']:<3}".ljust(len(s) + 18) for s in SYMBOLS))
    tot_clusters = sum(table[b]["clusters"] for b in table)
    tot_events = sum(table[b]["events"] for b in table)
    print(f"total: {tot_clusters} clusters, {tot_events} events; "
          f"clusters with 2+ events: {sum(table[b]['clusters'] for b in ('2', '3+'))}")
    print("cluster credit class counts (per symbol, by size bucket):")
    for s in SYMBOLS:
        for b in ("1", "2", "3+"):
            print(f"  {s} size {b:<2}: " + ", ".join(
                f"{c}={table[b][f'{c}_{s}']}" for c in ("solo", "agree", "conflict", "no_signal")))
    print("events with a non-mixed lean (any size): " + ", ".join(
        f"{s}={sum(table[b][f'lean_{s}'] for b in table)}/{tot_events}" for s in SYMBOLS))

    # ---- (d) baseline sanity ---------------------------------------------------------------
    print(f"\n== (d) Baseline sanity: XAUUSD, {BASELINE_HOUR}:00-{BASELINE_HOUR}:59 UTC, weekdays ==")
    gold = bars["XAUUSD"]
    release_set = set(minutes_all)
    # Shared window: weekdays that have bars in the hour (both methods read the same days).
    days = sorted({ts.date() for ts in gold if ts.weekday() < 5 and ts.hour == BASELINE_HOUR})
    gold_hr = {ts: v for ts, v in gold.items() if ts.date() in set(days)}
    print(f"shared window: {len(days)} weekdays ({days[0]} to {days[-1]})")
    spec = spec_baseline_moves(gold_hr, BASELINE_HOUR, release_set)
    spec_all = spec_baseline_moves(gold_hr, BASELINE_HOUR, set())
    audit5 = audit_baseline_moves(gold_hr, BASELINE_HOUR, 5)
    audit30 = audit_baseline_moves(gold_hr, BASELINE_HOUR, 30)
    rows = [
        ("spec method (5-min grid, release windows excluded, strict bars)", spec),
        ("spec method but release windows NOT excluded", spec_all),
        ("spec method restricted to the audit's 0/15/30/45 grid", spec_baseline_moves(gold_hr, BASELINE_HOUR, release_set, grid=(0, 15, 30, 45))),
        ("audit method, window shortened to 5 min (0/15/30/45 grid, tolerant price_at)", audit5),
        ("audit method as shipped, 30-min window (reference only; not comparable)", audit30),
    ]
    for label, vals in rows:
        m = median(vals)
        mean = sum(vals) / len(vals) if vals else None
        print(f"  {label:<78} n={len(vals):<5} median={m:.3f}  mean={mean:.3f}")
    ms, ma = median(spec), median(audit5)
    print(f"spec vs audit(5-min): {ms:.3f} vs {ma:.3f}  diff={ms - ma:+.3f} ({(ms - ma) / ma:+.1%} of audit)")
    print(f"excluding release windows changes the median by {median(spec) - median(spec_all):+.3f}; "
          f"release windows dropped: {len(spec_all) - len(spec)}")


if __name__ == "__main__":
    main()
