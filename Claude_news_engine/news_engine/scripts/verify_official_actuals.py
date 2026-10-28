"""
Revision-aware verification gate for official-publisher actuals (ACT Task 2).

For every registry title, compares what the official API says with what
event_history already holds, and decides whether the release-time poller may
write that title:

  - for every released USD row since GATE_START, the official value for the
    row's period (registry.expected_period) against the stored actual (rows
    whose actual one of the new publisher sources wrote are skipped: they are
    not an independent reference), and the prior period's value against FF's
    `previous` (for a re-estimate - Prelim/Final GDP, Revised Productivity -
    FF's previous is the earlier estimate of the SAME period);
  - official APIs serve today's revised numbers, so a mismatch still counts as
    agreement when the title's FRED twin read AS OF the row's release date
    (ALFRED vintage; for `previous` also as of the day before) formats to the
    stored string AND the official series equals the twin's current values over
    the last GATE_IDENTITY_PERIODS periods (identity "ok"). Without a twin the
    comparison is revision-blind;
  - verified = at least GATE_MIN_COMPARISONS comparisons and agreement >=
    VERIFY_AGREEMENT_THRESHOLD (B8's 0.8); fewer comparisons = unverified, lower
    agreement = suspect; a publisher error = unavailable / key_inactive.

READ-ONLY: the DB is opened `mode=ro`, and only HTTP GETs/POSTs to the
official APIs and FRED are made. `--write-results` writes the committed
data_layer/official_actuals/gate_results.json (sorted keys, LF), which the
engine reads once at start; `--markdown` writes the coverage table. API keys
come from `--env-file` (or the app's .env) and are never printed.

Times are shown in SAST (UTC+2) with the stored UTC value beside them.

Usage:
    python scripts/verify_official_actuals.py --db <dashboard.db> --env-file <.env>
    python scripts/verify_official_actuals.py ... --title "CPI m/m"      # repeatable
    python scripts/verify_official_actuals.py ... --write-results --markdown docs/superpowers/specs/2026-10-28-act-coverage.md
Exit codes: 0 ok, 2 the database does not exist.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import LOCAL_TZ, UTC_TZ
from data_layer.fred_history import FredClient, FredFetchError, FredMaintenanceError, transform_at
from data_layer.official_actuals.coverage import GATE_RESULTS_PATH
from data_layer.official_actuals.fetch import fetch_for_specs, series_key
from data_layer.official_actuals.http import Fetcher, KeyInactiveError, requests_fetcher
from data_layer.official_actuals.keys import Keys, load_keys
from data_layer.official_actuals.registry import (
    OFFICIAL_SPECS, PUBLISHER_SOURCES, OfficialSpec, expected_period, ff_values_match, format_like,
    is_ff_number, prior_period, release_date_et, value_for,
)
from scripts.seed_fred_history import VERIFY_AGREEMENT_THRESHOLD
import webapp.store as store

GATE_START = dt.date(2026, 1, 1)
GATE_MIN_COMPARISONS = 2
GATE_IDENTITY_PERIODS = 6
# Twin levels fetched before a period so its prior and y/y base are inside the vintage.
TWIN_LOOKBACK_DAYS = 400
DEFAULT_FRED_PACE_SECONDS = 0.6          # FRED allows 120 requests/min


class TwinSource(Protocol):
    def value_asof(self, series_id: str, transform: str, period: dt.date, vintage_date: dt.date) -> Optional[float]: ...

    def current_values(self, series_id: str, transform: str, since: dt.date, today: dt.date) -> dict[dt.date, float]: ...


class TwinReader:
    """FRED/ALFRED reads for the gate: a period as published on a given day, and today's values."""

    def __init__(self, client: FredClient) -> None:
        self._client = client

    def value_asof(self, series_id: str, transform: str, period: dt.date, vintage_date: dt.date) -> Optional[float]:
        levels = self._client.vintage_levels(series_id, vintage_date, period - dt.timedelta(days=TWIN_LOOKBACK_DAYS))
        return transform_at(levels, period, transform)

    def current_values(self, series_id: str, transform: str, since: dt.date, today: dt.date) -> dict[dt.date, float]:
        levels = self._client.vintage_levels(series_id, today, since)
        out: dict[dt.date, float] = {}
        for period, _ in levels:
            value = transform_at(levels, period, transform)
            if value is not None:
                out[period] = value
        return out


@dataclass
class TitleGate:
    status: str                  # verified | suspect | unverified | unavailable | key_inactive
    matches: int
    comparisons: int
    revision_explained: int
    identity: str                # ok | mismatch | unavailable | none (no twin)
    mismatches: list[str] = field(default_factory=list)


def _when(row: sqlite3.Row) -> dt.datetime:
    return dt.datetime.fromisoformat(row["event_time_utc"])


def _sast(when: dt.datetime) -> str:
    return f"{when.astimezone(LOCAL_TZ):%Y-%m-%d %H:%M} SAST ({when.isoformat()})"


def _status(matches: int, comparisons: int) -> str:
    if comparisons < GATE_MIN_COMPARISONS:
        return "unverified"
    return "verified" if matches / comparisons >= VERIFY_AGREEMENT_THRESHOLD else "suspect"


def _latest_template(rows: list[sqlite3.Row]) -> Optional[str]:
    """The newest FF number of the title (actual, else forecast, else previous): sets identity formatting."""
    for row in sorted(rows, key=lambda r: r["event_time_utc"], reverse=True):
        for column in ("actual", "forecast", "previous"):
            if is_ff_number(row[column]):
                return row[column]
    return None


def _identity(spec: OfficialSpec, series: Mapping[dt.date, Any], twin: Optional[TwinSource],
              template: Optional[str], now: dt.datetime) -> str:
    """Official values vs the twin's current values over the last common periods, formatted like FF."""
    if spec.fred_twin is None or twin is None or spec.transform == "auction":
        return "none"
    twin_id, twin_transform = spec.fred_twin
    official = {p: value_for(spec, series, p) for p in series}
    official = {p: v for p, v in official.items() if v is not None}
    if not official:
        return "unavailable"
    try:
        current = twin.current_values(twin_id, twin_transform, min(official) - dt.timedelta(days=TWIN_LOOKBACK_DAYS),
                                      now.date())
    except (FredFetchError, FredMaintenanceError):
        return "unavailable"
    common = sorted(set(official) & set(current))[-GATE_IDENTITY_PERIODS:]
    if not common:
        return "unavailable"
    agree = sum(
        1 for p in common
        if ff_values_match(format_like(official[p], template, spec), format_like(current[p], template, spec))
    )
    return "ok" if agree / len(common) >= VERIFY_AGREEMENT_THRESHOLD else "mismatch"


def _explained_by_twin(spec: OfficialSpec, twin: Optional[TwinSource], stored: str, period: dt.date,
                       vintages: tuple[dt.date, ...]) -> bool:
    """The stored string equals the twin's value for `period` as published on one of `vintages`."""
    if spec.fred_twin is None or twin is None:
        return False
    twin_id, twin_transform = spec.fred_twin
    for vintage in vintages:
        try:
            value = twin.value_asof(twin_id, twin_transform, period, vintage)
        except (FredFetchError, FredMaintenanceError):
            return False
        if value is not None and ff_values_match(stored, format_like(value, stored, spec)):
            return True
    return False


def gate_title(title: str, spec: OfficialSpec, rows: list[sqlite3.Row], series: Mapping[dt.date, Any],
               twin: Optional[TwinSource], now: dt.datetime) -> TitleGate:
    """Agreement of one title's official series with its stored actuals and FF `previous` strings."""
    released = [r for r in rows if release_date_et(_when(r)) >= GATE_START and _when(r) < now]
    identity = _identity(spec, series, twin, _latest_template(rows), now)
    matches = comparisons = explained = 0
    mismatches: list[str] = []
    for row in released:
        when = _when(row)
        release_et = release_date_et(when)
        period = expected_period(spec, release_et)
        checks: list[tuple[str, str, Optional[dt.date], tuple[dt.date, ...]]] = []
        if row["source"] not in PUBLISHER_SOURCES and is_ff_number(row["actual"]):
            checks.append(("actual", row["actual"], period, (release_et,)))
        if is_ff_number(row["previous"]):
            # A re-estimate's previous is the earlier estimate of the same period (a day-before vintage).
            prev_period = period if spec.reestimate else prior_period(spec, period, series.keys())
            checks.append(("previous", row["previous"], prev_period, (release_et, release_et - dt.timedelta(days=1))))
        for kind, stored, ref_period, vintages in checks:
            official = value_for(spec, series, ref_period) if ref_period is not None else None
            if official is None:
                continue                                     # the official data has no value to compare
            candidate = format_like(official, stored, spec)
            comparisons += 1
            if ff_values_match(stored, candidate):
                matches += 1
            elif identity == "ok" and _explained_by_twin(spec, twin, stored, ref_period, vintages):
                matches += 1
                explained += 1
            else:
                mismatches.append(f"{_sast(when)} {kind}: stored {stored} vs official {candidate} "
                                  f"(period {ref_period.isoformat()})")
    return TitleGate(_status(matches, comparisons), matches, comparisons, explained, identity, mismatches)


def _title_rows(conn: sqlite3.Connection, title: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM event_history WHERE event_title = ? AND country = 'USD' ORDER BY event_time_utc", (title,)
    ).fetchall()


def run_gate(conn: sqlite3.Connection, now: dt.datetime, fetcher: Fetcher, keys: Keys,
             fred_client: Optional[FredClient], titles: Optional[list[str]] = None) -> dict[str, TitleGate]:
    """One fetch for every wanted title, then `gate_title` per title; a publisher error marks only its titles."""
    wanted = [t for t in (titles or list(OFFICIAL_SPECS)) if t in OFFICIAL_SPECS]
    outcome = fetch_for_specs([OFFICIAL_SPECS[t] for t in wanted], GATE_START, fetcher, keys)
    twin = TwinReader(fred_client) if fred_client is not None else None
    results: dict[str, TitleGate] = {}
    for title in wanted:
        spec = OFFICIAL_SPECS[title]
        key = series_key(spec)
        if key not in outcome.data:
            error = outcome.errors.get(spec.source)
            status = "key_inactive" if isinstance(error, KeyInactiveError) else "unavailable"
            reason = f"{spec.source}: {type(error).__name__ if error is not None else 'no data'}"
            results[title] = TitleGate(status, 0, 0, 0, "none", [reason])
            continue
        results[title] = gate_title(title, spec, _title_rows(conn, title), outcome.data[key], twin, now)
    return results


def results_to_json(results: Mapping[str, TitleGate], now: dt.datetime) -> dict:
    """The committed gate_results.json payload."""
    return {
        "generated_at_utc": now.isoformat(),
        "threshold": VERIFY_AGREEMENT_THRESHOLD,
        "titles": {
            title: {
                "status": g.status, "matches": g.matches, "comparisons": g.comparisons,
                "revision_explained": g.revision_explained, "identity": g.identity, "mismatches": list(g.mismatches),
            }
            for title, g in results.items()
        },
    }


def coverage_markdown(results: Mapping[str, TitleGate]) -> str:
    """Title | source | series | gate status | agreement m/n | identity, one row per gated title."""
    lines = [
        "| Title | Source | Series | Gate status | Agreement | Identity |",
        "|---|---|---|---|---|---|",
    ]
    for title in sorted(results):
        g = results[title]
        spec = OFFICIAL_SPECS.get(title)
        source, series = (spec.source, spec.series) if spec is not None else ("?", "?")
        lines.append(f"| {title} | {source} | {series} | {g.status} | {g.matches}/{g.comparisons} | {g.identity} |")
    return "\n".join(lines) + "\n"


def format_report(results: Mapping[str, TitleGate], now: dt.datetime) -> str:
    counts = Counter(g.status for g in results.values())
    lines = [f"ACT verification gate, run {_sast(now)}",
             "status counts: " + ", ".join(f"{s} {n}" for s, n in sorted(counts.items()))]
    for title in sorted(results):
        g = results[title]
        lines.append(f"  {title}: {g.status} (agreement {g.matches}/{g.comparisons}, "
                     f"revision explained {g.revision_explained}, identity {g.identity})")
        lines.extend(f"      {m}" for m in g.mismatches)
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verify official-publisher actuals against stored FF-era values.")
    parser.add_argument("--db", default=str(store.DB_PATH), help="dashboard.db path (opened read-only)")
    parser.add_argument("--env-file", help=".env holding the API keys (default: the app's own .env)")
    parser.add_argument("--title", action="append", help="restrict to this FF title (repeatable)")
    parser.add_argument("--write-results", action="store_true", help=f"write {GATE_RESULTS_PATH.name}")
    parser.add_argument("--markdown", help="also write the coverage table to this path")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    if not db_path.is_file():
        print(f"database not found: {db_path} - nothing done.")
        return 2
    keys = load_keys(Path(args.env_file) if args.env_file else None)
    now = dt.datetime.now(UTC_TZ)
    fred_client = FredClient(keys.fred, pace_seconds=DEFAULT_FRED_PACE_SECONDS) if keys.fred else None
    conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        results = run_gate(conn, now, requests_fetcher(), keys, fred_client, titles=args.title)
    finally:
        conn.close()

    print(format_report(results, now))
    if args.write_results:
        text = json.dumps(results_to_json(results, now), indent=2, sort_keys=True) + "\n"
        with open(GATE_RESULTS_PATH, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print(f"gate results written: {GATE_RESULTS_PATH}")
    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(coverage_markdown(results))
        print(f"coverage table written: {args.markdown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
