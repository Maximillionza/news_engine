"""
Market reaction compute script (spec docs/superpowers/specs/2026-10-16-market-reaction-design.md §4, §6).

For every USD release minute `t` in dashboard.db's event_history and every tracked symbol, records how the
symbol moved over the 5 minutes after the release (open of the 1-minute bar at t+5 minus open of the bar at
t, Dukascopy BID bars) against the typical 5-minute move for that UTC hour, into the append-only tables
release_reactions and reaction_baselines of backtest_log.db. Never interpolates: a missing bar is "no data".

Rules (controller rulings for Task 3):
  * Release minutes: USD rows only; same-title rows within 3 minutes of the earliest row of their run are one
    event listed twice and collapse to that earliest row (a 9-minute pair is two events). The distinct exact
    minutes left are the release minutes that get judged. Baseline windows exclude EVERY raw USD row minute,
    including the collapsed duplicates (controller ruling 5). The release's own day is not excluded from
    the baseline: one row per hour cannot do that (about 0.5% of windows).
  * Baseline per instrument per UTC hour: the REACTION_BASELINE_QUANTILE (0.75, owner ruling 2026-10-16;
    linear interpolation like numpy) of |open(s+5) - open(s)| over windows starting on 5-minute boundaries,
    weekdays only, start not a release minute, both bars present. A reaction is |move| > that value x
    REACTION_MIN_MULTIPLE; both numbers are stored on every row (rows are versioned by quantile, so a 0.75 run
    never touches 0.5 rows and getters never mix them). Window starts are limited to
    the period [first bar fetched, last release minute judged] and that period is stored on the row, so a
    re-run over the same releases reproduces the same baseline and adds nothing. One row per hour with data.
  * A release younger than 10 minutes is skipped (skipped_recent). A release whose t+5 lies beyond the last
    bar the feed has returned is left for a later run (skipped_pending): the bar may simply not be published
    yet, and an append-only no_data row could never be corrected.
  * --backfill recomputes and records the baselines, then records every release minute since --since that
    has no row yet. --incremental only records release minutes with no row, judged against the latest stored
    baselines (computed and recorded first if none exist). Rows already present are counted, never rewritten.
  * --refresh-baselines (any mode) recomputes the baselines for the current period and records them as NEW
    rows (new period_end); existing rows are never touched, and an unchanged period adds nothing. Who runs
    it: the scheduler hook (Task 7) runs `--incremental --refresh-baselines` monthly so the typical move keeps
    up with volatility; ordinary incremental runs keep using the latest stored baselines.
  * A fetch failure (exception or no bars at all) for one symbol writes nothing for that symbol; a read
    (existing rows or stored baselines), compute or record failure is reported too (rows committed before
    it stay; a re-run resumes). Either way the other symbols still run and the exit code is 1.
    --dry-run computes and prints, writes nothing (no schema).

Usage (from the app dir):
    python scripts/compute_release_reactions.py --backfill [--since 2026-01-01] [--dry-run] --bt-db PATH
    python scripts/compute_release_reactions.py --incremental --bt-db PATH [--dash-db PATH] [--refresh-baselines]
Safety: refuses (exit 2) to target the app's default (live) backtest_log.db unless --bt-db is given or
STATS_BACKFILL_LIVE=1 is set; the refusal happens before any database is opened. dashboard.db is always
opened read-only (sqlite URI mode=ro).
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import os
import sqlite3
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Callable, Optional, Union

import pandas as pd

# Allow `python scripts/compute_release_reactions.py ...` (script dir, not the app root, is on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoring import backtest_store  # noqa: E402
from scripts import market_reaction_phase0 as phase0  # noqa: E402
from scripts.backfill_tier1_reconstructed import LIVE_ENV_VAR, open_dash_readonly  # noqa: E402
from webapp import store as dash_store  # noqa: E402
from webapp.reaction_rules import (  # noqa: E402
    REACTION_BASELINE_QUANTILE, REACTION_MIN_MULTIPLE, classify_reaction,
    collapse_same_title_duplicates,
)

UTC = dt.timezone.utc
WINDOW = dt.timedelta(minutes=phase0.WINDOW_MIN)      # the 5-minute reaction window (spec R1)
MIN_AGE = dt.timedelta(minutes=10)                     # a release must be at least this old to be judged
DEFAULT_SINCE = dt.datetime(2026, 1, 1, tzinfo=UTC)
BAR_SOURCE = "dukascopy_1m"
MODES = ("backfill", "incremental")

# The only code that touches the network: Dukascopy 1-minute BID bars per calendar month, completed months
# cached as pickles in the OS temp dir (scripts/market_reaction_phase0.py). Tests replace this attribute.
default_fetch_bars = phase0.fetch_bars

Bars = Union[pd.Series, Mapping]
FetchBars = Callable[[str, dt.datetime, dt.datetime], Bars]


# =============================================================================================
# Pure helpers
# =============================================================================================

def _aware_utc(value: dt.datetime, name: str) -> dt.datetime:
    """A naive datetime is ambiguous (local or UTC?), so it is refused rather than guessed."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware, got naive {value!r}")
    return value.astimezone(UTC)


def _release_minute(when: dt.datetime) -> dt.datetime:
    """The UTC minute a release falls in (event_history times are whole minutes; seconds are dropped)."""
    return _aware_utc(when, "release time").replace(second=0, microsecond=0)


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
        pairs = ((_aware_utc(ts, "bar timestamp"), value) for ts, value in bars.items())
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
    return _as_opens(bars).get(_aware_utc(when, "when"))


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


def compute_baselines(
    bars: Bars, release_minutes: set[dt.datetime],
    period: Optional[tuple[dt.datetime, dt.datetime]] = None, q: float = REACTION_BASELINE_QUANTILE,
) -> dict[int, tuple[float, int]]:
    """
    UTC hour -> (q-quantile of |5-minute move|, window count), spec §4 `typical`, over the moves from
    phase0.spec_baseline_moves (5-minute grid, weekdays only, starts on `release_minutes` excluded, strict
    exact-minute bars). `period` limits window starts to [lo, hi]: bars outside [lo, hi + 5 min] are dropped,
    so a window starting after hi loses its end bar. Hours without a window are absent (never invented).
    """
    opens = _as_opens(bars)
    if period is not None:
        lo, hi = period
        opens = {ts: price for ts, price in opens.items() if lo <= ts <= hi + WINDOW}
    baselines: dict[int, tuple[float, int]] = {}
    for hour in range(24):
        moves = phase0.spec_baseline_moves(opens, hour, release_minutes)
        if moves:
            baselines[hour] = (quantile(moves, q), len(moves))
    return baselines


def reaction_for(bars: Bars, release: dt.datetime, typical: Optional[float],
                 multiple: float = REACTION_MIN_MULTIPLE) -> dict:
    """
    status 'ok' with p0, p5 and reaction ('buy'/'sell'/'none' from classify_reaction: |move| > typical x
    multiple), or 'no_data' when either bar is missing or there is no usable baseline. `typical` (the
    quantile value) is echoed so a no_data row can keep it.
    """
    opens = _as_opens(bars)
    minute = _release_minute(release)
    p0, p5 = opens.get(minute), opens.get(minute + WINDOW)
    no_data = {"status": "no_data", "p0": None, "p5": None, "reaction": None, "typical": typical}
    if p0 is None or p5 is None:
        return no_data
    reaction = classify_reaction(p5 - p0, typical, multiple)
    if reaction is None:                       # no baseline for the hour (or a zero one): cannot judge
        return no_data
    return {"status": "ok", "p0": p0, "p5": p5, "reaction": reaction, "typical": typical}


def release_minute_sets(dash_conn: sqlite3.Connection) -> tuple[set[dt.datetime], set[dt.datetime]]:
    """
    (judged, excluded): judged = distinct UTC minutes of the USD rows after the same-title duplicate collapse
    (each is one release); excluded = EVERY raw USD row minute, including the dropped duplicates, which no
    baseline window may start on (controller ruling 5).
    """
    events = [(title, when) for title, when, _forecast, _actual in phase0.read_usd_events(dash_conn)]
    judged = {_release_minute(when) for _title, when in collapse_same_title_duplicates(events)}
    excluded = {_release_minute(when) for _title, when in events}
    return judged, excluded


def usd_release_minutes(dash_conn: sqlite3.Connection) -> set[dt.datetime]:
    """Distinct UTC release minutes of the USD event_history rows after the duplicate collapse."""
    return release_minute_sets(dash_conn)[0]


# =============================================================================================
# Store access tolerant of a read-only dry-run connection (tables may not exist yet)
# =============================================================================================

def _has_table(conn: Optional[sqlite3.Connection], name: str) -> bool:
    if conn is None:
        return False
    found = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return found is not None


def _existing_reaction_keys(conn: Optional[sqlite3.Connection], symbol: str) -> set[str]:
    if not _has_table(conn, "release_reactions"):
        return set()
    return set(backtest_store.get_release_reactions(conn, symbol, REACTION_BASELINE_QUANTILE,
                                                    REACTION_MIN_MULTIPLE))


def _stored_baselines(conn: Optional[sqlite3.Connection], symbol: str) -> dict[int, float]:
    if not _has_table(conn, "reaction_baselines"):
        return {}
    return backtest_store.get_latest_reaction_baselines(conn, symbol, REACTION_BASELINE_QUANTILE)


def _baseline_hours_at(conn: Optional[sqlite3.Connection], symbol: str, period_end: dt.datetime) -> set[int]:
    if not _has_table(conn, "reaction_baselines"):
        return set()
    rows = conn.execute(
        "SELECT utc_hour FROM reaction_baselines WHERE instrument=? AND quantile=? AND period_end_utc=?",
        (symbol, REACTION_BASELINE_QUANTILE, period_end.isoformat())).fetchall()
    return {int(r[0]) for r in rows}


def _resolve_dukascopy(symbol: str) -> Optional[str]:
    from data_layer.dukascopy_feed import _resolve_dukascopy_instrument
    return _resolve_dukascopy_instrument(symbol)


# =============================================================================================
# Orchestration
# =============================================================================================

_COUNTERS = ("written", "already_present", "ok", "no_data", "buy", "sell", "none",
             "skipped_recent", "skipped_pending", "baselines", "baselines_new")


def _judge_and_record(
    bt_conn: Optional[sqlite3.Connection], symbol: str, opens: dict, stats: dict, result: dict,
    stored: dict[int, float], need_baselines: bool, eligible: list[dt.datetime], todo: list[dt.datetime],
    excluded_minutes: set[dt.datetime], dry_run: bool,
) -> None:
    """Baselines (computed or stored), then one reaction row per todo minute. Raises on any failure."""
    if need_baselines:
        period = (min(opens), eligible[-1])
        computed = {int(hour): (float(value), int(n))
                    for hour, (value, n) in compute_baselines(opens, excluded_minutes, period).items()}
        already = _baseline_hours_at(bt_conn, symbol, period[1])
        stats["baselines"] = len(computed)
        stats["baselines_new"] = sum(1 for hour in computed if hour not in already)
        if not dry_run:
            for hour, (value, n) in sorted(computed.items()):
                backtest_store.record_reaction_baseline(bt_conn, symbol, hour, value, n, *period,
                                                        quantile=REACTION_BASELINE_QUANTILE)
        typical_by_hour = {hour: value for hour, (value, _n) in computed.items()}
        result["baselines_by_symbol"][symbol] = {
            "source": "computed", "period": [p.isoformat() for p in period],
            "hours": {hour: {"value": value, "n_windows": n} for hour, (value, n) in sorted(computed.items())}}
    else:
        typical_by_hour = {int(hour): float(value) for hour, value in stored.items()}
        result["baselines_by_symbol"][symbol] = {
            "source": "stored", "period": None,
            "hours": {hour: {"value": value, "n_windows": None} for hour, value in sorted(typical_by_hour.items())}}

    last_bar = max(opens)
    version = {"bar_source": BAR_SOURCE, "baseline_quantile": REACTION_BASELINE_QUANTILE,
               "reaction_multiple": REACTION_MIN_MULTIPLE}
    for minute in todo:
        if minute + WINDOW > last_bar:                 # the feed has not reached t+5 yet: try again later
            stats["skipped_pending"] += 1
            continue
        out = reaction_for(opens, minute, typical_by_hour.get(minute.hour), REACTION_MIN_MULTIPLE)
        if not dry_run:
            if out["status"] == "ok":
                backtest_store.record_release_reaction(
                    bt_conn, minute, symbol, "ok", p0=out["p0"], p5=out["p5"],
                    typical_abs_move=out["typical"], reaction=out["reaction"], **version)
            else:
                backtest_store.record_release_reaction(
                    bt_conn, minute, symbol, "no_data", typical_abs_move=out["typical"], **version)
        stats["written"] += 1
        stats[out["status"]] += 1
        if out["reaction"] is not None:
            stats[out["reaction"]] += 1


def run(
    dash_conn: sqlite3.Connection, bt_conn: Optional[sqlite3.Connection], fetch_bars: FetchBars, mode: str,
    now: dt.datetime, symbols: list[str], since: dt.datetime, dry_run: bool = False,
    resolve: Optional[Callable[[str], Optional[str]]] = None, refresh_baselines: bool = False,
) -> dict:
    """
    Compute and (unless dry_run) record reactions and baselines. Counts are per (release minute, symbol):
    written = rows newly recorded (would be, on a dry run); already_present = rows that existed and were
    left alone; skipped_recent = releases under 10 minutes old (future releases are not counted);
    baselines / baselines_new = hourly baseline rows computed / not yet stored.
    refresh_baselines: recompute baselines for the current period even in incremental mode (new rows only).
    fetch_failed / errors: per-symbol failures (fetch, or reading existing rows/baselines, compute or record);
    the other symbols still run.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    now, since = _aware_utc(now, "now"), _aware_utc(since, "since")
    resolve = resolve or _resolve_dukascopy
    release_minutes, excluded_minutes = release_minute_sets(dash_conn)
    cutoff = now - MIN_AGE
    eligible = sorted(m for m in release_minutes if since <= m <= cutoff)
    recent = [m for m in release_minutes if since <= m and cutoff < m <= now]

    result: dict = {"mode": mode, "dry_run": dry_run, **{key: 0 for key in _COUNTERS},
                    "fetch_failed": {}, "errors": {}, "unresolved": [], "per_symbol": {}, "baselines_by_symbol": {}}
    for symbol in symbols:
        if resolve(symbol) is None:
            result["unresolved"].append(symbol)
            continue
        stats = {key: 0 for key in _COUNTERS}
        result["per_symbol"][symbol] = stats
        stats["skipped_recent"] = len(recent)
        try:                                           # a read error for one symbol must not stop the others
            existing = _existing_reaction_keys(bt_conn, symbol)
            todo = [m for m in eligible if m.isoformat() not in existing]
            stats["already_present"] = len(eligible) - len(todo)
            if not eligible or (mode == "incremental" and not todo and not refresh_baselines):
                continue                               # nothing to judge or refresh: no fetch at all
            stored = _stored_baselines(bt_conn, symbol) if mode == "incremental" and not refresh_baselines else {}
        except Exception as exc:
            result["errors"][symbol] = f"{type(exc).__name__}: {exc}"
            continue
        need_baselines = not stored

        try:
            opens = to_opens(fetch_bars(symbol, since if need_baselines else todo[0], now))
            if not opens:
                raise ValueError("no bars returned")
        except Exception as exc:                       # one symbol's feed failure must not stop the others
            result["fetch_failed"][symbol] = f"{type(exc).__name__}: {exc}"
            continue
        try:
            _judge_and_record(bt_conn, symbol, opens, stats, result, stored, need_baselines, eligible, todo,
                              excluded_minutes, dry_run)
        except Exception as exc:                       # compute/record failure: report, keep going
            # Rows recorded before the failure stay (append-only, each committed); a re-run resumes.
            result["errors"][symbol] = f"{type(exc).__name__}: {exc}"

    for stats in result["per_symbol"].values():
        for key in _COUNTERS:
            result[key] += stats[key]
    return result


# =============================================================================================
# CLI
# =============================================================================================

def _parse_since(text: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(text)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _open_bt(path: Path, dry_run: bool) -> Optional[sqlite3.Connection]:
    """Read-only (and no schema setup) on a dry run; None if the file does not exist yet."""
    if not dry_run:
        return backtest_store.get_connection(path)
    if not path.exists():
        return None
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _print_summary(result: dict) -> None:
    head = "DRY RUN (nothing written)" if result["dry_run"] else "written to the backtest DB"
    print(f"mode={result['mode']}  {head}")
    print("totals: " + "  ".join(f"{key}={result[key]}" for key in _COUNTERS))
    for symbol, stats in result["per_symbol"].items():
        print(f"  {symbol}: " + "  ".join(f"{key}={stats[key]}" for key in _COUNTERS))
    for symbol, info in result["baselines_by_symbol"].items():
        period = f" period {info['period'][0]} .. {info['period'][1]}" if info["period"] else ""
        print(f"  {symbol} baselines ({info['source']}){period}:")
        for hour, row in info["hours"].items():
            n = "" if row["n_windows"] is None else f"  n={row['n_windows']}"
            print(f"    {hour:02d}:00-{hour:02d}:59 UTC  q{REACTION_BASELINE_QUANTILE:g} |5m move| = {row['value']:.4f}{n}")
    if result["unresolved"]:
        print("unresolved symbols (skipped, no Dukascopy mapping): " + ", ".join(result["unresolved"]))
    for symbol, error in result["fetch_failed"].items():
        print(f"FETCH FAILED {symbol}: {error} (nothing written for {symbol})", file=sys.stderr)
    for symbol, error in result.get("errors", {}).items():
        print(f"FAILED {symbol}: {error} (rows recorded before the failure are kept; re-run to resume)",
              file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--backfill", action="store_true", help="recompute baselines; record every missing release")
    which.add_argument("--incremental", action="store_true", help="record missing releases with stored baselines")
    parser.add_argument("--dry-run", action="store_true", help="compute and print; write nothing")
    parser.add_argument("--refresh-baselines", action="store_true",
                        help="recompute baselines for the current period and record them as new rows (any mode)")
    parser.add_argument("--bt-db", type=Path, default=None, help="backtest_log.db to write (required unless "
                                                                  f"{LIVE_ENV_VAR}=1)")
    parser.add_argument("--dash-db", type=Path, default=None, help="dashboard.db to read (opened read-only)")
    parser.add_argument("--since", default=DEFAULT_SINCE.date().isoformat(),
                        help="first release day considered (UTC, YYYY-MM-DD; default 2026-01-01)")
    args = parser.parse_args(argv)
    if args.bt_db is None and os.environ.get(LIVE_ENV_VAR) != "1":
        print(f"REFUSING to run: pass --bt-db PATH explicitly, or set {LIVE_ENV_VAR}=1 to deliberately write to the "
              "app's default (live) backtest_log.db.", file=sys.stderr)
        return 2
    since = _parse_since(args.since)
    bt_path = Path(args.bt_db) if args.bt_db is not None else backtest_store.DB_PATH
    dash_conn = open_dash_readonly(args.dash_db)
    bt_conn = None
    try:
        bt_conn = _open_bt(bt_path, args.dry_run)
        symbols = dash_store.list_tracked_symbols(dash_conn)
        result = run(dash_conn, bt_conn, default_fetch_bars, "backfill" if args.backfill else "incremental",
                     dt.datetime.now(UTC), symbols, since, dry_run=args.dry_run,
                     refresh_baselines=args.refresh_baselines)
    finally:
        dash_conn.close()
        if bt_conn is not None:
            bt_conn.close()
    _print_summary(result)
    return 1 if result["fetch_failed"] or result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
