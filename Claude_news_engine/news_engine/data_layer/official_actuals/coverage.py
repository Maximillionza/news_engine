"""
Coverage lists and the committed gate result (ACT Task 2).

Every USD title falls in exactly one bucket:
  - no_actual_expected: speeches, testimony, statements, minutes, projections,
    press conferences (no number is ever published);
  - official: in registry.OFFICIAL_SPECS (polled once the gate verifies it);
  - proprietary: the number belongs to a private publisher with no free
    release-time machine-readable source (ISM, UoM, S&P Global PMIs, ...);
  - not_mapped: official data exists but ACT has no adapter (kept on the
    FRED backfill where FRED carries it); also any title not listed at all.

The gate result (`gate_results.json`, beside this module) is produced by
scripts/verify_official_actuals.py from a read-only live run and committed;
the engine only reads it. A missing or corrupt file means "nothing verified".
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from data_layer.official_actuals.fetch import series_key
from data_layer.official_actuals.registry import OFFICIAL_SPECS, OfficialSpec, is_ff_number

GATE_RESULTS_PATH = Path(__file__).resolve().parent / "gate_results.json"

NO_ACTUAL_EXPECTED: tuple[re.Pattern[str], ...] = tuple(re.compile(p) for p in (
    r"Speaks$",
    r"Testifies$",
    r"^Beige Book$",
    r"Monetary Policy Report",
    r"Press Conference$",
    r"^FOMC Statement$",
    r"^FOMC Economic Projections$",
    r"^FOMC Meeting Minutes$",
))

PROPRIETARY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(re.compile(p) for p in (
    r"^ISM ",                       # ISM Manufacturing / Services PMI, Prices, ...
    r"\bUoM\b",                     # University of Michigan sentiment and inflation expectations
    # Regional Fed surveys: no release-time machine-readable source verified.
    r"^(Philly Fed|Empire State|Richmond|Kansas City|KC Fed|Dallas Fed|Dallas) .*Manufacturing Index$",
))
PROPRIETARY_TITLES = frozenset({
    "CB Consumer Confidence",
    "CB Leading Index m/m",
    "Flash Manufacturing PMI",
    "Final Manufacturing PMI",
    "Flash Services PMI",
    "Final Services PMI",
    "Chicago PMI",
    "NAHB Housing Market Index",
    "NFIB Small Business Index",
    "API Weekly Statistical Bulletin",
    "Challenger Job Cuts y/y",
    "RCM/TIPP Economic Optimism",
    "ADP Non-Farm Employment Change",
    "ADP Weekly Employment Change",
    "Existing Home Sales",
    "Pending Home Sales m/m",
    "S&P/CS Composite-20 HPI y/y",
    "Omdia Total Vehicle Sales",
})

# Official data, no ACT adapter (title -> publisher). Kept on the FRED backfill where FRED maps it.
NOT_MAPPED: dict[str, str] = {
    "Industrial Production m/m": "Fed G.17",
    "Capacity Utilization Rate": "Fed G.17",
    "Consumer Credit m/m": "Fed G.19",
    "Federal Budget Balance": "Treasury MTS (host not approved)",
    "HPI m/m": "FHFA",
    "Current Account": "BEA ITA",
    "TIC Long-Term Purchases": "Treasury TIC",
    "Final Wholesale Inventories m/m": "Census mwts (code unresolved in ACT Task 1)",
    "Prelim Wholesale Inventories m/m": "Census mwtsadv (code unresolved in ACT Task 1)",
    "Goods Trade Balance": "Census ftdadv (code unresolved in ACT Task 1)",
}


def coverage_for(title: str) -> str:
    """"no_actual_expected" | "official" | "proprietary" | "not_mapped"."""
    if any(p.search(title) for p in NO_ACTUAL_EXPECTED):
        return "no_actual_expected"
    if title in OFFICIAL_SPECS:
        return "official"
    if title in PROPRIETARY_TITLES or any(p.search(title) for p in PROPRIETARY_PATTERNS):
        return "proprietary"
    return "not_mapped"


@dataclass(frozen=True)
class GateResult:
    status: str                 # verified | suspect | unverified | unavailable | key_inactive
    matches: int
    comparisons: int
    identity: str               # ok | mismatch | unavailable | none


def load_gate_results(path: Optional[Path] = None) -> dict[str, GateResult]:
    """The committed gate result; a missing or corrupt file (or entry) is left out, never guessed."""
    target = Path(path) if path is not None else GATE_RESULTS_PATH
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        titles = payload["titles"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    if not isinstance(titles, dict):
        return {}
    out: dict[str, GateResult] = {}
    for title, entry in titles.items():
        try:
            out[str(title)] = GateResult(str(entry["status"]), int(entry["matches"]), int(entry["comparisons"]),
                                         str(entry["identity"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def enabled_titles(gate: Mapping[str, GateResult]) -> frozenset[str]:
    """Registry titles whose gate status is verified: the only titles the poller writes."""
    return frozenset(t for t, g in gate.items() if g.status == "verified" and t in OFFICIAL_SPECS)


def missing_numeric_rows(conn: sqlite3.Connection, start_utc: dt.datetime, end_utc: dt.datetime) -> list[sqlite3.Row]:
    """
    USD rows released in [start_utc, end_utc] with no actual, excluding titles
    that never get a number and rows whose forecast and previous are both
    non-numeric (text-only), oldest first.
    """
    rows = conn.execute(
        "SELECT * FROM event_history WHERE country = 'USD' AND actual IS NULL "
        "AND julianday(event_time_utc) BETWEEN julianday(?) AND julianday(?) ORDER BY event_time_utc",
        (start_utc.isoformat(), end_utc.isoformat()),
    ).fetchall()
    return [
        r for r in rows
        if coverage_for(r["event_title"]) != "no_actual_expected"
        and (is_ff_number(r["forecast"]) or is_ff_number(r["previous"]))
    ]


def titles_sharing_series(spec: OfficialSpec) -> list[str]:
    """Registry titles that read the same published series (e.g. CPI m/m and Core CPI m/m do not; Prelim/Final GDP do)."""
    key = series_key(spec)
    return sorted(t for t, s in OFFICIAL_SPECS.items() if series_key(s) == key)


def later_release_for(conn: sqlite3.Connection, spec: OfficialSpec, event_time: dt.datetime,
                      now: dt.datetime) -> tuple[bool, Optional[str]]:
    """
    (has a later release, its `previous`): the next USD row of this title, or of any title sharing the
    series, that is already out at `now`. A future row (next month's) does not count: it is not a release
    yet. Shared by the release poller and the backlog backfill so both apply the same revision rule.
    """
    titles = titles_sharing_series(spec)
    marks = ",".join("?" for _ in titles)
    row = conn.execute(
        f"SELECT previous FROM event_history WHERE country = 'USD' AND event_title IN ({marks}) "
        "AND julianday(event_time_utc) > julianday(?) AND julianday(event_time_utc) <= julianday(?) "
        "ORDER BY event_time_utc LIMIT 1",
        (*titles, event_time.isoformat(), now.isoformat()),
    ).fetchone()
    return (True, row["previous"]) if row is not None else (False, None)
