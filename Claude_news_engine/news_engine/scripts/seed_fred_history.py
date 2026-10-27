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

Times are shown in SAST (UTC+2) with the stored UTC value beside them.

Usage:
    python scripts/seed_fred_history.py                       # dry run, all seed titles
    python scripts/seed_fred_history.py --title "CPI m/m"     # one title (repeatable)
    python scripts/seed_fred_history.py --apply               # write (backs up the DB first)
    python scripts/seed_fred_history.py --apply --allow-unverified
Exit codes: 0 ok, 2 no FRED_API_KEY, 3 FRED under maintenance (nothing written).
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

from config.settings import FRED_API_KEY, LOCAL_TZ, NY_TZ, UTC_TZ
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
    report = SeedReport()
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


def format_report(report: SeedReport, apply: bool) -> str:
    lines = ["APPLIED - rows written" if apply else "DRY RUN - nothing written"]
    lines.append(f"inserts: {len(report.inserted)}  fills: {len(report.filled)}  "
                 f"new release minutes for the reaction job: {report.new_release_minutes}")
    lines.extend(report.details)
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
    args = parser.parse_args(argv)

    if not FRED_API_KEY:
        print("FRED_API_KEY is not set - nothing done.")
        return 2

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
