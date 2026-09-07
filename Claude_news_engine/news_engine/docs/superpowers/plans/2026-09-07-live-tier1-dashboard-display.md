# Live Tier 1 Dashboard Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a Causation-Matrix Tier 1 prediction a real place to live (persisted, per-instrument) and a real place to show up (the live dashboard card, directly under sentiment's own call), so the two can be visually compared at a glance — without adding any new judgment logic, live-fetch integration, or agreement computation.

**Architecture:** A new `tier1_predictions` table in `scoring/backtest_store.py`'s existing DB, keyed and shaped like the existing `predictions` table (`event_title`/`instrument`/`event_time_utc`, one row per instrument). `record_tier1_prediction()`/`get_latest_tier1_prediction_for_occurrence()` mirror the existing `record_prediction()`/`get_latest_prediction_for_occurrence()` pair exactly, including confidence-tag validation at write time (mirroring `record_outcome()`'s `Direction` validation). The already-drafted September 2026 cases get persisted by extending the script that already computed them. `webapp/app.py`'s `/api/predictions` route adds one more read-only lookup per event, additive to the JSON response. `webapp/static/app.js` renders it directly beneath whatever the sentiment line already shows, using the exact same bullish/bearish/neutral color classes.

**Tech Stack:** Python 3.14, sqlite3, Flask, vanilla JS/CSS — same stack as the rest of `webapp/`/`scoring/`.

**Spec:** `docs/superpowers/specs/2026-09-07-live-tier1-dashboard-display-design.md`

## Global Constraints

- **`predicted_direction` values stored in `tier1_predictions` must exactly match `scoring.probability_engine.Direction`'s string values** (`'bullish'`/`'bearish'`/`'neutral'`) — the same enum sentiment's own `predictions` table already uses.
- **`confidence` is validated at write time** against exactly `{"Certain", "Likely", "Guessing"}` — reject anything else with a `ValueError`, same discipline `record_outcome()` already applies to `actual_direction`.
- **No History tab changes** — `webapp/history.py` is untouched by this plan.
- **No live-fetch integration** — nothing in this plan calls out to the Cleveland Fed/BLS/ISM. Persisting a prediction is still a human running a script after doing real research.
- **No agree/disagree computation anywhere on the live path** — `BacktestReport.agreement_rate()` (`scoring/backtest.py`) is untouched; the live card shows both calls side by side, nothing more.
- **No retroactive backfill** — the two completed July 2026 cases (`tests/run_causation_matrix_option_a_backtest.py`) are not written to the new table by this plan.
- **`article_prediction`'s existing JSON shape, and every other existing `/api/predictions` field, is unchanged** — `tier1_prediction` is a new, additive, always-present (possibly `null`) sibling field only.

---

## File Structure

- **Modify:** `scoring/backtest_store.py` — new `tier1_predictions` table in `_SCHEMA`, new `Tier1PredictionRow` dataclass, new `record_tier1_prediction()`/`get_latest_tier1_prediction_for_occurrence()` functions.
- **Modify:** `tests/test_backtest_store.py` — round-trip, confidence-validation, and per-instrument-scoping tests for the two new functions.
- **Modify:** `tests/run_causation_matrix_option_a_pending_sep2026.py` — persists `TIER1_PPI_SEP2026`/`TIER1_CPI_SEP2026` for both `XAUUSD` and `US30` via `record_tier1_prediction()`, in addition to the existing print-only output.
- **Modify:** `webapp/app.py` — one new read-only lookup per event in the existing `/api/predictions` loop, one new additive field in the response dict.
- **Modify:** `tests/test_webapp_app.py` — route-level test: `tier1_prediction` present with the right shape for a logged occurrence, `null` for everything else.
- **Modify:** `webapp/static/app.js` — new `tier1PredictionHtml()`, rendered directly beneath the existing sentiment line.
- **Modify:** `webapp/static/style.css` — new `.tier1-prediction` rule (+ `.bullish`/`.bearish`/`.neutral` modifiers), placed next to the existing `.article-prediction`/`.article-prediction-conflict` rules.

---

### Task 1: `tier1_predictions` table + read/write functions

**Files:**
- Modify: `scoring/backtest_store.py`
- Test: `tests/test_backtest_store.py`

**Interfaces:**
- Consumes: `scoring.probability_engine.Direction` (existing enum, for `predicted_direction` validation — mirrors `record_outcome()`'s exact pattern at `scoring/backtest_store.py:369-380`).
- Produces (for Task 2 and Task 3): `record_tier1_prediction(conn, event_title: str, instrument: str, event_time_utc: dt.datetime, value: str, confidence: str, source: str, predicted_direction: str, logged_at_utc: Optional[dt.datetime] = None) -> int` and `get_latest_tier1_prediction_for_occurrence(conn, event_title: str, instrument: str, event_time_utc: dt.datetime) -> Optional[Tier1PredictionRow]`, plus the `Tier1PredictionRow` dataclass (fields: `id: int`, `event_title: str`, `instrument: str`, `event_time_utc: str`, `value: str`, `confidence: str`, `source: str`, `predicted_direction: str`, `logged_at_utc: str`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_backtest_store.py` (append near the end of the file; it already imports `get_connection` and other functions from `scoring.backtest_store` at the top — add `record_tier1_prediction, get_latest_tier1_prediction_for_occurrence` to that existing import list):

```python
def test_record_and_get_tier1_prediction_round_trip():
    print("=== backtest_store: record_tier1_prediction + get_latest_tier1_prediction_for_occurrence round-trip ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)

        assert get_latest_tier1_prediction_for_occurrence(conn, "PPI m/m", "XAUUSD", event_time) is None

        record_tier1_prediction(
            conn, "PPI m/m", "XAUUSD", event_time,
            value="Muted, non-reaccelerating call", confidence="Certain",
            source="BLS July 2026 PPI release; ISM Manufacturing Prices Paid Aug 2026",
            predicted_direction="bullish",
        )

        row = get_latest_tier1_prediction_for_occurrence(conn, "PPI m/m", "XAUUSD", event_time)
        assert row is not None
        assert row.event_title == "PPI m/m"
        assert row.instrument == "XAUUSD"
        assert row.value == "Muted, non-reaccelerating call"
        assert row.confidence == "Certain"
        assert row.source == "BLS July 2026 PPI release; ISM Manufacturing Prices Paid Aug 2026"
        assert row.predicted_direction == "bullish"
        conn.close()
    print("PASS\n")


def test_get_tier1_prediction_returns_none_when_never_logged():
    print("=== backtest_store: get_latest_tier1_prediction_for_occurrence returns None for an occurrence with no logged row, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 11, 12, 30, tzinfo=dt.timezone.utc)
        assert get_latest_tier1_prediction_for_occurrence(conn, "CPI m/m", "XAUUSD", event_time) is None
        conn.close()
    print("PASS\n")


def test_record_tier1_prediction_rejects_invalid_confidence():
    print("=== backtest_store: record_tier1_prediction rejects a confidence tag outside Certain/Likely/Guessing ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)
        try:
            record_tier1_prediction(
                conn, "PPI m/m", "XAUUSD", event_time,
                value="v", confidence="High", source="s", predicted_direction="bullish",
            )
            assert False, "expected a ValueError for an invalid confidence tag"
        except ValueError as exc:
            assert "High" in str(exc)
        conn.close()
    print("PASS\n")


def test_record_tier1_prediction_rejects_invalid_direction():
    print("=== backtest_store: record_tier1_prediction rejects a predicted_direction outside the Direction enum's values ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)
        try:
            record_tier1_prediction(
                conn, "PPI m/m", "XAUUSD", event_time,
                value="v", confidence="Certain", source="s", predicted_direction="up",
            )
            assert False, "expected a ValueError for an invalid predicted_direction"
        except ValueError as exc:
            assert "up" in str(exc)
        conn.close()
    print("PASS\n")


def test_tier1_prediction_scoped_per_instrument():
    print("=== backtest_store: two instruments for the same event/occurrence get independent rows, neither overwrites the other ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 11, 12, 30, tzinfo=dt.timezone.utc)

        record_tier1_prediction(
            conn, "CPI m/m", "XAUUSD", event_time,
            value="v", confidence="Guessing", source="s", predicted_direction="neutral",
        )
        record_tier1_prediction(
            conn, "CPI m/m", "US30", event_time,
            value="v", confidence="Guessing", source="s", predicted_direction="bearish",
        )

        xauusd_row = get_latest_tier1_prediction_for_occurrence(conn, "CPI m/m", "XAUUSD", event_time)
        us30_row = get_latest_tier1_prediction_for_occurrence(conn, "CPI m/m", "US30", event_time)
        assert xauusd_row.predicted_direction == "neutral"
        assert us30_row.predicted_direction == "bearish"
        conn.close()
    print("PASS\n")


def test_tier1_prediction_scoped_per_occurrence_not_just_title():
    print("=== backtest_store: get_latest_tier1_prediction_for_occurrence scopes to the exact event_time_utc, same reasoning as get_latest_prediction_for_occurrence ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        july_time = dt.datetime(2026, 8, 13, 12, 30, tzinfo=dt.timezone.utc)
        sept_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)

        record_tier1_prediction(
            conn, "PPI m/m", "XAUUSD", july_time,
            value="July call", confidence="Certain", source="s", predicted_direction="bullish",
        )
        # No row logged yet for the September occurrence.
        row = get_latest_tier1_prediction_for_occurrence(conn, "PPI m/m", "XAUUSD", sept_time)
        assert row is None, "must not leak the July occurrence's row onto an unrelated later one"
        conn.close()
    print("PASS\n")


def test_latest_tier1_prediction_wins_on_multiple_logs():
    print("=== backtest_store: get_latest_tier1_prediction_for_occurrence returns the most recently logged row when the same occurrence is logged twice (a revised call) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = get_connection(db_path)
        event_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)

        record_tier1_prediction(
            conn, "PPI m/m", "XAUUSD", event_time,
            value="first pass", confidence="Likely", source="s", predicted_direction="neutral",
            logged_at_utc=dt.datetime(2026, 9, 6, 9, 0, tzinfo=dt.timezone.utc),
        )
        record_tier1_prediction(
            conn, "PPI m/m", "XAUUSD", event_time,
            value="revised after ISM confirmed", confidence="Certain", source="s2", predicted_direction="bullish",
            logged_at_utc=dt.datetime(2026, 9, 7, 10, 0, tzinfo=dt.timezone.utc),
        )

        row = get_latest_tier1_prediction_for_occurrence(conn, "PPI m/m", "XAUUSD", event_time)
        assert row.value == "revised after ISM confirmed"
        assert row.confidence == "Certain"
        assert row.predicted_direction == "bullish"
        conn.close()
    print("PASS\n")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_backtest_store.py -k tier1 -v`
Expected: FAIL with `ImportError: cannot import name 'record_tier1_prediction'` (or `AttributeError`, depending on how the import line was edited).

- [ ] **Step 3: Write the implementation**

In `scoring/backtest_store.py`, add the new table to `_SCHEMA` (append inside the existing triple-quoted string, after the `kalshi_reads` table definition, before the closing `"""`):

```sql
CREATE TABLE IF NOT EXISTS tier1_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence TEXT NOT NULL,
    source TEXT NOT NULL,
    predicted_direction TEXT NOT NULL,
    logged_at_utc TEXT NOT NULL
);
```

No migration function needed — this is a brand-new table (`CREATE TABLE IF NOT EXISTS` already handles both a fresh DB and an existing one that predates this table), unlike adding a column to an existing table.

Add the dataclass (near the existing `Prediction` dataclass, same file):

```python
@dataclass
class Tier1PredictionRow:
    id: int
    event_title: str
    instrument: str
    event_time_utc: str
    value: str
    confidence: str          # 'Certain' | 'Likely' | 'Guessing'
    source: str
    predicted_direction: str  # 'bullish' | 'bearish' | 'neutral' -- Direction enum's own string values
    logged_at_utc: str
```

Add the two functions (near `record_outcome()`/`get_latest_prediction_for_occurrence()`, same file):

```python
_VALID_TIER1_CONFIDENCE = ("Certain", "Likely", "Guessing")


def record_tier1_prediction(
    conn: sqlite3.Connection,
    event_title: str,
    instrument: str,
    event_time_utc: dt.datetime,
    value: str,
    confidence: str,
    source: str,
    predicted_direction: str,
    logged_at_utc: Optional[dt.datetime] = None,
) -> int:
    """
    Persists a Causation-Matrix Tier 1 prediction (scoring.backtest.Tier1Prediction)
    for one (event_title, instrument, event_time_utc) occurrence -- a
    human-researched value/confidence/source/predicted_direction, never
    auto-derived (see Tier1Prediction's own docstring). One row per
    instrument, same as record_prediction() -- a Tier 1 finding's raw
    value/confidence/source don't change per instrument, but
    predicted_direction can (XAUUSD is inverse-mapped, US30 is
    risk-sentiment-dampened), so each instrument gets its own row.

    confidence and predicted_direction are validated here, not just by
    callers -- same reasoning as record_outcome()'s Direction validation:
    an unrecognized value must never sit silently in the DB until
    something crashes on it much later, for every reader, not just the
    one bad write.
    """
    if confidence not in _VALID_TIER1_CONFIDENCE:
        raise ValueError(
            f"confidence={confidence!r} is not valid — must be one of: "
            f"{', '.join(_VALID_TIER1_CONFIDENCE)}"
        )
    try:
        Direction(predicted_direction)
    except ValueError:
        valid = ", ".join(d.value for d in Direction)
        raise ValueError(
            f"predicted_direction={predicted_direction!r} is not valid — must be one of: {valid}"
        )

    logged_at = logged_at_utc or dt.datetime.now(dt.timezone.utc)
    cursor = conn.execute(
        "INSERT INTO tier1_predictions (event_title, instrument, event_time_utc, value, "
        "confidence, source, predicted_direction, logged_at_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (event_title, instrument, event_time_utc.isoformat(), value, confidence, source,
         predicted_direction, logged_at.isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_latest_tier1_prediction_for_occurrence(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
) -> Optional[Tier1PredictionRow]:
    """
    Most recent Tier 1 prediction logged for this EXACT (event_title,
    instrument, event_time_utc) occurrence -- same occurrence-scoping
    reasoning as get_latest_prediction_for_occurrence(): a title recurs
    monthly with the SAME title but a DIFFERENT event_time_utc each time,
    so a title-only lookup would leak a prior occurrence's Tier 1 call
    onto an unrelated later one.
    """
    row = conn.execute(
        "SELECT * FROM tier1_predictions WHERE event_title = ? AND instrument = ? AND event_time_utc = ? "
        "ORDER BY logged_at_utc DESC, id DESC LIMIT 1",
        (event_title, instrument, event_time_utc.isoformat()),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    return Tier1PredictionRow(
        id=d["id"], event_title=d["event_title"], instrument=d["instrument"],
        event_time_utc=d["event_time_utc"], value=d["value"], confidence=d["confidence"],
        source=d["source"], predicted_direction=d["predicted_direction"],
        logged_at_utc=d["logged_at_utc"],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_backtest_store.py -k tier1 -v`
Expected: 6 passed

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `python -m pytest -q`
Expected: same pass count as before this task plus 6, no new failures (one pre-existing FinBERT-environment failure is possible depending on test order — this repo has no currently-known pre-existing failure as of the last full-suite run, so investigate anything unexpected rather than assuming it's pre-existing).

- [ ] **Step 6: Commit**

```bash
git add scoring/backtest_store.py tests/test_backtest_store.py
git commit -m "feat: add tier1_predictions table for live Causation-Matrix Tier 1 predictions"
```

---

### Task 2: Persist the two September 2026 cases

**Files:**
- Modify: `tests/run_causation_matrix_option_a_pending_sep2026.py`

**Interfaces:**
- Consumes: `scoring.backtest_store.record_tier1_prediction` (Task 1), the existing `TIER1_PPI_SEP2026`/`TIER1_CPI_SEP2026` `Tier1Prediction` objects and `PPI_EVENT_TIME_SEP2026`/`CPI_EVENT_TIME_SEP2026` datetimes already defined in this file.
- Produces: nothing consumed by a later task in this plan — this is the actual live data Task 3/4 will display, but Tasks 3/4 read it through Task 1's functions, not through this script directly.

- [ ] **Step 1: Extend the script to persist both cases, for both instruments**

Read the current file first — it already defines `TIER1_PPI_SEP2026`, `TIER1_CPI_SEP2026`, `PPI_EVENT_TIME_SEP2026`, `CPI_EVENT_TIME_SEP2026`, and an `if __name__ == "__main__":` block that only prints. Add the import and the persistence calls to that block (don't remove the existing print statements — keep them, they're still useful confirmation output):

```python
from scoring.backtest_store import get_connection, record_tier1_prediction
```

Add at the end of the existing `if __name__ == "__main__":` block, after the existing print statements:

```python
    conn = get_connection()
    for instrument in ("XAUUSD", "US30"):
        record_tier1_prediction(
            conn, "PPI m/m", instrument, PPI_EVENT_TIME_SEP2026,
            value=TIER1_PPI_SEP2026.value, confidence=TIER1_PPI_SEP2026.confidence,
            source=TIER1_PPI_SEP2026.source,
            predicted_direction=TIER1_PPI_SEP2026.predicted_direction.value,
        )
        record_tier1_prediction(
            conn, "CPI m/m", instrument, CPI_EVENT_TIME_SEP2026,
            value=TIER1_CPI_SEP2026.value, confidence=TIER1_CPI_SEP2026.confidence,
            source=TIER1_CPI_SEP2026.source,
            predicted_direction=TIER1_CPI_SEP2026.predicted_direction.value,
        )
    conn.close()
    print("Persisted both cases to scoring/backtest_log.db's tier1_predictions table (XAUUSD + US30).")
```

Note: `predicted_direction=TIER1_PPI_SEP2026.predicted_direction.value` — `Tier1Prediction.predicted_direction` is a `Direction` enum member (e.g. `Direction.BULLISH`), and `record_tier1_prediction()` takes a plain string (`Direction`'s own `.value`, e.g. `"bullish"`) — don't pass the enum member itself.

Both cases currently use the SAME `predicted_direction` for both instruments (`TIER1_PPI_SEP2026.predicted_direction` is one value, applied to both XAUUSD and US30 here) — this is a known simplification worth flagging, not a bug: the spec's per-instrument design exists because a Tier 1 call CAN differ by instrument (XAUUSD inverse vs US30 risk-sentiment-dampened), but neither `tests/run_causation_matrix_option_a_pending_sep2026.py`'s existing research nor this task re-derives a separate US30-specific direction — that would be new judgment-call work outside this plan's scope. Log it as a note in the ledger, not something to silently resolve by guessing a different value for US30.

- [ ] **Step 2: Run it and verify persistence**

Run: `python tests/run_causation_matrix_option_a_pending_sep2026.py`
Expected: the existing print output, followed by the new confirmation line. Then verify directly:

```bash
python -c "
from scoring.backtest_store import get_connection, get_latest_tier1_prediction_for_occurrence
import datetime as dt
conn = get_connection()
for title, instrument, event_time in [
    ('PPI m/m', 'XAUUSD', dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)),
    ('PPI m/m', 'US30', dt.datetime(2026, 9, 10, 12, 30, tzinfo=dt.timezone.utc)),
    ('CPI m/m', 'XAUUSD', dt.datetime(2026, 9, 11, 12, 30, tzinfo=dt.timezone.utc)),
    ('CPI m/m', 'US30', dt.datetime(2026, 9, 11, 12, 30, tzinfo=dt.timezone.utc)),
]:
    row = get_latest_tier1_prediction_for_occurrence(conn, title, instrument, event_time)
    print(title, instrument, '->', row.predicted_direction if row else None, row.confidence if row else None)
conn.close()
"
```

Expected output: all four rows present, PPI both instruments `bullish`/`Certain`, CPI both instruments `neutral`/`Guessing`.

Running this script twice is safe (idempotent in effect, not in row count) — `get_latest_tier1_prediction_for_occurrence()` always returns the most recently logged row for an occurrence, so a second run just adds a newer row with the same content; it doesn't corrupt anything. Not worth deduplicating for a 2-case, run-once script.

- [ ] **Step 3: Commit**

```bash
git add tests/run_causation_matrix_option_a_pending_sep2026.py
git commit -m "feat: persist September 2026 PPI/CPI Tier 1 predictions to the live table"
```

(This commit records the code change; the actual database rows it produces live in `scoring/backtest_log.db`, which is not committed to git — running the script is what makes the live dashboard task in this plan actually show something.)

---

### Task 3: `/api/predictions` integration

**Files:**
- Modify: `webapp/app.py`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `scoring.backtest_store.get_latest_tier1_prediction_for_occurrence` (Task 1).
- Produces: each event dict in the `/api/predictions` JSON response gains a new, always-present `tier1_prediction` field — `{"value": str, "confidence": str, "source": str, "predicted_direction": str} | null`.

- [ ] **Step 1: Write the failing test**

`tests/test_webapp_app.py` already has everything this needs (see the existing `test_predictions_route_flags_co_released_conflict_and_leaves_singleton_events_alone` test for the exact fixture conventions — `_seed_calendar`, `store.add_tracked_symbol`, `webapp_app.app.test_client()`). Add:

```python
def test_predictions_route_includes_tier1_prediction_for_logged_occurrence():
    print("=== app: /api/predictions includes tier1_prediction for an event with a logged Tier 1 row, null otherwise ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            ppi_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ)
            cpi_time = dt.datetime(2026, 9, 11, 12, 30, tzinfo=UTC_TZ)
            _seed_calendar(db_path, [
                EconomicEvent(title="PPI m/m", country="USD", impact="High",
                               event_time_utc=ppi_time, forecast="0.2%", previous="0.0%", actual=None),
                EconomicEvent(title="CPI m/m", country="USD", impact="High",
                               event_time_utc=cpi_time, forecast="0.3%", previous="-0.4%", actual=None),
            ])
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            conn.close()

            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time, 0.55, "bullish", 0.4, 60, False,
            )
            backtest_store.record_tier1_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time,
                value="Muted, non-reaccelerating call", confidence="Certain",
                source="BLS July 2026 PPI release; ISM Manufacturing Prices Paid Aug 2026",
                predicted_direction="bullish",
            )
            backtest_store.record_prediction(
                bconn, "CPI m/m", "XAUUSD", cpi_time, 0.51, "neutral", 0.05, 70, False,
            )
            # No tier1_predictions row logged for CPI -- must read back as null.
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = resp.get_json()["predictions"][0]["events"]
            by_title = {e["event_title"]: e for e in events}

            assert by_title["PPI m/m"]["tier1_prediction"] == {
                "value": "Muted, non-reaccelerating call",
                "confidence": "Certain",
                "source": "BLS July 2026 PPI release; ISM Manufacturing Prices Paid Aug 2026",
                "predicted_direction": "bullish",
            }
            assert by_title["CPI m/m"]["tier1_prediction"] is None
    print("PASS\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_webapp_app.py -k test_predictions_route_includes_tier1_prediction -v`
Expected: FAIL — `KeyError: 'tier1_prediction'` (field doesn't exist yet).

- [ ] **Step 3: Write the implementation**

In `webapp/app.py`, add the import (alongside the existing `from scoring.backtest_store import (...)` block at the top of the file — add `get_latest_tier1_prediction_for_occurrence` to that existing import list):

```python
from scoring.backtest_store import (
    get_connection as get_backtest_connection, get_latest_two_predictions,
    get_latest_print_prediction, get_latest_kalshi_read, get_last_check_utc,
    get_latest_tier1_prediction_for_occurrence,
    Prediction,
    get_prediction_history as get_article_prediction_history,
)
```

Inside `get_predictions()`'s per-event loop, right after the existing `kalshi_read` block (`webapp/app.py:409-416`, ending with the `kalshi_read = {...}` assignment) and before the inclusion guard (`webapp/app.py:418` `if (latest is None and recomputed is None and ...)`), add:

```python
            tier1_row = get_latest_tier1_prediction_for_occurrence(backtest_conn, event["title"], ticker, event_time)
            tier1_prediction = None
            if tier1_row is not None:
                tier1_prediction = {
                    "value": tier1_row.value,
                    "confidence": tier1_row.confidence,
                    "source": tier1_row.source,
                    "predicted_direction": tier1_row.predicted_direction,
                }
```

Extend the inclusion guard so a Tier 1-only signal can't be silently dropped (same reasoning the guard's own comment already gives for `trend_signal`/`kalshi_read`):

```python
            if (latest is None and recomputed is None and article_prediction is None and print_prediction is None
                    and trend_signal is None and kalshi_read is None and tier1_prediction is None):
                continue
```

Add the new field to the `entry["events"].append({...})` dict (`webapp/app.py:438-453`), as a sibling of `kalshi_read`:

```python
            entry["events"].append({
                "event_title": event["title"],
                "event_time_utc": event["event_time_utc"],
                "probability": probability_value,
                "direction": direction_value,
                "recomputed_from_event_history": recomputed is not None,
                "previous_probability": previous.probability if previous else None,
                "previous_direction": previous.direction if previous else None,
                "article_count": accumulator_prediction.article_count if accumulator_prediction else None,
                "article_prediction": article_prediction,
                "article_prediction_conflict": None,
                "previous_article_prediction": previous_article_prediction,
                "print_prediction": print_prediction,
                "trend_signal": trend_signal,
                "kalshi_read": kalshi_read,
                "tier1_prediction": tier1_prediction,
            })
```

Note: this task does NOT touch the reconciliation loop further down (`webapp/app.py:455` onward, the `for time_key, predictions_by_title in accumulator_predictions_by_time_and_title.items():` block) — that loop only ever overwrites `article_prediction`/`article_prediction_conflict`, never `tier1_prediction`, and this plan's Global Constraints explicitly forbid adding any agree/disagree computation to the live path. Leave that loop exactly as it is.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_webapp_app.py -v`
Expected: all pass, including the new test.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: same pass count as Task 1 Step 5 plus the new test(s), no new failures.

- [ ] **Step 6: Commit**

```bash
git add webapp/app.py tests/test_webapp_app.py
git commit -m "feat: surface tier1_prediction in /api/predictions"
```

---

### Task 4: Frontend rendering

**Files:**
- Modify: `webapp/static/app.js`
- Modify: `webapp/static/style.css`

**Interfaces:**
- Consumes: the new `tier1_prediction` field on each `events[]` entry from `/api/predictions` (Task 3) — shape `{"value": string, "confidence": string, "source": string, "predicted_direction": string} | null`.
- Produces: nothing consumed elsewhere in this plan — terminal, user-visible piece.

- [ ] **Step 1: Add `tier1PredictionHtml()` and wire it into the card**

In `webapp/static/app.js`, locate `articlePredictionLine`'s assignment (`webapp/static/app.js:324-326`, currently `const articlePredictionLine = next.article_prediction ? articlePredictionHtml(...) : articlePredictionConflictHtml(...)`). Add the new function immediately after that assignment, and a new line variable right after it:

```javascript
  // tier1_prediction (2026-09-07): a Causation-Matrix Tier 1 causation-
  // matrix prediction for this exact occurrence, if one has been
  // manually researched and logged (webapp/reconciliation.py has no
  // role here -- this is a separate, independently-populated signal,
  // currently CPI/PPI only). Rendered directly beneath whatever the
  // sentiment line above already shows, using the SAME bullish/bearish/
  // neutral color classes -- shared color language is what makes "do
  // these two calls visually agree" readable at a glance, deliberately
  // without any computed agree/disagree badge (that stays a
  // backtest-only concept, scoring/backtest.py's BacktestReport.
  // agreement_rate() -- never live). confidence is rendered as its own
  // plain text tag (Certain/Likely/Guessing), never turned into a
  // percentage or a bar -- doing that would recreate exactly the
  // flattening Tier1Prediction's own design exists to avoid.
  function tier1PredictionHtml(tier1) {
    if (!tier1) return '';
    const dClass = directionClass(tier1.predicted_direction);
    return `<div class="tier1-prediction ${dClass}">
      🧮 Tier 1: <b>${directionLabel(tier1.predicted_direction)}</b>
      <span style="font-size:12px;color:#888">(${escapeHtml(tier1.confidence)})</span>
      <div style="font-size:12px;margin-top:4px">${escapeHtml(tier1.value)}</div>
      <div style="font-size:11px;color:#888;margin-top:2px">${escapeHtml(tier1.source)}</div>
    </div>`;
  }
  const tier1PredictionLine = tier1PredictionHtml(next.tier1_prediction);
```

Then update the two places `articlePredictionLine` is interpolated into the card's template string so `tier1PredictionLine` renders directly after it in both (the pending-branch template and the resolved/gauge-branch template — search for `${articlePredictionLine}` to find both; there are two occurrences per the existing code, one feeding `hasAnySignal`'s combined check around `webapp/static/app.js:448`, one in a template around `webapp/static/app.js:494`):

```javascript
${articlePredictionLine}${tier1PredictionLine}${printPredictionLine}${kalshiReadLine}${trendSignalLine}${otherEventsLine}
```

and

```javascript
${articlePredictionLine}${tier1PredictionLine}${printPredictionLine}${kalshiReadLine}</div></div>
```

(matching each template's own existing trailing content exactly — only insert `${tier1PredictionLine}` immediately after `${articlePredictionLine}` in each, don't otherwise change either line.)

Also extend `hasAnySignal`'s combined check (`webapp/static/app.js:448`, currently `const hasAnySignal = articlePredictionLine || printPredictionLine || kalshiReadLine || trendSignalLine;`) so a Tier 1-only signal doesn't get hidden behind the "no signal" heading:

```javascript
    const hasAnySignal = articlePredictionLine || tier1PredictionLine || printPredictionLine || kalshiReadLine || trendSignalLine;
```

- [ ] **Step 2: Add the CSS rule**

In `webapp/static/style.css`, add immediately after the existing `.article-prediction-conflict` rule (`webapp/static/style.css:83`, before `.other-events` at line 85):

```css
.tier1-prediction { margin-top: 8px; padding: 8px 10px; border-radius: 8px; font-size: 13px; text-align: center; }
.tier1-prediction.bullish { background: rgba(46, 125, 50, 0.10); color: var(--bullish); border: 1px solid rgba(46, 125, 50, 0.3); }
.tier1-prediction.bearish { background: rgba(198, 40, 40, 0.10); color: var(--bearish); border: 1px solid rgba(198, 40, 40, 0.3); }
.tier1-prediction.neutral { background: rgba(136, 136, 136, 0.10); color: var(--neutral); border: 1px solid rgba(136, 136, 136, 0.3); }
```

(Identical palette to `.article-prediction`'s own three modifiers, on purpose — this is the shared color language the design relies on.)

- [ ] **Step 3: Verify live in the browser**

This codebase has no JS/CSS automated test suite — verify by hand, same pattern used for the reconciliation feature's own frontend task:

1. Ensure Task 2's script has actually been run against the live, currently-running supervised dashboard's own database (not just a temp test DB) — re-run `python tests/run_causation_matrix_option_a_pending_sep2026.py` from the project root if it hasn't been, so `scoring/backtest_log.db` (the real file the running `webapp/app.py` reads) has the four real rows.
2. Navigate to the dashboard's root page.
3. Find the XAUUSD and US30 cards. If PPI m/m or CPI m/m (the September 2026 occurrences) are currently featured or listed under "N more events at this time," confirm the new 🧮 Tier 1 line renders directly beneath the 📰 sentiment line (or beneath the conflict badge, if that event is part of a co-released conflict), with the right color (green for the PPI case's bullish call, gray for the CPI case's neutral/no-confident-call) and the right text (value + confidence tag + source).
4. Confirm an unrelated event elsewhere on the page (no logged Tier 1 row) shows no Tier 1 line at all — not an empty box, nothing.
5. Take a screenshot as evidence.

- [ ] **Step 4: Commit**

```bash
git add webapp/static/app.js webapp/static/style.css
git commit -m "feat: render Tier 1 predictions on the dashboard, under sentiment's own call"
```

---

### Task 5: Final verification against the Global Constraints

**Files:** none created or modified — verification only.

**Interfaces:** none.

- [ ] **Step 1: Confirm History tab is unaffected**

Run: `python -m pytest tests/test_webapp_history.py -v`
Expected: all pass, unchanged pass count from before this plan (no task above touches `webapp/history.py`).

- [ ] **Step 2: Confirm no agree/disagree computation was added anywhere on the live path**

Run: `git diff --stat <BASE> -- scoring/backtest.py webapp/reconciliation.py` (where `<BASE>` is the commit before Task 1's — find it with `git log --oneline` and locate the last commit before this plan started).
Expected: empty output — zero lines changed in either file across every commit this plan made. `BacktestReport.agreement_rate()` and `reconcile_group()` must be byte-for-byte unchanged.

- [ ] **Step 3: Confirm the four real rows are actually live**

Run the verification snippet from Task 2 Step 2 again, against the real (non-test) `scoring/backtest_log.db` — confirm all four rows are still present and correct.

- [ ] **Step 4: Run the full test suite one final time**

Run: `python -m pytest -q`
Expected: same known-good pass count as Task 3 Step 5, no new failures.

- [ ] **Step 5: No commit needed for this task** — verification only. If Step 2 finds an unexpected diff, STOP and treat it as a plan violation to fix before considering this plan complete.
