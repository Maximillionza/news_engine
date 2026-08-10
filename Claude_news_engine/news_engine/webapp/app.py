"""
Flask API for the symbol impact dashboard — serves tracked symbols,
calendar events, and current/previous predictions to the frontend in
webapp/static/. Does not do any scoring itself; that's webapp/scheduler.py's
job, running in a background thread started at app startup.
"""
from __future__ import annotations

import sys
import os
import datetime as dt
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_from_directory

from data_layer.calendar_feed import fetch_calendar, filter_relevant_events
from webapp.scheduler import RAMP_INTERVAL_SECONDS, compute_adaptive_interval_seconds, start_scheduler
from webapp.store import (
    get_connection, get_latest_two, get_history,
    add_tracked_symbol, remove_tracked_symbol, list_tracked_symbols,
)
from webapp.symbols import classify_symbol, UnrecognizedSymbolError
from scoring.backtest_store import (
    get_connection as get_backtest_connection, get_latest_prediction,
)

app = Flask(__name__, static_folder="static")

DEFAULT_SYMBOLS = ["XAUUSD", "US30"]

# /api/calendar and /api/predictions both need the same filtered event
# list, and the frontend polls both every 60s (refreshAll() in app.js).
# Without a cache that's 2 live requests/min to Forex Factory's free feed
# forever — no auth, no rate-limit tolerance — which gets the dashboard
# 429'd in practice (observed live). A cache shared by both routes cuts
# that to one fetch per TTL window regardless of poll frequency or how
# many browser tabs are open. TTL is adaptive (webapp.scheduler.compute_adaptive_interval_seconds)
# — the same "how urgent is this right now" question the background
# scheduler answers for its own poll cadence, reused here rather than a
# second hardcoded constant. Starts at RAMP_INTERVAL_SECONDS before the
# first successful fetch, since there's no event data yet to reason from.
_calendar_cache = {
    "events": None, "fetched_at": 0.0, "ttl_seconds": RAMP_INTERVAL_SECONDS,
    "last_attempt_at": 0.0, "last_error": None,
}

# How long to back off after a FAILED fetch before attempting the live feed
# again. Distinct from ttl_seconds above (which only advances on success) —
# without this, a failure left fetched_at untouched, so with no successful
# fetch ever recorded, every single incoming request would immediately
# retry the live feed with zero cooldown: observed live, a 429 that never
# got a chance to clear because every dashboard poll kept re-triggering it.
FAILED_FETCH_BACKOFF_SECONDS = RAMP_INTERVAL_SECONDS


def _get_cached_events(now_fn=time.monotonic):
    """
    Shared cache for the two routes below. Raises whatever
    fetch_calendar()/filter_relevant_events() raises on a cache miss —
    callers already handle that by degrading to an empty list plus an
    error field, so a real fetch failure still surfaces as "stale." On a
    fresh failure, re-raises the SAME cached error for
    FAILED_FETCH_BACKOFF_SECONDS instead of re-attempting the live fetch
    on every request during that window (see FAILED_FETCH_BACKOFF_SECONDS).
    `now_fn` is injectable so tests can control elapsed time without
    monkeypatching the global `time` module (which Flask/Werkzeug
    internals may also call).
    """
    now = now_fn()
    if _calendar_cache["events"] is not None and (now - _calendar_cache["fetched_at"]) < _calendar_cache["ttl_seconds"]:
        return _calendar_cache["events"]

    if _calendar_cache["last_error"] is not None and (now - _calendar_cache["last_attempt_at"]) < FAILED_FETCH_BACKOFF_SECONDS:
        raise _calendar_cache["last_error"]

    _calendar_cache["last_attempt_at"] = now
    try:
        events = filter_relevant_events(fetch_calendar("thisweek"), min_impact="Medium")
    except Exception as exc:  # noqa: BLE001 — cached and re-raised, callers already degrade gracefully
        _calendar_cache["last_error"] = exc
        raise
    _calendar_cache["events"] = events
    _calendar_cache["fetched_at"] = now
    _calendar_cache["ttl_seconds"] = compute_adaptive_interval_seconds(events)
    _calendar_cache["last_error"] = None
    return events


def _ensure_defaults() -> None:
    conn = get_connection()
    if not list_tracked_symbols(conn):
        for symbol in DEFAULT_SYMBOLS:
            add_tracked_symbol(conn, symbol)
    conn.close()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/symbols", methods=["GET"])
def get_symbols():
    conn = get_connection()
    symbols = list_tracked_symbols(conn)
    conn.close()
    return jsonify([
        {"symbol": s.symbol, "symbol_class": s.symbol_class, "usd_relationship": s.usd_relationship}
        for s in (classify_symbol(sym) for sym in symbols)
    ])


# CSRF note on the two state-changing routes below (POST/DELETE /api/symbols):
# no CSRF token, because there's no session/auth to bind one to (single-user,
# no login anywhere in this app). This is not an open hole today — no CORS
# headers are configured anywhere in this codebase (grep confirms it), so the
# browser's own same-origin policy already blocks a cross-site page's fetch()
# from completing a JSON POST here (it requires a preflight this server never
# answers with Access-Control-Allow-Origin), and DELETE isn't issuable by a
# plain HTML <form> at all. If real auth is ever added, revisit this — a
# session existing is what would make a token-based CSRF defense meaningful,
# not the other way around.
@app.route("/api/symbols", methods=["POST"])
def add_symbol():
    data = request.get_json(silent=True) or {}
    ticker = (data.get("ticker") or "").strip().upper()
    if not ticker:
        return jsonify({"error": "ticker is required"}), 400
    try:
        symbol_class = classify_symbol(ticker)
    except UnrecognizedSymbolError as exc:
        return jsonify({"error": str(exc)}), 400

    conn = get_connection()
    add_tracked_symbol(conn, symbol_class.symbol)
    conn.close()
    return jsonify({
        "symbol": symbol_class.symbol,
        "symbol_class": symbol_class.symbol_class,
        "usd_relationship": symbol_class.usd_relationship,
    }), 201


@app.route("/api/symbols/<ticker>", methods=["DELETE"])
def remove_symbol(ticker: str):
    conn = get_connection()
    remove_tracked_symbol(conn, ticker.strip().upper())
    conn.close()
    return "", 204


@app.route("/api/calendar", methods=["GET"])
def get_calendar():
    try:
        events = _get_cached_events()
    except Exception as exc:  # noqa: BLE001 — a failed live fetch must not 500 the whole dashboard
        return jsonify({"error": f"calendar fetch failed: {exc}", "events": []}), 200
    return jsonify({
        "events": [
            {
                "title": e.title, "country": e.country, "impact": e.impact,
                "event_time_utc": e.event_time_utc.isoformat(),
                "forecast": e.forecast, "actual": e.actual,
            }
            for e in events
        ],
    })


@app.route("/api/predictions", methods=["GET"])
def get_predictions():
    conn = get_connection()
    # Separate connection to the article-based accumulator's own DB
    # (scoring/backtest_log.db), read-only here — this dashboard route
    # still computes nothing from articles itself (scoring_service.py is
    # untouched); it only displays a count the accumulator already
    # produced independently, purely for context alongside the essence-
    # only score below.
    backtest_conn = get_backtest_connection()
    symbols = list_tracked_symbols(conn)
    # Same failed-live-fetch degradation as /api/calendar (empty list, not a
    # 500) but this route was silently swallowing the exception with no way
    # for the frontend to know the event list — and therefore every score
    # below — might be stale. Surface it the same way /api/calendar does.
    error = None
    try:
        events = _get_cached_events()
    except Exception as exc:  # noqa: BLE001 — a failed live fetch must not 500 the whole dashboard
        events = []
        error = f"calendar fetch failed: {exc}"

    predictions = []
    for ticker in symbols:
        symbol_class = classify_symbol(ticker)
        entry = {"symbol": ticker, "symbol_class": symbol_class.symbol_class, "events": []}
        for event in events:
            runs = get_latest_two(conn, ticker, event.title)
            if not runs:
                continue
            latest = runs[0]
            previous = runs[1] if len(runs) > 1 else None
            accumulator_prediction = get_latest_prediction(backtest_conn, event.title, ticker)
            # The accumulator's own blind, article-based call — direction
            # and probability, not just how many articles backed it. This
            # is a REAL prediction the accumulator already made independently,
            # not derived from the essence-only score above; it can exist
            # (and disagree) even while the essence-only score is still
            # "pending," since the accumulator predicts BEFORE the event
            # resolves. Previously only article_count surfaced here, which
            # left the actual call itself invisible on the dashboard.
            article_prediction = None
            if accumulator_prediction is not None:
                article_prediction = {
                    "direction": accumulator_prediction.direction,
                    "probability": accumulator_prediction.probability,
                    "article_count": accumulator_prediction.article_count,
                }
            entry["events"].append({
                "event_title": event.title,
                "event_time_utc": event.event_time_utc.isoformat(),
                "probability": latest.probability,
                "direction": latest.direction,
                "previous_probability": previous.probability if previous else None,
                "previous_direction": previous.direction if previous else None,
                "article_count": accumulator_prediction.article_count if accumulator_prediction else None,
                "article_prediction": article_prediction,
            })

        # A resolved score always outranks a still-pending one, regardless
        # of which is chronologically closer — a real BUY/SELL/HOLD call is
        # more useful to show than an "awaiting" placeholder for a nearer
        # event (confirmed: this is a deliberate product choice, not just a
        # same-timestamp tie-break — release days routinely publish several
        # sub-metrics at the IDENTICAL time, e.g. Core CPI m/m, Core CPI y/y,
        # CPI m/m, CPI y/y all at 12:30 UTC, and a naive proximity-only sort
        # would let a still-pending sibling, or even a pending event on an
        # entirely different day, mask one that has actually scored).
        # Within each group (resolved / pending), proximity to now breaks ties.
        now = dt.datetime.now(dt.timezone.utc)
        entry["events"].sort(
            key=lambda ev: (
                ev["direction"] == "pending",
                abs((dt.datetime.fromisoformat(ev["event_time_utc"]) - now).total_seconds()),
            )
        )
        predictions.append(entry)

    conn.close()
    backtest_conn.close()
    return jsonify({"predictions": predictions, "error": error})


@app.route("/api/predictions/<symbol>/history", methods=["GET"])
def get_prediction_history(symbol: str):
    event_title = request.args.get("event_title", "")
    conn = get_connection()
    runs = get_history(conn, symbol.strip().upper(), event_title)
    conn.close()
    return jsonify([
        {"scored_at_utc": r.scored_at_utc, "probability": r.probability, "direction": r.direction}
        for r in runs
    ])


def _get_tracked_symbols() -> list[str]:
    conn = get_connection()
    try:
        return list_tracked_symbols(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    _ensure_defaults()
    start_scheduler(_get_tracked_symbols)
    app.run(port=5001, debug=False)
