# webapp/tier1_formula.py
"""
Formula-tier Tier 1 calls (B3 T5): the CPI-family pre-release call is a deterministic rule on the Cleveland
Fed nowcast, not researched by hand. The rule is the Stats tab's own surprise test: the nowcast vs the
forecast with a tolerance of one rounding step of the forecast's precision -> hotter / in line / cooler,
then per instrument through stats_methods.market_lean (buy -> bullish, sell -> bearish, mixed -> neutral).

Everything here is pure except record_formula_calls, which appends to tier1_predictions. It writes at most
one row per (title, release, instrument) per distinct (nowcast, forecast text): every capture run has a new
as-of, so a naive writer would add a row per run, and a revised forecast can flip the side under an unchanged
nowcast. No readable forecast -> nothing is written (never a guessed neutral).
"""
from __future__ import annotations

import datetime as dt
import re
import sqlite3
from typing import Optional

from config.settings import LOCAL_TZ
from data_layer.tier1_events import TIER1_FORMULA_CONFIDENCE, TIER1_FORMULA_SOURCE
from scoring.backtest_store import get_latest_tier1_prediction_for_occurrence, record_tier1_prediction
from webapp.stats_methods import market_lean
from webapp.stats_rules import parse_number, side, tolerance

SIDE_LABELS = {1: "hotter than forecast", 0: "in line with forecast", -1: "cooler than forecast"}
_LEAN_TO_DIRECTION = {"buy": "bullish", "sell": "bearish", "mixed": "neutral"}
# The stored value text starts with the nowcast at 4 decimals, then the forecast text up to ": <side label> (";
# these read both back for the dedupe.
_NOWCAST_IN_TEXT = re.compile(r"^Cleveland Fed nowcast (-?\d+\.\d{4})% vs forecast ")
SIDE_LABEL_ALTERNATION = "|".join(re.escape(label) for label in SIDE_LABELS.values())
_NOWCAST_KEY_IN_TEXT = re.compile(
    r"^Cleveland Fed nowcast (-?\d+\.\d{4})% vs forecast (.*): (?:" + SIDE_LABEL_ALTERNATION + r") \(",
    re.DOTALL)
NO_FORECAST = "no readable forecast yet"


def surprise_side(nowcast: float, forecast_text: Optional[str]) -> Optional[int]:
    """+1 hotter, 0 in line, -1 cooler vs the forecast; None when the forecast is missing or unreadable."""
    forecast = parse_number(forecast_text)
    tol = tolerance(forecast_text)
    if forecast is None or tol is None:
        return None
    return side(nowcast, forecast, tol)


def formula_direction(event_title: str, side: int, symbol: str) -> str:
    """bullish / bearish / neutral for one instrument (gold inverse, US30 risk sentiment, USDJPY direct)."""
    return _LEAN_TO_DIRECTION[market_lean(event_title, side, symbol)]


def formula_value_text(nowcast: float, forecast_text: str, side: int, value_date: dt.date,
                       captured_at_utc: dt.datetime) -> str:
    """The stored Tier 1 value: what the rule compared, its verdict, and when (SAST) - readable on the dashboard."""
    return (f"Cleveland Fed nowcast {nowcast:.4f}% vs forecast {forecast_text}: {SIDE_LABELS[side]} "
            f"(Fed value dated {value_date.isoformat()}, "
            f"captured {captured_at_utc.astimezone(LOCAL_TZ):%Y-%m-%d %H:%M} SAST)")


def nowcast_in_value_text(text: str) -> Optional[float]:
    """The nowcast a formula row was written from; None for any other text (e.g. a judgment row)."""
    match = _NOWCAST_IN_TEXT.match(text or "")
    return float(match.group(1)) if match else None


def nowcast_key_in_value_text(text: str) -> Optional[tuple[float, str]]:
    """(nowcast, forecast text) a formula row was written from - the dedupe key; None for any other text."""
    match = _NOWCAST_KEY_IN_TEXT.match(text or "")
    return (float(match.group(1)), match.group(2)) if match else None


def record_formula_calls(bt_conn: Optional[sqlite3.Connection], event_title: str, release_utc: dt.datetime,
                         nowcast: float, forecast_text: Optional[str], value_date: dt.date, symbols: list[str],
                         now_utc: dt.datetime, dry_run: bool = False) -> dict:
    """
    Write the formula Tier 1 call for each tracked symbol, stamped logged_at_utc = now_utc.
    Returns {"written": [(symbol, direction)], "unchanged": [symbol], "pending": Optional[str]}.
    A symbol is "unchanged" when its latest pre-release formula row already carries this nowcast (rounded to
    the 4 decimals the text stores) against this same forecast text; a revised forecast writes a new row even
    when the nowcast has not moved, since it can change the side. A judgment row for the same occurrence does
    not count. With dry_run every symbol is reported as would-write and nothing is read or written (bt_conn
    may be None).
    """
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise ValueError(f"now_utc must be timezone-aware, got naive {now_utc!r}")
    if now_utc > release_utc:
        # Same rule as capture(): a call stamped after the print is hindsight and the as-of guard hides it.
        raise ValueError(f"now_utc {now_utc.isoformat()} is after the release {release_utc.isoformat()}")
    result: dict = {"written": [], "unchanged": [], "pending": None}
    surprise = surprise_side(nowcast, forecast_text)
    if surprise is None:
        result["pending"] = NO_FORECAST
        return result

    value = formula_value_text(nowcast, forecast_text, surprise, value_date, now_utc)
    for symbol in symbols:
        direction = formula_direction(event_title, surprise, symbol)
        if dry_run:
            result["written"].append((symbol, direction))
            continue
        latest = get_latest_tier1_prediction_for_occurrence(
            bt_conn, event_title, symbol, release_utc, source=TIER1_FORMULA_SOURCE)
        if latest is not None and nowcast_key_in_value_text(latest.value) == (round(nowcast, 4), forecast_text):
            result["unchanged"].append(symbol)
            continue
        record_tier1_prediction(
            bt_conn, event_title, symbol, release_utc, value,
            confidence=TIER1_FORMULA_CONFIDENCE, source=TIER1_FORMULA_SOURCE,
            predicted_direction=direction, logged_at_utc=now_utc,
        )
        result["written"].append((symbol, direction))
    return result
