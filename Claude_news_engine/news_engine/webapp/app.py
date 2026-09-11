"""
Flask API for the symbol impact dashboard — serves tracked symbols,
calendar events, and current/previous predictions to the frontend in
webapp/static/. Does not do any scoring itself; that's webapp/scheduler.py's
job, running in a background thread started at app startup.
"""
from __future__ import annotations

import sys
import os
import logging
import datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_from_directory

from data_layer.calendar_feed import get_last_successful_fetch_age_seconds
from webapp.scheduler import start_scheduler
from webapp.actuals_sync import start_actuals_sync
from webapp.store import (
    get_connection, get_latest_two, get_history,
    add_tracked_symbol, remove_tracked_symbol, list_tracked_symbols,
    get_calendar_snapshot, get_event_history,
    get_macro_calendar_events,
)
from webapp.trend import summarize_trend
from webapp.history import build_print_call_history
from webapp.symbols import classify_symbol, UnrecognizedSymbolError
from scoring.backtest_store import (
    get_connection as get_backtest_connection, get_latest_two_predictions,
    get_latest_print_prediction, get_latest_kalshi_read,
    # Aliased — webapp/app.py already has its own route handler FUNCTION
    # named get_prediction_history() (the essence-only one, further down
    # this file) which would otherwise shadow this import at module scope.
    get_prediction_history as get_article_prediction_history,
)
from webapp.predictions_service import build_predictions_payload, _print_prediction_dict

app = Flask(__name__, static_folder="static")

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ["XAUUSD", "US30"]


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
    # No live fetch here at all — webapp/scheduler.py's background loop is
    # the SOLE calendar fetcher (see its module docstring); this route just
    # reads whatever it last persisted, instantly, regardless of the live
    # feed's health right now. `error` here means "nothing has ever been
    # fetched successfully yet" (fresh install, scheduler hasn't completed
    # its first cycle) — not "a live request just failed," since no live
    # request happens in this code path anymore.
    conn = get_connection()
    snapshot = get_calendar_snapshot(conn)
    conn.close()
    # R6 (docs/calendar-feed-staleness-policy.md): how long since anything
    # last talked to FF, regardless of tracked-symbol/prediction state —
    # None if no fetch attempt has ever been recorded on this machine.
    feed_staleness_seconds = get_last_successful_fetch_age_seconds()
    if snapshot is None:
        return jsonify({
            "error": "Calendar data not yet available — waiting for the first background fetch.",
            "events": [], "fetched_at_utc": None, "feed_staleness_seconds": feed_staleness_seconds,
        })
    return jsonify({
        "events": snapshot.events, "fetched_at_utc": snapshot.fetched_at_utc,
        "feed_staleness_seconds": feed_staleness_seconds,
    })


@app.route("/api/event_history", methods=["GET"])
def get_event_history_route():
    title = request.args.get("title", "")
    conn = get_connection()
    rows = get_event_history(conn, title)
    conn.close()
    return jsonify({
        "occurrences": [
            {
                "event_time_utc": r.event_time_utc, "forecast": r.forecast,
                "previous": r.previous, "actual": r.actual, "surprise_direction": r.surprise_direction,
            }
            for r in rows
        ],
        "trend_summary": summarize_trend(rows),
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
    try:
        payload = build_predictions_payload(conn, backtest_conn)
    finally:
        conn.close()
        backtest_conn.close()
    return jsonify(payload)


@app.route("/api/calendar/monthahead", methods=["GET"])
def get_calendar_month_ahead():
    """
    Macro/micro merged calendar view (docs/macro-calendar-design-2026-08-16.md):
    Forex Factory's persisted calendar_snapshot ("micro lens" — exact,
    near-term) plus webapp.store's macro_calendar table ("macro view" —
    FRED-sourced, month-ahead, estimated) for any (title, date) FF
    doesn't have yet. Display-only — this route computes nothing that
    feeds scoring; it exists purely so the Calendar tab can show the rest
    of the month FF's own "thisweek" feed hasn't populated.

    Every returned event carries "estimated": true/false so the frontend
    can render macro-only entries distinctly (e.g. a hollow/dashed dot)
    from FF-confirmed ones. A macro row already covered by a real FF
    event at the same (title, date) is skipped — FF is always the
    higher-trust source once it has the occurrence.
    """
    conn = get_connection()
    snapshot = get_calendar_snapshot(conn)
    ff_events = snapshot.events if snapshot is not None else []
    ff_keys = {(e["title"], e["event_time_utc"][:10]) for e in ff_events}

    today = dt.date.today()
    horizon = today + dt.timedelta(days=35)
    macro_rows = get_macro_calendar_events(conn, today.isoformat(), horizon.isoformat())
    conn.close()

    merged = [{**e, "estimated": False} for e in ff_events]
    for row in macro_rows:
        if (row.event_title, row.event_date) in ff_keys:
            continue  # FF already has this occurrence — it's the higher-trust source, skip the macro duplicate
        display_time = row.display_time_utc or f"{row.event_date}T00:00:00+00:00"
        merged.append({
            "title": row.event_title,
            "country": "USD",
            "impact": None,  # macro rows don't carry FF's impact tag — never fabricated
            "event_time_utc": display_time,
            "forecast": None, "previous": None, "actual": None,
            "estimated": row.confirmed_event_time_utc is None,
            "source": "fred_macro",
        })

    merged.sort(key=lambda e: e["event_time_utc"])
    return jsonify({"events": merged, "ff_fetched_at_utc": snapshot.fetched_at_utc if snapshot is not None else None})


@app.route("/api/calendar/date/<date_str>", methods=["GET"])
def get_calendar_for_date(date_str: str):
    """
    Every event on this exact calendar date, each with every tracked
    symbol's CURRENT call for it — the essence-only score plus the
    article- and print-based accumulator calls, same three read-only
    sources /api/predictions already reads, filtered down to this one
    date (not a new scoring path). date_str is YYYY-MM-DD.
    """
    try:
        target_date = dt.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400

    conn = get_connection()
    backtest_conn = get_backtest_connection()
    snapshot = get_calendar_snapshot(conn)
    all_events = snapshot.events if snapshot is not None else []
    day_events = [e for e in all_events if dt.datetime.fromisoformat(e["event_time_utc"]).date() == target_date]

    # Macro-view (FRED) rows for this exact date not already covered by a
    # real FF event — same "FF always wins once it has the occurrence"
    # rule /api/calendar/monthahead uses. These carry no `calls` (macro
    # rows aren't instrument-scored — see docs/macro-calendar-design-2026-08-16.md,
    # scoring stays untouched) so the frontend can render them as a
    # simple "estimated" entry rather than a full prediction panel.
    ff_titles_this_date = {e["title"] for e in day_events}
    macro_rows = [
        r for r in get_macro_calendar_events(conn, date_str, date_str)
        if r.event_title not in ff_titles_this_date
    ]

    symbols = list_tracked_symbols(conn)
    result_events = []
    for event in day_events:
        event_time = dt.datetime.fromisoformat(event["event_time_utc"])
        calls = {}
        for ticker in symbols:
            runs = get_latest_two(conn, ticker, event["title"])
            latest = runs[0] if runs else None

            # Same accumulator read as /api/predictions (Task 7's pattern)
            # — a real, independently-made article-based call, not derived
            # from the essence-only score above.
            accumulator_runs = get_latest_two_predictions(backtest_conn, event["title"], ticker)
            accumulator_prediction = accumulator_runs[0] if accumulator_runs else None
            article_prediction = None
            if accumulator_prediction is not None:
                article_prediction = {
                    "direction": accumulator_prediction.direction,
                    "probability": accumulator_prediction.probability,
                    "article_count": accumulator_prediction.article_count,
                }

            print_call = get_latest_print_prediction(backtest_conn, event["title"], event_time)
            print_prediction = None
            if print_call is not None:
                print_prediction = _print_prediction_dict(print_call)

            if latest is None and article_prediction is None and print_prediction is None:
                calls[ticker] = None
            else:
                calls[ticker] = {
                    "direction": latest.direction if latest else None,
                    "probability": latest.probability if latest else None,
                    "article_prediction": article_prediction,
                    "print_prediction": print_prediction,
                }

        result_events.append({
            "title": event["title"], "event_time_utc": event["event_time_utc"],
            "impact": event.get("impact"), "forecast": event.get("forecast"),
            "previous": event.get("previous"), "actual": event.get("actual"),
            "calls": calls, "estimated": False,
        })

    for row in macro_rows:
        result_events.append({
            "title": row.event_title,
            "event_time_utc": row.display_time_utc or f"{row.event_date}T00:00:00+00:00",
            "impact": None, "forecast": None, "previous": None, "actual": None,
            "calls": {}, "estimated": row.confirmed_event_time_utc is None,
        })

    conn.close()
    backtest_conn.close()
    return jsonify({"events": result_events})


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


@app.route("/api/predictions/<symbol>/article_history", methods=["GET"])
def get_article_prediction_history_route(symbol: str):
    """
    The full recorded progression of the ARTICLE-based accumulator's calls
    for this (symbol, event_title) pair (2026-08-17's "why did this call
    change" feature) — every material-change snapshot, most recent first,
    each carrying its own top_contributions. This is the "flip the card
    over" data: e.g. 51% indecisive -> 52% Sell, with the top-3 articles
    that drove each step. Distinct from /history above, which is the
    essence-only (no-articles) score's progression — a different pipeline
    entirely (see webapp/scheduler.py's module docstring).
    """
    event_title = request.args.get("event_title", "")
    if not event_title:
        return jsonify({"error": "event_title is required"}), 400
    backtest_conn = get_backtest_connection()
    runs = get_article_prediction_history(backtest_conn, event_title, symbol.strip().upper())
    backtest_conn.close()
    return jsonify({
        "progression": [
            {
                "scored_at_utc": r.scored_at_utc, "probability": r.probability, "direction": r.direction,
                "article_count": r.article_count, "top_contributions": r.top_contributions,
            }
            for r in runs
        ],
    })


@app.route("/api/history", methods=["GET"])
def get_print_call_history():
    rows = build_print_call_history()
    return jsonify({
        "rows": [
            {
                "event_title": r.event_title, "event_time_utc": r.event_time_utc,
                "instrument": r.instrument,
                "previous": r.previous, "forecast": r.forecast, "actual": r.actual,
                "unchanged_vs_previous": r.unchanged_vs_previous,
                "ne_prediction": r.ne_prediction, "ne_confidence": r.ne_confidence,
                "outcome": r.outcome, "unjudged_reason": r.unjudged_reason,
                "source": r.source,
            }
            for r in rows
        ],
    })


def _get_tracked_symbols() -> list[str]:
    conn = get_connection()
    try:
        return list_tracked_symbols(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    # webapp/scheduler.py's background thread (started below) logs
    # non-ASCII characters (e.g. the ⚠ in ProbabilityResult.summary) —
    # Windows' default console codepage (cp1252) can't encode those and
    # raises UnicodeEncodeError on print(), which reached this app once
    # this session (confirmed live 2026-08-19, same root cause as
    # scripts/run_accumulator.py's identical crash). reconfigure() (3.7+)
    # forces real UTF-8 on stdout/stderr regardless of the console's
    # codepage; errors="replace" so a still-unencodable character prints
    # a placeholder instead of crashing the process outright.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    _ensure_defaults()
    start_scheduler(_get_tracked_symbols)
    start_actuals_sync()
    # dashboard-review-2026-09-11.md: Flask's own dev server is
    # single-threaded by default and shares this process with the
    # scheduler + actuals-sync background threads, all contending for
    # SQLite file locks — not meant for anything beyond local
    # development. waitress is a real, pure-Python WSGI server (no
    # platform-specific build step, matters on Windows) and threads
    # requests by default, so one slow request no longer blocks every
    # other tab/poll hitting this same process.
    from waitress import serve
    serve(app, host="127.0.0.1", port=5001)
