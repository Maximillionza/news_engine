# Historical Backfill + Dashboard/Calendar UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backfill real historical event/prediction/outcome data for Jan 1 – Aug 9, 2026 (real data only, never reconstructed), and fix the dashboard's layer-gating bug while surfacing what the engine already computes but never shows (trend streak, print call, Kalshi read) plus a genuinely interactive, color-coded Calendar tab.

**Architecture:** Part 1 adds a `source` column (`'live'`/`'seeded'`) to four tables across both DBs, plus a one-off script that writes real researched event facts and — only where genuinely retrievable — real article-based predictions (via the actual `score_bundle()` against real historical Alpha Vantage articles) and real price outcomes (via the actual `outcome_classifier` against real historical Dukascopy prices). Part 2 fixes `/api/predictions`'s layer-gating bug, adds two already-existing-but-unexposed signals (trend streak, Kalshi read) to its response, and gives the Calendar tab impact color-coding plus click-to-inspect.

**Tech Stack:** Python 3.14, Flask, vanilla JS (no framework), SQLite. No new dependencies — reuses `data_layer.news_feed.AlphaVantageNewsSource`, `scoring.outcome_classifier.classify()`, `webapp.trend.compute_trend_signal()`, `scoring.backtest_store.get_latest_kalshi_read()` — all already exist.

## Global Constraints

- **Real data or absent, never reconstructed.** Event facts (forecast/previous/actual) are researched and cited (WebSearch), matching `tests/run_historical_backtest.py`'s existing standard. Article predictions and price outcomes are recorded ONLY when the actual live functions (`build_event_news_bundle()` + `score_bundle()`, `outcome_classifier.classify()`) return real, non-empty, genuinely-dated data — no fallback, no approximation, no confidence cap standing in for a guess.
- Backfill date range: **2026-01-01T00:00:00Z through 2026-08-09T23:49:59Z** (exclusive of the live system's earliest real row, confirmed at spec time as `2026-08-09T23:50:00+00:00`).
- `source` defaults to `'live'` on every affected function — every existing call site must remain unaffected, verified by running the existing test suite unchanged before adding new tests.
- Alpha Vantage free tier is 25 requests/day (`data_layer/news_feed.py`'s `AlphaVantageNewsSource` docstring) — the seed script must be resumable/rate-limit-aware, never assume it completes in one run.
- No changes to `scoring/probability_engine.py`'s scoring math anywhere in this plan — Part 2 only surfaces data that's already computed and already persisted elsewhere; Part 1 only ever calls existing scoring/classification functions unmodified.
- No Kalshi historical backfill (no genuine retrieval path exists — real-money market prices from the past cannot be reconstructed).

---

### Task 1: `source` column + param — `webapp/store.py`

**Files:**
- Modify: `webapp/store.py`
- Test: `tests/test_webapp_store.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `upsert_event_history(conn, event, surprise_direction, now, source='live')` (new optional param); `EventHistoryRow` gains a `source: str` field; `get_connection()` migrates existing DBs. Task 3's calendar-side write and Task 5's badge both depend on this.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_webapp_store.py` (check current imports first — this file already has `get_connection`, `upsert_event_history`, `get_event_history`, a fake `EconomicEvent`-shaped test helper):

```python
def test_upsert_event_history_defaults_to_live_source():
    print("=== webapp/store: upsert_event_history defaults source='live' when not passed ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event = _fake_event(title="CPI m/m", event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ))
        store.upsert_event_history(conn, event, "higher_bullish", dt.datetime(2026, 8, 12, 13, 0, tzinfo=UTC_TZ))
        rows = store.get_event_history(conn, "CPI m/m")
        assert rows[0].source == "live"
        conn.close()
    print("PASS\n")


def test_upsert_event_history_accepts_explicit_seeded_source():
    print("=== webapp/store: upsert_event_history(source='seeded') is stored and read back ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event = _fake_event(title="CPI m/m", event_time_utc=dt.datetime(2026, 1, 13, 12, 30, tzinfo=UTC_TZ))
        store.upsert_event_history(conn, event, "higher_bullish", dt.datetime(2026, 1, 13, 13, 0, tzinfo=UTC_TZ), source="seeded")
        rows = store.get_event_history(conn, "CPI m/m")
        assert rows[0].source == "seeded"
        conn.close()
    print("PASS\n")


def test_get_connection_migrates_preexisting_db_missing_source_column():
    print("=== webapp/store: get_connection() adds the source column to a pre-existing DB file that predates it ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        # Simulate a pre-migration DB: create event_history WITHOUT the source column.
        raw_conn = sqlite3.connect(db_path)
        raw_conn.execute("""
            CREATE TABLE event_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_title TEXT NOT NULL,
                event_time_utc TEXT NOT NULL,
                forecast TEXT, previous TEXT, actual TEXT, surprise_direction TEXT,
                recorded_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL,
                UNIQUE(event_title, event_time_utc)
            )
        """)
        raw_conn.execute(
            "INSERT INTO event_history (event_title, event_time_utc, recorded_at_utc, updated_at_utc) "
            "VALUES ('Old Event', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')"
        )
        raw_conn.commit()
        raw_conn.close()

        conn = store.get_connection(db_path)  # must not raise, must add the column
        rows = store.get_event_history(conn, "Old Event")
        assert rows[0].source == "live"  # pre-existing row backfilled to 'live' via the column's DEFAULT
        conn.close()
    print("PASS\n")


def test_get_connection_fresh_db_has_source_column_no_error():
    print("=== webapp/store: get_connection() on a brand-new DB (source already in CREATE TABLE) does not error on the migration step ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)  # fresh DB, schema already has source — migration must be a safe no-op
        conn2 = store.get_connection(db_path)  # second open — must also be a safe no-op
        conn.close()
        conn2.close()
    print("PASS\n")
```

Register all 4 in `__main__`. Ensure `import sqlite3` is present at the top of the test file (check first).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_store.py`
Expected: `TypeError: upsert_event_history() got an unexpected keyword argument 'source'` (and `AttributeError: 'EventHistoryRow' object has no attribute 'source'`).

- [ ] **Step 3: Add the column, migration, and param**

In `webapp/store.py`, add `source TEXT NOT NULL DEFAULT 'live'` to `event_history`'s `CREATE TABLE` block in `_SCHEMA`:

```python
CREATE TABLE IF NOT EXISTS event_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    forecast TEXT,
    previous TEXT,
    actual TEXT,
    surprise_direction TEXT,
    recorded_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'live',
    UNIQUE(event_title, event_time_utc)
);
```

Add a migration helper (near `get_connection()`):

```python
def _migrate_add_source_column(conn: sqlite3.Connection) -> None:
    """
    CREATE TABLE IF NOT EXISTS does not retroactively add a column to an
    already-created DB file — every DB created before this change lacks
    `source` on event_history. Adds it, defaulting existing (pre-backfill)
    rows to 'live' (their implicit meaning before this column existed).
    Safe to call on a fresh DB where the column already exists via
    CREATE TABLE — PRAGMA table_info is checked first, not a bare ALTER
    wrapped in try/except, so a genuine unrelated OperationalError isn't
    silently swallowed.
    """
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(event_history)").fetchall()}
    if "source" not in existing_columns:
        conn.execute("ALTER TABLE event_history ADD COLUMN source TEXT NOT NULL DEFAULT 'live'")
        conn.commit()
```

Modify `get_connection()` to call it after `executescript(_SCHEMA)` (read the current function body first to insert at the right point — do not guess at line numbers):

```python
def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _migrate_add_source_column(conn)
    return conn
```

Update `EventHistoryRow`:

```python
@dataclass
class EventHistoryRow:
    event_title: str
    event_time_utc: str
    forecast: Optional[str]
    previous: Optional[str]
    actual: Optional[str]
    surprise_direction: Optional[str]
    source: str
```

Update `upsert_event_history()`'s signature and INSERT:

```python
def upsert_event_history(
    conn: sqlite3.Connection,
    event,
    surprise_direction: Optional[str],
    now: dt.datetime,
    source: str = "live",
) -> None:
    conn.execute(
        """
        INSERT INTO event_history
            (event_title, event_time_utc, forecast, previous, actual, surprise_direction, recorded_at_utc, updated_at_utc, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_title, event_time_utc) DO UPDATE SET
            actual = excluded.actual,
            surprise_direction = excluded.surprise_direction,
            updated_at_utc = excluded.updated_at_utc
        WHERE excluded.actual IS NOT NULL
        """,
        (
            event.title, event.event_time_utc.isoformat(), event.forecast, event.previous,
            event.actual, surprise_direction, now.isoformat(), now.isoformat(), source,
        ),
    )
    conn.commit()
```

(`source` is intentionally NOT part of the `ON CONFLICT DO UPDATE SET` clause — a row's provenance is fixed at first insert and never flips; a later live re-fetch touching a seeded occurrence updates `actual`/`surprise_direction` per the existing guard but must not silently relabel a seeded row as live, which would misrepresent how the ORIGINAL forecast/previous were captured.)

Every `SELECT` that constructs an `EventHistoryRow` (`get_event_history()`, `get_resolved_event_history()`, `get_text_only_resolved_events()`) must add `source` to its column list — grep `webapp/store.py` for `EventHistoryRow(**dict(row))` or explicit field lists and update each `SELECT` to include `source`. Read each function before editing.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_store.py`
Expected: all tests PASS, including the 4 new ones.

- [ ] **Step 5: Run the full existing regression suite for this file**

Run: `python tests/test_webapp_app.py` (this file's routes construct `EventHistoryRow`-derived JSON — confirm nothing broke)
Expected: all existing tests PASS unchanged.

- [ ] **Step 6: Commit**

```bash
git add webapp/store.py tests/test_webapp_store.py
git commit -m "feat: add source column + migration to event_history

New source TEXT NOT NULL DEFAULT 'live' column on event_history,
threaded through upsert_event_history() as an optional param
(defaults to 'live', every existing call site unaffected). A
migration helper adds the column to pre-existing DB files (CREATE
TABLE IF NOT EXISTS doesn't retroactively add columns), guarded by
PRAGMA table_info so a genuine unrelated schema error isn't silently
swallowed. source is deliberately excluded from the upsert's ON
CONFLICT UPDATE clause — provenance is fixed at first insert, never
flipped by a later touch."
```

---

### Task 2: `source` column + param — `scoring/backtest_store.py`

**Files:**
- Modify: `scoring/backtest_store.py`
- Test: `tests/test_backtest_store.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `record_prediction(..., source='live')`, `record_print_prediction_if_changed(..., source='live')`, `record_outcome(..., source='live')` (all new optional params); `Prediction`/`PrintPrediction`/`Outcome` dataclasses gain `source: str`. Task 3 passes `source='seeded'` to all three.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_backtest_store.py` (mirror the exact style of Task 1's tests, adapted to this file's existing helpers — check current imports/fixtures first):

```python
def test_record_prediction_defaults_to_live_source():
    print("=== backtest_store: record_prediction defaults source='live' ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        store.record_prediction(conn, "CPI m/m", "XAUUSD", event_time, 0.7, "bullish", 0.6, 3, False)
        rows = conn.execute("SELECT source FROM predictions ORDER BY id DESC LIMIT 1").fetchall()
        assert rows[0]["source"] == "live"
        conn.close()
    print("PASS\n")


def test_record_prediction_accepts_explicit_seeded_source():
    print("=== backtest_store: record_prediction(source='seeded') round-trips ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 1, 13, 12, 30, tzinfo=UTC_TZ)
        store.record_prediction(conn, "CPI m/m", "XAUUSD", event_time, 0.7, "bullish", 0.6, 5, False, source="seeded")
        rows = conn.execute("SELECT source FROM predictions ORDER BY id DESC LIMIT 1").fetchall()
        assert rows[0]["source"] == "seeded"
        conn.close()
    print("PASS\n")


def test_record_print_prediction_if_changed_source_param():
    print("=== backtest_store: record_print_prediction_if_changed accepts and stores source ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 1, 13, 12, 30, tzinfo=UTC_TZ)
        store.record_print_prediction_if_changed(conn, "CPI m/m", event_time, "higher", 0.5, 3, now=event_time, source="seeded")
        rows = conn.execute("SELECT source FROM print_predictions ORDER BY id DESC LIMIT 1").fetchall()
        assert rows[0]["source"] == "seeded"
        conn.close()
    print("PASS\n")


def test_record_outcome_source_param():
    print("=== backtest_store: record_outcome accepts and stores source ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 1, 13, 12, 30, tzinfo=UTC_TZ)
        store.record_outcome(conn, "CPI m/m", "XAUUSD", event_time, "bullish", "Dukascopy: +0.30% in 30min (auto)", source="seeded")
        rows = conn.execute("SELECT source FROM outcomes ORDER BY id DESC LIMIT 1").fetchall()
        assert rows[0]["source"] == "seeded"
        conn.close()
    print("PASS\n")


def test_get_connection_migrates_all_four_source_columns():
    print("=== backtest_store: get_connection() adds source to predictions/print_predictions/outcomes on a pre-existing DB ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        raw_conn = sqlite3.connect(db_path)
        raw_conn.execute("""
            CREATE TABLE predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, event_title TEXT NOT NULL, instrument TEXT NOT NULL,
                event_time_utc TEXT NOT NULL, scored_at_utc TEXT NOT NULL, probability REAL NOT NULL,
                direction TEXT NOT NULL, confidence REAL NOT NULL, article_count INTEGER NOT NULL,
                contradiction_flag INTEGER NOT NULL
            )
        """)
        raw_conn.commit()
        raw_conn.close()

        conn = store.get_connection(db_path)  # must not raise, must add source to predictions
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(predictions)").fetchall()}
        assert "source" in cols
        conn.close()
    print("PASS\n")
```

Register all 5 in `__main__`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_backtest_store.py`
Expected: `TypeError` on the new `source` kwargs.

- [ ] **Step 3: Add columns, migration, and params**

Add `source TEXT NOT NULL DEFAULT 'live'` to `predictions`, `print_predictions`, and `outcomes` in `_SCHEMA` (leave `dismissals`, `check_log`, `kalshi_reads` untouched — out of scope, Kalshi has no backfill).

Add a migration helper (same pattern as Task 1, one table list):

```python
def _migrate_add_source_columns(conn: sqlite3.Connection) -> None:
    """
    Same reasoning as webapp/store.py's _migrate_add_source_column() —
    CREATE TABLE IF NOT EXISTS doesn't retroactively add a column.
    Covers predictions, print_predictions, and outcomes (NOT
    dismissals/check_log/kalshi_reads — no seeded rows are ever written
    to those).
    """
    for table in ("predictions", "print_predictions", "outcomes"):
        existing_columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if "source" not in existing_columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN source TEXT NOT NULL DEFAULT 'live'")
    conn.commit()
```

Call it from `get_connection()` after `executescript(_SCHEMA)`, same placement pattern as Task 1.

Update `Prediction`, `PrintPrediction`, `Outcome` dataclasses to add `source: str`. Update every `SELECT`/row-construction site for these three (grep the file for each dataclass's construction — `Prediction(`, `PrintPrediction(`, `Outcome(` — and add `source` to each).

Update `record_prediction()`:

```python
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
    source: str = "live",
) -> int:
    scored_at = scored_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO predictions (event_title, instrument, event_time_utc, scored_at_utc, "
        "probability, direction, confidence, article_count, contradiction_flag, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), scored_at.isoformat(),
         probability, direction, confidence, article_count, int(contradiction_flag), source),
    )
    conn.commit()
    return cursor.lastrowid
```

Update `record_outcome()` — add `source: str = "live"` param, add `source` to the INSERT column list and VALUES tuple (read the current function first — shown in context above, in the "Interfaces" background).

Update `record_print_prediction_if_changed()` — add `source: str = "live"` param, thread into its INSERT. Read the function's current body first (it has diff-aware "only write if changed" logic — do not alter that logic, only add the new column/param).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_backtest_store.py`
Expected: all tests PASS, including the 5 new ones.

- [ ] **Step 5: Run the full existing regression suite**

Run: `python tests/test_backtest_accumulator.py`, `python tests/test_probability_engine.py`
Expected: all PASS unchanged (both call the Task-2-modified functions without `source`, proving the default is safe).

- [ ] **Step 6: Commit**

```bash
git add scoring/backtest_store.py tests/test_backtest_store.py
git commit -m "feat: add source column + migration to predictions/print_predictions/outcomes

Same pattern as webapp/store.py's event_history migration:
source TEXT NOT NULL DEFAULT 'live' on all three tables, threaded as
an optional param through record_prediction(),
record_print_prediction_if_changed(), and record_outcome() — every
existing call site unaffected. dismissals/check_log/kalshi_reads are
untouched (no seeded rows are ever written to those)."
```

---

### Task 3: `scripts/seed_historical_data.py` — mechanism + proof-of-real-data run

**Files:**
- Create: `scripts/seed_historical_data.py`
- Create: `data_layer/historical_events.py` (the hand-authored event-fact list — separate file, since it will grow large and has one clear responsibility: real, cited historical data, not logic)
- Test: `tests/test_seed_historical_data.py`

**Interfaces:**
- Consumes: `webapp.store.upsert_event_history(..., source=)` (Task 1); `scoring.backtest_store.record_prediction/record_print_prediction_if_changed/record_outcome(..., source=)` (Task 2); `data_layer.event_context.build_event_news_bundle()`, `data_layer.news_feed.AlphaVantageNewsSource`, `scoring.probability_engine.score_bundle()`, `scoring.outcome_classifier.classify()`, `data_layer.calendar_feed.classify_surprise()`, `data_layer.calendar_feed.EconomicEvent` — all existing, unmodified.
- Produces: `data_layer.historical_events.HISTORICAL_EVENTS: list[HistoricalEventFact]` (the data Task 4 extends); `scripts/seed_historical_data.py`'s `run_seed(events, dashboard_conn, backtest_conn, instruments, now=None) -> SeedReport` — Task 4 invokes this script directly, doesn't need its internals.

- [ ] **Step 1: Define the data shape in `data_layer/historical_events.py`**

```python
"""
Hand-authored, cited historical event facts for the Jan 2026 -> live-start
backfill (2026-01-01T00:00:00Z through 2026-08-09T23:49:59Z — the live
system's earliest real captured row, confirmed at 2026-08-09T23:50:00+00:00).

Every forecast/previous/actual value here is REAL, researched history —
same citation standard as tests/run_historical_backtest.py's existing 14
cases (Reuters/CNBC/Kitco/BLS/TradingKey/etc.) — never simulated or
invented. See docs/superpowers/specs/2026-08-13-historical-backfill-and-ui-redesign-design.md
for the full provenance rules: this file is ONLY event facts (forecast/
previous/actual). Article-based predictions and price outcomes are never
hand-typed here — scripts/seed_historical_data.py attempts to derive
those from genuinely real, separately-fetched data (Alpha Vantage
articles, Dukascopy prices) at seed time, and records nothing for an
occurrence where that real data isn't retrievable.

Reuses tests/run_historical_backtest.py's already-researched cases where
their event_time_utc falls in this backfill's range (that file's docstring
says "2026 (Jan-Aug)" — several of its 14 cases are pre-live-start and are
copied here verbatim, sourced with the same citation each case already
carries).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from config.settings import UTC_TZ


@dataclass
class HistoricalEventFact:
    title: str                    # must exactly match a config.settings.EVENT_SURPRISE_DIRECTION key
    event_time_utc: dt.datetime
    forecast: str
    previous: str
    actual: str
    source_note: str              # citation — where this forecast/previous/actual was verified


# Populated by Task 4 — this file ships with a small real, verified seed
# set (proof the mechanism works end-to-end) and Task 4 extends it to
# cover the full Jan 1 - Aug 9 range.
HISTORICAL_EVENTS: list[HistoricalEventFact] = [
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 7, 2, 12, 30, tzinfo=UTC_TZ),
        forecast="~113K", previous="139K", actual="57K",
        source_note="June NFP, released Jul 2 2026 — actual +57K vs ~113K expected, "
                     "gold jumped above $4,100 on the miss (reused from "
                     "tests/run_historical_backtest.py case e2).",
    ),
    HistoricalEventFact(
        title="Non-Farm Employment Change",
        event_time_utc=dt.datetime(2026, 6, 5, 12, 30, tzinfo=UTC_TZ),
        forecast="TBD_RESEARCH", previous="TBD_RESEARCH", actual="TBD_RESEARCH",
        source_note="May NFP, released Jun 5 2026 — placeholder, verify against "
                     "tests/run_historical_backtest.py case e3 and correct before Task 4 runs.",
    ),
]
```

**Note to implementer:** the two example entries above are a STARTING POINT, not final — the first one's numbers are real (verify them independently before trusting them verbatim; they're transcribed from this plan's own research into `tests/run_historical_backtest.py`, not re-verified live). The second is intentionally marked `"TBD_RESEARCH"` to prove the test suite correctly rejects placeholder data (Step 2 below) — replace both with independently-verified facts (or delete the placeholder one) before this task's tests are expected to fully pass. Task 4 is where the full 7-month dataset gets built; this task only needs 2-3 real, working entries to prove the pipeline.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_seed_historical_data.py`:

```python
"""
Tests for scripts/seed_historical_data.py — no live network calls.
AlphaVantageNewsSource and outcome_classifier.classify are both mocked;
this proves the SEEDING MECHANISM (real functions called with real
data-shaped inputs, source='seeded' threaded through, absent-not-
fabricated on empty results) without depending on live API availability.
"""
import sys
import os
import datetime as dt
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
import webapp.store as dash_store
import scoring.backtest_store as bt_store
from data_layer.historical_events import HistoricalEventFact
from data_layer.news_feed import NewsArticle
import scripts.seed_historical_data as seed


def _fact(title="CPI m/m", event_time_utc=None, actual="0.3%", forecast="0.2%", previous="0.1%"):
    return HistoricalEventFact(
        title=title,
        event_time_utc=event_time_utc or dt.datetime(2026, 1, 13, 12, 30, tzinfo=UTC_TZ),
        forecast=forecast, previous=previous, actual=actual,
        source_note="test fixture",
    )


def test_no_placeholder_facts_in_the_shipped_dataset():
    print("=== seed_historical_data: HISTORICAL_EVENTS ships with zero TBD_RESEARCH placeholders ===")
    from data_layer.historical_events import HISTORICAL_EVENTS
    placeholders = [f for f in HISTORICAL_EVENTS if "TBD_RESEARCH" in (f.forecast, f.previous, f.actual)]
    assert placeholders == [], f"Found {len(placeholders)} unresearched placeholder fact(s) — replace before shipping: {placeholders}"
    print("PASS\n")


def test_calendar_side_write_always_happens():
    print("=== seed_historical_data: the calendar-side event_history write always happens, regardless of article/outcome availability ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()

        with patch.object(seed, "_attempt_article_prediction", return_value=None), \
             patch.object(seed, "_attempt_outcome_confirmation", return_value=None):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        rows = dash_store.get_event_history(dash_conn, "CPI m/m")
        assert len(rows) == 1
        assert rows[0].source == "seeded"
        assert rows[0].actual == "0.3%"
        assert report.calendar_writes == 1
        assert report.predictions_written == 0
        assert report.outcomes_written == 0
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_real_article_result_produces_a_real_scored_prediction():
    print("=== seed_historical_data: a genuine (mocked-but-real-shaped) article result runs through the actual score_bundle() and writes a prediction ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()
        real_article = NewsArticle(
            title="CPI comes in hot, dollar surges", summary="Inflation beats forecast, hawkish Fed bets rise",
            source="Test Wire", source_type="rss_reuters_business",
            published_utc=fact.event_time_utc - dt.timedelta(hours=2),
            url="https://example.test/real-article",
        )

        with patch.object(seed, "_fetch_real_articles", return_value=[real_article]), \
             patch.object(seed, "_attempt_outcome_confirmation", return_value=None):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        preds = bt_conn.execute("SELECT * FROM predictions WHERE event_title = ?", ("CPI m/m",)).fetchall()
        assert len(preds) == 1
        assert preds[0]["source"] == "seeded"
        assert preds[0]["article_count"] == 1  # the real article, not fabricated
        assert report.predictions_written == 1
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_empty_article_result_writes_nothing_not_a_fallback():
    print("=== seed_historical_data: no real articles found -> zero predictions rows, no reconstruction fallback ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()

        with patch.object(seed, "_fetch_real_articles", return_value=[]), \
             patch.object(seed, "_attempt_outcome_confirmation", return_value=None):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        preds = bt_conn.execute("SELECT * FROM predictions WHERE event_title = ?", ("CPI m/m",)).fetchall()
        assert len(preds) == 0
        assert report.predictions_written == 0
        assert report.predictions_skipped == 1
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_real_outcome_classification_writes_outcome():
    print("=== seed_historical_data: a clear (mocked-but-real-shaped) Dukascopy classification writes a real outcome ===")
    from scoring.outcome_classifier import ClassificationResult
    from scoring.probability_engine import Direction
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()
        clear_result = ClassificationResult(direction=Direction.BULLISH, move_pct=0.35, note="Dukascopy: +0.35% in 30min (auto)")

        with patch.object(seed, "_fetch_real_articles", return_value=[]), \
             patch.object(seed, "_classify_outcome", return_value=clear_result):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        outcomes = bt_conn.execute("SELECT * FROM outcomes WHERE event_title = ?", ("CPI m/m",)).fetchall()
        assert len(outcomes) == 1
        assert outcomes[0]["source"] == "seeded"
        assert outcomes[0]["actual_direction"] == "bullish"
        assert report.outcomes_written == 1
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_ambiguous_outcome_writes_nothing():
    print("=== seed_historical_data: an ambiguous (mocked) Dukascopy classification writes no outcome row ===")
    from scoring.outcome_classifier import ClassificationResult
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()
        ambiguous_result = ClassificationResult(direction=None, move_pct=0.05, note="Dukascopy: +0.05% in 30min, below 0.15% threshold")

        with patch.object(seed, "_fetch_real_articles", return_value=[]), \
             patch.object(seed, "_classify_outcome", return_value=ambiguous_result):
            report = seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        outcomes = bt_conn.execute("SELECT * FROM outcomes WHERE event_title = ?", ("CPI m/m",)).fetchall()
        assert len(outcomes) == 0
        assert report.outcomes_written == 0
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


def test_idempotent_rerun_does_not_duplicate_predictions():
    print("=== seed_historical_data: running twice does not duplicate a seeded predictions row for the same occurrence ===")
    with tempfile.TemporaryDirectory() as tmp:
        dash_conn = dash_store.get_connection(Path(tmp) / "dash.db")
        bt_conn = bt_store.get_connection(Path(tmp) / "bt.db")
        fact = _fact()
        real_article = NewsArticle(
            title="CPI in line", summary="Steady inflation read", source="Test Wire", source_type="rss_reuters_business",
            published_utc=fact.event_time_utc - dt.timedelta(hours=2), url="https://example.test/idempotent",
        )

        with patch.object(seed, "_fetch_real_articles", return_value=[real_article]), \
             patch.object(seed, "_attempt_outcome_confirmation", return_value=None):
            seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))
            seed.run_seed([fact], dash_conn, bt_conn, ["XAUUSD"], now=fact.event_time_utc + dt.timedelta(hours=1))

        preds = bt_conn.execute("SELECT * FROM predictions WHERE event_title = ? AND instrument = ?", ("CPI m/m", "XAUUSD")).fetchall()
        assert len(preds) == 1  # not 2
        dash_conn.close()
        bt_conn.close()
    print("PASS\n")


if __name__ == "__main__":
    test_no_placeholder_facts_in_the_shipped_dataset()
    test_calendar_side_write_always_happens()
    test_real_article_result_produces_a_real_scored_prediction()
    test_empty_article_result_writes_nothing_not_a_fallback()
    test_real_outcome_classification_writes_outcome()
    test_ambiguous_outcome_writes_nothing()
    test_idempotent_rerun_does_not_duplicate_predictions()
    print("All seed_historical_data tests passed.")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python tests/test_seed_historical_data.py`
Expected: `ModuleNotFoundError: No module named 'scripts.seed_historical_data'` (and, once that's fixed on the next iteration, the placeholder test fails until the `"TBD_RESEARCH"` entry from Step 1 is replaced/removed).

- [ ] **Step 4: Implement `scripts/seed_historical_data.py`**

```python
"""
One-off historical backfill: writes real researched event facts, and —
only where genuinely retrievable — real article-based predictions and
real price outcomes. Never reconstructs, never approximates. See
docs/superpowers/specs/2026-08-13-historical-backfill-and-ui-redesign-design.md.

Run: python scripts/seed_historical_data.py [--dry-run]

Idempotent: safe to re-run (e.g. across multiple days, respecting Alpha
Vantage's 25-req/day free-tier cap) — a seeded predictions/outcomes row
is only written once per (event_title, instrument, event_time_utc).
"""
from __future__ import annotations

import sys
import os
import datetime as dt
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import INSTRUMENTS, UTC_TZ, EVENT_SURPRISE_DIRECTION
from data_layer.calendar_feed import EconomicEvent, classify_surprise
from data_layer.historical_events import HISTORICAL_EVENTS, HistoricalEventFact
from data_layer.event_context import build_event_news_bundle
from data_layer.news_feed import AlphaVantageNewsSource, NewsArticle
import webapp.store as dash_store
import scoring.backtest_store as bt_store
from scoring.probability_engine import score_bundle


@dataclass
class SeedReport:
    calendar_writes: int = 0
    predictions_written: int = 0
    predictions_skipped: int = 0
    outcomes_written: int = 0
    outcomes_skipped: int = 0
    skip_reasons: list[str] = field(default_factory=list)


def _fetch_real_articles(event: EconomicEvent) -> list[NewsArticle]:
    """
    Attempts a genuine historical article pull via Alpha Vantage's
    NEWS_SENTIMENT endpoint (the only source in this codebase whose
    since_utc/time_from param genuinely queries the past — RSS sources
    are real-time-only, no archive). Returns [] — never fabricated — on
    any failure (API error, empty result, retention window exceeded).
    Reuses the EXACT same bundle-construction path the live accumulator
    uses (mode='backtest', cutoff at the event's own time — no future
    leak), just with AlphaVantageNewsSource as the only source.
    """
    try:
        bundle = build_event_news_bundle(
            event, sources=[AlphaVantageNewsSource()], query="",
            mode="backtest", backtest_cutoff_utc=event.event_time_utc,
        )
        return bundle.articles
    except Exception as exc:  # noqa: BLE001 — any fetch/config failure degrades to "no real articles", never a fabricated fallback
        print(f"[seed_historical_data] No real articles for {event.title} at {event.event_time_utc.isoformat()}: {exc}")
        return []


def _attempt_article_prediction(event: EconomicEvent, instrument: str, articles: list[NewsArticle]):
    """
    Runs the ACTUAL score_bundle() against genuinely-retrieved articles —
    never a hand-typed reconstruction. Returns None if there were no real
    articles (nothing to score) or if score_bundle() itself found nothing
    scoreable (e.g. all articles too far from the event to carry weight).
    """
    if not articles:
        return None
    bundle_as_of = event.event_time_utc
    from data_layer.event_context import EventNewsBundle
    bundle = EventNewsBundle(event=event, articles=articles, as_of_utc=bundle_as_of)
    result = score_bundle(bundle, instrument)
    if not result.contributions and not result.precursor_contributions:
        return None
    return result


def _classify_outcome(instrument: str, event_time_utc: dt.datetime):
    """
    Runs the ACTUAL outcome_classifier.classify() against genuine
    historical Dukascopy prices. Lazy import — same reasoning as
    scripts/confirm_backtest_outcomes.py: the optional Dukascopy
    dependency must not be required for a --dry-run or any caller that
    doesn't need it.
    """
    from scoring.outcome_classifier import classify
    return classify(instrument, event_time_utc)


def _attempt_outcome_confirmation(instrument: str, event_time_utc: dt.datetime):
    try:
        return _classify_outcome(instrument, event_time_utc)
    except Exception as exc:  # noqa: BLE001 — any fetch failure degrades to "no real outcome", never fabricated
        print(f"[seed_historical_data] No real outcome for {instrument} at {event_time_utc.isoformat()}: {exc}")
        return None


def run_seed(
    facts: list[HistoricalEventFact],
    dashboard_conn,
    backtest_conn,
    instruments: list[str],
    now: dt.datetime | None = None,
) -> SeedReport:
    report = SeedReport()
    now = now or dt.datetime.now(UTC_TZ)

    for fact in facts:
        event = EconomicEvent(fact.title, "USD", "High", fact.event_time_utc)
        event.forecast = fact.forecast
        event.previous = fact.previous
        event.actual = fact.actual

        surprise_direction = classify_surprise(event, EVENT_SURPRISE_DIRECTION.get(fact.title))
        dash_store.upsert_event_history(dashboard_conn, event, surprise_direction, now, source="seeded")
        report.calendar_writes += 1

        for instrument in instruments:
            already_seeded = backtest_conn.execute(
                "SELECT 1 FROM predictions WHERE event_title = ? AND instrument = ? AND event_time_utc = ? AND source = 'seeded'",
                (fact.title, instrument, fact.event_time_utc.isoformat()),
            ).fetchone()
            if already_seeded:
                continue  # idempotency: already ran for this occurrence

            articles = _fetch_real_articles(event)
            result = _attempt_article_prediction(event, instrument, articles)
            if result is None:
                report.predictions_skipped += 1
                report.skip_reasons.append(f"{fact.title}/{instrument}@{fact.event_time_utc.isoformat()}: no real article-based prediction")
                continue

            bt_store.record_prediction(
                backtest_conn, fact.title, instrument, fact.event_time_utc,
                result.probability, result.direction.value, result.confidence,
                result.article_count, result.contradiction_flag,
                scored_at_utc=fact.event_time_utc, source="seeded",
            )
            report.predictions_written += 1

            classification = _attempt_outcome_confirmation(instrument, fact.event_time_utc)
            if classification is None or classification.direction is None:
                report.outcomes_skipped += 1
                continue
            bt_store.record_outcome(
                backtest_conn, fact.title, instrument, fact.event_time_utc,
                classification.direction.value, classification.note,
                confirmed_at_utc=now, source="seeded",
            )
            report.outcomes_written += 1

    return report


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    dashboard_conn = dash_store.get_connection()
    backtest_conn = bt_store.get_connection()
    if dry_run:
        print(f"[seed_historical_data] DRY RUN — would process {len(HISTORICAL_EVENTS)} event facts, no writes.")
    else:
        report = run_seed(HISTORICAL_EVENTS, dashboard_conn, backtest_conn, list(INSTRUMENTS.keys()))
        print(f"[seed_historical_data] calendar_writes={report.calendar_writes} "
              f"predictions_written={report.predictions_written} predictions_skipped={report.predictions_skipped} "
              f"outcomes_written={report.outcomes_written} outcomes_skipped={report.outcomes_skipped}")
        for reason in report.skip_reasons:
            print(f"[seed_historical_data] skipped: {reason}")
    dashboard_conn.close()
    backtest_conn.close()
```

**Note:** `classify_surprise()`'s exact signature must be confirmed against `data_layer/calendar_feed.py` before this compiles — read that function first; adjust the call above (`classify_surprise(event, EVENT_SURPRISE_DIRECTION.get(fact.title))`) to match its real parameter order/names if they differ from this draft.

- [ ] **Step 5: Replace the placeholder fact and run tests**

Fix or delete the `"TBD_RESEARCH"` entry in `data_layer/historical_events.py`'s `HISTORICAL_EVENTS` (research it via `WebSearch`, or remove it if the first real entry alone is sufficient proof — your call, but `test_no_placeholder_facts_in_the_shipped_dataset` must pass).

Run: `python tests/test_seed_historical_data.py`
Expected: all 7 tests PASS.

- [ ] **Step 6: Run the full regression suite**

Run: `python tests/test_webapp_store.py`, `python tests/test_backtest_store.py`
Expected: all PASS unchanged.

- [ ] **Step 7: Commit**

```bash
git add scripts/seed_historical_data.py data_layer/historical_events.py tests/test_seed_historical_data.py
git commit -m "feat: add historical backfill seed script (real-data-only mechanism)

scripts/seed_historical_data.py: calendar-side event facts always
write (researched/cited, never simulated). Article-based predictions
and price outcomes are ONLY recorded when the actual, unmodified live
functions (build_event_news_bundle + score_bundle against real
Alpha Vantage articles; outcome_classifier.classify against real
Dukascopy prices) return real, non-empty results -- no reconstruction,
no confidence-capped guess, absent stays absent. Idempotent re-runs
via a source='seeded' existence check per occurrence.

data_layer/historical_events.py ships with real, cited seed facts
(reused from tests/run_historical_backtest.py where in-range) -- full
Jan-Aug 9 coverage is Task 4."
```

---

### Task 4: Research and populate the full Jan 1 – Aug 9, 2026 dataset

**Files:**
- Modify: `data_layer/historical_events.py`

**Interfaces:**
- Consumes: `HistoricalEventFact` (Task 3).
- Produces: an extended `HISTORICAL_EVENTS` list — no new interface, pure data.

- [ ] **Step 1: Research and add every High-impact USD occurrence, Jan 1 – Aug 9, 2026, for every title in `config.settings.EVENT_SURPRISE_DIRECTION`**

This is a pure research/content task, not a coding task — there is no code to write beyond appending `HistoricalEventFact(...)` entries to `HISTORICAL_EVENTS`. Use `WebSearch` per occurrence (or per event-type, searching for a full year's release calendar at once where a single source lists it — e.g. BLS's own release schedule page lists every CPI/NFP/PPI date for the year in one page, more efficient than one search per month).

Concretely, for each of these titles (`config.settings.EVENT_SURPRISE_DIRECTION`'s keys), find every occurrence between 2026-01-01 and 2026-08-09 and its real forecast/previous/actual: Non-Farm Employment Change, ADP Nonfarm Employment Change, Average Hourly Earnings m/m, Unemployment Rate, Unemployment Claims (weekly — this one alone is ~31 occurrences, consider whether weekly claims backfill is worth the volume vs. the monthly-cadence events; use your judgment and note the decision in the commit message if you scope it down), Challenger Job Cuts, CPI m/m, CPI y/y, Core CPI m/m, Core CPI y/y, PPI m/m, Core PPI m/m, Import Prices m/m, ISM Manufacturing PMI, Retail Sales m/m, Core PCE Price Index m/m.

**Reuse `tests/run_historical_backtest.py`'s 14 existing cases first** — read that file, extract every case whose `event_time_utc` falls in this backfill's range, and transcribe its already-researched forecast/previous/actual (with its existing citation) directly into `HistoricalEventFact` entries — this avoids re-researching what's already been found this session.

For every NEW occurrence you research, write a real `source_note` citing where you verified the number (e.g. "BLS Employment Situation report, bls.gov, released 2026-03-06" or "TradingEconomics historical CPI archive, verified 2026-08-13").

**Do not fabricate a plausible-looking number if you can't find a real source for it** — if a specific occurrence genuinely can't be verified after a real search attempt, skip that occurrence entirely (log it in the commit message as skipped-unverifiable) rather than guessing. This is the same "absent, not fabricated" rule as everything else in this plan, applied to the research step itself.

- [ ] **Step 2: Run the placeholder-scan test**

Run: `python tests/test_seed_historical_data.py::test_no_placeholder_facts_in_the_shipped_dataset` (or the whole file — `python tests/test_seed_historical_data.py`)
Expected: PASS — confirms zero `"TBD_RESEARCH"` markers remain.

- [ ] **Step 3: Dry-run the script against the full dataset**

Run: `python scripts/seed_historical_data.py --dry-run`
Expected: prints the event count with no errors — confirms every `HistoricalEventFact.title` matches a real `EVENT_SURPRISE_DIRECTION` key (a typo'd title would silently produce `classify_surprise(event, None)` — check the dry-run path validates titles, or add a simple validation loop that raises on an unrecognized title before this step is considered done).

- [ ] **Step 4: Run the real seed (respecting the Alpha Vantage rate limit)**

Run: `python scripts/seed_historical_data.py` — this makes REAL API calls (Alpha Vantage, Dukascopy). Given the 25-req/day free-tier cap, this will likely need multiple days' runs to complete the full dataset if there are more than ~25 occurrences with real historical article coverage attempted — the script's idempotency (Task 3) makes this safe to run once per day until `predictions_skipped`/`predictions_written` stabilizes. Report the final counts in the commit message.

- [ ] **Step 5: Commit**

```bash
git add data_layer/historical_events.py
git commit -m "feat: research and populate Jan 1 - Aug 9 2026 historical event dataset

Full High-impact USD event coverage for the backfill range, reusing
tests/run_historical_backtest.py's already-researched in-range cases
verbatim, researching every remaining occurrence via WebSearch with a
citation per fact. [N] occurrences skipped as genuinely unverifiable
after a real search attempt (listed below) rather than guessed.

Live seed run: [calendar_writes]/[predictions_written]/[outcomes_written]
per scripts/seed_historical_data.py's final report."
```

---

### Task 5: History tab "(seeded)" badge

**Files:**
- Modify: `webapp/history.py`
- Modify: `webapp/app.py`
- Modify: `webapp/static/app.js`
- Test: `tests/test_webapp_app.py`, `tests/test_webapp_history.py` (or wherever `build_print_call_history()`'s existing tests live — check current filename)

**Interfaces:**
- Consumes: `EventHistoryRow.source`, `Prediction.source`, `PrintPrediction.source` (Tasks 1-2).
- Produces: `HistoryRow.source: str` (new field); `GET /api/history`'s JSON gains a `source` key per row.

- [ ] **Step 1: Write the failing test**

Add to the History-tab test file (check exact filename/location first — `webapp/history.py`'s existing tests):

```python
def test_history_row_carries_source_and_prefers_seeded_when_mixed():
    print("=== webapp/history: HistoryRow.source reflects the underlying row's provenance ===")
    # Construct fixture data with a 'seeded' event_history row + a 'seeded' print_predictions
    # row for the same occurrence (check the existing test fixture-building helper in this
    # file and follow its exact pattern rather than duplicating setup logic).
    ...  # implementer: mirror this file's existing fixture-setup style exactly
    rows = build_print_call_history()
    assert rows[0].source == "seeded"
    print("PASS\n")
```

(Implementer: this file's exact fixture pattern for seeding `event_history`/`print_predictions` test rows must be read first — do not invent a new setup style; follow whatever helper the existing History-tab tests already use, e.g. a `_seed_event_history_row()`-style helper if one exists.)

- [ ] **Step 2: Run test to verify it fails**

Run the test file directly.
Expected: `AttributeError: 'HistoryRow' object has no attribute 'source'`.

- [ ] **Step 3: Add `source` to `HistoryRow` and its join logic**

In `webapp/history.py`, add `source: str` to the `HistoryRow` dataclass. In `build_print_call_history()`'s join logic (read the current function in full first — do not guess), a numeric row's `source` comes from the matched `event_history` row's `source`; a text-fallback row's `source` comes from the matched `predictions` row's `source`. If either side of a numeric row's join (event_history + print_predictions) disagrees on `source` (shouldn't normally happen, but if the print-call row is `'seeded'` while the calendar row is `'live'` or vice versa), prefer `'seeded'` — a row that's partially reconstructed is more honestly labeled by its most-uncertain component, not its most-certain one.

- [ ] **Step 4: Expose `source` in the API and UI**

In `webapp/app.py`'s `GET /api/history` route, add `"source": r.source` to each serialized row's dict.

In `webapp/static/app.js`'s `renderHistoryTable()`, add a small badge next to the event title when `r.source === 'seeded'`, matching the existing `unchanged_vs_previous` badge's visual weight (small, gray, informational — not alarming):

```javascript
const sourceBadge = r.source === 'seeded'
  ? ' <span style="color:#888;font-size:11px;font-weight:normal">(seeded)</span>'
  : '';
```

Add `sourceBadge` into the event-title cell's template string (the first `<td>` in the existing row template).

- [ ] **Step 5: Run tests to verify they pass**

Run the History-tab test file, then `python tests/test_webapp_app.py`.
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add webapp/history.py webapp/app.py webapp/static/app.js tests/test_webapp_history.py
git commit -m "feat: surface (seeded) provenance badge on the History tab

HistoryRow gains a source field, threaded from the underlying
event_history/print_predictions rows through GET /api/history to a
small, informational badge next to any backfilled row's event title —
matches the existing unchanged_vs_previous badge's visual weight.
A numeric row's mixed-provenance join (rare) prefers 'seeded' as the
more honest label."
```

---

### Task 6: README update (Part 1 — Backfill)

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a subsection**

Insert after the existing "Kalshi prediction-market scoring contribution" subsection (find via `grep -n "^### " README.md` to confirm current structure — other work may have interleaved since this plan was written):

```markdown
### Historical data backfill (Jan 2026 → live start)

`scripts/seed_historical_data.py` backfills real event/prediction/
outcome data for every High-impact USD event from 2026-01-01 through
the live system's actual tracking start (2026-08-09T23:50:00+00:00) —
see `data_layer/historical_events.py` for the researched, cited event
facts and `docs/superpowers/specs/2026-08-13-historical-backfill-and-ui-redesign-design.md`
for the full design.

**Real data or absent — never reconstructed.** Event facts (forecast/
previous/actual) are researched and cited. Article-based predictions
and price outcomes are recorded ONLY when the actual scoring/
classification functions (`score_bundle()`, `outcome_classifier.classify()`)
return real, genuinely-retrieved data (Alpha Vantage historical
articles, Dukascopy historical prices) — no fallback, no
confidence-capped guess standing in for a real signal. A `source`
column (`'live'`/`'seeded'`) on `event_history`/`predictions`/
`print_predictions`/`outcomes` marks provenance; the History tab shows
a small "(seeded)" badge on backfilled rows. Trend-streak scoring
treats seeded and live `event_history` rows identically — a real
historical CPI print is exactly as real as a live-captured one.

No Kalshi historical backfill — a real-money market price from the
past cannot be reconstructed with any integrity.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document the historical data backfill"
```

---

### Task 7: Decouple `/api/predictions`'s three layers (fix the bug)

**Files:**
- Modify: `webapp/app.py`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `/api/predictions`'s `events[]` entries no longer require an essence-only `prediction_runs` row to exist before `article_prediction`/`print_prediction` are populated.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_webapp_app.py` (check current fixture-setup helpers for this route's existing tests — mirror that style):

```python
def test_predictions_shows_article_prediction_even_when_essence_score_missing():
    print("=== /api/predictions: article_prediction/print_prediction show even when NO essence-only score exists yet for this symbol ===")
    # Set up: a tracked symbol with ZERO prediction_runs rows (simulating
    # a newly-added symbol before the scheduler's next cycle), but a REAL
    # accumulator prediction already recorded in the backtest DB for the
    # same event. Follow this file's existing pattern for seeding both
    # DBs (check how other /api/predictions tests set up fixtures).
    ...  # implementer: mirror existing fixture style exactly
    resp = client.get("/api/predictions")
    data = resp.get_json()
    entry = next(e for e in data["predictions"] if e["symbol"] == "XAUUSD")
    event = entry["events"][0]
    assert event["article_prediction"] is not None  # THE bug fix — this was previously unreachable without an essence score
    print("PASS\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_webapp_app.py`
Expected: fails — either an `IndexError`/`StopIteration` (the event never appears in `entry["events"]` at all today) or `AssertionError` if it does appear with `article_prediction: None`.

- [ ] **Step 3: Restructure the route**

In `webapp/app.py`'s `get_predictions()`, read the current loop body in full first (shown in earlier context: iterates `events`, calls `get_latest_two()`, `continue`s if empty, then fetches `accumulator_prediction`/`print_call` only after that point). Restructure so each event's dict is built even when `runs` is empty:

```python
        for event in events:
            runs = get_latest_two(conn, ticker, event["title"])
            latest = runs[0] if runs else None
            previous = runs[1] if len(runs) > 1 else None

            accumulator_runs = get_latest_two_predictions(backtest_conn, event["title"], ticker)
            accumulator_prediction = accumulator_runs[0] if accumulator_runs else None
            accumulator_previous = accumulator_runs[1] if len(accumulator_runs) > 1 else None
            article_prediction = None
            if accumulator_prediction is not None:
                article_prediction = {
                    "direction": accumulator_prediction.direction,
                    "probability": accumulator_prediction.probability,
                    "article_count": accumulator_prediction.article_count,
                }
            previous_article_prediction = None
            if accumulator_previous is not None:
                previous_article_prediction = {
                    "direction": accumulator_previous.direction,
                    "probability": accumulator_previous.probability,
                    "article_count": accumulator_previous.article_count,
                }
            print_call = get_latest_print_prediction(
                backtest_conn, event["title"], dt.datetime.fromisoformat(event["event_time_utc"]),
            )
            print_prediction = None
            if print_call is not None:
                print_prediction = {"direction": print_call.predicted_vs_forecast, "confidence": print_call.confidence}

            # An event is only worth including in this symbol's list at
            # all if SOME layer has something to say about it — an event
            # with zero essence score AND zero article prediction AND
            # zero print call is genuinely nothing-yet, same as before.
            if latest is None and article_prediction is None and print_prediction is None:
                continue

            entry["events"].append({
                "event_title": event["title"],
                "event_time_utc": event["event_time_utc"],
                "probability": latest.probability if latest else None,
                "direction": latest.direction if latest else "pending",
                "previous_probability": previous.probability if previous else None,
                "previous_direction": previous.direction if previous else None,
                "article_count": accumulator_prediction.article_count if accumulator_prediction else None,
                "article_prediction": article_prediction,
                "previous_article_prediction": previous_article_prediction,
                "print_prediction": print_prediction,
            })
```

(`direction` defaults to `"pending"` — not `None` — when `latest` is absent, matching the frontend's existing `next.direction === "pending"` branch so a card with only an article prediction and no essence score still renders sensibly rather than hitting an unhandled `direction` value.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_app.py`
Expected: all PASS, including the new test and the existing sort-order tests (confirm the sort key at the bottom of the function, which reads `ev["direction"]`, still works with the new `"pending"` default — it should, since that's the same string the essence-only-pending case already used).

- [ ] **Step 5: Commit**

```bash
git add webapp/app.py tests/test_webapp_app.py
git commit -m "fix: stop hiding article_prediction/print_prediction behind the essence-only score

/api/predictions required an essence-only prediction_runs row to exist
for an event before even LOOKING at article_prediction/print_prediction
-- a newly-added symbol showed a fully blank card until
webapp/scheduler.py's next cycle scored it, even when the accumulator
already had a real, independently-computed opinion sitting in its own
database. Each layer is now fetched and serialized independently; an
event is only dropped from the response if ALL THREE layers have
nothing to say, not just the essence-only one."
```

---

### Task 8: Frontend — render decoupled layers correctly

**Files:**
- Modify: `webapp/static/app.js`

**Interfaces:**
- Consumes: Task 7's restructured `/api/predictions` response (`direction: "pending"` with real `article_prediction`/`print_prediction` populated is now a valid, real combination, not just a placeholder state).

- [ ] **Step 1: Read `renderCard()`'s current pending-branch handling**

`webapp/static/app.js:260-270` (per the version read earlier in this plan's research) already renders `articlePredictionLine`/`printPredictionLine` inside the `pending` branch — check whether this still needs a code change after Task 7, or whether it already Just Works because the pending branch already includes those lines. Read the CURRENT file state first (it may have shifted since this plan was written) before assuming a change is needed.

- [ ] **Step 2: If needed, adjust the pending-branch copy**

If the pending branch's copy ("Awaiting: <event>") reads oddly when a real article prediction is ALSO present (e.g. it might now be worth distinguishing "no essence score yet, but here's what the article engine thinks" from "genuinely nothing happening"), adjust the heading text conditionally:

```javascript
  if (next.direction === "pending") {
    const hasAnySignal = articlePredictionLine || printPredictionLine;
    const heading = hasAnySignal
      ? `Awaiting essence score: ${escapeHtml(next.event_title)}`
      : `Awaiting: ${escapeHtml(next.event_title)}`;
    body += `<div class="pending">${heading}<br>
      <span style="font-size:12px;color:#888">${formatEventDateTime(next.event_time_utc)}</span></div>
      ${articlePredictionLine}${printPredictionLine}`;
    el.innerHTML = body;
    el.querySelector(".remove-btn").addEventListener("click", () => removeSymbol(symbol));
    return el;
  }
```

- [ ] **Step 3: Verify live**

Use the Browser pane: `preview_start` against the running dashboard (or restart `run_all.py` first if not already running), navigate to the Dashboard tab, confirm a symbol with a real article prediction but no essence score renders the article prediction — not a blank/plain "Awaiting" card. Screenshot as proof.

- [ ] **Step 4: Commit**

```bash
git add webapp/static/app.js
git commit -m "fix: distinguish 'no essence score yet, but a real article read exists' from 'nothing yet' in the pending-card heading"
```

---

### Task 9: Backend — add trend-streak + Kalshi read to `/api/predictions`

**Files:**
- Modify: `webapp/app.py`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `webapp.trend.compute_trend_signal()` (existing), `scoring.backtest_store.get_latest_kalshi_read()` (existing, from the Kalshi feature).
- Produces: each event dict in `/api/predictions` gains `trend_signal: {direction, strength} | None` and `kalshi_read: {implied_direction, implied_probability, open_interest} | None`.

**No changes to `scoring/probability_engine.py` anywhere in this task** — both signals are already independently persisted/computable; this task only adds two more read-only fetches to the same per-event loop Task 7 restructured.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_webapp_app.py`:

```python
def test_predictions_includes_trend_signal_and_kalshi_read_when_present():
    print("=== /api/predictions: trend_signal and kalshi_read appear on an event when real data exists for them ===")
    # Seed event_history with enough prior occurrences for compute_trend_signal()
    # to produce a real streak (check webapp/trend.py's MIN_OCCURRENCES_FOR_TREND_PRIOR-
    # equivalent threshold and existing trend tests for the exact fixture shape), and
    # seed kalshi_reads with a real row for the current occurrence (mirror
    # tests/test_backtest_store.py's kalshi_reads fixture pattern).
    ...  # implementer: mirror existing fixture styles exactly, from both webapp/trend's
         # own tests and backtest_store's kalshi_reads tests
    resp = client.get("/api/predictions")
    data = resp.get_json()
    event = data["predictions"][0]["events"][0]
    assert event["trend_signal"] is not None
    assert event["kalshi_read"] is not None
    assert event["kalshi_read"]["implied_direction"] in ("higher", "lower", "in_line")
    print("PASS\n")


def test_predictions_trend_signal_and_kalshi_read_absent_when_nothing_recorded():
    print("=== /api/predictions: trend_signal and kalshi_read are None, not fabricated, when nothing real exists for them ===")
    ...  # implementer: an event with no prior event_history occurrences and no kalshi_reads row
    resp = client.get("/api/predictions")
    data = resp.get_json()
    event = data["predictions"][0]["events"][0]
    assert event["trend_signal"] is None
    assert event["kalshi_read"] is None
    print("PASS\n")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_app.py`
Expected: `KeyError: 'trend_signal'` (the response dict doesn't have these keys yet).

- [ ] **Step 3: Add the two fetches to the per-event loop**

In `webapp/app.py`, add imports:

```python
from webapp.trend import compute_trend_signal
from scoring.backtest_store import get_latest_kalshi_read
```

(Merge into the existing `from webapp.trend import summarize_trend` and `from scoring.backtest_store import (...)` lines rather than duplicating — check current import blocks first.)

Inside the per-event loop (after the `print_call`/`print_prediction` block from Task 7, before appending to `entry["events"]`):

```python
            event_time = dt.datetime.fromisoformat(event["event_time_utc"])
            prior_occurrences = get_event_history(conn, event["title"])
            trend = compute_trend_signal(prior_occurrences)
            trend_signal = None
            if trend is not None:
                trend_signal = {"direction": trend.direction, "strength": trend.strength}

            kalshi_row = get_latest_kalshi_read(backtest_conn, event["title"], event_time)
            kalshi_read = None
            if kalshi_row is not None:
                kalshi_read = {
                    "implied_direction": kalshi_row.implied_direction,
                    "implied_probability": kalshi_row.implied_probability,
                    "open_interest": kalshi_row.open_interest,
                }
```

Add `"trend_signal": trend_signal, "kalshi_read": kalshi_read,` to the dict appended to `entry["events"]`.

**Note:** confirm `compute_trend_signal()`'s exact parameter shape and `TrendSignal`'s exact field names (`direction`/`strength` is this plan's assumption — verify against `webapp/trend.py` directly before writing this code) — read that file first, do not guess. Same for `get_latest_kalshi_read()`'s return type field names (`KalshiReadRecord` — confirmed earlier this session to have `implied_direction`, `implied_probability`, `open_interest`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_app.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add webapp/app.py tests/test_webapp_app.py
git commit -m "feat: surface trend_signal + kalshi_read on /api/predictions

Both signals were already computed/persisted elsewhere
(webapp.trend.compute_trend_signal() from event_history,
scoring.backtest_store.get_latest_kalshi_read() from the Kalshi
feature) but never reached the API response. No scoring engine
changes -- purely two more read-only fetches in the existing
per-event loop, same pattern as print_prediction."
```

---

### Task 10: Frontend — "Why this call" breakdown panel + Kalshi surface

**Files:**
- Modify: `webapp/static/app.js`
- Modify: `webapp/static/style.css`

**Interfaces:**
- Consumes: Task 9's `trend_signal`/`kalshi_read` fields.

- [ ] **Step 1: Add a Kalshi line, matching `articlePredictionHtml`/`printPredictionHtml`'s existing style**

In `webapp/static/app.js`, add a new render function near `printPredictionHtml()`:

```javascript
  // kalshi_read is the highest-trust signal in the system (real money
  // priced on the exact event) -- absent (null) whenever no Kalshi
  // market covers this event or the read hasn't landed yet, rendered as
  // nothing, never a fabricated placeholder, same convention as every
  // other optional signal on this card.
  function kalshiReadHtml(kalshi) {
    if (!kalshi) return '';
    const label = kalshi.implied_direction === 'higher' ? 'HIGHER than forecast'
      : kalshi.implied_direction === 'lower' ? 'LOWER than forecast' : 'IN LINE with forecast';
    const pct = Math.round(kalshi.implied_probability * 100);
    return `<div class="kalshi-read">
      💰 Kalshi market: likely <b>${label}</b> <span style="font-size:12px;color:#888">(${pct}% implied, ${Math.round(kalshi.open_interest)} open interest)</span>
    </div>`;
  }
```

Call it alongside `articlePredictionLine`/`printPredictionLine` in `renderCard()` (both the pending branch and the resolved branch) — add `const kalshiReadLine = kalshiReadHtml(next.kalshi_read);` and include `${kalshiReadLine}` wherever the other two lines are already inserted.

- [ ] **Step 2: Add the collapsible breakdown panel**

Add a "Why this call ▾" toggle (mirroring the existing `.history-toggle`/`.history-toggle-btn` pattern exactly — same expand/collapse mechanics, no new fetch needed since `trend_signal`/`kalshi_read`/`article_prediction`/`print_prediction` are already in the already-fetched `next` object):

```javascript
  function breakdownPanelHtml(next) {
    const rows = [];
    if (next.article_prediction) {
      rows.push(`<div>📰 Article sentiment: ${directionLabel(next.article_prediction.direction)} (${next.article_prediction.article_count} articles)</div>`);
    }
    if (next.print_prediction) {
      rows.push(`<div>📊 Print-direction lexicon: ${next.print_prediction.direction} (${Math.round(next.print_prediction.confidence * 100)}% conf.)</div>`);
    }
    if (next.trend_signal) {
      rows.push(`<div>📈 Trend streak: ${next.trend_signal.direction} (strength ${next.trend_signal.strength.toFixed(2)})</div>`);
    }
    if (next.kalshi_read) {
      rows.push(`<div>💰 Kalshi market: ${next.kalshi_read.implied_direction} (${Math.round(next.kalshi_read.implied_probability * 100)}% implied)</div>`);
    }
    if (rows.length === 0) {
      return '<div style="font-size:12px;color:#888">No structured signals fired for this event yet.</div>';
    }
    return rows.join('');
  }
```

In `renderCard()`'s resolved (non-pending) branch, after the existing History toggle block, add:

```javascript
  const breakdownToggleId = `breakdown-${symbol}-${next.event_title.replace(/[^a-zA-Z0-9]/g, '')}`;
  body += `<div class="history-toggle">
    <button class="history-toggle-btn" data-target="${breakdownToggleId}">Why this call ▾</button>
    <div class="history-panel" id="${breakdownToggleId}">${breakdownPanelHtml(next)}</div>
  </div>`;
```

(Reuses the existing `.history-toggle`/`.history-panel`/`.history-toggle-btn` CSS classes — no new styling needed. The toggle click-handler wiring below the existing History button needs a small generalization: the current code assumes every `.history-toggle-btn` fetches `/api/event_history` on first expand — the breakdown panel's content is already inline, no fetch needed. Read the current click-handler code (`app.js`'s `historyBtn.addEventListener(...)` block) and either add a second, simpler click handler for buttons whose panel already has content (check `panel.dataset.loaded` isn't required — just toggle `display`), or give the breakdown toggle a distinct class so the two toggles' handlers don't collide. Your judgment on the cleanest way to avoid the two toggle types interfering — this needs to actually work when both toggles exist on the same card, not just look right in isolation.)

- [ ] **Step 3: Verify live**

Use the Browser pane against the running dashboard. Expand a card's "Why this call" panel, confirm it shows real data (or the honest "no structured signals fired" message) and doesn't break the existing History toggle. Screenshot.

- [ ] **Step 4: Commit**

```bash
git add webapp/static/app.js webapp/static/style.css
git commit -m "feat: add 'Why this call' breakdown panel + Kalshi surface to dashboard cards

Kalshi gets a real line item matching article_prediction/
print_prediction's existing visual treatment. A new collapsible panel
(reusing the existing history-toggle CSS/interaction pattern) shows
which structured signals actually fired this cycle -- article
sentiment, print-direction lexicon, trend streak, Kalshi -- using data
already fetched on the card, no new network request on expand."
```

---

### Task 11: Calendar — impact color-coding + nearest-upcoming default

**Files:**
- Modify: `webapp/static/app.js`
- Modify: `webapp/static/style.css`

**Interfaces:**
- Consumes: `event.impact` (already present in every `/api/calendar` event dict — no backend change needed).

- [ ] **Step 1: Add impact-tier CSS classes**

In `webapp/static/style.css`, add (near the existing `.cal-dot`/`.cal-cell` rules):

```css
.cal-dot.impact-high { background: #c62828; }
.cal-dot.impact-medium { background: #f9a825; }
.cal-dot.impact-low { background: #9e9e9e; }
.cal-cell.nearest-upcoming { outline: 2px solid #1565c0; outline-offset: -2px; }
```

(Check `.cal-dot`'s existing base rule first — it likely already sets `background`/size/shape; the tier classes above should only override `background`, not duplicate the base rule's other properties.)

- [ ] **Step 2: Apply the classes in `refreshCalendar()`**

In `webapp/static/app.js`'s `refreshCalendar()`, change the dot-building line:

```javascript
    const dots = dayEvents.map((e) => {
      const impactClass = e.impact === 'High' ? 'impact-high' : e.impact === 'Medium' ? 'impact-medium' : 'impact-low';
      return `<span class="cal-dot ${impactClass}" title="${escapeHtml(e.title)} (${escapeHtml(e.impact)})"></span>`;
    }).join("");
```

Add nearest-upcoming highlighting: find the nearest future event (or today's, if one is happening now) and apply `.nearest-upcoming` to its cell:

```javascript
  const now = new Date();
  const upcoming = events
    .map((e) => new Date(e.event_time_utc))
    .filter((d) => d >= now)
    .sort((a, b) => a - b);
  const nearestUpcomingDateStr = upcoming.length > 0 ? upcoming[0].toDateString() : null;
```

Use `nearestUpcomingDateStr` inside the day-cell-building loop to add `nearest-upcoming` to the matching cell's class list (alongside the existing `isToday` check).

- [ ] **Step 3: Verify live**

Browser pane: navigate to the Calendar tab, confirm High/Medium/Low events show visibly distinct dot colors and the nearest upcoming event's cell is outlined. Screenshot.

- [ ] **Step 4: Commit**

```bash
git add webapp/static/app.js webapp/static/style.css
git commit -m "feat: color-code calendar events by impact tier, highlight nearest upcoming"
```

---

### Task 12: Calendar — click-to-inspect a date

**Files:**
- Modify: `webapp/app.py`
- Modify: `webapp/static/index.html`
- Modify: `webapp/static/app.js`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: nothing new on the backend beyond existing `get_event_history`/predictions logic.
- Produces: `GET /api/calendar/date/<date>` — new route returning that date's events plus each tracked symbol's current call for them.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_webapp_app.py`:

```python
def test_calendar_date_route_returns_events_and_calls_for_that_date_only():
    print("=== GET /api/calendar/date/<date>: returns only that date's events, with each tracked symbol's call ===")
    ...  # implementer: seed calendar_snapshot with events on two different dates,
         # seed prediction_runs for one symbol on one of those dates, mirror existing fixture style
    resp = client.get("/api/calendar/date/2026-08-12")
    data = resp.get_json()
    assert len(data["events"]) == 1  # only the one event actually on 2026-08-12
    assert data["events"][0]["calls"]["XAUUSD"] is not None  # or None if genuinely nothing recorded -- assert whichever your fixture set up
    print("PASS\n")


def test_calendar_date_route_empty_date_returns_empty_list_not_error():
    print("=== GET /api/calendar/date/<date>: a date with no events returns {events: []}, not a 404/500 ===")
    resp = client.get("/api/calendar/date/2026-12-25")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["events"] == []
    print("PASS\n")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_app.py`
Expected: 404 (route doesn't exist).

- [ ] **Step 3: Implement the route**

In `webapp/app.py`:

```python
@app.route("/api/calendar/date/<date_str>", methods=["GET"])
def get_calendar_for_date(date_str: str):
    """
    Every event on this exact calendar date, each with every tracked
    symbol's CURRENT call for it (same data /api/predictions already
    computes, filtered down to this date -- not a new scoring path).
    date_str is YYYY-MM-DD.
    """
    try:
        target_date = dt.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400

    conn = get_connection()
    backtest_conn = get_backtest_connection()
    snapshot = get_calendar_snapshot(conn)
    all_events = snapshot.events if snapshot is not None else []
    day_events = [e for e in all_events if dt.datetime.fromisoformat(e["event_time_utc"]).date() == target_date]

    symbols = list_tracked_symbols(conn)
    result_events = []
    for event in day_events:
        calls = {}
        for ticker in symbols:
            runs = get_latest_two(conn, ticker, event["title"])
            calls[ticker] = {"direction": runs[0].direction, "probability": runs[0].probability} if runs else None
        result_events.append({
            "title": event["title"], "event_time_utc": event["event_time_utc"],
            "impact": event.get("impact"), "forecast": event.get("forecast"),
            "previous": event.get("previous"), "actual": event.get("actual"),
            "calls": calls,
        })

    conn.close()
    backtest_conn.close()
    return jsonify({"events": result_events})
```

(`backtest_conn` is opened but unused in this draft — remove it, OR extend `calls` to also include each symbol's `article_prediction`/`print_prediction` the same way Task 7's route does, using `backtest_conn`. Your judgment on whether the date-inspect panel needs article/print-level detail or just the essence score is enough for a compact per-date view — if you include it, mirror Task 7's exact fetch pattern rather than inventing a new one.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_app.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add webapp/app.py tests/test_webapp_app.py
git commit -m "feat: add GET /api/calendar/date/<date> for calendar click-to-inspect"
```

---

### Task 13: Calendar — click-to-inspect frontend

**Files:**
- Modify: `webapp/static/index.html`
- Modify: `webapp/static/app.js`
- Modify: `webapp/static/style.css`

**Interfaces:**
- Consumes: Task 12's `GET /api/calendar/date/<date>`.

- [ ] **Step 1: Add a side-panel container**

In `webapp/static/index.html`'s `#view-calendar` section, add (after `#calendar-list`):

```html
  <div id="calendar-date-panel" style="display:none">
    <button id="calendar-date-panel-close">✕</button>
    <h3 id="calendar-date-panel-title"></h3>
    <div id="calendar-date-panel-body"></div>
  </div>
```

- [ ] **Step 2: Wire click handlers on day cells**

In `webapp/static/app.js`'s `refreshCalendar()`, each `.cal-cell` needs a `data-date` attribute and a click listener (currently cells are built as raw HTML strings via `cells +=` — after setting `calendarGridEl.innerHTML = cells`, attach listeners in a follow-up pass, same pattern the existing history-toggle buttons use):

```javascript
  calendarGridEl.innerHTML = cells;
  calendarGridEl.querySelectorAll(".cal-cell[data-date]").forEach((cellEl) => {
    cellEl.addEventListener("click", () => showDatePanel(cellEl.dataset.date));
  });
```

(Add `data-date="${cellDate.toISOString().slice(0,10)}"` to each day cell's opening `<div>` in the cell-building loop — only for cells that have a real date, not the leading blank padding cells.)

- [ ] **Step 3: Implement `showDatePanel()`**

```javascript
async function showDatePanel(dateStr) {
  const panel = document.getElementById("calendar-date-panel");
  const title = document.getElementById("calendar-date-panel-title");
  const body = document.getElementById("calendar-date-panel-body");
  title.textContent = new Date(dateStr).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  body.innerHTML = "Loading…";
  panel.style.display = "";

  const resp = await fetch(`/api/calendar/date/${dateStr}`);
  const data = await resp.json();
  if (!data.events || data.events.length === 0) {
    body.innerHTML = "<div style=\"color:#888\">No tracked events on this date.</div>";
    return;
  }
  body.innerHTML = data.events.map((e) => {
    const callsHtml = Object.entries(e.calls || {}).map(([symbol, call]) => {
      if (!call) return `<div>${escapeHtml(symbol)}: <span style="color:#888">no call recorded</span></div>`;
      const pct = directionPct(call.probability, call.direction);
      return `<div>${escapeHtml(symbol)}: <b>${directionLabel(call.direction)} ${pct}%</b></div>`;
    }).join("");
    return `<div style="margin-bottom:10px">
      <b>${escapeHtml(e.title)}</b> (${escapeHtml(e.impact ?? "")})<br>
      <span style="font-size:12px;color:#888">forecast ${escapeHtml(e.forecast ?? "—")}, previous ${escapeHtml(e.previous ?? "—")}, actual ${escapeHtml(e.actual ?? "—")}</span>
      ${callsHtml}
    </div>`;
  }).join("");
}

document.getElementById("calendar-date-panel-close").addEventListener("click", () => {
  document.getElementById("calendar-date-panel").style.display = "none";
});
```

- [ ] **Step 4: Scope the flat event list to the selected/default date**

Change `calendarListEl`'s rendering (currently a flat dump of the whole fetched window) to default to the nearest-upcoming date (Task 11's `nearestUpcomingDateStr`) instead of every event — replace the existing unconditional `calendarListEl.innerHTML = events.map(...)` with a call to `showDatePanel()` using the nearest-upcoming date on initial load, OR keep the flat list but visually de-emphasize it now that click-to-inspect exists as the primary interaction. Your judgment on which reads better — the spec's intent is "default to nearest upcoming, dynamic on click," not a mandate to delete the flat list entirely.

- [ ] **Step 5: Verify live**

Browser pane: click a day cell with events, confirm the panel shows real event + call data; click a day with none, confirm the honest empty message; click close, confirm it hides. Screenshot both states.

- [ ] **Step 6: Commit**

```bash
git add webapp/static/index.html webapp/static/app.js webapp/static/style.css
git commit -m "feat: click a calendar date to inspect its events + tracked-symbol calls"
```

---

### Task 14: README update (Part 2 — UI redesign)

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a subsection**

Insert after Task 6's new "Historical data backfill" subsection:

```markdown
### Dashboard/Calendar UI redesign

Fixed a real bug: `/api/predictions` used to require an essence-only
score to exist for a symbol before showing that symbol's real
article-based prediction or print-direction call — a newly-added
symbol looked fully blank until the essence-only scheduler caught up,
even when the accumulator already had a genuine opinion. The three
layers (essence score, article prediction, print call) — plus two more
that were already computed/persisted but never surfaced (trend streak,
Kalshi read) — now render independently on each dashboard card, with a
collapsible "Why this call" breakdown panel showing which structured
signals actually fired.

The Calendar tab now color-codes events by impact tier, highlights the
nearest upcoming event by default, and lets you click any date to see
that date's events plus every tracked symbol's current call for them
(`GET /api/calendar/date/<date>`).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document the dashboard/calendar UI redesign"
```

---

## Post-plan verification (after all 14 tasks are complete)

- [ ] Run the full regression suite:

```bash
for f in tests/test_*.py; do echo "--- $f ---"; python "$f" 2>&1 | tail -6; done
```

Expected: every file ends with its "All ... tests passed." line (pre-existing SKIP/crash lines in `test_contextual_sentiment.py`/`test_scoring_smoke.py` are expected, unrelated).

- [ ] Restart `run_all.py` (kill any existing process tree first, per this session's established pattern), confirm live: add a new symbol via the dashboard and verify it does NOT sit fully blank if the accumulator already has data for it; open the History tab and confirm seeded rows show the "(seeded)" badge; click a calendar date and confirm the panel populates; expand a card's "Why this call" panel and confirm it shows real signals.
