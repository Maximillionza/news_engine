# Co-Released Event Reconciliation — Design

**Date:** 2026-09-04
**Status:** Approved via conversational brainstorm (architectural path)
**Builds on:**
- `webapp/static/app.js`'s `otherEventsHtml()` (2026-09-04, same-day) — the "N more events at this time" list, which established the grouping key this spec reuses (exact `event_time_utc` match) and stays completely untouched by this spec.
- `scoring/probability_engine.py`'s accumulator and `scoring/backtest_store.py`'s `predictions` table — the pipeline this spec adds a read-time reconciliation layer over. Nothing about how predictions are scored or stored changes.
- `webapp/history.py` — deliberately NOT touched. History keeps grading every co-released title independently, exactly as today.

## Problem

`data_layer/event_context.py`'s `build_event_news_bundle()` filters each event's article pool via `EVENT_RELEVANCE_KEYWORDS_BY_TITLE.get(event.title)` — a title-specific keyword filter. When multiple tracked titles release at the exact same `event_time_utc` (e.g. 2026-09-04T12:30:00Z's Non-Farm Employment Change, Unemployment Rate, and Average Hourly Earnings m/m, all from one BLS jobs report), each title pulls its own independently-filtered article sample and scores it with zero cross-title reconciliation. Confirmed live: for that exact release, US30 scored bullish under NFP, bullish under AHE, and bearish under Unemployment Rate — three contradictory reads of what is economically one USD move at one instant, not three.

Real-world economic principle driving this design (the user's own framing): a single news event has exactly one effect on the dollar at a given instant. Different **instruments** may legitimately react in opposite directions to that one effect (gold inverse, US30 risk-sentiment-dampened) — that's correct and unaffected by this spec. But the **same instrument** should never see contradictory directional calls purely because different co-released titles happened to sample different articles.

## Scope boundary

- **Article-based accumulator only.** The dashboard's live headline gauge (`webapp/scoring_service.py`'s essence-only path) is untouched — it's pure forecast-vs-actual numeric math with no articles involved, and today's exact contradiction case doesn't occur there (Unemployment Rate and AHE both printed exactly at consensus today, so essence-only scores both neutral — no real conflict to reconcile). A future spec can revisit essence-only reconciliation if a genuine mixed-signal essence-only case ever shows up; out of scope here.
- **Display-only.** Nothing about how `scoring/probability_engine.py` scores or how `scoring/backtest_store.py`'s `predictions` table gets written changes. Every title's own prediction stays exactly as independently computed and stored today.
- **History tab (`webapp/history.py`) is untouched entirely.** It reads `predictions`/`print_predictions` directly and keeps grading each co-released title's own Confirmed/Missed independently — this spec adds a new, separate read-time view, not a replacement for the existing one.
- **`/api/predictions/<symbol>/day/<date>`** (the calendar day-drill-down route) reads the same underlying data and would benefit from the same treatment, but is an explicit non-goal for this pass — flagged as a known follow-on.
- Grouping key is exact `event_time_utc` equality — no fuzzy time-window matching, consistent with `otherEventsHtml()`'s existing precedent.

## Architecture

### 1. New module — `webapp/reconciliation.py`

Read-only derived view over `scoring.backtest_store`'s already-written `predictions` table, mirroring the existing pattern of `webapp/history.py`/`webapp/trend.py` (no new writes, fails open on any read error — never crashes `/api/predictions` over a reconciliation bug).

```python
@dataclass
class ReconciledCall:
    conflict: bool
    prediction: Optional[Prediction]      # the dominant title's own, untouched prediction — only when conflict=False and a real call exists
    conflicting_titles: Optional[list[str]]  # titles that disagreed — only when conflict=True

def reconcile_group(
    instrument: str,
    predictions_by_title: dict[str, Prediction],  # every co-released title's latest prediction for this instrument, from get_latest_prediction_for_occurrence()
) -> Optional[ReconciledCall]:
    """
    Returns None if predictions_by_title has 0-1 non-neutral-direction
    entries — nothing to reconcile, caller falls through to today's plain
    single-title behavior. (The accumulator's own predictions use
    direction == 'neutral' as their "no real call" signal already — see
    webapp/history.py's existing `prediction.direction == "neutral" ->
    shrug` handling; there's no separate confidence floor to apply here,
    unlike the article-lexicon print-call pipeline's NO_HIT_CONFIDENCE.)
    """
```

Algorithm (per instrument, only when 2+ titles in the group have a non-neutral direction):

1. Titles scored `neutral` are excluded from the agreement/conflict check (a neutral call has no direction to agree or conflict with) but still contribute to the consolidated calculation below (as a zero-lean, full-weight term — see the formula).
2. **Dominant** = the highest-confidence title among the non-neutral calls.
3. **Consolidated** = `sum(confidence_i * signed_lean_i) / sum(confidence_i)` across every co-released title in the group (neutral titles included, contributing `signed_lean_i = 0`), where `signed_lean_i = (probability_i - 0.5) * 2` maps each title's own stored probability onto a [-1, 1] bearish-to-bullish axis, weighted by that title's own confidence. A positive result means the consolidated lean is bullish, negative bearish. Pure arithmetic over rows already in `predictions` — no rescoring, no article re-fetch.
4. If every title in the group is neutral → group call is neutral, `conflict=False`, no dominant to report (falls through to today's neutral rendering).
5. If dominant's direction matches the consolidated result's sign → `conflict=False`, `prediction` = the dominant title's own real object (probability/confidence/article_count untouched — never a synthetic blend).
6. If they disagree → `conflict=True`, `conflicting_titles` = every title in the group with a non-neutral call.

### 2. `/api/predictions` integration (`webapp/app.py`)

For the featured event's instrument, when the featured event has co-released siblings (same `event_time_utc`, from the same grouping already computed for `otherEventsHtml()`'s underlying data) with real accumulator calls:

- Fetch each co-released title's latest prediction for this instrument (`get_latest_prediction_for_occurrence()`, already used).
- Call `reconcile_group()`.
- **No conflict, dominant found:** `article_prediction` in the JSON response = the dominant title's own object, exactly the shape already returned today — no schema change on this path.
- **Conflict:** `article_prediction` = `null`, plus a new sibling field `article_prediction_conflict: {"titles": [...]}` — purely additive, existing clients ignore it.
- **0-1 real calls in the group (or no group at all):** unchanged — today's plain single-title `article_prediction` value.

The "N more events" list's own data (each title's own individual accumulator call) is unaffected — it's built from the same per-title `get_latest_prediction_for_occurrence()` calls it already makes, independent of this reconciliation layer.

### 3. Frontend (`webapp/static/app.js`)

`articlePredictionHtml()`: unchanged when `article_prediction` is present (dominant call, same shape as today). When `article_prediction` is `null` AND `article_prediction_conflict` is present, render a distinct "⚠ Conflicting signals" badge instead of the current blank/no-signal state — new CSS class `.article-prediction-conflict`, styled distinctly from both a real call and the plain absent-signal case so it can never be mistaken for "no data" or a real bullish/bearish read.

## Error handling

- `reconcile_group()` never raises on bad/missing data — a title with a malformed prediction row is simply excluded from the group (same "one bad lookup must not crash the whole build" discipline `webapp/history.py` already uses).
- If the reconciliation computation itself throws for any reason, `/api/predictions` catches it, logs a warning, and falls back to today's plain single-title `article_prediction` value for that card — a reconciliation bug degrades to today's existing behavior, never to a card-rendering crash.

## Testing

- `tests/test_webapp_reconciliation.py` (new): `reconcile_group()` unit tests — all-agree (no conflict, dominant matches consolidated), genuine conflict (dominant disagrees consolidated), all-neutral group, single real call (returns None, caller falls through), mixed neutral+real calls, confidence-weighting correctness on the consolidated calculation.
- `tests/test_webapp_app.py`: extend `/api/predictions` tests for the new `article_prediction_conflict` field — present only on genuine conflict, absent otherwise (backward-compatible shape).
- Explicit regression test reproducing 2026-09-04's real case: NFP/AHE/Unemployment Rate co-released, US30 bullish/bullish/bearish → confirms `conflict=True` (2/3 bullish, 1/3 bearish, but need the actual dominant-vs-consolidated math to land on conflict given real confidences — a scenario worth verifying by construction, not assumption, once the plan implements the exact weighting).
- No change needed to `tests/test_webapp_history.py` — explicit assertion added there that History's per-title behavior is unaffected by this spec (belt-and-suspenders, since the module is untouched).
