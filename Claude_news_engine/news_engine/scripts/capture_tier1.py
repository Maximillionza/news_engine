"""
Deterministic Tier 1 capture for the Windows tasks NewsEngine_Tier1Daily / NewsEngine_Tier1Weekly (B12). No LLM:
every row comes from a fixed rule on a published source. Two phases, run in this order:

  1. Formula (Cleveland Fed nowcast): scripts/capture_nowcast_from_cleveland.run(), unchanged - CPI m/m,
     Core CPI m/m, CPI y/y, Core CPI y/y and Core PCE Price Index m/m.
  2. Market-implied (Kalshi, T10): for every market-implied title (data_layer.tier1_events) with a USD release
     strictly after now and within the window, read the open Kalshi strike ladder of the event that resolves on
     that release (data_layer.kalshi_feed.get_ladder) and apply the fixed rule in webapp/tier1_market.py
     (implied median vs the forecast). A call writes one tier1_predictions row per tracked instrument (source
     "Kalshi market-implied", confidence "Likely"), only when the median differs from the last Kalshi row for that
     occurrence. No open event, an illiquid or uncrossed ladder or a units mismatch = no call and no row (reported
     as MARKET NO CALL, a legitimate outcome, exit 0). No readable forecast = TIER1 PENDING, and a skip (exit 2)
     once the release is within MISSING_FORECAST_ALERT_WITHIN. A Kalshi read failure is a skip (exit 2).

The phases are isolated: a Cleveland download failure is printed and the Kalshi phase still runs (exit 1); a Kalshi
failure never touches the formula rows. Nothing is ever written for a release at or before now.

Usage:
    python scripts/capture_tier1.py [--dry-run] [--window-hours H] [--dash-db PATH] [--bt-db PATH]
Same flags as capture_nowcast_from_cleveland.py: dashboard.db is opened read-only (mode=ro); --dry-run prints what
would be written and writes nothing (it does not even open the backtest DB). Kalshi access is read-only public GETs
(/events, /markets); no auth, no trading endpoint.

Exit 0 ok (including no-calls), 1 Cleveland fetch failed (the Kalshi phase still ran), 2 a due release was skipped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Callable, Optional

# Allow `python scripts/capture_tier1.py ...` (script dir, not the app root, is on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_layer.kalshi_feed import KalshiFetchError, KalshiLadder, get_ladder  # noqa: E402
from data_layer.tier1_events import (  # noqa: E402
    TIER1_MARKET_IMPLIED, TIER1_MARKET_IMPLIED_SOURCE, tier1_titles,
)
from scoring import backtest_store  # noqa: E402
from scripts.backfill_tier1_reconstructed import open_dash_readonly  # noqa: E402
from scripts.capture_nowcast_from_cleveland import (  # noqa: E402
    MAX_WINDOW_HOURS, MISSING_FORECAST_ALERT_WITHIN, WINDOW, FetchError, _due_releases, print_summary,
)
from scripts.capture_nowcast_from_cleveland import run as run_cleveland  # noqa: E402
from webapp.store import list_tracked_symbols  # noqa: E402
from webapp.tier1_formula import SIDE_LABELS  # noqa: E402
from webapp.tier1_market import MARKET_SERIES, NO_FORECAST, market_call, record_market_calls  # noqa: E402

UTC = dt.timezone.utc

# (series_ticker, ticketing, release_utc) -> the open ladder, None when no event / no open markets; raises
# KalshiFetchError when Kalshi cannot be read. Default: kalshi_feed.get_ladder (live, read-only).
LadderFetch = Callable[[str, str, dt.datetime], Optional[KalshiLadder]]

# One producer per title: every market-implied title needs its Kalshi series, and no series may serve a title of
# another tier. Checked at import so a registry edit without a MARKET_SERIES edit fails loudly, not silently.
if set(MARKET_SERIES) != set(tier1_titles(TIER1_MARKET_IMPLIED)):
    raise RuntimeError(
        f"MARKET_SERIES {sorted(MARKET_SERIES)} != market-implied titles {tier1_titles(TIER1_MARKET_IMPLIED)}")

NO_EVENT = "no open Kalshi event for this release"


def run_market(dash_conn, bt_conn, now: dt.datetime, ladder_fetch: Optional[LadderFetch] = None,
               dry_run: bool = False, window: dt.timedelta = WINDOW) -> dict:
    """
    The Kalshi phase: a market-implied call for every market-implied release within `window` after `now`.
    Returns {"calls": [(title, release_iso, implied, side)], "no_call": [(title, release_iso, reason)],
    "skipped": [(title, release_iso, reason)], "tier1_rows": [(title, release_iso, symbol, direction,
    "written"|"unchanged")], "tier1_pending": [(title, release_iso, reason)], "dry_run": bool, "message": str}.
    With dry_run nothing is written (bt_conn may be None) and "tier1_rows" lists what would be.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError(f"now must be timezone-aware, got naive {now!r}")
    now = now.astimezone(UTC)
    fetch = ladder_fetch or get_ladder
    summary: dict = {"calls": [], "no_call": [], "skipped": [], "tier1_rows": [], "tier1_pending": [],
                     "dry_run": dry_run, "message": ""}
    due = _due_releases(dash_conn, now, window, tier1_titles(TIER1_MARKET_IMPLIED))
    if not due:
        hours = window.total_seconds() / 3600
        summary["message"] = f"No market-implied release within {hours:g} hours: nothing to read."
        return summary
    symbols = list_tracked_symbols(dash_conn)          # read once: every due release uses the same list

    for title, release, forecast in due:
        release_iso = release.isoformat()
        series = MARKET_SERIES[title]
        try:
            ladder = fetch(series.series_ticker, series.ticketing, release)
        except KalshiFetchError as exc:
            # An unreadable source is not "no market": the scheduler must notice (exit 2).
            summary["skipped"].append((title, release_iso, f"Kalshi read failed: {exc}"))
            continue
        if ladder is None:
            summary["no_call"].append((title, release_iso, f"{NO_EVENT} ({series.series_ticker}, {series.ticketing})"))
            continue
        call, reason = market_call(title, ladder, forecast)
        if reason == NO_FORECAST:
            # Same rule as the formula phase: no guessed neutral; alert only when the next run is too late.
            summary["tier1_pending"].append((title, release_iso, reason))
            if release - now <= MISSING_FORECAST_ALERT_WITHIN:
                summary["skipped"].append((title, release_iso, f"no Tier 1 market-implied call: {reason}"))
            continue
        if call is None:
            summary["no_call"].append((title, release_iso, reason))
            continue
        try:
            result = record_market_calls(bt_conn, title, release, call, forecast, symbols, now, dry_run=dry_run)
        except ValueError as exc:       # record_market_calls refuses a call stamped after the release
            summary["skipped"].append((title, release_iso, str(exc)))
            continue
        summary["calls"].append((title, release_iso, call.implied_value, call.side))
        for symbol, direction in result["written"]:
            summary["tier1_rows"].append((title, release_iso, symbol, direction, "written"))
        for symbol in result["unchanged"]:
            # Report the direction actually on the dashboard (the stored row), not a recomputation.
            row = backtest_store.get_latest_tier1_prediction_for_occurrence(
                bt_conn, title, symbol, release, source=TIER1_MARKET_IMPLIED_SOURCE)
            summary["tier1_rows"].append((title, release_iso, symbol, row.predicted_direction, "unchanged"))
    summary["message"] = (f"{'Would call' if dry_run else 'Called'} {len(summary['calls'])} market-implied, "
                          f"no call {len(summary['no_call'])}, skipped {len(summary['skipped'])}.")
    return summary


def print_market_summary(summary: dict, dry_run: bool) -> None:
    """Print run_market()'s summary in the same log style as the formula phase."""
    print(summary["message"])
    for title, release_iso, implied, side in summary["calls"]:
        print(f"  MARKET CALL {title} release {release_iso}: implied {implied:g} ({SIDE_LABELS[side]})")
    for title, release_iso, reason in summary["no_call"]:
        print(f"  MARKET NO CALL {title} release {release_iso}: {reason}")
    for title, release_iso, reason in summary["skipped"]:
        print(f"  SKIPPED {title} release {release_iso}: {reason}")
    for title, _release_iso, symbol, direction, status in summary["tier1_rows"]:
        print(f"  TIER1 [market-implied] {title} {symbol}: {direction} ({'would write' if dry_run else status})")
    for title, release_iso, reason in summary["tier1_pending"]:
        print(f"  TIER1 PENDING {title} release {release_iso}: {reason}")


def main(argv: Optional[list[str]] = None, cleveland_fetch: Optional[Callable[[str], object]] = None,
         ladder_fetch: Optional[LadderFetch] = None, now: Optional[dt.datetime] = None) -> int:
    """cleveland_fetch, ladder_fetch and now are test seams; the scheduler uses the defaults (live, real clock)."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print what would be written; write nothing")
    parser.add_argument("--dash-db", type=Path, default=None, help="dashboard.db to read event_history from (read-only)")
    parser.add_argument("--bt-db", type=Path, default=None, help="backtest_log.db to write Tier 1 rows to (default: live)")
    parser.add_argument("--window-hours", type=float, default=WINDOW.total_seconds() / 3600,
                        help="cover releases due within this many hours after now (default 48; weekly task: 192)")
    args = parser.parse_args(argv)
    if not 0 < args.window_hours <= MAX_WINDOW_HOURS:
        parser.error(f"--window-hours must be > 0 and <= {MAX_WINDOW_HOURS}, got {args.window_hours:g}")

    now = now or dt.datetime.now(UTC)
    window = dt.timedelta(hours=args.window_hours)
    dash_conn = open_dash_readonly(args.dash_db)
    bt_conn = None if args.dry_run else backtest_store.get_connection(args.bt_db)
    cleveland_failed = False
    try:
        # Phase 1, formula. Printed before phase 2 runs, so its result is in the log whatever phase 2 does.
        try:
            formula = run_cleveland(dash_conn, bt_conn, now, cleveland_fetch, dry_run=args.dry_run, window=window)
        except FetchError as exc:
            print(f"ERROR: Cleveland formula phase: {exc}", file=sys.stderr)
            cleveland_failed = True
            formula = None
        if formula is not None:
            print_summary(formula, args.dry_run, now)
        # Phase 2, market-implied: runs whatever happened to phase 1.
        market = run_market(dash_conn, bt_conn, now, ladder_fetch, dry_run=args.dry_run, window=window)
        print_market_summary(market, args.dry_run)
    finally:
        dash_conn.close()
        if bt_conn is not None:
            bt_conn.close()

    if cleveland_failed:
        return 1
    return 2 if (formula["skipped"] or market["skipped"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
