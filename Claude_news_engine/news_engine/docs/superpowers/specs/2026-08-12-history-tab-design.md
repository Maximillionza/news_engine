# History Tab — Print-Call Track Record — Design

## Problem

The dashboard shows the engine's live state (current predictions, the
per-event History panel of raw forecast/previous/actual) but nowhere shows
a consolidated, reviewable record of past print-direction calls against
what actually happened. There's no way to answer "how has the engine's
print-direction call actually done, across every event it's called?" in
one place — you'd have to piece it together event-by-event via the
existing per-event History panel.

## Scope boundary

Additive-only, read-only, display-only:

- No new tables, no schema change to `event_history` or `print_predictions`.
- No scoring change — the "unchanged vs previous" pattern (research-confirmed
  as real for inflation-type indicators specifically, not universal) is
  shown as an informational badge only, never fed into
  `score_bundle()` or the Confirmed/Missed judgment.
- No change to the existing per-event History panel (`webapp/trend.py`,
  `GET /api/event_history`) — this is a new, separate, wider view.

## Architecture

New module `webapp/history.py`, mirroring the read-only cross-pipeline
pattern already established twice in this codebase (`webapp/app.py`
reading `scoring/backtest_store.py`'s DB for the print-call badge;
`scoring/backtest_accumulator.py` reading `webapp/store.py`'s DB for the
trend signal):

```python
@dataclass
class HistoryRow:
    event_title: str
    event_time_utc: str
    previous: Optional[str]
    forecast: Optional[str]
    actual: Optional[str]
    unchanged_vs_previous: bool   # actual == previous, string-equal — informational only
    ne_prediction: str            # 'higher' | 'lower' | 'in_line'
    ne_confidence: float
    outcome: Optional[str]        # 'Confirmed' | 'Missed' | None (shrug call, excluded)


def build_print_call_history(limit: int = 50) -> list[HistoryRow]:
    ...
```

### Join logic

1. Read `webapp/store.py`'s `event_history` rows (this dashboard's own DB,
   normal connection) for occurrences with a non-`None` `actual` —
   unresolved events aren't "history" yet, they'll appear once they
   resolve.
2. Open a **read-only** connection to `scoring/backtest_store.py`'s DB
   (same precedent as the existing print-call badge) and, for each
   resolved `event_history` row, look up the **latest**
   `print_predictions` row for that exact `(event_title, event_time_utc)`
   occurrence — reusing the same "latest per occurrence" logic
   `get_latest_print_prediction()` already implements (a print call can
   have multiple historical rows via diff-aware writes on direction
   flips; only the final one matters here).
3. No matching `print_predictions` row → the occurrence is skipped
   entirely (not shown with a blank NE Prediction column) — matches the
   "only events with an NE prediction" scope decision.
4. **Shrug exclusion**: if the matched call's `confidence <=
   NO_HIT_CONFIDENCE` (0.15 — the exact constant `scoring/print_direction.py`
   already uses for its zero-phrase-hit default), `outcome = None` and
   the row displays "No strong call" instead of being judged. This keeps
   the Confirmed/Missed record from being padded by default-neutral
   guesses that happened to land right by chance (e.g. today's CPI m/m:
   `in_line` at 0.15 confidence, technically correct, but not a real
   signal).
5. **Confirmed/Missed** (for non-shrug calls): exact string equality
   between `print_predictions.predicted_vs_forecast` and
   `event_history.surprise_direction` — both already share the same
   `'higher'`/`'lower'`/`'in_line'` vocabulary (from `classify_surprise()`
   and `score_print_direction()` respectively), so no new comparison
   logic is needed beyond `==`.
6. `unchanged_vs_previous = (actual == previous)` — plain string equality
   on the raw stored values. Purely a display badge; has zero effect on
   `outcome`.
7. Cross-pipeline read failure (accumulator DB missing/locked) fails open
   to an empty result for that lookup — same pattern as
   `_read_trend_signal()` — never crashes the route. A total failure to
   open the accumulator DB at all means `build_print_call_history()`
   returns `[]`, not a 500.
8. Sorted most-recent-first (`event_time_utc DESC`), capped at `limit`
   (default 50 — generous flat cap, no pagination in this pass).

### API

`GET /api/history` (new route, `webapp/app.py`) — thin: calls
`build_print_call_history()`, returns
`{"rows": [...]}` where each row serializes `HistoryRow`'s fields
directly (dataclass → dict, same style `/api/event_history` already uses).

## UI

Third tab, "History", alongside the existing Dashboard/Calendar tabs
(`webapp/static/index.html`'s tab bar gains one more button + view div,
`webapp/static/app.js` gains a `showView`-compatible render function
following the existing `showView(name)` pattern).

Single table, most-recent-first:

```
Event          Previous   Forecast   Actual   NE Prediction              Outcome
CPI m/m        -0.4%      0.1%       0.1%     In-line (15% conf.)        No strong call
Core CPI m/m   0.0%       0.2%       0.2% =   Lower (51% conf.)          Missed
```

The `=` badge next to Actual marks `unchanged_vs_previous`. Missing
`forecast`/`previous` render as `—`. Fetched once when the History tab is
first selected (not on every dashboard poll cycle — matches the existing
"History ▾" panel's fetch-on-first-expand pattern, just scoped to
tab-selection instead of a per-card toggle). Empty result (fresh install,
or nothing resolved yet) shows an explicit "No confirmed calls yet"
message, not a blank table.

## Testing

- `build_print_call_history()`: resolved-with-real-call row appears with
  correct Confirmed/Missed; resolved-with-shrug-call row appears with
  `outcome=None`/"No strong call"; unresolved `event_history` row (actual
  still null) is excluded entirely; `event_history` row with no matching
  `print_predictions` row at all is excluded entirely; multiple
  historical `print_predictions` rows for one occurrence only surface the
  latest.
- Shrug-boundary test: confidence exactly `0.15` → excluded from judging;
  confidence just above `0.15` → judged normally.
- `unchanged_vs_previous` independence test: two otherwise-identical rows
  differing only in whether `actual == previous` must produce the same
  `outcome` — proving the badge has zero effect on judging.
- Cross-pipeline failure test: accumulator DB unreachable →
  `build_print_call_history()` returns `[]`, doesn't raise.
- `GET /api/history` route test: empty case (200, `{"rows": []}`, not
  500), populated case (seeded data in both DBs, correct JSON shape).
- Frontend: no automated test harness exists for this codebase's JS
  (established pattern) — verified live via browser after implementation,
  same as every other UI change this session.

## Explicitly out of scope (this pass)

- CSV export, filtering/search UI, pagination beyond the flat 50-row cap.
- Editing or annotating history rows.
- Feeding `unchanged_vs_previous` into scoring or into the Confirmed/Missed
  judgment — display-only, per the research finding that this pattern is
  real but indicator-specific (inflation-type prints), not a universal
  rule safe to hardcode across every event type this system tracks.
- Kalshi or any other specialist-forecasting-source integration
  (discussed separately in conversation) — a distinct, future spec.
