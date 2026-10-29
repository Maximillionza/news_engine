"""
Backlog backfill of official-publisher actuals (ACT Task 5).

Fills the USD rows released since --since (default 2026-07-28) that still have
no actual, from the official publishers, using exactly the poller's rules:
coverage bucket, verified gate status, decide_fill (expected period present,
older rows of revised series never relabelled as first prints, FF's `previous`
on the next release must agree) and store.fill_actual_if_missing (first writer
wins, never overwrites). Every row ends in exactly one outcome per title.

DRY RUN BY DEFAULT: the database is opened `mode=ro` and nothing is written.
`--apply` opens it read-write and fills; a rerun then reports `filled` 0. The
controller backs up dashboard.db before an --apply (no backup is made here).

API keys come from `--env-file` (or the app's .env) and are never printed.
Times are shown in SAST (UTC+2) with the stored UTC value beside them.

Usage:
    python scripts/backfill_official_actuals.py --db <dashboard.db> --env-file <.env>
    python scripts/backfill_official_actuals.py ... --title "CPI m/m" --since 2026-09-01
    python scripts/backfill_official_actuals.py ... --apply --report backfill-report.txt
Exit codes: 0 ok, 2 the database does not exist, 4 the --report folder does not exist.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import LOCAL_TZ
from data_layer.calendar_feed import EconomicEvent, classify_surprise
from data_layer.official_actuals.coverage import (
    GateResult, coverage_for, enabled_titles, later_release_for, load_gate_results,
)
from data_layer.official_actuals.fetch import FetchOutcome, fetch_for_specs, series_key
from data_layer.official_actuals.http import KeyInactiveError, requests_fetcher
from data_layer.official_actuals.keys import load_keys
from data_layer.official_actuals.registry import OFFICIAL_SPECS, OfficialSpec, decide_fill
from ops.health import ACTUALS_SLA_AFTER
import webapp.store as store

_UTC = dt.timezone.utc

DEFAULT_SINCE = dt.date(2026, 7, 28)
OUTCOMES = ("filled", "would fill", "already filled", "no actual expected", "proprietary", "not mapped",
            "gate disabled", "key inactive", "source error", "awaiting publication",
            "revised since release", "disagrees with FF previous")
LIMITATION = ("Official APIs serve today's revised numbers; older rows of revised series are left to the "
              "FRED/ALFRED backfill.")

FetchFn = Callable[[list[OfficialSpec], dt.date], FetchOutcome]


@dataclass
class BacklogReport:
    per_title: dict[str, Counter] = field(default_factory=dict)     # title -> outcome -> count
    details: list[str] = field(default_factory=list)                # one line per fill / would-fill, SAST + stored UTC

    def add(self, title: str, outcome: str) -> None:
        self.per_title.setdefault(title, Counter())[outcome] += 1

    def totals(self) -> Counter:
        total: Counter = Counter()
        for counter in self.per_title.values():
            total.update(counter)
        return total


def _parse_utc(text: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(text)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=_UTC)


def _sast(stamp: str) -> str:
    return f"{_parse_utc(stamp).astimezone(LOCAL_TZ):%Y-%m-%d %H:%M} SAST (stored {stamp})"


def _decision_outcome(reason: str) -> str:
    """Maps a decide_fill refusal reason onto an OUTCOMES label."""
    if reason.startswith("revised since release"):
        return "revised since release"
    if reason.startswith("disagrees with FF previous"):
        return "disagrees with FF previous"
    return "awaiting publication"        # also the re-estimate "not distinguishable" case (reason kept in details)


def run_backlog(conn: sqlite3.Connection, now: dt.datetime, fetch: FetchFn, gate: Mapping[str, GateResult],
                since: dt.date = DEFAULT_SINCE, apply: bool = False,
                titles: Optional[list[str]] = None) -> BacklogReport:
    """Classify every USD row released in [since, now - ACTUALS_SLA_AFTER]; fill the fillable ones when `apply`."""
    report = BacklogReport()
    start = dt.datetime.combine(since, dt.time(0), tzinfo=_UTC)
    end = now - ACTUALS_SLA_AFTER
    rows = conn.execute(
        "SELECT * FROM event_history WHERE country = 'USD' "
        "AND julianday(event_time_utc) BETWEEN julianday(?) AND julianday(?) ORDER BY event_time_utc, id",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    wanted = set(titles) if titles else None
    enabled = enabled_titles(gate)

    candidates: list[sqlite3.Row] = []
    for row in rows:
        title = row["event_title"]
        if wanted is not None and title not in wanted:
            continue
        if row["actual"] is not None:
            if title in OFFICIAL_SPECS:                  # filled rows of other titles are not this script's business
                report.add(title, "already filled")
            continue
        bucket = coverage_for(title)
        if bucket == "no_actual_expected":
            report.add(title, "no actual expected")
        elif bucket == "proprietary":
            report.add(title, "proprietary")
        elif bucket == "not_mapped":
            report.add(title, "not mapped")
        elif title not in enabled:
            status = gate[title].status if title in gate else None
            report.add(title, "key inactive" if status == "key_inactive" else "gate disabled")
        else:
            candidates.append(row)
    if not candidates:
        return report

    specs: dict[str, OfficialSpec] = {}
    for row in candidates:
        spec = OFFICIAL_SPECS[row["event_title"]]
        specs.setdefault(series_key(spec), spec)
    first_release = min(_parse_utc(r["event_time_utc"]) for r in candidates).astimezone(_UTC).date()
    outcome: Optional[FetchOutcome] = None
    try:
        outcome = fetch(list(specs.values()), first_release)
    except Exception as exc:  # noqa: BLE001 - class name only: messages can carry URLs
        print(f"WARNING: fetch failed: {type(exc).__name__}")

    for row in candidates:
        title = row["event_title"]
        spec = OFFICIAL_SPECS[title]
        key = series_key(spec)
        if outcome is None or key not in outcome.data:
            error = outcome.errors.get(spec.source) if outcome is not None else None
            report.add(title, "key inactive" if isinstance(error, KeyInactiveError) else "source error")
            continue
        release = _parse_utc(row["event_time_utc"])
        later_release, later_previous = later_release_for(conn, spec, release, now)
        decision = decide_fill(spec, release, row["forecast"], row["previous"], outcome.data[key],
                               later_release, later_previous, reestimate_evidence=outcome.evidence.get(key))
        if decision.actual is None:
            label = _decision_outcome(decision.reason)
            report.add(title, label)
            if not decision.reason.startswith(label):
                report.details.append(f"{title} {_sast(row['event_time_utc'])}: {decision.reason}")
            continue
        if not apply:
            report.add(title, "would fill")
            report.details.append(f"would fill {title} {_sast(row['event_time_utc'])} = {decision.actual} ({spec.source})")
            continue
        event = EconomicEvent(title, "USD", row["impact"] or "High", release,
                              forecast=row["forecast"], previous=row["previous"], actual=decision.actual)
        if store.fill_actual_if_missing(conn, row["id"], decision.actual, classify_surprise(event), spec.source, now):
            report.add(title, "filled")
            report.details.append(f"filled {title} {_sast(row['event_time_utc'])} = {decision.actual} ({spec.source})")
        else:
            report.add(title, "already filled")      # someone wrote it between the select and the write
    return report


def format_report(report: BacklogReport, apply: bool) -> str:
    lines = [f"ACT official-actuals backlog backfill ({'APPLY' if apply else 'DRY RUN - nothing written'})"]
    for title in sorted(report.per_title):
        counter = report.per_title[title]
        lines.append(f"  {title}: " + ", ".join(f"{o} {counter[o]}" for o in OUTCOMES if counter[o]))
    if report.details:
        lines.append("details:")
        lines.extend(f"  {d}" for d in report.details)
    totals = report.totals()
    always = "filled" if apply else "would fill"
    lines.append("totals: " + ", ".join(f"{o} {totals[o]}" for o in OUTCOMES if totals[o] or o == always))
    lines.append(LIMITATION)
    return "\n".join(lines)


def _default_fetch(env_file: Optional[Path]) -> FetchFn:
    keys = load_keys(env_file)          # never printed
    fetcher = requests_fetcher()
    return lambda specs, since: fetch_for_specs(specs, since, fetcher, keys)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill official-publisher actuals (dry run unless --apply).")
    parser.add_argument("--db", default=str(store.DB_PATH), help="dashboard.db path (read-only unless --apply)")
    parser.add_argument("--env-file", help=".env holding the API keys (default: the app's own .env)")
    parser.add_argument("--since", type=dt.date.fromisoformat, default=DEFAULT_SINCE,
                        help="first release date (UTC, YYYY-MM-DD; default %(default)s)")
    parser.add_argument("--title", action="append", help="restrict to this FF title (repeatable)")
    parser.add_argument("--apply", action="store_true", help="write the fills (default: dry run)")
    parser.add_argument("--report", help="also write the report to this file")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    if not db_path.is_file():
        print(f"database not found: {db_path} - nothing done.")
        return 2
    if args.report and not Path(args.report).resolve().parent.is_dir():
        print(f"report folder not found: {Path(args.report).resolve().parent} - nothing done.")
        return 4

    fetch = _default_fetch(Path(args.env_file) if args.env_file else None)
    now = dt.datetime.now(_UTC)
    uri = f"file:{db_path.resolve().as_posix()}?mode={'rw' if args.apply else 'ro'}"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        report = run_backlog(conn, now, fetch, load_gate_results(), args.since, args.apply, args.title)
    finally:
        conn.close()

    text = format_report(report, args.apply)
    print(text)
    if args.report:
        with open(args.report, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text + "\n")
        print(f"report written: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
