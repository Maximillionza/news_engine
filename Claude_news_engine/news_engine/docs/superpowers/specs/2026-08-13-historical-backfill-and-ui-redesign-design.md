# Historical Data Backfill + Dashboard/Calendar UI Redesign — Design

> Supersedes `docs/superpowers/specs/2026-08-13-historical-data-backfill-design.md`
> — same Jan-2026 backfill goal, but the Provenance/Architecture sections
> below replace that document's "researcher reconstruction, confidence-
> capped" model entirely, per explicit correction: *nothing seeded may be
> simulated or recreated — article data and price-outcome data are only
> ever real, best-effort retrievals; where genuine data isn't available,
> that layer is simply absent.* Merged into one spec with the UI redesign
> because the History tab's emptiness (part of the UI review) and the
> backfill gap are two faces of the same problem, and both touch
> `webapp/history.py`/`webapp/static/`.

## Part 1: Historical Data Backfill (Jan 2026 → live start)

### Problem

Unchanged from the original spec: both databases are empty before live
tracking started this session, so the History tab shows nothing and
trend-streak scoring has no real prior occurrences for months of
real, already-happened events.

### Revised principle: real data or nothing — never reconstructed

Three distinct layers, each with its own genuine-data-or-absent rule:

**1. Event facts (forecast/previous/actual) — MANDATORY, researched.**
These are historical record, not simulation — a real CPI print that
actually happened is a fact you can cite (BLS, Reuters, Kitco, etc.),
the same standard `tests/run_historical_backtest.py`'s 14 existing cases
already use for their `actual_move_note`. `source='seeded'` marks these
as backfilled, not live-captured, but the numbers themselves are real.

**2. Article-based prediction — OPTIONAL, real-retrieval-only, no
reconstruction.** For each occurrence, attempt a genuine historical
article pull via `data_layer.news_feed.AlphaVantageNewsSource` (already
supports a `since_utc`/`time_from`-style historical query — confirmed in
code, retention window not yet confirmed for Alpha Vantage's free tier).
If real, timestamped articles come back for that event's pre-event
window, feed them through the **actual, unmodified** scoring path
(`scoring.probability_engine.score_bundle()`, exactly as the live
accumulator calls it — same `build_event_news_bundle`-equivalent
construction) to produce a genuinely-computed prediction — not a
human-typed guess. If Alpha Vantage returns nothing usable for that
window (likely for anything more than ~a few months old, given typical
free-tier retention), **no `predictions`/`print_predictions` row is
written for that occurrence at all.** No fallback, no approximation, no
confidence-capped guess — absent, exactly like every other missing
signal in this system.

**3. Price-outcome confirmation — OPTIONAL, real-retrieval-only.** For
each occurrence, run the exact existing
`scoring.outcome_classifier.classify(instrument, event_time_utc)` —
already a genuine before/after real-price mechanism via Dukascopy
(`data_layer.dukascopy_feed.get_price_at()`), already proven to work for
any historical date (this is precisely what live outcome confirmation
already does via `scripts/confirm_backtest_outcomes.py --auto`, unchanged
here — same function, same thresholds, just invoked against a January
timestamp instead of yesterday's). Clear result →
`scoring.backtest_store.record_outcome()`, same as live. Ambiguous or a
fetch failure → **no `outcomes` row written**, same as live's "left for
manual review" state (there is no "manual review" step for backfilled
history — an unconfirmed occurrence just stays unconfirmed, shown as
"Awaiting confirmation" in the History tab exactly like any other
unconfirmed prediction).

**No `SEEDED_PREDICTION_MAX_CONFIDENCE` cap, no "researcher
reconstruction."** A prediction row only exists if it was genuinely
computed by `score_bundle()` against genuinely retrieved articles — its
confidence is whatever the real scoring engine actually produced, same
as any live prediction, because it *is* a real run of the same engine,
just against older data. This removes an entire mechanism from the prior
spec rather than adding one.

**No Kalshi backfill** (unchanged from the original spec) — a real-money
market price can't be reconstructed after the fact with any integrity;
there is no "real retrieval" path for this one at all, so it's simply
never attempted.

### Architecture

One new script, `scripts/seed_historical_data.py`:

1. **Event list**: a hand-authored list of (event_title, event_time_utc,
   forecast, previous, actual) tuples for every High-impact USD event
   from Jan 1, 2026 through the live system's actual earliest real row
   (determined at implementation time, not hardcoded here) — sourced via
   `WebSearch`, same citation discipline as
   `tests/run_historical_backtest.py`.
2. **Calendar-side write**: `webapp.store.upsert_event_history()` per
   occurrence, `source='seeded'` (new optional param, defaults `'live'`
   — every existing call site unaffected), `surprise_direction` computed
   via the real `data_layer.calendar_feed.classify_surprise()`, not
   hand-asserted.
3. **Article-based attempt** (per occurrence, per tracked instrument):
   call `AlphaVantageNewsSource` with the event's real pre-event window;
   on a real, non-empty, genuinely-dated result, run it through
   `score_bundle()` and write via `scoring.backtest_store.record_prediction()`
   / `record_print_prediction_if_changed()`, `source='seeded'`; on empty/
   no usable result, write nothing for that occurrence — logged, not
   silent (`print()` a one-line skip reason per occurrence, so a report
   at the end of the run shows exactly how many of N occurrences got a
   real prediction vs. how many were skipped for lack of real articles).
4. **Outcome-confirmation attempt** (per occurrence, per tracked
   instrument with a written prediction): call
   `scoring.outcome_classifier.classify()`; clear result →
   `record_outcome()`, `source='seeded'` (new column, same pattern);
   ambiguous/failed → nothing written, logged the same way as #3.
5. **Idempotency**: `event_history` is already upsert-safe
   (`UNIQUE(event_title, event_time_utc)`). `predictions`/
   `print_predictions`/`outcomes` need a pre-insert check — "does a
   `source='seeded'` row already exist for this exact occurrence" — so
   reruns don't duplicate (script-side logic, no schema change beyond
   the new `source` column).

### Migration

Both `webapp/store.py` and `scoring/backtest_store.py`'s `get_connection()`
need a guarded `ALTER TABLE ... ADD COLUMN source TEXT NOT NULL DEFAULT
'live'` for every affected table (`event_history`, `predictions`,
`print_predictions`, `outcomes`) — `CREATE TABLE IF NOT EXISTS` doesn't
retroactively add a column to an already-created DB file. Guard against
`sqlite3.OperationalError` (column already exists) or check
`PRAGMA table_info` first — exact mechanism decided in the plan.

### Testing

- `upsert_event_history()`/`record_prediction()`/`record_print_prediction_if_changed()`/
  `record_outcome()`: new `source` param defaults to `'live'`, existing
  call sites/tests fully unaffected; explicit `source='seeded'` round-trips.
- Migration: opening a connection against a pre-existing DB (no `source`
  column) succeeds and adds it; a fresh DB succeeds without error;
  existing rows read back `source='live'` after migration.
- `scripts/seed_historical_data.py`: an occurrence with a real
  Alpha-Vantage-returned article set produces a real `predictions` row
  computed by the actual `score_bundle()` (test with a mocked
  `AlphaVantageNewsSource` returning synthetic-but-realistic articles,
  asserting the recorded prediction matches what `score_bundle()` alone
  would compute against those same articles — proving no separate
  reconstruction path exists). An occurrence with an empty/failed
  article fetch writes an `event_history` row but zero `predictions`
  rows. A clear Dukascopy classification writes a real `outcomes` row;
  an ambiguous one writes nothing. Idempotency: running the script twice
  against the same temp DB produces identical row counts both times.
- `webapp/history.py`: a seeded row's Confirmed/Missed judgment is
  identical to a live row's given the same
  `predicted_vs_forecast`/`surprise_direction` (no special-casing).
- Trend-streak scoring (`webapp/trend.py`): a streak built from mixed
  seeded/live `event_history` rows matches an all-live streak with
  identical forecast/previous/actual — proves `source` affects display
  only, never the math.

### Explicitly out of scope (this pass)

- Kalshi historical backfill (no genuine retrieval path exists at all).
- Any UI beyond the existing History tab rendering a "(seeded)" badge
  where `source='seeded'` (small, informational — see Part 2's History
  tab note; no separate seeded-only view or filter toggle).
- Automating the WebSearch research step for event facts (still
  hand-authored/cited, same standard as the existing 14 backtest cases).
- Backfilling instruments beyond `config.settings.INSTRUMENTS`
  (XAUUSD, US30).

---

## Part 2: Dashboard + Calendar UI Redesign

### Problem

Confirmed via direct code review (`webapp/app.py`, `webapp/static/app.js`,
`webapp/static/index.html`):

1. **A real bug, not just thin UI**: `/api/predictions` (`app.py:154-157`)
   gates the accumulator's `article_prediction`/`print_prediction` fetch
   behind the essence-only score (`prediction_runs`) existing for that
   symbol first (`if not runs: continue`). A newly-added symbol shows a
   fully blank "Awaiting next tracked event" card until
   `webapp/scheduler.py`'s next cycle scores it — even when the
   accumulator already has a real, independently-computed opinion sitting
   in its own database. One layer's absence is currently hiding two
   other layers that have nothing to do with it.
2. **Thin surface for what's being computed**: `ProbabilityResult`
   already computes per-contribution weights and agreement/coverage
   stats (`scoring/probability_engine.py`) that never reach the UI — a
   card shows one final number, never the composition behind it. Kalshi's
   real market read (the system's highest-trust signal) has zero UI
   surface at all.
3. **Calendar tab**: no impact-tier color coding despite `impact` already
   being in every event dict; no click-to-inspect-a-date interaction; the
   event list below the grid is an unfiltered dump of the whole fetched
   window, not scoped to a selected date; no per-symbol calls surfaced
   anywhere on the tab (cross-referencing the Dashboard tab by hand is
   the only option today).

### A. Decouple the dashboard's three prediction layers

`/api/predictions` restructured so essence-only score, article
prediction, print-direction call, and Kalshi read are each fetched and
serialized independently per (symbol, event) — none gated behind another.
`webapp/static/app.js`'s `renderCard()` renders whatever subset exists:
an essence score with no article prediction yet looks the same as today;
an article prediction with no essence score yet (the bug case) now
actually shows the real call instead of a blank "Awaiting" card. Each
layer's own absence still renders as absent, never fabricated — this is
a strictly additive fix, not a relaxation of that rule.

### B. "Why this call" breakdown panel + Kalshi surface

New collapsible panel per card (same expand/collapse pattern the
existing History toggle already uses), populated from a new
`/api/predictions` field carrying each fired contribution's type,
direction, and weight (`ProbabilityResult`'s existing internal
contribution list, not new scoring logic — purely exposing what's
already computed), plus the existing agreement/coverage numbers. Kalshi
gets a real line item — implied probability, direction, and read
staleness — in the same visual style `article_prediction`/
`print_prediction` already use (an icon + bold label + confidence caveat),
not buried inside the breakdown panel only.

### C. Calendar color-coding + click-to-inspect

- Impact-tier color coding: High/Medium/Low each get a distinct dot
  color (data already present in every event dict — pure CSS/render
  change, no new fetch).
- Default view highlights the nearest upcoming event's day cell, not
  just "today."
- Clicking any day cell opens a side panel listing that date's events,
  each with every tracked symbol's call for it — reusing
  `/api/event_history` for the occurrence data and a new lightweight
  per-date predictions lookup (server-side: filter the same data
  `/api/predictions` already computes down to a given date, not a new
  scoring path).
- The flat event list below the grid becomes scoped to the selected
  date (or the nearest-upcoming default) instead of dumping the whole
  fetched window.

### History tab

No new UI work required beyond a "(seeded)" badge (Part 1) — the
existing `renderHistoryTable()`/`GET /api/history` path is otherwise
already correct; its emptiness today is entirely explained by Part 1's
gap, not a UI defect.

### Testing

- `/api/predictions`: a symbol with only an article prediction (no
  essence score yet) now serializes it; a symbol with genuinely nothing
  in any layer still serializes the existing "no events" shape. Existing
  tests for the fully-populated case still pass unchanged (additive,
  not restructured field shapes for what already worked).
- Breakdown panel: contribution list matches what `score_bundle()`
  actually computed for a given fixture bundle — no drift between what's
  shown and what's scored.
- Calendar: impact color mapping is a pure function of `impact` string →
  CSS class, testable in isolation; click-to-inspect's date-filtering
  logic (server or client, decided in the plan) has a dedicated test for
  "events on this exact date, nothing from adjacent dates."
- Frontend: no automated JS test harness exists in this codebase
  (established pattern) — verified live via browser after implementation,
  same as every other UI change this session.

### Explicitly out of scope (this pass)

- Any change to the underlying scoring math (`score_bundle()`'s
  contribution weights, thresholds) — this redesign only changes what's
  *displayed*, never what's *computed*.
- A dedicated Kalshi-only tab or historical Kalshi chart.
- Calendar month navigation beyond the current single-month view (no
  prev/next month browsing) unless the plan finds it trivially cheap
  alongside the click-to-inspect work.
- Mobile-specific layout work.
