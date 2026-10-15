# scripts/stats_phase0_news_input.py
"""Phase 0: how often does each news signal take a side? Read-only. Run by hand."""
from __future__ import annotations

import datetime as dt
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

# Extension (Task 0, 2026-10-15): R3 coverage below reuses the app's own surprise map and symbol
# classifier from THIS checkout; it still only reads the live DB, read-only.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.settings import EVENT_SURPRISE_DIRECTION  # noqa: E402
from webapp.symbols import classify_symbol  # noqa: E402

LIVE = Path(r"C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine")


def implied_surprise_side(event_title: str, direction: str) -> Optional[str]:
    """XAUUSD accumulator direction -> 'higher'/'lower' surprise side (mirrors webapp.history logic)."""
    surprise_map = EVENT_SURPRISE_DIRECTION.get(event_title)
    relationship = classify_symbol("XAUUSD").usd_relationship
    if surprise_map is None or relationship is None:
        return None
    usd_dir = direction if relationship == "direct" else ("bearish" if direction == "bullish" else "bullish")
    return "higher" if (usd_dir == "bullish") == (surprise_map == "higher_bullish") else "lower"


def r3_coverage(bt: sqlite3.Connection) -> None:
    """Rule R3: print call if it takes a side, else XAUUSD accumulator mapped to a surprise side.
    Counts occurrences (title + event time) whose lean is non-zero. Uses the LATEST row per occurrence scored at or before the event time (no lookahead)."""
    prints = {}
    for title, when, side, conf in bt.execute(
        "SELECT event_title, event_time_utc, predicted_vs_forecast, confidence FROM print_predictions "
        "WHERE scored_at_utc <= event_time_utc ORDER BY scored_at_utc, id"
    ):
        prints[(title, when)] = (side, conf)          # later rows overwrite earlier ones
    accs = {}
    for title, when, direction, prob in bt.execute(
        "SELECT event_title, event_time_utc, direction, probability FROM predictions "
        "WHERE instrument='XAUUSD' AND scored_at_utc <= event_time_utc ORDER BY scored_at_utc, id"
    ):
        accs[(title, when)] = (direction, prob)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    occurrences = sorted(set(prints) | set(accs), key=lambda k: (k[1], k[0]))
    buckets = {"all": [], "past (event_time <= now)": [], "past + title has surprise map": []}
    via = Counter()
    for key in occurrences:
        title, when = key
        side, conf = prints.get(key, (None, None))
        direction, prob = accs.get(key, (None, None))
        lean_via: Optional[str] = None
        if side in ("higher", "lower") and conf is not None and conf > 0:
            lean_via = "print"
        elif direction in ("bullish", "bearish") and prob is not None and abs(2 * prob - 1) > 0:
            if implied_surprise_side(title, direction) is not None:
                lean_via = "accumulator"
        buckets["all"].append(lean_via)
        if when <= now:
            buckets["past (event_time <= now)"].append(lean_via)
            if title in EVENT_SURPRISE_DIRECTION:
                buckets["past + title has surprise map"].append(lean_via)
                via[lean_via] += 1
    print("R3 non-zero lean (latest pre-event row per occurrence):")
    for name, vals in buckets.items():
        nz = sum(1 for v in vals if v)
        pct = (100.0 * nz / len(vals)) if vals else 0.0
        print(f"  {name}: {nz}/{len(vals)} = {pct:.1f}%")
    print(f"  source of lean in 'past + title has surprise map': {dict(via)}")
    unmapped = sorted({t for t, _ in occurrences if t not in EVENT_SURPRISE_DIRECTION})
    print(f"  titles with no EVENT_SURPRISE_DIRECTION (R3 can never lean): {unmapped}")


def main(root: Path = LIVE) -> None:
    bt = sqlite3.connect(f"file:{(root / 'scoring' / 'backtest_log.db').as_posix()}?mode=ro", uri=True)
    prints = Counter(r[0] for r in bt.execute("SELECT predicted_vs_forecast FROM print_predictions"))
    total = sum(prints.values())
    sided = prints.get("higher", 0) + prints.get("lower", 0)
    print(f"print calls: {dict(prints)}  takes-a-side: {sided}/{total}")
    acc = Counter(r[0] for r in bt.execute("SELECT direction FROM predictions WHERE instrument='XAUUSD'"))
    acc_total = sum(acc.values())
    acc_sided = acc.get("bullish", 0) + acc.get("bearish", 0)
    print(f"XAUUSD accumulator calls: {dict(acc)}  takes-a-side: {acc_sided}/{acc_total}")
    covered = bt.execute(
        "SELECT COUNT(DISTINCT event_title || event_time_utc) FROM predictions WHERE instrument='XAUUSD'"
    ).fetchone()[0]
    print(f"occurrences with an accumulator XAUUSD prediction: {covered}")
    r3_coverage(bt)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else LIVE)
