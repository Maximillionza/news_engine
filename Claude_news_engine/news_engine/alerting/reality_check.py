# alerting/reality_check.py
"""
Task Scheduler entry point — runs weekly. For every alert without a
reality check yet, fetches price at detection time, +5min, and +30min
for each affected symbol, compares the realized move against per-symbol
magnitude thresholds, and flags a mismatch for manual review. Never
auto-changes an alert's category/severity or the thresholds themselves.
See docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md.
"""
from __future__ import annotations

import datetime as dt

from alerting import store
from data_layer.dukascopy_feed import get_price_at

# V1 defaults, tunable -- see design spec's "V1 magnitude thresholds" table.
# $10 on XAUUSD's ~$2,800-3,000/oz base is ~0.35%; 150pts on US30 is the
# percentage-matched equivalent.
MAGNITUDE_THRESHOLDS: dict[str, float] = {
    "XAUUSD": 10.0,
    "US30": 150.0,
}

SECONDARY_WINDOW_MINUTES = 30


def run_reality_check(conn=None) -> None:
    conn = conn if conn is not None else store.get_connection()
    older_than = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)  # every unchecked alert, regardless of age
    for alert in store.get_alerts_needing_reality_check(conn, older_than):
        _check_alert(conn, alert)


def _check_alert(conn, alert) -> None:
    if not alert.affected_symbols:
        # Nothing to price-check -- still mark it checked so it doesn't
        # get re-queried every week forever.
        store.record_reality_check(conn, alert.id, move_5min=None, move_secondary=None, mismatch=None)
        return

    move_5min: dict[str, float] = {}
    move_secondary: dict[str, float] = {}
    any_threshold_cleared = False
    any_price_data = False

    for impact in alert.affected_symbols:
        symbol = impact["symbol"]
        threshold = MAGNITUDE_THRESHOLDS.get(symbol)
        if threshold is None:
            continue  # no v1 threshold for this symbol -- skip it, not a mismatch signal either way

        t0 = get_price_at(symbol, alert.detected_at_utc)
        t5 = get_price_at(symbol, alert.detected_at_utc + dt.timedelta(minutes=5))
        t_secondary = get_price_at(symbol, alert.detected_at_utc + dt.timedelta(minutes=SECONDARY_WINDOW_MINUTES))

        if t0 is None or t5 is None:
            continue  # real data unavailable for this symbol -- never fabricated

        any_price_data = True
        move_5min[symbol] = round(t5.price - t0.price, 4)
        if t_secondary is not None:
            move_secondary[symbol] = round(t_secondary.price - t0.price, 4)

        if abs(move_5min[symbol]) >= threshold or (symbol in move_secondary and abs(move_secondary[symbol]) >= threshold):
            any_threshold_cleared = True

    if not any_price_data:
        store.record_reality_check(conn, alert.id, move_5min=None, move_secondary=None, mismatch=None)
        return

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


if __name__ == "__main__":
    run_reality_check()
