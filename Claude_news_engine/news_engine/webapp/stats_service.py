# webapp/stats_service.py
"""
Read-only join behind the Stats tab (spec 2026-10-15 §4, §4.1, §7, §9). Writes nothing. Per-row failures
degrade to a not-scoreable row instead of breaking the page (same fail-open stance as webapp/history.py).

No lookahead: every input is the latest row stamped AT OR BEFORE the release time. Nowcast snapshots use
get_scored_nowcast_snapshot (as_of_utc <= release); print calls and accumulator predictions use
scored_at_utc <= release; hand-logged Tier 1 calls use logged_at_utc <= release. The backtest_store
"latest for occurrence" helpers are deliberately NOT used here, because they return the newest row even
if it was written after the number came out (Phase 0 found 9 such accumulator rows in the live DB).
Occurrence keys and time bounds are compared as instants via SQLite julianday(), not as strings, so an
equivalent stored form ('Z', a space separator, another offset) neither drops a row nor slips past the
bound. julianday() resolves to the millisecond, so a stamp under 1 ms after the release counts as at it.
"""
from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Callable, Optional

from config.settings import EVENT_SURPRISE_DIRECTION
from data_layer import brent_feed
from scoring.backtest_store import get_scored_nowcast_snapshot
from webapp.history import _implied_surprise_direction
from webapp.stats_methods import (
    NEWS_WEIGHT, TIER1_WEIGHT, combine, market_lean, news_lean, news_scale, news_surprise, tier1_surprise,
)
from webapp.stats_rules import judge, miss_size, parse_number, side, tolerance

logger = logging.getLogger(__name__)

NOWCAST_EVENTS = frozenset({"CPI m/m", "Core CPI m/m"})
NEWS_START_UTC = dt.datetime(2026, 8, 12, tzinfo=dt.timezone.utc)   # first article-based prediction day
MIN_SCORED_FOR_PERCENT = 20                                          # below this, accuracy % is hidden
TRACKED_SYMBOLS = ("XAUUSD", "US30")
METHODS = ("tier1", "news", "combined")
NEWS_INSTRUMENT = "XAUUSD"     # accumulator and hand-logged Tier 1 calls are read from the gold rows


@dataclass(frozen=True)
class MethodCall:
    predicted: Optional[float]
    surprise: Optional[float]
    side: Optional[int]
    verdict: Optional[str]
    miss: Optional[float]
    leans: dict[str, str] = field(default_factory=dict)
    note: Optional[str] = None      # 'hand-logged' | 'scaled' | 'news_missing'
    kind: Optional[str] = None      # 'live' | 'reconstructed' for Tier 1 snapshots


@dataclass(frozen=True)
class RowDetail:
    """
    The readings behind a row's calls, for the click-through panel and the News table (spec §5).
    Every value is one the service already computed for the calls; nothing here is scored.
    """
    forecast_text: Optional[str]
    nowcast_value: Optional[float] = None
    nowcast_as_of_utc: Optional[str] = None
    tier1_surprise: Optional[float] = None
    news_lean: Optional[float] = None           # None for a title with no surprise map (ruling 3)
    news_scale: Optional[float] = None
    news_surprise: Optional[float] = None
    combined_surprise: Optional[float] = None
    news_article_count: Optional[int] = None    # bounded print call's count, else the bounded XAUUSD prediction's
    hand_logged: Optional[dict] = None          # {"value", "confidence", "source"} of the hand-logged Tier 1 call
    weights: dict = field(default_factory=lambda: {"tier1": TIER1_WEIGHT, "news": NEWS_WEIGHT})
    # Brent crude beside the nowcast snapshot: information only, 0% weight, never part of any call.
    # None, or {"snapshot_price", "snapshot_price_date", "release_price", "release_price_date", "change_pct", "source"}.
    brent: Optional[dict] = None


@dataclass(frozen=True)
class StatsRow:
    event_title: str
    event_time_utc: dt.datetime
    forecast_text: Optional[str]
    actual_text: Optional[str]
    forecast: Optional[float]
    actual: Optional[float]
    tol: Optional[float]
    status: str                      # scored | pending | not_scoreable
    tier1_tracked: bool
    tier1: Optional[MethodCall]
    news: Optional[MethodCall]
    combined: Optional[MethodCall]
    nowcast_as_of_utc: Optional[str]
    pre_news_period: bool
    detail: Optional[RowDetail] = None


def _parse_time(value: str) -> dt.datetime:
    """Always tz-aware UTC (naive stored values are taken as UTC), as the snapshot store requires."""
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


# --- point-in-time lookups (no lookahead) ------------------------------------------------------

def _print_call_before(bt_conn: sqlite3.Connection, title: str, release_iso: str) -> Optional[sqlite3.Row]:
    return bt_conn.execute(
        "SELECT predicted_vs_forecast, confidence, article_count FROM print_predictions "
        "WHERE event_title = ? AND julianday(event_time_utc) = julianday(?) "
        "AND julianday(scored_at_utc) <= julianday(?) "
        "ORDER BY julianday(scored_at_utc) DESC, id DESC LIMIT 1",
        (title, release_iso, release_iso),
    ).fetchone()


def _accumulator_call_before(bt_conn: sqlite3.Connection, title: str, release_iso: str) -> Optional[sqlite3.Row]:
    return bt_conn.execute(
        "SELECT direction, probability, article_count FROM predictions "
        "WHERE event_title = ? AND instrument = ? AND julianday(event_time_utc) = julianday(?) "
        "AND julianday(scored_at_utc) <= julianday(?) "
        "ORDER BY julianday(scored_at_utc) DESC, id DESC LIMIT 1",
        (title, NEWS_INSTRUMENT, release_iso, release_iso),
    ).fetchone()


def _hand_logged_tier1_before(bt_conn: sqlite3.Connection, title: str, release_iso: str) -> Optional[sqlite3.Row]:
    return bt_conn.execute(
        "SELECT predicted_direction, value, confidence, source FROM tier1_predictions "
        "WHERE event_title = ? AND instrument = ? AND julianday(event_time_utc) = julianday(?) "
        "AND julianday(logged_at_utc) <= julianday(?) "
        "ORDER BY julianday(logged_at_utc) DESC, id DESC LIMIT 1",
        (title, NEWS_INSTRUMENT, release_iso, release_iso),
    ).fetchone()


# --- Brent crude beside the nowcast (information only) -------------------------------------------

class _LazySeries:
    """
    Calls the Brent lookup at most once per build_rows, and only if a row has a nowcast snapshot to
    compare against. Any failure becomes "no series": Brent is information and must never break a row.
    """

    def __init__(self, fn: Optional[Callable[[], Optional[list]]]):
        self._fn = fn
        self._done = False
        self._series: Optional[list] = None

    def __call__(self) -> Optional[list]:
        if not self._done:
            self._done = True
            try:
                fn = self._fn or brent_feed.get_brent_series     # looked up now, so a test can swap the module attr
                self._series = fn()
            except Exception:  # noqa: BLE001 -- fail open
                logger.warning("stats: Brent lookup failed", exc_info=True)
                self._series = None
        return self._series


def _brent_detail(series: Optional[list], snapshot_as_of: dt.datetime, release: dt.datetime) -> Optional[dict]:
    """
    Brent at the nowcast snapshot vs just before the release. The release price is the latest observation
    on or before the day BEFORE the release day, so neither the release day nor anything later is ever
    read; the snapshot price is capped at that same day (a snapshot taken on the release day itself must
    not see that day's price either). None when the series is missing or neither side has a price.
    """
    if not series:
        return None
    last_allowed = release.date() - dt.timedelta(days=1)
    snap = brent_feed.brent_on_or_before(series, min(snapshot_as_of.date(), last_allowed))
    rel = brent_feed.brent_on_or_before(series, last_allowed)
    if snap is None and rel is None:
        return None
    change = None
    if snap is not None and rel is not None and snap[1] != 0:
        change = round((rel[1] / snap[1] - 1.0) * 100.0, 2)
    return {
        "snapshot_price": None if snap is None else snap[1],
        "snapshot_price_date": None if snap is None else snap[0].isoformat(),
        "release_price": None if rel is None else rel[1],
        "release_price_date": None if rel is None else rel[0].isoformat(),
        "change_pct": change,
        "source": brent_feed.SOURCE_LABEL,
    }


# --- row building -----------------------------------------------------------------------------

def _call(predicted: Optional[float], surprise: Optional[float], forecast: float, tol: float,
          actual: Optional[float], title: str, note: Optional[str] = None, kind: Optional[str] = None,
          explicit_side: Optional[int] = None) -> MethodCall:
    """One method's call, judged by side vs the forecast. explicit_side is for direction-only calls."""
    if explicit_side is not None:
        predicted_side = explicit_side
    else:
        predicted_side = None if predicted is None else side(predicted, forecast, tol)
    actual_side = None if actual is None else side(actual, forecast, tol)
    leans = {} if predicted_side is None else {s: market_lean(title, predicted_side, s) for s in TRACKED_SYMBOLS}
    return MethodCall(
        predicted=predicted, surprise=surprise, side=predicted_side,
        verdict=judge(predicted_side, actual_side), miss=miss_size(predicted, actual),
        leans=leans, note=note, kind=kind,
    )


def build_rows(dash_conn: sqlite3.Connection, bt_conn: sqlite3.Connection, year: Optional[int] = None,
               month: Optional[int] = None, event_title: Optional[str] = None,
               brent_series_fn: Optional[Callable[[], Optional[list]]] = None) -> list[StatsRow]:
    """
    Every USD event_history occurrence, ascending by time. Filters are applied AFTER computing so each
    title's scale history (prior |actual - forecast|) is complete regardless of the filter.

    brent_series_fn: returns the daily Brent series [(date, price)] or None; defaults to
    data_layer.brent_feed.get_brent_series (cached, fail-open). Tests inject a stub so nothing hits the network.

    USD only (spec D2): country NULL rows are non-USD or unattributed prints that reuse US titles (e.g.
    an 01:30Z "CPI m/m"); left in, they would add bogus rows and pollute the US scale history.
    """
    raw = dash_conn.execute(
        "SELECT * FROM event_history WHERE country = 'USD' "
        "ORDER BY event_time_utc, event_title"   # UNIQUE(title, time): no duplicates
    ).fetchall()

    brent_series = _LazySeries(brent_series_fn)
    history: dict[str, list[float]] = {}
    out: list[StatsRow] = []
    for r in raw:
        title = r["event_title"]
        try:
            when = _parse_time(r["event_time_utc"])
        except (TypeError, ValueError):
            logger.warning("stats: skipping %s with unreadable time %r", title, r["event_time_utc"])
            continue
        try:
            row = _build_one(bt_conn, r, title, when, list(history.get(title, [])), brent_series)
        except Exception:  # noqa: BLE001 -- one bad row must not break the tab
            logger.warning("stats row failed for %s %s", title, when, exc_info=True)
            row = _not_scoreable(r, title, when)
        out.append(row)
        # Added only after this row is built, so the scale never sees its own (or a later) surprise.
        f, a = parse_number(r["forecast"]), parse_number(r["actual"])
        if f is not None and a is not None:
            history.setdefault(title, []).append(abs(a - f))

    def keep(row: StatsRow) -> bool:
        return ((year is None or row.event_time_utc.year == year)
                and (month is None or row.event_time_utc.month == month)
                and (event_title is None or row.event_title == event_title))
    return [row for row in out if keep(row)]


def _not_scoreable(r: sqlite3.Row, title: str, when: dt.datetime) -> StatsRow:
    return StatsRow(title, when, r["forecast"], r["actual"], None, None, None, "not_scoreable",
                    False, None, None, None, None, when < NEWS_START_UTC, RowDetail(forecast_text=r["forecast"]))


def _build_one(bt_conn: sqlite3.Connection, r: sqlite3.Row, title: str, when: dt.datetime,
               prior: list[float], brent_series: Optional[Callable[[], Optional[list]]] = None) -> StatsRow:
    forecast, actual = parse_number(r["forecast"]), parse_number(r["actual"])
    tol = tolerance(r["forecast"])
    if forecast is None or tol is None:
        return _not_scoreable(r, title, when)
    status = "pending" if actual is None else "scored"
    pre_news = when < NEWS_START_UTC
    release_iso = when.isoformat()      # already UTC, so "+00:00" like every stored stamp

    # Tier 1: the scored nowcast snapshot for the CPI family, else a hand-logged direction call.
    tier1: Optional[MethodCall] = None
    tier1_tracked = False
    nowcast_as_of = None
    nowcast_value: Optional[float] = None
    brent: Optional[dict] = None
    hand_logged: Optional[dict] = None
    s1 = None
    snapshot = get_scored_nowcast_snapshot(bt_conn, title, when) if title in NOWCAST_EVENTS else None
    if snapshot is not None:
        nowcast_value = snapshot["nowcast_value"]
        s1 = tier1_surprise(nowcast_value, forecast)
        nowcast_as_of = snapshot["as_of_utc"]
        if brent_series is not None:
            brent = _brent_detail(brent_series(), _parse_time(nowcast_as_of), when)
        tier1 = _call(nowcast_value, s1, forecast, tol, actual, title, kind=snapshot["kind"])
        tier1_tracked = True
    else:
        logged = _hand_logged_tier1_before(bt_conn, title, release_iso)
        if logged is not None:
            direction = logged["predicted_direction"]
            # 'neutral' is NO call (backtest_store tier1_comparisons convention), never an 'in line' call;
            # so is any direction without a surprise map. side None -> verdict None -> not scored.
            logged_side: Optional[int] = None
            if direction in ("bullish", "bearish"):
                implied = _implied_surprise_direction(title, NEWS_INSTRUMENT, direction)
                logged_side = {"higher": 1, "lower": -1}.get(implied)
            tier1 = _call(None, None, forecast, tol, actual, title, note="hand-logged", explicit_side=logged_side)
            hand_logged = {"value": logged["value"], "confidence": logged["confidence"], "source": logged["source"]}
            tier1_tracked = True
        else:
            tier1_tracked = title in NOWCAST_EVENTS      # tracked but no snapshot yet: row shows no call

    # News: rule R3 lean (print call first, accumulator fallback) times the prior-only median scale.
    print_row = _print_call_before(bt_conn, title, release_iso)
    acc_row = _accumulator_call_before(bt_conn, title, release_iso)
    lean = news_lean(
        title,
        None if print_row is None else print_row["predicted_vs_forecast"],
        None if print_row is None else print_row["confidence"],
        None if acc_row is None else acc_row["direction"],
        None if acc_row is None else acc_row["probability"],
    )
    scale = news_scale(prior)
    if title not in EVENT_SURPRISE_DIRECTION:
        # Ruling 3: an unmapped title never gets a news call. news_lean's print-call branch does not check
        # the map, so it is enforced here; the lean is cleared too, so Combined treats it as news missing.
        lean = None
    sn = news_surprise(lean, scale)
    news = None if sn is None else _call(forecast + sn, sn, forecast, tol, actual, title, note="scaled")

    # Combined: 70/30 blend; Tier 1 only (flagged news_missing) when there is no news; n/a without Tier 1.
    # It carries the Tier 1 snapshot's kind, so the scoreboard keeps live and reconstructed apart.
    combined = None
    blended = combine(s1, sn)
    if blended is not None:
        combined = _call(forecast + blended.surprise, blended.surprise, forecast, tol, actual, title,
                         note="news_missing" if blended.news_missing else None,
                         kind=None if tier1 is None else tier1.kind)

    if print_row is not None:
        article_count = print_row["article_count"]
    else:
        article_count = None if acc_row is None else acc_row["article_count"]
    detail = RowDetail(
        forecast_text=r["forecast"], nowcast_value=nowcast_value, nowcast_as_of_utc=nowcast_as_of,
        tier1_surprise=s1, news_lean=lean, news_scale=scale, news_surprise=sn,
        combined_surprise=None if blended is None else blended.surprise,
        news_article_count=article_count, hand_logged=hand_logged, brent=brent,
    )
    return StatsRow(title, when, r["forecast"], r["actual"], forecast, actual, tol, status,
                    tier1_tracked, tier1, news, combined, nowcast_as_of, pre_news, detail)


# --- payloads ---------------------------------------------------------------------------------

def _unit(rows: list[StatsRow]) -> str:
    """First non-digit trailing character of a numeric forecast: '0.3%' -> '%', '89K' -> 'K' ('N/A' skipped)."""
    for row in rows:
        if parse_number(row.forecast_text) is None:
            continue
        text = row.forecast_text.strip()
        if not text[-1].isdigit():
            return text[-1]
    return ""


def build_chart(rows: list[StatsRow], method: str) -> dict:
    """
    One point per scoreable occurrence; a month with no call has predicted/verdict None (a gap, not 0).
    `label` is the x-axis text: 'YYYY-MM' when every month has at most one point, otherwise 'YYYY-MM-DD'
    on every point (weekly titles such as Unemployment Claims would otherwise repeat a month label).
    """
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    points = []
    for row in rows:
        if row.status == "not_scoreable":
            continue
        call = getattr(row, method)
        points.append({
            "month": row.event_time_utc.strftime("%Y-%m"), "event_time_utc": row.event_time_utc.isoformat(),
            "forecast": row.forecast, "actual": row.actual,
            "predicted": None if call is None else call.predicted,
            "verdict": None if call is None else call.verdict,
        })
    months = [p["month"] for p in points]
    label_format = "%Y-%m" if len(months) == len(set(months)) else "%Y-%m-%d"
    for point in points:
        point["label"] = dt.datetime.fromisoformat(point["event_time_utc"]).strftime(label_format)
    return {"method": method, "unit": _unit(rows), "points": points}


def build_scoreboard(rows: list[StatsRow]) -> dict:
    """
    Per method: calls with a verdict, how many were right, accuracy (hidden under MIN_SCORED_FOR_PERCENT)
    and mean miss. A news_missing Combined call counts for Combined (it is the Tier 1 call); News counts
    only rows where a news call exists, since a row without one has news = None.

    The spec keeps populations apart, so each method also carries `by_kind` (live vs reconstructed, from
    MethodCall.kind; None counts as live) and Combined carries `with_news` (rows that really blended news,
    i.e. note != 'news_missing'). The percentage threshold still applies to the total.

    Mean miss is only reported when every scored call belongs to ONE event title: titles carry their own
    units (% vs K), so averaging across them is meaningless. Counts and accuracy are still reported.
    """
    methods = {}
    for name in METHODS:
        scored = right = 0
        by_kind = {"live": {"scored": 0, "right": 0}, "reconstructed": {"scored": 0, "right": 0}}
        with_news = {"scored": 0, "right": 0}
        misses: list[float] = []
        titles: set[str] = set()
        for row in rows:
            call = getattr(row, name)
            if call is None or call.verdict is None:
                continue
            is_right = call.verdict == "right"
            scored += 1
            right += is_right
            bucket = by_kind["reconstructed" if call.kind == "reconstructed" else "live"]
            bucket["scored"] += 1
            bucket["right"] += is_right
            if call.note != "news_missing":
                with_news["scored"] += 1
                with_news["right"] += is_right
            titles.add(row.event_title)
            if call.miss is not None:
                misses.append(call.miss)
        shown = scored >= MIN_SCORED_FOR_PERCENT
        one_title = len(titles) == 1
        methods[name] = {
            "scored": scored, "right": right,
            "accuracy": (right / scored) if shown else None, "accuracy_shown": shown,
            "mean_miss": (sum(misses) / len(misses)) if misses and one_title else None,
            "by_kind": by_kind,
        }
        if name == "combined":
            methods[name]["with_news"] = with_news
    return {"methods": methods, "min_for_percent": MIN_SCORED_FOR_PERCENT}
