# SWOT Recommendations (P0+P1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Execution note (this run):** implemented inline by the planning session itself rather than dispatched to fresh subagents — Tasks 4-5 depend on live Kalshi API verification already performed in-session (see Task 4), which a fresh subagent would have to redo from scratch at real cost. Recorded here anyway per the skill's requirement that a plan exist before code changes.

**Goal:** Implement the P0 (critical-flaw) and P1 (highest-impact) recommendations from `docs/fundamental-analysis-swot-2026-08-14.md`, scoped per the user's non-response to the scope-clarifying question (defaults taken: P0+P1 only, R5 deferred to a write-up, R7 out of scope).

**Architecture:** Five independent, additive changes to existing modules — no new subsystems. Each is a bounded diff to a file already read and understood this session.

**Tech Stack:** Python (existing stack — Flask, sqlite3, requests, torch/transformers already installed in this environment).

**Spec:** `docs/fundamental-analysis-swot-2026-08-14.md` (R1, R2, R3, R4, R6 sections)

## Global Constraints

- Never call `data_layer/calendar_feed.py`'s underlying Forex Factory feed directly or bypass `fetch_calendar()`'s cooldown — this session already made one accidental ungated FF request during research; no further live FF calls this session.
- Kalshi's public API has no documented rate limit in this codebase and was queried directly several times this session for live verification — that's an accepted, established pattern (see `data_layer/kalshi_feed.py`'s docstring), not a new risk.
- Every existing test in `tests/test_*.py` must still pass after each task (`python tests/test_X.py` convention — plain functions with asserts run via each file's own `__main__` block, not pytest).
- No new external paid dependency or API key requirement introduced without asking first (this ruled out doing live R5 work this pass).
- Preserve the codebase's established conventions: fail-open on external calls, "never fabricate — return None on missing data," dated/reasoned inline comments on every constant, `source`/provenance style transparency fields on any read-time-computed value.

---

### Task 1 (R1): Read-time merge for the stale "pending" essence-only direction

**Files:**
- Modify: `webapp/app.py` (`get_predictions()`, `webapp/app.py:165-322`)
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `webapp.scoring_service.score_event_for_symbol(event: EconomicEvent, symbol_class) -> EssenceScore` (existing, unchanged), `webapp.store.get_event_history(conn, event_title) -> list[EventHistoryRow]` (existing), `data_layer.calendar_feed.EconomicEvent` (existing dataclass).
- Produces: `_recompute_stale_pending(event: dict, symbol_class, history_rows: list[EventHistoryRow]) -> Optional[EssenceScore]` — new private helper in `webapp/app.py`, used only within `get_predictions()`.

- [x] Add `_recompute_stale_pending()` helper and wire it into `get_predictions()`'s per-event loop, replacing the `prior_occurrences` fetch's current position (move it earlier so it can also drive the stale-pending check) and reusing it for the trend computation that already exists later in the same loop (removes a duplicate query).
- [x] Add `"recomputed_from_event_history": bool` to each event entry in the API response for transparency (provenance, matching the codebase's `source` column convention elsewhere).
- [x] Update the `latest is None and article_prediction is None and ...` inclusion guard to also treat a successful recompute as non-empty.
- [x] Write `test_predictions_recomputes_stale_pending_direction_from_event_history()` in `tests/test_webapp_app.py`: seed a calendar snapshot event with `actual=None` (still shows pending on the calendar), record a `prediction_runs` row with `direction="pending"` via `store.record_run` (simulating what the scheduler wrote before the actual existed), then seed `event_history` with a resolved actual via `store.upsert_event_history`, call `/api/predictions`, and assert the returned `direction` is a real value (not `"pending"`), `probability` is not `None`, and `recomputed_from_event_history` is `True`.
- [x] Write `test_predictions_stale_pending_without_resolved_history_stays_pending()`: same setup but `event_history` has no matching resolved row — assert `direction == "pending"` and `recomputed_from_event_history` is `False`.
- [x] Run `python tests/test_webapp_app.py` — all tests pass (including two new ones).
- [x] Commit: `fix: recompute stale pending essence-only direction from event_history at read time`

---

### Task 2 (R3): Sample-size-aware probability ceiling on the article-based engine

**Files:**
- Modify: `scoring/probability_engine.py` (`score_bundle()`, `ProbabilityResult`)
- Modify: `config/settings.py` (two new constants)
- Test: `tests/test_probability_engine.py`

**Interfaces:**
- Produces: `ProbabilityResult.thin_sample: bool` (new field), `_signal_bearing_count(contributions) -> int` (new private helper), `config.settings.THIN_SAMPLE_SIGNAL_THRESHOLD` / `THIN_SAMPLE_PROBABILITY_CAP` (new constants).

- [x] Add `THIN_SAMPLE_SIGNAL_THRESHOLD = 3` and `THIN_SAMPLE_PROBABILITY_CAP = 0.80` to `config/settings.py` with a comment citing `BACKTEST_REPORT.md`'s own overconfidence finding.
- [x] Add `_signal_bearing_count()` and `_apply_thin_sample_cap()` to `scoring/probability_engine.py`, apply after `adjusted_probability` is computed, add `thin_sample` field to `ProbabilityResult`.
- [x] Write `test_thin_sample_caps_extreme_probability()`: 2 strongly-agreeing articles (reproducing a BACKTEST_REPORT-style 98%+ case) — assert final `probability` is capped at `THIN_SAMPLE_PROBABILITY_CAP` and `thin_sample is True`.
- [x] Write `test_sufficient_signal_count_is_not_capped()`: 3+ signal-bearing contributions (mix of articles and a Kalshi/precursor contribution) strongly agreeing — assert probability can exceed the cap and `thin_sample is False`.
- [x] Run `python tests/test_probability_engine.py` — all tests pass.
- [x] Commit: `feat: cap probability on thin signal samples independent of confidence`

---

### Task 3 (R2): Default-on contextual sentiment tier (FinBERT), LLM tier stays opt-in

**Files:**
- Modify: `config/settings.py:36-37`
- Modify: `tests/test_contextual_sentiment.py` (un-skip the FinBERT-only portion; it currently skips entirely on missing `ANTHROPIC_API_KEY` even though FinBERT doesn't need one)

**Interfaces:**
- No signature changes — `ENABLE_FINBERT_SENTIMENT`/`ENABLE_LLM_SENTIMENT` remain module-level bools read by `scoring/probability_engine.py`'s `_get_article_sentiment()` (unchanged).

- [x] Flip `ENABLE_FINBERT_SENTIMENT` default to on (`os.environ.get("ENABLE_FINBERT_SENTIMENT", "1") != "0"`), keep `ENABLE_LLM_SENTIMENT` default off (paid API, no key configured) — comment explains the asymmetry.
- [x] Add `test_finbert_handles_hedged_conditional_language()` reproducing BACKTEST_REPORT.md case #2's exact failure text ("Rate hike risk if jobs data surprises to upside") — assert FinBERT's `usd_score` is not a maximal +1.0 declarative read (the lexicon's actual documented failure), independent of `ANTHROPIC_API_KEY`.
- [x] Run `python tests/test_contextual_sentiment.py` — passes using the already-installed local FinBERT weights (no network/API key needed).
- [x] Run full suite once more (`for f in tests/test_*.py; do python "$f"; done`) to confirm the default flip doesn't silently change any lexicon-assuming test's expected output — fix any that assumed lexicon-only scoring without mocking `ENABLE_FINBERT_SENTIMENT`.
- [x] Commit: `feat: make FinBERT contextual sentiment the default tier, LLM tier stays opt-in`

---

### Task 4 (R4): Fix KXFED misclassification, restore FOMC Kalshi coverage, add real date-ticketed resolution for the other 6 events

**Live verification performed this session (Kalshi API only, not FF):**
- `KXFED` events are **month-ticketed** (`KXFED-26SEP`, `KXFED-26JUL`, ...) — `config/settings.py`'s existing claim that it's date-ticketed (`"-26mar19"`) is **wrong**, live-disproved.
- `KXUSRETAIL`, `KXJOBLESSCLAIMS`, `KXGDP`, `KXCHCUTS`, `KXUSPPI`, `KXUSMICHCSP` are genuinely **date-ticketed** (`KXUSRETAIL-26AUG14`, `KXJOBLESSCLAIMS-26AUG20`, ...) — confirmed correctly classified.

**Files:**
- Modify: `data_layer/kalshi_feed.py` (extract shared market-selection logic, add `_resolve_event_ticker_by_date()` + `get_market_read_by_date()`)
- Modify: `config/settings.py` (re-enable `KALSHI_RATE_DECISION_SERIES`, add `KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE`)
- Modify: `scoring/backtest_accumulator.py` (`_read_kalshi_signal()`)
- Test: `tests/test_kalshi_feed.py`, `tests/test_backtest_accumulator.py`

**Interfaces:**
- Produces: `data_layer.kalshi_feed.get_market_read_by_date(series_ticker: str, event_date: dt.date, target_strike: float) -> Optional[KalshiRead]` — same return type as existing `get_market_read()`.
- Produces: `config.settings.KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE: dict[str, str]`.

- [x] In `data_layer/kalshi_feed.py`: extract `get_market_read()`'s post-ticker-resolution body (market fetch, unit-mismatch guard, nearest-strike selection, liquidity gate, direction discretization) into `_read_market_for_event_ticker(event_ticker: str, target_strike: float) -> Optional[KalshiRead]`. Have `get_market_read()` call `_resolve_event_ticker()` then delegate to it.
- [x] Add `_resolve_event_ticker_by_date(series_ticker: str, event_date: dt.date) -> Optional[str]` — same `/events` fetch, suffix match on `-{yy}{MON}{DD}` (case-insensitive), exact date first, then ±1 day tolerance (log which matched) — fail closed (`None`) otherwise.
- [x] Add `get_market_read_by_date(series_ticker, event_date, target_strike)` — resolves via the new by-date function, delegates to `_read_market_for_event_ticker()`, same fail-open `try/except` wrapper as `get_market_read()`.
- [x] In `config/settings.py`: correct the `KALSHI_RATE_DECISION_SERIES` comment (was: "ticketed to a specific FOMC MEETING DATE" — now: month-ticketed, live-verified 2026-08-14, restore `{"Federal Funds Rate": "KXFED"}`). Add `KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE` with the 6 real date-ticketed series, remove them from `KALSHI_SERIES_BY_EVENT_TITLE`'s comment block (they're no longer "not implemented").
- [x] In `scoring/backtest_accumulator.py`'s `_read_kalshi_signal()`: add a second branch checking `KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE` (calls `get_market_read_by_date` with `event.event_time_utc.date()`) between the existing month-ticketed branch and the FOMC branch; in the FOMC branch, fall back to `event.previous` when `event.forecast` doesn't parse (rate-hold expectations sometimes carry the rate only in `previous`).
- [x] Write `test_resolve_event_ticker_by_date_matches_exact_date()`, `test_resolve_event_ticker_by_date_falls_back_to_one_day_tolerance()`, `test_resolve_event_ticker_by_date_fails_closed_with_no_match()` in `tests/test_kalshi_feed.py` (mock `requests.get`, same pattern the file already uses for `_resolve_event_ticker`).
- [x] Write `test_read_kalshi_signal_resolves_fomc_via_month_ticker()` and `test_read_kalshi_signal_resolves_date_ticketed_event()` in `tests/test_backtest_accumulator.py`.
- [x] Run `python tests/test_kalshi_feed.py` and `python tests/test_backtest_accumulator.py` — all pass.
- [x] Commit: `fix: correct KXFED month-vs-date misclassification, restore FOMC Kalshi coverage, add date-ticketed series resolution for 6 more events`

---

### Task 5 (R6): Single-source calendar-feed risk — explicit staleness policy + monitoring

**Files:**
- Modify: `data_layer/calendar_feed.py` (expose last-successful-fetch age)
- Modify: `webapp/app.py` (surface staleness on `/api/calendar`)
- Create: `docs/calendar-feed-staleness-policy.md`
- Test: `tests/test_calendar_feed.py`, `tests/test_webapp_app.py`

**Interfaces:**
- Produces: `data_layer.calendar_feed.get_last_successful_fetch_age_seconds() -> Optional[float]` (reads the existing `_LAST_FETCH_TIMESTAMP_FILE`, returns `None` if it doesn't exist yet).

- [x] Add `get_last_successful_fetch_age_seconds()` to `data_layer/calendar_feed.py`, reading the existing cooldown timestamp file (already written on every successful fetch).
- [x] In `webapp/app.py`'s `/api/calendar` route, add a `"feed_staleness_seconds"` field to the response using the new function (`None` if never fetched).
- [x] Write `docs/calendar-feed-staleness-policy.md`: documents W5/T1 from the SWOT explicitly — single-source dependency on `nfs.faireconomy.media`, FF's own "fetch once a week" guidance, the project's 600s cooldown as a conservative floor (not a target cadence), what "too stale to trust" means operationally (recommend: treat data older than 24h as display-only/flagged, not scoring-fresh — this is a policy recommendation, not a new code gate, since the existing scoring paths already fail open on a failed fetch and keep prior data), and the explicit decision already made with the user this session to not chase further free alternatives (Trading Economics/FMP/NewsAPI all live-verified paid/unsuitable).
- [x] Write `test_get_last_successful_fetch_age_seconds_reads_the_cooldown_file()` and `test_get_last_successful_fetch_age_seconds_none_when_never_fetched()` in `tests/test_calendar_feed.py`.
- [x] Write `test_calendar_route_includes_feed_staleness_seconds()` in `tests/test_webapp_app.py`.
- [x] Run `python tests/test_calendar_feed.py` and `python tests/test_webapp_app.py` — all pass.
- [x] Commit: `feat: surface calendar-feed staleness, document single-source risk policy`

---

## Explicitly deferred (documented, not implemented this pass)

- **R5** (macro-backdrop DXY/real-yield cross-check) — no live data source in this codebase; needs a scoped follow-up spec before any code, per user's non-response defaulting to "document only."
- **R7** (EV/Kelly position sizing) — out of scope per default answer: sizing belongs in the MQL5 ACE EA, not this Python signal engine.
- **R8** (recalibrate trust weights/constants against real outcome data) and **R10** (echo-chamber self-check on trend-streak) — both require an accumulated real (non-seeded) outcome dataset that doesn't exist yet; revisit once `confirm_backtest_outcomes.py` has enough real rows.
- **R9** (competing-story/shock flag) — P2, smallest remaining item, left for a follow-up pass; not blocking any P0/P1 item.
