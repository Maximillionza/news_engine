# Article-Based Backtest Accumulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build infrastructure that automatically accumulates real, growing backtest data for the article-based scoring pipeline — persisting real predictions made blind (before an event) and, once manually confirmed against real outcomes, reporting real accuracy over time.

**Architecture:** New `scoring/backtest_store.py` (SQLite persistence, two tables: `predictions` and `outcomes`), `scoring/backtest_accumulator.py` (background scheduler, budget-capped article fetches), `scripts/confirm_backtest_outcomes.py` (manual outcome-confirmation CLI), and an extension to the existing `scoring/backtest.py` for reporting. Deliberately separate from `webapp/` — the dashboard is essence-only by design; this is article-based and a distinct concern, run as its own standalone process.

**Tech Stack:** Python 3.14, stdlib `sqlite3`/`threading` (no new dependencies) — reuses `data_layer.calendar_feed`, `data_layer.event_context`, `data_layer.rss_sources`, `scoring.probability_engine`, and `webapp.scheduler.compute_adaptive_interval_seconds` (cross-package reuse, no cycle — `webapp` doesn't import from this new code).

## Global Constraints

- No article fetching happens in `webapp/` — this accumulator is entirely separate, its own script/process, never imported by `webapp/app.py` or `webapp/scheduler.py`.
- Article fetches are budget-capped: **at most 2 prediction snapshots per (event, instrument) pair** — one when the event enters its pre-event window, one more only once inside the final `NEAR_WINDOW_HOURS` stretch (reuse `webapp.scheduler.NEAR_WINDOW_HOURS`, don't redefine it).
- High-impact USD events only (`filter_relevant_events()`'s default) — no widening to Medium-impact like the dashboard does; article fetches are expensive/rate-limited, essence-only scoring is free.
- Never fabricate an outcome — a prediction with no confirmed outcome simply doesn't appear in reporting until manually confirmed.
- `get_connection()`'s `db_path` parameter must be resolved inside the function body (not as a default-argument value) — same pattern as `webapp/store.py`, needed so tests can patch the module-level `DB_PATH`.
- New tests follow the existing project's plain-`assert`-plus-`__main__` style (see `tests/test_scoring_smoke.py`) — no pytest. `unittest.mock.patch` is fine for avoiding live network calls.

---

### Task 1: Persistence layer

**Files:**
- Create: `scoring/backtest_store.py`
- Test: `tests/test_backtest_store.py`

**Interfaces:**
- Produces: `DB_PATH: Path`, `Prediction` (dataclass: `id: int`, `event_title: str`, `instrument: str`, `event_time_utc: str`, `scored_at_utc: str`, `probability: float`, `direction: str`, `confidence: float`, `article_count: int`, `contradiction_flag: bool`), `Outcome` (dataclass: `id: int`, `event_title: str`, `instrument: str`, `event_time_utc: str`, `actual_direction: str`, `actual_move_note: str`, `confirmed_at_utc: str`), `get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection`, `record_prediction(conn, event_title, instrument, event_time_utc, probability, direction, confidence, article_count, contradiction_flag, scored_at_utc=None) -> int`, `count_predictions(conn, event_title, instrument) -> int`, `get_predictions_awaiting_outcome(conn, now=None) -> list[Prediction]`, `record_outcome(conn, event_title, instrument, event_time_utc, actual_direction, actual_move_note, confirmed_at_utc=None) -> int`, `get_all_confirmed_cases(conn) -> list[tuple[Prediction, Outcome]]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_backtest_store.py`:

```python
"""
Tests for scoring/backtest_store.py — uses a temp SQLite file, no network needed.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import (
    get_connection, record_prediction, count_predictions,
    get_predictions_awaiting_outcome, record_outcome, get_all_confirmed_cases,
)


def test_record_and_count_predictions():
    print("=== backtest_store: record_prediction + count_predictions round-trip ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=dt.timezone.utc)

        assert count_predictions(conn, "CPI m/m", "XAUUSD") == 0
        record_prediction(conn, "CPI m/m", "XAUUSD", event_time, 0.71, "bullish", 0.55, 12, False)
        assert count_predictions(conn, "CPI m/m", "XAUUSD") == 1
        record_prediction(conn, "CPI m/m", "XAUUSD", event_time, 0.68, "bullish", 0.60, 15, False)
        assert count_predictions(conn, "CPI m/m", "XAUUSD") == 2
        conn.close()
    print("PASS\n")


def test_awaiting_outcome_uses_latest_snapshot_and_excludes_confirmed():
    print("=== backtest_store: awaiting-outcome list uses latest snapshot, excludes already-confirmed pairs ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        past_event = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)   # already passed
        future_event = dt.datetime(2026, 8, 20, 12, 30, tzinfo=dt.timezone.utc)  # not yet
        now = dt.datetime(2026, 8, 10, tzinfo=dt.timezone.utc)

        t1 = dt.datetime(2026, 7, 30, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2026, 7, 31, tzinfo=dt.timezone.utc)
        record_prediction(conn, "NFP", "XAUUSD", past_event, 0.5, "neutral", 0.1, 3, False, scored_at_utc=t1)
        record_prediction(conn, "NFP", "XAUUSD", past_event, 0.7, "bullish", 0.4, 8, False, scored_at_utc=t2)
        record_prediction(conn, "CPI", "US30", future_event, 0.6, "bullish", 0.3, 5, False)

        awaiting = get_predictions_awaiting_outcome(conn, now=now)
        assert len(awaiting) == 1, f"expected only the past NFP event, got {len(awaiting)}"
        assert awaiting[0].event_title == "NFP"
        assert awaiting[0].probability == 0.7, "should surface the LATEST snapshot, not the first"

        record_outcome(conn, "NFP", "XAUUSD", past_event, "bullish", "real outcome confirmed")
        awaiting_after = get_predictions_awaiting_outcome(conn, now=now)
        assert len(awaiting_after) == 0, "confirmed pair should no longer be awaiting"
        conn.close()
    print("PASS\n")


def test_confirmed_cases_joins_latest_prediction_with_outcome():
    print("=== backtest_store: get_all_confirmed_cases joins the latest snapshot with its outcome ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        t1 = dt.datetime(2026, 7, 30, tzinfo=dt.timezone.utc)
        t2 = dt.datetime(2026, 7, 31, tzinfo=dt.timezone.utc)
        record_prediction(conn, "NFP", "XAUUSD", event_time, 0.5, "neutral", 0.1, 3, False, scored_at_utc=t1)
        record_prediction(conn, "NFP", "XAUUSD", event_time, 0.7, "bullish", 0.4, 8, False, scored_at_utc=t2)
        record_prediction(conn, "CPI", "US30", event_time, 0.6, "bullish", 0.3, 5, True)  # never confirmed

        record_outcome(conn, "NFP", "XAUUSD", event_time, "bullish", "confirmed real move")

        cases = get_all_confirmed_cases(conn)
        assert len(cases) == 1, "only the confirmed NFP/XAUUSD pair should appear, not the unconfirmed CPI/US30 one"
        prediction, outcome = cases[0]
        assert prediction.probability == 0.7, "should join the LATEST prediction snapshot"
        assert outcome.actual_direction == "bullish"
        conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_record_and_count_predictions()
    test_awaiting_outcome_uses_latest_snapshot_and_excludes_confirmed()
    test_confirmed_cases_joins_latest_prediction_with_outcome()
    print("All backtest_store tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_backtest_store.py`
Expected: `ModuleNotFoundError: No module named 'scoring.backtest_store'`

- [ ] **Step 3: Write the implementation**

Create `scoring/backtest_store.py`:

```python
"""
Persistence for the article-based backtest accumulator — a running log
of real predictions (made blind, before the event) and their real
confirmed outcomes (added later, via research). Separate from
webapp/store.py's essence-only prediction_runs table on purpose: this is
for the article-based pipeline (scoring/probability_engine.py), a
distinct concern from the dashboard's article-free scoring.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "backtest_log.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    scored_at_utc TEXT NOT NULL,
    probability REAL NOT NULL,
    direction TEXT NOT NULL,
    confidence REAL NOT NULL,
    article_count INTEGER NOT NULL,
    contradiction_flag INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    actual_direction TEXT NOT NULL,
    actual_move_note TEXT NOT NULL,
    confirmed_at_utc TEXT NOT NULL,
    UNIQUE(event_title, instrument, event_time_utc)
);
"""


@dataclass
class Prediction:
    id: int
    event_title: str
    instrument: str
    event_time_utc: str
    scored_at_utc: str
    probability: float
    direction: str
    confidence: float
    article_count: int
    contradiction_flag: bool


@dataclass
class Outcome:
    id: int
    event_title: str
    instrument: str
    event_time_utc: str
    actual_direction: str
    actual_move_note: str
    confirmed_at_utc: str


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    # db_path resolved inside the body (not as a default arg value) so
    # tests can patch module-level DB_PATH and have it take effect.
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def record_prediction(
    conn: sqlite3.Connection,
    event_title: str,
    instrument: str,
    event_time_utc: dt.datetime,
    probability: float,
    direction: str,
    confidence: float,
    article_count: int,
    contradiction_flag: bool,
    scored_at_utc: Optional[dt.datetime] = None,
) -> int:
    scored_at = scored_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO predictions (event_title, instrument, event_time_utc, scored_at_utc, "
        "probability, direction, confidence, article_count, contradiction_flag) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), scored_at.isoformat(),
         probability, direction, confidence, article_count, int(contradiction_flag)),
    )
    conn.commit()
    return cursor.lastrowid


def count_predictions(conn: sqlite3.Connection, event_title: str, instrument: str) -> int:
    """
    How many prediction snapshots already exist for this (event,
    instrument) pair. This is pure data access — the accumulator's own
    snapshot budget cap enforcement lives in scoring/backtest_accumulator.py,
    not here.
    """
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM predictions WHERE event_title = ? AND instrument = ?",
        (event_title, instrument),
    ).fetchone()
    return row["n"]


def get_predictions_awaiting_outcome(
    conn: sqlite3.Connection, now: Optional[dt.datetime] = None
) -> list[Prediction]:
    """
    Distinct (event_title, instrument, event_time_utc) triples whose
    event has already passed and have no matching row in outcomes yet —
    the LATEST prediction snapshot per pair is what gets surfaced (not
    every snapshot, just the final one before the event).
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = conn.execute(
        """
        SELECT p.* FROM predictions p
        WHERE p.event_time_utc <= ?
          AND p.scored_at_utc = (
              SELECT MAX(p2.scored_at_utc) FROM predictions p2
              WHERE p2.event_title = p.event_title AND p2.instrument = p.instrument
                AND p2.event_time_utc = p.event_time_utc
          )
          AND NOT EXISTS (
              SELECT 1 FROM outcomes o
              WHERE o.event_title = p.event_title AND o.instrument = p.instrument
                AND o.event_time_utc = p.event_time_utc
          )
        ORDER BY p.event_time_utc ASC
        """,
        (now.isoformat(),),
    ).fetchall()
    return [Prediction(**dict(row)) for row in rows]


def record_outcome(
    conn: sqlite3.Connection,
    event_title: str,
    instrument: str,
    event_time_utc: dt.datetime,
    actual_direction: str,
    actual_move_note: str,
    confirmed_at_utc: Optional[dt.datetime] = None,
) -> int:
    confirmed_at = confirmed_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO outcomes (event_title, instrument, event_time_utc, actual_direction, "
        "actual_move_note, confirmed_at_utc) VALUES (?, ?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), actual_direction,
         actual_move_note, confirmed_at.isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_all_confirmed_cases(conn: sqlite3.Connection) -> list[tuple[Prediction, Outcome]]:
    """
    Joins each (event, instrument) pair's LATEST prediction snapshot with
    its confirmed outcome, for reporting. Pairs with no confirmed outcome
    yet are excluded — never fabricate a result.
    """
    rows = conn.execute(
        """
        SELECT p.*, o.actual_direction, o.actual_move_note, o.confirmed_at_utc,
               o.id AS outcome_id
        FROM outcomes o
        JOIN predictions p ON p.event_title = o.event_title
                           AND p.instrument = o.instrument
                           AND p.event_time_utc = o.event_time_utc
        WHERE p.scored_at_utc = (
            SELECT MAX(p2.scored_at_utc) FROM predictions p2
            WHERE p2.event_title = p.event_title AND p2.instrument = p.instrument
              AND p2.event_time_utc = p.event_time_utc
        )
        ORDER BY p.event_time_utc ASC
        """
    ).fetchall()

    cases = []
    for row in rows:
        d = dict(row)
        prediction = Prediction(
            id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
            event_time_utc=d["event_time_utc"], scored_at_utc=d["scored_at_utc"],
            probability=d["probability"], direction=d["direction"], confidence=d["confidence"],
            article_count=d["article_count"], contradiction_flag=bool(d["contradiction_flag"]),
        )
        outcome = Outcome(
            id=d["outcome_id"], event_title=d["event_title"], instrument=d["instrument"],
            event_time_utc=d["event_time_utc"], actual_direction=d["actual_direction"],
            actual_move_note=d["actual_move_note"], confirmed_at_utc=d["confirmed_at_utc"],
        )
        cases.append((prediction, outcome))
    return cases
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_backtest_store.py`
Expected: `All backtest_store tests passed.`

- [ ] **Step 5: Commit**

```bash
git add scoring/backtest_store.py tests/test_backtest_store.py
git commit -m "feat: persistence for the article-based backtest accumulator"
```

---

### Task 2: Accumulator scheduler

**Files:**
- Create: `scoring/backtest_accumulator.py`
- Test: `tests/test_backtest_accumulator.py`

**Interfaces:**
- Consumes: `fetch_calendar`, `filter_relevant_events`, `events_in_pre_window` from `data_layer.calendar_feed` (already exist); `build_event_news_bundle` from `data_layer.event_context` (already exists); `build_all_preview_sources` from `data_layer.rss_sources` (already exists); `score_bundle` from `scoring.probability_engine` (already exists); `get_connection`, `record_prediction`, `count_predictions` from `scoring.backtest_store` (Task 1); `compute_adaptive_interval_seconds`, `NEAR_WINDOW_HOURS` from `webapp.scheduler` (already exist — cross-package reuse, not a cycle).
- Produces: `SNAPSHOT_BUDGET_PER_PAIR: int` (= 2), `ACCUMULATOR_FALLBACK_INTERVAL_SECONDS: int`, `run_accumulator_cycle(instruments: list[str], db_path: Optional[Path] = None, now: Optional[dt.datetime] = None) -> Optional[list]` (returns fetched events on success, `None` on calendar-fetch failure), `start_accumulator(instruments: list[str]) -> None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_backtest_accumulator.py`:

```python
"""
Tests for scoring/backtest_accumulator.py — no live network, calendar/
article fetching and scoring are all mocked.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle
from scoring.probability_engine import Direction, ProbabilityResult
import scoring.backtest_accumulator as accumulator
import scoring.backtest_store as store


def _fake_event(hours_from_now, now):
    return EconomicEvent(
        title="Test Event", country="USD", impact="High",
        event_time_utc=now + dt.timedelta(hours=hours_from_now),
        forecast="1.0%", actual=None,
    )


def _fake_result(probability=0.7, direction=Direction.BULLISH):
    return ProbabilityResult(
        instrument="XAUUSD", as_of_utc=dt.datetime.now(UTC_TZ),
        aggregate_usd_sentiment=0.3, instrument_score=-0.3,
        probability=probability, direction=direction, confidence=0.5,
        article_count=5, contradiction_flag=False, contradiction_note=None,
    )


def test_first_snapshot_taken_immediately_second_only_in_near_window():
    print("=== accumulator: first snapshot on window entry, second only within NEAR_WINDOW_HOURS, third never ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)  # inside 72h pre-window, outside NEAR_WINDOW_HOURS(4h)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()):

            # Cycle 1: 20h out, first snapshot should be taken.
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD") == 1

            # Cycle 2: still 20h out (not near window) — second snapshot must NOT be taken yet.
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD") == 1, "should not take a 2nd snapshot outside the near window"

            # Cycle 3: now inside the near window (2h out) — second snapshot should be taken.
            near_now = event.event_time_utc - dt.timedelta(hours=2)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD") == 2

            # Cycle 4: budget exhausted, must not take a 3rd snapshot even still in near window.
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD") == 2, "budget cap must hold"
            conn.close()
    print("PASS\n")


def test_high_impact_only_no_medium_widening():
    print("=== accumulator: uses filter_relevant_events with default (High-only), not Medium widening like the dashboard ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)

        with patch.object(accumulator, "fetch_calendar", return_value=[]) as mock_fetch, \
             patch.object(accumulator, "filter_relevant_events", return_value=[]) as mock_filter:

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            mock_filter.assert_called_once_with(mock_fetch.return_value)
            # No min_impact kwarg — confirms this does NOT widen to Medium like webapp/scheduler.py does.
            assert mock_filter.call_args.kwargs == {}
    print("PASS\n")


def test_failed_scoring_for_one_pair_does_not_stop_others():
    print("=== accumulator: a scoring failure for one instrument doesn't stop the other instrument's snapshot ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)

        def flaky_score_bundle(bundle, instrument):
            if instrument == "XAUUSD":
                raise Exception("scoring blew up")
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", side_effect=flaky_score_bundle):

            accumulator.run_accumulator_cycle(["XAUUSD", "US30"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD") == 0, "the failing instrument should not get a row"
            assert store.count_predictions(conn, "Test Event", "US30") == 1, "the other instrument should still succeed"
            conn.close()
    print("PASS\n")


def test_failed_calendar_fetch_returns_none_without_crashing():
    print("=== accumulator: a failed calendar fetch returns None and does not crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(accumulator, "fetch_calendar", side_effect=Exception("network down")):
            result = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path)
            assert result is None
    print("PASS\n")


if __name__ == "__main__":
    test_first_snapshot_taken_immediately_second_only_in_near_window()
    test_high_impact_only_no_medium_widening()
    test_failed_scoring_for_one_pair_does_not_stop_others()
    test_failed_calendar_fetch_returns_none_without_crashing()
    print("All backtest_accumulator tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_backtest_accumulator.py`
Expected: `ModuleNotFoundError: No module named 'scoring.backtest_accumulator'`

- [ ] **Step 3: Write the implementation**

Create `scoring/backtest_accumulator.py`:

```python
"""
Background accumulator for the article-based backtest log — periodically
checks the calendar for high-impact USD events, and for tracked
instruments, runs the REAL article-based scoring pipeline
(scoring/probability_engine.py, not the essence-only dashboard path) and
persists each prediction to scoring/backtest_store.py's log — a genuine,
growing record of real predictions made blind, before the event, to be
confirmed against real outcomes later via scripts/confirm_backtest_outcomes.py.

Deliberately NOT wired into webapp/ — the dashboard is essence-only by
design (no article fetching at all); this accumulator is article-based
and a distinct concern, run as its own standalone process.

Budget-capped, not continuous: article fetches (RSS + Alpha Vantage) are
rate-limited resources, unlike the dashboard's free essence-only scoring.
At most SNAPSHOT_BUDGET_PER_PAIR prediction snapshots per (event,
instrument) pair — one when the event enters its pre-event window, one
more only once inside the final NEAR_WINDOW_HOURS stretch (same "how
close is close" definition as webapp/scheduler.py, reused directly
rather than re-defined).
"""
from __future__ import annotations

import datetime as dt
import threading
import time
from pathlib import Path
from typing import Optional

from data_layer.calendar_feed import fetch_calendar, filter_relevant_events, events_in_pre_window
from data_layer.event_context import build_event_news_bundle
from data_layer.rss_sources import build_all_preview_sources
from scoring.probability_engine import score_bundle
from scoring.backtest_store import get_connection, record_prediction, count_predictions
from webapp.scheduler import compute_adaptive_interval_seconds, NEAR_WINDOW_HOURS

SNAPSHOT_BUDGET_PER_PAIR = 2
# Used when a calendar fetch fails and there's no fresh event list to
# reason an adaptive interval from — same fallback pattern as
# webapp/scheduler.py's SCHEDULER_INTERVAL_SECONDS.
ACCUMULATOR_FALLBACK_INTERVAL_SECONDS = 15 * 60


def run_accumulator_cycle(
    instruments: list[str],
    db_path: Optional[Path] = None,
    now: Optional[dt.datetime] = None,
) -> Optional[list]:
    """
    Returns the fetched high-impact events on success (the caller uses
    this to pick the next adaptive poll interval), or None if the
    calendar fetch failed.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    conn = get_connection(db_path)
    try:
        try:
            all_events = fetch_calendar("thisweek")
        except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop
            print(f"[backtest_accumulator] WARNING: calendar fetch failed: {exc}")
            return None

        # High-impact only (default) — article fetches are budget-limited,
        # unlike the dashboard's free essence-only scoring which widens to Medium.
        events = filter_relevant_events(all_events)
        active = events_in_pre_window(events, now_utc=now)

        sources = None  # lazily built, only if at least one pair actually needs a fetch this cycle
        for event in active:
            hours_until = (event.event_time_utc - now).total_seconds() / 3600.0
            for instrument in instruments:
                existing = count_predictions(conn, event.title, instrument)
                if existing >= SNAPSHOT_BUDGET_PER_PAIR:
                    continue
                if existing == 1 and hours_until > NEAR_WINDOW_HOURS:
                    continue  # second snapshot only allowed in the final stretch

                if sources is None:
                    sources = build_all_preview_sources()

                try:
                    bundle = build_event_news_bundle(event, sources, query="", mode="live")
                    result = score_bundle(bundle, instrument)
                except Exception as exc:  # noqa: BLE001 — one pair's failure must not stop the others
                    print(f"[backtest_accumulator] WARNING: scoring failed for {instrument}/{event.title}: {exc}")
                    continue

                record_prediction(
                    conn, event.title, instrument, event.event_time_utc,
                    result.probability, result.direction.value, result.confidence,
                    result.article_count, result.contradiction_flag,
                )
                print(f"[backtest_accumulator] recorded {instrument} / {event.title}: {result.summary()}")

        return events
    finally:
        conn.close()


def start_accumulator(instruments: list[str]) -> None:
    def _loop():
        while True:
            try:
                events = run_accumulator_cycle(instruments)
                interval = (
                    ACCUMULATOR_FALLBACK_INTERVAL_SECONDS if events is None
                    else compute_adaptive_interval_seconds(events)
                )
            except Exception as exc:  # noqa: BLE001 — the loop must survive any unhandled error
                print(f"[backtest_accumulator] ERROR: cycle failed, will retry next interval: {exc}")
                interval = ACCUMULATOR_FALLBACK_INTERVAL_SECONDS
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()


if __name__ == "__main__":
    from config.settings import INSTRUMENTS
    tracked = list(INSTRUMENTS.keys())
    print(f"Running one accumulator cycle for: {tracked}")
    run_accumulator_cycle(tracked)
    print("Done. For continuous operation, import start_accumulator() into a long-running process.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_backtest_accumulator.py`
Expected: `All backtest_accumulator tests passed.`

- [ ] **Step 5: Commit**

```bash
git add scoring/backtest_accumulator.py tests/test_backtest_accumulator.py
git commit -m "feat: budget-capped article-based backtest accumulator scheduler"
```

---

### Task 3: Manual outcome-confirmation CLI

**Files:**
- Create: `scripts/confirm_backtest_outcomes.py`

**Interfaces:**
- Consumes: `get_connection`, `get_predictions_awaiting_outcome`, `record_outcome` from `scoring.backtest_store` (Task 1).
- Produces: a runnable script, `python scripts/confirm_backtest_outcomes.py` (interactive) or `--list` (list only, no prompts).
- No automated test — this is an interactive CLI with no good automated-test harness in this project's conventions (same category as Task 6 of the earlier dashboard plan's frontend). Verification is manual, per Step 3 below. `record_outcome()` itself is already covered by Task 1's tests — this script is a thin orchestration layer over it.

- [ ] **Step 1: Write the implementation**

Create `scripts/confirm_backtest_outcomes.py`:

```python
"""
Manual outcome confirmation for the article-based backtest accumulator.
Lists every prediction whose event has passed with no recorded outcome
yet, and prompts for the real result — same research rigor as this
project's reconstructed backtest cases (tests/run_historical_backtest.py),
just applied to real predictions made blind (before the event actually
happened), not reconstructed after the fact.

Usage:
    python scripts/confirm_backtest_outcomes.py          # interactive
    python scripts/confirm_backtest_outcomes.py --list   # list only, no prompts
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import get_connection, get_predictions_awaiting_outcome, record_outcome


def main():
    list_only = "--list" in sys.argv
    conn = get_connection()
    awaiting = get_predictions_awaiting_outcome(conn)

    if not awaiting:
        print("Nothing awaiting confirmation — every past prediction already has a recorded outcome.")
        conn.close()
        return

    print(f"{len(awaiting)} prediction(s) awaiting outcome confirmation:\n")
    for p in awaiting:
        print(f"  {p.instrument} / {p.event_title} ({p.event_time_utc}) — "
              f"predicted {p.direction.upper()} {p.probability:.0%}, "
              f"{p.confidence:.0%} confidence, {p.article_count} articles")

    if list_only:
        conn.close()
        return

    print("\nFor each, research the real outcome and enter it below (blank direction to skip):\n")
    for p in awaiting:
        print(f"--- {p.instrument} / {p.event_title} ({p.event_time_utc}) ---")
        print(f"    predicted: {p.direction.upper()} {p.probability:.0%}")
        direction = input("    actual direction (bullish/bearish/neutral, blank to skip): ").strip().lower()
        if not direction:
            print("    skipped.\n")
            continue
        if direction not in {"bullish", "bearish", "neutral"}:
            print(f"    {direction!r} is not bullish/bearish/neutral — skipped.\n")
            continue
        note = input("    real outcome note (what actually happened, with source): ").strip()
        event_time = dt.datetime.fromisoformat(p.event_time_utc)
        record_outcome(conn, p.event_title, p.instrument, event_time, direction, note)
        print("    recorded.\n")

    conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Manual verification**

Run: `python scripts/confirm_backtest_outcomes.py --list`
Expected (with an empty/fresh `scoring/backtest_log.db`): `Nothing awaiting confirmation — every past prediction already has a recorded outcome.`

Then seed a fake past prediction to confirm the listing/prompt path works:

```bash
python -c "
import datetime as dt
from scoring.backtest_store import get_connection, record_prediction
conn = get_connection()
record_prediction(conn, 'Test Event', 'XAUUSD', dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1), 0.7, 'bullish', 0.5, 5, False)
conn.close()
print('seeded')
"
python scripts/confirm_backtest_outcomes.py --list
```

Expected: the seeded prediction appears in the list. Then clean up the test row (delete `scoring/backtest_log.db` — it's gitignored, safe to remove) so it doesn't linger as fake data:

```bash
rm scoring/backtest_log.db
```

- [ ] **Step 3: Commit**

```bash
git add scripts/confirm_backtest_outcomes.py
git commit -m "feat: manual outcome-confirmation CLI for the backtest accumulator"
```

---

### Task 4: Reporting

**Files:**
- Modify: `scoring/backtest.py`
- Test: `tests/test_backtest_report.py`

**Interfaces:**
- Consumes: `get_all_confirmed_cases`, `get_connection` from `scoring.backtest_store` (Task 1); `EconomicEvent` from `data_layer.calendar_feed` (already imported in `backtest.py`); `Direction`, `ProbabilityResult` from `scoring.probability_engine` (already imported in `backtest.py`); `BacktestCase`, `BacktestReport` (already defined in `backtest.py`).
- Produces: `build_real_backtest_report(db_path: Optional[Path] = None) -> BacktestReport` (new function, appended to `scoring/backtest.py`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_backtest_report.py`:

```python
"""
Tests for scoring/backtest.py's build_real_backtest_report() — uses a
temp SQLite file, no network needed.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scoring.backtest_store as store
import scoring.backtest as backtest


def test_build_real_backtest_report_from_confirmed_cases():
    print("=== backtest: build_real_backtest_report reads confirmed cases and produces a working report ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        store.record_prediction(conn, "NFP", "XAUUSD", event_time, 0.71, "bullish", 0.55, 12, False)
        store.record_outcome(conn, "NFP", "XAUUSD", event_time, "bullish", "confirmed real move")
        conn.close()

        report = backtest.build_real_backtest_report(db_path=db_path)
        assert len(report.cases) == 1
        assert report.cases[0].predicted_correct is True
        assert report.accuracy() == 1.0
    print("PASS\n")


def test_build_real_backtest_report_marks_wrong_calls_correctly():
    print("=== backtest: a mismatched prediction/outcome direction is correctly marked wrong ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 1, 12, 30, tzinfo=dt.timezone.utc)
        store.record_prediction(conn, "CPI", "XAUUSD", event_time, 0.65, "bearish", 0.4, 8, False)
        store.record_outcome(conn, "CPI", "XAUUSD", event_time, "bullish", "actual move was the opposite direction")
        conn.close()

        report = backtest.build_real_backtest_report(db_path=db_path)
        assert len(report.cases) == 1
        assert report.cases[0].predicted_correct is False
        assert report.accuracy() == 0.0
    print("PASS\n")


def test_build_real_backtest_report_empty_when_nothing_confirmed():
    print("=== backtest: an empty confirmed-cases table produces an empty report, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        store.get_connection(db_path).close()  # just create the schema, no rows

        report = backtest.build_real_backtest_report(db_path=db_path)
        assert len(report.cases) == 0
        assert report.accuracy() is None
    print("PASS\n")


if __name__ == "__main__":
    test_build_real_backtest_report_from_confirmed_cases()
    test_build_real_backtest_report_marks_wrong_calls_correctly()
    test_build_real_backtest_report_empty_when_nothing_confirmed()
    print("All backtest_report tests passed.")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_backtest_report.py`
Expected: `AttributeError: module 'scoring.backtest' has no attribute 'build_real_backtest_report'`

- [ ] **Step 3: Write the implementation**

Append to `scoring/backtest.py` (at the end of the file, after the existing `BacktestReport` class — check the file's current imports first: it already imports `EconomicEvent` from `data_layer.calendar_feed`, `Direction`/`ProbabilityResult`/`score_bundle` from `scoring.probability_engine`, and `import datetime as dt`; only new import needed is from `scoring.backtest_store`):

```python
def build_real_backtest_report(db_path: Optional[Path] = None) -> BacktestReport:
    """
    Builds a BacktestReport from the article-based accumulator's real,
    confirmed (prediction, outcome) pairs — scoring/backtest_store.py's
    running log. Same report shape as the reconstructed backtest
    (tests/run_historical_backtest.py), so real and reconstructed
    results are directly comparable via the same print_report() output.
    """
    from scoring.backtest_store import get_all_confirmed_cases, get_connection

    conn = get_connection(db_path)
    confirmed = get_all_confirmed_cases(conn)
    conn.close()

    report = BacktestReport()
    for prediction, outcome in confirmed:
        event = EconomicEvent(
            title=prediction.event_title, country="USD", impact="High",
            event_time_utc=dt.datetime.fromisoformat(prediction.event_time_utc),
        )
        case = BacktestCase(
            event=event, instrument=prediction.instrument,
            actual_direction=Direction(outcome.actual_direction),
            actual_move_note=outcome.actual_move_note,
        )
        case.result = ProbabilityResult(
            instrument=prediction.instrument,
            as_of_utc=dt.datetime.fromisoformat(prediction.scored_at_utc),
            aggregate_usd_sentiment=0.0, instrument_score=0.0,
            probability=prediction.probability, direction=Direction(prediction.direction),
            confidence=prediction.confidence, article_count=prediction.article_count,
            contradiction_flag=prediction.contradiction_flag, contradiction_note=None,
        )
        case.evaluate()
        report.add(case)
    return report
```

Also add `from pathlib import Path` and `from typing import Optional` to `backtest.py`'s imports if not already present — check the top of the file first, add only what's missing.

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_backtest_report.py`
Expected: `All backtest_report tests passed.`

- [ ] **Step 5: Run the existing backtest-related tests to confirm no regression**

Run: `python tests/run_historical_backtest.py` (with `PYTHONIOENCODING=utf-8` if on Windows)
Expected: same output as before this task (14 events, ~92% accuracy) — this task only adds a new function, doesn't touch `run_backtest_case`/`run_backtest_case_manual`/`BacktestCase`/`BacktestReport`'s existing behavior.

- [ ] **Step 6: Commit**

```bash
git add scoring/backtest.py tests/test_backtest_report.py
git commit -m "feat: build a BacktestReport from the real accumulated (prediction, outcome) log"
```

---

### Task 5: Wire-up — README and final smoke check

**Files:**
- Modify: `README.md`

**Interfaces:**
- None — documentation only.

- [ ] **Step 1: Add a section to the README**

In `README.md`, after the "## Symbol impact dashboard (optional)" section (added in the earlier dashboard plan) and before "## Known gaps / things to watch", add:

```markdown
## Article-based backtest accumulator (optional)

Separate from the dashboard above (which is essence-only, no articles at
all) — this accumulates REAL backtest data for the article-based
pipeline (`scoring/probability_engine.py`) automatically, going forward.
Predictions are made blind (before the event, real fetched articles),
persisted immediately; outcomes are confirmed manually afterward via
research, same rigor as `tests/run_historical_backtest.py`'s
reconstructed cases — just applied to real predictions instead.

```bash
python scoring/backtest_accumulator.py   # runs one cycle; import start_accumulator() for continuous operation
python scripts/confirm_backtest_outcomes.py --list   # see what's awaiting confirmation
python scripts/confirm_backtest_outcomes.py          # confirm outcomes interactively
```

Then view real accuracy at any time:

```python
from scoring.backtest import build_real_backtest_report
build_real_backtest_report().print_report()
```

Budget-capped: at most 2 article-fetch snapshots per (event, instrument)
pair (once on window entry, once in the final stretch) — article fetches
are rate-limited (Alpha Vantage: 25/day), unlike the dashboard's free
essence-only scoring. High-impact USD events only, no Medium-impact
widening.

This is also what finally makes real calibration of
`TIME_DECAY_HALF_LIFE_MINUTES`/`CONTRADICTION_MIN_MAGNITUDE`/the sigmoid
steepness `k` possible — once this log has enough real confirmed cases,
those constants can be revisited against genuine data instead of guesses
(see "Known gaps" below).
```

- [ ] **Step 2: Run every test file in the project to confirm nothing regressed**

Run (with `PYTHONIOENCODING=utf-8` on Windows):
```bash
python tests/test_scoring_smoke.py
python tests/test_news_sources.py
python tests/test_calendar_feed.py
python tests/test_backtest_store.py
python tests/test_backtest_accumulator.py
python tests/test_backtest_report.py
python tests/test_webapp_symbols.py
python tests/test_webapp_scoring_service.py
python tests/test_webapp_store.py
python tests/test_webapp_scheduler.py
python tests/test_webapp_app.py
```
Expected: every file prints its own "All ... passed." line, no failures.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document the article-based backtest accumulator"
```
