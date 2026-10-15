"""
Frozen, rule-based backfill of Tier 1 nowcast snapshots (spec §8). Never invents data: where the
provider has nothing the occurrence is skipped; a value dated after the release is refused.

Usage:
    python scripts/backfill_tier1_reconstructed.py nowcasts.csv v1 2026-01-01 2026-10-15 \
        [--dash-db PATH] [--bt-db PATH]
Without --dash-db/--bt-db the app's default databases are used, so point both at a COPY when validating.
The CSV is produced by scripts/cleveland_nowcast_to_csv.py.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path
from typing import Optional, Protocol

# Allow `python scripts/backfill_tier1_reconstructed.py ...` (script dir, not the app root, is on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoring import backtest_store  # noqa: E402
from webapp import store as dash_store  # noqa: E402
from webapp.stats_service import NOWCAST_EVENTS  # noqa: E402

UTC = dt.timezone.utc


class NowcastProvider(Protocol):
    def nowcast_before(self, event_title: str, release_utc: dt.datetime) -> Optional[tuple[float, dt.datetime, str]]: ...


class FileNowcastProvider:
    """Reads columns event_title,release_utc,as_of_utc,value,source; returns the latest as-of <= release."""

    def __init__(self, csv_path: Path):
        self._rows: dict[tuple[str, str], list[tuple[dt.datetime, float, str]]] = {}
        with open(csv_path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = (row["event_title"], dt.datetime.fromisoformat(row["release_utc"]).isoformat())
                self._rows.setdefault(key, []).append(
                    (dt.datetime.fromisoformat(row["as_of_utc"]), float(row["value"]), row["source"]))

    def nowcast_before(self, event_title, release_utc):
        candidates = [c for c in self._rows.get((event_title, release_utc.isoformat()), []) if c[0] <= release_utc]
        if not candidates:
            return None
        as_of, value, source = max(candidates, key=lambda c: c[0])
        return value, as_of, source


def run_backfill(dash_conn, bt_conn, provider: NowcastProvider, rule_version: str,
                 since: dt.datetime, until: dt.datetime) -> dict:
    """Write one 'reconstructed' snapshot per CPI-family occurrence in [since, until). Idempotent."""
    result = {"written": 0, "skipped_no_data": 0, "skipped_lookahead": 0}
    rows = dash_conn.execute(
        "SELECT DISTINCT event_title, event_time_utc FROM event_history WHERE event_time_utc >= ? AND event_time_utc < ? "
        "ORDER BY event_time_utc", (since.isoformat(), until.isoformat())).fetchall()
    for r in rows:
        if r["event_title"] not in NOWCAST_EVENTS:
            continue
        release = dt.datetime.fromisoformat(r["event_time_utc"])
        found = provider.nowcast_before(r["event_title"], release)
        if found is None:
            result["skipped_no_data"] += 1
            continue
        value, as_of, source = found
        if as_of > release:   # defence in depth: a provider must never hand back post-release data
            result["skipped_lookahead"] += 1
            continue
        backtest_store.record_nowcast_snapshot(
            bt_conn, r["event_title"], release, value, as_of, source, "reconstructed", rule_version=rule_version)
        result["written"] += 1
    return result


def _parse_day(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text).replace(tzinfo=UTC)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", type=Path, help="nowcast CSV (event_title,release_utc,as_of_utc,value,source)")
    parser.add_argument("rule_version", help="label stored on every row, e.g. v1")
    parser.add_argument("since", help="first release day (UTC), YYYY-MM-DD, inclusive")
    parser.add_argument("until", help="last release day (UTC), YYYY-MM-DD, exclusive")
    parser.add_argument("--dash-db", type=Path, default=None, help="dashboard.db to read event_history from")
    parser.add_argument("--bt-db", type=Path, default=None, help="backtest_log.db to write snapshots to")
    args = parser.parse_args()
    print(run_backfill(
        dash_store.get_connection(args.dash_db), backtest_store.get_connection(args.bt_db),
        FileNowcastProvider(args.csv_path), args.rule_version, _parse_day(args.since), _parse_day(args.until)))
