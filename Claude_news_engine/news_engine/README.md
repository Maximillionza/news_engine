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
  dukascopy_feed.py         — free historical price lookup (dukascopy-python,
                               opt-in), backs --auto outcome confirmation below
scoring/
  sentiment.py              — lexicon-based USD-directional sentiment fallback
  probability_engine.py     — time-decay + trust weighting, instrument mapping,
                               sigmoid probability, agreement-based confidence,
                               intra-run contradiction detection
  history.py                — tracks direction flips across successive scoring
                               runs through an event window
  backtest.py                — replays events through the pipeline, compares
                                predicted vs. actual direction
  backtest_store.py          — SQLite log for the article-based accumulator
                                below (predictions/outcomes/dismissals)
  backtest_accumulator.py    — the accumulator's own scoring/persistence cycle
  outcome_classifier.py      — Dukascopy-price-based bullish/bearish/ambiguous
                                classification, backs --auto below
scripts/
  run_live_check.py           — end-to-end RSS-only live run, start here
  run_all.py                   — single launcher for dashboard + accumulator together
  run_accumulator.py           — continuous accumulator process
  confirm_backtest_outcomes.py — manual + --auto outcome confirmation CLI
tests/
  test_scoring_smoke.py       — synthetic unit tests, no network needed
  run_historical_backtest.py  — the 10-event reconstructed backtest (reference only)
```

## Run everything at once (optional)

The dashboard and the accumulator (both described below) are separate
processes by design — but if you want both running together without
juggling two terminals, one launcher starts both:

```bash
python scripts/run_all.py
```

Combined, tagged output (`[dashboard]` / `[accumulator]`) in one
terminal; Ctrl+C stops both cleanly, and either process crashing stops
the other too — no daemonization, no auto-restart. This is purely an
additive convenience: each script still works exactly the same run on
its own, and `scripts/confirm_backtest_outcomes.py` (needs a real
terminal for interactive prompts) and `scripts/run_live_check.py`
(one-off diagnostic) are deliberately NOT part of it — neither fits
"continuous service."

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
re-scores on an adaptive schedule (`webapp/scheduler.py`) — a sparse
12-hourly baseline days out, ramping to hourly once an event is within
24h, then every 5 minutes in the final hour (and briefly after, in case
a release is delayed). A detected reschedule (an event's time shifting
between fetches) triggers an extra-tight check in the final 15 minutes
before the new time. `webapp/dashboard.db` (gitignored) persists history
across restarts so the before/after diff still works after you close and
reopen the app.

**The calendar is fetched live from exactly one place: this background
loop.** It persists whatever it fetches into `webapp/dashboard.db`'s
`calendar_snapshot` table — but only when the data actually changed;
an unchanged fetch is a no-op, not even a timestamp bump ("store and use
as current until new information supersedes this"). `/api/calendar` and
`/api/predictions` never fetch live themselves — they just read whatever
is currently persisted, instantly, regardless of the live feed's health
at that moment. This means a Forex Factory rate-limit or outage no longer
blanks the dashboard; it keeps showing the last known-good calendar until
the background loop successfully fetches something new. Only genuinely
fresh installs (or right after a restart, before the first background
cycle completes) see "Calendar data not yet available."

If the article-based accumulator below has already scored an event for
XAUUSD/US30, its card also shows "backed by N articles" — a read-only
display sourced from the accumulator's own database
(`scoring/backtest_log.db`); the dashboard's own score computation stays
essence-only (no article fetching), this is purely extra context shown
alongside it. Won't appear for other tracked symbols or events the
accumulator hasn't processed — that's expected, not a bug.

## Article-based backtest accumulator (optional)

Separate from the dashboard above (which is essence-only, no articles at
all) — this accumulates REAL backtest data for the article-based
pipeline (`scoring/probability_engine.py`) automatically, going forward.
Predictions are made blind (before the event, real fetched articles),
persisted immediately; outcomes are confirmed manually afterward via
research, same rigor as `tests/run_historical_backtest.py`'s
reconstructed cases — just applied to real predictions instead.

```bash
python scripts/run_accumulator.py                     # runs continuously — this is what actually keeps it accumulating; Ctrl-C to stop
python scoring/backtest_accumulator.py                # or: runs ONE cycle then exits, useful for a manual one-off check
python scripts/confirm_backtest_outcomes.py --list    # see what's awaiting confirmation
python scripts/confirm_backtest_outcomes.py           # confirm outcomes interactively
python scripts/confirm_backtest_outcomes.py --auto    # auto-confirm clear cases first (see below), then interactive for what's left
```

Runs as its own separate process from the dashboard (`webapp/app.py`) —
starting one does NOT start the other, by design. Run both if you want
both, or use `python scripts/run_all.py` (see "Run everything at once"
above) to start both together.

**`--auto` auto-confirms outcomes using free historical price data**
(Dukascopy, no API key) instead of manual research: a real post-event
price move ≥0.15% in the 30 minutes after the release gets confirmed
automatically, anything smaller or a failed fetch is left in the same
manual-review queue exactly as before — never auto-classified as
neutral, since a small move means "needs a human to check," not
"confidently no reaction." Needs the optional dependency:

```bash
pip install -r requirements-dukascopy.txt
```

Bare `confirm_backtest_outcomes.py` (no `--auto`) is completely
unaffected — still fully manual, zero network calls to Dukascopy, no
extra dependency required.

Then view real accuracy at any time:

```python
from scoring.backtest import build_real_backtest_report
build_real_backtest_report().print_report()
```

High-impact USD events only, no Medium-impact widening — article fetches
are rate-limited (Alpha Vantage: 25/day), unlike the dashboard's free
essence-only scoring. Also blends in already-released precursor data
(PPI before CPI, ADP before NFP — see `config.settings.PRECURSOR_EVENTS`)
alongside article sentiment when a real precursor relationship exists and
has actually printed.

**Checks every instrument for every active event on every cycle** — but
the cycle itself now has its own adaptive cadence, tighter than a flat
"check every loop tick" and independent of the dashboard's tiers
(`scoring/backtest_accumulator.py`'s
`compute_accumulator_interval_seconds()`):

| Window | Interval |
|---|---|
| Nothing within `PRE_EVENT_WINDOW_HOURS` yet | 12h (`FAR_INTERVAL_SECONDS`) |
| Inside the pre-event window, still >24h out | 1h (`HOURLY_INTERVAL_SECONDS`) |
| Within 24h of the event, outside the final hour | 15min (`DAY_OF_EVENT_INTERVAL_SECONDS`) |
| Final hour before release, or ≤30min after it (`POST_RELEASE_GRACE_MINUTES`) | 5min (`FINAL_INTERVAL_SECONDS`) — never throttled |

A rolling-24h check budget (`check_log` table,
`record_check()`/`count_recent_checks()` in `scoring/backtest_store.py`)
guards against Alpha Vantage quota exhaustion: once the rolling count
hits `DAILY_CHECK_BUDGET_THRESHOLD` (20), the Hourly and Day-of-event
tiers fall back to a 3h floor (`BUDGET_FALLBACK_INTERVAL_SECONDS`) — the
Final tier is exempt, since missing the check right before an actual
release is worse than a little extra spend.

Whether a check gets **written** is a separate, diff-aware decision:
only if the result materially differs from the current stored
prediction — a direction flip, or a same-direction probability move of
at least 10 percentage points. Supporting articles that just reinforce
the existing read are checked and discarded without a write — "current
sentiment is the truth until articles are found to contradict or change
it." No cap on how many times a genuinely material change can be
recorded.

**Revised 2026-08-11 (twice)** — first pass replaced the old
twice-total-per-pair budget model (window entry + a narrow final-30min
stretch) with "check every cycle," since a real news shift over most of
a multi-day pre-event window was never picked up under the old model:
observed live, CPI predictions sat with an identical `scored_at_utc` for
a full 24 hours despite the process running. That fixed staleness but
checked on every loop tick regardless of how far out the event was —
this second pass adds the Hourly/Day-of-event/Final tiering above so
checks ramp up as the event approaches instead of firing at a flat rate,
plus the rolling budget fallback so a busy day (multiple concurrent
events) can't blow through Alpha Vantage's 25/day quota unnoticed.

This is also what finally makes real calibration of
`TIME_DECAY_HALF_LIFE_MINUTES`/`CONTRADICTION_MIN_MAGNITUDE`/the sigmoid
steepness `k` possible — once this log has enough real confirmed cases,
those constants can be revisited against genuine data instead of guesses
(see "Known gaps" below).

### Economic-print prediction + trend history

Two additive signals, separate from the article-based direction call above:

- **Print-direction call** (`scoring/print_direction.py`) — "will THIS
  release come in higher or lower than forecast," derived from article
  language via `config.settings.PRINT_SURPRISE_LEXICON` (currently covers
  CPI m/m, Core CPI m/m, Non-Farm Employment Change, Unemployment Rate —
  config-only to extend). Reuses the accumulator's already-fetched article
  bundle, zero extra fetch cost. Shown on the dashboard as a "📊 Print call"
  badge next to the article-based read.
- **Event history** (`webapp/store.py`'s `event_history` table) — persists
  forecast/previous/actual per event occurrence, captured by
  `webapp/scheduler.py`'s existing fetch cycle for every calendar event
  (all impact levels), surviving the weekly Forex Factory rollover that
  previously erased it. A "History ▾" toggle on each dashboard card shows
  past occurrences plus a `summarize_trend()` line ("beat forecast 3 of
  last 4", "trending higher for 2 consecutive releases").

Both were purely additive/display when first shipped — see
`docs/superpowers/specs/2026-08-11-economic-print-prediction-trend-history-design.md`
for that original design and its out-of-scope list (numeric print-value
estimation, feeding the trend back into scoring). The trend-history
feed-back into scoring has since shipped — see the next subsection.

### Trend-history feed-back into scoring

The two signals above now also feed back into the article-based
accumulator's actual instrument scoring
(`scoring/probability_engine.score_bundle()`), not just the dashboard
display — gated so neither contributes anything on thin data:

- **This occurrence's print call** blends in at
  `PRINT_CALL_TRUST_WEIGHT=0.5` (below a real precursor's `0.9`, above raw
  article trust) whenever it's `higher`/`lower` (never `in_line`), decaying
  like a precursor across the pre-event window.
- **The event's historical beat/miss streak** blends in at
  `TREND_STREAK_TRUST_WEIGHT=0.3`, with no time decay, but only once
  `MIN_OCCURRENCES_FOR_TREND_PRIOR=3` confirmed past occurrences exist —
  below that, exactly like a `None` print call, it contributes nothing at
  all, not a diluted nudge.

Both are additive to `score_bundle()`'s existing weighted-average math —
called without them, `score_bundle()` produces byte-for-byte the same
result as before this feature, verified by a dedicated regression test.
`scoring/backtest_accumulator.py` computes the trend signal via a
short-lived **read-only** connection to the dashboard's own
`event_history` table (`webapp/store.py`) — the one deliberate crossing of
this project's usual dashboard/accumulator pipeline separation, mirroring
the existing reverse precedent where `webapp/app.py` already reads the
accumulator's DB read-only for display.

See
`docs/superpowers/specs/2026-08-12-trend-history-scoring-feedback-design.md`
for the full design, including why the trust weights and the
3-occurrence gate are launch defaults rather than tuned values — this
session's first live CPI release produced one correct print call and one
wrong one out of two, exactly the kind of thin sample this design
protects live scoring from over-trusting.

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
- **Dukascopy's Terms of Use conflict with `--auto` outcome confirmation,
  read and confirmed 2026-08-10.** Their ToS explicitly bans "any
  'scraper,' 'robot,' 'bot,' ... or any other automate[d] device, program,
  tool, algorithm, process or methodology to access, acquire, copy, or
  monitor any portion of the WEBSITE," and separately bans using their
  data "to construct a database of any kind." `get_price_at()`'s
  programmatic fetch and `outcomes` table storage both do exactly that —
  this is a real ToS violation, not just an availability risk. Knowingly
  left running as-is (personal, low-volume, non-commercial use) — an
  informed decision, not an oversight. Revisit if usage grows, or if a
  properly-licensed price source turns up.
- `--auto`'s `MEASUREMENT_WINDOW_MINUTES` (30) and
  `CLEAR_MOVE_THRESHOLD_PCT` (0.15%) in `scoring/outcome_classifier.py`
  are unvalidated guesses, same "don't retune without real evidence"
  discipline as the constants above — revisit once real auto-confirmed
  data accumulates, not before.
- **`scoring/backtest.py`'s calibration harness and `scripts/run_live_check.py` don't pass `print_call`/`trend_signal` into `score_bundle()`** — only `scoring/backtest_accumulator.py`'s live cycle does. Backtested/live-check accuracy numbers therefore don't reflect the trend-history feed-back feature at all; they measure `score_bundle()` as if it were still article+precursor-only. Revisit if/when calibrating those two constants (`PRINT_CALL_TRUST_WEIGHT`/`TREND_STREAK_TRUST_WEIGHT`) against backtest results specifically — see `docs/superpowers/specs/2026-08-12-trend-history-scoring-feedback-design.md`'s out-of-scope list.
