# News Engine — Master Feature Inventory (Shipped vs. Outstanding)

**Prepared:** 2026-09-11
**Purpose:** One place to track what the Causation-Matrix/News-Engine project was *designed* to be (per `docs/News_Engine_Causation_Matrix_v2.xlsx` and the original engine's own code/docs) against what has actually *shipped* into `scoring/`, `webapp/`, and the live dashboard — so future sessions build against real gaps instead of re-discovering them. Update this file's status column as things ship; don't let it drift into another undocumented gap.

**Sources synthesized:** `docs/News_Engine_Causation_Matrix_v2.xlsx` (all 20 sheets), `docs/dashboard-review-2026-09-11.md`, `docs/fundamental-analysis-review-2026-09-11.md`, `docs/fundamental-analysis-swot-2026-08-14.md`, `BACKTEST_REPORT.md`, `git log`, and a direct read of the current `scoring/`/`webapp/`/`data_layer/`/`scripts/` module list.

**Maintenance rule — living document, not a one-time snapshot:** any new news_engine functionality discussed in code, chat, or Cowork that gets agreed as something to build (now or later, "planned") must be added here — a new row in the relevant §2 table, or a new batch in §5 if it doesn't fit an existing row. Functionality that's discussed and explicitly agreed *not* worth deploying does not need an entry — this file tracks real backlog, not a transcript of every idea raised. When something here actually ships, flip its status and move the entry's detail into a "shipped" note rather than deleting the row, so the history of what was designed vs. built stays intact.

---

## 1. The engine as designed — three layers, one holistic view

The workbook's own README (written before any of Option A existed) describes an architecture the codebase never fully built. Restated in the terms clarified this session:

1. **News/sentiment engine** (the original, pre-Causation-Matrix core) — lexicon + FinBERT/Claude sentiment over RSS/news articles. Opinion-based, live, continuously re-scoring. **This is the only layer that's fully shipped.**
2. **Tier 1 — per-event numeric calculation** ("pure maths, not opinion") — a deterministic-once-inputs-land read of what a specific print is likely to show, built from real precursor data (BLS actuals, ISM Prices Paid, Cleveland Fed nowcast, etc.), one methodology per event type. **Partially shipped** — only CPI and PPI have a live `Tier1Prediction` methodology; 7 more POC event types are documented but never coded.
3. **Tier 2/3 — exogenous market context** (oil price shocks, geopolitical/war events, Fed-independence shocks, Treasury buyback changes, tariff actions, government shutdowns) — deliberately *not* part of any single event's calculation, because these can happen independently of and on top of any scheduled release. **Fully designed, zero percent shipped.** This is `AdHoc_Category_Taxonomy` + `Discovery_Detector_Spec` + `Periodic_Qualitative_Calendar`, plus the causal-chain knowledge base (`Layer1_Event_to_USD` → `Layer2_Asset_Transmission`) meant to connect any of the above to an actual instrument effect.

The 2026-09-10 PPI miss (Tier 1 called `Certain`/bullish, wrong) is a direct symptom of shipping layer 2 in isolation with layer 3 never built — nothing in the live system checks "was anything exogenous happening that day" before treating Tier 1's narrow calculation as a standalone verdict.

---

## 2. Feature inventory

### 2a. Sentiment / core scoring engine (Layer 1 above)

| Feature | Status | Where |
|---|---|---|
| Lexicon + FinBERT/Claude sentiment scoring, multi-source triangulation (article/precursor/print/trend/Kalshi) on one -1..+1 axis | **Shipped** | `scoring/probability_engine.py` |
| Confidence decoupled from probability (agreement × coverage) | **Shipped** | `scoring/probability_engine.py:393-432` |
| Contradiction detection (recent vs. older article window) | **Shipped** | `scoring/probability_engine.py:462-501` |
| Co-released event reconciliation (strict unanimity across titles at the same instant) | **Shipped** | `webapp/reconciliation.py` (2026-09-04/05) |
| Kalshi prediction-market integration | **Shipped**, partially extended | `data_layer/kalshi_feed.py` — date-ticketed series extension still open (SWOT R4) |
| Macro-backdrop / COT / equity-risk / oil-shock confidence dampeners | **Shipped** | `data_layer/macro_backdrop.py`, `data_layer/cot_positioning.py` |
| Country-scoped precursor lookups (fixes foreign-release title collisions) | **Shipped** (2026-09-03, commit `b985c3e`) | `data_layer/event_context.py` — **caveat:** any precursor-linked call scored before this fix is unverifiable, not necessarily wrong |
| Graduated thin-sample probability cap (n=1 vs n=2 vs n=3+) | **Outstanding — P0** | fundamental-analysis-review §6.1: FOMC's 0/2 record traces directly to a flat 0.80 cap regardless of how thin the sample is |
| Confidence floor independent of agreement×coverage (n=1 shouldn't hit 1.0 confidence) | **Outstanding — P0** | same review §6.2 |
| CPI zero-signal diagnosis (89 articles, zero registered as a contribution) | **Outstanding — P0** | review §4: not yet determined whether it's topic-filter dilution or a lexicon/FinBERT framing gap specific to CPI headlines |
| Per-multiplier audit trail (which of macro-backdrop/COT/equity-risk/oil-shock fired on a call) | **Outstanding — P2** | review §6.9 |

### 2b. Tier 1 — Causation-Matrix numeric methodology (Option A)

| Feature | Status | Where |
|---|---|---|
| `Tier1Prediction` interface (value/confidence/source/predicted_direction) | **Shipped** | `scoring/backtest.py` |
| CPI methodology (Cleveland Fed nowcast only) | **Shipped**, live-tested | 3 real cases logged; currently a confirmed no-call (genuinely split headline y/y vs m/m) |
| PPI methodology (BLS prior actual + ISM Prices Paid) | **Shipped**, live-tested | 3 real cases: 2 correct (July CPI, July PPI), 1 wrong (Sep PPI — see §1 above) |
| NFP / FOMC / GDP / Core PCE / ISM Manufacturing / ISM Services / Retail Sales methodologies | **Outstanding** | Documented as POC sheets in the workbook (`POC_NFP_Leading_Indicators` etc., 7 more event types), never coded as `Tier1Prediction` sources |
| Live persistence (`tier1_predictions` table) | **Shipped** | `scoring/backtest_store.py` |
| Live dashboard display, per-instrument, alongside sentiment's own call | **Shipped** | `webapp/app.py`, `webapp/static/app.js` |
| Automatic outcome grading (Dukascopy, scheduled every 15 min) | **Shipped** | `scripts/confirm_backtest_outcomes.py` + Windows Scheduled Task `NewsEngine_OutcomeConfirm` |
| Automatic Tier1-vs-sentiment-vs-actual comparison, persisted | **Shipped** | `scoring/tier1_comparison.py`, `tier1_comparisons` table |
| Automatic pre-release research trigger (daily check, logs a call if a gap exists) | **Shipped**, not yet run | scheduled task `tier1-cpi-ppi-autoresearch` (this app's own scheduler) |
| Contradiction detection between Tier 1 and sentiment's own call | **Outstanding — P0** | fundamental-analysis-review §6.5: `reconcile_group()` exists for co-released sentiment titles but doesn't look at Tier 1 at all — the Sep 10 divergence (Tier 1 `Certain`/wrong vs sentiment/right) shipped with zero flag on the dashboard |
| `POC_Sub_Event_Consolidation` standardized-surprise heuristic wired into an actual calculation | **Outstanding** | Currently a documented, `predicted_direction`-stays-manual heuristic only (explicit warning comment on `Tier1Prediction`); "Option B" in this project's own terms, explicitly deferred until real comparison data existed — it now does (n=3, 1 wrong) |

### 2c. Tier 2/3 — exogenous market context (never built)

| Feature | Status | Where documented |
|---|---|---|
| `AdHoc_Category_Taxonomy` — 8 real, sourced categories (oil/OPEC+, geopolitical war-driven oil shock, Fed-independence shocks, Fed Chair transitions, tariff actions, government shutdown, Treasury buyback changes, credit-rating actions) | **Documented, zero code** | workbook sheet, real instances logged (e.g. Feb 2026 Iran war / WTI +78% intraday) |
| `Discovery_Detector_Spec` — anomaly detector (DXY/10Y/30Y/XAUUSD moves vs 20-day rolling stdev, flags unclassified shocks, pulls same-day headlines) | **Documented, zero code** | workbook sheet — explicitly designed to mirror `EventScoreTracker`'s existing contradiction-flagging pattern, "a new consumer of already-built feeds, no new data layer needed" |
| `Periodic_Qualitative_Calendar` — fixed-schedule non-numeric events (FOMC, Treasury Quarterly Refunding, Jackson Hole) | **Documented, zero code** | workbook sheet |
| `Layer1_Event_to_USD` — sourced causal-chain knowledge base (event → USD/rate/yield effect) | **Documented, zero code** | workbook sheet, dozens of real dated rows |
| `Layer2_Asset_Transmission` — USD effect → per-instrument transmission nuance (XAUUSD/XAGUSD/BTC/US30/FX majors, each with its own documented mechanism and caveats) | **Documented, zero code** | workbook sheet |
| Any mechanism connecting Tier 2/3 context to a Tier 1 verdict's confidence/direction | **Outstanding — not yet designed**, this session's open brainstorm | Two open design questions remain: (1) fixed checklist vs. open-ended judgment, (2) log-only context vs. actually overriding Tier 1's own call |

### 2d. Dashboard — backend

| Feature | Status | Where |
|---|---|---|
| `/api/predictions` N+1 query batching | **Shipped** (2026-09-11, `7f596bc`) | `webapp/store.py`, `scoring/backtest_store.py` bulk lookups |
| Per-request DB connection pooling / one-time schema migration | **Outstanding** | dashboard-review: schema + 3 `PRAGMA table_info` checks re-run on every request |
| `get_predictions()` extraction into a testable service module | **Outstanding** | 800+ line `app.py`, one 230-line route function |
| Indexed/partial calendar snapshot storage (currently one JSON blob) | **Outstanding** | fine at current volume, no path to scale |
| Production WSGI server (currently Flask dev server, single-threaded, shares process with scheduler + actuals-sync threads) | **Outstanding** | `app.py:808` |
| Shared serialization helper across article/print/tier1 prediction dict-shaping | **Outstanding** | only article prediction got the shared-helper treatment |

### 2e. Dashboard — frontend

| Feature | Status | Where |
|---|---|---|
| Keyed/targeted re-render (vs. full DOM teardown every 60s poll) | **Outstanding** | root cause of the existing card-state-restoration hacks (expanded History panels, flipped cards) |
| Component boundaries in `app.js` (~1000 lines, hand-rolled string templates) | **Outstanding** | `renderCard()` alone ~300 lines |
| Consistent HTML escaping (ticker symbol interpolated raw in a couple of places) | **Outstanding**, not currently exploitable (server-validated) but not structurally enforced | `app.js:260`, `:465` |
| Fetch error handling on the 60s poll path | **Outstanding** | a transient network blip silently freezes the dashboard on stale data, no visible indicator |
| Accessibility (ARIA roles, `aria-expanded`, hit targets, meta-text via CSS class not inline style) | **Outstanding** | minor, color has a text fallback already |
| Responsive/mobile layout | **Outstanding**, low priority unless mobile viewing becomes a real use case | hard 7-column calendar grid, zero media queries |

### 2f. Automation / operations

| Feature | Status | Where |
|---|---|---|
| Auto-restart supervisor for dashboard + accumulator processes | **Shipped** | `scripts/run_engine.bat` / `_restart_loop.bat` |
| Auto-start after reboot | **Shipped** | Windows Scheduled Task `NewsEngine_AutoStart` (at logon) |
| Automatic outcome confirmation (every 15 min) | **Shipped** | Windows Scheduled Task `NewsEngine_OutcomeConfirm` |
| Automatic Tier 1 pre-release research trigger (daily) | **Shipped**, first live run pending | app-scheduler task `tier1-cpi-ppi-autoresearch` |

---

## 3. Real accuracy, as of this review (not claimed, pulled live from `scoring/backtest_log.db`)

From `docs/fundamental-analysis-review-2026-09-11.md` — figures will drift as more outcomes resolve; re-pull rather than trust this snapshot after any material time has passed.

| Category | Calls made | Accuracy | Read with care because |
|---|---|---|---|
| CPI (m/m, y/y, core) | 0 | n/a | Never once called a direction — zero-signal bug, unresolved |
| FOMC Meeting Minutes | 2 | 0% | Both driven by a single-article, ceiling-capped call (thin-sample bug) |
| PPI | 8 | 50% | Regressed from an earlier 0/4 as more outcomes resolved — small-sample, don't over-read either direction |
| Everything else (NFP, AHE, Unemployment Rate, Jobless Claims, GDP, ISM Mfg, Fed Chair Warsh, Payrolls Revision, Core PCE) | 1-6 each | mostly 100% | n=1 or n=2 in every row — not a demonstrated edge |
| **Total** | **30** | **73%** | 95% CI roughly 55–86% on n=30 — real, but small |

**Bottom line carried over from that review:** not yet trustworthy enough to size real risk against, specifically for the two events (CPI, FOMC) you'd actually risk the most capital on.

---

## 4. Recommended build order

See §5 below — grouped into shippable batches by touched files and dependency order, not just a flat priority list. That grouping *is* the build order; don't maintain two separate orderings that can drift out of sync.

---

## 5. Deployment batching — what to ship together, and why

Grouped by touched files/area and dependency order, not just priority — the goal is fewer, more coherent deploys instead of one PR per row above. Each batch is independently shippable; do them in this order because later batches build on top of files earlier batches clean up or extend.

**Batch 1 — Scoring engine, two small fixes, same file, ship together (P0, low risk, ~1 PR)**
- Graduated thin-sample probability cap (n=1/n=2/n=3+)
- Confidence floor independent of agreement×coverage
Both are isolated, scoped changes inside `scoring/probability_engine.py`'s existing confidence/probability math, both directly fix the diagnosed FOMC 0/2 failure. No shared work with any other batch — do first, smallest blast radius, immediately testable against the real FOMC misses already in the DB.

**Batch 2 — CPI zero-signal, investigate-then-fix (P0, sequenced on its own)**
- Pull raw article titles from the 89-article Aug-12 window
- Fix topic-filter dilution (extend `EVENT_RELEVANCE_KEYWORDS_BY_TITLE` to CPI/Core CPI) **or** a lexicon/FinBERT framing gap — diagnosis decides which, don't guess both at once
Kept separate from Batch 1 because scope is genuinely unknown until the diagnosis step runs — bundling it with Batch 1 risks scope creep on a PR that was supposed to be small.

**Batch 3 — Dashboard backend debt paydown (no new features, same files Tier 2/3 will also need to touch)**
- `get_predictions()` extraction into a testable service module
- One-time schema/migration + connection pooling
- Shared serialization helper across article/print/tier1 dicts
- Production WSGI server swap
Bundle these four: they're all refactor/ops work against `webapp/app.py`/`store.py` with no behavior change, and the dashboard-review explicitly flags `get_predictions()` as needing extraction "before the next signal source gets added" — Tier 2/3 (Batch 6) is that next signal source. Doing this now means Tier 2/3 lands in a service module, not a 230-line route function that's already past readable.

**Batch 4 — Tier1-vs-sentiment contradiction detection (P0, contained blast radius)**
- Extend `reconcile_group()`'s pattern to flag Tier 1 vs. sentiment disagreement, same way it already flags co-released sentiment titles
Touches `webapp/reconciliation.py` + the same dashboard card rendering Batch 3 will have just cleaned up — sequence after Batch 3 so this doesn't get written twice (once against the messy route, once against the extracted service).

**Batch 5 — Frontend debt paydown (same file Tier 2/3's new card content will also need, do before it lands)**
- Keyed/targeted re-render (replaces full-DOM-rebuild + state-restoration hacks)
- Component boundaries in `app.js`
- Consistent HTML escaping
- Fetch error handling on the poll path
Bundle these — all touch `app.js`, none are behavior-visible features on their own, and same "next signal source" argument as Batch 3: Tier 2/3 will add another card element, and every element added to the current hand-rolled template makes the eventual refactor more expensive. Accessibility and responsive/mobile are real but lower-priority — fold into this batch only if it's convenient, don't let them block it.

**Batch 6 — Tier 2/3 exogenous-context architecture (the big one — needs its own brainstorm→spec→plan cycle first)**
- Build from `AdHoc_Category_Taxonomy` + `Discovery_Detector_Spec` (already-designed, not a blank page)
- Wire `Layer1_Event_to_USD`/`Layer2_Asset_Transmission` as the causal-chain connecting an exogenous event to an instrument effect
- Resolve the two open design questions from this session (fixed checklist vs. open-ended; log-only context vs. override-capable)
Sequenced last on purpose: it's the largest, most novel piece, it's the "next signal source" both debt-paydown batches above are explicitly clearing room for, and its own design questions aren't resolved yet — don't start this until Batches 3 and 5 land, or it inherits the exact technical debt those batches exist to remove.

**Batch 7 — Remaining Tier1 per-event methodologies (independent, incremental, no urgency)**
- NFP / FOMC / GDP / Core PCE / ISM Manufacturing / ISM Services / Retail Sales, one event type at a time, mirroring the CPI/PPI pattern already shipped
Each is independent of every other batch and of each other — ship opportunistically whenever there's a real upcoming release to predict-then-check against, same discipline as CPI/PPI.

**Batch 8 — Remaining P1/P2 items, no batching needed (small, independent, low urgency)**
- FinBERT validation against the NFP conditional-language failure (10-minute check, no deploy)
- Flag pre-2026-09-03 precursor-linked calls
- Log which confidence multiplier fired per call
- Kalshi FOMC date-ticketed extension

---

## 6. Explicitly out of scope / deferred by prior decisions (don't re-litigate without a reason)

- **Option B** (a more automated consolidation approach, likely overlapping with the Tier 2/3 work above) — explicitly deferred until Option A produced real comparison data. That data now exists (n=3, 1 wrong).
- **Live-fetch integration** for Cleveland Fed/BLS/ISM's own APIs — Tier 1 research stays WebSearch + human/LLM judgment by design; `predicted_direction` must never be auto-derived from a formula.
- **Retroactive backfill** of the two completed July 2026 cases into the live `tier1_predictions` table — they stay backtest-only artifacts.
