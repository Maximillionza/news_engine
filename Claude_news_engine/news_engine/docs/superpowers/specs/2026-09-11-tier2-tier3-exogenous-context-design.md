# Tier 2/3 Exogenous Market Context — Design

**Date:** 2026-09-11
**Status:** Approved via conversational brainstorm (architectural path)
**Builds on:**
- `docs/News_Engine_Causation_Matrix_v2.xlsx`'s `Discovery_Detector_Spec` sheet — the anomaly-detection design this spec implements almost verbatim: "A move beyond approx. 2 standard deviations on a session with no matching entry in either the periodic calendar or [`AdHoc_Category_Taxonomy`]... pull same-day headlines via existing `news_feed.py`/`rss_sources.py`... attach best-candidate cause."
- `AdHoc_Category_Taxonomy` — 8 real, sourced exogenous categories (oil/OPEC+, geopolitical war-driven oil shock, Fed-independence shocks, Fed Chair transitions, tariff actions, government shutdown, Treasury buyback changes, credit-rating actions), each with at least one real logged in-window instance. This spec's headline-research step classifies a detected anomaly against this taxonomy where it fits, rather than inventing new categories per shock.
- `scoring/backtest.py`'s `Tier1Prediction`/`BacktestCase` (Causation-Matrix Option A) — this spec never modifies a stored `Tier1Prediction` row; it adds a live-display-only confidence adjustment layered on top, same non-destructive relationship Batch 4's `tier1_sentiment_conflict` already established for a different cross-check.
- Batch 4's `tier1_sentiment_conflict` (`webapp/predictions_service.py`, `webapp/conflict.py`) — the precedent this spec's live-surfacing mechanism reuses directly: a new field on the event dict, computed after the existing per-event data is assembled, rendered as a warning badge.
- `data_layer/dukascopy_feed.py` / `scoring/outcome_classifier.py` — the existing Dukascopy tick-fetch pattern (`get_price_at()`) this spec's daily-move computation reuses, not a new price integration.

## Problem

The 2026-09-10 PPI miss (Tier 1 called `Certain`/bullish, wrong) was a direct symptom of a documented, never-built gap: `Tier1Prediction` is a narrow, per-event numeric calculation (BLS actuals, ISM Prices Paid, Cleveland Fed nowcast, etc.) that has no way to know whether something *outside* that calculation — an oil shock, a geopolitical event, a Fed-independence crisis — was also moving the instrument that day. The workbook designed a real answer to this (`AdHoc_Category_Taxonomy` + `Discovery_Detector_Spec`) months before Option A shipped; nothing from either sheet has ever been coded. This spec builds the detector, not a redesign of the taxonomy — the taxonomy and its 8 categories already exist and are already sourced.

## Scope boundary

- **Confidence-only, never direction.** A detected anomaly can downgrade a Tier 1 row's *displayed* confidence one tier (Certain→Likely→Guessing) on the live dashboard. It never touches `predicted_direction`, never rewrites or deletes the stored `Tier1Prediction` row, and never invents a directional call of its own — same "manual judgment only" boundary `Tier1Prediction.predicted_direction` itself already enforces, extended to this new signal.
- **Detector, not a checklist.** No code walks `AdHoc_Category_Taxonomy`'s 8 categories looking for a match before a real anomaly exists. The detector fires only on a statistically real, unexplained move; the taxonomy is consulted *after* a real anomaly is found, to classify it, not to generate false positives from a fixed list.
- **CPI/PPI Tier 1 rows only, for now** — same event-type boundary Option A itself held. The detector computes anomalies across five market-wide series (below), but its downstream effect is scoped to downgrading confidence on the CPI/PPI `Tier1Prediction` rows already live on the dashboard, not to any new event type.
- **No automated headline-to-taxonomy classification.** Attaching a same-day headline as the "best-candidate cause" is a human/LLM judgment step (the scheduled research task, same pattern as Tier 1's own research), not a keyword-matching algorithm.
- **No retroactive re-scoring.** A detected anomaly changes what the *live* dashboard shows today; it does not reach back and change any already-graded historical `Tier1ComparisonRow` or outcome.

## Open technical risk, flagged before any code is written

`data_layer/dukascopy_feed.py`'s `_INSTRUMENT_MAP` currently covers exactly two series: `XAUUSD` and `US30`. **DXY, 10Y, and 30Y are not currently known to be available through this project's existing Dukascopy integration** — Dukascopy's own catalog covers FX/metals/CFDs/indices, and it is not yet confirmed whether a US Dollar Index proxy or Treasury-yield-equivalent series exists there in a form `get_price_at()` can consume. The implementation plan's first task must be a real, throwaway spike (per `superpowers:brainstorming`'s own spike path) that checks `dukascopy_python`'s instrument catalog directly for DXY/10Y/30Y equivalents *before* the rest of this architecture is built on top of an assumption. If any of the three don't exist on Dukascopy, the honest fallback is dropping that series from the detector (documented as a real, disclosed gap, same as every other honestly-flagged limitation in this project) rather than substituting a different, unverified data source silently.

## Architecture

### 1. New module — `data_layer/discovery_detector.py`

```python
DETECTOR_SERIES = ["DXY", "10Y", "30Y", "XAUUSD", "US30"]  # US30 added beyond
# Discovery_Detector_Spec's original 4 -- this project tracks US30 as a
# real instrument; an unexplained equity-index move deserves the same
# detector, not silence. Flagged as a deliberate scope addition, reversible
# if you'd rather match the spec's original 4 exactly.

ANOMALY_STDEV_THRESHOLD = 2.0   # Discovery_Detector_Spec's own number, verbatim
BASELINE_WINDOW_DAYS = 20        # Discovery_Detector_Spec's own number, verbatim

@dataclass
class AnomalyResult:
    series: str
    move_pct: float
    baseline_mean: float
    baseline_stdev: float
    stdev_move: float            # (move_pct - baseline_mean) / baseline_stdev
    date: dt.date

def compute_daily_move(series: str, date: dt.date) -> Optional[float]:
    """Real Dukascopy tick at session open vs. session close for `date` — same get_price_at() pattern outcome_classifier.py already uses. None on any fetch failure, never fabricated."""

def rolling_baseline(series: str, as_of_date: dt.date, window_days: int = BASELINE_WINDOW_DAYS) -> Optional[tuple[float, float]]:
    """Mean and stdev of the `window_days` daily moves immediately BEFORE as_of_date -- never includes as_of_date itself, same no-lookahead discipline event_context.py's build_event_news_bundle() already enforces. None if fewer than window_days real moves are available (e.g. early in this feature's life, or a data gap)."""

def detect_anomaly(series: str, date: dt.date, calendar_events: list[EconomicEvent]) -> Optional[AnomalyResult]:
    """
    None if: compute_daily_move or rolling_baseline returned None (real
    data unavailable -- never guessed), the move is within
    ANOMALY_STDEV_THRESHOLD, OR a USD Medium+ impact calendar event already
    covers this date for a title plausibly linked to `series` (an expected
    move from a known release is not an anomaly -- same "the calendar
    already explains this" check Discovery_Detector_Spec itself specifies).
    """
```

### 2. Persistence — new `exogenous_shocks` table, `scoring/backtest_store.py`

Mirrors `tier1_predictions`' shape and occurrence-scoping conventions:

```sql
CREATE TABLE IF NOT EXISTS exogenous_shocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series TEXT NOT NULL,
    shock_date TEXT NOT NULL,           -- ISO date, not datetime -- this is a daily-move detector, not occurrence-scoped to an event
    move_pct REAL NOT NULL,
    stdev_move REAL NOT NULL,
    taxonomy_category TEXT,             -- one of AdHoc_Category_Taxonomy's 8, or NULL if the research step found no fit
    headline_cause TEXT,                -- human/LLM-researched "best-candidate cause", never auto-classified
    source TEXT,                        -- citation for headline_cause
    logged_at_utc TEXT NOT NULL,
    UNIQUE(series, shock_date)
);
```

`record_exogenous_shock()` / `get_exogenous_shock_for_date()` mirror `record_tier1_prediction()`/`get_latest_tier1_prediction_for_occurrence()`'s validation and occurrence-scoping patterns exactly — `taxonomy_category`, when set, is validated against `AdHoc_Category_Taxonomy`'s 8 real category names, same rejection-on-typo discipline `record_tier1_prediction()`'s confidence-tag validation already uses.

### 3. Detection + research trigger — extends the existing scheduled task

`tier1-cpi-ppi-autoresearch` (already renamed `tier1-multi-event-autoresearch` in Batch 7) gains one more daily step, reusing its existing cadence rather than adding a second scheduler: for each of the 5 `DETECTOR_SERIES`, call `detect_anomaly()` for yesterday's session (the most recent date with a complete, non-lookahead 24h move). If a real anomaly is found with no existing `exogenous_shocks` row for that `(series, date)`, do the same real-WebSearch "same-day headlines, best-candidate cause" research `Discovery_Detector_Spec` describes, classify against `AdHoc_Category_Taxonomy` where a real fit exists (leave `taxonomy_category` NULL rather than force a fit), and persist via `record_exogenous_shock()`.

### 4. Live display — `webapp/predictions_service.py`

Same non-destructive pattern as Batch 4's `tier1_sentiment_conflict`: after `tier1_prediction` is assembled for an event, check `get_exogenous_shock_for_date()` for today's date across `DETECTOR_SERIES`. If an unresolved shock exists, add a new field to the event dict:

```python
"tier1_confidence_downgrade": {
    "original_confidence": tier1_row.confidence,
    "displayed_confidence": _downgrade_one_tier(tier1_row.confidence),  # Certain->Likely->Guessing->Guessing
    "reason": shock.headline_cause,
    "series": shock.series,
} if shock is not None else None
```

The stored `tier1_predictions` row is never rewritten — `_downgrade_one_tier()` is a pure display-time function, same as `tier1DirectionLabel()`'s existing display-only relabeling in `app.js`. Frontend: a new badge next to `tier1PredictionHtml()`'s existing confidence tag, same warning palette as `.tier1-sentiment-conflict`.

Two rules made explicit here (self-review — both were ambiguous as first drafted):
- **Which instrument's Tier 1 row gets downgraded:** ANY unresolved anomaly across the 5 `DETECTOR_SERIES` downgrades EVERY tracked instrument's CPI/PPI `Tier1Prediction` rows for that day, not just the series' own instrument (DXY/10Y/30Y are USD-wide macro signals relevant to both XAUUSD and US30 regardless of which specific series moved) — `shock.series` is shown in the reason precisely so the viewer can judge relevance themselves, same "show context, let the viewer decide" principle the original live-tier1-dashboard-display spec already established.
- **Multiple same-day shocks don't compound:** if 2+ series are anomalous on the same day, the displayed confidence still drops exactly ONE tier, not one tier per shock — `get_exogenous_shock_for_date()`-driven lookup checks whether ANY unresolved shock exists that day, not how many.

## Error handling

- Every `None` case above (`compute_daily_move`, `rolling_baseline`, `detect_anomaly`) is the expected, common path — most days have no anomaly, and that's correct, not a failure.
- A failed Dukascopy fetch for any of the 5 series must never block the other 4 or crash the scheduled task — same per-series try/except `confirm_backtest_outcomes.py`'s auto-confirm phase already uses.
- The live-display lookup in `predictions_service.py` is wrapped fail-open, same as the existing `get_latest_tier1_predictions_bulk()` try/except: a broken shock lookup must never take down `/api/predictions`.

## Testing

- Synthetic unit tests for `rolling_baseline()`'s mean/stdev math and `detect_anomaly()`'s threshold logic (real numbers, fabricated price series — this is pure math, not a live claim).
- `detect_anomaly()`'s "calendar already explains this" gate tested against a real historical high-impact release day (should NOT flag) and a real historical date with no matching calendar event (should flag, if the real move happens to exceed threshold).
- The DXY/10Y/30Y Dukascopy-availability spike (see "Open technical risk" above) is its own task, output is a written finding, not code.
- No fabricated "pretend a shock happened" test data reaches the live path — same predict-then-check discipline as every other real signal in this project. The live `tier1_confidence_downgrade` field gets its first real test the next time a genuine anomaly is detected.
