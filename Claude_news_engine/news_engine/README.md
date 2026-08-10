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

No API keys are required to start — the system runs RSS-only (Reuters,
CNBC, Investing.com — all free, no auth) by default.

**Alpha Vantage is wired in and opt-in by key presence.** Copy
`.env.example` to `.env`, fill in `ALPHA_VANTAGE_API_KEY` (free signup
at alphavantage.co), and `data_layer.rss_sources.build_all_preview_sources()`
picks it up automatically alongside the RSS feeds — no other code
changes needed. `.env` is loaded via `python-dotenv` at import time
(`config/settings.py`); this didn't actually work before — `.env` was
documented but nothing ever loaded it into `os.environ`.

Verified live, worth knowing before touching `AlphaVantageNewsSource`:
- Its `topics` param does NOT take a lexicon-style `query=""` "no
  filter" — that convention is RSS-specific. Empty query maps to
  `DEFAULT_TOPICS` (`"economy_macro"`) instead.
- **Multiple comma-separated topics act as an AND, not an OR** —
  `"economy_monetary,economy_macro"` returned zero articles, repeatedly,
  while `"economy_macro"` alone reliably returns dozens. Don't combine
  topics expecting broader coverage.
- Even the single best topic (`economy_macro`) is still broad, generic
  financial news (earnings reports, ETF prices) — not reliably
  Fed/CPI/NFP-specific despite the name. Same "free feed is noisy
  relative to what we actually want" finding as the RSS sources; Alpha
  Vantage's free tier doesn't solve that, confirmed via a real live
  pipeline run (77 combined RSS+AV articles, real scored output).

APITube's client also exists in `data_layer/news_feed.py` but isn't
wired into `build_all_preview_sources()` yet — same opt-in-by-key
pattern would apply, just not connected.

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
   objects for past dates — build them by hand with known past NFP/CPI
   event times. `calendar_feed.py` cannot fetch historical/future-week
   periods — confirmed (live + research) that Forex Factory's feed only
   ever serves `"thisweek"`, `"lastweek"`/`"nextweek"` don't exist on
   the server at all. See `tests/run_historical_backtest.py` for the
   established hand-reconstruction pattern this project already uses.

## Architecture

```
config/settings.py       — timezones (SAST), instruments, trust weights, tuning knobs
data_layer/
  calendar_feed.py        — Forex Factory calendar, SAST conversion
  news_feed.py             — Alpha Vantage (wired in, opt-in by key) + APITube (client exists, not wired) clients
  rss_sources.py           — free RSS sources + build_all_preview_sources(),
                              split into pre-event scoring vs. backtest-only
                              ground-truth outcome feeds
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

## Symbol impact dashboard (optional)

A local web dashboard showing a BUY/HOLD/SELL-style call per tracked
symbol, driven entirely by structured calendar data (forecast vs.
actual) — no article fetching, separate from the pipeline above. See
`docs/superpowers/specs/2026-08-09-symbol-impact-dashboard-design.md`
for the full design.

```bash
pip install -r requirements-webapp.txt
python webapp/app.py
```

Then open `http://localhost:5001`. Defaults to tracking XAUUSD and US30;
add more symbols from the dashboard itself — tickers are auto-classified
(metal / USD-base FX / USD-quote FX / risk index / non-USD cross pair)
from the symbol shape, no manual config needed. A background thread
re-scores every 15 minutes; `webapp/dashboard.db` (gitignored) persists
history across restarts so the before/after diff still works after you
close and reopen the app.

## Article-based backtest accumulator (optional)

Separate from the dashboard above (which is essence-only, no articles at
all) — this accumulates REAL backtest data for the article-based
pipeline (`scoring/probability_engine.py`) automatically, going forward.
Predictions are made blind (before the event, real fetched articles),
persisted immediately; outcomes are confirmed manually afterward via
research, same rigor as `tests/run_historical_backtest.py`'s
reconstructed cases — just applied to real predictions instead.

```bash
python scoring/backtest_accumulator.py   # runs one cycle; import start_accumulator() for continuous operation
python scripts/confirm_backtest_outcomes.py --list   # see what's awaiting confirmation
python scripts/confirm_backtest_outcomes.py          # confirm outcomes interactively
```

Then view real accuracy at any time:

```python
from scoring.backtest import build_real_backtest_report
build_real_backtest_report().print_report()
```

Budget-capped: at most 2 article-fetch snapshots per (event, instrument)
pair (once on window entry, once in the final stretch) — article fetches
are rate-limited (Alpha Vantage: 25/day), unlike the dashboard's free
essence-only scoring. High-impact USD events only, no Medium-impact
widening.

This is also what finally makes real calibration of
`TIME_DECAY_HALF_LIFE_MINUTES`/`CONTRADICTION_MIN_MAGNITUDE`/the sigmoid
steepness `k` possible — once this log has enough real confirmed cases,
those constants can be revisited against genuine data instead of guesses
(see "Known gaps" below).

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
