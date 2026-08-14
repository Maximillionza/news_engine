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
from typing import Optional
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_from_directory

from config.settings import EVENT_SURPRISE_DIRECTION, INSTRUMENTS
from webapp.scheduler import start_scheduler
from webapp.store import (
    get_connection, get_latest_two, get_history,
    add_tracked_symbol, remove_tracked_symbol, list_tracked_symbols,
    get_calendar_snapshot, get_event_history,
)
from webapp.trend import summarize_trend, compute_trend_signal, MIN_CONFIRMED_ROWS_FOR_A_TREND
from webapp.history import build_print_call_history
from webapp.symbols import classify_symbol, UnrecognizedSymbolError
from scoring.backtest_store import (
    get_connection as get_backtest_connection, get_latest_two_predictions,
    get_latest_print_prediction, get_latest_kalshi_read,
)

app = Flask(__name__, static_folder="static")

DEFAULT_SYMBOLS = ["XAUUSD", "US30"]


def _trend_instrument_lean(event_title: str, trend_direction: str, instrument: str) -> Optional[str]:
    """
    Translates a trend streak's raw forecast-relative direction ('higher'/
    'lower') into a USD-bullish/bearish/neutral lean for THIS instrument —
    same EVENT_SURPRISE_DIRECTION + usd_relationship mapping score_bundle()
    uses internally, reimplemented here at display-only granularity (no
    score_bundle() call, no scoring-math change). Returns None — never
    fabricated — when event_title has no EVENT_SURPRISE_DIRECTION entry.
    """
    surprise_mapping = EVENT_SURPRISE_DIRECTION.get(event_title)
    if surprise_mapping is None:
        return None
    # surprise_mapping is 'higher_bullish' or 'higher_bearish' — the sign
    # this event's "higher than forecast" carries for USD.
    higher_is_usd_bullish = surprise_mapping == "higher_bullish"
    usd_bullish = higher_is_usd_bullish if trend_direction == "higher" else not higher_is_usd_bullish

    relationship = INSTRUMENTS[instrument]["usd_relationship"]
    if relationship == "inverse":
        instrument_bullish = not usd_bullish
    elif relationship == "direct":
        instrument_bullish = usd_bullish
    elif relationship == "risk_sentiment":
        instrument_bullish = not usd_bullish  # dovish/USD-bearish -> risk-on -> equity-bullish, same simplification score_bundle() uses
    else:
        return None
    return "bullish" if instrument_bullish else "bearish"


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
    if snapshot is None:
        return jsonify({"error": "Calendar data not yet available — waiting for the first background fetch.", "events": [], "fetched_at_utc": None})
    return jsonify({"events": snapshot.events, "fetched_at_utc": snapshot.fetched_at_utc})


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
    symbols = list_tracked_symbols(conn)
    # No live fetch here either — same reasoning as /api/calendar. `error`
    # means "nothing persisted yet," not "a live request just failed."
    snapshot = get_calendar_snapshot(conn)
    events = snapshot.events if snapshot is not None else []
    error = None if snapshot is not None else "Calendar data not yet available — waiting for the first background fetch."

    predictions = []
    for ticker in symbols:
        symbol_class = classify_symbol(ticker)
        entry = {"symbol": ticker, "symbol_class": symbol_class.symbol_class, "events": []}
        for event in events:
            runs = get_latest_two(conn, ticker, event["title"])
            latest = runs[0] if runs else None
            previous = runs[1] if len(runs) > 1 else None
            # The accumulator's own blind, article-based call — direction
            # and probability, not just how many articles backed it. This
            # is a REAL prediction the accumulator already made independently,
            # not derived from the essence-only score above; it can exist
            # (and disagree) even while the essence-only score is still
            # "pending," since the accumulator predicts BEFORE the event
            # resolves. Previously only article_count surfaced here, which
            # left the actual call itself invisible on the dashboard.
            #
            # Two rows, not one: scoring/backtest_accumulator.py only
            # RECORDS a snapshot on a material change (direction flip, or a
            # same-direction move past its threshold) — so unlike the
            # essence-only score's every-cycle rows, any two consecutive
            # article predictions represent a genuine shift, not noise.
            # That's exactly what the frontend's diff strip needs.
            accumulator_runs = get_latest_two_predictions(backtest_conn, event["title"], ticker)
            accumulator_prediction = accumulator_runs[0] if accumulator_runs else None
            accumulator_previous = accumulator_runs[1] if len(accumulator_runs) > 1 else None
            article_prediction = None
            if accumulator_prediction is not None:
                article_prediction = {
                    "direction": accumulator_prediction.direction,
                    "probability": accumulator_prediction.probability,
                    "article_count": accumulator_prediction.article_count,
                }
            previous_article_prediction = None
            if accumulator_previous is not None:
                previous_article_prediction = {
                    "direction": accumulator_previous.direction,
                    "probability": accumulator_previous.probability,
                    "article_count": accumulator_previous.article_count,
                }
            print_call = get_latest_print_prediction(
                backtest_conn, event["title"], dt.datetime.fromisoformat(event["event_time_utc"]),
            )
            print_prediction = None
            if print_call is not None:
                print_prediction = {"direction": print_call.predicted_vs_forecast, "confidence": print_call.confidence}

            # Two more independently-computed signals, same read-only
            # pattern as article_prediction/print_prediction above.
            # compute_trend_signal() requires its input pre-filtered to
            # confirmed (non-None surprise_direction) rows and non-empty
            # (see webapp/trend.py's docstring) — unlike
            # scoring/backtest_accumulator.py's live-scoring caller, this
            # is a mere display, so no MIN_OCCURRENCES_FOR_TREND_PRIOR
            # gate is applied here. It DOES apply the same
            # MIN_CONFIRMED_ROWS_FOR_A_TREND floor summarize_trend() uses,
            # though — this is the one place a user actually sees the
            # numeric strength, and with exactly 1 confirmed row
            # _analyze_trend()'s tally branch saturates strength at 1.0
            # (maximum conviction from a single data point), same failure
            # summarize_trend() already guards against.
            event_time = dt.datetime.fromisoformat(event["event_time_utc"])
            prior_occurrences = get_event_history(conn, event["title"])
            confirmed_occurrences = [r for r in prior_occurrences if r.surprise_direction is not None]
            trend = (
                compute_trend_signal(confirmed_occurrences)
                if len(confirmed_occurrences) >= MIN_CONFIRMED_ROWS_FOR_A_TREND
                else None
            )
            trend_signal = None
            if trend is not None:
                trend_signal = {
                    "direction": trend.direction, "strength": trend.strength,
                    "instrument_lean": _trend_instrument_lean(event["title"], trend.direction, ticker),
                }

            kalshi_row = get_latest_kalshi_read(backtest_conn, event["title"], event_time)
            kalshi_read = None
            if kalshi_row is not None:
                kalshi_read = {
                    "implied_direction": kalshi_row.implied_direction,
                    "implied_probability": kalshi_row.implied_probability,
                    "open_interest": kalshi_row.open_interest,
                }

            # An event is only worth including in this symbol's list at
            # all if SOME layer has something to say about it — an event
            # with zero essence score AND zero article prediction AND zero
            # print call AND zero trend signal AND zero Kalshi read is
            # genuinely nothing-yet, same as before (extended here so
            # Task 9's two new signals can't be silently dropped by a
            # guard that never learned about them).
            if (latest is None and article_prediction is None and print_prediction is None
                    and trend_signal is None and kalshi_read is None):
                continue

            entry["events"].append({
                "event_title": event["title"],
                "event_time_utc": event["event_time_utc"],
                "probability": latest.probability if latest else None,
                "direction": latest.direction if latest else "pending",
                "previous_probability": previous.probability if previous else None,
                "previous_direction": previous.direction if previous else None,
                "article_count": accumulator_prediction.article_count if accumulator_prediction else None,
                "article_prediction": article_prediction,
                "previous_article_prediction": previous_article_prediction,
                "print_prediction": print_prediction,
                "trend_signal": trend_signal,
                "kalshi_read": kalshi_read,
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
        #
        # Within the pending group specifically, a genuinely UPCOMING event
        # outranks one whose release time already passed but is still stuck
        # "pending" (observed live: the calendar feed can lag publishing an
        # actual for hours after the scheduled time) — abs(distance) alone
        # treats "6h48m ago, stuck" as closer than "11h from now, upcoming"
        # and would keep showing the stale event long after a real next
        # event exists to show instead.
        now = dt.datetime.now(dt.timezone.utc)
        entry["events"].sort(
            key=lambda ev: (
                ev["direction"] == "pending",
                ev["direction"] == "pending" and dt.datetime.fromisoformat(ev["event_time_utc"]) < now,
                abs((dt.datetime.fromisoformat(ev["event_time_utc"]) - now).total_seconds()),
            )
        )
        predictions.append(entry)

    conn.close()
    backtest_conn.close()
    return jsonify({"predictions": predictions, "error": error})


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
                print_prediction = {"direction": print_call.predicted_vs_forecast, "confidence": print_call.confidence}

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
            "calls": calls,
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
    _ensure_defaults()
    start_scheduler(_get_tracked_symbols)
    app.run(port=5001, debug=False)
