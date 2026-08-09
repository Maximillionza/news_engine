"""
Flask API for the symbol impact dashboard — serves tracked symbols,
calendar events, and current/previous predictions to the frontend in
webapp/static/. Does not do any scoring itself; that's webapp/scheduler.py's
job, running in a background thread started at app startup.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, send_from_directory

from data_layer.calendar_feed import fetch_calendar, filter_relevant_events
from webapp.scheduler import start_scheduler
from webapp.store import (
    get_connection, get_latest_two, get_history,
    add_tracked_symbol, remove_tracked_symbol, list_tracked_symbols,
)
from webapp.symbols import classify_symbol, UnrecognizedSymbolError

app = Flask(__name__, static_folder="static")

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
        events = filter_relevant_events(fetch_calendar("thisweek"))
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
    symbols = list_tracked_symbols(conn)
    try:
        events = filter_relevant_events(fetch_calendar("thisweek"))
    except Exception:
        events = []

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
            entry["events"].append({
                "event_title": event.title,
                "event_time_utc": event.event_time_utc.isoformat(),
                "probability": latest.probability,
                "direction": latest.direction,
                "previous_probability": previous.probability if previous else None,
                "previous_direction": previous.direction if previous else None,
            })
        predictions.append(entry)

    conn.close()
    return jsonify(predictions)


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


if __name__ == "__main__":
    _ensure_defaults()
    start_scheduler(lambda: list_tracked_symbols(get_connection()))
    app.run(port=5001, debug=False)
