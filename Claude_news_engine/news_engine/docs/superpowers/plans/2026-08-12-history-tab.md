# History Tab (Print-Call Track Record) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third dashboard tab showing a consolidated, reviewable
record of the engine's calls against what actually happened —
Previous/Forecast/Actual columns plus an NE Prediction column with a
Confirmed/Missed judgment, covering both numeric-forecast events (CPI,
PPI, etc.) and text-only high-impact events with no number at all (FOMC
Statement, Press Conference), which get their own instrument-specific row
using the accumulator's regular article-sentiment call instead.

**Architecture:** A new read-only cross-pipeline module
(`webapp/history.py`) joins `webapp/store.py`'s `event_history` with
`scoring/backtest_store.py`'s `print_predictions` (numeric events) and,
separately, `predictions`/`outcomes` (text-only events lacking any
forecast), merging both into one `HistoryRow` list. A new `GET
/api/history` route serves it. A new "History" tab, fetched once on first
selection, renders the table.

**Tech Stack:** Python 3.14, Flask, SQLite (stdlib `sqlite3`), vanilla JS
— matches the existing stack, no new dependencies.

## Global Constraints

- No new tables, no schema change to any existing table — every new
  function queries tables that already exist.
- **Numeric rows**: only resolved occurrences (`event_history.actual IS
  NOT NULL`) **with** a matching `print_predictions` row appear — both
  conditions required, neither shown alone. A call with `confidence <=
  NO_HIT_CONFIDENCE` (0.15, `scoring/print_direction.py`'s zero-hit
  default) is shown but excluded from judging (`outcome=None`, "No strong
  call"). Confirmed/Missed is exact string equality between
  `print_predictions.predicted_vs_forecast` and
  `event_history.surprise_direction`.
- **Text-event fallback rows**: only occurrences where `event_history`
  has **both** `forecast IS NULL` and `actual IS NULL` (the data-driven
  "genuinely non-numeric" signal — never a lexicon-coverage check) **and**
  `event_time_utc` is in the past qualify. One row per `(occurrence,
  instrument)` that has a real `predictions` row — instruments with no
  prediction get no row. Outcome is Confirmed/Missed against
  `outcomes.actual_direction` if a confirmed outcome exists, else
  `None`/"Awaiting confirmation" (never fabricated).
- `unchanged_vs_previous` (`actual == previous`, plain string equality) is
  a **display-only** badge on numeric rows only — always `False` on
  fallback rows (never fed into scoring or `outcome`).
- A cross-pipeline read failure (accumulator DB missing/locked) fails open
  to an empty result — never crashes the route, never a 500.
- `limit` default is 50, most-recent-first (`event_time_utc DESC`) across
  the merged (numeric + fallback) result.

---

### Task 1: `webapp/store.py` — resolved + text-only query functions

**Files:**
- Modify: `webapp/store.py`
- Test: `tests/test_webapp_store.py`

**Interfaces:**
- Consumes: `EventHistoryRow` (existing).
- Produces: `get_resolved_event_history(conn, limit=200) ->
  list[EventHistoryRow]`, `get_text_only_resolved_events(conn, now=None,
  limit=200) -> list[EventHistoryRow]`. Task 3 imports both.

- [ ] **Step 1: Write the failing tests**

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


def test_get_text_only_resolved_events_requires_both_forecast_and_actual_null():
    print("=== store: get_text_only_resolved_events only returns rows with BOTH forecast and actual NULL, past events only ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 12, 15, 0, tzinfo=UTC_TZ)

        text_only_past = EconomicEvent(
            title="FOMC Statement", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2),
            forecast=None, previous=None, actual=None,
        )
        numeric_event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2),
            forecast="0.1%", previous="-0.4%", actual="0.1%",
        )
        text_only_future = EconomicEvent(
            title="FOMC Press Conference", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=2),
            forecast=None, previous=None, actual=None,
        )
        store.upsert_event_history(conn, text_only_past, None, now=now)
        store.upsert_event_history(conn, numeric_event, "in_line", now=now)
        store.upsert_event_history(conn, text_only_future, None, now=now)

        rows = store.get_text_only_resolved_events(conn, now=now)
        assert len(rows) == 1
        assert rows[0].event_title == "FOMC Statement"
        conn.close()
    print("PASS\n")


def test_get_text_only_resolved_events_excludes_event_missing_only_one_field():
    print("=== store: an event with forecast set but actual null is NOT text-only (partial data, not genuinely numberless) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        now = dt.datetime(2026, 8, 12, 15, 0, tzinfo=UTC_TZ)
        partial = EconomicEvent(
            title="Advance GDP q/q", country="USD", impact="High",
            event_time_utc=now - dt.timedelta(hours=2),
            forecast="2.1%", previous="2.0%", actual=None,
        )
        store.upsert_event_history(conn, partial, None, now=now)

        rows = store.get_text_only_resolved_events(conn, now=now)
        assert rows == []
        conn.close()
    print("PASS\n")
```

Register all 4 in the file's `__main__` block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_store.py`
Expected: `AttributeError: module 'webapp.store' has no attribute 'get_resolved_event_history'`

- [ ] **Step 3: Add both functions to `webapp/store.py`**

Add at the end of the file:

```python
def get_resolved_event_history(conn: sqlite3.Connection, limit: int = 200) -> list[EventHistoryRow]:
    """
    Every RESOLVED event occurrence (actual IS NOT NULL) across ALL event
    titles, most recent first, capped at `limit`. Unlike get_event_history()
    (scoped to one title, includes pending occurrences), this is the
    cross-title, resolved-only query webapp/history.py's History tab needs
    for its numeric-forecast rows.
    """
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction "
        "FROM event_history WHERE actual IS NOT NULL ORDER BY event_time_utc DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]


def get_text_only_resolved_events(conn: sqlite3.Connection, now: Optional[dt.datetime] = None, limit: int = 200) -> list[EventHistoryRow]:
    """
    Past event occurrences that genuinely have NO forecast/actual figure
    at all (forecast IS NULL AND actual IS NULL) — e.g. FOMC Statement,
    FOMC Press Conference. Deliberately data-driven, not a check against
    PRINT_SURPRISE_LEXICON/EVENT_SURPRISE_DIRECTION: an event missing
    lexicon coverage today but that DOES have a real forecast (e.g. Core
    PPI m/m before it's added to the lexicon) is a config gap, not the
    same case as an event that structurally never publishes a number —
    only the latter belongs here.

    "Past" uses lexicographic ISO-8601 string comparison against `now`,
    same pattern get_predictions_awaiting_outcome() (scoring/backtest_store.py)
    already uses.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction "
        "FROM event_history WHERE forecast IS NULL AND actual IS NULL AND event_time_utc <= ? "
        "ORDER BY event_time_utc DESC LIMIT ?",
        (now.isoformat(), limit),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_store.py`
Expected: all tests PASS, including the 4 new ones.

- [ ] **Step 5: Commit**

```bash
git add webapp/store.py tests/test_webapp_store.py
git commit -m "feat: add get_resolved_event_history() + get_text_only_resolved_events()

Two new cross-title query functions on event_history for the History
tab: get_resolved_event_history() returns every occurrence with a
known actual, across all titles. get_text_only_resolved_events()
returns past occurrences with BOTH forecast and actual NULL — the
data-driven signal for a genuinely non-numeric event (FOMC Statement,
Press Conference), deliberately not a lexicon-coverage check, so a
numeric event just missing lexicon coverage isn't misclassified as
text-only."
```

---

### Task 2: `scoring/backtest_store.py` — occurrence-scoped prediction + outcome lookups

**Files:**
- Modify: `scoring/backtest_store.py`
- Test: `tests/test_backtest_store.py`

**Interfaces:**
- Consumes: `Prediction`, `Outcome` (existing dataclasses).
- Produces: `get_latest_prediction_for_occurrence(conn, event_title,
  instrument, event_time_utc) -> Optional[Prediction]`,
  `get_outcome(conn, event_title, instrument, event_time_utc) ->
  Optional[Outcome]`. Task 3 imports both.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_backtest_store.py`, before its `__main__` block:

```python
def test_get_latest_prediction_for_occurrence_scoped_not_title_leak():
    print("=== backtest_store: get_latest_prediction_for_occurrence does NOT leak a prior occurrence's prediction onto a different one ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        july_time = dt.datetime(2026, 7, 30, 18, 0, tzinfo=UTC_TZ)
        august_time = dt.datetime(2026, 9, 17, 18, 0, tzinfo=UTC_TZ)
        store.record_prediction(
            conn, "FOMC Statement", "XAUUSD", july_time,
            0.6, "bullish", 0.5, 40, False, scored_at_utc=july_time,
        )

        assert store.get_latest_prediction_for_occurrence(conn, "FOMC Statement", "XAUUSD", august_time) is None

        latest = store.get_latest_prediction_for_occurrence(conn, "FOMC Statement", "XAUUSD", july_time)
        assert latest is not None
        assert latest.probability == 0.6
        conn.close()
    print("PASS\n")


def test_get_outcome_returns_none_when_unconfirmed():
    print("=== backtest_store: get_outcome returns None when no outcome has been confirmed yet, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 7, 30, 18, 0, tzinfo=UTC_TZ)
        assert store.get_outcome(conn, "FOMC Statement", "XAUUSD", event_time) is None
        conn.close()
    print("PASS\n")


def test_get_outcome_returns_confirmed_outcome():
    print("=== backtest_store: get_outcome returns the confirmed outcome for this exact occurrence ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 7, 30, 18, 0, tzinfo=UTC_TZ)
        store.record_outcome(conn, "FOMC Statement", "XAUUSD", event_time, "bullish", "gold rallied on dovish tone")

        outcome = store.get_outcome(conn, "FOMC Statement", "XAUUSD", event_time)
        assert outcome is not None
        assert outcome.actual_direction == "bullish"
    print("PASS\n")
```

Register all 3 in the file's `__main__` block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_backtest_store.py`
Expected: `AttributeError: module 'scoring.backtest_store' has no attribute 'get_latest_prediction_for_occurrence'`

- [ ] **Step 3: Add both functions to `scoring/backtest_store.py`**

Add at the end of the file:

```python
def get_latest_prediction_for_occurrence(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
) -> Optional[Prediction]:
    """
    Most recent prediction snapshot for this EXACT (event_title,
    instrument, event_time_utc) occurrence — unlike get_latest_prediction()
    (title+instrument only), this is scoped to the specific occurrence,
    same reasoning as get_latest_print_prediction()'s occurrence scoping:
    a title recurs monthly/quarterly with the SAME title but a DIFFERENT
    event_time_utc each time, so a title-only lookup would leak a prior
    occurrence's prediction onto an unrelated later one.
    """
    row = conn.execute(
        "SELECT * FROM predictions WHERE event_title = ? AND instrument = ? AND event_time_utc = ? "
        "ORDER BY scored_at_utc DESC, id DESC LIMIT 1",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return Prediction(
        id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
        event_time_utc=d["event_time_utc"], scored_at_utc=d["scored_at_utc"],
        probability=d["probability"], direction=d["direction"], confidence=d["confidence"],
        article_count=d["article_count"], contradiction_flag=bool(d["contradiction_flag"]),
    )


def get_outcome(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
) -> Optional[Outcome]:
    """Confirmed outcome for this exact occurrence, or None if not yet confirmed — never fabricated."""
    row = conn.execute(
        "SELECT * FROM outcomes WHERE event_title = ? AND instrument = ? AND event_time_utc = ?",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return Outcome(
        id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
        event_time_utc=d["event_time_utc"], actual_direction=d["actual_direction"],
        actual_move_note=d["actual_move_note"], confirmed_at_utc=d["confirmed_at_utc"],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_backtest_store.py`
Expected: all tests PASS, including the 3 new ones.

- [ ] **Step 5: Commit**

```bash
git add scoring/backtest_store.py tests/test_backtest_store.py
git commit -m "feat: add occurrence-scoped get_latest_prediction_for_occurrence() + get_outcome()

Both needed by the History tab's text-only-event fallback rows (Task
3). get_latest_prediction_for_occurrence() is scoped to the exact
(event_title, instrument, event_time_utc) triple — the existing
get_latest_prediction() is title+instrument only, which would leak a
prior occurrence's call onto a later one with the same title (e.g.
July's FOMC Statement onto September's), the same bug class already
fixed for print_predictions. get_outcome() is a plain None-if-
unconfirmed lookup — outcome confirmation is a manual/--auto step in
this system, not automatic, so an absent outcome is a normal state."
```

---

### Task 3: `webapp/history.py` — merged join (numeric + text-event fallback)

**Files:**
- Create: `webapp/history.py`
- Test: `tests/test_webapp_history.py` (new file)

**Interfaces:**
- Consumes: `get_resolved_event_history`, `get_text_only_resolved_events`
  (Task 1, `webapp.store`); `get_latest_print_prediction`,
  `get_latest_prediction_for_occurrence`, `get_outcome` (existing +
  Task 2, `scoring.backtest_store`); `NO_HIT_CONFIDENCE` (existing,
  `scoring.print_direction`); `INSTRUMENTS` (existing, `config.settings`).
- Produces: `HistoryRow` dataclass (fields: `event_title: str,
  event_time_utc: str, instrument: Optional[str], previous: Optional[str],
  forecast: Optional[str], actual: Optional[str], unchanged_vs_previous:
  bool, ne_prediction: str, ne_confidence: float, outcome: Optional[str]`)
  and `build_print_call_history(limit=50) -> list[HistoryRow]`. Task 4
  imports `build_print_call_history`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_webapp_history.py`:

```python
"""
Tests for webapp/history.py — the History tab's read-only cross-pipeline
join between webapp.store's event_history and scoring.backtest_store's
print_predictions (numeric events) / predictions+outcomes (text-only
events). No network needed.
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


# --- Numeric-event rows ---

def test_resolved_event_with_real_call_is_judged():
    print("=== build_print_call_history: a resolved numeric event with a real (non-shrug) call is Confirmed or Missed ===")
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
        assert rows[0].instrument is None
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


def test_unresolved_numeric_event_excluded_entirely():
    print("=== build_print_call_history: a numeric event with no actual yet is excluded entirely ===")
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


def test_resolved_numeric_event_with_no_print_call_excluded_entirely():
    print("=== build_print_call_history: a resolved numeric event with NO print_predictions row is excluded entirely ===")
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

        backtest_store.get_connection(backtest_db).close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history()

        assert rows == []
    print("PASS\n")


def test_unchanged_vs_previous_badge_does_not_affect_outcome():
    print("=== build_print_call_history: unchanged_vs_previous is a pure display flag on numeric rows, zero effect on outcome ===")
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
        assert unchanged_row.outcome == "Confirmed"
        assert changed_row.outcome == "Confirmed"
    print("PASS\n")


# --- Text-event fallback rows ---

def test_text_only_event_with_prediction_produces_fallback_row():
    print("=== build_print_call_history: a text-only event (no forecast/actual) with a real prediction produces one row per instrument ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 17, 18, 0, tzinfo=UTC_TZ)
        now = event_time + dt.timedelta(hours=1)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("FOMC Statement", event_time, None, None, None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", event_time,
            0.62, "bullish", 0.5, 40, False, scored_at_utc=event_time,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert len(rows) == 1
        assert rows[0].event_title == "FOMC Statement"
        assert rows[0].instrument == "XAUUSD"
        assert rows[0].previous is None
        assert rows[0].forecast is None
        assert rows[0].actual is None
        assert rows[0].unchanged_vs_previous is False
        assert rows[0].ne_prediction == "bullish"
        assert rows[0].outcome is None  # not confirmed yet — "Awaiting confirmation"
    print("PASS\n")


def test_text_only_event_confirmed_outcome_judged_correctly():
    print("=== build_print_call_history: a confirmed outcome for a text-only event judges Confirmed/Missed correctly ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 17, 18, 0, tzinfo=UTC_TZ)
        now = event_time + dt.timedelta(hours=1)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("FOMC Statement", event_time, None, None, None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", event_time,
            0.62, "bullish", 0.5, 40, False, scored_at_utc=event_time,
        )
        backtest_store.record_outcome(bt_conn, "FOMC Statement", "XAUUSD", event_time, "bearish", "gold sold off on hawkish tone")
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert rows[0].outcome == "Missed"  # predicted bullish, actual was bearish
    print("PASS\n")


def test_text_only_event_missing_prediction_for_one_instrument_produces_no_row_for_it():
    print("=== build_print_call_history: an instrument with no prediction for a text-only occurrence gets no row ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        event_time = dt.datetime(2026, 9, 17, 18, 0, tzinfo=UTC_TZ)
        now = event_time + dt.timedelta(hours=1)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("FOMC Statement", event_time, None, None, None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", event_time,
            0.62, "bullish", 0.5, 40, False, scored_at_utc=event_time,
        )
        # No prediction recorded for US30 for this occurrence.
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert len(rows) == 1
        assert rows[0].instrument == "XAUUSD"
    print("PASS\n")


def test_future_text_only_event_excluded():
    print("=== build_print_call_history: a text-only event that hasn't happened yet is excluded, even with a prediction ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        now = dt.datetime(2026, 9, 1, 12, 0, tzinfo=UTC_TZ)
        future_event_time = now + dt.timedelta(hours=48)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("FOMC Statement", future_event_time, None, None, None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "FOMC Statement", "XAUUSD", future_event_time,
            0.62, "bullish", 0.5, 40, False, scored_at_utc=now,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert rows == []
    print("PASS\n")


def test_partially_numeric_event_not_misclassified_as_text_only():
    print("=== build_print_call_history: an event with a forecast but no actual yet is NOT treated as text-only ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_db = Path(tmp) / "dashboard.db"
        backtest_db = Path(tmp) / "backtest.db"
        now = dt.datetime(2026, 9, 1, 12, 0, tzinfo=UTC_TZ)
        event_time = now - dt.timedelta(hours=2)

        dash_conn = store.get_connection(dash_db)
        store.upsert_event_history(
            dash_conn, _resolved_event("Advance GDP q/q", event_time, "2.1%", "2.0%", None),
            None, now=now,
        )
        dash_conn.close()

        bt_conn = backtest_store.get_connection(backtest_db)
        backtest_store.record_prediction(
            bt_conn, "Advance GDP q/q", "XAUUSD", event_time,
            0.55, "bullish", 0.4, 30, False, scored_at_utc=now,
        )
        bt_conn.close()

        with patch.object(store, "DB_PATH", dash_db), patch.object(backtest_store, "DB_PATH", backtest_db):
            rows = history.build_print_call_history(now=now)

        assert rows == []  # not resolved numerically (no actual), and NOT text-only (has a forecast)
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
            rows = history.build_print_call_history()

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
    test_unresolved_numeric_event_excluded_entirely()
    test_resolved_numeric_event_with_no_print_call_excluded_entirely()
    test_unchanged_vs_previous_badge_does_not_affect_outcome()
    test_text_only_event_with_prediction_produces_fallback_row()
    test_text_only_event_confirmed_outcome_judged_correctly()
    test_text_only_event_missing_prediction_for_one_instrument_produces_no_row_for_it()
    test_future_text_only_event_excluded()
    test_partially_numeric_event_not_misclassified_as_text_only()
    test_cross_pipeline_read_failure_fails_open_to_empty_list()
    test_empty_result_when_nothing_resolved()
    print("All webapp_history tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_history.py`
Expected: `ModuleNotFoundError: No module named 'webapp.history'`

- [ ] **Step 3: Implement `webapp/history.py`**

```python
"""
Read-only cross-pipeline join for the dashboard's History tab —
webapp.store's event_history (resolved occurrences, this dashboard's own
DB) joined with scoring.backtest_store's print_predictions (numeric
events) or predictions+outcomes (text-only events with no forecast at
all, e.g. FOMC Statement), producing a Confirmed/Missed track record.

Mirrors the read-only cross-pipeline pattern already established twice in
this codebase: webapp/app.py reads scoring.backtest_store's DB read-only
for the print-call badge; scoring/backtest_accumulator.py reads
webapp.store's DB read-only for the trend signal. This module is the
third instance, dashboard-side, display-only — it writes nothing to
either DB.

Not every High-impact USD event has a number to compare against — FOMC
Statement/Press Conference publish no forecast/actual at all, but the
accumulator's article-based sentiment call (predictions table) already
scores them regardless (score_bundle()'s core article-sentiment path
requires no numeric forecast — only the additional structured
contributions like the print-direction lexicon do). Those events get a
separate row per instrument using that regular sentiment call instead of
a numeric surprise comparison.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from config.settings import INSTRUMENTS
from scoring.print_direction import NO_HIT_CONFIDENCE
from webapp.store import get_connection, get_resolved_event_history, get_text_only_resolved_events

DEFAULT_HISTORY_LIMIT = 50


@dataclass
class HistoryRow:
    event_title: str
    event_time_utc: str
    instrument: Optional[str]       # None for numeric rows; 'XAUUSD'/'US30' for text-event fallback rows
    previous: Optional[str]
    forecast: Optional[str]
    actual: Optional[str]
    unchanged_vs_previous: bool
    ne_prediction: str
    ne_confidence: float
    outcome: Optional[str]          # 'Confirmed' | 'Missed' | None


def build_print_call_history(limit: int = DEFAULT_HISTORY_LIMIT, now: Optional[dt.datetime] = None) -> list[HistoryRow]:
    """
    Only resolved event_history occurrences (actual IS NOT NULL) WITH a
    matching print_predictions row appear as numeric rows — either
    condition missing means the occurrence is skipped entirely. Text-only
    occurrences (forecast AND actual both NULL) with a real predictions
    row appear as one fallback row per instrument. Fails open to an empty
    list if the backtest DB is unreachable for any reason — never crashes
    the /api/history route over a cross-pipeline read error.
    """
    now = now or dt.datetime.now(dt.timezone.utc)

    # Imported here, not at module level, to avoid a hard import-time
    # dependency cycle risk between webapp and scoring — matches the
    # existing lazy-import style already used for cross-pipeline reads in
    # scoring/backtest_accumulator.py's _read_trend_signal().
    from scoring.backtest_store import (
        get_connection as get_backtest_connection,
        get_latest_print_prediction,
        get_latest_prediction_for_occurrence,
        get_outcome,
    )

    dash_conn = get_connection()
    try:
        numeric_resolved = get_resolved_event_history(dash_conn, limit=limit)
        text_only_resolved = get_text_only_resolved_events(dash_conn, now=now, limit=limit)
    finally:
        dash_conn.close()

    if not numeric_resolved and not text_only_resolved:
        return []

    try:
        bt_conn = get_backtest_connection()
    except Exception as exc:  # noqa: BLE001 — an unreachable backtest DB must not crash the route
        print(f"[webapp.history] WARNING: could not read backtest data: {exc}")
        return []

    rows: list[HistoryRow] = []
    try:
        for event in numeric_resolved:
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
                instrument=None,
                previous=event.previous,
                forecast=event.forecast,
                actual=event.actual,
                unchanged_vs_previous=(event.actual == event.previous),
                ne_prediction=call.predicted_vs_forecast,
                ne_confidence=call.confidence,
                outcome=outcome,
            ))

        for event in text_only_resolved:
            event_time = dt.datetime.fromisoformat(event.event_time_utc)
            for instrument in INSTRUMENTS.keys():
                try:
                    prediction = get_latest_prediction_for_occurrence(bt_conn, event.event_title, instrument, event_time)
                except Exception as exc:  # noqa: BLE001 — one bad lookup must not crash the whole build
                    print(f"[webapp.history] WARNING: could not read prediction for {event.event_title}/{instrument}: {exc}")
                    continue
                if prediction is None:
                    continue  # no real call for this instrument at this occurrence — no row, not shown with blanks

                try:
                    outcome_row = get_outcome(bt_conn, event.event_title, instrument, event_time)
                except Exception as exc:  # noqa: BLE001
                    print(f"[webapp.history] WARNING: could not read outcome for {event.event_title}/{instrument}: {exc}")
                    outcome_row = None

                text_outcome: Optional[str] = None
                if outcome_row is not None:
                    text_outcome = "Confirmed" if outcome_row.actual_direction == prediction.direction else "Missed"

                rows.append(HistoryRow(
                    event_title=event.event_title,
                    event_time_utc=event.event_time_utc,
                    instrument=instrument,
                    previous=None,
                    forecast=None,
                    actual=None,
                    unchanged_vs_previous=False,
                    ne_prediction=prediction.direction,
                    ne_confidence=prediction.confidence,
                    outcome=text_outcome,
                ))
    finally:
        bt_conn.close()

    rows.sort(key=lambda r: r.event_time_utc, reverse=True)
    return rows[:limit]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_history.py`
Expected: all 12 tests PASS.

- [ ] **Step 5: Run the regression sweep**

```bash
python tests/test_webapp_store.py
python tests/test_webapp_history.py
python tests/test_backtest_store.py
```

Expected: all PASS, no regressions.

- [ ] **Step 6: Commit**

```bash
git add webapp/history.py tests/test_webapp_history.py
git commit -m "feat: add webapp/history.py — print-call + text-event track record join

build_print_call_history() merges two independent row sources:
numeric events (event_history joined with the latest print_predictions
call per occurrence, Confirmed/Missed via exact predicted_vs_forecast/
surprise_direction equality, shrug calls at/below NO_HIT_CONFIDENCE
shown but excluded from judging) and text-only events with no
forecast/actual at all (FOMC Statement, Press Conference — one row per
instrument using the regular predictions-table sentiment call,
Confirmed/Missed against the outcomes table, 'Awaiting confirmation'
when unconfirmed).

Read-only cross-pipeline read of the accumulator's DB, mirroring the
two existing precedents (webapp/app.py's print-call badge,
scoring/backtest_accumulator.py's trend-signal read) — fails open to
an empty list on any read error."
```

---

### Task 4: `GET /api/history` route

**Files:**
- Modify: `webapp/app.py`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `build_print_call_history()` (Task 3, `webapp.history`).
- Produces: no new interface — this is a thin route wrapping Task 3's function.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_webapp_app.py`, before its `__main__` block:

```python
def test_history_endpoint_returns_numeric_and_text_rows():
    print("=== app: /api/history returns build_print_call_history()'s rows as JSON, including the instrument field ===")
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
            assert data["rows"][0]["instrument"] is None
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
                "instrument": r.instrument,
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
git commit -m "feat: add GET /api/history route serving the print-call + text-event track record

Thin wrapper over webapp.history.build_print_call_history() — no
logic of its own beyond JSON serialization, including the new
instrument field. Empty case returns 200 with an empty rows list,
never a 500."
```

---

### Task 5: History tab UI

**Files:**
- Modify: `webapp/static/index.html` (new tab button + view section)
- Modify: `webapp/static/app.js` (render function, fetch-on-first-select, `showView` update)
- Modify: `webapp/static/style.css` (minimal table styling)

**Interfaces:**
- Consumes: `GET /api/history` (Task 4's route, response shape
  `{rows: [{event_title, event_time_utc, instrument, previous, forecast,
  actual, unchanged_vs_previous, ne_prediction, ne_confidence, outcome}]}`).
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
      <tr><th>Event</th><th>Instr.</th><th>Previous</th><th>Forecast</th><th>Actual</th><th>NE Prediction</th><th>Outcome</th></tr>
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
    // Numeric rows use higher/lower/in_line; text-event fallback rows use bullish/bearish/neutral.
    const predictionLabel = { higher: "Higher", lower: "Lower", in_line: "In-line", bullish: "Bullish", bearish: "Bearish", neutral: "Neutral" }[r.ne_prediction] || escapeHtml(r.ne_prediction);
    const outcomeLabel = r.outcome === null
      ? `<span style="color:#888">${r.instrument ? "Awaiting confirmation" : "No strong call"}</span>`
      : r.outcome === "Confirmed"
        ? '<span style="color:#2e7d32;font-weight:bold">Confirmed</span>'
        : '<span style="color:#c62828;font-weight:bold">Missed</span>';
    return `<tr>
      <td>${escapeHtml(r.event_title)}<br><span style="font-size:11px;color:#888">${dateLabel}</span></td>
      <td>${escapeHtml(r.instrument ?? "")}</td>
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
- If any row IS present, confirm: numeric rows show a blank Instr.
  column and the `(= prev)` badge when applicable; if a text-only event
  (e.g. FOMC) has resolved with a real prediction, it shows its
  instrument, blank Previous/Forecast/Actual, and "Awaiting
  confirmation"/Confirmed/Missed appropriately in Outcome.

- [ ] **Step 6: Commit**

```bash
git add webapp/static/index.html webapp/static/app.js webapp/static/style.css
git commit -m "feat: add History tab UI for the print-call + text-event track record

Third tab (Dashboard/Calendar/History), table fetched once on first
selection via /api/history, not on the dashboard's 60s poll cycle.
Shows Instrument/Previous/Forecast/Actual/NE Prediction/Outcome per
resolved occurrence — numeric events leave Instrument blank (the call
is symbol-agnostic), text-only events (FOMC etc.) populate it (the
call IS instrument-specific) and leave Previous/Forecast/Actual blank.
A (= prev) badge marks unchanged-vs-previous numeric rows (display-only,
per the design's research finding). Empty state shown explicitly when
nothing has resolved yet. Verified live via run_all.py — no JS test
harness exists in this codebase."
```

---

### Task 6: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a new subsection**

Find the "### Trend-history feed-back into scoring" subsection via `grep
-n "Trend-history feed-back" README.md`, and insert this new subsection
immediately after it, before the next `##`/`###` heading:

```markdown
### History tab

A third dashboard tab ("History", alongside Dashboard/Calendar) shows a
consolidated, reviewable record of the engine's calls against what
actually happened — `webapp/history.py`'s `build_print_call_history()`
merges two independent row sources:

- **Numeric events** (CPI, PPI, NFP, etc.) — `webapp/store.py`'s
  `event_history` (resolved occurrences: Previous/Forecast/Actual) joined
  with `scoring/backtest_store.py`'s `print_predictions` (the latest call
  per occurrence), Confirmed/Missed via exact
  `predicted_vs_forecast`/`surprise_direction` equality. A call at or
  below `NO_HIT_CONFIDENCE` (0.15) is shown but excluded from judging
  ("No strong call").
- **Text-only events** (FOMC Statement, Press Conference, and anything
  else with no forecast/actual figure at all — a data-driven distinction,
  `forecast IS NULL AND actual IS NULL` in `event_history`, not a
  lexicon-coverage check) — one row per instrument using the
  accumulator's regular article-based sentiment call
  (`scoring/backtest_store.py`'s `predictions` table), Confirmed/Missed
  against a real confirmed `outcomes` row if one exists, "Awaiting
  confirmation" otherwise (outcome confirmation is a manual/`--auto` step
  in this system, never automatic).

Only occurrences **with** a real call appear in either case — neither
condition alone. A `(= prev)` badge marks numeric occurrences where
`actual` exactly matches `previous` — display-only context (real pattern
for inflation-type indicators specifically, per research done during this
feature's design; never fed into scoring or the Confirmed/Missed
judgment — see
`docs/superpowers/specs/2026-08-12-history-tab-design.md`).

Same read-only cross-pipeline pattern as the print-call badge and trend
signal before it: opens a connection to the accumulator's DB, never
writes to it, fails open to an empty result on any read error.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document the History tab (print-call + text-event track record)"
```

---

## Post-plan verification (do this after all 6 tasks are complete)

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
