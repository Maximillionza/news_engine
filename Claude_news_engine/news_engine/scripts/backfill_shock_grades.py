"""
One-time backfill of shock-alert lean grades (B10 K14, 2026-10-28; plan
docs/superpowers/plans/2026-10-28-b10-shock-grading.md, Task 4).

Grades every past alert's stored lean (alerting/lean_grading.py: 5-minute window, published and detected anchors,
hourly Market reaction baselines) and, with --apply, writes the grades to shock_alerts.db. Safe by default:

  * Dry run unless --apply. A dry run opens ALL three DBs read-only (sqlite URI mode=ro), writes nothing and does
    not even create the grade tables, so it can be pointed at the live DBs to preview what a deploy will write.
  * --apply opens shock_alerts.db through alerting.store.get_connection (additive migration) and records one
    summary row (source "backfill"). backtest_log.db and dashboard.db are always read-only.
  * Grade writes are INSERT OR IGNORE, so a rerun prints "graded 0".
  * Refuses to run against the live default paths unless --alerts-db is given or SHOCK_GRADES_LIVE=1.
  * Exit 1 when a symbol's bar fetch failed (nothing written for it; rerun later), 2 when refusing.

Usage (from the app dir):
  python scripts/backfill_shock_grades.py --alerts-db <path> --bt-db <path> --dash-db <path> [--apply]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path
from typing import Optional

# Allow `python scripts/backfill_shock_grades.py ...` (script dir, not the app root, is on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alerting import lean_grading, store  # noqa: E402
from data_layer import minute_bars  # noqa: E402
from scoring import backtest_store  # noqa: E402
from webapp import store as dash_store  # noqa: E402

LIVE_ENV_VAR = "SHOCK_GRADES_LIVE"
# Module-level so tests can substitute a fake feed (resolved at call time).
FETCH_BARS = minute_bars.fetch_bars

# The leans graded by hand at the 2026-10-20 sweep: 14 correct of 26 at 5 minutes (roadmap-2026-10-20.md).
STARTING_POINT = "14 of 26"


def _pct(right: int, n: int) -> str:
    return f"{right / n * 100:.1f}%" if n else "n/a"


def _print_counts(counts: dict) -> None:
    """Verdict counts per anchor, overall and per symbol."""
    def line(label: str, anchor: str, c: dict) -> None:
        print(f"  {label:<8} {anchor:<9} right {c['right']}, wrong {c['wrong']}, no_move {c['no_move']}, "
              f"no_lean {c['no_lean']}, no_data {c['no_data']}, no_baseline {c['no_baseline']}")
    for anchor, c in counts["overall"].items():
        line("overall", anchor, c)
    for symbol, per_anchor in counts["by_symbol"].items():
        for anchor, c in per_anchor.items():
            line(symbol, anchor, c)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill shock-alert lean grades (dry run unless --apply).")
    parser.add_argument("--apply", action="store_true", help="write the grades (default: dry run, nothing written)")
    parser.add_argument("--alerts-db", type=Path, default=None, help="shock_alerts.db path")
    parser.add_argument("--bt-db", type=Path, default=None, help="backtest_log.db path (read-only)")
    parser.add_argument("--dash-db", type=Path, default=None, help="dashboard.db path (read-only)")
    args = parser.parse_args(argv)

    if args.alerts_db is None and os.environ.get(LIVE_ENV_VAR) != "1":
        print(f"REFUSING to run: pass --alerts-db PATH explicitly, or set {LIVE_ENV_VAR}=1 to deliberately use the "
              f"live default paths.")
        return 2
    alerts_db = args.alerts_db if args.alerts_db is not None else store.DB_PATH
    bt_db = args.bt_db if args.bt_db is not None else backtest_store.DB_PATH
    dash_db = args.dash_db if args.dash_db is not None else dash_store.DB_PATH

    now = dt.datetime.now(dt.timezone.utc)
    symbols = lean_grading.load_tracked_symbols(dash_db)
    baselines = lean_grading.load_baselines(bt_db, symbols)
    conn = store.get_connection(alerts_db) if args.apply else lean_grading.open_readonly(alerts_db)
    try:
        result = lean_grading.grade_pending_alerts(
            conn, symbols, baselines, FETCH_BARS, now, dry_run=not args.apply)
        line = lean_grading.format_summary_line(result)
        if args.apply:
            store.record_grading_run(conn, now, "backfill", result["counts"], line)
    finally:
        conn.close()

    print(f"[backfill_shock_grades] {'APPLY' if args.apply else 'dry run (nothing written; pass --apply to write)'}"
          f" -- symbols {', '.join(symbols) or 'none'}")
    _print_counts(result["counts"])
    print(f"written {result['written']}, pending {result['pending']}, already_present {result['already_present']}")
    for symbol, error in sorted(result["fetch_failed"].items()):
        print(f"fetch failed for {symbol}: {error}")
    print(line)
    detected = result["counts"]["overall"]["detected"]
    print(f"overall 5-minute detection-anchored hit rate: {_pct(detected['right'], detected['n'])} "
          f"({detected['right']} of {detected['n']}); starting point before B10: {STARTING_POINT}")
    return 1 if result["fetch_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
