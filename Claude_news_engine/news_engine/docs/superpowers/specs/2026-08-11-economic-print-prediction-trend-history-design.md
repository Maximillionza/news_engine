# Economic-Print Prediction + Trend History — Design

## Problem

The engine's core spec (Masood, verbatim):

> A news engine that checks articles relating to major forex market events... the
> articles are analysed and data extracted to formulate an assessment and
> probability of where (against the targets set) the event will come in based on
> likely outcomes, the engine assess the articles context against probability and
> scores it against the symbol to determine the likely direction of trade. Post
> the event the engine should check where the event ended and if it predicted
> trade direction immediately after the event took place. It should store the
> metadata of the event for future assessments to better identify a trend (e.g.
> July CPI was @4.2% and came in at 4.5%, which is higher than the market
> predicted outcome but also higher than the previous result).

Two things this describes are not built:

1. **Explicit print-direction prediction** — an assessment of where the
   economic print itself will land relative to forecast, as a distinct stored
   step. Today the engine goes straight from article sentiment to symbol
   direction (`scoring/probability_engine.score_bundle()`); it never states
   "articles suggest CPI comes in hotter than forecast" as its own claim.
2. **Durable trend history** — `EconomicEvent` carries `forecast`/`previous`/
   `actual` fields and `usd_surprise_score()` computes a beat/miss magnitude,
   but nothing persists these across the weekly calendar rollover. Once a new
   week's Forex Factory pull replaces "July CPI" with "August CPI," July's
   forecast/previous/actual is gone. There is no way to answer "has CPI beaten
   forecast N releases running?"

## Scope boundary

This spec covers both halves as one build — they're tightly coupled (the
print-direction call becomes one of the things trend history stores). It does
**not** change any existing scoring math: `score_bundle()`,
`_is_material_change()`, `usd_surprise_score()`, and the `predictions`/
`outcomes`/`check_log` tables are all untouched. Everything here is additive:
two new tables, two new small modules, one new UI panel.

## Architecture

Two new tables, split by pipeline ownership — matching this project's
established pattern of keeping the essence-only dashboard and the
article-based accumulator decoupled.

### `event_history` (dashboard-owned)

Lives in `webapp/store.py`'s existing SQLite DB. Populated on every
`webapp/scheduler.py` fetch cycle, for every event on the calendar regardless
of impact level or symbol — free, no article cost, broadest possible
coverage.

```sql
CREATE TABLE IF NOT EXISTS event_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    forecast TEXT,
    previous TEXT,
    actual TEXT,
    surprise_direction TEXT,      -- 'higher' | 'lower' | 'in_line' | NULL
    recorded_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    UNIQUE(event_title, event_time_utc)
);
```

One row per event *occurrence* — `event_title` + its specific
`event_time_utc` together identify one release (e.g. "Core CPI m/m" on
2026-08-12 vs. the same title on 2026-07-14 are different rows, which is what
makes a trend queryable: `SELECT ... WHERE event_title = ? ORDER BY
event_time_utc DESC`).

Row lifecycle, via upsert:

- **First sight** (event appears on the calendar, pre-release): insert with
  `forecast`/`previous` populated, `actual`/`surprise_direction` NULL.
- **Later sight** (event has since printed, Forex Factory now shows
  `actual`): update `actual` and `surprise_direction`, leave
  `forecast`/`previous` untouched (they don't change after the fact).
- `surprise_direction` is the literal actual-vs-forecast comparison — "did
  the print come in above or below what was forecast" — **not** a
  USD-bullish/bearish judgment (that's a different question, already answered
  by `usd_surprise_score()`'s bullish/bearish-mapped magnitude, used
  elsewhere for instrument-score blending). It reuses
  `EVENT_SURPRISE_DIRECTION` only as an *is-this-title-trackable* gate — the
  same set of titles `usd_surprise_score()` already recognizes — not for its
  higher_bullish/higher_bearish values. Computed the same way
  `usd_surprise_score()` computes `pct_diff` (percent difference when
  `|forecast| > 1e-9`, else raw absolute difference): `'in_line'` when
  `abs(pct_diff) <= EVENT_HISTORY_IN_LINE_TOLERANCE` (new constant,
  `config/settings.py`, default `0.05` — a print within 5% of forecast counts
  as in-line), otherwise `'higher'` (actual > forecast) or `'lower'` (actual
  < forecast) by sign of `pct_diff`. If the title isn't in
  `EVENT_SURPRISE_DIRECTION`, or forecast/actual don't parse,
  `surprise_direction` stays NULL — never a guessed value.

### `print_predictions` (accumulator-owned)

Lives in `scoring/backtest_store.py`'s existing SQLite DB, alongside
`predictions`/`outcomes`/`dismissals`/`check_log`. Only produced for
High-impact USD events the accumulator is already actively scoring, since it
needs the fetched article bundle.

```sql
CREATE TABLE IF NOT EXISTS print_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    predicted_vs_forecast TEXT NOT NULL,   -- 'higher' | 'lower' | 'in_line'
    confidence REAL NOT NULL,
    article_count INTEGER NOT NULL,
    scored_at_utc TEXT NOT NULL
);
```

Diff-aware recording: a new row is only written when
`predicted_vs_forecast` differs from the latest stored call for that event
(direction flip), mirroring `_is_material_change()`'s "current sentiment is
the truth until articles contradict it" principle, just applied to a
categorical value instead of a probability threshold.

## Data flow

### Capture: `webapp/scheduler.py`

One new call after the existing `save_calendar_snapshot_if_changed()`:

```python
def record_event_history(conn, events, now):
    for event in events:
        surprise = classify_surprise(event)  # EVENT_SURPRISE_DIRECTION lookup -> 'higher'/'lower'/'in_line'/None
        upsert_event_history(conn, event, surprise, now)
```

`classify_surprise()` lives in `data_layer/calendar_feed.py` next to
`usd_surprise_score()` (same inputs, same "no data" vs "no surprise"
distinction — returns `None` for either missing data or an unmapped title,
`'in_line'` only for a genuinely small forecast/actual delta).

`upsert_event_history()` lives in `webapp/store.py`, using
`INSERT ... ON CONFLICT(event_title, event_time_utc) DO UPDATE SET
actual = excluded.actual, surprise_direction = excluded.surprise_direction,
updated_at_utc = excluded.updated_at_utc WHERE excluded.actual IS NOT NULL` —
so a pre-release upsert (no actual yet) never blanks out a previously-recorded
actual on a later, stale re-fetch.

### Prediction: `scoring/backtest_accumulator.py`

One new sibling call to the existing `score_bundle()`, per event, using the
same already-fetched `EventNewsBundle` — no additional article fetch:

```python
print_call = score_print_direction(bundle, event)
if print_call is not None:
    store.record_print_prediction_if_changed(conn, event, print_call, now)
```

`score_print_direction()` is a new module, `scoring/print_direction.py`,
shaped like `scoring/sentiment.py`'s lexicon tier:

- Looks up `PRINT_SURPRISE_LEXICON.get(event.title)` (new dict in
  `config/settings.py`, alongside `EVENT_SURPRISE_DIRECTION`). No entry →
  returns `None` immediately, nothing scored, nothing written.
- Scans each article's text for higher/lower phrase hits from that event's
  lexicon entry.
- Returns `PrintCall(direction, confidence, article_count)`:
  `direction` is whichever side has more hits (`'in_line'` if zero hits on
  either side or an exact tie); `confidence` scales with hit count and
  agreement — unanimous hits score higher than a narrow majority, capped at
  the same ceiling the existing lexicon sentiment scorer uses.

Initial `PRINT_SURPRISE_LEXICON` coverage — the four highest-traffic events
already in `EVENT_SURPRISE_DIRECTION`:

```python
PRINT_SURPRISE_LEXICON = {
    "CPI m/m": {
        "higher": ["sticky inflation", "hotter than expected", "upside surprise", "inflation accelerat"],
        "lower":  ["cooling inflation", "softer than expected", "downside surprise", "disinflation"],
    },
    "Core CPI m/m": {
        "higher": ["sticky core inflation", "hotter than expected", "upside surprise"],
        "lower":  ["cooling", "softer than expected", "downside surprise"],
    },
    "Non-Farm Employment Change": {
        "higher": ["blowout jobs", "stronger than expected", "beat estimates", "hot jobs report"],
        "lower":  ["weaker than expected", "missed estimates", "soft jobs report", "payrolls disappoint"],
    },
    "Unemployment Rate": {
        "higher": ["rate ticks up", "unemployment rises", "labor market cooling"],
        "lower":  ["rate ticks down", "unemployment falls", "labor market tightening"],
    },
}
```

Expanding coverage to more events later is a config-only change — no code
changes required, matching how `EVENT_SURPRISE_DIRECTION` itself grows.

## UI

Two additions to the existing dashboard event cards. No new pages.

**1. Print-call badge**, next to the existing article-based read line.
`/api/predictions` gains a `print_prediction` field, sourced from a new
`backtest_store.get_latest_print_prediction()`:

```
📰 Article-based read: SELL 61% (backed by 127 articles)
📊 Print call: CPI likely HIGHER than forecast (62% confidence)
```

Omitted entirely — not shown, not "N/A" — when there's no lexicon coverage or
no call has been made yet for that event, consistent with this codebase's
"never fabricate a value" convention.

**2. History panel**, a "History ▾" toggle per event card, collapsed by
default. Expanding it fetches `GET /api/event_history?title=<event_title>`
(only on expand, no added cost to normal page load), backed by
`webapp/store.py`'s `get_event_history(conn, event_title, limit=6)` +
`summarize_trend(rows)`:

```
History ▾
  Jul 2026: forecast 0.3%, previous 0.4%, actual 0.4%  (in-line)
  Jun 2026: forecast 0.3%, previous 0.4%, actual 0.5%  (beat)
  May 2026: forecast 0.2%, previous 0.3%, actual 0.2%  (in-line)
  → Mixed — no clean streak over the last 3 prints
```

`summarize_trend()` is plain Python arithmetic over the returned rows — no
new dependency, no LLM call:

- Fewer than 2 rows with a non-NULL `actual` → `"Not enough history yet"`.
- Walk from most recent backward counting consecutive `'higher'` or
  `'lower'` — 2+ in a row → `"trending {direction} for N consecutive
  releases"`.
- Otherwise, count beat/miss (`'higher'`/`'lower'` vs. `'in_line'` doesn't
  count as either) over the returned window →
  `"beat forecast N of last M"` (M = count of non-`'in_line'` rows) if beats
  are a clear majority, `"missed forecast N of last M"` if misses are, else
  `"Mixed — no clean streak over the last N prints"`.

## Testing

- `event_history` upsert: first-sight insert (forecast/previous only, actual
  NULL); later-sight update fills `actual`/`surprise_direction` without
  touching forecast/previous; a stale re-fetch with `actual=None` never
  blanks a previously-recorded actual (the `WHERE excluded.actual IS NOT
  NULL` guard).
- `classify_surprise()`: unmapped title → `None`; unparseable forecast/actual
  → `None`; small delta → `'in_line'`; matches `usd_surprise_score()`'s
  existing higher_bullish/higher_bearish direction convention.
- `score_print_direction()`: no lexicon entry → `None`, nothing written; all
  hits on one side → high confidence; mixed hits → lower confidence, correct
  majority side; zero hits → `'in_line'`, low confidence.
- `record_print_prediction_if_changed()`: identical `predicted_vs_forecast`
  as the latest stored row → no write; a flip → new row.
- `summarize_trend()`: 0 rows, 1 row, all-pending (`actual IS NULL`) rows,
  a clean streak, and a mixed set — each produces the correct message, never
  a crash or a fabricated streak.
- `/api/event_history`: unknown title → empty list (200, not 500).
- Full existing regression suite (all `tests/test_*.py`) re-run and confirmed
  passing unchanged — this feature touches no existing scoring/persistence
  code path, only adds new tables/modules/endpoints.

## Explicitly out of scope (this pass)

- Feeding the print-direction call or the trend streak back into
  `score_bundle()`'s instrument scoring — this spec is additive/display-only.
  A future spec can revisit once there's enough real `print_predictions`
  data to know whether it's actually predictive.
- Numeric print-value estimation (e.g. inferring "articles imply ~4.4%") —
  only the categorical higher/lower/in-line call.
- Lexicon coverage beyond the 4 initial events — same "add config, not code"
  path as `EVENT_SURPRISE_DIRECTION`, deferred to when there's a concrete
  need.
