# Article-Based Backtest Accumulator — Design Spec

**Date:** 2026-08-10
**Status:** Approved, pending implementation plan

## Purpose

The article-based scoring pipeline (`scoring/probability_engine.py` — RSS + Alpha Vantage + lexicon/FinBERT/LLM) has almost no real backtest coverage: one live-fetched case (Aug 7 NFP, done manually this session) plus 14 hand-reconstructed historical events. Reconstructed cases validate the *scoring mechanics*, not real-world accuracy, by construction (the articles are written to trigger the pipeline cleanly).

This builds infrastructure to accumulate **genuine** real-world backtest data automatically, going forward: whenever a tracked instrument has a high-impact USD event approaching, run the real fetch-based pipeline and persist the prediction *before* the outcome is known (no lookahead, same discipline `event_context.py` already enforces), then confirm the real outcome after the fact.

## Non-goals

- Not a price-data integration. Ground truth (`actual_direction`) is confirmed manually/via research, not fetched automatically — the earlier attempt to wire in a free gold price API hit a real wall (Alpha Vantage's free FX endpoints reject `XAU`; today's Alpha Vantage budget is separately exhausted from combined testing). A parallel, separate effort may research a working free price source later; this accumulator does not depend on it and should not block on it.
- Not wired into `webapp/` — the dashboard is essence-only by deliberate design (established earlier this session); this accumulator uses real articles and is a distinct, separate concern, run as its own standalone process/script.
- Not a redesign of `scoring/probability_engine.py` or `scoring/backtest.py`'s existing `run_backtest_case()` — this reuses both as-is, just adds a scheduling + persistence layer around them.

## 1. Persistence — `scoring/backtest_store.py`, own SQLite file (`scoring/backtest_log.db`, gitignored — extend the existing `*.db` pattern)

```sql
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    scored_at_utc TEXT NOT NULL,
    probability REAL NOT NULL,
    direction TEXT NOT NULL,
    confidence REAL NOT NULL,
    article_count INTEGER NOT NULL,
    contradiction_flag INTEGER NOT NULL  -- 0/1, SQLite has no native bool
);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_title TEXT NOT NULL,
    instrument TEXT NOT NULL,
    event_time_utc TEXT NOT NULL,
    actual_direction TEXT NOT NULL,
    actual_move_note TEXT NOT NULL,
    confirmed_at_utc TEXT NOT NULL,
    UNIQUE(event_title, instrument, event_time_utc)  -- one confirmed outcome per (event, instrument) pair
);
```

Functions: `get_connection(db_path=None)` (same late-binding pattern as `webapp/store.py` — resolved inside the function body, not a default-argument value, so tests can patch the module-level `DB_PATH`), `record_prediction(...)`, `get_predictions_awaiting_outcome(conn) -> list[Prediction]` (event_time_utc in the past, no matching row in `outcomes`), `record_outcome(...)`, `get_all_confirmed_cases(conn) -> list[(Prediction, Outcome)]` (joined, for reporting).

## 2. Accumulator scheduler — `scoring/backtest_accumulator.py`

```python
def run_accumulator_cycle(instruments: list[str], db_path=None) -> None:
    """
    One cycle: fetch the calendar (cheap, cached-friendly), find
    high-impact USD events in their pre-event window, and — respecting
    the per-event snapshot budget — run the real article-based pipeline
    and persist a prediction.
    """
```

- Uses `data_layer.calendar_feed.fetch_calendar("thisweek")` + `filter_relevant_events(events)` (High-impact only — default, NOT the Medium-impact widening used for the essence-only dashboard; article fetches are expensive/budget-limited, no reason to chase Medium-impact events here).
- **Snapshot budget: at most 2 article-fetch scoring passes per (event, instrument) pair** — approved. First snapshot when the event enters its pre-event window; second snapshot once inside a "final stretch" window (reuse `webapp/scheduler.py`'s `NEAR_WINDOW_HOURS` constant for consistency — same "how close is close" definition already established). Track snapshot count via `predictions` row count per (event_title, instrument) pair — if 2 rows already exist for a still-pending event, skip.
- For each event/instrument pair due a snapshot: `build_all_preview_sources()` → `build_event_news_bundle(event, sources, query="", mode="live")` → `score_bundle(bundle, instrument)` → `record_prediction(...)`.
- Poll interval for the *calendar check itself* (not the article fetch): reuse `webapp.scheduler.compute_adaptive_interval_seconds` — same tiering, same rationale, avoids a second copy of the same logic.
- Runs as its own script's background loop (`if __name__ == "__main__": start loop`), NOT threaded into `webapp/app.py`.

## 3. Manual outcome confirmation — `scripts/confirm_backtest_outcomes.py`

```
python scripts/confirm_backtest_outcomes.py
```

- Lists every row from `get_predictions_awaiting_outcome()` (event has passed, no outcome recorded).
- For each, prompts for `actual_direction` (bullish/bearish/neutral) and `actual_move_note` (free text) via stdin — same manual-research rigor as tonight's reconstructed backtest cases, just applied to real predictions made blind (before the event) rather than reconstructed after the fact.
- Also usable non-interactively: `record_outcome()` importable directly for scripted/researched batch confirmation (matches how this session's reconstructed cases were built — real web research, then a direct call recording the result).

## 4. Reporting

New function in `scoring/backtest.py` (or a small new `scoring/backtest_report.py` if `backtest.py` starts feeling overloaded — implementer's call, follow existing file-size judgment) that reads `get_all_confirmed_cases()`, builds `BacktestCase` objects from the stored (prediction, outcome) pairs, and feeds them into the existing `BacktestReport` — reusing the exact same accuracy/call-rate/contradiction-rate computation and `print_report()` output format already used for the reconstructed set, so real and reconstructed results are visually comparable using the same report shape.

**This is the running log the whole accumulator exists to build** — a persistent, growing record of every real tracked event/instrument prediction next to its confirmed real outcome, queryable at any time to check performance. It's also what finally makes the earlier-declined constant-tuning conversation (`TIME_DECAY_HALF_LIFE_MINUTES`, `CONTRADICTION_MIN_MAGNITUDE`, sigmoid `k`) answerable with real evidence instead of guesses — once this table has enough real confirmed cases, those constants can be revisited against genuine calibration data rather than the circular reconstructed set. Not in scope for this build (needs real data to accumulate first), but the reason this table's schema keeps `probability`/`confidence`/`article_count` alongside the direction call, not just win/loss — those fields are exactly what a future calibration pass would need.

## Error handling

- Calendar fetch failure: log and skip the cycle, same pattern as `webapp/scheduler.py`.
- Article fetch failure for one event/instrument pair: log and skip that pair, don't crash the cycle (other pairs still get their chance).
- Alpha Vantage budget exhaustion mid-cycle (e.g. a 429/rate-limit response): log clearly, skip remaining article-fetch snapshots for that cycle — RSS-only sources still get scored (graceful degradation, matching `build_all_preview_sources()`'s existing per-source failure tolerance in `fetch_from_all_sources()`).
- Never fabricate an outcome — a prediction with no confirmed outcome simply doesn't appear in reporting until `confirm_backtest_outcomes.py` fills it in.

## Testing

- `scoring/backtest_store.py`: round-trip tests (record prediction, record outcome, join query), snapshot-budget-limit test (2 predictions for the same pair, third is correctly identified as "budget exhausted" by the accumulator — store itself doesn't enforce the cap, the accumulator does, so this is really an accumulator-level test).
- `scoring/backtest_accumulator.py`: mocked calendar + mocked `score_bundle` (no live network in tests), confirms the 2-snapshot cap is respected, confirms High-impact-only filtering (no Medium-impact events trigger a snapshot), confirms a failed article fetch for one pair doesn't stop others.
- No test requires a real Alpha Vantage call or real network — same discipline as every other test file this session.

## Open items carried forward, not blocking this spec

- Free price-data source research — separate, parallel effort, not blocking.
- Whether `article_count == 0` (all sources failed) should still record a prediction (NEUTRAL, 0% confidence — this is what `score_bundle()` already returns for an empty bundle) or skip recording entirely. Recommend: still record it — a "no articles found" case is itself real, useful information about source coverage over time, and `score_bundle()`'s existing empty-bundle handling already produces an honest NEUTRAL/0%-confidence result rather than fabricating anything.
