# Live Tier 1 Dashboard Display — Design

**Date:** 2026-09-07
**Status:** Approved via conversational brainstorm (architectural path)
**Builds on:**
- `scoring/backtest.py`'s `Tier1Prediction` (Causation-Matrix Option A, 2026-09-06) — the value/confidence/source/predicted_direction shape this spec persists and displays. Untouched by this spec; this is purely a new consumer of the same dataclass.
- `tests/run_causation_matrix_option_a_backtest.py` / `tests/run_causation_matrix_option_a_pending_sep2026.py` — the two existing one-off scripts this spec's entry pattern extends (adds persistence; doesn't replace the research/judgment process).
- `scoring/backtest_store.py`'s `predictions` table — the shape and key (`event_title`, `instrument`, `event_time_utc`) this spec's new table mirrors.
- The co-released-event reconciliation feature (2026-09-04/05) — precedent for an additive `/api/predictions` field and a same-day frontend rendering pattern; this spec deliberately does NOT reuse its agree/disagree computation (see Scope boundary).

## Problem

Causation-Matrix Option A gave `BacktestCase`/`BacktestReport` a way to compare a Tier 1 causation-matrix prediction against sentiment's own call — but only for completed, past events, via one-off scripts with zero persistence and zero path to the live dashboard. There is currently no way for a Tier 1 prediction to reach a symbol card while the event is still pending — you have to run a script and read its printed output. The user wants Tier 1 calls visible on the dashboard, next to sentiment's own call, so they can be visually compared at a glance, going forward.

## Scope boundary

- **CPI and PPI only**, matching Option A's own scope — nothing about this spec widens which event types get a Tier 1 methodology; it just gives the two that already have one (and any added later) a place to show up live.
- **`predicted_direction` stays manually supplied, never auto-derived** — same rule as `Tier1Prediction` itself. This spec adds persistence and display for a value a human already decided; it builds no new judgment logic.
- **No live-fetch integration.** Logging a Tier 1 prediction still means a human runs a script after doing real research (WebSearch, primary sources) — this spec doesn't reach into Cleveland Fed/BLS/ISM's own APIs.
- **No agree/disagree computation on the live path.** The card shows both calls side by side, colored consistently, for the viewer to compare themselves — no new comparison logic runs at API-response time. `BacktestReport.agreement_rate()` stays exactly what it is: a backtest-only metric, computed after the fact over completed cases, never live.
- **No History tab changes** — this is a live-card feature only, same non-goal Option A itself already carried forward.
- **No retroactive backfill.** The two completed July 2026 cases (`tests/run_causation_matrix_option_a_backtest.py`) stay backtest-only artifacts; only new, forward-going entries get written to the new table.
- **Per-instrument, not per-event.** A Tier 1 prediction's `value`/`confidence`/`source` don't change per instrument, but `predicted_direction` can (XAUUSD is inverse-mapped, US30 is risk-sentiment-dampened) — a case covering both instruments logs two rows, same as sentiment's own `predictions` table already does per instrument.

## Architecture

### 1. New table — `tier1_predictions`, in `scoring/backtest_store.py`'s existing DB

```sql
CREATE TABLE IF NOT EXISTS tier1_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    value TEXT NOT NULL,
    confidence TEXT NOT NULL,          -- 'Certain' | 'Likely' | 'Guessing' -- a tag, never a float
    source TEXT NOT NULL,
    predicted_direction TEXT NOT NULL, -- 'bullish' | 'bearish' | 'neutral'
    logged_at_utc TEXT NOT NULL
);
```

A new `Tier1PredictionRow` dataclass mirrors the existing `Prediction` dataclass's shape (`id`, `event_title`, `instrument`, `event_time_utc`, `value`, `confidence`, `source`, `predicted_direction`, `logged_at_utc`) — the read-side return type for the function below.

Two new functions, mirroring the existing `record_prediction()`/`get_latest_prediction_for_occurrence()` pair exactly:

```python
def record_tier1_prediction(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
    value: str, confidence: str, source: str, predicted_direction: str,
    logged_at_utc: Optional[dt.datetime] = None,
) -> int: ...

def get_latest_tier1_prediction_for_occurrence(
    conn: sqlite3.Connection, event_title: str, instrument: str, event_time_utc: dt.datetime,
) -> Optional[Tier1PredictionRow]: ...
```

`confidence` is validated the same way `record_outcome()` already validates `actual_direction` against the `Direction` enum — reject anything outside `{"Certain", "Likely", "Guessing"}` at write time, so a typo can't silently reach the dashboard as an unrecognized tag.

### 2. Entry — one-off scripts persist, don't just print

`tests/run_causation_matrix_option_a_pending_sep2026.py`'s pattern extends by one call per instrument once the research/judgment is done:

```python
record_tier1_prediction(
    conn, "PPI m/m", "XAUUSD", PPI_EVENT_TIME_SEP2026,
    value=TIER1_PPI_SEP2026.value, confidence=TIER1_PPI_SEP2026.confidence,
    source=TIER1_PPI_SEP2026.source,
    predicted_direction=TIER1_PPI_SEP2026.predicted_direction.value,
)
```

The research and manual judgment process is completely unchanged — this only adds where the result ends up. The two already-drafted September cases (PPI/CPI, both instruments) get logged this way as part of implementation, not left as print-only.

### 3. `/api/predictions` integration (`webapp/app.py`)

Same per-event, per-ticker loop that already fetches `accumulator_prediction` — one more lookup, `get_latest_tier1_prediction_for_occurrence(backtest_conn, event["title"], ticker, event_time)`. New field on each event dict:

```python
"tier1_prediction": {
    "value": tier1_row.value,
    "confidence": tier1_row.confidence,
    "source": tier1_row.source,
    "predicted_direction": tier1_row.predicted_direction,
} if tier1_row is not None else None
```

Purely additive — `null` for every event with no logged row (everything except a CPI/PPI occurrence someone's actually researched and logged). No change to any existing field.

### 4. Frontend (`webapp/static/app.js`/`style.css`)

New `tier1PredictionHtml()`, rendered directly beneath whatever the sentiment line already shows (the real 📰 call, or the conflict badge from the reconciliation feature) — visual adjacency is the actual point, not a new computed relationship between them. New icon (🧮), new CSS class `.tier1-prediction`, colored via the SAME bullish/bearish/neutral palette `.article-prediction` already uses (`--bullish`/`--bearish`/`--neutral` CSS variables) — a shared color language across both lines is what makes "do these visually agree" readable at a glance without a computed badge. Confidence tag (`Certain`/`Likely`/`Guessing`) rendered as plain text, never converted to a percentage or a bar — that would recreate exactly the flattening Option A's own design was built to avoid.

## Error handling

- `get_latest_tier1_prediction_for_occurrence()` returning `None` (no row logged) is the overwhelmingly common case for every non-CPI/PPI event — never an error, never logged as a warning.
- If the lookup itself throws for any reason, `/api/predictions` catches it, logs a warning, and the event's `tier1_prediction` field is simply `null` for that response — same fail-open discipline as the reconciliation feature's own exception handling, never a route crash.

## Testing

- `tests/test_backtest_store.py` (or a focused addition to it): `record_tier1_prediction()`/`get_latest_tier1_prediction_for_occurrence()` round-trip; confidence-tag validation rejects an invalid value; per-instrument scoping (two rows for the same event_title/event_time_utc, different instrument, don't collide or overwrite each other).
- `tests/test_webapp_app.py`: extend `/api/predictions` tests — `tier1_prediction` present with the right shape for a logged CPI/PPI occurrence, `null` for everything else, no change to any existing field's shape.
- Frontend: no automated test (no JS suite in this codebase) — verified live in-browser once the two September cases are logged, confirming the new line renders under sentiment's own line with the right color and text, and every other card's existing rendering is unaffected.
