"""
B8 (2026-10-27) standardized surprise (roadmap §B8 U3): each USD surprise is
measured against that indicator's own typical miss, so NFP, CPI and claims
become comparable. A 6K claims miss and a 0.1 CPI miss used to be scored as
percents of the forecast (2.7% vs 33%); in sigmas of their own history they
are both about one typical miss.

sigma = sample standard deviation of the last SURPRISE_SIGMA_MAX_HISTORY
(24) PRIOR surprises (actual - forecast, data_layer.calendar_feed._parse_numeric
units) of the same title. Rules, all deliberate:
  - prior only: julianday(event_time_utc) strictly before the release being
    scored, so the release itself and anything later can never leak in;
  - USD only: country = 'USD' strictly (a NULL/unknown or foreign row is
    never part of a USD sigma — same rule as get_precursor_events_for);
  - rows need both a forecast and an actual; FRED-seeded rows (forecast
    NULL) and unparseable values ("N/A") are skipped, never guessed;
  - fewer than MIN_PRIOR_SURPRISES_FOR_SIGMA (6) usable priors -> None, and
    usd_surprise_score() keeps the percent method;
  - floor of one rounding step of the forecast (calendar_feed.tick_of:
    "0.3%" -> 0.1, "225K" -> 1000), so a run of exact hits cannot make the
    next 0.1 miss look like 5 sigma.

Read-only: nothing here writes. Used by the dashboard essence calls
(webapp/scheduler.py, webapp/predictions_service.py) and precursor
contributions (scoring/probability_engine.get_precursor_events_for). Stats
(webapp/stats_service.py) and classify_surprise() (the grading truth) do not
use it.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import logging
import sqlite3
import statistics
from typing import Optional

from config.settings import (
    EVENT_SURPRISE_DIRECTION,
    MIN_PRIOR_SURPRISES_FOR_SIGMA,
    SURPRISE_SIGMA_MAX_HISTORY,
)
from data_layer.calendar_feed import EconomicEvent, _parse_numeric, tick_of

logger = logging.getLogger(__name__)


def prior_surprises(
    conn: sqlite3.Connection,
    title: str,
    before_utc: dt.datetime,
    limit: int = SURPRISE_SIGMA_MAX_HISTORY,
) -> list[float]:
    """
    actual - forecast for the most recent `limit` parseable USD rows of
    `title` strictly before `before_utc`, newest first. julianday() compares
    instants, not strings, so a row stored with another UTC offset is still
    ordered correctly. Unparseable rows are skipped before the cap is applied.
    """
    rows = conn.execute(
        "SELECT forecast, actual FROM event_history "
        "WHERE event_title = ? AND country = 'USD' AND forecast IS NOT NULL AND actual IS NOT NULL "
        "AND julianday(event_time_utc) < julianday(?) "
        "ORDER BY julianday(event_time_utc) DESC",
        (title, before_utc.isoformat()),
    ).fetchall()
    surprises: list[float] = []
    for forecast_text, actual_text in rows:
        forecast = _parse_numeric(forecast_text)
        actual = _parse_numeric(actual_text)
        if forecast is None or actual is None:
            continue
        surprises.append(actual - forecast)
        if len(surprises) >= limit:
            break
    return surprises


def surprise_sigma(prior: list[float], forecast_text: Optional[str]) -> Optional[float]:
    """
    Sample stdev of `prior`, floored at one rounding step of this release's
    forecast. None below MIN_PRIOR_SURPRISES_FOR_SIGMA priors, or when the
    result is not > 0 (all exact hits and no parseable forecast to floor on).
    """
    if len(prior) < MIN_PRIOR_SURPRISES_FOR_SIGMA:
        return None
    sigma = max(statistics.stdev(prior), tick_of(forecast_text) or 0.0)
    return sigma if sigma > 0 else None


def sigma_for_event(conn: sqlite3.Connection, event: EconomicEvent) -> Optional[float]:
    """None for a non-USD event or a title with no EVENT_SURPRISE_DIRECTION entry (it is never scored)."""
    if event.country != "USD" or event.title not in EVENT_SURPRISE_DIRECTION:
        return None
    return surprise_sigma(prior_surprises(conn, event.title, event.event_time_utc), event.forecast)


def with_surprise_sigma(conn: sqlite3.Connection, event: EconomicEvent) -> EconomicEvent:
    """
    A copy of `event` with surprise_sigma attached. Fails open: any error
    (closed connection, locked DB, bad row) is logged and the event is
    returned unchanged, so scoring falls back to the percent method rather
    than losing the call.
    """
    try:
        return dataclasses.replace(event, surprise_sigma=sigma_for_event(conn, event))
    except Exception:  # noqa: BLE001 — fail open to today's method, never cost a call
        logger.warning("surprise sigma lookup failed for %r, using the percent method", event.title, exc_info=True)
        return event


if __name__ == "__main__":
    # Worked example on a temp DB, from the app dir: python -m scoring.surprise_scale
    import tempfile
    from pathlib import Path

    from webapp.store import get_connection, insert_event_history_if_absent

    release = dt.datetime(2026, 10, 22, 12, 30, tzinfo=dt.timezone.utc)
    priors = [("225K", "215K"), ("220K", "215K"), ("202K", "209K"), ("210K", "206K"), ("208K", "203K"), ("205K", "206K")]
    with tempfile.TemporaryDirectory() as tmp:
        conn = get_connection(Path(tmp) / "example.db")
        for k, (f, a) in enumerate(priors, start=1):
            when = release - dt.timedelta(days=7 * k)
            insert_event_history_if_absent(conn, "Unemployment Claims", when, f, None, a, None, "live", "Medium", "USD", when)
        claims = EconomicEvent("Unemployment Claims", "USD", "Medium", release, forecast="225K", actual="219K")
        scaled = with_surprise_sigma(conn, claims)
        print(f"sigma {scaled.surprise_sigma:.2f}; percent score {claims.usd_surprise_score():.6f}; "
              f"standardized score {scaled.usd_surprise_score():.6f}")
        conn.close()
