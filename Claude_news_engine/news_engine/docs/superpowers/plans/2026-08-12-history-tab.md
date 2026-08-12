# History Tab (Print-Call Track Record) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third dashboard tab showing a consolidated, reviewable
record of the engine's print-direction calls against what actually
happened — Previous/Forecast/Actual columns plus an NE Prediction column
with a Confirmed/Missed judgment.

**Architecture:** A new read-only cross-pipeline module
(`webapp/history.py`) joins `webapp/store.py`'s `event_history` (resolved
occurrences) with `scoring/backtest_store.py`'s `print_predictions` (the
latest call per occurrence), producing `HistoryRow`s with a computed
Confirmed/Missed outcome. A new `GET /api/history` route serves it. A new
"History" tab, fetched once on first selection (not on the dashboard's
60s poll cycle), renders the table.

**Tech Stack:** Python 3.14, Flask, SQLite (stdlib `sqlite3`), vanilla JS
— matches the existing stack, no new dependencies.

## Global Constraints

- No new tables, no schema change to `event_history` or `print_predictions`.
- Only resolved occurrences (`event_history.actual IS NOT NULL`) **with**
  a matching `print_predictions` row appear — both conditions required,
  neither shown alone.
- A print call is excluded from Confirmed/Missed judging (shown as "No
  strong call", `outcome=None`) when its `confidence <= NO_HIT_CONFIDENCE`
  (0.15 — the exact constant `scoring/print_direction.py` already defines
  for its zero-phrase-hit default).
- Confirmed/Missed is exact string equality between
  `print_predictions.predicted_vs_forecast` and
  `event_history.surprise_direction` — no new comparison vocabulary.
- `unchanged_vs_previous` (`actual == previous`, plain string equality) is
  a **display-only** badge — it must never affect `outcome`, must never be
  fed into `score_bundle()` or any scoring path.
- A cross-pipeline read failure (accumulator DB missing/locked) fails open
  to an empty result — never crashes the route, never a 500.
- `limit` default is 50, most-recent-first (`event_time_utc DESC`).

---

### Task 1: `get_resolved_event_history()` + `webapp/history.py`

**Files:**
- Modify: `webapp/store.py` (add `get_resolved_event_history()`)
- Create: `webapp/history.py`
- Test: `tests/test_webapp_store.py`, `tests/test_webapp_history.py` (new file)

**Interfaces:**
- Consumes: `EventHistoryRow` (existing, `webapp.store`), `PrintPrediction`,
  `get_latest_print_prediction(conn, event_title, event_time_utc)`
  (existing, `scoring.backtest_store`), `NO_HIT_CONFIDENCE` (existing,
  `scoring.print_direction`).
- Produces: `get_resolved_event_history(conn, limit=200) ->
  list[EventHistoryRow]` (`webapp.store`); `HistoryRow` dataclass and
  `build_print_call_history(limit=50) -> list[HistoryRow]`
  (`webapp.history`). Task 2 imports `build_print_call_history`.

- [ ] **Step 1: Write the failing `get_resolved_event_history()` test**

Add to `tests/test_webapp_store.py`, before its `__main__` block:

```python
def test_get_resolved_event_history_only_returns_rows_with_actual():
    print("=== store: get_resolved_event_history only returns rows where actual is set, across ALL titles ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        resolved = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
            forecast="0.1%", previous="-0.4%", actual="0.1%",
        )
        pending = EconomicEvent(
            title="Core CPI m/m", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
            forecast="0.2%", previous="0.0%", actual=None,
        )
        store.upsert_event_history(conn, resolved, "in_line", now=dt.datetime(2026, 8, 12, 13, 0, tzinfo=UTC_TZ))
        store.upsert_event_history(conn, pending, None, now=dt.datetime(2026, 8, 12, 4, 0, tzinfo=UTC_TZ))

        rows = store.get_resolved_event_history(conn)
        assert len(rows) == 1
        assert rows[0].event_title == "CPI m/m"
        conn.close()
    print("PASS\n")


def test_get_resolved_event_history_most_recent_first_and_limit():
    print("=== store: get_resolved_event_history orders most-recent-first, respects limit ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        for month, title in [(6, "CPI m/m"), (7, "PPI m/m"), (8, "NFP")]:
            event = EconomicEvent(
                title=title, country="USD", impact="High",
                event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                forecast="0.1%", previous="0.1%", actual="0.2%",
            )
            store.upsert_event_history(conn, event, "higher", now=dt.datetime(2026, month, 12, 13, 0, tzinfo=UTC_TZ))

        rows = store.get_resolved_event_history(conn, limit=2)
        assert len(rows) == 2
        assert rows[0].event_title == "NFP"
        assert rows[1].event_title == "PPI m/m"
        conn.close()
    print("PASS\n")
```

Register both in the file's `__main__` block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_store.py`
Expected: `AttributeError: module 'webapp.store' has no attribute 'get_resolved_event_history'`

- [ ] **Step 3: Add `get_resolved_event_history()` to `webapp/store.py`**

Add at the end of the file:

```python
def get_resolved_event_history(conn: sqlite3.Connection, limit: int = 200) -> list[EventHistoryRow]:
    """
    Every RESOLVED event occurrence (actual IS NOT NULL) across ALL event
    titles, most recent first, capped at `limit`. Unlike get_event_history()
    (scoped to one title, includes pending occurrences), this is the
    cross-title, resolved-only query webapp/history.py's History tab needs.
    """
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction "
        "FROM event_history WHERE actual IS NOT NULL ORDER BY event_time_utc DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_store.py`
Expected: all tests PASS, including the 2 new ones.

- [ ] **Step 5: Write the failing `webapp/history.py` tests**

Create `tests/test_webapp_history.py`:

```python
"""
Tests for webapp/history.py — the History tab's read-only cross-pipeline
join between webapp.store's event_history and scoring.backtest_store's
print_predictions. No network needed.
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
from scoring.print_direction import PrintCall
import webapp.history as history
import webapp.store as store
import scoring.backtest_store as backtest_store


def _resolved_event(title, event_time, forecast, previous, actual):
    return EconomicEvent(
        title=title, country="USD", impact="High", event_time_utc=event_time,
        forecast=forecast, previous=previous, actual=actual,
    )


def test_resolved_event_with_real_call_is_judged():
    print("=== build_print_call_history: a resolved event with a real (non-shrug) call is Confirmed or Missed ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Core CPI m/m", event_time, "0.2%", "0.0%", "0.2%"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "Core CPI m/m", event_time,
            PrintCall(direction="lower", confidence=0.51, article_count=89), now=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].event_title == "Core CPI m/m"
        assert rows[0].ne_prediction == "lower"
        assert rows[0].outcome == "Missed"  # predicted lower, actual was in_line
    print("PASS\n")


def test_resolved_event_with_shrug_call_excluded_from_judging():
    print("=== build_print_call_history: a shrug call (confidence <= NO_HIT_CONFIDENCE) is shown but not judged ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.1%"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", event_time,
            PrintCall(direction="in_line", confidence=0.15, article_count=89), now=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].outcome is None
    print("PASS\n")


def test_confidence_just_above_shrug_threshold_is_judged():
    print("=== build_print_call_history: confidence just above NO_HIT_CONFIDENCE is judged normally, not excluded ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.1%"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", event_time,
            PrintCall(direction="in_line", confidence=0.16, article_count=89), now=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows[0].outcome == "Confirmed"
    print("PASS\n")


def test_unresolved_event_excluded_entirely():
    print("=== build_print_call_history: an event with no actual yet is excluded entirely, not shown with blanks ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 13, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("PPI m/m", event_time, "0.2%", "-0.3%", None),
            None, now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "PPI m/m", event_time,
            PrintCall(direction="in_line", confidence=0.15, article_count=93), now=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows == []
    print("PASS\n")


def test_resolved_event_with_no_print_call_excluded_entirely():
    print("=== build_print_call_history: a resolved event with NO print_predictions row at all is excluded entirely ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Building Permits m/m", event_time, "0.8%", "-1.7%", "0.9%"),
            "higher", now=event_time,
        )
        dash_conn.close()

        backtest_store.get_connection(backtest_db).close()  # real, empty backtest DB

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows == []
    print("PASS\n")


def test_only_latest_print_prediction_per_occurrence_surfaces():
    print("=== build_print_call_history: multiple historical print_predictions rows for one occurrence only surface the latest ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.1%"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", event_time,
            PrintCall(direction="higher", confidence=0.6, article_count=40), now=event_time - dt.timedelta(hours=6),
        )
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", event_time,
            PrintCall(direction="in_line", confidence=0.3, article_count=89), now=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert len(rows) == 1
        assert rows[0].ne_prediction == "in_line"  # the latest call, not the first
        assert rows[0].outcome == "Confirmed"
    print("PASS\n")


def test_unchanged_vs_previous_badge_does_not_affect_outcome():
    print("=== build_print_call_history: unchanged_vs_previous is a pure display flag, zero effect on outcome ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        unchanged_time = dt.datetime(2026, 7, 12, 12, 30, tzinfo=UTC_TZ)
        changed_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", unchanged_time, "0.2%", "0.2%", "0.2%"),
            "in_line", now=unchanged_time,
        )
        store.upsert_event_history(
            dash_conn, _resolved_event("PPI m/m", changed_time, "0.2%", "-0.3%", "0.2%"),
            "higher", now=changed_time,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "CPI m/m", unchanged_time,
            PrintCall(direction="in_line", confidence=0.4, article_count=50), now=unchanged_time,
        )
        backtest_store.record_print_prediction_if_changed(
            bt_conn, "PPI m/m", changed_time,
            PrintCall(direction="higher", confidence=0.4, article_count=50), now=changed_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        unchanged_row = next(r for r in rows if r.event_title == "CPI m/m")
        changed_row = next(r for r in rows if r.event_title == "PPI m/m")
        assert unchanged_row.unchanged_vs_previous is True
        assert changed_row.unchanged_vs_previous is False
        # Both otherwise-correct calls — outcome must be identical regardless of the badge.
        assert unchanged_row.outcome == "Confirmed"
        assert changed_row.outcome == "Confirmed"
    print("PASS\n")


def test_cross_pipeline_read_failure_fails_open_to_empty_list():
    print("=== build_print_call_history: an unreachable backtest DB fails open to an empty list, does not raise ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("CPI m/m", event_time, "0.1%", "-0.4%", "0.1%"),
            "in_line", now=event_time,
        )
        dash_conn.close()

        unreachable_backtest_db = Path(tmp) / "nonexistent_subdir" / "backtest.db"

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", unreachable_backtest_db):
            rows = history.build_print_call_history()  # must not raise

        assert rows == []
    print("PASS\n")


def test_empty_result_when_nothing_resolved():
    print("=== build_print_call_history: no resolved history at all returns an empty list, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        store.get_connection(dash_db).close()
        backtest_store.get_connection(backtest_db).close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows == []
    print("PASS\n")


if __name__ == "__main__":
    test_resolved_event_with_real_call_is_judged()
    test_resolved_event_with_shrug_call_excluded_from_judging()
    test_confidence_just_above_shrug_threshold_is_judged()
    test_unresolved_event_excluded_entirely()
    test_resolved_event_with_no_print_call_excluded_entirely()
    test_only_latest_print_prediction_per_occurrence_surfaces()
    test_unchanged_vs_previous_badge_does_not_affect_outcome()
    test_cross_pipeline_read_failure_fails_open_to_empty_list()
    test_empty_result_when_nothing_resolved()
    print("All webapp_history tests passed.")
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `python tests/test_webapp_history.py`
Expected: `ModuleNotFoundError: No module named 'webapp.history'`

- [ ] **Step 7: Implement `webapp/history.py`**

```python
"""
Read-only cross-pipeline join for the dashboard's History tab —
webapp.store's event_history (resolved occurrences, this dashboard's own
DB) joined with scoring.backtest_store's print_predictions (the latest
call per occurrence, the accumulator's DB), producing a Confirmed/Missed
track record.

Mirrors the read-only cross-pipeline pattern already established twice in
this codebase: webapp/app.py reads scoring.backtest_store's DB read-only
for the print-call badge; scoring/backtest_accumulator.py reads
webapp.store's DB read-only for the trend signal. This module is the
third instance, dashboard-side, display-only — it writes nothing to
either DB.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from scoring.print_direction import NO_HIT_CONFIDENCE
from webapp.store import get_connection, get_resolved_event_history

DEFAULT_HISTORY_LIMIT = 50


@dataclass
class HistoryRow:
    event_title: str
    event_time_utc: str
    previous: Optional[str]
    forecast: Optional[str]
    actual: Optional[str]
    unchanged_vs_previous: bool
    ne_prediction: str
    ne_confidence: float
    outcome: Optional[str]  # 'Confirmed' | 'Missed' | None


def build_print_call_history(limit: int = DEFAULT_HISTORY_LIMIT) -> list[HistoryRow]:
    """
    Only resolved event_history occurrences (actual IS NOT NULL) WITH a
    matching print_predictions row appear — either condition missing means
    the occurrence is skipped entirely, not shown with blanks. Fails open
    to an empty list if the backtest DB is unreachable for any reason —
    never crashes the /api/history route over a cross-pipeline read error.
    """
    # Import here, not at module level, to avoid a hard import-time
    # dependency cycle risk between webapp and scoring — matches the
    # existing lazy-import style already used for cross-pipeline reads
    # in scoring/backtest_accumulator.py's _read_trend_signal().
    from scoring.backtest_store import get_connection as get_backtest_connection, get_latest_print_prediction

    dash_conn = get_connection()
    try:
        resolved = get_resolved_event_history(dash_conn, limit=limit)
    finally:
        dash_conn.close()

    if not resolved:
        return []

    try:
        bt_conn = get_backtest_connection()
    except Exception as exc:  # noqa: BLE001 — an unreachable backtest DB must not crash the route
        print(f"[webapp.history] WARNING: could not read print_predictions: {exc}")
        return []

    rows: list[HistoryRow] = []
    try:
        for event in resolved:
            event_time = dt.datetime.fromisoformat(event.event_time_utc)
            try:
                call = get_latest_print_prediction(bt_conn, event.event_title, event_time)
            except Exception as exc:  # noqa: BLE001 — one bad lookup must not crash the whole build
                print(f"[webapp.history] WARNING: could not read print call for {event.event_title}: {exc}")
                continue
            if call is None:
                continue  # resolved event, but never scored by the accumulator — excluded, not shown with blanks

            outcome: Optional[str] = None
            if call.confidence > NO_HIT_CONFIDENCE:
                outcome = "Confirmed" if call.predicted_vs_forecast == event.surprise_direction else "Missed"

            rows.append(HistoryRow(
                event_title=event.event_title,
                event_time_utc=event.event_time_utc,
                previous=event.previous,
                forecast=event.forecast,
                actual=event.actual,
                unchanged_vs_previous=(event.actual == event.previous),
                ne_prediction=call.predicted_vs_forecast,
                ne_confidence=call.confidence,
                outcome=outcome,
            ))
    finally:
        bt_conn.close()

    return rows
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `python tests/test_webapp_history.py`
Expected: all 9 tests PASS.

- [ ] **Step 9: Run the regression sweep**

```bash
python tests/test_webapp_store.py
python tests/test_webapp_history.py
python tests/test_backtest_store.py
```

Expected: all PASS, no regressions.

- [ ] **Step 10: Commit**

```bash
git add webapp/store.py webapp/history.py tests/test_webapp_store.py tests/test_webapp_history.py
git commit -m "feat: add webapp/history.py — print-call track record join

get_resolved_event_history() (webapp/store.py) returns every resolved
occurrence across all event titles. build_print_call_history()
(new webapp/history.py) joins that with scoring/backtest_store.py's
latest print_predictions call per occurrence, producing Confirmed/
Missed via exact predicted_vs_forecast/surprise_direction equality.
Calls at or below NO_HIT_CONFIDENCE (0.15, the zero-hit lexicon
default) are shown but excluded from judging. unchanged_vs_previous
is computed but proven (via a dedicated test) to have zero effect on
outcome — display-only, never a scoring input.

Read-only cross-pipeline read of the accumulator's DB, mirroring the
two existing precedents (webapp/app.py's print-call badge,
scoring/backtest_accumulator.py's trend-signal read) — fails open to
an empty list on any read error, verified by a dedicated test using
an unreachable DB path."
```

---

### Task 2: `GET /api/history` route

**Files:**
- Modify: `webapp/app.py`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `build_print_call_history()` (Task 1, `webapp.history`).
- Produces: no new interface — this is a thin route wrapping Task 1's function.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_webapp_app.py`, before its `__main__` block:

```python
def test_history_endpoint_returns_rows():
    print("=== app: /api/history returns build_print_call_history()'s rows as JSON ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
            event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
                forecast="0.1%", previous="-0.4%", actual="0.1%",
            )
            conn = store.get_connection(db_path)
            store.upsert_event_history(conn, event, "in_line", now=event_time)
            conn.close()

            from scoring.print_direction import PrintCall
            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_print_prediction_if_changed(
                bconn, "CPI m/m", event_time,
                PrintCall(direction="in_line", confidence=0.4, article_count=89), now=event_time,
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/history")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data["rows"]) == 1
            assert data["rows"][0]["event_title"] == "CPI m/m"
            assert data["rows"][0]["outcome"] == "Confirmed"
    print("PASS\n")


def test_history_endpoint_empty_when_nothing_resolved():
    print("=== app: /api/history returns an empty list (200, not 500) when nothing has resolved yet ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            store.get_connection(db_path).close()
            backtest_store.get_connection(backtest_db_path).close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/history")
            assert resp.status_code == 200
            assert resp.get_json()["rows"] == []
    print("PASS\n")
```

Register both in the file's `__main__` block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_app.py`
Expected: `404` — the route doesn't exist yet.

- [ ] **Step 3: Add the route to `webapp/app.py`**

Modify the import block (add one line, after the existing `from webapp.trend import summarize_trend` line):

```python
from webapp.trend import summarize_trend
from webapp.history import build_print_call_history
```

Add the route (after `get_prediction_history()`, before `_get_tracked_symbols()`):

```python
@app.route("/api/history", methods=["GET"])
def get_print_call_history():
    rows = build_print_call_history()
    return jsonify({
        "rows": [
            {
                "event_title": r.event_title, "event_time_utc": r.event_time_utc,
                "previous": r.previous, "forecast": r.forecast, "actual": r.actual,
                "unchanged_vs_previous": r.unchanged_vs_previous,
                "ne_prediction": r.ne_prediction, "ne_confidence": r.ne_confidence,
                "outcome": r.outcome,
            }
            for r in rows
        ],
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_app.py`
Expected: all tests PASS, including the 2 new ones.

- [ ] **Step 5: Run the regression sweep**

```bash
python tests/test_webapp_app.py
python tests/test_webapp_history.py
```

Expected: all PASS, no regressions.

- [ ] **Step 6: Commit**

```bash
git add webapp/app.py tests/test_webapp_app.py
git commit -m "feat: add GET /api/history route serving the print-call track record

Thin wrapper over webapp.history.build_print_call_history() — no
logic of its own beyond JSON serialization. Empty case returns 200
with an empty rows list, never a 500."
```

---

### Task 3: History tab UI

**Files:**
- Modify: `webapp/static/index.html` (new tab button + view section)
- Modify: `webapp/static/app.js` (render function, fetch-on-first-select, `showView` update)
- Modify: `webapp/static/style.css` (minimal table styling)

**Interfaces:**
- Consumes: `GET /api/history` (Task 2's route, response shape
  `{rows: [{event_title, event_time_utc, previous, forecast, actual,
  unchanged_vs_previous, ne_prediction, ne_confidence, outcome}]}`).
- Produces: no new interfaces — final UI-only task.

No automated test — this codebase has no JS test harness (established
pattern from every prior UI task this session). Verified live via browser
after implementation.

- [ ] **Step 1: Add the tab button and view section to `webapp/static/index.html`**

Modify the `<nav>` block (currently lines 11-14):

```html
  <nav>
    <button id="tab-dashboard" class="tab-btn active">Dashboard</button>
    <button id="tab-calendar" class="tab-btn">Calendar</button>
    <button id="tab-history" class="tab-btn">History</button>
  </nav>
```

Add a new `<section>` after the existing `#view-calendar` section (currently ending at line 30), before `<script src="/static/app.js"></script>`:

```html
<section id="view-history" style="display:none">
  <div id="history-empty-notice" class="stale-notice" style="display:none">No confirmed calls yet.</div>
  <table id="history-table" style="display:none">
    <thead>
      <tr><th>Event</th><th>Previous</th><th>Forecast</th><th>Actual</th><th>NE Prediction</th><th>Outcome</th></tr>
    </thead>
    <tbody id="history-tbody"></tbody>
  </table>
</section>
```

- [ ] **Step 2: Wire the tab and fetch-on-first-select in `webapp/static/app.js`**

Modify the tab click-handler block (currently lines 21-22):

```javascript
document.getElementById("tab-dashboard").addEventListener("click", () => showView("dashboard"));
document.getElementById("tab-calendar").addEventListener("click", () => showView("calendar"));
document.getElementById("tab-history").addEventListener("click", () => {
  showView("history");
  loadHistoryIfNeeded();
});
```

Modify `showView()` (currently lines 24-29):

```javascript
function showView(name) {
  document.getElementById("view-dashboard").style.display = name === "dashboard" ? "" : "none";
  document.getElementById("view-calendar").style.display = name === "calendar" ? "" : "none";
  document.getElementById("view-history").style.display = name === "history" ? "" : "none";
  document.getElementById("tab-dashboard").classList.toggle("active", name === "dashboard");
  document.getElementById("tab-calendar").classList.toggle("active", name === "calendar");
  document.getElementById("tab-history").classList.toggle("active", name === "history");
}
```

Add the fetch-on-first-select logic and render function at the end of the file, after the existing `refreshAll();` / `setInterval(refreshAll, POLL_INTERVAL_MS);` lines:

```javascript
let historyLoaded = false;

async function loadHistoryIfNeeded() {
  if (historyLoaded) return;  // fetched once per page load, not on the dashboard's poll cycle
  historyLoaded = true;
  const resp = await fetch("/api/history");
  const data = await resp.json();
  renderHistoryTable(data.rows || []);
}

function renderHistoryTable(rows) {
  const table = document.getElementById("history-table");
  const emptyNotice = document.getElementById("history-empty-notice");
  const tbody = document.getElementById("history-tbody");

  if (rows.length === 0) {
    table.style.display = "none";
    emptyNotice.style.display = "";
    return;
  }

  emptyNotice.style.display = "none";
  table.style.display = "";
  tbody.innerHTML = rows.map((r) => {
    const dateLabel = new Date(r.event_time_utc).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    const actualCell = r.unchanged_vs_previous
      ? `${escapeHtml(r.actual ?? "—")} <span style="color:#888;font-size:11px">(= prev)</span>`
      : escapeHtml(r.actual ?? "—");
    const predictionLabel = r.ne_prediction === "higher" ? "Higher"
      : r.ne_prediction === "lower" ? "Lower" : "In-line";
    const outcomeLabel = r.outcome === null
      ? '<span style="color:#888">No strong call</span>'
      : r.outcome === "Confirmed"
        ? '<span style="color:#2e7d32;font-weight:bold">Confirmed</span>'
        : '<span style="color:#c62828;font-weight:bold">Missed</span>';
    return `<tr>
      <td>${escapeHtml(r.event_title)}<br><span style="font-size:11px;color:#888">${dateLabel}</span></td>
      <td>${escapeHtml(r.previous ?? "—")}</td>
      <td>${escapeHtml(r.forecast ?? "—")}</td>
      <td>${actualCell}</td>
      <td>${predictionLabel} <span style="font-size:11px;color:#888">(${Math.round(r.ne_confidence * 100)}% conf.)</span></td>
      <td>${outcomeLabel}</td>
    </tr>`;
  }).join("");
}
```

- [ ] **Step 3: Add minimal styling**

Append to `webapp/static/style.css`:

```css
#history-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
#history-table th, #history-table td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #ddd; font-size: 13px; }
#history-table th { color: #666; font-weight: 600; }
```

- [ ] **Step 4: Verify no JS syntax errors**

Run: `node --check webapp/static/app.js`
Expected: no output (clean).

- [ ] **Step 5: Verify in the browser**

Restart `run_all.py` (kill the existing process tree first, matching this
project's established restart procedure):

```bash
python scripts/run_all.py
```

Open `http://localhost:5001`, confirm:
- A "History" tab appears in the nav, alongside Dashboard/Calendar.
- Clicking it shows the History table (or the "No confirmed calls yet"
  empty-state message if nothing has resolved yet — expected on a fresh
  restart if the live CPI/PPI data hasn't fully resolved).
- No console errors on tab switch.
- Switching to Dashboard and back to History does NOT re-fetch
  `/api/history` a second time (check the browser's network tab, or
  trust the `historyLoaded` guard in Step 2).
- If any row IS present, confirm the `(= prev)` badge appears correctly
  when `actual` matches `previous`, and the Outcome column shows
  Confirmed/Missed/"No strong call" appropriately.

- [ ] **Step 6: Commit**

```bash
git add webapp/static/index.html webapp/static/app.js webapp/static/style.css
git commit -m "feat: add History tab UI for the print-call track record

Third tab (Dashboard/Calendar/History), table fetched once on first
selection via /api/history, not on the dashboard's 60s poll cycle.
Shows Previous/Forecast/Actual/NE Prediction/Outcome per resolved
occurrence, with a (= prev) badge when actual matches previous
(display-only, per the design's research finding — real for
inflation-type prints specifically, never fed into scoring). Empty
state shown explicitly when nothing has resolved yet. Verified live
via run_all.py — no JS test harness exists in this codebase."
```

---

### Task 4: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a new subsection**

Find the "### Trend-history feed-back into scoring" subsection (added by
the prior feature's plan) via `grep -n "Trend-history feed-back"
README.md`, and insert this new subsection immediately after it, before
the next `##`/`###` heading:

```markdown
### History tab

A third dashboard tab ("History", alongside Dashboard/Calendar) shows a
consolidated, reviewable record of the engine's print-direction calls
against what actually happened — `webapp/history.py`'s
`build_print_call_history()` joins `webapp/store.py`'s `event_history`
(resolved occurrences: Previous/Forecast/Actual) with
`scoring/backtest_store.py`'s `print_predictions` (the latest call per
occurrence), producing a Confirmed/Missed judgment via exact
`predicted_vs_forecast`/`surprise_direction` equality.

Only resolved occurrences (`actual` present) **with** a real print call
appear — either condition missing means the row is skipped, never shown
with blanks. A call at or below `NO_HIT_CONFIDENCE` (0.15 —
`scoring/print_direction.py`'s zero-phrase-hit default) is shown but
excluded from judging ("No strong call"), so the track record isn't
padded by default-neutral guesses that happened to land right by chance.

A `(= prev)` badge marks occurrences where `actual` exactly matches
`previous` — display-only context (real pattern for inflation-type
indicators specifically, per research done during this feature's design;
never fed into scoring or the Confirmed/Missed judgment — see
`docs/superpowers/specs/2026-08-12-history-tab-design.md`).

Same read-only cross-pipeline pattern as the print-call badge and trend
signal before it: opens a connection to the accumulator's DB, never
writes to it, fails open to an empty result on any read error.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document the History tab (print-call track record)"
```

---

## Post-plan verification (do this after all 4 tasks are complete)

- [ ] Run the full regression suite across every `tests/test_*.py` file:

```bash
for f in tests/test_*.py; do echo "--- $f ---"; python "$f" 2>&1 | tail -6; done
```

Expected: every file ends with its "All ... tests passed." line (or PASS).
`test_contextual_sentiment.py`'s SKIP lines and `test_scoring_smoke.py`'s
pre-existing Windows-console Unicode crash are both expected, pre-existing,
unrelated to this feature.

- [ ] Restart `run_all.py` and confirm live: the History tab loads, shows
      either real rows or the empty-state message, no console errors, and
      re-selecting the tab doesn't trigger a second fetch.
