# Dukascopy Auto-Confirmation — Design Spec

**Date:** 2026-08-10
**Status:** Approved, pending implementation plan

## Purpose

`scripts/confirm_backtest_outcomes.py` requires manually researching and typing in
the real outcome for every prediction the article-based backtest accumulator makes
— the exact bottleneck the accumulator's own spec flagged as future work ("Free
price-data source research — separate, parallel effort, not blocking"). This adds
that price-data integration: fetch the real post-event price move from Dukascopy's
free historical data feed and auto-confirm the clear cases, leaving only genuinely
ambiguous ones (small move, or a failed/missing fetch) for manual review — the
existing `get_predictions_awaiting_outcome()` queue, unchanged.

Research (prior session) ruled out Alpha Vantage (rejects `XAU` as a currency
code) and evaluated Twelve Data (unclear free-tier commodity/index access) and
XAUS.com (rolling 24-48h window only, no historical timestamp queries) before
settling on Dukascopy: free, no API key, no documented rate limit, covers both
`XAUUSD` and `usa30idxusd` (Dow Jones/US30) with minute-level granularity back to
2013. See the prior turn's research summary for the comparison; not reproduced
here.

**Caveat carried forward, not resolved by this spec:** Dukascopy's public data
feed is reused via an undocumented/unofficial URL pattern, not a published API
with an SLA. Their Terms of Use / Important Disclaimer documents were not fully
read. This is a real risk to the *availability* of this feature (the feed could
change or start blocking automated access without notice) but not to its
*correctness* — every fetch failure degrades to "leave in the manual queue,"
never a wrong answer. Worth a manual ToS read before leaning on this heavily.

## Non-goals

- Not a redesign of `confirm_backtest_outcomes.py`'s existing interactive flow or
  `record_outcome()`/`record_dismissal()` — this adds an auto-confirm pass in
  front of it, reusing both as-is.
- Not full historical backfill tooling — this confirms outcomes for predictions
  already sitting in `get_predictions_awaiting_outcome()` (recent, from the live
  accumulator), not a bulk reconstruction of the 14 hand-built historical cases.
- Never auto-classifies `neutral`. A below-threshold move means "ambiguous, needs
  a human," not "confidently no reaction" — those are different claims, and
  conflating them would silently under-report real (small) directional moves as
  neutral in the accuracy report.
- No continuous background process. This is an on-demand script, matching
  `confirm_backtest_outcomes.py`'s existing pattern — not a new always-on loop
  alongside `backtest_accumulator.py` and `webapp/scheduler.py`.

## 1. Data fetch — `data_layer/dukascopy_feed.py`

**Revised after research spike (2026-08-10, during plan-writing):** hand-rolling
the `.bi5` LZMA/struct parser turned out to carry a real, hard-to-verify risk —
the raw tick price is a scaled integer, and the per-instrument decimal-scaling
divisor (1000? 100000? does it differ for an index CFD vs. spot gold?) could not
be confirmed with confidence from available documentation. A wrong divisor would
silently produce a garbage price, not a loud error — exactly the kind of mistake
this spec's whole point is to avoid making manually.

Instead, use the `dukascopy-python` PyPI package (MIT license, actively
maintained, `requires-python = ">=3.10"`, deps: `pandas` + `requests`) — it
already solves the fetch/decompress/parse/scale problem, including instrument
constants for both instruments this project needs:
`dukascopy_python.instruments.INSTRUMENT_FX_METALS_XAU_USD` (`"XAU/USD"`) and
`dukascopy_python.instruments.INSTRUMENT_IDX_AMERICA_E_D_J_IND`
(`"E_D&J-Ind"`, Dow Jones). This is a deliberate departure from "stdlib-only" —
flagged to the user, who did not object.

```python
def get_price_at(instrument: str, when_utc: dt.datetime) -> Optional[PricePoint]:
    """
    Fetches Dukascopy tick data for a short window starting at when_utc and
    returns the price of the first tick — i.e. the first real print AT OR
    AFTER when_utc, same no-lookahead discipline event_context.py already
    enforces on the prediction side, applied here on the confirmation side.
    Returns None on any fetch failure, or if the window contains no ticks
    at all (market closed, data gap) — never raises out to the caller,
    matching every other feed module in this codebase.
    """
```

- Instrument mapping is a 2-entry dict, `{"XAUUSD": INSTRUMENT_FX_METALS_XAU_USD, "US30": INSTRUMENT_IDX_AMERICA_E_D_J_IND}`
  — deliberately not reusing `config.settings.INSTRUMENTS` directly (that dict's
  keys are the right lookup, but its values are UI labels/relationships, not
  Dukascopy's instrument identifiers; a small local mapping keeps this module
  from reaching into an unrelated config concern for an unrelated purpose).
- Implementation: `dukascopy_python.fetch(instrument, dukascopy_python.INTERVAL_TICK, dukascopy_python.OFFER_SIDE_BID, start=when_utc, end=when_utc + dt.timedelta(minutes=5))`
  — a tight 5-minute window is enough to catch the next real tick without
  pulling a large range; BID consistently (documented choice, avoids spread
  noise from mixing sides across the two measurement points). Returns a pandas
  DataFrame; take the first row's `bidPrice` (renamed `PricePoint.price` at
  this module's boundary — callers never touch pandas directly, keeping the
  third-party dependency contained to this one file, same pattern
  `data_layer/news_feed.py` already uses to contain Alpha Vantage's response
  shape).
- An empty DataFrame (no ticks in the 5-minute window — market closed, weekend,
  data gap) or any raised exception (network failure, library error) → `None`.
- New dependency: `dukascopy-python` (pulls in `pandas`). Added to a new
  `requirements-dukascopy.txt`, following this project's existing opt-in-file
  convention (`requirements-webapp.txt`, `requirements-contextual.txt`) — the
  core RSS-only pipeline stays free of it.

## 2. Classification — `scoring/outcome_classifier.py`

```python
MEASUREMENT_WINDOW_MINUTES = 30
CLEAR_MOVE_THRESHOLD_PCT = 0.15

@dataclass
class ClassificationResult:
    direction: Optional[Direction]   # bullish/bearish, or None if ambiguous
    move_pct: Optional[float]        # None only if a fetch failed outright
    note: str                        # human-readable, becomes actual_move_note verbatim on auto-confirm

def classify(instrument: str, event_time_utc: dt.datetime) -> ClassificationResult:
    ...
```

- Fetches price at `event_time_utc` and `event_time_utc + MEASUREMENT_WINDOW_MINUTES`.
- Either fetch returning `None` → `ClassificationResult(direction=None, move_pct=None, note="Dukascopy: no data available (market closed or feed gap)")`.
- `abs(move_pct) < CLEAR_MOVE_THRESHOLD_PCT` → `ClassificationResult(direction=None, move_pct=move_pct, note=f"Dukascopy: {move_pct:+.2f}% in {MEASUREMENT_WINDOW_MINUTES}min, below {CLEAR_MOVE_THRESHOLD_PCT}% threshold")`.
- Otherwise → `Direction.BULLISH` (positive) or `Direction.BEARISH` (negative), note `f"Dukascopy: {move_pct:+.2f}% in {MEASUREMENT_WINDOW_MINUTES}min (auto)"`.
- Both constants live at module level, not buried in a function default — same
  reasoning as every other tunable constant in this codebase (`config/settings.py`'s
  `RISK_SENTIMENT_DAMPENING`, `NEAR_WINDOW_HOURS`, etc.): easy to find, easy to
  revisit once real auto-confirm data accumulates.

## 3. CLI integration — `scripts/confirm_backtest_outcomes.py`

```
python scripts/confirm_backtest_outcomes.py --auto           # auto phase only, report and exit
python scripts/confirm_backtest_outcomes.py --auto --list    # auto phase, then --list of what's left
python scripts/confirm_backtest_outcomes.py --auto <no other flag>  # auto phase, then falls into the existing interactive loop for what's left
```

- Auto phase: for each row from `get_predictions_awaiting_outcome()`, call
  `classify()`. Clear result → `record_outcome(conn, ..., actual_direction=result.direction.value, actual_move_note=result.note)`. Ambiguous/failed → left alone, tallied for the summary line.
- Always prints a summary: `"N auto-confirmed, M left for review"` — never a
  silent partial pass.
- When falling through to the existing interactive loop (no other flag passed),
  each remaining row's already-computed `ClassificationResult.note` is printed
  alongside the manual prompt as a suggestion (e.g. `"Dukascopy: +0.08% in
  30min, below threshold"`) so the fetch that already ran isn't wasted — the
  "flagged for review" experience promised in brainstorming, without any new
  persisted state, since the classification is recomputed fresh each run rather
  than stored.
- Bare `python scripts/confirm_backtest_outcomes.py` (no `--auto`) keeps today's
  behavior exactly — fully manual, zero Dukascopy calls. This is an additive
  flag, not a default-on behavior change.

## Error handling

- Every Dukascopy fetch/parse failure degrades to "ambiguous, stays in the
  manual queue" — never crashes the auto phase, never guesses. Same
  never-crash-the-loop discipline as `backtest_accumulator.py` and
  `webapp/scheduler.py`: one bad row logs a warning and the loop continues to
  the next.
- `record_outcome()`'s existing `Direction` validation (added the prior session)
  is a free safety net here too — a classifier bug producing something other
  than a real `Direction` member gets caught there rather than silently
  corrupting `build_real_backtest_report()`.
- No retries, no backoff logic — a failed fetch this run is a candidate for
  manual confirmation or a re-run later; this isn't a budget-capped resource
  like the article pipeline's RSS/Alpha Vantage fetches, so there's no equivalent
  budget-exhaustion case to handle.

## Testing

- `data_layer/dukascopy_feed.py`: mock `dukascopy_python.fetch()` (no live
  network) with synthetic pandas DataFrames — a normal non-empty result (assert
  the first row's price is returned), an empty DataFrame (assert `None`), and a
  raised exception (assert `None`, not a crash).
- `scoring/outcome_classifier.py`: mock `get_price_at()` with synthetic price
  pairs — exactly-0.15% move, just under, just over (both directions), one side
  returning `None` (fetch failure) → all assert the correct `ClassificationResult`.
- `scripts/confirm_backtest_outcomes.py --auto`: integration-style test seeding
  `backtest_store` directly with awaiting predictions, mocking `classify()`,
  asserting which rows got a `record_outcome()` call and which didn't, and that
  the summary counts match.
- No test requires a real Dukascopy network call — same discipline as every
  other test file in this codebase.

## Open items carried forward, not blocking this spec

- The Dukascopy ToS caveat above — read before leaning on this in production;
  does not block building/testing the integration itself.
- Whether `MEASUREMENT_WINDOW_MINUTES` (30) and `CLEAR_MOVE_THRESHOLD_PCT`
  (0.15%) are the right values is genuinely unknown until real auto-confirmed
  data accumulates — same "don't retune without real evidence" discipline
  already established for `TIME_DECAY_HALF_LIFE_MINUTES` etc. Revisit once
  there's a real sample, not before.
- Continuous background auto-confirmation (declined this round in favor of an
  on-demand script) — could be revisited later as a small follow-up if manual
  script-running proves to be the actual friction point in practice.
