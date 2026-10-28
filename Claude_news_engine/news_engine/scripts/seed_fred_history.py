"""
Seed the 2026 USD event_history from FRED/ALFRED first prints (B8 U1, 2026-10-27).

Forex Factory's feed never carries an `actual` (every one comes from a
fallback), so most 2026 High-impact releases have no actual, and some have
no row at all. This script reads each seed title's release-day vintage
(data_layer/fred_history.py: the value as published that day, never the
revised number) and:

  - INSERTS a row for a release with no USD row within 3 days
    (forecast NULL, previous = prior period as published that day,
    actual = first print, source='fred', country='USD', impact NULL);
  - FILLS the actual of an existing USD row whose actual is NULL
    (forecast/previous/impact untouched).

Safety:
  - DRY RUN by default: nothing is written (not even a backup). `--apply` writes.
  - Two phases: every FRED fetch and decision first, then (only when applying)
    one pre-write backup `<db>.pre_b8_<date>`, then the writes. A FRED
    maintenance page or fetch error mid-run therefore leaves the DB untouched.
  - Verification gate per title: stored first-print actuals (and FF's `previous`)
    are compared with FRED's; >= 80% agreement = verified, below = suspect
    (never written), no comparison possible = unverified (written only with
    --allow-unverified), FRED error for the series = unavailable.
  - Idempotent: a second --apply adds zero rows.
  - Rollback key: every row one --apply inserts shares recorded_at_utc = that
    run's start time (printed as "seed run recorded_at_utc"), with impact and
    forecast NULL. Forex Factory rows always carry an impact, so that triple
    never matches a live row that a later FRED fill relabels source='fred'.

The report also lists the titles whose graded rows (surprise_direction set)
among the EVENT_HISTORY_WINDOW most recent rows change: that window feeds the
accumulator's trend prior and the History trend text. A seeded row has no
forecast, so no direction, and can push older graded rows out of the window;
a fill can give a title graded rows it never had.

Times are shown in SAST (UTC+2) with the stored UTC value beside them.

Usage:
    python scripts/seed_fred_history.py                       # dry run, all seed titles
    python scripts/seed_fred_history.py --title "CPI m/m"     # one title (repeatable)
    python scripts/seed_fred_history.py --apply               # write (backs up the DB first)
    python scripts/seed_fred_history.py --apply --allow-unverified
    python scripts/seed_fred_history.py --rollback "<run key>"           # count that run's inserts (read-only)
    python scripts/seed_fred_history.py --rollback "<run key>" --apply   # delete them
Exit codes: 0 ok, 2 no FRED_API_KEY (or, for --rollback, no DB / bad key),
3 FRED under maintenance (nothing written), 4 the --report folder does not
exist (checked before any fetch or write).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import FRED_API_KEY, LOCAL_TZ, MIN_OCCURRENCES_FOR_TREND_PRIOR, NY_TZ, UTC_TZ
from data_layer.calendar_feed import EconomicEvent, classify_surprise
from data_layer.fred_history import (
    FRED_HISTORY_SPECS, FredClient, FredFetchError, FredMaintenanceError, VintageReading,
    actual_check, previous_check, releases_between,
)
import webapp.store as store

# A title is "verified" when at least this share of its comparisons with stored rows agree.
VERIFY_AGREEMENT_THRESHOLD = 0.8
# A stored row this close to the computed release time is the same release (FF can sit hours/a day off).
DEDUP_WINDOW_DAYS = 3
SEED_SOURCE = "fred"
DEFAULT_START = dt.date(2026, 1, 1)
DEFAULT_PACE_SECONDS = 0.6          # FRED allows 120 requests/min


@dataclass
class SeedReport:
    inserted: list[tuple[str, str]] = field(default_factory=list)     # (title, event_time_utc iso)
    filled: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    title_status: dict[str, str] = field(default_factory=dict)        # verified | suspect | unverified | unavailable
    agreement: dict[str, tuple[int, int]] = field(default_factory=dict)  # title -> (matches, comparisons)
    new_release_minutes: int = 0
    details: list[str] = field(default_factory=list)                  # one printable line per insert/fill
    run_at_utc: str = ""                                              # recorded_at_utc of every row this run inserts
    # (title, graded rows in the trend window before, after) for titles where the count changes
    trend_window_changes: list[tuple[str, int, int]] = field(default_factory=list)


@dataclass
class _Queued:
    kind: str                       # "insert" | "fill"
    title: str
    event_time: dt.datetime
    reading: VintageReading
    row_id: Optional[int] = None
    surprise_direction: Optional[str] = None


def _is_usd(row: sqlite3.Row) -> bool:
    return row["country"] == "USD"


def _event_time_utc(title: str, vintage_date: dt.date) -> dt.datetime:
    """The title's New York release time on the vintage date, as UTC."""
    release_time = FRED_HISTORY_SPECS[title].release_time_et
    return dt.datetime.combine(vintage_date, release_time, NY_TZ).astimezone(UTC_TZ)


def _status(matches: int, comparisons: int, unavailable: bool) -> str:
    if unavailable:
        return "unavailable"
    if comparisons == 0:
        return "unverified"
    return "verified" if matches / comparisons >= VERIFY_AGREEMENT_THRESHOLD else "suspect"


def _plan_title(
    conn: sqlite3.Connection, title: str, readings: list[VintageReading], now: dt.datetime, report: SeedReport,
) -> list[_Queued]:
    """Decide (no writes) what each release needs; also accumulates agreement for the gate."""
    queued: list[_Queued] = []
    matches = comparisons = 0
    for reading in readings:
        event_time = _event_time_utc(title, reading.vintage_date)
        if event_time >= now:
            continue                                   # not released yet by the New York clock
        near = store.find_event_history_near(conn, title, event_time, DEDUP_WINDOW_DAYS)
        usd_rows = [r for r in near if _is_usd(r)]
        if not usd_rows and any(r["country"] is None for r in near):
            report.skipped.append(f"{title}@{event_time.isoformat()}: ambiguous existing row (country NULL)")
            continue
        if not usd_rows:                                # none, or foreign prints only -> treat as absent
            queued.append(_Queued("insert", title, event_time, reading))
            continue
        row = min(usd_rows, key=lambda r: abs(dt.datetime.fromisoformat(r["event_time_utc"]) - event_time))
        checks = (actual_check(reading, row["actual"]), previous_check(reading, row["previous"]))
        for c in checks:
            if c != "no_reference":
                comparisons += 1
                matches += c == "match"
        if row["actual"] is not None:
            continue
        if checks[1] == "mismatch":
            report.skipped.append(f"{title}@{row['event_time_utc']}: previous mismatch, actual not filled")
            continue
        event = EconomicEvent(title, "USD", row["impact"] or "High", event_time,
                              forecast=row["forecast"], previous=row["previous"], actual=reading.actual)
        queued.append(_Queued("fill", title, event_time, reading, row_id=row["id"],
                              surprise_direction=classify_surprise(event)))
    report.agreement[title] = (matches, comparisons)
    return queued


def _graded_in_window(rows: list[tuple[str, Optional[str]]]) -> int:
    """Graded rows among the EVENT_HISTORY_WINDOW most recent, as store.get_event_history orders them."""
    newest = sorted(rows, key=lambda r: r[0], reverse=True)[:store.EVENT_HISTORY_WINDOW]
    return sum(1 for _, direction in newest if direction is not None)


def _trend_window_changes(conn: sqlite3.Connection, approved: list[_Queued]) -> list[tuple[str, int, int]]:
    """
    Simulates the approved writes (no DB change) and returns (title, before,
    after) for every touched title whose graded count in the trend window moves.
    Inserts add a row with no direction; fills set the row's direction.
    """
    changes: list[tuple[str, int, int]] = []
    for title in sorted({q.title for q in approved}):
        rows = {
            r["id"]: (r["event_time_utc"], r["surprise_direction"])
            for r in conn.execute(
                "SELECT id, event_time_utc, surprise_direction FROM event_history WHERE event_title = ?", (title,)
            )
        }
        before = _graded_in_window(list(rows.values()))
        simulated = dict(rows)
        for n, q in enumerate(x for x in approved if x.title == title):
            if q.kind == "fill":
                simulated[q.row_id] = (simulated[q.row_id][0], q.surprise_direction)
            else:
                simulated[f"new{n}"] = (q.event_time.isoformat(), None)
        after = _graded_in_window(list(simulated.values()))
        if after != before:
            changes.append((title, before, after))
    return changes


def _detail(q: _Queued) -> str:
    sast = q.event_time.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M SAST")
    return (f"{q.kind.upper():6} {q.title}  {sast} ({q.event_time.isoformat()})  "
            f"actual={q.reading.actual} previous={q.reading.previous}")


def run_seed(
    conn: sqlite3.Connection,
    client: FredClient,
    now: dt.datetime,
    start: dt.date = DEFAULT_START,
    apply: bool = False,
    allow_unverified: bool = False,
    titles: Optional[list[str]] = None,
    before_first_write: Optional[Callable[[], object]] = None,
) -> SeedReport:
    """
    Phase 1: every FRED fetch and decision (FredMaintenanceError propagates,
    leaving the DB untouched). Phase 2 (only when `apply` and something
    passes the gate): `before_first_write()` once, then the writes. Without
    `apply` the report lists what WOULD be written and nothing is touched.
    """
    report = SeedReport(run_at_utc=now.isoformat())
    wanted = titles if titles else [t for t, s in FRED_HISTORY_SPECS.items() if s.seed]
    plans: dict[str, list[_Queued]] = {}
    for title in wanted:
        if title not in FRED_HISTORY_SPECS or FRED_HISTORY_SPECS[title].release_time_et is None:
            report.title_status[title] = "unavailable"
            report.skipped.append(f"{title}: no seedable FRED mapping")
            continue
        try:
            readings = releases_between(client, title, start, now.date())
        except FredFetchError as exc:
            report.title_status[title] = "unavailable"
            report.skipped.append(f"{title}: {exc}")
            continue
        plans[title] = _plan_title(conn, title, readings, now, report)
        matches, comparisons = report.agreement[title]
        report.title_status[title] = _status(matches, comparisons, unavailable=False)

    approved: list[_Queued] = []
    for title, queue in plans.items():
        status = report.title_status[title]
        if status == "verified" or (status == "unverified" and allow_unverified):
            approved.extend(queue)
        elif queue:
            report.skipped.append(f"{title}: {len(queue)} write(s) withheld, title is {status}")

    existing_minutes = {
        r[0] for r in conn.execute("SELECT DISTINCT substr(event_time_utc, 1, 16) FROM event_history WHERE country = 'USD'")
    }
    report.new_release_minutes = len({
        q.event_time.isoformat()[:16] for q in approved if q.kind == "insert"
    } - existing_minutes)
    report.trend_window_changes = _trend_window_changes(conn, approved)

    if not apply:                                      # dry run: report the plan, write nothing
        for q in approved:
            (report.inserted if q.kind == "insert" else report.filled).append((q.title, q.event_time.isoformat()))
            report.details.append(_detail(q))
        return report

    if approved and before_first_write is not None:
        before_first_write()
    for q in approved:
        if q.kind == "insert":
            ok = store.insert_event_history_if_absent(
                conn, q.title, q.event_time, None, q.reading.previous, q.reading.actual, None,
                SEED_SOURCE, None, "USD", now,
            )
            target = report.inserted
        else:
            ok = store.fill_actual_if_missing(conn, q.row_id, q.reading.actual, q.surprise_direction, SEED_SOURCE, now)
            target = report.filled
        if ok:
            target.append((q.title, q.event_time.isoformat()))
            report.details.append(_detail(q))
        else:
            report.skipped.append(f"{q.title}@{q.event_time.isoformat()}: row appeared meanwhile, not written")
    return report


def backup_db(db_path: Path, now: dt.datetime) -> Path:
    """SQLite-API copy to `<db>.pre_b8_<YYYY-MM-DD>`; never overwrites (appends _2, _3, ...)."""
    base = Path(f"{db_path}.pre_b8_{now.date().isoformat()}")
    target, n = base, 1
    while target.exists():
        n += 1
        target = Path(f"{base}_{n}")
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return target


def rollback_seed_inserts(conn: sqlite3.Connection, run_at_utc: str, apply: bool = False) -> int:
    """
    Rows ONE seed --apply inserted (its printed run key), counted or, with
    `apply`, deleted. The predicate is the seed insert's exact signature:
    source 'fred', impact NULL, forecast NULL and recorded_at_utc equal to
    the run key. A Forex Factory row relabelled source='fred' by a later FRED
    fill (same-day fast path or hourly backfill) keeps its own recorded_at_utc
    and an impact, so it never matches. A seeded row that FF later upserted
    (impact filled in) is left alone too - conservative, never over-deletes.
    """
    when = dt.datetime.fromisoformat(run_at_utc)          # rejects a typo'd key before touching anything
    if when.tzinfo is None:
        raise ValueError(f"rollback key must carry a UTC offset: {run_at_utc!r}")
    where = ("FROM event_history WHERE source = ? AND impact IS NULL AND forecast IS NULL "
             "AND recorded_at_utc = ?")
    params = (SEED_SOURCE, run_at_utc)
    if not apply:
        return conn.execute(f"SELECT COUNT(*) {where}", params).fetchone()[0]
    deleted = conn.execute(f"DELETE {where}", params).rowcount
    conn.commit()
    return deleted


def format_report(report: SeedReport, apply: bool) -> str:
    if not apply:
        header = "DRY RUN - nothing written"
    elif report.inserted or report.filled:
        header = "APPLIED - rows written"
    else:
        header = "APPLIED - nothing to write"
    lines = [header]
    if apply:
        lines.append(f"seed run recorded_at_utc (rollback key for this run's inserts): {report.run_at_utc}")
    lines.append(f"inserts: {len(report.inserted)}  fills: {len(report.filled)}  "
                 f"new release minutes for the reaction job: {report.new_release_minutes}")
    lines.extend(report.details)
    lines.append(f"trend window (graded rows among the {store.EVENT_HISTORY_WINDOW} most recent; "
                 f"trend prior needs {MIN_OCCURRENCES_FOR_TREND_PRIOR}):")
    if not report.trend_window_changes:
        lines.append("  no title changes")
    for title, before, after in report.trend_window_changes:
        lines.append(f"  {title}: {before} -> {after}")
    lines.append("title status:")
    for title, status in report.title_status.items():
        m, c = report.agreement.get(title, (0, 0))
        lines.append(f"  {title}: {status} (agreement {m}/{c})")
    if report.skipped:
        lines.append("skipped:")
        lines.extend(f"  {s}" for s in report.skipped)
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Seed 2026 USD event_history from FRED/ALFRED first prints.")
    parser.add_argument("--db", default=str(store.DB_PATH), help="dashboard.db path (default: webapp/dashboard.db)")
    parser.add_argument("--apply", action="store_true", help="write (default is a dry run)")
    parser.add_argument("--allow-unverified", action="store_true", help="also write titles with nothing to verify against")
    parser.add_argument("--title", action="append", help="restrict to this FF title (repeatable)")
    parser.add_argument("--report", help="also write the report text to this path")
    parser.add_argument("--pace", type=float, default=DEFAULT_PACE_SECONDS, help="seconds between FRED requests")
    parser.add_argument("--rollback", metavar="RUN_KEY",
                        help="count (or with --apply delete) the rows one seed run inserted; RUN_KEY is the printed "
                             "'seed run recorded_at_utc'. No FRED access.")
    args = parser.parse_args(argv)

    if args.rollback is not None:
        db_path = Path(args.db)
        if not db_path.is_file():
            print(f"database not found: {db_path} - nothing done.")
            return 2
        # The count (no --apply) opens the DB read-only; only the delete opens it for writing.
        conn = (sqlite3.connect(str(db_path)) if args.apply
                else sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True))
        try:
            n = rollback_seed_inserts(conn, args.rollback, apply=args.apply)
        except ValueError as exc:
            print(f"bad rollback key: {exc} - nothing done.")
            return 2
        finally:
            conn.close()
        print(f"{'deleted' if args.apply else 'would delete (dry run)'}: {n} seeded rows of run {args.rollback}")
        return 0

    if not FRED_API_KEY:
        print("FRED_API_KEY is not set - nothing done.")
        return 2
    # Fail before any fetch or write: a missing folder used to raise only after the DB writes.
    if args.report and not Path(args.report).parent.is_dir():
        print(f"--report folder does not exist: {Path(args.report).parent} - nothing done.")
        return 4

    db_path = Path(args.db)
    now = dt.datetime.now(UTC_TZ)
    conn = store.get_connection(db_path)
    try:
        report = run_seed(
            conn, FredClient(FRED_API_KEY, pace_seconds=args.pace), now,
            apply=args.apply, allow_unverified=args.allow_unverified, titles=args.title,
            before_first_write=lambda: print(f"backup written: {backup_db(db_path, now)}"),
        )
    except FredMaintenanceError:
        print("FRED under maintenance - nothing written")
        return 3
    finally:
        conn.close()

    text = format_report(report, args.apply)
    print(text)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
