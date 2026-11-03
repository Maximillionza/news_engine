"""
FIX (2026-11-03) rule-tier replay: which stored rule-tier alerts the C1 guards would now send to the classifier.

Read-only and offline: the alerts database is opened through a SQLite `file:...?mode=ro` URI and nothing
is written. Run it on a copy of the live database all the same.

For every shock_alerts row with classification_method = 'rule_tier' it runs the real
alerting.triage.rule_guard_reason() on the stored headline and the hard-rule phrases found in that
headline. shock_alerts keeps no summary, so a headline that holds no phrase must have matched in its
summary, which is exactly what rule_guard_reason() reports as summary_only.

Usage:
    python scripts/rule_tier_replay.py --alerts-db <copy of shock_alerts.db>
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alerting.taxonomy import HARD_RULE_PATTERNS
from alerting.triage import GUARD_REASONS, rule_guard_reason


def open_readonly(db_path: Path) -> sqlite3.Connection:
    """Open db_path through a mode=ro URI; any write raises sqlite3.OperationalError."""
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"database not found: {path}")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def headline_hits(headline: str) -> list[str]:
    """The first category's phrases found in the headline, as triage_article picks them; [] when none is."""
    text = headline.lower()
    for patterns in HARD_RULE_PATTERNS.values():
        hits = [phrase for phrase in patterns if phrase in text]
        if hits:
            return hits
    return []


def replay(conn: sqlite3.Connection) -> dict[Optional[str], list[int]]:
    """Alert ids per guard reason; the None key holds the alerts that stay on the rule tier."""
    outcome: dict[Optional[str], list[int]] = {reason: [] for reason in GUARD_REASONS}
    outcome[None] = []
    rows = conn.execute(
        "SELECT id, headline FROM shock_alerts WHERE classification_method = 'rule_tier' ORDER BY id"
    ).fetchall()
    for row in rows:
        outcome[rule_guard_reason(row["headline"], headline_hits(row["headline"]))].append(row["id"])
    return outcome


def _count_line(label: str, ids: list[int]) -> str:
    if not ids:
        return f"  {label}: 0"
    return f"  {label}: {len(ids)} (ids {', '.join(str(alert_id) for alert_id in ids)})"


def render_report(outcome: dict[Optional[str], list[int]], db_name: str) -> str:
    total = sum(len(ids) for ids in outcome.values())
    changed = total - len(outcome[None])
    lines = [f"Rule-tier replay on {db_name}", f"{changed} of {total} rule-tier alerts would go to the classifier."]
    lines.extend(_count_line(reason, outcome[reason]) for reason in GUARD_REASONS)
    lines.append(_count_line("stays on the rule tier", outcome[None]))
    lines.append("Limits: summaries are not stored, so guards run on the headline alone and a headline "
                 "with no hard-rule phrase counts as summary_only.")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="FIX read-only hard-rule guard replay")
    parser.add_argument("--alerts-db", required=True, help="shock_alerts.db path (opened read-only)")
    args = parser.parse_args(argv)
    try:
        conn = open_readonly(Path(args.alerts_db))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        print(render_report(replay(conn), Path(args.alerts_db).name))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    # Example: python scripts/rule_tier_replay.py --alerts-db "%TEMP%\shock_alerts_copy.db"
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
