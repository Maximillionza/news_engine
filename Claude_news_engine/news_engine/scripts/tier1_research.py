"""
Research-task CLI for judgment-tier Tier 1 calls (B3 / T5 skip, T7). Replaces the free-hand Python the research
task used to write, so fixed commands can be pre-approved and the rules live in code, not in prompt text.

    python scripts/tier1_research.py plan [--days 8]
    python scripts/tier1_research.py record-call        --event T --release ISO --instrument S --value V --confidence C --source SRC --direction D
    python scripts/tier1_research.py record-late-check (same arguments)

plan prints JSON: every USD judgment-tier event (data_layer.tier1_events) within --days, with one status per
tracked instrument: needs_call, covered, or late_check_due (with the reason and the call of record).
record-call logs the FIRST pre-release call for an occurrence and refuses a second one (the first call stands),
a formula-tier title (CPI m/m and Core CPI m/m come from the Cleveland capture), an untracked instrument, a
release time without a UTC offset, and a release that has already happened.
record-late-check appends a re-check to tier1_late_checks only when plan says it is due; it never changes the
call of record.

--dash-db is opened read-only (it supplies events and tracked instruments); --bt-db defaults to the live backtest
DB. Exit 0 ok, 2 refused (one-line reason on stderr).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Optional

# Allow `python scripts/tier1_research.py ...` (script dir, not the app root, is on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.settings import LOCAL_TZ  # noqa: E402
from data_layer.tier1_events import (  # noqa: E402
    TIER1_FORMULA, TIER1_JUDGMENT, TIER1_RESEARCH_LOOKAHEAD, late_check_reason, tier1_titles,
)
from scoring import backtest_store  # noqa: E402
from scripts.backfill_tier1_reconstructed import open_dash_readonly  # noqa: E402
from scripts.capture_nowcast_snapshot import parse_aware  # noqa: E402
from webapp.store import list_tracked_symbols  # noqa: E402

UTC = dt.timezone.utc


class Refused(Exception):
    """A request the CLI will not act on; the message is the one-line reason printed on stderr."""


def _as_utc(text: str) -> Optional[dt.datetime]:
    """Stored event time -> aware UTC (naive stamps are UTC); None when unreadable."""
    try:
        parsed = dt.datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _call_dict(row: backtest_store.Tier1PredictionRow) -> dict:
    return {"id": row.id, "value": row.value, "confidence": row.confidence, "source": row.source,
            "predicted_direction": row.predicted_direction, "logged_at_utc": row.logged_at_utc}


def _late_check_state(bt_conn, title: str, symbol: str, release: dt.datetime, now: dt.datetime):
    """(call_of_record, due_reason): the reason is None when no late check is due right now."""
    call = backtest_store.get_latest_tier1_prediction_for_occurrence(bt_conn, title, symbol, release)
    if call is None:
        return None, None
    checks = backtest_store.get_tier1_late_checks_for_occurrence(bt_conn, title, symbol, release)
    newest = _as_utc(call.logged_at_utc)
    for check in checks:                       # oldest first, so the last one is the newest reading
        newest = max(newest, _as_utc(check.checked_at_utc))
    has_window_check = any(check.reason == "release_within_24h" for check in checks)
    return call, late_check_reason(newest, release, now, has_window_check)


def build_plan(dash_conn, bt_conn, now: dt.datetime, days: float) -> list[dict]:
    """Judgment-tier USD events in (now, now + days], each with a per-instrument status."""
    titles = tier1_titles(TIER1_JUDGMENT)
    marks = ",".join("?" for _ in titles)
    rows = dash_conn.execute(
        f"SELECT DISTINCT event_title, event_time_utc FROM event_history "
        f"WHERE country = 'USD' AND event_title IN ({marks})", titles).fetchall()
    symbols = list_tracked_symbols(dash_conn)
    events = []
    for row in rows:
        release = _as_utc(row[1])
        if release is None or not now < release <= now + dt.timedelta(days=days):
            continue
        instruments = {}
        for symbol in symbols:
            call, reason = _late_check_state(bt_conn, row[0], symbol, release, now)
            if call is None:
                instruments[symbol] = {"status": "needs_call"}
            elif reason is not None:
                instruments[symbol] = {"status": "late_check_due", "reason": reason, "call": _call_dict(call)}
            else:
                instruments[symbol] = {"status": "covered", "call": _call_dict(call)}
        events.append({"event_title": row[0], "event_time_utc": release.isoformat(),
                       "event_time_sast": f"{release.astimezone(LOCAL_TZ):%Y-%m-%d %H:%M} SAST",
                       "tier": TIER1_JUDGMENT, "instruments": instruments})
    return sorted(events, key=lambda e: (e["event_time_utc"], e["event_title"]))


def _check_target(args: argparse.Namespace, dash_conn, now: dt.datetime) -> dt.datetime:
    """Shared validation for record-call / record-late-check; returns the aware release time."""
    if args.event in tier1_titles(TIER1_FORMULA):
        raise Refused(f"{args.event!r} is a formula-tier event: the Cleveland Fed formula capture "
                      f"(capture_nowcast_from_cleveland.py) writes its call, do not log one by hand")
    if args.event not in tier1_titles(TIER1_JUDGMENT):
        raise Refused(f"{args.event!r} is not a judgment-tier Tier 1 event")
    if args.instrument not in list_tracked_symbols(dash_conn):
        raise Refused(f"instrument {args.instrument!r} is not tracked")
    try:
        release = parse_aware(args.release).astimezone(UTC)  # stored/keyed as +00:00 everywhere
    except ValueError as exc:
        raise Refused(str(exc))
    if now >= release:
        raise Refused(f"release {release.isoformat()} has already happened: a call or check now is hindsight")
    return release


def _record_call(args: argparse.Namespace, dash_conn, bt_conn, now: dt.datetime) -> str:
    release = _check_target(args, dash_conn, now)
    if backtest_store.get_latest_tier1_prediction_for_occurrence(bt_conn, args.event, args.instrument, release):
        raise Refused("a pre-release call already exists: the first pre-release call stands; use record-late-check")
    row_id = backtest_store.record_tier1_prediction(
        bt_conn, args.event, args.instrument, release, args.value, args.confidence, args.source,
        args.direction, logged_at_utc=now)
    return str(row_id)


def _record_late_check(args: argparse.Namespace, dash_conn, bt_conn, now: dt.datetime) -> str:
    release = _check_target(args, dash_conn, now)
    call, reason = _late_check_state(bt_conn, args.event, args.instrument, release, now)
    if call is None:
        raise Refused("no call of record for this occurrence: use record-call first")
    if reason is None:
        raise Refused("late check not due: the call (or its last check) is fresh, or the 24h check was already made")
    row_id = backtest_store.record_tier1_late_check(
        bt_conn, args.event, args.instrument, release, args.value, args.confidence, args.direction,
        args.source, reason, checked_at_utc=now)
    outcome = "same" if args.direction == call.predicted_direction else "changed"
    return f"late check {row_id}: {outcome} ({reason})"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_dbs(p: argparse.ArgumentParser) -> None:
        p.add_argument("--dash-db", type=Path, default=None, help="dashboard.db (read-only; default: live)")
        p.add_argument("--bt-db", type=Path, default=None, help="backtest_log.db (default: live)")

    plan = sub.add_parser("plan", help="print the judgment-tier events due a call or late check as JSON")
    add_dbs(plan)
    plan.add_argument("--days", type=float, default=TIER1_RESEARCH_LOOKAHEAD.days,
                      help="look this many days ahead (default 8)")
    for name, help_text in (("record-call", "log the first pre-release call for one instrument"),
                            ("record-late-check", "append a late check (only when plan says it is due)")):
        p = sub.add_parser(name, help=help_text)
        add_dbs(p)
        p.add_argument("--event", required=True, help="event title, e.g. 'PPI m/m'")
        p.add_argument("--release", required=True, help="release time with UTC offset, e.g. 2026-11-12T13:30:00+00:00")
        p.add_argument("--instrument", required=True, help="tracked symbol, e.g. XAUUSD")
        p.add_argument("--value", required=True, help="the researched finding, in plain words")
        p.add_argument("--confidence", required=True, help="Certain | Likely | Guessing")
        p.add_argument("--source", required=True, help="where the finding came from")
        p.add_argument("--direction", required=True, help="bullish | bearish | neutral (for this instrument)")
    return parser


def main(argv: Optional[list[str]] = None, now: Optional[dt.datetime] = None) -> int:
    """now is a test seam; the research task uses the real clock."""
    args = _build_parser().parse_args(argv)
    now = now or dt.datetime.now(UTC)
    dash_conn = open_dash_readonly(args.dash_db)
    bt_conn = backtest_store.get_connection(args.bt_db)
    try:
        if args.command == "plan":
            print(json.dumps(build_plan(dash_conn, bt_conn, now, args.days), indent=2))
        elif args.command == "record-call":
            print(_record_call(args, dash_conn, bt_conn, now))
        else:
            print(_record_late_check(args, dash_conn, bt_conn, now))
    except (Refused, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    finally:
        dash_conn.close()
        bt_conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
