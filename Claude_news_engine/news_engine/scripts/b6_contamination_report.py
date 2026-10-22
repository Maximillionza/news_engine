"""
B6 (2026-10-22) before/after contamination report: how much foreign-central-bank
and off-subject article evidence sits in the recorded FOMC- and CPI-family calls,
and (after the B6 deploy) a check that no new foreign-CB article is still voting.

Read-only and offline: no network, no writes. The database is opened through a
SQLite `file:...?mode=ro` URI, so even a bug here cannot touch the live
scoring/backtest_log.db. Two caveats are printed with every report:

  * top-3 only: predictions.top_contributions_json keeps the three heaviest
    articles per call, so every count is an undercount of the real contamination.
  * title only: the article summary is not stored, so each stored title is re-run
    through b6_exclusion_reason(title, "", event_title); `no_fed_coterm` (which
    reads title + summary live) is therefore an upper bound.

Usage:
    python scripts/b6_contamination_report.py --db scoring/backtest_log.db
    python scripts/b6_contamination_report.py --db scoring/backtest_log.db --verify-since 2026-10-23T08:00:00+00:00

--verify-since prints a single integer: the foreign-CB articles that were INCLUDED
in the vote (prediction_article_contributions, status 'included') since that UTC
instant. After the deploy it must stay 0; exit code 0 when it is, 1 when it is not,
2 when it cannot be checked (missing DB or pre-B6 database without the table).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_layer.subject_rules import b6_exclusion_reason, foreign_cb_match, title_family
from scoring.backtest_store import DB_PATH

SAST = dt.timezone(dt.timedelta(hours=2))
NONZERO_SENTIMENT = 0.05   # abs(usd_sentiment) at or above this counts as a real vote
EXAMPLES_PER_REASON = 5
_REASONS = ("foreign_cb", "no_fed_coterm", "off_subject")
_COUNT_KEYS = ("rows", "rows_with_contributions", "contributions", "unique_contributions", "removed_unique",
               "removed_nonzero", "rows_touched", "rows_all_removed", "occurrences_touched", "same_url_pairs")


def open_readonly(db_path: Path) -> sqlite3.Connection:
    """Open db_path through a mode=ro URI; any write raises sqlite3.OperationalError."""
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"database not found: {path}")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _blank_stats() -> dict:
    stats: dict = {key: 0 for key in _COUNT_KEYS}
    stats["removed_by_reason"] = {}
    return stats


def _stored_contributions(raw: str | None) -> list[dict]:
    """The parsed top_contributions_json list; [] for NULL, malformed or non-list values."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return [c for c in parsed if isinstance(c, dict)] if isinstance(parsed, list) else []


def summarize(conn: sqlite3.Connection) -> dict:
    """
    Re-run the B6 rules over every live prediction's stored top contributions.

    Returns {"families": {family: FamilyStats}, "examples": {family: {reason: [titles]}},
    "totals": FamilyStats-shaped sums}. `contributions` / `removed_by_reason` count every stored
    entry; `unique_contributions` / `removed_unique` count distinct (event, time, url or title).
    """
    families: dict[str, dict] = {}
    unique_seen: dict[str, set] = {}
    removed_unique_seen: dict[str, set] = {}
    occurrences: dict[str, set] = {}
    examples: dict[str, dict[str, list[str]]] = {}
    reasons: dict[str, Counter] = {}

    rows = conn.execute(
        "SELECT event_title, event_time_utc, top_contributions_json FROM predictions "
        "WHERE source = 'live' AND top_contributions_json IS NOT NULL ORDER BY id"
    ).fetchall()
    for row in rows:
        event_title = row["event_title"]
        family = title_family(event_title)
        stats = families.setdefault(family, _blank_stats())
        reasons.setdefault(family, Counter())
        unique_seen.setdefault(family, set())
        removed_unique_seen.setdefault(family, set())
        occurrences.setdefault(family, set())
        stats["rows"] += 1

        contributions = _stored_contributions(row["top_contributions_json"])
        if not contributions:
            continue
        stats["rows_with_contributions"] += 1

        seen_urls: set[str] = set()
        removed_in_row = 0
        for entry in contributions:
            title = str(entry.get("title") or "")
            url = str(entry.get("url") or "")
            key = (event_title, row["event_time_utc"], url or title)
            stats["contributions"] += 1
            unique_seen[family].add(key)
            if url:
                if url in seen_urls:
                    stats["same_url_pairs"] += 1
                seen_urls.add(url)

            reason = b6_exclusion_reason(title, "", event_title)
            if reason is None:
                continue
            removed_in_row += 1
            reasons[family][reason] += 1
            removed_unique_seen[family].add(key)
            if abs(entry.get("usd_sentiment") or 0.0) >= NONZERO_SENTIMENT:
                stats["removed_nonzero"] += 1
            bucket = examples.setdefault(family, {}).setdefault(reason, [])
            if title not in bucket and len(bucket) < EXAMPLES_PER_REASON:
                bucket.append(title)

        if removed_in_row:
            stats["rows_touched"] += 1
            occurrences[family].add((event_title, row["event_time_utc"]))
            if removed_in_row == len(contributions):
                stats["rows_all_removed"] += 1

    totals = _blank_stats()
    total_reasons: Counter = Counter()
    for family, stats in families.items():
        stats["unique_contributions"] = len(unique_seen[family])
        stats["removed_unique"] = len(removed_unique_seen[family])
        stats["occurrences_touched"] = len(occurrences[family])
        stats["removed_by_reason"] = {r: reasons[family][r] for r in _REASONS if reasons[family][r]}
        total_reasons.update(reasons[family])
        for key in _COUNT_KEYS:
            totals[key] += stats[key]
    totals["removed_by_reason"] = {r: total_reasons[r] for r in _REASONS if total_reasons[r]}
    return {"families": families, "examples": examples, "totals": totals}


def _utc_instant(value: str) -> str:
    """Normalise an ISO timestamp (Z or offset, naive = UTC) to a UTC ISO string."""
    parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).isoformat()


def count_foreign_cb_included(conn: sqlite3.Connection, since_utc: str) -> int:
    """
    Included (voting) articles recorded at or after since_utc whose title names a foreign
    central bank. Acceptance for B6: 0 for any window that starts after the deploy.
    """
    since = _utc_instant(since_utc)
    rows = conn.execute(
        "SELECT title FROM prediction_article_contributions "
        "WHERE status = 'included' AND julianday(recorded_at_utc) >= julianday(?)",
        (since,),
    ).fetchall()
    return sum(1 for row in rows if foreign_cb_match(row["title"]) is not None)


def _reason_cell(by_reason: dict) -> str:
    return ", ".join(f"{reason} {n}" for reason, n in by_reason.items()) or "none"


def render_markdown(summary: dict, db_label: str, generated_sast: str) -> str:
    """The report as Markdown: family table, per-reason examples, caveats. Times in SAST."""
    lines = [
        "# B6 contamination report",
        "",
        f"Database: `{db_label}` (opened read-only). Generated {generated_sast}.",
        "",
        "| Family | Rows | Rows touched | Rows losing all evidence | Contributions | Unique | Removed (unique) "
        "| Removed with a real vote | Same-URL pairs | Removed by reason |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    ordered = sorted(summary["families"].items(), key=lambda item: (-item[1]["rows_touched"], item[0]))
    for family, s in ordered + [("**total**", summary["totals"])]:
        lines.append(
            f"| {family} | {s['rows']} | {s['rows_touched']} | {s['rows_all_removed']} | {s['contributions']} "
            f"| {s['unique_contributions']} | {s['removed_unique']} | {s['removed_nonzero']} "
            f"| {s['same_url_pairs']} | {_reason_cell(s['removed_by_reason'])} |"
        )
    lines += ["", "## Examples (up to 5 titles per family and reason)", ""]
    if not summary["examples"]:
        lines.append("None.")
    for family in sorted(summary["examples"]):
        for reason in _REASONS:
            for title in summary["examples"][family].get(reason, []):
                lines.append(f"- {family} / {reason}: {title}")
    lines += [
        "",
        "## Caveats",
        "",
        "- top-3 only: each prediction stores its three heaviest articles, so every count is an undercount.",
        "- title only: the summary is not stored, so `no_fed_coterm` is an upper bound.",
        "- Precursor and Kalshi contributions are not stored and are not covered.",
        "- Only source = 'live' predictions with stored evidence are counted; times shown are SAST (UTC+2).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B6 read-only contamination report")
    parser.add_argument("--db", default=str(DB_PATH), help="backtest_log.db path (opened read-only)")
    parser.add_argument("--verify-since", default=None, metavar="ISO",
                        help="print the count of foreign-CB articles included since this UTC ISO instant")
    args = parser.parse_args(argv)

    try:
        conn = open_readonly(Path(args.db))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        if args.verify_since:
            try:
                count = count_foreign_cb_included(conn, args.verify_since)
            except sqlite3.OperationalError as exc:
                print(f"error: cannot verify ({exc}); has the B6 build created prediction_article_contributions yet?",
                      file=sys.stderr)
                return 2
            print(count)
            return 0 if count == 0 else 1
        generated = dt.datetime.now(SAST).strftime("%Y-%m-%d %H:%M SAST")
        print(render_markdown(summarize(conn), Path(args.db).name, generated))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    # Example: python scripts/b6_contamination_report.py --db scoring/backtest_log.db
    sys.stdout.reconfigure(encoding="utf-8")  # headlines carry non-ASCII quotes; the Windows console is cp1252
    sys.exit(main())
