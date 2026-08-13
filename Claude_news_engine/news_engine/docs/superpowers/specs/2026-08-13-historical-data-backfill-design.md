# Historical Data Backfill (Jan 2026 → Live Start) — Design

## Problem

Both databases only contain real data from whenever live tracking
actually began this session — `webapp/store.py`'s `event_history` and
`scoring/backtest_store.py`'s `predictions`/`print_predictions` are both
empty for every USD High-impact event before that point. The History tab
shows nothing for January–[live start], and trend-streak scoring
(`webapp/trend.py`'s `compute_trend_signal()`, fed by `event_history`)
has no real prior occurrences to build a streak from for months of real,
researchable events.

## Scope boundary

- Covers every High-impact USD event from **January 1, 2026** through
  whichever date the live system's earliest real captured row already
  covers (the actual cutoff is determined at implementation time by
  reading the earliest `recorded_at_utc`/`scored_at_utc` row in each DB —
  not hardcoded in this spec, since it depends on exactly when live
  tracking started).
- Covers **both** pipelines: calendar-side `event_history` (forecast/
  previous/actual — powers trend streaks and the History tab's numeric
  columns) and accumulator-side `predictions`/`print_predictions`
  (powers the History tab's NE Prediction + Confirmed/Missed).
- **No Kalshi backfill.** `kalshi_reads` prices a real-money market *at
  the time of the read* — there is no way to reconstruct "what the
  market thought in January" months later with any integrity. Historical
  rows simply have no `kalshi_reads` entry, same as any other absent
  signal in this system's established "absent, not fabricated"
  convention.
- **No article backfill.** The accumulator's real signal is built from
  actual timestamped articles (`scoring/backtest_accumulator.py`'s
  `build_event_news_bundle`) — reconstructing "what articles existed and
  when" for January is not something research can genuinely recover with
  real timestamps. Seeded `predictions`/`print_predictions` rows are a
  **researched reconstruction of the correct call**, not a replay of the
  live pipeline — see Provenance below for exactly what that means and
  how it's marked.
- One-off script, not a recurring job. Run once (or once per author
  session, incrementally, idempotently — see Idempotency below), not
  wired into `run_all.py` or any scheduler.

## Provenance — the central design decision

Every prior feature in this project has held to "absent, not fabricated"
(the History tab's `unjudged_reason` field, the print-call shrug
exclusion, Kalshi's liquidity gate). A hand-researched historical row is
categorically different from a live-captured one: there's no real
pre-event article timestamp trail, no real print-direction lexicon hit
count at the actual moment, just a researched forecast/previous/actual
triple and — where reconstructable — a researched judgment of what the
correct call would have been.

**Both `event_history` and `predictions`/`print_predictions` gain a new
`source` column: `'live'` | `'seeded'`, defaulting to `'live'` for the
existing schema's implicit meaning (see Migration below).**

- **`event_history` (calendar side):** forecast/previous/actual are
  **facts** — a researched actual CPI print is exactly as real as a
  live-captured one. `source='seeded'` here is purely informational
  (shown as a badge in the History tab, e.g. a small "(seeded)" label),
  and feeds trend-streak scoring **identically** to a live row — the
  streak math (`webapp/trend.py`) doesn't care how the fact was
  captured, only what the fact is.
- **`predictions`/`print_predictions` (accumulator side):** this is
  different in kind. A live row's `direction`/`confidence` came from the
  actual scoring engine running on real articles at the time. A seeded
  row's `direction`/`confidence` is a **researcher's reconstruction of
  what the engine's logic would plausibly have called**, informed by the
  same kind of forecast/expectation framing that was actually being
  reported at the time (same evidence standard as
  `tests/run_historical_backtest.py`'s existing 14 cases) — never
  fabricated as "the engine ran and confidently said X." `article_count`
  is set to `0` for every seeded row (there were no real articles fed
  in) and `contradiction_flag` to `False` — both are honest zeros, not
  guesses. `confidence` is deliberately kept conservative (see
  Confidence Discipline below) rather than asserting high certainty
  about a reconstruction.
- The History tab (`webapp/history.py`, `webapp/static/app.js`) gains a
  visible **"(seeded)"** badge next to any row where `source='seeded'` —
  same visual pattern as the existing `unchanged_vs_previous` `=` badge.
  This is purely a display concern; `outcome` (Confirmed/Missed)
  judgment logic is completely unchanged and applies identically to
  seeded and live rows, since a seeded row's `predicted_vs_forecast`
  vs. `event_history.surprise_direction` comparison is the same `==`
  check either way.

**Confidence discipline for seeded `predictions`/`print_predictions`
rows:** a seeded row's `confidence` must never exceed a fixed ceiling —
a new `SEEDED_PREDICTION_MAX_CONFIDENCE = 0.6` constant in
`config/settings.py`, enforced by the seed script (assert/clamp before
writing, not just a documentation convention) —
reflecting that a post-hoc researcher reconstruction, however
well-evidenced, is not the same epistemic category as a live multi-
article aggregate score. This also means seeded rows are naturally more
likely to fall into the existing shrug-exclusion path
(`NO_HIT_CONFIDENCE`/`MIN_TEXT_EVENT_CONFIDENCE`) if the reconstruction
is genuinely uncertain — which is correct, not a bug: "we're not
confident what the engine would have called this one" should render as
"No strong call," exactly like a real low-confidence live row does.

## Architecture

One new script, `scripts/seed_historical_data.py`:

1. **Data file**: a hand-authored Python data structure (list of event
   occurrences, each with real forecast/previous/actual sourced via
   `WebSearch`, plus — where a genuine reconstruction is possible — a
   researched `predicted_vs_forecast`/`direction` and a capped
   `confidence`, with a short cited `research_note` per occurrence
   explaining the source). Same authorship pattern as
   `tests/run_historical_backtest.py`'s existing 14 cases — this script
   reuses that research, plus new research to fill January onward, and
   writes it into the **live** databases instead of a throwaway test
   report.
2. **Calendar-side write**: for each occurrence, construct a duck-typed
   event object (or reuse `data_layer.calendar_feed.EconomicEvent`
   directly) and call `webapp.store.upsert_event_history()` — the exact
   same function the live scheduler calls — passing the researched
   `surprise_direction` (computed via the existing
   `data_layer.calendar_feed.classify_surprise()`, not hand-asserted,
   so seeded rows use identical classification logic to live ones).
   `source='seeded'` is threaded through a new optional param on
   `upsert_event_history()` (defaults to `'live'`, so every existing
   call site is unaffected — same non-breaking-optional-param pattern
   used throughout this project, e.g. `score_bundle()`'s `kalshi_read`).
3. **Accumulator-side write**: for occurrences where a genuine NE-
   prediction reconstruction is possible, call `scoring.backtest_store
   .record_prediction()` and, where the numeric-lexicon convention
   applies, `record_print_prediction_if_changed()` — same functions the
   live accumulator calls — with `source='seeded'`,
   `article_count=0`, `contradiction_flag=False`, and
   `confidence <= SEEDED_PREDICTION_MAX_CONFIDENCE`.
4. **Idempotency**: re-running the script must not duplicate rows.
   `event_history` already has a `UNIQUE(event_title, event_time_utc)`
   constraint with `ON CONFLICT DO UPDATE` semantics
   (`upsert_event_history()`), so it's naturally idempotent — reruns
   just refresh the same row. `predictions`/`print_predictions` have no
   such constraint today (live rows accumulate diff-aware, multiple rows
   per occurrence is normal) — the seed script must check
   "does a `source='seeded'` row already exist for this exact
   (event_title, instrument, event_time_utc)" before inserting, so
   reruns are safe. This is script-side logic, not a schema change.

## Migration

`_SCHEMA`'s `CREATE TABLE IF NOT EXISTS` blocks in both `webapp/store.py`
and `scoring/backtest_store.py` do not retroactively add a column to an
already-created database file — this project's DBs already exist on
disk with the old schema. `get_connection()` in both files needs a
guarded `ALTER TABLE ... ADD COLUMN source TEXT NOT NULL DEFAULT 'live'`
for each affected table, wrapped so it's a no-op if the column already
exists (SQLite has no `ADD COLUMN IF NOT EXISTS`; use a
`try/except sqlite3.OperationalError` guard, or a
`PRAGMA table_info(...)` check before altering — implementation detail
for the plan, not decided here). This runs once per connection open,
same lightweight cost profile as the existing `executescript(_SCHEMA)`
call it sits beside.

## Testing

- `upsert_event_history()`: new `source` param defaults to `'live'`,
  existing call sites/tests unaffected; explicit `source='seeded'` call
  is stored and read back correctly; a live row is never downgraded to
  `'seeded'` by a later conflicting write (the existing
  `WHERE excluded.actual IS NOT NULL` guard already protects
  actual/surprise_direction — confirm `source` follows the same
  never-regress-to-seeded-once-live rule if a live fetch ever re-touches
  a seeded occurrence).
- Migration: opening a connection against a pre-existing DB file (no
  `source` column) succeeds and adds the column; opening a connection
  against a fresh DB (column already in `CREATE TABLE`) succeeds without
  error; existing rows read back with `source='live'` after migration.
- `record_prediction()`/`record_print_prediction_if_changed()`: same
  default-to-`'live'` pattern, explicit `source='seeded'` round-trips.
- `scripts/seed_historical_data.py`: idempotency test — running twice
  against the same temp DB produces the same row count both times, not
  double.
- `webapp/history.py`/`webapp/static/app.js`: a seeded row's
  Confirmed/Missed judgment is identical to a live row's given the same
  `predicted_vs_forecast`/`surprise_direction` values (no special-casing
  in the judgment logic); the "(seeded)" badge appears only when
  `source='seeded'`.
- Trend-streak scoring (`webapp/trend.py`): a streak built from a mix of
  seeded and live `event_history` rows produces the same result as an
  all-live streak with identical forecast/previous/actual values —
  proves `source` has zero effect on the streak math, only on display.

## Explicitly out of scope (this pass)

- Kalshi historical backfill (no way to reconstruct a past market price
  with integrity — see Scope boundary).
- Real article backfill / replaying the live accumulator's article-based
  scoring against January's actual news (no real timestamped article
  archive to replay against for most sources — RSS has no archive,
  Alpha Vantage's retention is unconfirmed).
- Automating the research step itself (no LLM-driven "go find January's
  CPI data" pipeline — this is a hand-authored, cited data file, same
  standard as `tests/run_historical_backtest.py`).
- Any UI beyond the "(seeded)" badge — no separate seeded-only view, no
  filter toggle.
- Backfilling instruments other than what `config.settings.INSTRUMENTS`
  already tracks (XAUUSD, US30) — no new instrument coverage.
