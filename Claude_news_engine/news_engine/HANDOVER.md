# News Engine — Handover Doc

Status as of 2026-08-08 (SAST). Written for whoever/whatever picks this up next
(including a future Claude Code session with no memory of this one).

## What this project is

Standalone Python system that scores directional probability (XAUUSD primary,
US30 also configured) ahead of major USD economic releases, from two
independent angles:

1. **Article-based pipeline** (`scoring/probability_engine.py`) — real news
   articles (RSS + Alpha Vantage) scored for USD-directional sentiment,
   time-decayed and trust-weighted, blended with structured calendar
   surprise data.
2. **Essence-only dashboard** (`webapp/`) — Flask UI, no article fetching at
   all, purely forecast-vs-actual calendar math per tracked symbol.

These are **deliberately separate concerns**, run as separate processes, by
design — this boundary was reinforced repeatedly through the session and
should not be collapsed.

## Run it

```bash
# Article pipeline — one-off live check
python scripts/run_live_check.py

# Dashboard (essence-only, own process)
pip install -r requirements-webapp.txt
python webapp/app.py            # http://localhost:5001

# Article-based backtest accumulator (own process, continuous)
python scripts/run_accumulator.py       # Ctrl-C to stop
python scoring/backtest_accumulator.py  # or: one cycle then exit

# Confirm accumulated predictions against real outcomes
python scripts/confirm_backtest_outcomes.py --list
python scripts/confirm_backtest_outcomes.py

# Real accuracy report at any time
python -c "from scoring.backtest import build_real_backtest_report as b; b().print_report()"
```

**Running `webapp/app.py` does NOT start the accumulator, and vice versa.**
Run both explicitly if you want both. This was asked and answered directly
mid-session — worth restating here since it's the kind of thing that gets
assumed wrong.

No API keys required to start (RSS-only by default). Alpha Vantage is
opt-in: copy `.env.example` → `.env`, set `ALPHA_VANTAGE_API_KEY`. A real
key (`UB1NI694Q1SN2IE6`) is already in the gitignored `.env` — never
committed, confirmed via `git status`.

## Architecture map

```
config/settings.py       — SAST timezone, instruments, trust weights, all tuning knobs, load_dotenv()
data_layer/
  calendar_feed.py         — Forex Factory calendar ("thisweek" ONLY — see Known limitations), usd_surprise_score(), find_precursor_events()
  news_feed.py              — Alpha Vantage (wired) + APITube (client exists, NOT wired) + deduplicate_articles()
  rss_sources.py            — RSS feeds + build_all_preview_sources()
  event_context.py          — bundles event + pre-event news window, no-lookahead cutoff
scoring/
  sentiment.py               — naive lexicon, final fallback tier
  finbert_sentiment.py       — local FinBERT, opt-in (ENABLE_FINBERT_SENTIMENT)
  llm_sentiment.py           — Claude API fallback for FinBERT low-confidence, opt-in (ENABLE_LLM_SENTIMENT)
  probability_engine.py      — time-decay + trust weighting, sigmoid probability, coverage-aware confidence, precursor blending
  backtest.py                 — replay/report machinery + build_real_backtest_report() (real accumulated data)
  backtest_store.py           — SQLite predictions/outcomes log, late-bound DB_PATH
  backtest_accumulator.py     — budget-capped (2 snapshots/pair) continuous scoring loop
scripts/
  run_live_check.py           — end-to-end RSS-only live run
  run_accumulator.py          — long-running entry point, actually calls start_accumulator()
  confirm_backtest_outcomes.py — interactive outcome-confirmation CLI
webapp/
  app.py, scheduler.py, store.py, scoring_service.py, symbols.py, static/{index.html,style.css,app.js}
  — Flask dashboard, adaptive polling, SQLite dashboard.db
tests/                       — plain assert+print, NOT pytest (project convention)
docs/superpowers/{specs,plans}/ — design docs + plans for the two big features built this session
```

## What got built/fixed this session, in order

1. **Live-network validation pass** — ran smoke test → calendar → RSS →
   live check → real backtest. Fixed 3 real bugs found live: dead Reuters
   RSS URL (replaced with Google News RSS scoped to `site:reuters.com`),
   BLS RSS 403 (Akamai bot-fingerprinting, documented as unfixable,
   backtest-only path so not blocking), investing.com pubDate parse
   (`%Y-%m-%d %H:%M:%S` fallback added).
2. **Confidence scoring bug** — `confidence = agreement × coverage`
   replaced a formula that reported ~100% confidence from 1 signal article
   among many silent ones.
3. **Leading-indicator "precursor events"** — minor/medium events ahead of
   a major one (FOMC/CPI/NFP) now contribute a decayed, trust-weighted
   surprise signal via `usd_surprise_score()` / `find_precursor_events()`,
   with their own slower half-life so a 48h-old print isn't crushed by the
   fast article decay.
4. **Contextual sentiment (3-tier stack)** — lexicon keyword-matching
   couldn't handle hedged language ("could trigger a hawkish adjustment
   if..."). Added local FinBERT primary + Claude API fallback for
   FinBERT's own low-confidence cases, lexicon as final fallback. Both
   contextual tiers are **explicit env-var opt-in**
   (`ENABLE_FINBERT_SENTIMENT`, `ENABLE_LLM_SENTIMENT`) — a real bug was
   caught and fixed where merely having `torch`/`transformers` importable
   silently changed default output.
5. **Symbol Impact Dashboard** — full Flask UI: per-symbol BUY/HOLD/SELL
   gauge, month-grid + day-strip calendar with today-vs-event highlighting,
   two-tone (green=increase/red=decrease) before/after diff donut.
   Essence-only by design (no articles). Built via
   superpowers:subagent-driven-development (7 tasks); final whole-branch
   review caught 2 Critical bugs (pending-state never persisted so the
   diff could never render; dedup logic silently limited to 1 row per
   event forever) — both fixed and re-reviewed clean.
6. **Dashboard live-production fixes** — 429 rate-limit from unshared
   calendar fetches (fixed with a TTL cache), fixed-interval polling
   replaced with adaptive tiers (`NEAR_WINDOW_HOURS=4`,
   `FAR_THRESHOLD_HOURS=48` → 60min/15min/5min), event-selection tie-break
   bug (resolved events now always outrank pending ones at the same or
   nearer proximity — confirmed as the intended rule with the user).
7. **"Outstanding items" sweep**, one item at a time per user's explicit
   pacing preference: confirmed `EVENT_SURPRISE_DIRECTION` "typos" were a
   false positive (nothing fixed); declined to arbitrarily retune
   `TIME_DECAY_HALF_LIFE_MINUTES`/`CONTRADICTION_MIN_MAGNITUDE`/sigmoid `k`
   without real data (this is why item 8 below exists); fixed a genuine
   `RISK_SENTIMENT_DAMPENING` DRY violation; wired in Alpha Vantage (real
   key supplied in chat, `.env` loading was itself a bug — `load_dotenv()`
   was never called); confirmed Forex Factory's `lastweek`/`nextweek`
   endpoints are permanently nonexistent (not a bug, docs corrected); fixed
   `count_predictions()`'s under-scoping — see item 8.
8. **Article-Based Backtest Accumulator** — the forward-accumulating real
   prediction/outcome log needed to eventually calibrate the untouched
   constants from item 7. Built via subagent-driven-development (5 tasks).
   Final review caught 1 Critical bug (`count_predictions()` wasn't scoped
   to `event_time_utc`, so recurring event titles — NFP, CPI, etc. — would
   permanently stop accumulating after their first-ever occurrence used up
   the budget) + fixed a real double-spend bug (article bundle was being
   fetched once per instrument instead of once per event). Both fixed,
   re-reviewed clean, merged.
9. **Wired up the runner script** — `start_accumulator()` existed but
   nothing ever called it for continuous operation. Created
   `scripts/run_accumulator.py`, verified live, merged.

## Known limitations / things to watch

- **Forex Factory calendar only ever serves `"thisweek"`** — confirmed
  live + via research that `lastweek`/`nextweek` return a plain 404, they
  don't exist on the server. Real rate limit: ~2 downloads/5min, recommend
  weekly caching (this caused two real 429 incidents this session before
  the TTL cache was added).
- **Alpha Vantage topics are AND, not OR** — combining
  `"economy_monetary,economy_macro"` returns 0 articles. `DEFAULT_TOPICS`
  is `"economy_macro"` alone, and even that is mostly generic financial
  news, not reliably Fed/CPI/NFP-specific.
- **Untuned constants**: `TIME_DECAY_HALF_LIFE_MINUTES`,
  `CONTRADICTION_MIN_MAGNITUDE`, sigmoid `k` in
  `probability_engine._score_to_probability()` are still placeholders —
  intentionally left alone pending real data from the accumulator (item 8
  above exists specifically to make this eventually possible).
- **No git remote configured** — pushing is blocked; needs a repo URL from
  the user, never resolved this session.
- **APITube client exists but isn't wired into
  `build_all_preview_sources()`** — same opt-in-by-key pattern as Alpha
  Vantage would apply, just not connected.
- **US30's `risk_sentiment` mapping** is flagged in code as a
  simplification — worth revisiting if US30 backtest accuracy comes out
  weak relative to gold's.

## Explicitly deferred / not yet started

From the accumulator's final review, triaged by the reviewer as
"fast follow-up, not blocking" — none started yet:

1. Final snapshot lands at the 4-hour mark (start of near-window) rather
   than closer to the actual event — open design decision.
2. No expiry/dismissal for a prediction whose event gets
   rescheduled/canceled — sits in the confirmation queue forever.
3. `record_outcome()`'s `actual_direction` isn't validated at the data
   layer — a typo (e.g. "Bullish" capitalized) can crash
   `build_real_backtest_report()`. Validation currently only exists in the
   interactive CLI.

From the broader outstanding-items inventory:

- Free historical price-data source research (user asked for this "in the
  background" — not yet begun; this is what would eventually let the
  accumulator auto-confirm outcomes instead of manual research).
- Dashboard polish (all Minor severity): `/api/predictions` lacks the
  stale-data indicator `/api/calendar` has; `/api/predictions/<symbol>/history`
  has zero test coverage; no `id` tiebreaker on `ORDER BY scored_at_utc`;
  `flask` unpinned in `requirements-webapp.txt`; pending card doesn't show
  which event/when; no CSRF protection on symbol-management endpoints;
  `DEFAULT_SYMBOLS` narrower than the originally-chosen "major USD pairs"
  default — reviewed 2026-08-10: no record anywhere in the repo of what that
  original list actually was, and `["XAUUSD", "US30"]` matches
  `config/settings.py`'s `INSTRUMENTS` exactly (every default symbol is
  therefore guaranteed to actually score). Left as-is rather than guess at a
  lost list; revisit only if a real "majors" set is explicitly requested.

## Working conventions established this session (for whoever continues)

- User wants each fix/feature requested **one at a time**, confirmed
  explicitly before proceeding to the next — don't batch fixes ahead of
  being asked.
- Branch → work → `git merge --no-ff` locally → delete branch. No remote
  yet, so no PRs.
- Big features go through `superpowers:brainstorming` → spec in
  `docs/superpowers/specs/` → `superpowers:writing-plans` → plan in
  `docs/superpowers/plans/` → `superpowers:subagent-driven-development`
  (fresh subagent per task + per-task review + final whole-branch review
  on a more capable model) → `superpowers:finishing-a-development-branch`.
  This caught real, empirically-reproduced Critical bugs on **both** major
  features this session (dashboard's pending-lifecycle gap, accumulator's
  per-occurrence budget-cap gap) that no individual task review had caught
  — keep using the final whole-branch review step, it's earned its cost
  twice.
- Tests in this repo are plain `assert` + `print` + `if __name__ ==
  "__main__"` — not pytest, anywhere.
- Never commit real API keys — `.env` is gitignored, confirmed clean via
  `git status` after adding the Alpha Vantage key.
