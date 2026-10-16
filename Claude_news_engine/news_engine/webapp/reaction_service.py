# webapp/reaction_service.py
"""
Read-only service behind the Stats "Market reaction" sub-tab
(docs/superpowers/specs/2026-10-16-market-reaction-design.md §4, §4.1, §4.2, §5).

Joins USD event_history rows, the stored release_reactions (backtest_log.db, written only by
scripts/compute_release_reactions.py) and the Stats rows (engine calls). SELECT-only: never recomputes a
reaction and never writes. Fail-open per row: an unreadable row is logged and skipped, a failing engine
lookup leaves the engine column empty, and the rest of the payload still renders.

Releases: USD rows after the same-title duplicate collapse (reaction_rules.collapse_same_title_duplicates),
grouped by exact UTC minute into clusters. A cluster always holds every collapsed USD row at that minute,
whatever the impact/year/month filter: the market does not apply the filter. The filter only decides which
events are listed and counted ("visible"); hidden cluster members still take part in the credit.
"""
from __future__ import annotations

import bisect
import datetime as dt
import logging
import sqlite3
from dataclasses import dataclass
from typing import Optional

from scoring.backtest_store import get_release_reactions
from webapp import stats_service
from webapp.reaction_rules import (
    FEW_RELEASES_TAG, REACTION_BASELINE_QUANTILE, REACTION_MIN_MULTIPLE, cluster_credit,
    collapse_same_title_duplicates, impact_info, rate_display, title_tag_counts,
)
from webapp.stats_methods import market_lean
from webapp.stats_rules import parse_number, side, tolerance

logger = logging.getLogger(__name__)

WINDOW = dt.timedelta(minutes=5)          # the reaction window (spec R1); used only for the overlap tag
ENGINE_METHODS = ("combined", "tier1", "news")     # engine column precedence (controller decision D6)
DISCLAIMERS = {
    "association": "Reaction is measured over 5 minutes against the 75th-percentile ordinary move for that "
                   "hour; it shows association, not proof that the release caused the move.",
    "cluster": "Credit in a cluster is shared or matched, never exclusive.",
}
_LEANED = ("buy", "sell")
_HIT_CREDITS = ("solo_hit", "shared_hit", "matched")


@dataclass(frozen=True)
class _Event:
    """One release: a collapsed USD event_history row."""
    title: str
    when: dt.datetime              # the stored time, aware UTC (matches StatsRow.event_time_utc)
    minute: dt.datetime            # the UTC release minute (cluster key, reaction key)
    forecast_text: Optional[str]
    actual_text: Optional[str]
    impact: dict                   # reaction_rules.impact_info output: bucket / effective / inferred


@dataclass(frozen=True)
class _Judged:
    """One visible event with its cluster's verdict for the instrument."""
    event: _Event
    lean: str                      # 'buy' | 'sell' | 'mixed'
    reaction: Optional[str]        # 'buy' | 'sell' | 'none' | None (no data)
    reaction_row: Optional[sqlite3.Row]
    credit: str                    # reaction_rules.cluster_credit label
    cluster: list[dict]            # visible members (self included)
    cluster_size: int              # every collapsed USD row at the minute
    hidden_in_cluster: int         # members not visible under the filter
    engine_call: Optional[dict]
    note: Optional[str]


# --- inputs ---------------------------------------------------------------------------------------

def _parse_utc(value: str) -> dt.datetime:
    """Aware UTC; a naive stored value is taken as UTC (same rule as stats_service)."""
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _minute(when: dt.datetime) -> dt.datetime:
    return when.replace(second=0, microsecond=0)


def _load_events(dash_conn: sqlite3.Connection) -> list[_Event]:
    """Collapsed USD releases, ascending. Effective impact is inferred from the tags of ALL USD rows."""
    raw = dash_conn.execute(
        "SELECT event_title, event_time_utc, forecast, actual, impact FROM event_history "
        "WHERE country = 'USD' ORDER BY event_time_utc, event_title"
    ).fetchall()
    title_tags = title_tag_counts((r["event_title"], r["impact"] or None) for r in raw)

    by_key: dict[tuple[str, dt.datetime], sqlite3.Row] = {}
    for r in raw:
        try:
            when = _parse_utc(r["event_time_utc"])
        except (TypeError, ValueError):
            logger.warning("reaction: skipping %s with unreadable time %r", r["event_title"], r["event_time_utc"])
            continue
        by_key.setdefault((r["event_title"], when), r)

    events = []
    for title, when in collapse_same_title_duplicates(list(by_key)):
        r = by_key[(title, when)]
        events.append(_Event(
            title=title, when=when, minute=_minute(when), forecast_text=r["forecast"], actual_text=r["actual"],
            impact=impact_info(r["impact"] or None, title_tags.get(title, {})),
        ))
    return events


def implied_lean(title: str, forecast_text: Optional[str], actual_text: Optional[str], instrument: str) -> str:
    """
    Surprise-implied lean for the instrument (spec §4): side(actual vs forecast, one rounding step) through
    market_lean. 'mixed' (no signal) when either number is missing or unreadable, in line, or unmapped.
    """
    forecast, actual, tol = parse_number(forecast_text), parse_number(actual_text), tolerance(forecast_text)
    if forecast is None or actual is None or tol is None:
        return "mixed"
    try:
        return market_lean(title, side(actual, forecast, tol), instrument)
    except Exception:  # noqa: BLE001 -- an unexpected symbol/config problem is no signal, not a crash
        logger.warning("reaction: lean failed for %s on %s", title, instrument, exc_info=True)
        return "mixed"


def _reactions_by_minute(bt_conn: sqlite3.Connection, instrument: str) -> dict[dt.datetime, sqlite3.Row]:
    """Stored rows for the instrument at the current baseline quantile and multiple, keyed by aware UTC minute."""
    try:
        stored = get_release_reactions(bt_conn, instrument, REACTION_BASELINE_QUANTILE, REACTION_MIN_MULTIPLE)
    except sqlite3.Error:
        logger.warning("reaction: could not read release_reactions for %s", instrument, exc_info=True)
        return {}
    out: dict[dt.datetime, sqlite3.Row] = {}
    for key, row in stored.items():
        try:
            out.setdefault(_minute(_parse_utc(key)), row)
        except (TypeError, ValueError):
            logger.warning("reaction: skipping stored reaction with unreadable time %r", key)
    return out


def _stored_reaction(row: Optional[sqlite3.Row]) -> Optional[str]:
    """The stored call for a status 'ok' row; None (no data) for a no_data row or a missing one."""
    if row is None or row["status"] != "ok":
        return None
    return row["reaction"] if row["reaction"] in ("buy", "sell", "none") else None


def _engine_calls(dash_conn: sqlite3.Connection, bt_conn: sqlite3.Connection) -> dict:
    """{(title, stored UTC time): StatsRow} from the unfiltered Stats rows; {} if the Stats build fails."""
    try:
        rows = stats_service.build_rows(dash_conn, bt_conn, brent_series_fn=lambda: None)   # Brent unused here
    except Exception:  # noqa: BLE001 -- the engine column is optional; reactions still render
        logger.warning("reaction: Stats rows unavailable, engine column left empty", exc_info=True)
        return {}
    return {(row.event_title, row.event_time_utc): row for row in rows}


def _engine_call(stats_row) -> Optional[dict]:
    """The first of combined, tier1, news that has a verdict, as {"method", "verdict"}; None otherwise."""
    if stats_row is None:
        return None
    for method in ENGINE_METHODS:
        call = getattr(stats_row, method, None)
        if call is not None and call.verdict is not None:
            return {"method": method, "verdict": call.verdict}
    return None


def _overlap_note(minute: dt.datetime, release_minutes: list[dt.datetime]) -> Optional[str]:
    """Tag only (spec R12): the first other release minute strictly inside (t, t + 5 min)."""
    i = bisect.bisect_right(release_minutes, minute)
    if i < len(release_minutes) and release_minutes[i] < minute + WINDOW:
        gap = int((release_minutes[i] - minute).total_seconds() // 60)
        return f"another release {gap} min later"
    return None


# --- the shared join -------------------------------------------------------------------------------

def _judge(dash_conn: sqlite3.Connection, bt_conn: sqlite3.Connection, instrument: str,
           impacts: Optional[frozenset[str]], year: Optional[int], month: Optional[int],
           event_title: Optional[str] = None) -> list[_Judged]:
    """Every visible event (optionally one title) with its cluster credit, ascending by time."""
    events = _load_events(dash_conn)
    reactions = _reactions_by_minute(bt_conn, instrument)
    engine_rows = _engine_calls(dash_conn, bt_conn)
    release_minutes = sorted({e.minute for e in events})

    def visible(e: _Event) -> bool:
        return ((impacts is None or e.impact["bucket"] in impacts)
                and (year is None or e.minute.year == year)
                and (month is None or e.minute.month == month))

    clusters: dict[dt.datetime, list[_Event]] = {}
    for e in events:
        clusters.setdefault(e.minute, []).append(e)

    leans_by_minute: dict[dt.datetime, dict[str, str]] = {}
    out: list[_Judged] = []
    for e in events:
        if not visible(e) or (event_title is not None and e.title != event_title):
            continue
        try:
            members = clusters[e.minute]
            if e.minute not in leans_by_minute:
                leans_by_minute[e.minute] = {
                    m.title: implied_lean(m.title, m.forecast_text, m.actual_text, instrument) for m in members}
            leans = leans_by_minute[e.minute]
            row = reactions.get(e.minute)
            reaction = _stored_reaction(row)
            credits = cluster_credit(leans, reaction)
            shown = [m for m in members if visible(m)]
            out.append(_Judged(
                event=e, lean=leans[e.title], reaction=reaction, reaction_row=row, credit=credits[e.title],
                cluster=[{"event_title": m.title, "lean": leans[m.title], "credit": credits[m.title],
                          "impact_effective": m.impact["effective"]} for m in shown],
                cluster_size=len(members), hidden_in_cluster=len(members) - len(shown),
                engine_call=_engine_call(engine_rows.get((e.title, e.when))),
                note=_overlap_note(e.minute, release_minutes),
            ))
        except Exception:  # noqa: BLE001 -- one bad row must not break the tab
            logger.warning("reaction: row failed for %s %s", e.title, e.minute, exc_info=True)
    return out


def _signed_move_pct(j: _Judged) -> Optional[float]:
    """move_pct in the implied direction: + when the market moved the way the lean said."""
    move_pct = j.reaction_row["move_pct"] if j.reaction_row is not None else None
    if move_pct is None:
        return None
    return move_pct if j.lean == "buy" else -move_pct


# --- payloads --------------------------------------------------------------------------------------

def build_leaderboard(dash_conn: sqlite3.Connection, bt_conn: sqlite3.Connection, instrument: str,
                      impacts: Optional[frozenset[str]], year: Optional[int], month: Optional[int]) -> dict:
    """
    One row per event title with at least one counted release (spec §4.2). A counted release is a visible
    event with a lean whose minute has a status 'ok' reaction row; no-signal and no-data events are left out
    of every rate (they appear only in the drill-down). Sorted by reactions, then releases (both desc), then title.
    """
    judged = _judge(dash_conn, bt_conn, instrument, impacts, year, month)
    by_title: dict[str, list[_Judged]] = {}
    for j in judged:
        by_title.setdefault(j.event.title, []).append(j)

    rows = []
    for title, items in by_title.items():
        counted = [j for j in items if j.lean in _LEANED and j.reaction is not None]
        if not counted:
            continue
        reacted = [j for j in counted if j.reaction in _LEANED]
        hits = sum(1 for j in reacted if j.credit in _HIT_CREDITS)
        signed = [m for m in (_signed_move_pct(j) for j in reacted) if m is not None]
        engine = [j.engine_call for j in items if j.engine_call is not None]
        title_impact = impact_info(None, _title_tags_of(items))
        rows.append({
            "event_title": title,
            "impact_effective": title_impact["effective"],
            "impact_inferred": any(j.event.impact["inferred"] for j in items),
            "releases": len(counted),
            "solo": sum(1 for j in counted if j.credit in ("solo_hit", "solo_miss")),
            "shared": sum(1 for j in counted if j.credit in ("shared_hit", "shared_miss")),
            "in_conflict": sum(1 for j in counted if j.credit in ("matched", "overruled")),
            "reaction": rate_display(len(reacted), len(counted)),
            "hit": rate_display(hits, len(reacted)),
            "avg_move_pct": sum(signed) / len(signed) if signed else None,
            "engine": ({"k": sum(1 for c in engine if c["verdict"] == "right"), "n": len(engine)}
                       if engine else None),
            "few": len(counted) < FEW_RELEASES_TAG,
        })
    rows.sort(key=lambda r: (-r["reaction"]["k"], -r["releases"], r["event_title"]))
    return {"instrument": instrument, "quantile": REACTION_BASELINE_QUANTILE, "rows": rows,
            "disclaimers": dict(DISCLAIMERS)}


def _title_tags_of(items: list[_Judged]) -> dict[str, int]:
    """
    The title's effective tag for the leaderboard: the most common effective impact over its visible
    releases (each release's effective tag already folds in inheritance), ties to the stronger tag.
    """
    counts: dict[str, int] = {}
    for j in items:
        tag = j.event.impact["effective"]
        counts[tag] = counts.get(tag, 0) + 1
    return counts


def build_event_releases(dash_conn: sqlite3.Connection, bt_conn: sqlite3.Connection, instrument: str,
                         event_title: str, impacts: Optional[frozenset[str]], year: Optional[int],
                         month: Optional[int]) -> dict:
    """Every visible release of one title, newest first, including no-signal and no-data ones."""
    judged = _judge(dash_conn, bt_conn, instrument, impacts, year, month, event_title=event_title)
    releases = []
    for j in reversed(judged):
        row = j.reaction_row
        typical = None if row is None else row["typical_abs_move"]
        multiple = None if row is None else row["reaction_multiple"]
        releases.append({
            "event_time_utc": j.event.minute.isoformat(),
            "move": None if row is None else row["move"],
            "move_pct": None if row is None else row["move_pct"],
            "threshold": None if typical is None else typical * (1.0 if multiple is None else multiple),
            "reaction": j.reaction,
            "lean": j.lean,
            "credit": j.credit,
            "cluster_size": j.cluster_size,
            "hidden_in_cluster": j.hidden_in_cluster,
            "cluster": j.cluster,
            "engine_call": j.engine_call,
            "note": j.note,
        })
    return {"event_title": event_title, "instrument": instrument, "releases": releases}
