# ops/health.py
"""
One health check for every scheduled job, RSS feed, shock classifier and
Tier 1 capture (B4 O6). build_health() grades each against its expected
interval (ok / amber / red); it is served at GET /api/health, drawn as the
dashboard strip, and turned into at most ONE Telegram notice per UTC day by
maybe_send_health_notice() (called from the shock poll and the outcome job,
so each covers the other's death; the ops_state ledger keeps it to one).

Rules worth knowing:
- Heartbeats (ops_state.job_runs), not data timestamps, are the primary
  signal: several jobs may legitimately write nothing. Data timestamps are
  a fallback where they exist (the later of the two counts).
- A job never seen since tracking started is amber, and turns red only once
  tracking itself is older than its red threshold -- so a monthly job is not
  red on deploy day, but a task that never fires is still caught.
- Instants are compared with julianday() in SQL, never as raw strings:
  naive and offset ISO stamps both occur in these DBs.
- Every check is wrapped: one failing check is amber "check failed: ..." and
  never takes the whole build (or the job that asked for it) down.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from alerting import notify_telegram
from alerting import store as alerting_store
from alerting.source_backoff import in_backoff, is_drop_candidate
from config.settings import CLASSIFIER_PROVIDER_ORDER, CLAUDE_COOLDOWN_MINUTES, LOCAL_TZ, OLLAMA_COOLDOWN_MINUTES
from data_layer.rss_sources import FREE_PREVIEW_FEEDS
from data_layer.tier1_events import TIER1_FORMULA, TIER1_FORMULA_SOURCE, TIER1_JUDGMENT, tier1_titles
from ops import state as ops_state
from scoring import backtest_store
from webapp import store as webapp_store

UTC = dt.timezone.utc

# scripts/refresh_macro_calendar.py's _LAST_MACRO_REFRESH_FILE (pinned equal by a
# test). Not imported, so the 2-minute poll never loads the refresh script.
MACRO_MARKER_PATH: Path = Path(__file__).parent.parent / "data_layer" / ".last_macro_calendar_refresh_at"
# scripts/refresh_macro_calendar.py's _LAST_MACRO_FAILURE_FILE (pinned equal by a test too).
MACRO_FAILURE_MARKER_PATH: Path = Path(__file__).parent.parent / "data_layer" / ".last_macro_calendar_refresh_failure"
MISSED_RELEASE_LOOKBACK = dt.timedelta(days=7)
TIER1_DUE_WINDOW = dt.timedelta(hours=24)
# Same as alerting/poll_once.py's _METHOD_BY_PROVIDER (pinned equal by a test).
PROVIDER_METHOD = {"claude": "llm", "ollama": "llm_ollama"}
_COOLDOWN_MINUTES = {"claude": CLAUDE_COOLDOWN_MINUTES, "ollama": OLLAMA_COOLDOWN_MINUTES}
CLASSIFIER_WINDOW = dt.timedelta(hours=24)
# scripts/confirm_backtest_outcomes.py's FINAL_NO_REACTION_AFTER (pinned equal by a
# test): a row still awaiting after this is a fetch failure, not a quiet market.
AWAITING_STUCK_AFTER = dt.timedelta(days=3)
_DETAIL_LIST_MAX = 3
# Two stamps of the same instant written in different ISO forms can differ in the
# last julianday bits; half a second is far below any real release spacing.
_SAME_INSTANT_DAYS = 0.5 / 86400

_STATUS_RANK = {"ok": 0, "amber": 1, "red": 2}


@dataclass(frozen=True)
class HealthItem:
    key: str
    label: str
    status: str  # "ok" | "amber" | "red"
    last_success_utc: Optional[dt.datetime]
    age_seconds: Optional[float]
    expected_every_seconds: int
    detail: str


@dataclass(frozen=True)
class _JobSpec:
    key: str
    label: str
    expected: dt.timedelta
    amber_after: dt.timedelta
    red_after: dt.timedelta
    # (connection name, SQL returning newest data timestamp first) used as a fallback
    data_sql: tuple[tuple[str, str], ...] = ()


_H = dt.timedelta(hours=1)
_D = dt.timedelta(days=1)
_M = dt.timedelta(minutes=1)

_JOBS: dict[str, _JobSpec] = {spec.key: spec for spec in (
    _JobSpec("shock_poll", "Shock poll", 2 * _M, 10 * _M, 30 * _M),
    _JobSpec("outcome_confirm", "Outcome confirm", 15 * _M, 45 * _M, 2 * _H),
    _JobSpec("reaction_incremental", "Market reaction (hourly)", _H, 3 * _H, 6 * _H),
    _JobSpec("reaction_baselines", "Market reaction baselines (monthly)", 31 * _D, 32 * _D, 35 * _D, (
        ("bt", "SELECT computed_at_utc FROM reaction_baselines ORDER BY julianday(computed_at_utc) DESC LIMIT 1"),
    )),
    _JobSpec("tier1_capture_daily", "Tier 1 formula capture (daily)", 24 * _H, 26 * _H, 50 * _H),
    _JobSpec("tier1_capture_weekly", "Tier 1 formula capture (weekly)", 7 * _D, 8 * _D, 9 * _D),
    _JobSpec("shock_reality_check", "Shock reality check (weekly)", 7 * _D, 8 * _D, 9 * _D),
    _JobSpec("article_accumulator", "Article accumulator", 12 * _H, 13 * _H, 25 * _H, (
        ("bt", "SELECT checked_at_utc FROM check_log ORDER BY julianday(checked_at_utc) DESC LIMIT 1"),
        ("bt", "SELECT scored_at_utc FROM predictions WHERE source = 'live' "
               "ORDER BY julianday(scored_at_utc) DESC LIMIT 1"),
    )),
    _JobSpec("calendar_refresh", "Forex Factory calendar", 12 * _H, 13 * _H, 25 * _H, (
        ("dash", "SELECT fetched_at_utc FROM calendar_snapshot ORDER BY julianday(fetched_at_utc) DESC LIMIT 1"),
    )),
)}
_MACRO = _JobSpec("macro_calendar", "Macro calendar (FRED)", 29 * _D, 30 * _D, 31 * _D)
_TIER1_RESEARCH_LABEL = "Tier 1 research (judgment calls)"
_NOWCAST_LIVE_LABEL = "Tier 1 live nowcast (formula)"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _parse_utc(value: Optional[str]) -> Optional[dt.datetime]:
    """ISO string -> aware UTC datetime; a naive value is read as UTC; None/empty -> None."""
    if not value:
        return None
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_utc(when: Optional[dt.datetime]) -> Optional[dt.datetime]:
    if when is None:
        return None
    return when.replace(tzinfo=UTC) if when.tzinfo is None else when.astimezone(UTC)


def _sast(when: dt.datetime) -> str:
    return when.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M SAST")


def _newest(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> Optional[dt.datetime]:
    row = conn.execute(sql, params).fetchone()
    return _parse_utc(row[0]) if row is not None else None


def _grade(age: dt.timedelta, amber_after: dt.timedelta, red_after: dt.timedelta) -> str:
    if age <= amber_after:
        return "ok"
    return "amber" if age <= red_after else "red"


def _worst(*statuses: str) -> str:
    return max(statuses, key=lambda s: _STATUS_RANK[s])


def _list_detail(prefix: str, entries: list[str]) -> str:
    """'prefix: a, b, c and N more' -- the first three entries, then a count."""
    shown = ", ".join(entries[:_DETAIL_LIST_MAX])
    rest = len(entries) - _DETAIL_LIST_MAX
    return f"{prefix}: {shown}" + (f" and {rest} more" if rest > 0 else "")


def _aged_item(
    spec: _JobSpec, now: dt.datetime, last_success: Optional[dt.datetime], tracking_since: dt.datetime,
    run: Optional[ops_state.JobRun] = None,
) -> HealthItem:
    """Grades by age of the last success; never seen -> amber until tracking is older than red_after."""
    expected = int(spec.expected.total_seconds())
    if last_success is None:
        status = "red" if now - tracking_since > spec.red_after else "amber"
        detail = f"no successful run since tracking started {_sast(tracking_since)}"
        if run is not None:
            detail += f"; last run {_sast(run.last_run_utc)} exited {run.last_exit_code}"
        return HealthItem(spec.key, spec.label, status, None, None, expected, detail)
    age = now - last_success
    status = _grade(age, spec.amber_after, spec.red_after)
    parts = []
    if status != "ok":
        parts.append(f"last success {_sast(last_success)}")
    if run is not None and run.last_exit_code != 0:
        parts.append(f"last run {_sast(run.last_run_utc)} exited {run.last_exit_code}")
    return HealthItem(spec.key, spec.label, status, last_success, age.total_seconds(), expected, "; ".join(parts))


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def _job_check(spec: _JobSpec, now: dt.datetime, conns: dict[str, sqlite3.Connection]) -> HealthItem:
    ops_conn = conns["ops"]
    run = ops_state.get_job_runs(ops_conn).get(spec.key)
    candidates = [_as_utc(run.last_success_utc)] if run is not None and run.last_success_utc else []
    for conn_name, sql in spec.data_sql:
        stamp = _newest(conns[conn_name], sql)
        if stamp is not None:
            candidates.append(stamp)
    last = max(candidates) if candidates else None
    return _aged_item(spec, now, last, _as_utc(ops_state.get_tracking_since(ops_conn)), run)


def _outcome_confirm_check(now: dt.datetime, conns: dict[str, sqlite3.Connection]) -> HealthItem:
    item = _job_check(_JOBS["outcome_confirm"], now, conns)
    awaiting = backtest_store.get_predictions_awaiting_outcome(conns["bt"], now)
    stuck = [p for p in awaiting if now - _parse_utc(p.event_time_utc) > AWAITING_STUCK_AFTER]
    if not stuck:
        return item
    detail = "; ".join(d for d in (item.detail, f"{len(stuck)} awaiting more than 3 days (no price data)") if d)
    return HealthItem(item.key, item.label, _worst(item.status, "amber"), item.last_success_utc,
                      item.age_seconds, item.expected_every_seconds, detail)


def _occurrences(
    dash: sqlite3.Connection, titles: list[str], start: dt.datetime, end: dt.datetime, *, include_start: bool,
) -> list[tuple[str, str]]:
    """USD event_history (title, raw event_time_utc) with start <(=) event_time <= end, oldest first."""
    if not titles:
        return []
    marks = ",".join("?" for _ in titles)
    lower = ">=" if include_start else ">"
    return [(r[0], r[1]) for r in dash.execute(
        f"SELECT event_title, event_time_utc FROM event_history WHERE country = 'USD' "
        f"AND event_title IN ({marks}) AND julianday(event_time_utc) {lower} julianday(?) "
        f"AND julianday(event_time_utc) <= julianday(?) ORDER BY julianday(event_time_utc)",
        (*titles, start.isoformat(), end.isoformat()),
    ).fetchall()]


def _has_row(bt: sqlite3.Connection, sql: str, title: str, event_time: str, *, before_release: bool) -> bool:
    """A row for this title and release instant; with before_release, only one made at or before it."""
    params: tuple = (title, event_time, _SAME_INSTANT_DAYS)
    return bt.execute(sql, params + ((event_time,) if before_release else ())).fetchone() is not None


# A call/snapshot for this title and release instant, made at or before the release.
_PRE_RELEASE_CALL_SQL = (
    "SELECT 1 FROM tier1_predictions WHERE event_title = ? "
    "AND abs(julianday(event_time_utc) - julianday(?)) < ? AND julianday(logged_at_utc) <= julianday(?) LIMIT 1"
)
_PRE_RELEASE_LIVE_SNAPSHOT_SQL = (
    "SELECT 1 FROM tier1_nowcast_snapshots WHERE kind = 'live' AND event_title = ? "
    "AND abs(julianday(event_time_utc) - julianday(?)) < ? AND julianday(as_of_utc) <= julianday(?) LIMIT 1"
)
# Any call yet for an upcoming release.
_ANY_CALL_SQL = (
    "SELECT 1 FROM tier1_predictions WHERE event_title = ? "
    "AND abs(julianday(event_time_utc) - julianday(?)) < ? LIMIT 1"
)


def _missed_release_item(
    key: str, label: str, now: dt.datetime, dash: sqlite3.Connection, bt: sqlite3.Connection,
    titles: list[str], present_sql: str, last_success: Optional[dt.datetime], *, check_due: bool,
) -> HealthItem:
    """
    Red when a covered USD release in the last 7 days had no pre-release
    row; amber (research only) when one due within 24h has no call yet.
    last_success is informational: these captures are graded by misses.
    """
    missed = [
        f"{title} {_sast(_parse_utc(when))}"
        for title, when in _occurrences(dash, titles, now - MISSED_RELEASE_LOOKBACK, now, include_start=True)
        if not _has_row(bt, present_sql, title, when, before_release=True)
    ]
    due = []
    if check_due:
        due = [
            f"{title} {_sast(_parse_utc(when))}"
            for title, when in _occurrences(dash, titles, now, now + TIER1_DUE_WINDOW, include_start=False)
            if not _has_row(bt, _ANY_CALL_SQL, title, when, before_release=False)
        ]
    parts = []
    if missed:
        parts.append(_list_detail("missed", missed))
    if due:
        parts.append(_list_detail("due within 24h without a call", due))
    status = "red" if missed else "amber" if due else "ok"
    age = (now - last_success).total_seconds() if last_success is not None else None
    return HealthItem(key, label, status, last_success, age, int(_D.total_seconds()), "; ".join(parts))


def _tier1_research_check(now: dt.datetime, conns: dict[str, sqlite3.Connection]) -> HealthItem:
    bt = conns["bt"]
    stamps = [
        _newest(bt, "SELECT logged_at_utc FROM tier1_predictions WHERE source != ? "
                    "ORDER BY julianday(logged_at_utc) DESC LIMIT 1", (TIER1_FORMULA_SOURCE,)),
        _newest(bt, "SELECT checked_at_utc FROM tier1_late_checks ORDER BY julianday(checked_at_utc) DESC LIMIT 1"),
    ]
    last = max((s for s in stamps if s is not None), default=None)
    return _missed_release_item("tier1_research", _TIER1_RESEARCH_LABEL, now, conns["dash"], bt,
                                tier1_titles(TIER1_JUDGMENT), _PRE_RELEASE_CALL_SQL, last, check_due=True)


def _nowcast_live_check(now: dt.datetime, conns: dict[str, sqlite3.Connection]) -> HealthItem:
    bt = conns["bt"]
    last = _newest(bt, "SELECT recorded_at_utc FROM tier1_nowcast_snapshots WHERE kind = 'live' "
                       "ORDER BY julianday(recorded_at_utc) DESC LIMIT 1")
    return _missed_release_item("nowcast_live", _NOWCAST_LIVE_LABEL, now, conns["dash"], bt,
                                tier1_titles(TIER1_FORMULA), _PRE_RELEASE_LIVE_SNAPSHOT_SQL, last, check_due=False)


def _read_marker(path: Path) -> Optional[dt.datetime]:
    try:
        return _parse_utc(path.read_text().strip())
    except (OSError, ValueError):
        return None  # missing or unreadable marker: fall back to the rows' own stamps


def _macro_calendar_check(
    now: dt.datetime, conns: dict[str, sqlite3.Connection], marker: Path, failure_marker: Path,
) -> HealthItem:
    dash = conns["dash"]
    last = _read_marker(marker)
    if last is None:
        last = _newest(dash, "SELECT recorded_at_utc FROM macro_calendar ORDER BY julianday(recorded_at_utc) DESC LIMIT 1")
    max_date = dash.execute("SELECT MAX(event_date) FROM macro_calendar").fetchone()[0]
    item = _aged_item(_MACRO, now, last, _as_utc(ops_state.get_tracking_since(conns["ops"])))
    # A FRED-maintenance failure newer than the last good refresh adds detail text only; it never moves the status.
    failed_at = _read_marker(failure_marker)
    failure_note = (f"last refresh attempt failed: FRED under maintenance ({_sast(failed_at)})"
                    if failed_at is not None and (last is None or failed_at > last) else "")
    # event_date is a plain YYYY-MM-DD date, so a string compare is a date compare.
    if max_date is not None and max_date < now.astimezone(UTC).date().isoformat():
        detail = f"no macro_calendar rows after {max_date}"
        if last is not None:
            detail += f"; last refresh {_sast(last)}"
        detail = "; ".join(part for part in (detail, failure_note) if part)
        return HealthItem(item.key, item.label, "red", item.last_success_utc, item.age_seconds,
                          item.expected_every_seconds, detail)
    if failure_note:
        detail = "; ".join(part for part in (item.detail, failure_note) if part)
        return HealthItem(item.key, item.label, item.status, item.last_success_utc, item.age_seconds,
                          item.expected_every_seconds, detail)
    return item


def _classifier_check(provider: str, now: dt.datetime, conns: dict[str, sqlite3.Connection]) -> HealthItem:
    alerts = conns["alerts"]
    label = f"Shock classifier: {provider}"
    expected = int(CLASSIFIER_WINDOW.total_seconds())
    last_success = _newest(
        alerts, "SELECT detected_at_utc FROM shock_alerts WHERE classification_method = ? "
                "ORDER BY julianday(detected_at_utc) DESC LIMIT 1", (PROVIDER_METHOD[provider],))
    until = _as_utc(alerting_store.get_provider_cooldown_until(alerts, provider))
    # The cooldown is set at the failure, for that provider's cooldown length.
    last_failure = until - dt.timedelta(minutes=_COOLDOWN_MINUTES[provider]) if until is not None else None
    failed_recently = last_failure is not None and now - last_failure <= CLASSIFIER_WINDOW
    succeeded_recently = last_success is not None and now - last_success <= CLASSIFIER_WINDOW
    age = (now - last_success).total_seconds() if last_success is not None else None
    if failed_recently and not succeeded_recently:
        status = "red"
        detail = (f"failing; last success {_sast(last_success) if last_success else 'never'}; "
                  f"cooling down until {_sast(until)}")
    elif failed_recently:
        status, detail = "amber", "intermittent failures in the last 24h"
    else:
        status, detail = "ok", ""
    return HealthItem(f"classifier:{provider}", label, status, last_success, age, expected, detail)


def _feed_check(name: str, now: dt.datetime, conns: dict[str, sqlite3.Connection]) -> HealthItem:
    key, label, expected = f"feed:{name}", f"Feed: {name}", 120
    health = alerting_store.get_source_health(conns["alerts"], name)
    if health is None:
        return HealthItem(key, label, "amber", None, None, expected, "no poll recorded yet")
    last = _as_utc(health.last_success_utc)
    age = (now - last).total_seconds() if last is not None else None
    n = health.consecutive_failures
    if is_drop_candidate(health, now):
        status = "red"
        detail = f"failing since {_sast(health.failing_since_utc)} (14+ days): candidate to drop (owner decision)"
    elif in_backoff(health, now):
        status, detail = "amber", f"in backoff until {_sast(health.backoff_until_utc)} after {n} consecutive failures"
    elif n > 0:
        status, detail = "amber", f"{n} consecutive failure(s)"
    else:
        status, detail = "ok", ""
    return HealthItem(key, label, status, last, age, expected, detail)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_health(
    now: dt.datetime, *, dash_conn: sqlite3.Connection, bt_conn: sqlite3.Connection,
    alerts_conn: sqlite3.Connection, ops_conn: sqlite3.Connection, macro_marker_path: Optional[Path] = None,
    macro_failure_marker_path: Optional[Path] = None,
) -> list[HealthItem]:
    """Every item in a fixed order; a check that raises becomes an amber 'check failed' item."""
    now = _as_utc(now)
    # Resolved here (not as a default argument) so tests can patch MACRO_MARKER_PATH.
    marker = macro_marker_path if macro_marker_path is not None else MACRO_MARKER_PATH
    failure_marker = (macro_failure_marker_path if macro_failure_marker_path is not None
                      else MACRO_FAILURE_MARKER_PATH)
    conns = {"dash": dash_conn, "bt": bt_conn, "alerts": alerts_conn, "ops": ops_conn}

    def job(key: str) -> tuple[str, str, int, Callable[[], HealthItem]]:
        spec = _JOBS[key]
        return key, spec.label, int(spec.expected.total_seconds()), lambda: _job_check(spec, now, conns)

    day = int(_D.total_seconds())
    checks: list[tuple[str, str, int, Callable[[], HealthItem]]] = [
        job("shock_poll"),
        ("outcome_confirm", _JOBS["outcome_confirm"].label, int(_JOBS["outcome_confirm"].expected.total_seconds()),
         lambda: _outcome_confirm_check(now, conns)),
        job("reaction_incremental"),
        job("reaction_baselines"),
        job("tier1_capture_daily"),
        job("tier1_capture_weekly"),
        ("tier1_research", _TIER1_RESEARCH_LABEL, day, lambda: _tier1_research_check(now, conns)),
        ("nowcast_live", _NOWCAST_LIVE_LABEL, day, lambda: _nowcast_live_check(now, conns)),
        job("shock_reality_check"),
        job("article_accumulator"),
        job("calendar_refresh"),
        (_MACRO.key, _MACRO.label, int(_MACRO.expected.total_seconds()),
         lambda: _macro_calendar_check(now, conns, marker, failure_marker)),
    ]
    for provider in CLASSIFIER_PROVIDER_ORDER:
        checks.append((f"classifier:{provider}", f"Shock classifier: {provider}", day,
                       lambda p=provider: _classifier_check(p, now, conns)))
    for name in FREE_PREVIEW_FEEDS:
        checks.append((f"feed:{name}", f"Feed: {name}", 120, lambda n=name: _feed_check(n, now, conns)))

    items = []
    for key, label, expected, check in checks:
        try:
            items.append(check())
        except Exception as exc:  # fail-open: one broken check never hides the others
            items.append(HealthItem(key, label, "amber", None, None, expected, f"check failed: {exc}"))
    return items


def overall_status(items: list[HealthItem]) -> str:
    return _worst("ok", *(item.status for item in items))


def health_item_dict(item: HealthItem) -> dict:
    """Explicit serializer for /api/health: exactly these seven keys."""
    return {
        "key": item.key,
        "label": item.label,
        "status": item.status,
        "last_success_utc": item.last_success_utc.isoformat() if item.last_success_utc is not None else None,
        "age_seconds": int(round(item.age_seconds)) if item.age_seconds is not None else None,
        "expected_every_seconds": item.expected_every_seconds,
        "detail": item.detail,
    }


def _close_all(conns) -> None:
    for conn in conns:
        try:
            conn.close()
        except Exception:
            pass


def open_data_connections() -> tuple[sqlite3.Connection, sqlite3.Connection, sqlite3.Connection]:
    """(dashboard, backtest, alerts) connections; the opened ones are closed if a later open fails."""
    opened: list[sqlite3.Connection] = []
    try:
        for opener in (webapp_store.get_connection, backtest_store.get_connection, alerting_store.get_connection):
            opened.append(opener())
    except Exception:
        _close_all(opened)
        raise
    return opened[0], opened[1], opened[2]


def open_health_connections() -> tuple[sqlite3.Connection, sqlite3.Connection, sqlite3.Connection, sqlite3.Connection]:
    """(dashboard, backtest, alerts, ops) connections; the opened ones are closed if a later open fails."""
    data = open_data_connections()
    try:
        return (*data, ops_state.get_connection())
    except Exception:
        _close_all(data)
        raise


def health_notice_text(red_items: list[HealthItem], now: dt.datetime) -> str:
    lines = [f"🩺 News engine health ({_sast(now)}): {len(red_items)} item(s) need attention"]
    for item in red_items:
        detail = item.detail or (f"last success {_sast(item.last_success_utc)}" if item.last_success_utc else "no success")
        lines.append(f"- {item.label}: {detail}")
    lines.append("Full list on the dashboard. Sent at most once per UTC day.")
    return "\n".join(lines)


def maybe_send_health_notice(
    now: Optional[dt.datetime] = None, *, send: Optional[Callable[[str], bool]] = None,
    connections: Optional[tuple] = None,
) -> bool:
    """
    At most one Telegram notice per UTC day listing the RED items (B2's
    once-per-day pattern). The ops ledger is checked first, so the other
    700-odd polls of the day cost one small DB open and one query (the
    dashboard, backtest and alerts DBs are opened only while the day is
    still open). The day is claimed (atomic INSERT OR IGNORE) before the
    send, so the shock poll and the outcome job cannot both send; a failed
    send deletes the claim, so the next trigger retries. Never raises: it
    runs at the end of the shock poll and the outcome job, and must never
    fail them. Closes connections it opened (those passed in stay open).
    """
    opened: list[sqlite3.Connection] = []
    try:
        now = _as_utc(now) if now is not None else dt.datetime.now(UTC)
        utc_day = now.date()
        if connections is None:
            ops = ops_state.get_connection()
            opened.append(ops)
            if ops_state.health_notice_sent(ops, utc_day):
                return False
            data = open_data_connections()
            opened.extend(data)
            dash, bt, alerts = data
        else:
            dash, bt, alerts, ops = connections
            if ops_state.health_notice_sent(ops, utc_day):
                return False
        items = build_health(now, dash_conn=dash, bt_conn=bt, alerts_conn=alerts, ops_conn=ops)
        red = [item for item in items if item.status == "red"]
        if not red:
            return False
        if not ops_state.claim_health_notice(ops, utc_day, now, ", ".join(item.key for item in red)[:300]):
            return False  # the other trigger claimed the day first
        sender = send if send is not None else notify_telegram.send_notice
        try:
            sent = sender(health_notice_text(red, now))
        except Exception:
            ops_state.release_health_notice(ops, utc_day)
            raise
        if not sent:
            ops_state.release_health_notice(ops, utc_day)
            return False
        return True
    except Exception as exc:  # fail-open: the notice must never break the job that triggered it
        print(f"[ops.health] WARNING: health notice skipped: {exc}")
        return False
    finally:
        _close_all(opened)
