"""
Shock-alert lean grading (B10 K11/K12, 2026-10-28; plan docs/superpowers/plans/2026-10-28-b10-shock-grading.md).

Every alert's STORED lean per tracked symbol is graded against what the symbol actually did over the 5 minutes
after two anchors -- first publication (`published`) and detection (`detected`) -- judged against the normal
5-minute move for that UTC hour: the Market reaction hourly baselines (reaction_baselines in backtest_log.db,
REACTION_BASELINE_QUANTILE 0.75), never a second baseline definition and never a fixed-dollar threshold.

Rules:
  * Anchor minute m = the anchor rounded UP to a whole UTC minute (nothing before the anchor is used). Move =
    open(bar at m+5) - open(bar at m), Dukascopy BID bars matched to the exact minute (the reaction job's rule);
    a missing bar is no_data, a neighbouring bar is never substituted. The baseline hour is the UTC hour of m.
  * A publication time more than MAX_PUBLICATION_LAG before detection is treated as unknown (no_data).
  * Verdict precedence: no_lean (stored lean not buy/sell, or the symbol absent from affected_symbols; the move
    is still stored) > no_data > no_baseline > no_move (|move| <= 1.0 x baseline, classify_reaction) > right/wrong.
  * A cell is not written while m+5 is later than the last bar the feed returned or later than now -
    PENDING_MARGIN (weekend alerts wait for Monday's bars, then read no_data). A fetch failure writes nothing for
    that symbol. A symbol with no Dukascopy mapping is permanent: no_data (or no_lean).
  * Grades are append-only (INSERT OR IGNORE in alerting/store.py) and store the baseline used, so a rerun
    writes 0 and a later baseline refresh never changes a grade. Grading never touches shock_alerts rows.
  * Hit rate = right / (right + wrong), n = right + wrong; the other verdicts are counts, never in n.
backtest_log.db and dashboard.db are only ever opened read-only here (open_readonly, sqlite URI mode=ro).
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union

from alerting import store
from alerting.store import ShockAlertRow
from data_layer.minute_bars import FetchBars, to_opens
from scoring import backtest_store
from webapp import store as web_store
from webapp.reaction_rules import REACTION_BASELINE_QUANTILE, REACTION_MIN_MULTIPLE, classify_reaction

UTC = dt.timezone.utc
ANCHORS: tuple[str, ...] = ("published", "detected")
GRADE_WINDOW_MINUTES = 5
VERDICTS: tuple[str, ...] = ("right", "wrong", "no_move", "no_lean", "no_data", "no_baseline")
# Bars for a minute this recent may simply not be published yet; mirrors the reaction job's skipped_pending.
PENDING_MARGIN = dt.timedelta(minutes=10)
# Guards the bar fetch range against a garbage publication stamp; live lag never exceeds 465 min (2026-10-28).
MAX_PUBLICATION_LAG = dt.timedelta(days=7)
_WINDOW = dt.timedelta(minutes=GRADE_WINDOW_MINUTES)
_LEANS = ("buy", "sell")


@dataclass(frozen=True)
class Grade:
    """One graded cell: alert x symbol x anchor x window. None fields mean "not available", never zero."""
    alert_id: int
    symbol: str
    anchor: str
    window_minutes: int
    lean: Optional[str]                  # the stored lean verbatim (None when absent)
    anchor_utc: Optional[dt.datetime]    # the rounded-up anchor minute m, None when the anchor time is unknown
    p0: Optional[float]
    p_end: Optional[float]
    move: Optional[float]                # p_end - p0
    baseline: Optional[float]            # the hourly baseline used (stored so a refresh never regrades)
    baseline_multiple: float
    moved: Optional[bool]                # |move| > baseline x multiple; None when unjudgeable
    verdict: str


# =============================================================================================
# Pure rules
# =============================================================================================

def _utc(value: dt.datetime) -> dt.datetime:
    """Aware UTC; a naive stored stamp is taken as UTC (the alerting store writes UTC ISO)."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def anchor_minute(when: dt.datetime) -> dt.datetime:
    """Ceiling to a whole UTC minute (an exact minute is unchanged), so no bar before the anchor is used."""
    when = _utc(when)
    floor = when.replace(second=0, microsecond=0)
    return floor if floor == when else floor + dt.timedelta(minutes=1)


def anchor_time(alert: ShockAlertRow, anchor: str) -> Optional[dt.datetime]:
    """
    The raw anchor time (aware UTC) or None when unknown. `published` is first_published_utc (the reader falls
    back to sources[0]); one more than MAX_PUBLICATION_LAG before detection is treated as unknown.
    """
    detected = _utc(alert.detected_at_utc)
    if anchor == "detected":
        return detected
    if anchor == "published":
        if alert.first_published_utc is None:
            return None
        published = _utc(alert.first_published_utc)
        if detected - published > MAX_PUBLICATION_LAG:
            return None
        return published
    raise ValueError(f"anchor must be one of {ANCHORS}, got {anchor!r}")


def stored_lean(alert: ShockAlertRow, symbol: str) -> Optional[str]:
    """The lean stored for `symbol` verbatim, or None when the symbol or its lean key is absent. Never inferred."""
    for impact in alert.affected_symbols or []:
        if isinstance(impact, Mapping) and impact.get("symbol") == symbol:
            return impact.get("lean")
    return None


def grade_cell(
    alert_id: int, symbol: str, anchor: str, when: Optional[dt.datetime], lean: Optional[str],
    opens: Optional[dict[dt.datetime, float]], baselines: dict[int, float],
) -> Grade:
    """
    Grades one cell. `when` is the raw anchor time (None = unknown); `opens` is {aware UTC minute: open}, None
    when the symbol has no Dukascopy mapping; `baselines` is {UTC hour: typical |5-min move|}.
    """
    minute = anchor_minute(when) if when is not None else None
    p0 = p_end = move = baseline = None
    if minute is not None:
        baseline = baselines.get(minute.hour)
        if opens is not None:
            p0, p_end = opens.get(minute), opens.get(minute + _WINDOW)    # exact minutes only, never a neighbour
            if p0 is not None and p_end is not None:
                move = p_end - p0
    reaction = classify_reaction(move, baseline, REACTION_MIN_MULTIPLE)
    moved = None if reaction is None else reaction in _LEANS

    if lean not in _LEANS:
        verdict = "no_lean"
    elif move is None:
        verdict = "no_data"
    elif reaction is None:                      # no baseline for the hour (or a zero one): no fixed fallback
        verdict = "no_baseline"
    elif reaction == "none":
        verdict = "no_move"
    else:
        verdict = "right" if reaction == lean else "wrong"
    return Grade(
        alert_id=alert_id, symbol=symbol, anchor=anchor, window_minutes=GRADE_WINDOW_MINUTES, lean=lean,
        anchor_utc=minute, p0=p0, p_end=p_end, move=move, baseline=baseline,
        baseline_multiple=REACTION_MIN_MULTIPLE, moved=moved, verdict=verdict,
    )


def is_pending(when: Optional[dt.datetime], last_bar: Optional[dt.datetime], now: dt.datetime) -> bool:
    """
    True while the cell's m+5 is later than now - PENDING_MARGIN, or later than `last_bar` (the last bar the
    feed returned). An unknown anchor is never pending (graded at once). last_bar None = no feed to wait for
    (the symbol has no Dukascopy mapping), so only the time margin applies.
    """
    if when is None:
        return False
    end = anchor_minute(when) + _WINDOW
    if end > _utc(now) - PENDING_MARGIN:
        return True
    return last_bar is not None and end > _utc(last_bar)


# =============================================================================================
# Summaries
# =============================================================================================

def empty_counts() -> dict:
    return {"n": 0, "right": 0, "wrong": 0, "hit_rate": None,
            "no_move": 0, "no_lean": 0, "no_data": 0, "no_baseline": 0}


def _field(grade: Union[Grade, Mapping], name: str):
    return grade[name] if isinstance(grade, Mapping) else getattr(grade, name)


def _add(counts: dict, verdict: str) -> None:
    if verdict not in VERDICTS:
        raise ValueError(f"unknown verdict {verdict!r}")
    counts[verdict] += 1
    counts["n"] = counts["right"] + counts["wrong"]
    counts["hit_rate"] = round(counts["right"] / counts["n"], 4) if counts["n"] else None


def summarize_grades(grades: Iterable[Union[Grade, Mapping]]) -> dict:
    """{"overall": {anchor: counts}, "by_symbol": {symbol: {anchor: counts}}}; only right + wrong count in n."""
    overall = {anchor: empty_counts() for anchor in ANCHORS}
    by_symbol: dict[str, dict[str, dict]] = {}
    for grade in grades:
        anchor, symbol, verdict = _field(grade, "anchor"), _field(grade, "symbol"), _field(grade, "verdict")
        per_symbol = by_symbol.setdefault(symbol, {a: empty_counts() for a in ANCHORS})
        _add(overall.setdefault(anchor, empty_counts()), verdict)
        _add(per_symbol.setdefault(anchor, empty_counts()), verdict)
    return {"overall": overall, "by_symbol": {symbol: by_symbol[symbol] for symbol in sorted(by_symbol)}}


def summarize_incidents(alerts: list[ShockAlertRow], grades_by_alert: dict[int, list[dict]]) -> list[dict]:
    """
    One entry per B7 incident among `alerts` (the caller's range), newest incident first: the headline of the
    incident's earliest alert in the list, its first detection (UTC ISO), the alert count and per-anchor counts
    summed over every symbol of every alert in it.
    """
    groups: dict[int, list[ShockAlertRow]] = {}
    for alert in alerts:
        groups.setdefault(alert.incident_id if alert.incident_id is not None else alert.id, []).append(alert)
    out = []
    for incident_id, members in groups.items():
        first = min(members, key=lambda a: (_utc(a.detected_at_utc), a.id))
        overall = summarize_grades(g for a in members for g in grades_by_alert.get(a.id, []))["overall"]
        out.append({
            "incident_id": incident_id,
            "headline": first.headline,
            "first_detected_utc": _utc(first.detected_at_utc).isoformat(),
            "alerts": len(members),
            "published": overall["published"],
            "detected": overall["detected"],
        })
    out.sort(key=lambda entry: (entry["first_detected_utc"], entry["incident_id"]), reverse=True)
    return out


def _pct(right: int, n: int) -> str:
    return f"{right / n * 100:.1f}%" if n else "n/a"


def format_summary_line(result: dict) -> str:
    """The one-line job/health summary; verdict counts sum both anchors, plus the detection-anchored hit rate."""
    overall = result["counts"]["overall"]
    totals = {key: sum(overall[a][key] for a in overall) for key in ("right", "wrong", *VERDICTS[2:])}
    n = totals["right"] + totals["wrong"]
    detected = overall.get("detected", empty_counts())
    line = (
        f"graded {result['written']}: right {totals['right']}, wrong {totals['wrong']}, "
        f"no_move {totals['no_move']}, no_lean {totals['no_lean']}, no_data {totals['no_data']}, "
        f"no_baseline {totals['no_baseline']}; hit rate {_pct(totals['right'], n)} ({totals['right']} of {n}); "
        f"detected {_pct(detected['right'], detected['n'])} ({detected['right']} of {detected['n']}); "
        f"pending {result['pending']}"
    )
    if result.get("fetch_failed"):
        line += "; fetch failed: " + ", ".join(sorted(result["fetch_failed"]))
    return line


# =============================================================================================
# The batch job
# =============================================================================================

def _resolve_dukascopy(symbol: str) -> Optional[str]:
    from data_layer.dukascopy_feed import _resolve_dukascopy_instrument
    return _resolve_dukascopy_instrument(symbol)


def grade_pending_alerts(
    conn: sqlite3.Connection, symbols: list[str], baselines_by_symbol: dict[str, dict[int, float]],
    fetch_bars: FetchBars, now: dt.datetime, *, dry_run: bool = False,
    resolve: Optional[Callable[[str], Optional[str]]] = None,
) -> dict:
    """
    Grades every (alert, symbol, anchor) cell not yet stored and due. Bars are fetched once per symbol, from the
    earliest due anchor minute to now (no fetch when nothing is due or the symbol has no mapping). Returns
    {"written", "pending", "already_present", "fetch_failed": {symbol: error}, "counts": summarize_grades(written)};
    on a dry run "written" counts the rows that would be written and nothing is stored.
    """
    now = _utc(now)
    resolve = resolve or _resolve_dukascopy
    alerts = store.list_all_alerts(conn)
    existing = store.graded_keys(conn)
    times = {(alert.id, anchor): anchor_time(alert, anchor) for alert in alerts for anchor in ANCHORS}
    result: dict = {"written": 0, "pending": 0, "already_present": 0, "fetch_failed": {}}
    written: list[Grade] = []

    # Phase 1: one fetch per symbol that has due, timed cells. feeds[symbol] = (opens or None, last bar or None).
    feeds: dict[str, tuple[Optional[dict[dt.datetime, float]], Optional[dt.datetime]]] = {}
    for symbol in symbols:
        todo = [key for key in times if (key[0], symbol, key[1], GRADE_WINDOW_MINUTES) not in existing]
        if not todo:
            continue
        if resolve(symbol) is None:
            feeds[symbol] = (None, None)        # permanent: no Dukascopy mapping
            continue
        due = [anchor_minute(times[key]) for key in todo
               if times[key] is not None and not is_pending(times[key], None, now)]
        if not due:
            feeds[symbol] = ({}, None)          # only unknown-anchor or not-yet-due cells: nothing to fetch
            continue
        try:
            opens = to_opens(fetch_bars(symbol, min(due), now))
            if not opens:
                raise ValueError("no bars returned")
        except Exception as exc:                # one symbol's feed failure must not stop the others
            result["fetch_failed"][symbol] = f"{type(exc).__name__}: {exc}"
            continue
        feeds[symbol] = (opens, max(opens))

    # Phase 2: grade per alert, one commit per alert.
    for alert in alerts:
        wrote_any = False
        for symbol in symbols:
            for anchor in ANCHORS:
                if (alert.id, symbol, anchor, GRADE_WINDOW_MINUTES) in existing:
                    result["already_present"] += 1
                    continue
                if symbol not in feeds:          # fetch failed this run: write nothing, retry next run
                    continue
                opens, last_bar = feeds[symbol]
                when = times[(alert.id, anchor)]
                if is_pending(when, last_bar, now):
                    result["pending"] += 1
                    continue
                grade = grade_cell(alert.id, symbol, anchor, when, stored_lean(alert, symbol), opens,
                                   baselines_by_symbol.get(symbol, {}))
                if dry_run:
                    written.append(grade)
                elif store.record_grade(conn, grade, now, commit=False):
                    written.append(grade)
                    wrote_any = True
                else:                            # a concurrent run stored it first
                    result["already_present"] += 1
        if wrote_any:
            conn.commit()

    result["written"] = len(written)
    result["counts"] = summarize_grades(written)
    return result


# =============================================================================================
# Read-only loaders (backtest_log.db and dashboard.db are never written by shock grading)
# =============================================================================================

def open_readonly(path: Path) -> sqlite3.Connection:
    """sqlite URI mode=ro with sqlite3.Row; any write through it raises sqlite3.OperationalError."""
    conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_baselines(bt_db: Path, symbols: list[str]) -> dict[str, dict[int, float]]:
    """{symbol: {UTC hour: baseline}} at REACTION_BASELINE_QUANTILE, latest per hour; {} per symbol when absent."""
    conn = open_readonly(bt_db)
    try:
        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'reaction_baselines'").fetchone() is not None
        return {
            symbol: (backtest_store.get_latest_reaction_baselines(conn, symbol, REACTION_BASELINE_QUANTILE)
                     if has_table else {})
            for symbol in symbols
        }
    finally:
        conn.close()


def load_tracked_symbols(dash_db: Path) -> list[str]:
    """dashboard.db's tracked symbols (sorted), read-only."""
    conn = open_readonly(dash_db)
    try:
        return web_store.list_tracked_symbols(conn)
    finally:
        conn.close()
