# alerting/reality_check.py
"""
Task Scheduler entry point — runs weekly. For every alert without a
reality check yet, fetches price at detection time, +5min, and +30min
for each affected symbol, compares the realized move against that UTC hour's
Market reaction baseline, and flags a mismatch for manual review. Never
auto-changes an alert's category/severity or the baselines themselves.

B10 (2026-10-28): the same run first grades every due alert's stored lean
(alerting/lean_grading.py, 5-minute window, published and detected anchors)
and records one summary row that ops/health.py shows. The fixed
MAGNITUDE_THRESHOLDS ($10 / 150 pts) are gone: "moved" now means the 5-minute
detection move beats the hourly baseline (no 30-minute baseline exists, so the
30-minute move is stored but no longer compared).
See docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Optional

from alerting import lean_grading, store
from data_layer import minute_bars
from data_layer.dukascopy_feed import get_price_at
from data_layer.minute_bars import FetchBars
from scoring import backtest_store
from webapp import store as webapp_store
from webapp.reaction_rules import classify_reaction

SECONDARY_WINDOW_MINUTES = 30

# An alert detected less than this many minutes before the job runs would
# still have its detected_at_utc + SECONDARY_WINDOW_MINUTES window in the
# future, so get_price_at correctly returns None for it -- but without
# this floor it would get permanently stamped reality_check_at_utc with
# mismatch=None and never be re-examined later once real price data
# exists (get_alerts_needing_reality_check only returns rows still NULL).
# Comfortably past the 30-minute secondary window.
MIN_AGE_MINUTES = 60


def run_reality_check(
    conn: Optional[sqlite3.Connection] = None, *, symbols: Optional[list[str]] = None,
    baselines_by_symbol: Optional[dict[str, dict[int, float]]] = None, fetch_bars: Optional[FetchBars] = None,
    now: Optional[dt.datetime] = None,
) -> dict:
    """
    Grades due leans, records the grading summary, then checks every due alert. A None argument is loaded from
    the live default paths (read-only for dashboard.db / backtest_log.db), so tests pass all four explicitly.
    Returns the mismatch counts plus "grading" (grade_pending_alerts result) and "summary_line".
    """
    conn = conn if conn is not None else store.get_connection()
    older_than = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)  # every unchecked alert, regardless of age
    now = now if now is not None else dt.datetime.now(dt.timezone.utc)
    if symbols is None:
        symbols = lean_grading.load_tracked_symbols(webapp_store.DB_PATH)
    if baselines_by_symbol is None:
        baselines_by_symbol = lean_grading.load_baselines(backtest_store.DB_PATH, symbols)
    if fetch_bars is None:
        fetch_bars = minute_bars.fetch_bars

    grading = lean_grading.grade_pending_alerts(conn, symbols, baselines_by_symbol, fetch_bars, now)
    summary_line = lean_grading.format_summary_line(grading)
    store.record_grading_run(conn, now, "weekly", grading["counts"], summary_line)

    counts: dict = {"checked": 0, "mismatches": 0, "no_price_data": 0}
    min_age_cutoff = now - dt.timedelta(minutes=MIN_AGE_MINUTES)
    for alert in store.get_alerts_needing_reality_check(conn, older_than):
        if alert.detected_at_utc > min_age_cutoff:
            # Too recent -- skip silently this run. It was never marked
            # checked, so a future run will pick it up once it's old
            # enough for real price data to exist.
            continue
        outcome = _check_alert(conn, alert, baselines_by_symbol)
        counts["checked"] += 1
        if outcome == "mismatch":
            counts["mismatches"] += 1
        elif outcome == "no_price_data":
            counts["no_price_data"] += 1
    counts["grading"] = grading
    counts["summary_line"] = summary_line
    return counts


def _check_alert(conn: sqlite3.Connection, alert: store.ShockAlertRow,
                 baselines_by_symbol: dict[str, dict[int, float]]) -> str:
    """Returns "mismatch", "no_price_data" or "ok"."""
    if not alert.affected_symbols:
        # Nothing to price-check -- still mark it checked so it doesn't
        # get re-queried every week forever.
        store.record_reality_check(conn, alert.id, move_5min=None, move_secondary=None, mismatch=None)
        return "ok"

    move_5min: dict[str, float] = {}
    move_secondary: dict[str, float] = {}
    any_threshold_cleared = False
    any_price_data = False

    for impact in alert.affected_symbols:
        symbol = impact["symbol"]
        # B10 (2026-10-28): the hourly Market reaction baseline of the detection minute's UTC hour.
        threshold = baselines_by_symbol.get(symbol, {}).get(lean_grading.anchor_minute(alert.detected_at_utc).hour)
        if threshold is None:
            continue  # no baseline for this symbol/hour -- skip it, not a mismatch signal either way

        t0 = get_price_at(symbol, alert.detected_at_utc)
        t5 = get_price_at(symbol, alert.detected_at_utc + dt.timedelta(minutes=5))
        t_secondary = get_price_at(symbol, alert.detected_at_utc + dt.timedelta(minutes=SECONDARY_WINDOW_MINUTES))

        if t0 is None or t5 is None:
            continue  # real data unavailable for this symbol -- never fabricated

        any_price_data = True
        move_5min[symbol] = round(t5.price - t0.price, 4)
        if t_secondary is not None:
            move_secondary[symbol] = round(t_secondary.price - t0.price, 4)

        # The 30-minute move is stored above but not compared: no 30-minute baseline exists.
        if classify_reaction(move_5min[symbol], threshold) in ("buy", "sell"):
            any_threshold_cleared = True

    if not any_price_data:
        store.record_reality_check(conn, alert.id, move_5min=None, move_secondary=None, mismatch=None)
        return "no_price_data"

    # A High alert with no confirming move is a mismatch (over-alerted);
    # a Low alert WITH a confirming move is also a mismatch (under-alerted,
    # the exact "should this have been a High" case the design discusses).
    if alert.severity == "High":
        mismatch = not any_threshold_cleared
    elif alert.severity == "Low":
        mismatch = any_threshold_cleared
    else:  # Medium is never flagged as a mismatch in v1 -- no established
           # "expected" magnitude band for Medium to compare against yet
        mismatch = False

    store.record_reality_check(
        conn, alert.id,
        move_5min=move_5min or None, move_secondary=move_secondary or None, mismatch=mismatch,
    )
    return "mismatch" if mismatch else "ok"


def main() -> int:
    """Job entry point; exit 1 when a symbol's bar fetch failed (nothing written for it; the next run retries)."""
    result = run_reality_check()
    print(f"[reality_check] checked {result['checked']} alert(s): "
          f"{result['mismatches']} mismatch(es), {result['no_price_data']} without price data")
    print(f"[lean_grading] {result['summary_line']}")
    return 1 if result["grading"]["fetch_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
