"""
FIX task 2 (owner ruling R2, 2026-11-03): re-derive the stored surprise_direction
labels in event_history under the one in-line definition (an actual is "in line"
only when it equals the forecast at the forecast's own published precision; the
5%-of-forecast band is retired, data_layer/surprise_side.py).

Only the `surprise_direction` label (and its `updated_at_utc`) changes: actual,
source, forecast and previous are never touched. Rows whose title is untracked
or whose numbers do not parse derive None and are left exactly as they are, so
a NULL label stays NULL and an existing label is never blanked.

Dry run (default) opens the DB through a SQLite `mode=ro` URI and writes nothing.
`--apply` runs ONE transaction of
    UPDATE event_history SET surprise_direction = ?, updated_at_utc = ?
    WHERE id = ? AND surprise_direction IS ?
so a second run finds nothing to change (idempotent). It makes no backup: the
deploy runbook (docs/fix-deploy.md) copies the DB first. --apply needs an
explicit --db so it can never hit the default path by accident.

Usage:
    python scripts/rederive_surprise_direction.py --db <copy of dashboard.db>
    python scripts/rederive_surprise_direction.py --db <db> --apply --report <folder>

Exit codes: 0 ok, 2 database missing (or --apply without --db), 4 --report folder missing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import LOCAL_TZ, UTC_TZ
from data_layer.calendar_feed import EconomicEvent, classify_surprise


@dataclass
class RederiveReport:
    """Outcome of one pass: per-title Counter of (old, new) label changes."""
    total: int = 0                      # rows with an actual that were examined
    unchanged: int = 0                  # derived label equals the stored one
    skipped: int = 0                    # derived None (untracked / unparsable): row left as is
    changes: dict[str, Counter] = field(default_factory=dict)   # title -> Counter[(old, new)]
    writes: int = 0                     # rows actually updated (0 on a dry run)

    @property
    def changed(self) -> int:
        return sum(sum(counter.values()) for counter in self.changes.values())


def _open(db_path: Path, read_only: bool) -> sqlite3.Connection:
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"database not found: {path}")
    if read_only:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _derive(row: sqlite3.Row) -> Optional[str]:
    """Label for one stored row via the same classify_surprise the live writers use."""
    event_time = dt.datetime.fromisoformat(row["event_time_utc"])
    event = EconomicEvent(
        title=row["event_title"], country=row["country"] or "USD", impact=row["impact"] or "",
        event_time_utc=event_time, forecast=row["forecast"], previous=row["previous"], actual=row["actual"],
    )
    return classify_surprise(event)


def rederive(conn: sqlite3.Connection, now: dt.datetime, apply: bool) -> RederiveReport:
    """Re-derive every row that has an actual; with apply=True write the changes in one transaction."""
    report = RederiveReport()
    pending: list[tuple[int, Optional[str], str]] = []   # (id, old label, new label)
    rows = conn.execute(
        "SELECT id, event_title, event_time_utc, forecast, previous, actual, surprise_direction, impact, country "
        "FROM event_history WHERE actual IS NOT NULL ORDER BY event_title, event_time_utc"
    ).fetchall()
    for row in rows:
        report.total += 1
        new = _derive(row)
        old = row["surprise_direction"]
        if new is None:
            report.skipped += 1
            continue
        if new == old:
            report.unchanged += 1
            continue
        report.changes.setdefault(row["event_title"], Counter())[(old, new)] += 1
        pending.append((row["id"], old, new))

    if apply and pending:
        stamp = now.isoformat()
        with conn:   # one transaction: all rows or none
            for row_id, old, new in pending:
                cursor = conn.execute(
                    "UPDATE event_history SET surprise_direction = ?, updated_at_utc = ? "
                    "WHERE id = ? AND surprise_direction IS ?",
                    (new, stamp, row_id, old),
                )
                report.writes += cursor.rowcount
    return report


def format_report(report: RederiveReport, now: dt.datetime, apply: bool) -> str:
    """Plain-text report; times in SAST with the UTC value beside them."""
    sast = now.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M SAST")
    lines = [
        f"Surprise-direction re-derive ({'APPLY' if apply else 'dry run'}) at {sast} ({now.astimezone(UTC_TZ).isoformat()})",
        f"rows with an actual: {report.total}; unchanged: {report.unchanged}; "
        f"left as is (untracked/unparsable): {report.skipped}; to change: {report.changed}; written: {report.writes}",
    ]
    for title in sorted(report.changes):
        counter = report.changes[title]
        pieces = ", ".join(f"{old} -> {new}: {count}" for (old, new), count in sorted(counter.items(), key=str))
        lines.append(f"  {title}: {pieces}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Re-derive event_history.surprise_direction under the one in-line rule")
    parser.add_argument("--db", default=None, help="dashboard.db path (required with --apply)")
    parser.add_argument("--apply", action="store_true", help="write the changes (default is a read-only dry run)")
    parser.add_argument("--report", default=None, metavar="FOLDER", help="also write the report text into this existing folder")
    args = parser.parse_args(argv)

    if args.report and not Path(args.report).is_dir():
        print(f"report folder not found: {args.report}", file=sys.stderr)
        return 4
    if args.apply and not args.db:
        print("--apply needs an explicit --db", file=sys.stderr)
        return 2
    if args.db:
        db_path = Path(args.db)
    else:
        from webapp.store import DB_PATH
        db_path = DB_PATH
    try:
        conn = _open(db_path, read_only=not args.apply)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    now = dt.datetime.now(UTC_TZ)
    try:
        report = rederive(conn, now, apply=args.apply)
    finally:
        conn.close()
    text = format_report(report, now, args.apply)
    print(text)
    if args.report:
        stamp = now.astimezone(LOCAL_TZ).strftime("%Y%m%d-%H%M")
        (Path(args.report) / f"rederive_surprise_direction_{stamp}.txt").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    # Example: dry run against a COPY of dashboard.db (never the live file):
    #   python scripts/rederive_surprise_direction.py --db %TEMP%\dashboard_copy.db
    sys.exit(main())
