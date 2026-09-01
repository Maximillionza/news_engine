# Low-Impact Event Context Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track Low-impact USD economic events as context-only data (Calendar tab + history, no card/gauge), keep the article accumulator and dashboard-card scoring untouched at Medium+, and close a pre-existing leak where resolved non-USD/non-Medium+ events could surface as dashboard cards via the "recently resolved" backfill.

**Architecture:** `webapp/scheduler.py`'s `run_scoring_cycle()` currently computes one `events` list (USD Medium+) used for the calendar snapshot, the symbol-scoring loop, AND (via the separate `all_events` variable) fully-unfiltered history writes. This plan adds an `impact` column to `event_history` (captured at write time), splits scheduler's event handling into `calendar_events` (USD, Low+ — snapshot + history writes) and `scoring_events` (USD, Medium+ — unchanged, feeds symbol scoring), and filters `/api/predictions`'s recently-resolved backfill to Medium+ using the new stored `impact` value.

**Tech Stack:** Python 3, Flask, SQLite (stdlib `sqlite3`), pytest.

**Spec:** [docs/superpowers/specs/2026-08-31-low-impact-context-tracking-design.md](../specs/2026-08-31-low-impact-context-tracking-design.md)

## Global Constraints

- Low-impact events must NEVER produce a `prediction_runs` row, a dashboard card, or a gauge — data-only (actual/forecast/previous), visible in Calendar tab + `/api/event_history` only.
- Accumulator (`scoring/backtest_accumulator.py`) is not touched by this plan — verify at the end it still only sees High + the 3-title `ACCUMULATOR_MEDIUM_ALLOWLIST`.
- `event_history` writes must be scoped to USD only (any impact tier) — never a foreign-country event, regardless of this plan's Low-impact change.
- Every existing test in `tests/test_webapp_store.py`, `tests/test_webapp_scheduler.py`, `tests/test_webapp_app.py`, `tests/test_calendar_feed.py` must still pass unmodified except where a task explicitly updates one (called out in that task).

---

## File Structure

- **Modify `data_layer/calendar_feed.py`**: extract the impact-rank map (currently a local dict inside `filter_relevant_events`) to a module-level `IMPACT_RANK` constant, so `webapp/app.py` can reuse the exact same ranking instead of duplicating it.
- **Modify `webapp/store.py`**: add an `impact` column to `event_history` (additive migration, same pattern as the existing `source` column migration), thread it through `upsert_event_history()`, `EventHistoryRow`, `get_event_history()`, `get_resolved_event_history()`.
- **Modify `webapp/scheduler.py`**: split the single `events` list into `calendar_events` (USD Low+, drives the calendar snapshot AND the history-writing loop) and `scoring_events` (USD Medium+, unchanged — drives symbol scoring and is what `run_scoring_cycle()` returns for adaptive-interval purposes).
- **Modify `webapp/app.py`**: filter `/api/predictions`'s `recently_resolved` backfill to Medium+ using the new `impact` field, so a Low-impact (or impact-unknown/legacy) resolved event can never re-enter the card-building list.
- **Tests**: extend `tests/test_webapp_store.py`, `tests/test_webapp_scheduler.py`, `tests/test_webapp_app.py`, `tests/test_calendar_feed.py` — no new test files, these are the existing homes for this behavior.

---

### Task 1: `IMPACT_RANK` shared constant in `data_layer/calendar_feed.py`

**Files:**
- Modify: `data_layer/calendar_feed.py:323-344` (`filter_relevant_events`)
- Test: `tests/test_calendar_feed.py`

**Interfaces:**
- Produces: `IMPACT_RANK: dict[str, int]` module-level constant, `{"Low": 1, "Medium": 2, "High": 3}` — importable as `from data_layer.calendar_feed import IMPACT_RANK`. `filter_relevant_events()`'s signature and behavior are unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_calendar_feed.py` (near the other `filter_relevant_events` tests):

```python
def test_impact_rank_constant_matches_filter_relevant_events_ranking():
    print("=== IMPACT_RANK: exported constant matches filter_relevant_events' own Low<Medium<High ranking ===")
    from data_layer.calendar_feed import IMPACT_RANK
    assert IMPACT_RANK == {"Low": 1, "Medium": 2, "High": 3}
    assert IMPACT_RANK["Low"] < IMPACT_RANK["Medium"] < IMPACT_RANK["High"]
    print("PASS\n")
```

Add the call to this test in the `if __name__ == "__main__":` block at the bottom of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_calendar_feed.py::test_impact_rank_constant_matches_filter_relevant_events_ranking -v`
Expected: FAIL with `ImportError: cannot import name 'IMPACT_RANK'`

- [ ] **Step 3: Extract the constant**

In `data_layer/calendar_feed.py`, add above `def filter_relevant_events(`:

```python
# Shared with webapp/app.py's recently-resolved backfill filter — the
# single source of truth for "how do Low/Medium/High rank against each
# other," so a future impact tier (if FF ever adds one) only needs
# updating here, not re-derived at each call site.
IMPACT_RANK = {"Low": 1, "Medium": 2, "High": 3}
```

Then replace the local dict inside `filter_relevant_events`:

```python
def filter_relevant_events(
    events: list[EconomicEvent],
    countries: tuple[str, ...] = ("USD",),
    min_impact: str = "High",
    extra_titles: frozenset[str] = frozenset(),
) -> list[EconomicEvent]:
    """
    Narrow the full calendar down to the events that actually matter for
    gold / US30 directional analysis — high-impact USD releases by default
    (NFP, CPI, FOMC, PCE, ISM, retail sales, etc.), plus any event whose
    exact title is in extra_titles regardless of its impact tier (a
    curated allowlist, e.g. config.settings.ACCUMULATOR_MEDIUM_ALLOWLIST —
    never a blanket lower threshold, which would dilute callers that rely
    on this function's default High-only behavior).
    """
    min_rank = IMPACT_RANK.get(min_impact, 3)

    return [
        e for e in events
        if e.country in countries and (IMPACT_RANK.get(e.impact, 0) >= min_rank or e.title in extra_titles)
    ]
```

(Only the local `impact_rank = {...}` line is deleted and its two usages renamed to `IMPACT_RANK`; nothing else in the function changes.)

- [ ] **Step 4: Run test to verify it passes, and run the full file to confirm no regression**

Run: `python -m pytest tests/test_calendar_feed.py -v`
Expected: all PASS, including the new test.

- [ ] **Step 5: Commit**

```bash
git add data_layer/calendar_feed.py tests/test_calendar_feed.py
git commit -m "refactor: extract IMPACT_RANK as a shared constant in calendar_feed"
```

---

### Task 2: `impact` column on `event_history`

**Files:**
- Modify: `webapp/store.py` (schema, `_migrate_add_source_column` sibling migration, `EventHistoryRow`, `upsert_event_history`, `get_event_history`, `get_resolved_event_history`)
- Test: `tests/test_webapp_store.py`

**Interfaces:**
- Consumes: nothing new from Task 1 in this task's code (the column is stored as a plain string, ranked later by the caller in Task 4).
- Produces: `EventHistoryRow.impact: Optional[str]` (new field — `None` for rows written before this migration, or if the source event's impact was somehow missing). `upsert_event_history(conn, event, surprise_direction, now, source="live")` now also persists `event.impact` (no new parameter — `event` already carries `.impact`, same object used for `.title`/`.forecast`/etc. today).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_webapp_store.py` (find the existing `upsert_event_history`/`get_event_history` tests and add near them — use whatever local `_event(...)` / connection-fixture helper that file already uses for `EconomicEvent` construction and an in-memory `get_connection`):

```python
def test_upsert_event_history_persists_impact():
    print("=== upsert_event_history: stores the event's impact tier on the row ===")
    conn = get_connection(":memory:")
    event = _event(title="Housing Starts", impact="Low", forecast="1.35M", previous="1.32M", actual=None)
    now = dt.datetime(2026, 8, 31, 12, 0, tzinfo=dt.timezone.utc)
    upsert_event_history(conn, event, surprise_direction=None, now=now)

    rows = get_event_history(conn, "Housing Starts")
    assert len(rows) == 1
    assert rows[0].impact == "Low"
    print("PASS\n")


def test_get_resolved_event_history_returns_impact():
    print("=== get_resolved_event_history: impact field flows through to the cross-title resolved query too ===")
    conn = get_connection(":memory:")
    event = _event(title="Factory Orders m/m", impact="Low", forecast="0.2%", previous="0.1%", actual="0.3%")
    now = dt.datetime(2026, 8, 31, 12, 0, tzinfo=dt.timezone.utc)
    upsert_event_history(conn, event, surprise_direction="higher", now=now)

    rows = get_resolved_event_history(conn)
    assert len(rows) == 1
    assert rows[0].impact == "Low"
    print("PASS\n")


def test_pre_migration_row_has_none_impact():
    print("=== event_history: a row written before this column existed reads back impact=None, not a crash or a fabricated value ===")
    conn = get_connection(":memory:")
    now = dt.datetime(2026, 8, 31, 12, 0, tzinfo=dt.timezone.utc)
    # Simulate a pre-migration row by inserting directly, bypassing upsert_event_history
    # (which always supplies impact going forward) — this is exactly what a real
    # database file created before this change looks like.
    conn.execute(
        "INSERT INTO event_history (event_title, event_time_utc, forecast, previous, actual, "
        "surprise_direction, recorded_at_utc, updated_at_utc, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("Legacy Event", now.isoformat(), "1.0", "0.9", "1.1", "higher", now.isoformat(), now.isoformat(), "live"),
    )
    conn.commit()

    rows = get_event_history(conn, "Legacy Event")
    assert len(rows) == 1
    assert rows[0].impact is None
    print("PASS\n")
```

Add each new test's call to the `if __name__ == "__main__":` block at the bottom of the file. If `tests/test_webapp_store.py` doesn't already import `get_resolved_event_history`, add it to the existing `from webapp.store import (...)` import block.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_webapp_store.py -k "impact" -v`
Expected: FAIL — `AttributeError: 'EventHistoryRow' object has no attribute 'impact'` (or similar) on all three.

- [ ] **Step 3: Add the column, migration, and thread `impact` through**

In `webapp/store.py`, update the schema (inside the `_SCHEMA` string):

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
    impact TEXT,
    UNIQUE(event_title, event_time_utc)
);
```

Add a sibling migration function right after `_migrate_add_source_column`:

```python
def _migrate_add_impact_column(conn: sqlite3.Connection) -> None:
    """
    Same reasoning as _migrate_add_source_column: CREATE TABLE IF NOT
    EXISTS doesn't retroactively add a column to an already-created DB
    file. Existing rows read back impact=None (genuinely unknown — never
    guessed) until a fresh upsert_event_history() call for that exact
    occurrence supplies it, which only happens for a row whose `actual`
    is still NULL (see upsert_event_history's docstring on why the
    UPDATE path is conditional) — an already-resolved legacy row's
    impact stays None permanently, which is fine: it's never read again
    once outside the 7-day recently-resolved retention window.
    """
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(event_history)").fetchall()}
    if "impact" not in existing_columns:
        conn.execute("ALTER TABLE event_history ADD COLUMN impact TEXT")
        conn.commit()
```

Update `get_connection()` to call it:

```python
def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path if db_path is not None else DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _migrate_add_source_column(conn)
    _migrate_add_impact_column(conn)
    return conn
```

Update the `EventHistoryRow` dataclass:

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
    impact: Optional[str]
```

Update `upsert_event_history()`'s INSERT (the UPDATE/CONFLICT clause is unchanged — impact is written once, at first insert, same as forecast/previous, and is never revised by the conditional UPDATE branch):

```python
    conn.execute(
        """
        INSERT INTO event_history
            (event_title, event_time_utc, forecast, previous, actual, surprise_direction, recorded_at_utc, updated_at_utc, source, impact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_title, event_time_utc) DO UPDATE SET
            actual = excluded.actual,
            surprise_direction = excluded.surprise_direction,
            updated_at_utc = excluded.updated_at_utc,
            source = CASE WHEN event_history.actual IS NULL THEN excluded.source ELSE event_history.source END
        WHERE excluded.actual IS NOT NULL AND event_history.actual IS NULL
        """,
        (
            event.title, event.event_time_utc.isoformat(), event.forecast, event.previous,
            event.actual, surprise_direction, now.isoformat(), now.isoformat(), source, event.impact,
        ),
    )
```

Update `get_event_history()`'s SELECT and construction:

```python
def get_event_history(conn: sqlite3.Connection, event_title: str, limit: int = 6) -> list[EventHistoryRow]:
    """Past occurrences of this event title, most recent first, capped at `limit`. Empty list if none recorded yet."""
    rows = conn.execute(
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction, source, impact "
        "FROM event_history WHERE event_title = ? ORDER BY event_time_utc DESC LIMIT ?",
        (event_title, limit),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]
```

Update `get_resolved_event_history()`'s SELECT the same way:

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
        "SELECT event_title, event_time_utc, forecast, previous, actual, surprise_direction, source, impact "
        "FROM event_history WHERE actual IS NOT NULL ORDER BY event_time_utc DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [EventHistoryRow(**dict(row)) for row in rows]
```

- [ ] **Step 4: Run tests to verify they pass, and run the whole store test file**

Run: `python -m pytest tests/test_webapp_store.py -v`
Expected: all PASS, including the three new tests. If any pre-existing test constructs an `EventHistoryRow(...)` positionally or by keyword without `impact`, update that call site to pass `impact=None` (or a real value if the test is about impact-sensitive behavior) — this is the one place outside this task's own new tests where the dataclass's new required field can break an existing test.

- [ ] **Step 5: Commit**

```bash
git add webapp/store.py tests/test_webapp_store.py
git commit -m "feat: add impact column to event_history, threaded through EventHistoryRow"
```

---

### Task 3: Split `webapp/scheduler.py` into `calendar_events` (Low+) and `scoring_events` (Medium+)

**Files:**
- Modify: `webapp/scheduler.py:113-215` (`run_scoring_cycle`)
- Test: `tests/test_webapp_scheduler.py`

**Interfaces:**
- Consumes: `data_layer.calendar_feed.filter_relevant_events(events, countries=("USD",), min_impact=..., extra_titles=...)` (unchanged signature), `webapp.store.upsert_event_history(conn, event, surprise_direction, now, source="live")` (Task 2 — now also persists `event.impact`, no call-site change needed since it reads `.impact` off the `event` object already passed in).
- Produces: `run_scoring_cycle()`'s return type and meaning are unchanged (`scoring_events`, i.e. USD Medium+ — same list identity/contents `events` held before this task, just renamed). No other module calls into scheduler's internals directly, so no other production file changes.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_webapp_scheduler.py` (this file already mocks `fetch_calendar`/`filter_relevant_events`/`upsert_event_history` — follow its existing patching style; find the block of tests around `run_scoring_cycle` and add these alongside them):

```python
def test_run_scoring_cycle_writes_history_for_low_impact_usd_event_but_does_not_score_it():
    print("=== run_scoring_cycle: a Low-impact USD event gets an event_history row but is NEVER passed to score_event_for_symbol ===")
    low_event = EconomicEvent(
        title="Housing Starts", country="USD", impact="Low",
        event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ),
        forecast="1.35M", previous="1.32M", actual=None,
    )
    with patch.object(scheduler, "fetch_calendar", return_value=[low_event]), \
         patch.object(scheduler, "save_calendar_snapshot_if_changed") as mock_save, \
         patch.object(scheduler, "upsert_event_history") as mock_history, \
         patch.object(scheduler, "confirm_macro_calendar_event"), \
         patch.object(scheduler, "get_actual_from_fred", return_value=None), \
         patch.object(scheduler, "get_connection"), \
         patch.object(scheduler, "get_latest_two", return_value=[]), \
         patch.object(scheduler, "record_run") as mock_record, \
         patch.object(scheduler, "classify_symbol") as mock_classify:
        mock_classify.return_value.symbol_class = "gold"
        result = scheduler.run_scoring_cycle(["XAUUSD"])

    # History IS written for the Low-impact event...
    mock_history.assert_called_once()
    assert mock_history.call_args.args[1] is low_event
    # ...but it's never scored (record_run never called), and it's not
    # part of the returned scoring-relevant event list either.
    mock_record.assert_not_called()
    assert result == []


def test_run_scoring_cycle_calendar_snapshot_includes_low_impact_but_scoring_stays_medium_plus():
    print("=== run_scoring_cycle: the persisted calendar snapshot includes Low-impact events; the returned/scored event list does not ===")
    low_event = EconomicEvent(
        title="Housing Starts", country="USD", impact="Low",
        event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ),
        forecast="1.35M", previous="1.32M", actual=None,
    )
    high_event = EconomicEvent(
        title="ISM Manufacturing PMI", country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 9, 2, 14, 0, tzinfo=UTC_TZ),
        forecast="55.2", previous="55.6", actual=None,
    )
    with patch.object(scheduler, "fetch_calendar", return_value=[low_event, high_event]), \
         patch.object(scheduler, "save_calendar_snapshot_if_changed") as mock_save, \
         patch.object(scheduler, "upsert_event_history"), \
         patch.object(scheduler, "confirm_macro_calendar_event"), \
         patch.object(scheduler, "get_actual_from_fred", return_value=None), \
         patch.object(scheduler, "get_connection"), \
         patch.object(scheduler, "get_latest_two", return_value=[]), \
         patch.object(scheduler, "record_run"), \
         patch.object(scheduler, "classify_symbol") as mock_classify:
        mock_classify.return_value.symbol_class = "gold"
        result = scheduler.run_scoring_cycle(["XAUUSD"])

    snapshot_events = mock_save.call_args.args[1]
    assert low_event in snapshot_events and high_event in snapshot_events
    assert result == [high_event]  # scoring-relevant list excludes the Low-impact event
```

Add both test names to the `if __name__ == "__main__":` block. Check the top of `tests/test_webapp_scheduler.py` for its existing `EconomicEvent`/`UTC_TZ`/`scheduler` imports and reuse them — do not re-import.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_webapp_scheduler.py -k "low_impact" -v`
Expected: FAIL — `result == []`/`result == [high_event]` assertions fail because today's `run_scoring_cycle` uses one Medium+ list for everything, so the Low-impact event never reaches `upsert_event_history` at all (first test fails on `mock_history.assert_called_once()`), and the second test's snapshot never contains the Low event either.

- [ ] **Step 3: Split the event lists in `run_scoring_cycle`**

In `webapp/scheduler.py`, replace lines 113-143 (roughly — the top of `run_scoring_cycle` through the history-writing loop) with:

```python
def run_scoring_cycle(tracked_symbols: list[str], db_path: Optional[Path] = None) -> Optional[list[EconomicEvent]]:
    """
    Returns the fetched Medium+ impact, USD scoring-relevant events on
    success (the same list this always returned — Low-impact events are
    tracked for context but never drive scoring or the adaptive poll
    interval), or None if the calendar fetch failed — the caller
    (start_scheduler's loop) uses this to pick the next adaptive poll
    interval; a failed fetch means "no fresh info to reason from," not
    "nothing is urgent."
    """
    conn = get_connection(db_path)
    try:
        all_events = fetch_calendar("thisweek")
    except Exception as exc:  # noqa: BLE001 — a failed fetch must not crash the loop or wipe existing data
        print(f"[scheduler] WARNING: calendar fetch failed, keeping existing data: {exc}")
        conn.close()
        return None

    # Two distinct thresholds, deliberately not one list (design doc:
    # docs/superpowers/specs/2026-08-31-low-impact-context-tracking-design.md):
    #
    # calendar_events (USD, Low+) — drives the persisted calendar snapshot
    # (Calendar tab) AND the history-writing loop below. Low-impact events
    # get real actual/forecast/previous data for context and the macro-
    # backdrop cross-check, but deliberately never reach the scoring loop.
    #
    # scoring_events (USD, Medium+) — unchanged threshold from before this
    # change. Drives symbol scoring (dashboard cards/gauges) and is what
    # this function returns for the adaptive-interval calculation. A
    # Low-impact event approaching must never tighten the poll interval,
    # since nothing about it is ever traded.
    calendar_events = filter_relevant_events(all_events, min_impact="Low")
    scoring_events = filter_relevant_events(all_events, min_impact="Medium")

    # This loop is the SOLE calendar fetcher for the whole dashboard — see
    # module docstring. Persist immediately so /api/calendar and
    # /api/predictions (webapp/app.py) can answer instantly from storage,
    # never blocking a request on a live fetch or a live feed's rate limit.
    # No-ops (returns False) if this fetch matches what's already stored —
    # "store and use as current until new information supersedes this."
    save_calendar_snapshot_if_changed(conn, calendar_events, dt.datetime.now(dt.timezone.utc))

    now_for_history = dt.datetime.now(dt.timezone.utc)
    # USD-only (any impact tier) — NOT all_events. all_events is the full,
    # unfiltered global FF feed (every country, every impact tier);
    # writing history for foreign-country events was a pre-existing gap
    # (see the design doc's "Problem" section, point 2) — nothing in this
    # codebase ever scores a non-USD instrument, so those rows were pure
    # bloat and, worse, could leak into webapp/app.py's recently-resolved
    # backfill. calendar_events is exactly "USD, Low+" — the correct scope.
    for event in calendar_events:
        upsert_event_history(conn, event, classify_surprise(event), now_for_history)
        # "Micro lens" reconciliation (docs/macro-calendar-design-2026-08-16.md):
        # every real event FF's feed returns gets a chance to confirm a
        # macro_calendar row (scripts/refresh_macro_calendar.py's FRED-sourced
        # month-ahead estimate) with FF's real exact time. No-ops (returns
        # False) if no macro row exists for this occurrence — normal, not
        # every FF event necessarily has a prior FRED-sourced entry.
        confirm_macro_calendar_event(conn, event.title, event.event_time_utc, now_for_history)

        # FRED actuals fallback (docs/superpowers/specs/2026-08-26-fred-actuals-fallback-design.md):
        # FF's own `actual` is frequently missing or posts hours late,
        # confirmed recurring — only attempted for events that have
        # already released (a future event obviously has no actual yet
        # regardless of source) and only when FF hasn't supplied one
        # already. get_actual_from_fred() itself is a cheap no-op (a dict
        # lookup, no request) for any title outside its ~10-title
        # coverage, so this is safe to call unconditionally here.
        if event.actual is None and event.event_time_utc <= now_for_history:
            fred_actual = get_actual_from_fred(event.title, event.event_time_utc)
            if fred_actual is not None:
                fred_event = dataclasses.replace(event, actual=fred_actual)
                upsert_event_history(
                    conn, fred_event, classify_surprise(fred_event), now_for_history,
                    source="fred",
                )
```

Then update the scoring loop (originally `for event in events:` inside the `for ticker in tracked_symbols:` loop) to iterate `scoring_events` instead of `events`:

```python
            for event in scoring_events:
                result = score_event_for_symbol(event, symbol_class)
```

(Only that one line's variable name changes — everything else in the scoring loop body is untouched.)

Finally, update the function's closing return statement:

```python
    return scoring_events
```

- [ ] **Step 4: Run tests to verify they pass, and run the whole scheduler test file**

Run: `python -m pytest tests/test_webapp_scheduler.py -v`
Expected: all PASS, including the two new tests. Any pre-existing test that patches `filter_relevant_events` with `side_effect=lambda events, **kwargs: events` (returns input unchanged regardless of `min_impact`) will now be called twice per cycle (once for `min_impact="Low"`, once for `min_impact="Medium"`) instead of once — check call counts in any test that asserts `mock_filter.assert_called_once()`; if one does, update it to assert on the specific `min_impact="Medium"` call instead (matching this file's existing pattern for asserting specific kwargs, e.g. `mock_filter.assert_any_call(mock_fetch.return_value, min_impact="Medium")`).

- [ ] **Step 5: Commit**

```bash
git add webapp/scheduler.py tests/test_webapp_scheduler.py
git commit -m "feat: track Low-impact USD events for calendar/history, keep scoring at Medium+"
```

---

### Task 4: Filter `/api/predictions`'s recently-resolved backfill to Medium+

**Files:**
- Modify: `webapp/app.py:254-267` (the `recently_resolved` list comprehension inside `get_predictions()`)
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `data_layer.calendar_feed.IMPACT_RANK` (Task 1), `webapp.store.get_resolved_event_history()` returning `EventHistoryRow` with `.impact: Optional[str]` (Task 2).
- Produces: no new public interface — this closes the leak described in the design doc's "Problem" point 2. A resolved event whose `impact` is `None` (legacy row, migration gap) or `"Low"` can no longer appear in `/api/predictions`'s `events` list via this backfill path.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_webapp_app.py`. Find this file's existing test(s) for the recently-resolved backfill (search for `recently_resolved` or `PREDICTIONS_RECENT_RESOLVED_RETENTION_DAYS` in that file) and add these alongside them, reusing whatever DB-seeding helpers that file already provides for `event_history` rows and the Flask test client:

```python
def test_recently_resolved_backfill_excludes_low_impact_event():
    print("=== /api/predictions: a resolved Low-impact event does NOT get backfilled into the events/cards list ===")
    conn = get_connection(TEST_DB_PATH)
    now = dt.datetime.now(dt.timezone.utc)
    low_event = EconomicEvent(
        title="Housing Starts (Test)", country="USD", impact="Low",
        event_time_utc=now - dt.timedelta(hours=2),
        forecast="1.35M", previous="1.32M", actual="1.40M",
    )
    upsert_event_history(conn, low_event, surprise_direction="higher", now=now)
    conn.close()

    client = app.test_client()
    resp = client.get("/api/predictions")
    data = resp.get_json()

    titles = {
        event["event_title"] if "event_title" in event else event.get("title")
        for prediction in data["predictions"]
        for event in prediction["events"]
    }
    assert "Housing Starts (Test)" not in titles
    print("PASS\n")


def test_recently_resolved_backfill_still_includes_medium_impact_event():
    print("=== /api/predictions: a resolved Medium-impact event is still backfilled — this task narrows the threshold, it doesn't remove the feature ===")
    conn = get_connection(TEST_DB_PATH)
    now = dt.datetime.now(dt.timezone.utc)
    medium_event = EconomicEvent(
        title="Retail Sales m/m (Test)", country="USD", impact="Medium",
        event_time_utc=now - dt.timedelta(hours=2),
        forecast="0.3%", previous="0.2%", actual="0.4%",
    )
    upsert_event_history(conn, medium_event, surprise_direction="higher", now=now)
    conn.close()

    client = app.test_client()
    resp = client.get("/api/predictions")
    data = resp.get_json()

    titles = {
        event["event_title"] if "event_title" in event else event.get("title")
        for prediction in data["predictions"]
        for event in prediction["events"]
    }
    assert "Retail Sales m/m (Test)" in titles
    print("PASS\n")
```

Check this test file's existing conventions before finalizing: the exact dict key for an event's title inside `prediction["events"]` entries (`event_title` vs `title`) and how `TEST_DB_PATH`/`get_connection`/`app`/`EconomicEvent`/`upsert_event_history` are already imported and reset between tests (this file already has `event_history`-seeding tests for the retention-window feature — match that exact setup/teardown pattern instead of introducing a new one).

- [ ] **Step 2: Run tests to verify their status**

Run: `python -m pytest tests/test_webapp_app.py -k "recently_resolved_backfill" -v`
Expected: `test_recently_resolved_backfill_excludes_low_impact_event` FAILS (the Low-impact title currently IS present — that's the bug this task fixes). `test_recently_resolved_backfill_still_includes_medium_impact_event` PASSES already (today's behavior already includes Medium+ — this test only guards against a future regression while narrowing the filter).

- [ ] **Step 3: Filter the backfill to Medium+**

In `webapp/app.py`, add the import at the top of the file (alongside the existing `from webapp.store import (...)` block):

```python
from data_layer.calendar_feed import IMPACT_RANK
```

Replace the `recently_resolved` list comprehension:

```python
    now = dt.datetime.now(dt.timezone.utc)
    retention_cutoff = now - dt.timedelta(days=PREDICTIONS_RECENT_RESOLVED_RETENTION_DAYS)
    existing_keys = {(e["title"], e["event_time_utc"]) for e in events}
    recently_resolved = [
        {
            "title": row.event_title, "country": "USD", "impact": None,
            "event_time_utc": row.event_time_utc,
            "forecast": row.forecast, "previous": row.previous, "actual": row.actual,
        }
        for row in get_resolved_event_history(conn)
        if dt.datetime.fromisoformat(row.event_time_utc) >= retention_cutoff
        and (row.event_title, row.event_time_utc) not in existing_keys
        # Medium+ only — IMPACT_RANK.get(row.impact, 0) is 0 for both a
        # genuinely Low-impact row and a legacy/impact-unknown row (impact
        # IS NULL, e.g. a row written before webapp/store.py's impact
        # column existed), and 0 is always below IMPACT_RANK["Medium"].
        # That's the deliberate fail-safe: when impact tier is unknown,
        # treat it as NOT card-worthy rather than risk showing one for
        # something that might be Low-impact (design doc: "recently
        # resolved backfill: scope to USD Medium+ only").
        and IMPACT_RANK.get(row.impact, 0) >= IMPACT_RANK["Medium"]
    ]
```

- [ ] **Step 4: Run tests to verify they pass, and run the whole app test file**

Run: `python -m pytest tests/test_webapp_app.py -v`
Expected: all PASS, including both new tests.

- [ ] **Step 5: Commit**

```bash
git add webapp/app.py tests/test_webapp_app.py
git commit -m "fix: exclude Low-impact/impact-unknown events from recently-resolved backfill"
```

---

### Task 5: Whole-feature verification

**Files:** none modified — this task runs the full suite and a live manual check, no code changes.

- [ ] **Step 1: Run the entire test suite**

Run: `python -m pytest tests/ -v`
Expected: all PASS (same pre-existing known-unrelated failure count as before this plan started, if any — do not treat that one as new breakage; if the count of failures changed, stop and investigate before proceeding).

- [ ] **Step 2: Confirm the accumulator is untouched**

Run: `python -m pytest tests/test_backtest_accumulator.py -v`
Expected: all PASS, unmodified by this plan — confirms `scoring/backtest_accumulator.py` still only ever sees High + the 3-title `ACCUMULATOR_MEDIUM_ALLOWLIST`, exactly as before.

- [ ] **Step 3: Manual live check against the running engine**

With the live dashboard running (`http://127.0.0.1:5001/`):
- `curl http://127.0.0.1:5001/api/calendar` — confirm at least one `"impact":"Low"` USD event now appears in the response (if none is currently on the calendar, this step can be deferred to the next natural scheduler cycle after deploy — not a blocker).
- `curl http://127.0.0.1:5001/api/predictions` — confirm no Low-impact event's title appears anywhere in any `predictions[].events[]` entry.
- Open the Calendar tab in the browser, click into a date with a Low-impact event, and confirm its actual/forecast/previous shows in the date panel with no essence-score gauge for it (same "no essence score yet" treatment already used for genuinely unscored events, per `webapp/static/app.js`'s existing `showDatePanel` logic — no frontend change was needed for this, since Low events simply never get a `prediction_runs` row to display in the first place).

- [ ] **Step 4: Restart the live engine on the merged code**

Follow the same restart procedure already established for prior changes this session: identify the running dashboard/accumulator PIDs, stop them, relaunch via `scripts\run_engine.bat`, confirm the dashboard comes back up (HTTP 200 on port 5001) and the accumulator process is alive.

---

## Self-Review Notes

- **Spec coverage:** Low-impact tracking (Task 3), no card/gauge for Low events (Task 3's `scoring_events` split + Task 4's backfill filter — the two places a card could otherwise originate), accumulator untouched (Task 5 Step 2 verifies, no code change), `event_history` USD-only scoping (Task 3's `calendar_events` replacing `all_events` in the history loop), recently-resolved leak closed (Task 4). NON_MARKET_MOVING tag is explicitly out of scope per the design doc — no task for it, correctly.
- **Placeholder scan:** none found — every step has real code, real test bodies, real commands.
- **Type consistency:** `EventHistoryRow.impact: Optional[str]` (Task 2) is the single new field; Task 4 consumes it via `IMPACT_RANK.get(row.impact, 0)`, matching the `Optional[str]` type (a `None` key lookup returns the default `0`, no crash). `run_scoring_cycle()`'s return type (`Optional[list[EconomicEvent]]`) is unchanged — it now returns `scoring_events` instead of `events`, same list shape and meaning as before this plan.
