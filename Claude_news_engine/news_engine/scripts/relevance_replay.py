"""
FIX (2026-11-03) relevance replay: what the new article filter would do to the
articles already stored, per event family.

Read-only and offline: no network, no writes. The database is opened through a
SQLite `file:...?mode=ro` URI, so even a bug here cannot touch scoring/backtest_log.db.
Run it on a copy of the live database all the same.

Per family it reports:

  * stored exclusion rate, before and after, on the evidence table
    (prediction_article_contributions, from 2026-10-22). "Before" is the share of
    distinct (event, article) pairs the filter excluded when they were scored;
    "after" adds the included pairs the new rules would drop. duplicate_url and
    same_incident rows are left out of both: they are repeats of a kept article,
    not a filter decision.
  * would-exclude rate, overall and per reason, on every voting article stored:
    included evidence rows plus predictions.top_contributions_json.
  * final pre-release XAUUSD predictions left with fewer than 3 kept non-zero
    articles. Evidence rows when the prediction has them, else the non-zero entries
    of top_contributions_json, which hold 3 articles at most, so that count is a
    lower bound. A prediction with neither counts as thin.

The limits are printed with every report. Summaries are not stored, so each title
runs through b6_exclusion_reason(title, "", event_title), `no_fed_coterm` is an upper
bound and the whole-word keyword change cannot be replayed at all. Predictions from
before 2026-09-17 were scored with no keyword list for most titles, so the
would-exclude rate includes off-topic articles the live filter already stops.

Usage:
    python scripts/relevance_replay.py --bt-db <copy of backtest_log.db>
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_layer.event_context import EXCLUSION_REASONS
from data_layer.subject_rules import b6_exclusion_reason, title_family
from scoring.backtest_store import DB_PATH

NEWS_INSTRUMENT = "XAUUSD"
MIN_ARTICLES = 3   # the evidence floor; webapp/stats_methods.py owns it from the next task on
_REPLAYED_REASONS = tuple(reason for reason in EXCLUSION_REASONS if reason not in ("single_stock_blurb", "duplicate_url"))
_STORED_FILTER_REASONS = tuple(reason for reason in EXCLUSION_REASONS if reason != "duplicate_url")


@dataclass
class FamilyReplay:
    articles: int = 0                  # distinct (event, title) voting pairs: included evidence + top contributions
    stored_excluded: int = 0           # distinct pairs the stored evidence rows show as filtered out
    would_exclude: Counter = field(default_factory=Counter)   # of `articles`, keyed by reason
    thin_predictions: int = 0          # final pre-release XAUUSD rows under the floor once the new rules run
    evidence_articles: int = 0         # distinct pairs in the evidence table, included or filtered out
    evidence_would_exclude: int = 0    # included evidence pairs the new rules would drop
    predictions: int = 0               # final pre-release XAUUSD rows
    thin_before: int = 0               # the same rows under the floor with the rules as stored


def open_readonly(db_path: Path) -> sqlite3.Connection:
    """Open db_path through a mode=ro URI; any write raises sqlite3.OperationalError."""
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"database not found: {path}")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _stored_contributions(raw: Optional[str]) -> list[dict]:
    """The parsed top_contributions_json list; [] for NULL, malformed or non-list values."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return [entry for entry in parsed if isinstance(entry, dict)] if isinstance(parsed, list) else []


def _has_evidence_table(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'prediction_article_contributions'"
    ).fetchone()
    return row is not None


def _evidence_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    if not _has_evidence_table(conn):
        return []
    return conn.execute(
        "SELECT prediction_id, event_title, title, status, reason, usd_sentiment "
        "FROM prediction_article_contributions ORDER BY id"
    ).fetchall()


def _final_prediction_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """
    The last XAUUSD row scored at or before each occurrence's release, the same pick
    as webapp/stats_service._accumulator_call_before(). Later rows overwrite earlier ones.
    """
    rows = conn.execute(
        "SELECT id, event_title, event_time_utc, top_contributions_json FROM predictions "
        "WHERE instrument = ? AND julianday(scored_at_utc) <= julianday(event_time_utc) "
        "ORDER BY julianday(scored_at_utc), id",
        (NEWS_INSTRUMENT,),
    ).fetchall()
    final: dict[tuple[str, str], sqlite3.Row] = {}
    for row in rows:
        final[(row["event_title"], row["event_time_utc"])] = row
    return list(final.values())


def _voting_titles(row: sqlite3.Row, included_by_prediction: dict[int, list[sqlite3.Row]]) -> list[str]:
    """Titles of the non-zero articles behind one prediction: evidence rows first, else the stored top 3."""
    evidence = included_by_prediction.get(row["id"])
    if evidence:
        return [item["title"] for item in evidence if item["usd_sentiment"]]
    return [
        str(entry.get("title") or "")
        for entry in _stored_contributions(row["top_contributions_json"])
        if entry.get("usd_sentiment")
    ]


def replay(conn: sqlite3.Connection) -> dict[str, FamilyReplay]:
    """Re-run the current b6_exclusion_reason() over every stored article; one FamilyReplay per family."""
    families: dict[str, FamilyReplay] = {}

    def family_of(event_title: str) -> FamilyReplay:
        return families.setdefault(title_family(event_title), FamilyReplay())

    evidence_rows = _evidence_rows(conn)
    included_by_prediction: dict[int, list[sqlite3.Row]] = {}
    voting_pairs: set[tuple[str, str]] = set()
    evidence_pairs: set[tuple[str, str]] = set()
    stored_excluded_pairs: set[tuple[str, str]] = set()
    for row in evidence_rows:
        pair = (row["event_title"], row["title"])
        if row["status"] == "included":
            included_by_prediction.setdefault(row["prediction_id"], []).append(row)
            voting_pairs.add(pair)
            evidence_pairs.add(pair)
        elif row["reason"] in _STORED_FILTER_REASONS:
            stored_excluded_pairs.add(pair)
            evidence_pairs.add(pair)

    for row in conn.execute("SELECT event_title, top_contributions_json FROM predictions "
                            "WHERE top_contributions_json IS NOT NULL").fetchall():
        for entry in _stored_contributions(row["top_contributions_json"]):
            title = str(entry.get("title") or "")
            if title:
                voting_pairs.add((row["event_title"], title))

    for event_title, title in voting_pairs:
        family = family_of(event_title)
        family.articles += 1
        reason = b6_exclusion_reason(title, "", event_title)
        if reason is None:
            continue
        family.would_exclude[reason] += 1
        if (event_title, title) in evidence_pairs:
            family.evidence_would_exclude += 1
    for event_title, _ in evidence_pairs:
        family_of(event_title).evidence_articles += 1
    for event_title, _ in stored_excluded_pairs:
        family_of(event_title).stored_excluded += 1

    for row in _final_prediction_rows(conn):
        family = family_of(row["event_title"])
        family.predictions += 1
        titles = _voting_titles(row, included_by_prediction)
        kept = [title for title in titles if b6_exclusion_reason(title, "", row["event_title"]) is None]
        family.thin_before += len(titles) < MIN_ARTICLES
        family.thin_predictions += len(kept) < MIN_ARTICLES
    return families


def _rate(part: int, whole: int) -> str:
    return f"{part / whole:.1%}" if whole else "n/a"


def _reason_cell(would_exclude: Counter, articles: int) -> str:
    cells = [f"{reason} {would_exclude[reason]} ({_rate(would_exclude[reason], articles)})"
             for reason in _REPLAYED_REASONS if would_exclude[reason]]
    return ", ".join(cells) or "none"


def render_report(families: dict[str, FamilyReplay], db_label: str) -> str:
    """The replay as a Markdown table per family, with its limits."""
    lines = [
        "# Relevance replay",
        "",
        f"Database: `{db_label}` (opened read-only).",
        "",
        "| Family | Evidence pairs | Stored exclusion, before | After | Voting articles | Would exclude | By reason "
        f"| Final XAUUSD rows | Under {MIN_ARTICLES} before | Under {MIN_ARTICLES} after |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    totals = FamilyReplay()
    for name, family in sorted(families.items(), key=lambda item: -sum(item[1].would_exclude.values())):
        lines.append(_row_markdown(name, family))
        totals.articles += family.articles
        totals.stored_excluded += family.stored_excluded
        totals.would_exclude.update(family.would_exclude)
        totals.thin_predictions += family.thin_predictions
        totals.evidence_articles += family.evidence_articles
        totals.evidence_would_exclude += family.evidence_would_exclude
        totals.predictions += family.predictions
        totals.thin_before += family.thin_before
    lines.append(_row_markdown("**total**", totals))
    lines += [
        "",
        "## Limits",
        "",
        "- Article summaries are not stored, so each title runs with an empty summary: `no_fed_coterm` is an "
        "upper bound and the whole-word keyword change and summary `foreign_cb` cannot be replayed.",
        "- top_contributions_json holds the three heaviest articles, so older predictions are a lower bound.",
        "- Predictions from before 2026-09-17 had no keyword list for most titles, so the would-exclude rate "
        "includes off-topic articles the live filter already stops.",
        "",
    ]
    return "\n".join(lines)


def _row_markdown(name: str, family: FamilyReplay) -> str:
    would_exclude = sum(family.would_exclude.values())
    after = family.stored_excluded + family.evidence_would_exclude
    return (
        f"| {name} | {family.evidence_articles} | {_rate(family.stored_excluded, family.evidence_articles)} "
        f"| {_rate(after, family.evidence_articles)} | {family.articles} "
        f"| {would_exclude} ({_rate(would_exclude, family.articles)}) "
        f"| {_reason_cell(family.would_exclude, family.articles)} "
        f"| {family.predictions} | {family.thin_before} | {family.thin_predictions} |"
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="FIX read-only relevance replay")
    parser.add_argument("--bt-db", default=str(DB_PATH), help="backtest_log.db path (opened read-only)")
    args = parser.parse_args(argv)

    try:
        conn = open_readonly(Path(args.bt_db))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        print(render_report(replay(conn), Path(args.bt_db).name))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    # Example: python scripts/relevance_replay.py --bt-db "%TEMP%\backtest_log_copy.db"
    sys.stdout.reconfigure(encoding="utf-8")  # headlines carry non-ASCII quotes; the Windows console is cp1252
    sys.exit(main())
