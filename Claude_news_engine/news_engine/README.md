# News Fundamental Engine

Standalone Python system that reads news/economic-calendar data and scores
the probability of directional moves (currently gold/XAUUSD, with US30
also configured) ahead of major USD economic releases.

Built in a sandboxed environment with no live network access, so nothing
in this repo has been run against real data yet. That's the first job
for whichever environment (e.g. Claude Code) picks this up next.

## Current status

- Data layer, scoring engine, and backtest harness are built and pass
  synthetic/smoke tests (`tests/test_scoring_smoke.py`).
- A 10-event historical backtest was run using reconstructed (not live-
  pulled) pre-event articles, based on real researched outcomes — see
  `tests/run_historical_backtest.py`. It scored 8/9 directional calls
  correct, but this is a logic sanity-check, not a real accuracy number.
- Nothing has been tested against a live network. Every network call
  (Forex Factory calendar, RSS feeds, Alpha Vantage, APITube) is
  unverified — URLs and response parsing may need fixes once run for real.

## Setup

```bash
pip install -r requirements.txt
```

No API keys are required to start. The system currently runs RSS-only
(Reuters, CNBC, Investing.com — all free, no auth), which is the
deliberate choice for this validation phase: fewer moving parts, easier
to debug, and sufficient for testing whether the scoring logic itself
holds up before paying for broader source coverage.

Alpha Vantage and APITube clients exist in `data_layer/news_feed.py` and
can be added later (via `.env`, see `.env.example`) if RSS-only backtest
results suggest more source breadth would help — no code changes needed,
just add the sources to the list passed into scoring.

## First things to run, in order

1. **Smoke test the scoring logic** (no network needed):
   ```bash
   python tests/test_scoring_smoke.py
   ```
   Should print "All smoke tests passed." This confirms the core
   pipeline logic works in principle — start here to isolate whether any
   later failure is a network/parsing issue or a logic issue.

2. **Verify the Forex Factory calendar feed still works**:
   ```bash
   python data_layer/calendar_feed.py
   ```
   This hits `https://nfs.faireconomy.media/ff_calendar_thisweek.json`
   directly — unverified from this build, that URL or the response shape
   may have changed.

3. **Verify the RSS feed URLs still resolve** — check
   `data_layer/rss_sources.py`, `FREE_PREVIEW_FEEDS` and
   `OFFICIAL_OUTCOME_FEEDS`. Reuters and CNBC have changed RSS structure
   before; confirm each URL returns valid RSS XML before trusting it.

4. **Run the live end-to-end check**:
   ```bash
   python scripts/run_live_check.py
   ```
   Fetches this week's high-impact USD calendar, and for any event
   currently in its pre-event window, pulls RSS news and scores XAUUSD.
   If no event is currently in-window, it lists upcoming ones instead —
   that's normal, not a bug.

5. **Once step 4 works, run a real backtest** using
   `scoring/backtest.py`'s `run_backtest_case()` (the fetch-based path,
   not `run_backtest_case_manual()` which was only used for the
   reconstructed historical test). This needs real `EconomicEvent`
   objects for past dates — either build them by hand with known past
   NFP/CPI event times, or extend `calendar_feed.py` to fetch
   `"lastweek"` / historical periods if the feed supports it.

## Architecture

```
config/settings.py       — timezones (SAST), instruments, trust weights, tuning knobs
data_layer/
  calendar_feed.py        — Forex Factory calendar, SAST conversion
  news_feed.py             — Alpha Vantage + APITube clients (optional, unused by default)
  rss_sources.py           — free RSS sources, split into pre-event scoring
                              vs. backtest-only ground-truth outcome feeds
  event_context.py         — bundles an event with its pre-event news window,
                              enforces no-lookahead cutoff for backtesting
scoring/
  sentiment.py              — lexicon-based USD-directional sentiment fallback
  probability_engine.py     — time-decay + trust weighting, instrument mapping,
                               sigmoid probability, agreement-based confidence,
                               intra-run contradiction detection
  history.py                — tracks direction flips across successive scoring
                               runs through an event window
  backtest.py                — replays events through the pipeline, compares
                                predicted vs. actual direction
scripts/run_live_check.py   — end-to-end RSS-only live run, start here
tests/
  test_scoring_smoke.py       — synthetic unit tests, no network needed
  run_historical_backtest.py  — the 10-event reconstructed backtest (reference only)
```

## Known gaps / things to watch

- **Sentiment scoring now has 3 tiers**, cheapest/most-deterministic
  first: vendor-native sentiment (Alpha Vantage/APITube) if present, then
  local FinBERT (`scoring/finbert_sentiment.py`, needs
  `requirements-contextual.txt` AND `ENABLE_FINBERT_SENTIMENT=1`), then
  the Claude API for genuinely ambiguous cases FinBERT itself flags as
  low-confidence (`scoring/llm_sentiment.py`, needs `ANTHROPIC_API_KEY`
  AND `ENABLE_LLM_SENTIMENT=1`), and only then the original **naive
  keyword lexicon** (`scoring/sentiment.py`) as the final fallback. Both
  contextual tiers are **explicit opt-in via environment variable**, not
  just "installed = active" — having `torch`/`transformers` importable
  for an unrelated reason must never silently change scoring output.
  With both flags unset (the default), behavior is identical to before
  this tiering existed, deps installed or not. See the block comment
  above `CONTEXTUAL_CONFIDENCE_THRESHOLD` in `config/settings.py` for the
  full rationale.
- The June-NFP case in the reconstructed backtest was wrong because the
  lexicon scored hedged/conditional language ("could trigger a hawkish
  adjustment if...") as directional — this is specifically the failure
  mode the LLM tier was built to fix (see
  `tests/test_contextual_sentiment.py`). The lexicon tier still has this
  bug; it's now only reached when the contextual tiers aren't configured.
- `TIME_DECAY_HALF_LIFE_MINUTES`, `CONTRADICTION_MIN_MAGNITUDE`, and the
  sigmoid steepness constant `k` in `probability_engine._score_to_probability()`
  are all untuned placeholders — the historical backtest showed very
  extreme probabilities (3%/98%) from just 3-4 articles, which is
  probably over-confident and worth calibrating once real backtest data
  is available.
- US30's `usd_relationship: "risk_sentiment"` mapping is explicitly
  flagged in code as a simplification — worth revisiting if US30 backtest
  accuracy comes out weak relative to gold's.
