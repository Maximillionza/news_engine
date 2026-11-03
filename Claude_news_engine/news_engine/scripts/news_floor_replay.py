"""
FIX (2026-11-03) evidence-floor replay: which News calls the 3-article floor would have turned into
no-calls, per title, for the releases already stored.

Read-only and offline: both databases are opened through SQLite `file:...?mode=ro` URIs, the Brent
lookup is switched off, and nothing is written. Run it on copies of the live databases all the same.

It runs the real webapp.stats_service.build_rows(), then lists every row the floor now turns into a
no-call while the lean alone (news_side) would have called a side, split into scored (the lean was
graded right or wrong) and pending (no actual yet). The count n comes from the final pre-release
XAUUSD accumulator row: evidence rows when it has them, else the non-zero entries of
top_contributions_json, which hold three articles at most. Those n values are lower bounds, and a
flip caused by one cannot be more than a "3 or more" claim away from the truth, so they are counted.

Usage:
    python scripts/news_floor_replay.py --dash-db <copy of dashboard.db> --bt-db <copy of backtest_log.db>
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webapp import stats_service
from webapp.stats_methods import NEWS_CALL_MIN_ARTICLES, news_side
from webapp.stats_rules import judge


@dataclass
class TitleFlips:
    scored_with_side: int = 0          # scored rows whose lean alone gave a side (the "of how many")
    scored_flipped: int = 0            # of those, turned into a no-call by the floor
    pending_flipped: int = 0           # upcoming rows turned into a no-call by the floor
    verdicts: Counter = field(default_factory=Counter)   # pre-floor verdict of the scored flips: right / wrong / none
    lower_bound: int = 0               # flips whose n is a top-3 lower bound (the row predates the evidence table)
    unknown_n: int = 0                 # flips with n unrecoverable
    n_values: Counter = field(default_factory=Counter)   # n of each flip


def open_readonly(db_path: Path) -> sqlite3.Connection:
    """Open db_path through a mode=ro URI; any write raises sqlite3.OperationalError."""
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"database not found: {path}")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _has_evidence(bt_conn: sqlite3.Connection, row: stats_service.StatsRow) -> bool:
    """True when the accumulator row behind this release has evidence rows (n is exact, not a top-3 bound)."""
    acc = stats_service._accumulator_call_before(bt_conn, row.event_title, row.event_time_utc.isoformat())
    if acc is None:
        return False
    return bt_conn.execute(
        "SELECT 1 FROM prediction_article_contributions WHERE prediction_id = ? LIMIT 1", (acc["id"],)
    ).fetchone() is not None


def replay(dash_conn: sqlite3.Connection, bt_conn: sqlite3.Connection) -> dict[str, TitleFlips]:
    """Per title: how many News calls the floor flips to no-call, from the real build_rows()."""
    rows = stats_service.build_rows(dash_conn, bt_conn, brent_series_fn=lambda: None)
    out: dict[str, TitleFlips] = defaultdict(TitleFlips)
    for row in rows:
        lean = None if row.detail is None else row.detail.news_lean
        if lean is None or news_side(lean) is None:
            continue                                   # no lean side before the floor: nothing to flip
        flips = out[row.event_title]
        flipped = row.news_call == "no_call" and (row.news_no_call_reason or "").startswith("too few")
        if row.status == "scored":
            flips.scored_with_side += 1
        if not flipped:
            continue
        n = row.detail.news_article_count
        if row.status == "scored":
            flips.scored_flipped += 1
            actual_side = stats_service._actual_side(row)
            flips.verdicts[judge(news_side(lean), actual_side) or "none"] += 1
        else:
            flips.pending_flipped += 1
        if n is None:
            flips.unknown_n += 1
        else:
            flips.n_values[n] += 1
            if n > 0 and not _has_evidence(bt_conn, row):     # n = 0 from article_count 0 is exact
                flips.lower_bound += 1
    return dict(out)


def render_report(result: dict[str, TitleFlips], bt_name: str) -> str:
    lines = [f"News evidence-floor replay on {bt_name} (floor: {NEWS_CALL_MIN_ARTICLES} signal-bearing articles)", ""]
    total_scored = total_flipped = total_pending = total_lower = total_unknown = 0
    verdicts: Counter = Counter()
    for title in sorted(result):
        f = result[title]
        if not (f.scored_with_side or f.pending_flipped):
            continue
        total_scored += f.scored_with_side
        total_flipped += f.scored_flipped
        total_pending += f.pending_flipped
        total_lower += f.lower_bound
        total_unknown += f.unknown_n
        verdicts.update(f.verdicts)
        lines.append(f"{title}: scored {f.scored_flipped} of {f.scored_with_side} News calls flip to no-call "
                     f"(right {f.verdicts['right']}, wrong {f.verdicts['wrong']}, ungraded {f.verdicts['none']}); "
                     f"pending flips {f.pending_flipped}; n lower bounds {f.lower_bound}, n unknown {f.unknown_n}")
    lines.append("")
    lines.append(f"Total: {total_flipped} of {total_scored} scored News calls flip to no-call "
                 f"(right {verdicts['right']}, wrong {verdicts['wrong']}, ungraded {verdicts['none']}); "
                 f"{total_pending} pending rows flip.")
    lines.append(f"Of all flips, {total_lower} rest on a top-3 lower bound for n and {total_unknown} on an unknown n.")
    lines.append("Limits: n for rows before 2026-10-22 comes from top_contributions_json (3 articles at most); "
                 "an unrecoverable n fails closed.")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="FIX read-only News evidence-floor replay")
    parser.add_argument("--dash-db", required=True, help="dashboard.db path (opened read-only)")
    parser.add_argument("--bt-db", required=True, help="backtest_log.db path (opened read-only)")
    args = parser.parse_args(argv)
    try:
        dash = open_readonly(Path(args.dash_db))
        bt = open_readonly(Path(args.bt_db))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    try:
        print(render_report(replay(dash, bt), Path(args.bt_db).name))
        return 0
    finally:
        dash.close()
        bt.close()


if __name__ == "__main__":
    # Example: python scripts/news_floor_replay.py --dash-db "%TEMP%\dashboard_copy.db" --bt-db "%TEMP%\backtest_log_copy.db"
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
