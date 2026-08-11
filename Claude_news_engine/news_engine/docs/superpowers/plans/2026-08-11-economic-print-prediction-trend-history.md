# Economic-Print Prediction + Trend History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two additive, display-oriented features: an explicit "will this
print beat/miss forecast" call from the accumulator's articles, and durable
forecast/previous/actual history per event series so a trend (e.g. "CPI beat
forecast 3 of last 4") can be shown.

**Architecture:** Two new SQLite tables, one per pipeline that already owns
the relevant data source — `event_history` in `webapp/store.py` (populated by
`webapp/scheduler.py`'s existing fetch cycle, every event regardless of
impact) and `print_predictions` in `scoring/backtest_store.py` (populated by
`scoring/backtest_accumulator.py`'s existing per-event cycle, High-impact USD
only, reusing the article bundle already fetched for `score_bundle()`). A new
small lexicon-based classifier (`scoring/print_direction.py`, same shape as
`scoring/sentiment.py`) produces the print-direction call. Two dashboard
additions: a print-call badge next to the existing article-based read, and a
collapsible per-event "History" panel backed by a new `/api/event_history`
route. Nothing in `score_bundle()`, `_is_material_change()`,
`usd_surprise_score()`, or any existing table changes.

**Tech Stack:** Python 3.14, Flask, SQLite (stdlib `sqlite3`), vanilla JS
(`webapp/static/app.js`) — matches the existing stack, no new dependencies.

## Global Constraints

- Never fabricate a value: missing/unmappable/unparseable data always
  produces `None`/`NULL`/an omitted UI element, never a guessed default.
- `db_path` is always resolved inside a function body (not a default arg
  value), so tests can `patch.object(module, "DB_PATH", tmp_path)`.
- `conn.row_factory = sqlite3.Row` and `executescript(_SCHEMA)` on every
  `get_connection()` call, matching `webapp/store.py` and
  `scoring/backtest_store.py`'s existing pattern.
- `EVENT_HISTORY_IN_LINE_TOLERANCE = 0.05` (5%) — the threshold below which
  an actual-vs-forecast `pct_diff` counts as `'in_line'` rather than
  `'higher'`/`'lower'`.
- Initial `PRINT_SURPRISE_LEXICON` coverage is exactly 4 events: `CPI m/m`,
  `Core CPI m/m`, `Non-Farm Employment Change`, `Unemployment Rate`. No other
  titles get a lexicon entry in this plan.
- `record_check()`/`count_recent_checks()`/`DAILY_CHECK_BUDGET_THRESHOLD`
  (the accumulator's existing article-fetch budget guard) are untouched —
  the new print-direction call reuses the bundle already fetched for
  `score_bundle()`, so it adds zero extra article-fetch cost and must not be
  logged as a separate check.

---

### Task 1: `classify_surprise()` — literal actual-vs-forecast classification

**Files:**
- Modify: `config/settings.py` (add `EVENT_HISTORY_IN_LINE_TOLERANCE`, near `SURPRISE_SENSITIVITY` at line 214)
- Modify: `data_layer/calendar_feed.py` (add `classify_surprise()` function, near `usd_surprise_score()` at line 78-108)
- Test: `tests/test_calendar_feed.py`

**Interfaces:**
- Consumes: `EconomicEvent` (existing, `data_layer/calendar_feed.py`),
  `_parse_numeric()` (existing, same file), `EVENT_SURPRISE_DIRECTION`
  (existing, `config/settings.py`).
- Produces: `classify_surprise(event: EconomicEvent) -> Optional[str]` —
  returns `'higher'`, `'lower'`, `'in_line'`, or `None`. Task 2 imports this.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_calendar_feed.py` (append at end of file, before any
`if __name__ ==` block — check the file's current ending first with `tail -5
tests/test_calendar_feed.py` and insert before it):

```python
def test_classify_surprise_higher_when_actual_above_forecast():
    print("=== classify_surprise: actual clearly above forecast returns 'higher' ===")
    event = EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", actual="0.5%",
    )
    assert classify_surprise(event) == "higher"
    print("PASS\n")


def test_classify_surprise_lower_when_actual_below_forecast():
    print("=== classify_surprise: actual clearly below forecast returns 'lower' ===")
    event = EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.5%", actual="0.2%",
    )
    assert classify_surprise(event) == "lower"
    print("PASS\n")


def test_classify_surprise_in_line_within_tolerance():
    print("=== classify_surprise: a tiny delta within EVENT_HISTORY_IN_LINE_TOLERANCE returns 'in_line' ===")
    event = EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.40%", actual="0.41%",  # 2.5% relative delta, well under the 5% tolerance
    )
    assert classify_surprise(event) == "in_line"
    print("PASS\n")


def test_classify_surprise_none_when_title_not_tracked():
    print("=== classify_surprise: an event title outside EVENT_SURPRISE_DIRECTION returns None, never guessed ===")
    event = EconomicEvent(
        title="Some Untracked Indicator", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", actual="0.5%",
    )
    assert classify_surprise(event) is None
    print("PASS\n")


def test_classify_surprise_none_when_forecast_or_actual_missing():
    print("=== classify_surprise: missing forecast or actual returns None, not a fabricated guess ===")
    event = EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="0.3%", actual=None,
    )
    assert classify_surprise(event) is None
    print("PASS\n")


def test_classify_surprise_is_literal_not_bullish_bearish():
    print("=== classify_surprise: 'higher' means actual > forecast literally, independent of USD-bullish/bearish direction ===")
    # Unemployment Rate is 'higher_bearish' in EVENT_SURPRISE_DIRECTION (a
    # higher actual is USD-bearish) — but classify_surprise must still say
    # 'higher' here, since actual DID come in above forecast. Conflating the
    # two would silently invert the displayed history for bearish-mapped
    # indicators.
    event = EconomicEvent(
        title="Unemployment Rate", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
        forecast="4.0%", actual="4.3%",
    )
    assert classify_surprise(event) == "higher"
    print("PASS\n")
```

Also update the test file's imports at the top (check current imports with
`head -20 tests/test_calendar_feed.py` — add `classify_surprise` to the
existing `from data_layer.calendar_feed import ...` line).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_calendar_feed.py`
Expected: `NameError` or `ImportError` — `classify_surprise` doesn't exist yet.

- [ ] **Step 3: Add the constant to `config/settings.py`**

Insert immediately after the `SURPRISE_SENSITIVITY = 3.0` line (currently
line 214):

```python

# Below this relative (or, when forecast≈0, absolute) delta between actual
# and forecast, classify_surprise() below calls it 'in_line' rather than
# 'higher'/'lower' — a literal actual-vs-forecast comparison for event
# history/trend display, distinct from usd_surprise_score()'s continuous
# bullish/bearish-mapped magnitude used for instrument-score blending.
EVENT_HISTORY_IN_LINE_TOLERANCE = 0.05
```

- [ ] **Step 4: Implement `classify_surprise()` in `data_layer/calendar_feed.py`**

Add the import (modify the existing `from config.settings import (...)` block
at lines 39-45 to include the new constant):

```python
from config.settings import (
    EVENT_HISTORY_IN_LINE_TOLERANCE,
    EVENT_SURPRISE_DIRECTION,
    LOCAL_TZ,
    PRE_EVENT_WINDOW_HOURS,
    PRECURSOR_EVENTS,
    SURPRISE_SENSITIVITY,
    UTC_TZ,
)
```

Add the function immediately after `usd_surprise_score()` (after line 108,
before `def __repr__`) — as a **module-level function**, not a method (unlike
`usd_surprise_score()`, this doesn't need `self`, but for consistency with
call sites that already have an `EconomicEvent` in hand, define it as a
free function taking the event as its argument):

```python
def classify_surprise(event: "EconomicEvent") -> Optional[str]:
    """
    Literal actual-vs-forecast comparison for this event — "did the print
    come in above, below, or in line with what was forecast." Distinct
    from usd_surprise_score()'s USD-bullish/bearish-mapped magnitude:
    that answers "was this good or bad for the dollar," this answers "was
    the number itself higher or lower than expected," which for a
    'higher_bearish' indicator (e.g. Unemployment Rate) point in OPPOSITE
    directions from the bullish/bearish read.

    Reuses EVENT_SURPRISE_DIRECTION only as an is-this-title-tracked gate
    (same set of titles usd_surprise_score() recognizes) — not for its
    higher_bullish/higher_bearish values, which don't apply here.

    Returns 'higher', 'lower', 'in_line', or None — never a fabricated
    guess — when the title isn't tracked or forecast/actual don't parse.
    """
    if event.title not in EVENT_SURPRISE_DIRECTION:
        return None

    forecast = _parse_numeric(event.forecast)
    actual = _parse_numeric(event.actual)
    if forecast is None or actual is None:
        return None

    if abs(forecast) > 1e-9:
        pct_diff = (actual - forecast) / abs(forecast)
    else:
        pct_diff = actual - forecast

    if abs(pct_diff) <= EVENT_HISTORY_IN_LINE_TOLERANCE:
        return "in_line"
    return "higher" if pct_diff > 0 else "lower"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python tests/test_calendar_feed.py`
Expected: all tests PASS, including the 6 new ones.

- [ ] **Step 6: Run the full existing regression suite for this file**

Run: `python tests/test_calendar_feed.py` (same command — this file has no
`__main__` registration issue since Task steps above already added the new
tests to the file; if the file uses a `pytest`-discovered style instead of an
`if __name__ == "__main__":` block, run `python -m pytest
tests/test_calendar_feed.py -v` instead — check the file's ending first).
Expected: PASS, no regressions in the existing 3 tests.

- [ ] **Step 7: Commit**

```bash
git add config/settings.py data_layer/calendar_feed.py tests/test_calendar_feed.py
git commit -m "feat: add classify_surprise() for literal actual-vs-forecast comparison

New EVENT_HISTORY_IN_LINE_TOLERANCE constant + classify_surprise()
function, laying the groundwork for event_history's surprise_direction
column (Task 2). Deliberately separate from usd_surprise_score()'s
bullish/bearish-mapped magnitude — this is a literal higher/lower/
in_line comparison, which points opposite the bullish/bearish read for
'higher_bearish' indicators like Unemployment Rate."
```

---

### Task 2: `event_history` table + capture in `webapp/scheduler.py`

**Files:**
- Modify: `webapp/store.py` (add `event_history` table, `upsert_event_history()`, `get_event_history()`)
- Modify: `webapp/scheduler.py` (call `upsert_event_history()` per event, every cycle)
- Test: `tests/test_webapp_store.py`, `tests/test_webapp_scheduler.py`

**Interfaces:**
- Consumes: `classify_surprise()` (Task 1, `data_layer.calendar_feed`),
  `EconomicEvent` (existing), `get_connection()` (existing,
  `webapp/store.py`).
- Produces: `upsert_event_history(conn, event: EconomicEvent, surprise_direction: Optional[str], now: dt.datetime) -> None` and
  `get_event_history(conn, event_title: str, limit: int = 6) -> list[EventHistoryRow]` where
  `EventHistoryRow` is a new dataclass with fields
  `event_title: str, event_time_utc: str, forecast: Optional[str], previous: Optional[str], actual: Optional[str], surprise_direction: Optional[str]`.
  Task 5 (UI) and Task 6 (`/api/event_history`) consume `get_event_history()`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_webapp_store.py` (append before the file's `__main__`
block — check with `grep -n "if __name__" tests/test_webapp_store.py`):

```python
def test_upsert_event_history_creates_row_on_first_sight():
    print("=== store: upsert_event_history creates a row with forecast/previous, actual still NULL, on first sight ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
            forecast="0.3%", previous="0.4%", actual=None,
        )
        now = dt.datetime(2026, 8, 5, 9, 0, tzinfo=UTC_TZ)
        store.upsert_event_history(conn, event, surprise_direction=None, now=now)

        rows = store.get_event_history(conn, "CPI m/m")
        assert len(rows) == 1
        assert rows[0].forecast == "0.3%"
        assert rows[0].previous == "0.4%"
        assert rows[0].actual is None
        assert rows[0].surprise_direction is None
        conn.close()
    print("PASS\n")


def test_upsert_event_history_fills_actual_on_later_sight_without_clobbering_forecast():
    print("=== store: a later upsert (post-release) fills actual/surprise_direction, leaves forecast/previous untouched ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        pre_event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
            forecast="0.3%", previous="0.4%", actual=None,
        )
        store.upsert_event_history(conn, pre_event, surprise_direction=None, now=dt.datetime(2026, 8, 5, 9, 0, tzinfo=UTC_TZ))

        post_event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
            forecast="0.3%", previous="0.4%", actual="0.5%",
        )
        store.upsert_event_history(conn, post_event, surprise_direction="higher", now=dt.datetime(2026, 8, 12, 13, 0, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "CPI m/m")
        assert len(rows) == 1
        assert rows[0].forecast == "0.3%"
        assert rows[0].previous == "0.4%"
        assert rows[0].actual == "0.5%"
        assert rows[0].surprise_direction == "higher"
        conn.close()
    print("PASS\n")


def test_upsert_event_history_stale_refetch_does_not_blank_actual():
    print("=== store: a stale re-fetch with actual=None never blanks a previously-recorded actual ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        released = EconomicEvent(
            title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
            forecast="0.3%", previous="0.4%", actual="0.5%",
        )
        store.upsert_event_history(conn, released, surprise_direction="higher", now=dt.datetime(2026, 8, 12, 13, 0, tzinfo=UTC_TZ))

        stale_refetch = EconomicEvent(
            title="CPI m/m", country="USD", impact="High", event_time_utc=event_time,
            forecast="0.3%", previous="0.4%", actual=None,
        )
        store.upsert_event_history(conn, stale_refetch, surprise_direction=None, now=dt.datetime(2026, 8, 12, 13, 5, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "CPI m/m")
        assert rows[0].actual == "0.5%"
        assert rows[0].surprise_direction == "higher"
        conn.close()
    print("PASS\n")


def test_get_event_history_multiple_occurrences_most_recent_first_and_limit():
    print("=== store: get_event_history returns occurrences most-recent-first, capped at limit ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        for month, actual in [(6, "0.5%"), (7, "0.4%"), (8, "0.6%")]:
            event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                forecast="0.3%", previous="0.3%", actual=actual,
            )
            store.upsert_event_history(conn, event, surprise_direction="higher", now=dt.datetime(2026, month, 12, 13, 0, tzinfo=UTC_TZ))

        rows = store.get_event_history(conn, "CPI m/m", limit=2)
        assert len(rows) == 2
        assert rows[0].event_time_utc.startswith("2026-08")
        assert rows[1].event_time_utc.startswith("2026-07")
        conn.close()
    print("PASS\n")


def test_get_event_history_unknown_title_returns_empty_list():
    print("=== store: get_event_history for a title with no history returns an empty list, not an error ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        rows = store.get_event_history(conn, "Nonexistent Event")
        assert rows == []
        conn.close()
    print("PASS\n")
```

Check `tests/test_webapp_store.py`'s existing imports (`head -20
tests/test_webapp_store.py`) — add `from data_layer.calendar_feed import
EconomicEvent` and `from config.settings import UTC_TZ` if not already
present (they likely are, since other tests in this file construct
`EconomicEvent`s — verify before adding to avoid a duplicate import).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_store.py`
Expected: `AttributeError: module 'webapp.store' has no attribute 'upsert_event_history'`

- [ ] **Step 3: Add the schema, dataclass, and functions to `webapp/store.py`**

Modify `_SCHEMA` (add after the `calendar_snapshot` table definition, before
the closing `"""`):

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
    UNIQUE(event_title, event_time_utc)
);
```

Add the dataclass (after `CalendarSnapshot`):

```python
@dataclass
class EventHistoryRow:
    event_title: str
    event_time_utc: str
    forecast: Optional[str]
    previous: Optional[str]
    actual: Optional[str]
    surprise_direction: Optional[str]
```

Add the two functions (at the end of the file):

```python
def upsert_event_history(
    conn: sqlite3.Connection,
    event,  # EconomicEvent — duck-typed, same reasoning as _event_to_dict()
    surprise_direction: Optional[str],
    now: dt.datetime,
) -> None:
    """
    Records this event occurrence's forecast/previous, filling in
    actual/surprise_direction once available without ever blanking a
    previously-recorded actual on a later, stale re-fetch that hasn't
    caught up yet (the `WHERE excluded.actual IS NOT NULL` guard below —
    SQLite's ON CONFLICT DO UPDATE has no per-column conditional syntax,
    so the WHERE clause on the whole UPDATE governs whether the actual/
    surprise_direction pair updates at all; forecast/previous are
    harmless to re-write identically every time since they don't change
    after an event first appears on the calendar).
    """
    conn.execute(
        """
        INSERT INTO event_history
            (event_title, event_time_utc, forecast, previous, actual, surprise_direction, recorded_at_utc, updated_at_utc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_title, event_time_utc) DO UPDATE SET
            actual = excluded.actual,
            surprise_direction = excluded.surprise_direction,
            updated_at_utc = excluded.updated_at_utc
        WHERE excluded.actual IS NOT NULL
        """,
        (
            event.title, event.event_time_utc.isoformat(), event.forecast, event.previous,
            event.actual, surprise_direction, now.isoformat(), now.isoformat(),
        ),
    )
    conn.commit()


def get_event_history(conn: sqlite3.Connection, event_title: str, limit: int = 6) -> list[EventHistoryRow]:
    """Past occurrences of this event title, most recent first, capped at `limit`. Empty list if none recorded yet."""
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction "
        "FROM event_history WHERE event_title = ? ORDER BY event_time_utc DESC LIMIT ?",
        (event_title, limit),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_store.py`
Expected: all tests PASS, including the 5 new ones.

- [ ] **Step 5: Wire capture into `webapp/scheduler.py`**

Modify the import block (currently lines 15-19) to add `classify_surprise`
and the two new store functions:

```python
from config.settings import EVENT_SURPRISE_DIRECTION
from data_layer.calendar_feed import EconomicEvent, classify_surprise, fetch_calendar, filter_relevant_events
from webapp.scoring_service import score_event_for_symbol
from webapp.store import (
    get_connection, record_run, get_latest_two, save_calendar_snapshot_if_changed, upsert_event_history,
)
from webapp.symbols import classify_symbol, UnrecognizedSymbolError
```

In `run_scoring_cycle()`, immediately after the existing
`save_calendar_snapshot_if_changed(conn, events, dt.datetime.now(dt.timezone.utc))`
line, add:

```python
    now_for_history = dt.datetime.now(dt.timezone.utc)
    for event in events:
        upsert_event_history(conn, event, classify_surprise(event), now_for_history)
```

(This iterates `events` — the `filter_relevant_events(all_events,
min_impact="Medium")` result already computed above, matching the design's
"every event the dashboard sees, not just what the accumulator scores.")

- [ ] **Step 6: Write the failing scheduler test**

Add to `tests/test_webapp_scheduler.py` (check existing imports/helpers with
`head -30 tests/test_webapp_scheduler.py` first, reuse whatever event-fetch
mocking pattern the existing `run_scoring_cycle` tests use):

```python
def test_run_scoring_cycle_records_event_history_for_every_event():
    print("=== scheduler: run_scoring_cycle records event_history for every fetched event, not just tracked-symbol matches ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ),
            forecast="0.3%", previous="0.4%", actual=None,
        )
        with patch.object(scheduler, "fetch_calendar", return_value=[event]), \
             patch.object(store, "DB_PATH", db_path):
            scheduler.run_scoring_cycle(["XAUUSD"], db_path=db_path)

        conn = store.get_connection(db_path)
        rows = store.get_event_history(conn, "CPI m/m")
        assert len(rows) == 1
        assert rows[0].forecast == "0.3%"
        conn.close()
    print("PASS\n")
```

Register it in the file's `__main__` block (find with `grep -n "if
__name__" tests/test_webapp_scheduler.py`) alongside the other
`run_scoring_cycle` tests.

- [ ] **Step 7: Run test to verify it fails, then implement, then verify it passes**

Run: `python tests/test_webapp_scheduler.py`
Expected before Step 5's implementation: fails (no `event_history` rows).
After Step 5 is done (it already is, from above) and this test is added: run
again, expect PASS.

- [ ] **Step 8: Run the full regression sweep for touched files**

```bash
python tests/test_webapp_store.py
python tests/test_webapp_scheduler.py
```

Expected: all PASS, no regressions.

- [ ] **Step 9: Commit**

```bash
git add webapp/store.py webapp/scheduler.py tests/test_webapp_store.py tests/test_webapp_scheduler.py
git commit -m "feat: persist event_history (forecast/previous/actual) across calendar rollovers

New event_history table in webapp/store.py, upserted by
webapp/scheduler.py's existing fetch cycle for every event it sees
(all impact levels, all symbols — same broad coverage the dashboard
already has, no article cost). First sight records forecast/previous;
a later sight fills actual/surprise_direction once released, without
ever blanking a previously-recorded actual on a stale re-fetch.

This is the durable per-event-series storage the engine's core spec
described but never had — 'July CPI was @4.2%, came in at 4.5%...'
is now a queryable row, not lost the moment the weekly calendar
rolls over."
```

---

### Task 3: `PRINT_SURPRISE_LEXICON` + `scoring/print_direction.py`

**Files:**
- Modify: `config/settings.py` (add `PRINT_SURPRISE_LEXICON`, near `EVENT_SURPRISE_DIRECTION`)
- Create: `scoring/print_direction.py`
- Test: `tests/test_print_direction.py` (new file)

**Interfaces:**
- Consumes: `NewsArticle` (existing, `data_layer/news_feed.py` — `.title`,
  `.summary` fields), `EventNewsBundle` (existing,
  `data_layer/event_context.py` — `.articles`, `.event` fields).
- Produces: `PrintCall` dataclass (`direction: str, confidence: float,
  article_count: int`) and `score_print_direction(bundle: EventNewsBundle) ->
  Optional[PrintCall]`. Task 4 imports this.

- [ ] **Step 1: Add the lexicon to `config/settings.py`**

Insert immediately after the `EVENT_SURPRISE_DIRECTION = { ... }` dict closes
(currently ends around line 188, right before the `PRECURSOR_TRUST_WEIGHT`
comment block):

```python

# Phrase-based lexicon for scoring/print_direction.py's print-surprise call
# — "will THIS release come in higher or lower than forecast," derived from
# article language, distinct from scoring/sentiment.py's general USD-
# directional lexicon. Only the 4 highest-traffic events (from
# EVENT_SURPRISE_DIRECTION) get an entry for this first pass; an event
# title with no entry here always returns None from score_print_direction()
# — never a guessed call. Adding coverage for another event later is a
# config-only change here, no code changes required.
PRINT_SURPRISE_LEXICON = {
    "CPI m/m": {
        "higher": ["sticky inflation", "hotter than expected", "upside surprise", "inflation accelerat"],
        "lower": ["cooling inflation", "softer than expected", "downside surprise", "disinflation"],
    },
    "Core CPI m/m": {
        "higher": ["sticky core inflation", "hotter than expected", "upside surprise"],
        "lower": ["cooling", "softer than expected", "downside surprise"],
    },
    "Non-Farm Employment Change": {
        "higher": ["blowout jobs", "stronger than expected", "beat estimates", "hot jobs report"],
        "lower": ["weaker than expected", "missed estimates", "soft jobs report", "payrolls disappoint"],
    },
    "Unemployment Rate": {
        "higher": ["rate ticks up", "unemployment rises", "labor market cooling"],
        "lower": ["rate ticks down", "unemployment falls", "labor market tightening"],
    },
}
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_print_direction.py`:

```python
"""
Tests for scoring/print_direction.py — the print-surprise lexicon
classifier ("will this release come in higher/lower than forecast,"
distinct from scoring/sentiment.py's general USD-directional lexicon).
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle
from data_layer.news_feed import NewsArticle
from scoring.print_direction import score_print_direction, PrintCall


def _article(title, summary="", published_hours_ago=2, now=None):
    now = now or dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
    return NewsArticle(
        title=title, summary=summary, source="Test Wire", source_type="test",
        published_utc=now - dt.timedelta(hours=published_hours_ago),
        url="https://example.test/a",
    )


def _bundle(event_title, articles, now=None):
    now = now or dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
    event = EconomicEvent(
        title=event_title, country="USD", impact="High",
        event_time_utc=now, forecast="0.3%", previous="0.3%",
    )
    return EventNewsBundle(event=event, articles=articles, as_of_utc=now)


def test_no_lexicon_entry_returns_none():
    print("=== score_print_direction: an event title with no PRINT_SURPRISE_LEXICON entry returns None ===")
    bundle = _bundle("Some Untracked Indicator", [_article("Hotter than expected inflation data")])
    assert score_print_direction(bundle) is None
    print("PASS\n")


def test_unanimous_higher_hits_high_confidence():
    print("=== score_print_direction: all articles hitting 'higher' phrases returns HIGHER with high confidence ===")
    bundle = _bundle("CPI m/m", [
        _article("Economists warn of sticky inflation ahead of CPI"),
        _article("Analysts see upside surprise risk for CPI print"),
    ])
    call = score_print_direction(bundle)
    assert call is not None
    assert call.direction == "higher"
    assert call.confidence > 0.5
    assert call.article_count == 2
    print("PASS\n")


def test_unanimous_lower_hits():
    print("=== score_print_direction: all articles hitting 'lower' phrases returns LOWER ===")
    bundle = _bundle("CPI m/m", [
        _article("Signs of cooling inflation build ahead of report"),
        _article("Disinflation trend expected to continue"),
    ])
    call = score_print_direction(bundle)
    assert call.direction == "lower"
    print("PASS\n")


def test_mixed_hits_lower_confidence_correct_majority():
    print("=== score_print_direction: mixed higher/lower hits picks the majority side with lower confidence than unanimous ===")
    bundle = _bundle("CPI m/m", [
        _article("Sticky inflation could push CPI higher"),
        _article("Sticky inflation remains a concern"),
        _article("Some see a downside surprise possible"),
    ])
    call = score_print_direction(bundle)
    assert call.direction == "higher"  # 2 higher-hit articles vs 1 lower-hit article

    unanimous_bundle = _bundle("CPI m/m", [
        _article("Sticky inflation could push CPI higher"),
        _article("Sticky inflation remains a concern"),
    ])
    unanimous_call = score_print_direction(unanimous_bundle)
    assert call.confidence < unanimous_call.confidence
    print("PASS\n")


def test_zero_hits_returns_in_line_low_confidence():
    print("=== score_print_direction: no phrase hits at all returns IN_LINE with low confidence, not a fabricated lean ===")
    bundle = _bundle("CPI m/m", [_article("Markets await Friday's jobs report")])
    call = score_print_direction(bundle)
    assert call is not None
    assert call.direction == "in_line"
    assert call.confidence < 0.3
    print("PASS\n")


def test_no_articles_returns_none():
    print("=== score_print_direction: an empty article bundle returns None, nothing to reason from ===")
    bundle = _bundle("CPI m/m", [])
    assert score_print_direction(bundle) is None
    print("PASS\n")


if __name__ == "__main__":
    test_no_lexicon_entry_returns_none()
    test_unanimous_higher_hits_high_confidence()
    test_unanimous_lower_hits()
    test_mixed_hits_lower_confidence_correct_majority()
    test_zero_hits_returns_in_line_low_confidence()
    test_no_articles_returns_none()
    print("All print_direction tests passed.")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python tests/test_print_direction.py`
Expected: `ModuleNotFoundError: No module named 'scoring.print_direction'`

- [ ] **Step 4: Implement `scoring/print_direction.py`**

```python
"""
Print-surprise classifier — "will THIS release come in higher or lower
than forecast," derived from real article text via
config.settings.PRINT_SURPRISE_LEXICON. Same shape and honesty
conventions as scoring/sentiment.py's lexicon scorer (case-insensitive
substring matching, never fabricates a call for untracked event titles
or an empty article set), but a distinct axis: sentiment.py answers "is
this article USD-bullish/bearish," this answers "does article language
suggest this specific number will beat or miss consensus."

Deliberately NOT wired into score_bundle()'s instrument-score math —
this is an additive, separately-stored signal (see
docs/superpowers/specs/2026-08-11-economic-print-prediction-trend-history-design.md).
"""
from __future__ import annotations

from dataclasses import dataclass

from config.settings import PRINT_SURPRISE_LEXICON
from data_layer.event_context import EventNewsBundle

# A call built from zero phrase hits is a shrug, not a lean — kept
# distinct from a genuine (even weak) majority so callers can tell
# "articles were silent on this" from "articles leaned one way, barely."
NO_HIT_CONFIDENCE = 0.15


@dataclass
class PrintCall:
    direction: str       # 'higher' | 'lower' | 'in_line'
    confidence: float     # 0.0 to 1.0
    article_count: int


def _hit_count(text: str, phrases: list[str]) -> int:
    lower_text = text.lower()
    return sum(1 for phrase in phrases if phrase in lower_text)


def score_print_direction(bundle: EventNewsBundle) -> "PrintCall | None":
    """
    Returns None (no call made) if the event's title has no
    PRINT_SURPRISE_LEXICON entry, or if the bundle has no articles to
    reason from — both are "no data," not "no surprise."
    """
    lexicon = PRINT_SURPRISE_LEXICON.get(bundle.event.title)
    if lexicon is None or not bundle.articles:
        return None

    higher_phrases = lexicon.get("higher", [])
    lower_phrases = lexicon.get("lower", [])

    higher_hits = 0
    lower_hits = 0
    for article in bundle.articles:
        text = f"{article.title} {article.summary}"
        higher_hits += _hit_count(text, higher_phrases)
        lower_hits += _hit_count(text, lower_phrases)

    total_hits = higher_hits + lower_hits
    article_count = len(bundle.articles)

    if total_hits == 0:
        return PrintCall(direction="in_line", confidence=NO_HIT_CONFIDENCE, article_count=article_count)

    if higher_hits == lower_hits:
        direction = "in_line"
        agreement = 0.5
    elif higher_hits > lower_hits:
        direction = "higher"
        agreement = higher_hits / total_hits
    else:
        direction = "lower"
        agreement = lower_hits / total_hits

    # Confidence scales with both agreement (unanimous > narrow majority)
    # and coverage (more hits = more signal), capped at 0.9 — same
    # "never claim full certainty from a lexicon" ceiling spirit as
    # scoring/sentiment.py's clamped range.
    coverage = min(1.0, total_hits / max(article_count, 1))
    confidence = min(0.9, agreement * (0.5 + 0.5 * coverage))

    return PrintCall(direction=direction, confidence=confidence, article_count=article_count)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python tests/test_print_direction.py`
Expected: all 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add config/settings.py scoring/print_direction.py tests/test_print_direction.py
git commit -m "feat: add scoring/print_direction.py — lexicon-based print-surprise classifier

PRINT_SURPRISE_LEXICON (config/settings.py) covers the 4 highest-
traffic events from EVENT_SURPRISE_DIRECTION. score_print_direction()
mirrors scoring/sentiment.py's shape: phrase-hit scoring, confidence
scaled by agreement and coverage, None for untracked titles or empty
article sets. Not yet wired into the accumulator — that's Task 4."
```

---

### Task 4: `print_predictions` table + accumulator wiring

**Files:**
- Modify: `scoring/backtest_store.py` (add `print_predictions` table, `record_print_prediction_if_changed()`, `get_latest_print_prediction()`)
- Modify: `scoring/backtest_accumulator.py` (call `score_print_direction()` per event, record if changed)
- Test: `tests/test_backtest_store.py`, `tests/test_backtest_accumulator.py`

**Interfaces:**
- Consumes: `score_print_direction()`, `PrintCall` (Task 3,
  `scoring.print_direction`), `EventNewsBundle` (existing).
- Produces: `PrintPrediction` dataclass (`id: int, event_title: str,
  event_time_utc: str, predicted_vs_forecast: str, confidence: float,
  article_count: int, scored_at_utc: str` — keyed per EVENT, not per
  instrument, unlike `Prediction`/`Outcome`) in
  `scoring/backtest_store.py`; `record_print_prediction_if_changed(conn,
  event_title: str, event_time_utc: dt.datetime, call: PrintCall, now:
  Optional[dt.datetime] = None) -> bool` (returns True if a new row was
  written) and `get_latest_print_prediction(conn, event_title: str) ->
  Optional[PrintPrediction]`. Task 5 (`/api/predictions`) consumes
  `get_latest_print_prediction()`.

- [ ] **Step 1: Write the failing store tests**

Add to `tests/test_backtest_store.py` (before its `__main__` block):

```python
def test_record_print_prediction_if_changed_writes_first_call():
    print("=== backtest_store: record_print_prediction_if_changed writes a row when nothing exists yet ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        call = PrintCall(direction="higher", confidence=0.6, article_count=3)

        written = store.record_print_prediction_if_changed(conn, "CPI m/m", event_time, call, now=dt.datetime(2026, 8, 10, 9, 0, tzinfo=UTC_TZ))
        assert written is True

        latest = store.get_latest_print_prediction(conn, "CPI m/m")
        assert latest is not None
        assert latest.predicted_vs_forecast == "higher"
        assert latest.confidence == 0.6
        assert latest.article_count == 3
        conn.close()
    print("PASS\n")


def test_record_print_prediction_if_changed_skips_identical_call():
    print("=== backtest_store: an identical predicted_vs_forecast call does not write a new row ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        first = PrintCall(direction="higher", confidence=0.6, article_count=3)
        store.record_print_prediction_if_changed(conn, "CPI m/m", event_time, first, now=dt.datetime(2026, 8, 10, 9, 0, tzinfo=UTC_TZ))

        second = PrintCall(direction="higher", confidence=0.7, article_count=4)
        written = store.record_print_prediction_if_changed(conn, "CPI m/m", event_time, second, now=dt.datetime(2026, 8, 10, 10, 0, tzinfo=UTC_TZ))
        assert written is False

        latest = store.get_latest_print_prediction(conn, "CPI m/m")
        assert latest.confidence == 0.6  # unchanged — the second call was never written
        conn.close()
    print("PASS\n")


def test_record_print_prediction_if_changed_writes_on_direction_flip():
    print("=== backtest_store: a direction flip (higher -> lower) always writes a new row ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        event_time = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
        first = PrintCall(direction="higher", confidence=0.6, article_count=3)
        store.record_print_prediction_if_changed(conn, "CPI m/m", event_time, first, now=dt.datetime(2026, 8, 10, 9, 0, tzinfo=UTC_TZ))

        flipped = PrintCall(direction="lower", confidence=0.55, article_count=5)
        written = store.record_print_prediction_if_changed(conn, "CPI m/m", event_time, flipped, now=dt.datetime(2026, 8, 11, 9, 0, tzinfo=UTC_TZ))
        assert written is True

        latest = store.get_latest_print_prediction(conn, "CPI m/m")
        assert latest.predicted_vs_forecast == "lower"
        conn.close()
    print("PASS\n")


def test_get_latest_print_prediction_none_when_nothing_recorded():
    print("=== backtest_store: get_latest_print_prediction returns None when nothing has been recorded for this event ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = store.get_connection(db_path)
        assert store.get_latest_print_prediction(conn, "CPI m/m") is None
        conn.close()
    print("PASS\n")
```

Add `PrintCall` to the test file's imports (check current imports with
`head -20 tests/test_backtest_store.py`):
`from scoring.print_direction import PrintCall`

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_backtest_store.py`
Expected: `AttributeError: module 'scoring.backtest_store' has no attribute 'record_print_prediction_if_changed'`

- [ ] **Step 3: Add schema, dataclass, and functions to `scoring/backtest_store.py`**

Modify `_SCHEMA` (add after `check_log`, before the closing `"""`):

```python
CREATE TABLE IF NOT EXISTS print_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    predicted_vs_forecast TEXT NOT NULL,
    confidence REAL NOT NULL,
    article_count INTEGER NOT NULL,
    scored_at_utc TEXT NOT NULL
);
```

Add the dataclass (after `Outcome`):

```python
@dataclass
class PrintPrediction:
    id: int
    event_title: str
    event_time_utc: str
    predicted_vs_forecast: str
    confidence: float
    article_count: int
    scored_at_utc: str
```

Add the two functions (at the end of the file):

```python
def get_latest_print_prediction(conn: sqlite3.Connection, event_title: str) -> Optional[PrintPrediction]:
    """Most recent recorded print-direction call for this event title, across ALL its occurrences — None if never scored."""
    row = conn.execute(
        "SELECT * FROM print_predictions WHERE event_title = ? "
        "ORDER BY scored_at_utc DESC, id DESC LIMIT 1",
        (event_title,),
    ).fetchone()
    if row is None:
        return None
    return PrintPrediction(**dict(row))


def record_print_prediction_if_changed(
    conn: sqlite3.Connection,
    event_title: str,
    event_time_utc: dt.datetime,
    call,  # PrintCall from scoring.print_direction — duck-typed to avoid a circular import (print_direction doesn't import this module, but keeping this module free of a hard dependency on it costs nothing)
    now: Optional[dt.datetime] = None,
) -> bool:
    """
    Writes a new print_predictions row only if `call.direction` differs
    from the latest recorded call for this event title — same "current
    call is the truth until articles contradict it" principle as
    _is_material_change() in scoring/backtest_accumulator.py, applied to
    a categorical value instead of a probability threshold. Returns
    True if a row was written, False if skipped as unchanged.
    """
    latest = get_latest_print_prediction(conn, event_title)
    if latest is not None and latest.predicted_vs_forecast == call.direction:
        return False

    scored_at = now or dt.datetime.now(dt.timezone.utc)
    conn.execute(
        "INSERT INTO print_predictions (event_title, event_time_utc, predicted_vs_forecast, confidence, article_count, scored_at_utc) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (event_title, event_time_utc.isoformat(), call.direction, call.confidence, call.article_count, scored_at.isoformat()),
    )
    conn.commit()
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_backtest_store.py`
Expected: all tests PASS, including the 4 new ones.

- [ ] **Step 5: Wire into `scoring/backtest_accumulator.py`**

Modify the imports (currently lines 55-59):

```python
from data_layer.calendar_feed import fetch_calendar, filter_relevant_events, events_in_pre_window, find_precursor_events
from data_layer.event_context import build_event_news_bundle
from data_layer.rss_sources import build_all_preview_sources
from scoring.probability_engine import score_bundle
from scoring.print_direction import score_print_direction
from scoring.backtest_store import (
    get_connection, record_prediction, get_latest_prediction, record_check, count_recent_checks,
    record_print_prediction_if_changed,
)
```

In `run_accumulator_cycle()`, immediately after the existing precursor-lookup
block (right after the `if precursors: print(...)` line, before `for
instrument in instruments:`), add:

```python
            print_call = score_print_direction(bundle)
            if print_call is not None:
                written = record_print_prediction_if_changed(conn, event.title, event.event_time_utc, print_call, now=now)
                if written:
                    print(f"[backtest_accumulator] print call for {event.title}: {print_call.direction} ({print_call.confidence:.0%} confidence, {print_call.article_count} articles)")
```

(This runs once per event, using the already-fetched `bundle` — no extra
article fetch, no extra `record_check()` call, matching the Global
Constraints.)

- [ ] **Step 6: Write the failing accumulator test**

Add to `tests/test_backtest_accumulator.py` (before the `__main__` block —
find insertion point near the other `run_accumulator_cycle` tests, e.g. right
after `test_precursor_events_found_and_passed_to_score_bundle`):

```python
def test_print_direction_call_recorded_once_per_event():
    print("=== accumulator: score_print_direction is called once per event and recorded via record_print_prediction_if_changed ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=20),
            forecast="0.3%", actual=None,
        )
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)
        fake_call = accumulator_print_direction.PrintCall(direction="higher", confidence=0.6, article_count=2)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "score_print_direction", return_value=fake_call):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            conn = store.get_connection(db_path)
            latest = store.get_latest_print_prediction(conn, "CPI m/m")
            assert latest is not None
            assert latest.predicted_vs_forecast == "higher"
            assert latest.article_count == 2
            conn.close()
    print("PASS\n")


def test_print_direction_none_call_writes_nothing():
    print("=== accumulator: score_print_direction returning None (no lexicon coverage) writes no print_predictions row ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "score_print_direction", return_value=None):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            conn = store.get_connection(db_path)
            assert store.get_latest_print_prediction(conn, event.title) is None
            conn.close()
    print("PASS\n")
```

Add the required import at the top of the file (near the existing imports):
`import scoring.print_direction as accumulator_print_direction` (aliased to
avoid clashing with the `score_print_direction` name already patched via
`patch.object(accumulator, "score_print_direction", ...)` — the module
itself, `scoring.backtest_accumulator`, must also import `score_print_direction`
directly by name for `patch.object(accumulator, "score_print_direction",
...)` to work, which Step 5 already did).

Register both new tests in the file's `__main__` block, alongside the other
`run_accumulator_cycle`-based tests.

- [ ] **Step 7: Run tests to verify they pass**

Run: `python tests/test_backtest_accumulator.py`
Expected: all tests PASS, including the 2 new ones.

- [ ] **Step 8: Run the full regression sweep for touched files**

```bash
python tests/test_backtest_store.py
python tests/test_backtest_accumulator.py
```

Expected: all PASS, no regressions.

- [ ] **Step 9: Commit**

```bash
git add scoring/backtest_store.py scoring/backtest_accumulator.py tests/test_backtest_store.py tests/test_backtest_accumulator.py
git commit -m "feat: wire print-direction calls into the accumulator, record diff-aware

New print_predictions table (scoring/backtest_store.py) +
record_print_prediction_if_changed()/get_latest_print_prediction().
scoring/backtest_accumulator.py calls score_print_direction() once
per event using the already-fetched article bundle — zero extra
fetch cost, not logged against the check_log budget. Diff-aware like
predictions: only a direction flip writes a new row."
```

---

### Task 5: `summarize_trend()` + `/api/event_history` route

**Files:**
- Create: `webapp/trend.py`
- Modify: `webapp/app.py` (add `GET /api/event_history` route, add
  `print_prediction` field to `/api/predictions`)
- Test: `tests/test_webapp_trend.py` (new file), `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `get_event_history()` (Task 2, `webapp.store`),
  `get_latest_print_prediction()` (Task 4, `scoring.backtest_store`).
- Produces: `summarize_trend(rows: list[EventHistoryRow]) -> str` in
  `webapp/trend.py`. Task 6 (UI) consumes the `/api/event_history` response
  shape and the `print_prediction` field on `/api/predictions`.

- [ ] **Step 1: Write the failing `summarize_trend()` tests**

Create `tests/test_webapp_trend.py`:

```python
"""Tests for webapp/trend.py — plain-Python arithmetic over event_history rows, no I/O."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.store import EventHistoryRow
from webapp.trend import summarize_trend


def _row(month, surprise):
    return EventHistoryRow(
        event_title="CPI m/m", event_time_utc=f"2026-{month:02d}-12T12:30:00+00:00",
        forecast="0.3%", previous="0.3%", actual="0.4%", surprise_direction=surprise,
    )


def test_not_enough_history_with_zero_rows():
    print("=== summarize_trend: zero rows returns 'not enough history' ===")
    assert summarize_trend([]) == "Not enough history yet"
    print("PASS\n")


def test_not_enough_history_with_one_confirmed_row():
    print("=== summarize_trend: a single confirmed row is still not enough for a trend ===")
    assert summarize_trend([_row(8, "higher")]) == "Not enough history yet"
    print("PASS\n")


def test_not_enough_history_when_all_rows_still_pending():
    print("=== summarize_trend: rows with surprise_direction=None (still pending) don't count toward history ===")
    rows = [_row(8, None), _row(7, None)]
    assert summarize_trend(rows) == "Not enough history yet"
    print("PASS\n")


def test_consecutive_streak_trending_higher():
    print("=== summarize_trend: 2+ consecutive same-direction rows (most recent first) reports a trending streak ===")
    rows = [_row(8, "higher"), _row(7, "higher"), _row(6, "lower")]
    assert summarize_trend(rows) == "Trending higher for 2 consecutive releases"
    print("PASS\n")


def test_no_streak_reports_beat_miss_tally():
    print("=== summarize_trend: no consecutive streak falls back to a beat/miss tally over the window ===")
    rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "higher")]
    assert summarize_trend(rows) == "Beat forecast 3 of last 4"
    print("PASS\n")


def test_mixed_no_clear_majority():
    print("=== summarize_trend: an even split reports 'mixed', not a fabricated lean ===")
    rows = [_row(8, "higher"), _row(7, "lower"), _row(6, "higher"), _row(5, "lower")]
    assert summarize_trend(rows) == "Mixed — no clean streak over the last 4 prints"
    print("PASS\n")


def test_in_line_rows_excluded_from_beat_miss_tally():
    print("=== summarize_trend: 'in_line' rows count toward the window but not toward beat/miss ===")
    rows = [_row(8, "higher"), _row(7, "in_line"), _row(6, "higher")]
    assert summarize_trend(rows) == "Beat forecast 2 of last 2"
    print("PASS\n")


if __name__ == "__main__":
    test_not_enough_history_with_zero_rows()
    test_not_enough_history_with_one_confirmed_row()
    test_not_enough_history_when_all_rows_still_pending()
    test_consecutive_streak_trending_higher()
    test_no_streak_reports_beat_miss_tally()
    test_mixed_no_clear_majority()
    test_in_line_rows_excluded_from_beat_miss_tally()
    print("All webapp_trend tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python tests/test_webapp_trend.py`
Expected: `ModuleNotFoundError: No module named 'webapp.trend'`

- [ ] **Step 3: Implement `webapp/trend.py`**

```python
"""
Plain-Python trend summary over webapp.store's event_history rows — no
I/O, no network, no LLM call. "beat forecast N of last M" / "trending
{direction} for N consecutive releases" / a "mixed" fallback / "not
enough history yet" when there's too little confirmed data to say
anything. Deliberately arithmetic, not inference — same "cheap and
deterministic before reaching for anything smarter" pattern as
scoring/sentiment.py's lexicon tier.
"""
from __future__ import annotations

from webapp.store import EventHistoryRow

MIN_CONFIRMED_ROWS_FOR_A_TREND = 2
MIN_STREAK_LENGTH = 2


def summarize_trend(rows: list[EventHistoryRow]) -> str:
    """
    `rows` is expected most-recent-first (get_event_history()'s existing
    order). Only rows with a non-None surprise_direction count as
    "confirmed" — a still-pending occurrence (event hasn't printed yet)
    doesn't count toward the trend.
    """
    confirmed = [r for r in rows if r.surprise_direction is not None]
    if len(confirmed) < MIN_CONFIRMED_ROWS_FOR_A_TREND:
        return "Not enough history yet"

    # Consecutive-streak check, most recent backward.
    streak_direction = confirmed[0].surprise_direction
    streak_length = 1
    for row in confirmed[1:]:
        if row.surprise_direction == streak_direction:
            streak_length += 1
        else:
            break

    if streak_length >= MIN_STREAK_LENGTH and streak_direction in ("higher", "lower"):
        return f"Trending {streak_direction} for {streak_length} consecutive releases"

    # Fall back to a beat/miss tally over the confirmed window —
    # 'in_line' rows count toward the window total but not toward
    # either side, since they're neither a beat nor a miss.
    higher_count = sum(1 for r in confirmed if r.surprise_direction == "higher")
    lower_count = sum(1 for r in confirmed if r.surprise_direction == "lower")
    directional_total = higher_count + lower_count

    if directional_total == 0:
        return "Mixed — no clean streak over the last {} prints".format(len(confirmed))

    if higher_count > lower_count:
        return f"Beat forecast {higher_count} of last {directional_total}"
    if lower_count > higher_count:
        return f"Missed forecast {lower_count} of last {directional_total}"
    return f"Mixed — no clean streak over the last {len(confirmed)} prints"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python tests/test_webapp_trend.py`
Expected: all 7 tests PASS.

- [ ] **Step 5: Write failing `/api/event_history` and `print_prediction` tests**

Add to `tests/test_webapp_app.py` (before its `__main__` block — check
imports first, add `EventHistoryRow` and backtest_store's
`record_print_prediction_if_changed`/`PrintCall` if needed):

```python
def test_event_history_endpoint_returns_occurrences_and_trend():
    print("=== app: /api/event_history returns past occurrences plus a summarized trend ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        with patch.object(store, "DB_PATH", db_path):
            conn = store.get_connection(db_path)
            for month, actual, surprise in [(6, "0.4%", "higher"), (7, "0.5%", "higher")]:
                event = EconomicEvent(
                    title="CPI m/m", country="USD", impact="High",
                    event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                    forecast="0.3%", previous="0.3%", actual=actual,
                )
                store.upsert_event_history(conn, event, surprise, now=dt.datetime(2026, month, 12, 13, 0, tzinfo=UTC_TZ))
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/event_history?title=CPI m/m")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data["occurrences"]) == 2
            assert data["occurrences"][0]["actual"] == "0.5%"  # most recent first
            assert "trend_summary" in data
    print("PASS\n")


def test_event_history_endpoint_unknown_title_returns_empty():
    print("=== app: /api/event_history for an unknown title returns an empty list, not a 500 ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        with patch.object(store, "DB_PATH", db_path):
            client = webapp_app.app.test_client()
            resp = client.get("/api/event_history?title=Nonexistent Event")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["occurrences"] == []
    print("PASS\n")


def test_predictions_includes_print_prediction_when_accumulator_scored_it():
    print("=== app: /api/predictions includes print_prediction sourced from the accumulator's print_predictions table ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            events = _fake_events()
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", events[0].title, events[0].event_time_utc, 0.6, "bullish", 0.4)
            conn.close()

            from scoring.print_direction import PrintCall
            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_print_prediction_if_changed(
                bconn, events[0].title, events[0].event_time_utc,
                PrintCall(direction="higher", confidence=0.62, article_count=4),
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            event_entry = data["predictions"][0]["events"][0]
            assert event_entry["print_prediction"] == {"direction": "higher", "confidence": 0.62}
    print("PASS\n")


def test_predictions_print_prediction_is_none_when_never_scored():
    print("=== app: /api/predictions omits print_prediction (None) when the accumulator never made a print call ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "dashboard.db"
        backtest_db_path = Path(tmp) / "backtest.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            events = _fake_events()
            _seed_calendar(db_path, events)
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            store.record_run(conn, "XAUUSD", events[0].title, events[0].event_time_utc, 0.6, "bullish", 0.4)
            conn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            data = resp.get_json()
            event_entry = data["predictions"][0]["events"][0]
            assert event_entry["print_prediction"] is None
    print("PASS\n")
```

Register all 4 new tests in the file's `__main__` block.

- [ ] **Step 6: Run tests to verify they fail**

Run: `python tests/test_webapp_app.py`
Expected: `404` for `/api/event_history` (route doesn't exist), `KeyError:
'print_prediction'` for the other two.

- [ ] **Step 7: Add the route and field to `webapp/app.py`**

Modify the imports (add to the existing `from webapp.store import (...)`
block and add a new import line):

```python
from webapp.store import (
    get_connection, get_latest_two, get_history,
    add_tracked_symbol, remove_tracked_symbol, list_tracked_symbols,
    get_calendar_snapshot, get_event_history,
)
from webapp.trend import summarize_trend
from webapp.symbols import classify_symbol, UnrecognizedSymbolError
from scoring.backtest_store import (
    get_connection as get_backtest_connection, get_latest_two_predictions,
    get_latest_print_prediction,
)
```

Add the new route (after `get_calendar()`, before `get_predictions()`):

```python
@app.route("/api/event_history", methods=["GET"])
def get_event_history_route():
    title = request.args.get("title", "")
    conn = get_connection()
    rows = get_event_history(conn, title)
    conn.close()
    return jsonify({
        "occurrences": [
            {
                "event_time_utc": r.event_time_utc, "forecast": r.forecast,
                "previous": r.previous, "actual": r.actual, "surprise_direction": r.surprise_direction,
            }
            for r in rows
        ],
        "trend_summary": summarize_trend(rows),
    })
```

In `get_predictions()`, inside the `for event in events:` loop, right after
the existing `previous_article_prediction = None` block (after line ~170,
before `entry["events"].append(...)`), add:

```python
            print_call = get_latest_print_prediction(backtest_conn, event["title"])
            print_prediction = None
            if print_call is not None:
                print_prediction = {"direction": print_call.predicted_vs_forecast, "confidence": print_call.confidence}
```

Then add `"print_prediction": print_prediction,` as a new key inside the
existing `entry["events"].append({...})` dict (alongside
`"article_prediction": article_prediction,`).

- [ ] **Step 8: Run tests to verify they pass**

Run: `python tests/test_webapp_app.py`
Expected: all tests PASS, including the 4 new ones.

- [ ] **Step 9: Run the full regression sweep for touched files**

```bash
python tests/test_webapp_trend.py
python tests/test_webapp_app.py
```

Expected: all PASS, no regressions.

- [ ] **Step 10: Commit**

```bash
git add webapp/trend.py webapp/app.py tests/test_webapp_trend.py tests/test_webapp_app.py
git commit -m "feat: add /api/event_history + print_prediction field, summarize_trend()

webapp/trend.py's summarize_trend() is plain arithmetic over
event_history rows — no LLM, no new dependency — producing 'beat
forecast N of last M' / 'trending {direction} for N consecutive
releases' / 'mixed' / 'not enough history yet'. New GET
/api/event_history route serves occurrences + the trend summary on
demand (not on every dashboard load). /api/predictions gains a
print_prediction field sourced from the accumulator's
print_predictions table, omitted (None) when nothing's been scored."
```

---

### Task 6: Dashboard UI — print-call badge + History panel

**Files:**
- Modify: `webapp/static/app.js` (print-call badge in `renderCard()`,
  History toggle + fetch-on-expand)
- Modify: `webapp/static/style.css` (styling for the new elements — check
  the file exists first: `ls webapp/static/*.css`; if the project inlines
  styles in `index.html` instead, add there — verify before writing this
  step's exact target)

**Interfaces:**
- Consumes: `next.print_prediction` (`{direction, confidence}` or `null`,
  Task 5's `/api/predictions` field), `GET /api/event_history?title=...`
  (Task 5's route, response shape `{occurrences: [...], trend_summary:
  str}`).
- Produces: no new interfaces — this is the final, UI-only task.

No backend, no SQL, no Python — this task is browser-verified rather than
`pytest`-verified, matching how this project's frontend changes have been
checked throughout (no existing JS test harness in `tests/`).

- [ ] **Step 1: Add the print-call badge in `renderCard()`**

In `webapp/static/app.js`, inside `renderCard()`, immediately after the
existing `const articlePredictionLine = articlePredictionHtml(...)` line
(currently line 236), add a sibling function and call:

```javascript
  // print_prediction is the accumulator's separate "will THIS number beat
  // or miss forecast" call (scoring/print_direction.py), distinct from
  // article_prediction's price-direction call above. Absent (null) for
  // events with no PRINT_SURPRISE_LEXICON coverage or no call made yet —
  // rendered as nothing, never a fabricated placeholder.
  function printPredictionHtml(printPred) {
    if (!printPred) return '';
    const label = printPred.direction === 'higher' ? 'HIGHER'
      : printPred.direction === 'lower' ? 'LOWER' : 'IN LINE with';
    const confPct = Math.round(printPred.confidence * 100);
    return `<div class="print-prediction">
      📊 Print call: likely <b>${label}</b> than forecast <span style="font-size:12px;color:#888">(${confPct}% confidence)</span>
    </div>`;
  }
  const printPredictionLine = printPredictionHtml(next.print_prediction);
```

Then append `${printPredictionLine}` immediately after
`${articlePredictionLine}` in both places it currently appears in this
function: the pending-event branch (currently line 244,
`${articlePredictionLine}` inside the template literal for the "Awaiting"
card) and the resolved-event branch (currently line 276, inside the
`gauge-row` div).

- [ ] **Step 2: Add the History toggle**

Immediately after the `body += dayStripHtml(next.event_time_utc);` line
(currently line 278), add:

```javascript
  const historyToggleId = `history-${symbol}-${next.event_title.replace(/[^a-zA-Z0-9]/g, '')}`;
  body += `<div class="history-toggle">
    <button class="history-toggle-btn" data-event-title="${escapeHtml(next.event_title)}" data-target="${historyToggleId}">History ▾</button>
    <div class="history-panel" id="${historyToggleId}" style="display:none"></div>
  </div>`;
```

At the end of `renderCard()`, right before the final `return el;`, add the
click handler (event delegation isn't set up elsewhere in this file per the
existing pattern of per-element `addEventListener` after `el.innerHTML =
body`, so follow that same pattern):

```javascript
  const historyBtn = el.querySelector(".history-toggle-btn");
  if (historyBtn) {
    historyBtn.addEventListener("click", async () => {
      const panel = document.getElementById(historyBtn.dataset.target);
      if (panel.style.display !== "none") {
        panel.style.display = "none";
        return;
      }
      panel.style.display = "";
      panel.innerHTML = "Loading…";
      const resp = await fetch(`/api/event_history?title=${encodeURIComponent(historyBtn.dataset.eventTitle)}`);
      const data = await resp.json();
      if (!data.occurrences || data.occurrences.length === 0) {
        panel.innerHTML = "<div style=\"font-size:12px;color:#888\">No history recorded yet</div>";
        return;
      }
      const rows = data.occurrences.map((o) => {
        const dateLabel = new Date(o.event_time_utc).toLocaleDateString(undefined, { year: "numeric", month: "short" });
        const surpriseLabel = o.surprise_direction
          ? `(${o.surprise_direction.replace("_", "-")})`
          : "(pending)";
        return `<div>${dateLabel}: forecast ${escapeHtml(o.forecast ?? "—")}, previous ${escapeHtml(o.previous ?? "—")}, actual ${escapeHtml(o.actual ?? "—")} ${surpriseLabel}</div>`;
      }).join("");
      panel.innerHTML = `${rows}<div style="margin-top:4px;font-weight:bold">→ ${escapeHtml(data.trend_summary)}</div>`;
    });
  }
```

- [ ] **Step 3: Add minimal styling**

Styles live in `webapp/static/style.css` (confirmed — no inline `<style>`
block to worry about). Append:

```css
.print-prediction { margin-top: 4px; font-size: 13px; }
.history-toggle { margin-top: 8px; }
.history-toggle-btn { background: none; border: none; color: #666; font-size: 12px; cursor: pointer; padding: 2px 0; }
.history-toggle-btn:hover { text-decoration: underline; }
.history-panel { font-size: 12px; color: #555; margin-top: 4px; padding-left: 8px; border-left: 2px solid #ddd; }
```

- [ ] **Step 4: Verify in the browser**

This step requires a running dashboard with real or seeded data — follow the
project's established live-verification pattern (restart `run_all.py`,
open the dashboard, confirm visually) rather than an automated test, since
no JS test harness exists in this codebase.

```bash
python scripts/run_all.py
```

Open `http://localhost:5001`, confirm:
- No console errors on load (`print_prediction: null` for events with no
  lexicon coverage should render nothing, not throw).
- If any tracked event has a `print_predictions` row (may take a live cycle
  to populate for `CPI m/m`/`Core CPI m/m`/`Non-Farm Employment
  Change`/`Unemployment Rate` specifically — other events will correctly
  show nothing), the badge appears.
- Clicking "History ▾" on any event card expands the panel, fetches
  `/api/event_history`, and shows either occurrences + a trend line or "No
  history recorded yet" (expected immediately after this feature ships,
  since `event_history` starts empty and only accumulates going forward —
  the same "cold start" as this codebase's other backtest tables).
- Clicking again collapses it without a second fetch call (check via the
  browser's network tab, or trust the `style.display !== "none"` early
  return in Step 2's handler).

- [ ] **Step 5: Commit**

```bash
git add webapp/static/app.js webapp/static/style.css
git commit -m "feat: dashboard UI for print-call badge and per-event History panel

Print-call badge (📊) renders next to the existing article-based
read whenever print_prediction is present, absent entirely otherwise.
History toggle fetches /api/event_history on first expand only (not
on page load), showing past occurrences and the summarize_trend()
line. Verified live via run_all.py — no JS test harness exists in
this codebase, matching the frontend verification pattern used
throughout this project."
```

---

### Task 7: README update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a new section documenting the feature**

Find the accumulator section (`grep -n "## Article-based backtest
accumulator" README.md`) and add a new subsection immediately after it,
before the next `##` heading:

```markdown
### Economic-print prediction + trend history

Two additive signals, separate from the article-based direction call above:

- **Print-direction call** (`scoring/print_direction.py`) — "will THIS
  release come in higher or lower than forecast," derived from article
  language via `config.settings.PRINT_SURPRISE_LEXICON` (currently covers
  CPI m/m, Core CPI m/m, Non-Farm Employment Change, Unemployment Rate —
  config-only to extend). Reuses the accumulator's already-fetched article
  bundle, zero extra fetch cost. Shown on the dashboard as a "📊 Print call"
  badge next to the article-based read.
- **Event history** (`webapp/store.py`'s `event_history` table) — persists
  forecast/previous/actual per event occurrence, captured by
  `webapp/scheduler.py`'s existing fetch cycle for every calendar event
  (all impact levels), surviving the weekly Forex Factory rollover that
  previously erased it. A "History ▾" toggle on each dashboard card shows
  past occurrences plus a `summarize_trend()` line ("beat forecast 3 of
  last 4", "trending higher for 2 consecutive releases").

Both are purely additive/display — neither feeds back into
`score_bundle()`'s instrument scoring or `_is_material_change()`'s
recording logic. See
`docs/superpowers/specs/2026-08-11-economic-print-prediction-trend-history-design.md`
for the full design and the explicit out-of-scope list (numeric print-value
estimation, feeding the trend back into scoring — deferred to a future pass
once there's enough real data to know if it's predictive).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document economic-print prediction + trend history feature"
```

---

## Post-plan verification (do this after all 7 tasks are complete)

- [ ] Run the full regression suite across every `tests/test_*.py` file (not
      just the ones this plan touched) to confirm nothing outside this
      feature's scope broke:

```bash
for f in tests/test_*.py; do echo "--- $f ---"; python "$f" 2>&1 | tail -6; done
```

Expected: every file ends with its "All ... tests passed." line (or PASS for
files without that convention) — `test_contextual_sentiment.py`'s SKIP lines
(no `ANTHROPIC_API_KEY` configured) are pre-existing and expected, not a
regression.

- [ ] Restart `run_all.py` (kill the existing process tree first, matching
      this project's established restart procedure) and confirm live via the
      browser: dashboard loads, no console errors, an event card's History
      panel fetches and renders correctly.
