# News Engine — Master Feature Inventory (Shipped vs. Outstanding)

**Prepared:** 2026-09-11
**Purpose:** One place to track what the Causation-Matrix/News-Engine project was *designed* to be (per `docs/News_Engine_Causation_Matrix_v2.xlsx` and the original engine's own code/docs) against what has actually *shipped* into `scoring/`, `webapp/`, and the live dashboard — so future sessions build against real gaps instead of re-discovering them. Update this file's status column as things ship; don't let it drift into another undocumented gap.

**Sources synthesized:** `docs/News_Engine_Causation_Matrix_v2.xlsx` (all 20 sheets), `docs/dashboard-review-2026-09-11.md`, `docs/fundamental-analysis-review-2026-09-11.md`, `docs/fundamental-analysis-swot-2026-08-14.md`, `BACKTEST_REPORT.md`, `git log`, a direct read of the current `scoring/`/`webapp/`/`data_layer/`/`scripts/` module list, and a live browser walkthrough of the running dashboard at `localhost:5001` (Dashboard/Calendar/History tabs + drill-down panel) added 2026-09-11.

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
| Graduated thin-sample probability cap (n=1 → 0.60, n=2 → 0.70, n=3+ unchanged) | **Shipped** (2026-09-11, Batch 1) | `config/settings.py`'s `THIN_SAMPLE_PROBABILITY_CAP_BY_SIGNAL_COUNT`, `scoring/probability_engine.py`'s `_apply_thin_sample_cap()`; targets the diagnosed FOMC 0/2 failure |
| Confidence floor independent of agreement×coverage (`min(1.0, signal_count / MIN_CONFIDENT_SAMPLE_SIZE)`) | **Shipped** (2026-09-11, Batch 1) | `config/settings.py`'s `MIN_CONFIDENT_SAMPLE_SIZE = 4`, applied in `score_bundle()` alongside the existing confidence multipliers |
| CPI zero-signal diagnosis + fix (89 articles, zero registered as a contribution) | **Shipped** (2026-09-11, Batch 2) | Diagnosed as topic-filter dilution, not a lexicon/FinBERT gap — confirmed via the live Aug-12 top_contributions (3 "contributions", all sentiment=0.0, all unrelated to CPI) and a live re-fetch showing the same noise pattern reproducing today. Fixed by extending `EVENT_RELEVANCE_KEYWORDS_BY_TITLE` (`config/settings.py`) to CPI's 4 title variants — live-verified: 13 genuine CPI/inflation articles now surface vs. 3 irrelevant ones before |
| Per-multiplier audit trail (which of macro-backdrop/COT/equity-risk/oil-shock fired on a call) | **Shipped** (2026-09-11, Batch 8) | New `confidence_multipliers_json` column on `predictions` (mirrors `top_contributions_json`'s pattern exactly), `Prediction.confidence_multipliers` parsed property, `scoring/backtest_accumulator.py`'s `_build_confidence_multipliers()`. Only includes a key when a modifier actually fired (non-None/non-default-False) — no noise from the overwhelmingly common "nothing fired" case. Centralized the 4 separate row-construction call sites into one `_prediction_from_row()` helper as part of this change — fixed a pre-existing gap where 2 of the 4 never exposed `top_contributions_json` at all |
| FinBERT conditional-language validation (P1) | **Checked, real finding — 2026-09-11** | Fed the original June-NFP failure headline ("rate hike risk IF data surprises") through `scoring/finbert_sentiment.py` directly: it scored 0.90 confidence, essentially IDENTICAL to a flat declarative control headline (0.898). **FinBERT does NOT discount confidence for conditional/hedged language** — the specific failure mode this was meant to validate is not closed by FinBERT alone. Not a code claim to act on yet, a disclosed diagnostic result |
| Pre-2026-09-03 precursor-linked calls, flagged concretely | **Checked, concrete list produced — 2026-09-11** | Queried directly: 20 distinct precursor-eligible occurrences scored before the country-scoping fix, **19 already resolved** — meaning most of the review's own n=30 "confirmed" sample carries this caveat, not a handful of edge cases. Full list in §3 below |
| Kalshi FOMC extension (P2, SWOT R4) | **Already shipped 2026-08-14 — review's "still open" note is stale** | `KALSHI_RATE_DECISION_SERIES = {"Federal Funds Rate": "KXFED"}`, live-verified the same day, real test confirms the correct month-only ticket resolution (`tests/test_backtest_accumulator.py:1059`). **Real remaining gap, structural, not a build item:** the event that actually failed 0/2 is "FOMC Meeting Minutes," a different Forex Factory title from "Federal Funds Rate" — Kalshi has no market on meeting-minutes CONTENT, only on the rate decision itself, so there is no Kalshi cross-check possible for the specific title that failed |

### 2b. Tier 1 — Causation-Matrix numeric methodology (Option A)

| Feature | Status | Where |
|---|---|---|
| `Tier1Prediction` interface (value/confidence/source/predicted_direction) | **Shipped** | `scoring/backtest.py` |
| CPI methodology (Cleveland Fed nowcast only) | **Shipped**, live-tested | 3 real cases logged; currently a confirmed no-call (genuinely split headline y/y vs m/m) |
| PPI methodology (BLS prior actual + ISM Prices Paid) | **Shipped**, live-tested | 3 real cases: 2 correct (July CPI, July PPI), 1 wrong (Sep PPI — see §1 above) |
| NFP / FOMC / GDP / Core PCE / ISM Manufacturing / ISM Services / Retail Sales methodologies | **Automation ready (2026-09-11, Batch 7), no real prediction yet — see note** | Each event's own documented POC methodology (jobless claims for NFP, CME FedWatch for FOMC, GDPNow+yield-curve for GDP, etc.) wired into the scheduled `tier1-cpi-ppi-autoresearch` task's prompt (renamed `tier1-multi-event-autoresearch`). No real occurrence for any of these 7 types was in the 3-day lookahead as of this check — nothing to log without fabricating, so nothing is logged yet. Will fire opportunistically the next time a real one appears |
| Live persistence (`tier1_predictions` table) | **Shipped** | `scoring/backtest_store.py` |
| Live dashboard display, per-instrument, alongside sentiment's own call | **Shipped** | `webapp/app.py`, `webapp/static/app.js` |
| Automatic outcome grading (Dukascopy, scheduled every 15 min) | **Shipped** | `scripts/confirm_backtest_outcomes.py` + Windows Scheduled Task `NewsEngine_OutcomeConfirm` |
| Automatic Tier1-vs-sentiment-vs-actual comparison, persisted | **Shipped** | `scoring/tier1_comparison.py`, `tier1_comparisons` table |
| Automatic pre-release research trigger (daily check, logs a call if a gap exists) | **Shipped**, not yet run | scheduled task `tier1-cpi-ppi-autoresearch` (this app's own scheduler) |
| Contradiction detection between Tier 1 and sentiment's own call | **Shipped** (2026-09-11, Batch 4) | `webapp/predictions_service.py`'s new `tier1_sentiment_conflict` field, computed after reconciliation settles the final `article_prediction`. Revises the original live-tier1-dashboard-display spec's "no agree/disagree computation on the live path" constraint — explicit user ruling, documented here. Rendered via `webapp/static/app.js`'s `tier1SentimentConflictHtml()`/`otherEventTier1ConflictMarkerHtml()`. **Real limitation found during live verification, not fixed in this batch:** the Sep 10 PPI conflict (the one real occurrence with live data) does NOT currently render on the Dashboard tab — it's neither `events[0]` nor timestamp-simultaneous with the currently-featured cluster, and the card only ever renders those. This is a bigger, pre-existing structural limit (every signal type on this dashboard is invisible once its event scrolls out of the featured cluster), not something introduced by or scoped to this batch — flagging as a real follow-up, not silently claiming full visibility |
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
| One-time schema/migration (was: 3 `PRAGMA table_info` checks re-run every request) | **Shipped** (2026-09-11, Batch 3) | `webapp/store.py`/`scoring/backtest_store.py`'s `get_connection()` — cached per resolved path, `:memory:` deliberately never cached (each call is a genuinely separate DB). Full `g`-scoped connection pooling itself still not done — SQLite is a local file, the real cost was the repeated migration overhead, not the connect() call |
| `get_predictions()` extraction into a testable service module | **Shipped** (2026-09-11, Batch 3) | `webapp/predictions_service.py`'s `build_predictions_payload()` — moved verbatim, route is now a thin open/call/close/serialize wrapper. Live-verified via a process restart + browser check, not just tests |
| Indexed/partial calendar snapshot storage (currently one JSON blob) | **Outstanding** | fine at current volume, no path to scale |
| Production WSGI server (was: Flask dev server, single-threaded) | **Shipped** (2026-09-11, Batch 3) | `webapp/app.py`'s `__main__` now calls `waitress.serve()`; `requirements.txt` updated. Live-verified: `Server: waitress` response header |
| Shared serialization helper across article/print/tier1 prediction dict-shaping | **Shipped** (2026-09-11, Batch 3) | `webapp/predictions_service.py`'s `_print_prediction_dict()`/`_tier1_prediction_dict()`, alongside the existing `_article_prediction_dict()` — `_print_prediction_dict()` now also used by `/api/calendar/date/<date>`, the actual literal duplicate the review found |

### 2e. Dashboard — frontend

| Feature | Status | Where |
|---|---|---|
| Keyed/targeted re-render (vs. full DOM teardown every 60s poll) | **Outstanding — deliberately deferred, see Batch 5** | root cause of the existing card-state-restoration hacks (expanded History panels, flipped cards); needs its own dedicated pass, no JS test suite exists to verify a rewrite against |
| Only `events[0]` and its exact-timestamp siblings ever render on the Dashboard tab — every other event for a tracked symbol (a different day/cluster) is completely invisible there, regardless of signal type | **Outstanding — found 2026-09-11 during Batch 4 live verification; assigned Batch 9** | Confirmed live: the real Sep 10 PPI Tier1-vs-sentiment conflict has no visibility path on the Dashboard tab once CPI's cluster became current the next day — same root cause as the pre-existing "only events[0] was ever rendered" note, just bigger than previously scoped (this affects ANY past-but-recent event, not only same-timestamp siblings) |
| Component boundaries in `app.js` (~1000 lines, hand-rolled string templates) | **Outstanding — deliberately deferred, see Batch 5** | `renderCard()` alone ~400 lines; needs its own dedicated pass, no JS test suite exists to verify a rewrite against |
| Consistent HTML escaping (ticker symbol interpolated raw in a couple of places) | **Shipped** (2026-09-11, Batch 5) | `symbol` now escaped in `renderCard()`'s header and `finalizeCardFlip()`'s back-face — not previously exploitable (server-validated) but now structurally enforced like every other string in the file |
| Fetch error handling on the 60s poll path | **Shipped** (2026-09-11, Batch 5) | `refreshDashboard()`/`refreshCalendar()` now catch fetch failures, show a distinct notice, never wipe already-rendered cards; live-verified by simulating a failure |
| Accessibility (ARIA roles, `aria-expanded`, hit targets, meta-text via CSS class not inline style) | **Outstanding** | minor, color has a text fallback already |
| Responsive/mobile layout | **Outstanding**, low priority unless mobile viewing becomes a real use case | hard 7-column calendar grid, zero media queries |
| No aggregate/rollup accuracy anywhere in the UI — History tab lists ~35 individual rows with no overall %, no per-event-type breakdown, no recent streak | **Outstanding — found 2026-09-11, live UI walkthrough; assigned Batch 9** | User has to manually eyeball Confirmed-vs-Missed across a growing, unsorted table to answer the one question the whole tool exists for. Same category breakdown already hand-built via SQL twice this project (`docs/fundamental-analysis-review-2026-09-11.md` §3) should be a standing feature, not a re-derived one |
| No visible warning state on the drill-down panel's "no individual article stood out" case — renders as plain grey text, same visual weight as a genuinely on-topic read | **Outstanding — found 2026-09-11, live UI walkthrough; assigned Batch 9** | Live-confirmed on tomorrow's Core CPI m/m card: two of five consecutive snapshots (Sep 8-10) had zero signal-bearing top_contributions and rendered the fallback text with no visual distinction from a confident read. Scoped down from a general article-relevance/quality indicator during implementation planning (2026-09-11): flagging every off-topic-but-nonzero top_contribution would need per-event keyword curation (`EVENT_RELEVANCE_KEYWORDS_BY_TITLE`) this codebase doesn't have for most events yet — a content task, not a UI one, correctly out of scope here. Batch 2's CPI-specific keyword fix already prevents new off-topic contributions from appearing for CPI going forward; this item only elevates the ALREADY-DETECTABLE empty-contributions case to a real visible warning |
| Tier1-vs-sentiment conflict has no visibility in the History tab (only the Dashboard card, and only when `events[0]`-eligible per the row above) | **Outstanding — found 2026-09-11, live UI walkthrough; assigned Batch 9** | History table has no Tier1 column at all — the real Sep 10 PPI conflict (Tier1 `Certain`/bullish, sentiment correctly `bearish`) is unauditable from the UI; you'd have to already know to query the database, same as this review did |
| ~~US30 has no card on the Dashboard tab at all~~ | **False positive as a code task — confirmed 2026-09-11 during Batch 9 scoping; not in Batch 9** | `webapp/store.py`'s `tracked_symbols` table already has full add/remove support (`add_symbol()`/`remove_symbol()`/`list_tracked_symbols()`, lines 367-377), and `classify_symbol()` already recognizes US30 as an index (`webapp/symbols.py`'s `INDICES` set). Nothing to build — it's missing purely because nobody has clicked "Add" with `US30` in the existing textbox. Retracting from the implementation plan |
| Outcome vocabulary in the History tab is inconsistent and unexplained (`Confirmed`/`Missed`/`No strong call`/`Awaiting confirmation`/`Actual not comparable`, no legend) | **Outstanding — found 2026-09-11, live UI walkthrough; assigned Batch 10** | "Confirmed" reads ambiguously as "the actual print is confirmed" rather than "the prediction was correct" — costly ambiguity during a fast scan before a release |
| Confidence has no visual weighting in the History table or Dashboard cards (1% and 100% render as identical plain text) | **Outstanding — found 2026-09-11, live UI walkthrough; assigned Batch 10** | No color/bar/threshold treatment distinguishes a genuinely strong call from one riding on noise — the exact distinction this whole review has been trying to make is invisible in the UI itself |
| No filter or sort on the History table | **Outstanding — found 2026-09-11, live UI walkthrough; assigned Batch 10** | No way to view "just CPI," "just XAUUSD," "just misses," or a date range — the category breakdown that mattered most for this review required direct SQL because the UI has no equivalent |
| ~~Blank Instr. cell on the `Core CPI m/m` / Aug 12, 2026 History row~~ | **False positive — confirmed 2026-09-11 during Batch 9 scoping, not a bug** | `HistoryRow.instrument` is `None` BY DESIGN for a print-call-backed numeric row (`webapp/history.py`'s own docstring: "None for a print-call-backed numeric row"), and `app.js`'s `renderHistoryTable()` renders that as `r.instrument ?? ""` — an empty cell, on purpose, since a print-direction call is about the number, not a specific instrument. Same convention as the row's `previous`/`forecast`/`actual` columns rendering "—" for genuinely absent values. Retracting this from the earlier UI review — it was a misdiagnosis, not a rendering defect |
| Drill-down ("why this changed") exists only for pending Dashboard cards, not resolved History rows | **Outstanding — found 2026-09-11, live UI walkthrough; assigned Batch 10** | Exactly when you'd want to see which articles drove a wrong call (to judge whether it's a repeat failure mode), the UI removes that view |
| Calendar tab: nav buttons crowd/overlap at the pane's default width; Confirmed/Estimated legend dots too small to read at a glance | **Outstanding — found 2026-09-11, live UI walkthrough; assigned Batch 10** | Minor visual polish, not functional |

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

**Additional caveat, checked concretely 2026-09-11 (Batch 8):** of the 30 "confirmed" calls above, **19 distinct occurrences are precursor-eligible and were scored before the 2026-09-03 country-scoping fix** (`data_layer/event_context.py`, commit `b985c3e`) — Average Hourly Earnings m/m, CPI m/m, CPI y/y, Core CPI m/m, Core CPI y/y (all ×2 instruments), Core PCE Price Index m/m (×2), ISM Manufacturing PMI, Non-Farm Employment Change (×2), Prelim GDP q/q (×2), Unemployment Rate (×2), across occurrences on 2026-08-12, 2026-08-26, 2026-09-01, and 2026-09-04. That's roughly two-thirds of the whole sample, not a handful of edge cases — this accuracy figure carries that caveat broadly, not narrowly.

---

## 4. Recommended build order

See §5 below — grouped into shippable batches by touched files and dependency order, not just a flat priority list. That grouping *is* the build order; don't maintain two separate orderings that can drift out of sync.

---

## 5. Deployment batching — what to ship together, and why

Grouped by touched files/area and dependency order, not just priority — the goal is fewer, more coherent deploys instead of one PR per row above. Each batch is independently shippable; do them in this order because later batches build on top of files earlier batches clean up or extend.

**Batch 1 — Scoring engine, two small fixes, same file, ship together (P0, low risk, ~1 PR) — ✅ SHIPPED 2026-09-11**
- Graduated thin-sample probability cap (n=1/n=2/n=3+)
- Confidence floor independent of agreement×coverage
Both are isolated, scoped changes inside `scoring/probability_engine.py`'s existing confidence/probability math, both directly fix the diagnosed FOMC 0/2 failure. No shared work with any other batch. 5 new tests added (`tests/test_probability_engine.py`), full suite 552/552 passing. Not yet re-validated against a live FOMC re-score (prospective fix — the historical 0/2 calls stay in the DB as-is; only future calls benefit).

**Batch 2 — CPI zero-signal, investigate-then-fix (P0, sequenced on its own) — ✅ SHIPPED 2026-09-11**
- Pulled the live Aug-12 top_contributions (3 entries, all sentiment=0.0, all unrelated to CPI: a UAE-Germany investment deal, a Nubank product launch, an OpenAI product launch) — confirmed topic-filter dilution, not a lexicon/FinBERT framing gap.
- Extended `EVENT_RELEVANCE_KEYWORDS_BY_TITLE` to `CPI m/m`/`CPI y/y`/`Core CPI m/m`/`Core CPI y/y`, same pattern as the existing FOMC entries.
- Live-verified: re-fetching today's real news window shows 13 genuine CPI/inflation articles surviving the filter vs. 3 irrelevant ones before the fix. 2 new tests in `tests/test_event_context.py`, full suite 554/554 passing.

**Batch 3 — Dashboard backend debt paydown (no new features, same files Tier 2/3 will also need to touch) — ✅ SHIPPED 2026-09-11**
- `get_predictions()` extracted into `webapp/predictions_service.py`'s `build_predictions_payload()` — moved verbatim, route is now a thin wrapper. Live-verified via a process restart + browser check.
- One-time schema/migration caching in both `get_connection()`s (`webapp/store.py`, `scoring/backtest_store.py`) — `:memory:` deliberately excluded (each call is a genuinely separate DB; caching it would leave every connection after the first with no tables). Full `g`-scoped connection pooling scoped OUT — SQLite is a local file, the actual cost was the repeated migration overhead, not the connect() call itself; noting this as a deliberate scope reduction, not a silent drop.
- Shared `_print_prediction_dict()`/`_tier1_prediction_dict()` helpers alongside the existing `_article_prediction_dict()` — `_print_prediction_dict()` now used by both `/api/predictions` and `/api/calendar/date/<date>`, the actual literal duplicate the review found.
- Production WSGI server: `waitress.serve()` replaces `app.run()`. Live-verified: `Server: waitress` response header.
8 new/updated tests (2 migration-caching tests each in `test_webapp_store.py`/`test_backtest_store.py`). Full suite: 558/558 passing throughout.

**Batch 4 — Tier1-vs-sentiment contradiction detection (P0, contained blast radius) — ✅ SHIPPED 2026-09-11**
- New `tier1_sentiment_conflict` field in `webapp/predictions_service.py` (not `reconcile_group()` itself — a genuinely different comparison: two SOURCES for the same title, not co-released titles disagreeing with each other), computed after reconciliation settles the final `article_prediction` value.
- Explicit user ruling revising the original "no agree/disagree on the live path" constraint (asked before building, not routed around).
- Frontend: `tier1SentimentConflictHtml()` (featured card) + `otherEventTier1ConflictMarkerHtml()` (sibling row), same warning palette as the existing co-released-conflict badge.
- 3 new tests, full suite 561/561. Live-verified: the real Sep 10 PPI conflict (bearish sentiment vs bullish Tier1) round-trips correctly through `/api/predictions`; CSS/markup independently confirmed correct via direct DOM injection.
- **Real gap found, not fixed here:** that same real conflict doesn't currently render anywhere on the Dashboard tab, because it's neither the featured event nor timestamp-simultaneous with today's cluster — logged as its own outstanding row in §2e, out of scope for this batch.

**Batch 5 — Frontend debt paydown — split 2026-09-11, only the small half shipped**
- ✅ **Consistent HTML escaping** — `symbol` is now `escapeHtml()`-ed everywhere it's interpolated (`renderCard()`'s header, `finalizeCardFlip()`'s back-face header/button/id), matching the discipline every other string in this file already follows. Live-verified via console + rendered text, no behavior change.
- ✅ **Fetch error handling on the poll path** — `refreshDashboard()`/`refreshCalendar()` now wrap their `fetch`/`.json()` in try/catch, checking `resp.ok` too. On failure: logs to console, shows a new distinct notice (`#predictions-poll-error-notice` / `#calendar-poll-error-notice`, `index.html`) reading "Couldn't reach the server — showing the last data received," and — critically — **does NOT wipe `cardsEl`**, so a transient blip no longer destroys what's already rendered. Clears automatically on the next successful poll. Live-verified by monkey-patching `window.fetch` to reject and confirming: notice appears, existing card count unchanged, notice clears on recovery.
- ⏸️ **Keyed/targeted re-render** (replaces full-DOM-rebuild + state-restoration hacks) — **deferred**, not built. A rewrite of the full-teardown pattern in `refreshDashboard()` and its restoration hacks.
- ⏸️ **Component boundaries in `app.js`** (~1000 lines, `renderCard()` alone ~400) — **deferred**, not built.
Both deferred items are real refactors of code with **zero automated test coverage in this codebase** (no JS test suite exists) — the only verification path is manual browser inspection. Given that risk profile, doing them properly needs its own dedicated pass with careful manual verification, not a fold-in alongside three other batches. Flagging honestly rather than rushing a large, unverified rewrite of the file every other frontend feature (including Tier 2/3's eventual card content) depends on. Still recommended to land before Batch 6, per the original reasoning — just not bundled with the two small, safe items above.

**Batch 6 — Tier 2/3 exogenous-context architecture (the big one — needs its own brainstorm→spec→plan cycle first)**
- Build from `AdHoc_Category_Taxonomy` + `Discovery_Detector_Spec` (already-designed, not a blank page)
- Wire `Layer1_Event_to_USD`/`Layer2_Asset_Transmission` as the causal-chain connecting an exogenous event to an instrument effect
- Resolve the two open design questions from this session (fixed checklist vs. open-ended; log-only context vs. override-capable)
Sequenced last on purpose: it's the largest, most novel piece, it's the "next signal source" both debt-paydown batches above are explicitly clearing room for, and its own design questions aren't resolved yet — don't start this until Batches 3 and 5 land, or it inherits the exact technical debt those batches exist to remove.

**Batch 7 — Remaining Tier1 per-event methodologies (independent, incremental, no urgency) — automation shipped 2026-09-11, real predictions still pending real occurrences**
- Checked the live calendar for all 7 remaining event types — none had a real occurrence in the 3-day lookahead as of 2026-09-11. Per this project's own "predict-then-check against real events only" discipline, nothing was logged (fabricating one would violate the same rule this project has held everywhere else).
- Instead: read each event's own already-documented POC methodology (`POC_NFP_Leading_Indicators`, `POC_FOMC_Rate_Decision`, `POC_GDP_Nowcast`, `POC_Core_PCE`, `POC_ISM_Manufacturing_PMI`, `POC_ISM_Services_PMI`, `POC_Retail_Sales`) and wired the specific sourced methodology for each — including which candidate indicators were already tested and REJECTED (ADP for NFP, unadjusted same-month CPI for PCE, consumer confidence for Retail Sales) — into the scheduled `tier1-cpi-ppi-autoresearch` task, renamed `tier1-multi-event-autoresearch`, extending its daily 3-day lookahead from CPI/PPI-only to all 9 event types.
- Real predictions for these 7 types will log automatically the first time a real occurrence enters the lookahead window — same opportunistic, no-fabrication discipline as CPI/PPI, just not yet triggered by a real event.
Each is independent of every other batch and of each other — ship opportunistically whenever there's a real upcoming release to predict-then-check against, same discipline as CPI/PPI.

**Batch 8 — Remaining P1/P2 items, no batching needed (small, independent, low urgency) — ✅ DONE 2026-09-11, mixed outcomes reported honestly**
- FinBERT validation: **checked, real negative finding** — FinBERT does NOT discount confidence for conditional/hedged language (0.90 confidence on the hedged NFP headline vs. 0.898 on a flat declarative control). The failure mode it was meant to close is not closed.
- Precursor caveat: **checked, concrete list produced** — 19 of 20 precursor-eligible occurrences (≈two-thirds of the n=30 accuracy sample) predate the fix. See §3.
- Confidence multiplier audit trail: **shipped** — `confidence_multipliers_json` column, `_build_confidence_multipliers()`, 4 new tests, full suite 565/565.
- Kalshi FOMC extension: **already shipped 2026-08-14** — the review's "still open" note is stale. Real remaining gap is structural (no Kalshi market exists on FOMC Meeting Minutes CONTENT, only on the separate rate-decision event), not a build item.

**Batch 9 — Dashboard/History trust surface (P0, live UI walkthrough 2026-09-11) — ✅ IMPLEMENTED 2026-09-11 via subagent-driven-development, plan at `docs/superpowers/plans/2026-09-11-dashboard-history-trust-surface.md`, full ledger at `.superpowers/sdd/2026-09-11-dashboard-history-trust-surface/progress.md`**
- Aggregate + per-event-type accuracy rollup on the History tab — **shipped**: `webapp/history.py`'s `compute_history_stats()`, `/api/history/stats` route, rendered in `webapp/static/app.js`'s `renderHistoryStats()`.
- Low-signal-coverage warning badge on the drill-down panel's existing "no individual article stood out" state — **shipped**: `.low-signal-warning` CSS class (reuses the existing orange warning palette), wired into `articleProgressionEntryHtml()`.
- Surface the Tier1-vs-sentiment conflict field (Batch 4) in the History tab — **shipped**: `compute_tier1_sentiment_conflict()` extracted to a new dependency-free `webapp/conflict.py` (moved there during the final whole-branch review to fix a 27x import-time regression the initial extraction to `webapp/predictions_service.py` caused), `HistoryRow.tier1_conflict` field, rendered as an inline badge in `renderHistoryTable()`.
- Fix the `events[0]`-only Dashboard rendering limit — **shipped**: `otherTrackedEventsHtml()`, bounded at `OTHER_TRACKED_EVENTS_LIMIT=3`, with a fix-round correction so Tier1/sentiment-conflict-flagged events are promoted ahead of pure recency (the original recency-only ordering would have let the real motivating case — an aging resolved conflict — permanently lose ground and never resurface).
- ~~Add US30 to the dashboard's tracked symbols~~ — dropped during scoping: confirmed not a code task (see the retracted §2e row above), just click Add with `US30` in the existing textbox
- Final whole-branch review (opus) found 4 Important issues beyond what any single task's scoped review could see — all fixed in one consolidated pass, re-reviewed clean: the `webapp.conflict` extraction above (import-weight regression), an `webapp/history.py` N+1 query reintroduction (now using the existing `get_latest_tier1_predictions_bulk()`), an inaccurate `STATS_LOOKBACK_LIMIT` comment plus a new `window_limit` field surfaced in the rollup UI, and a new Flask-level test covering `/api/history`'s `tier1_conflict` key (previously untested end-to-end). 5 Minor findings carried into Batch 10 below rather than expanding this batch further.
- Test suite: 575 passed (net +1 test from the final-review fix), 1 pre-existing (baseline, unrelated) failure throughout every commit on this batch.
Touches the same files Batch 3/4/5 already cleared debt in (`webapp/predictions_service.py`, `webapp/app.js`, `webapp/history.py`, `webapp/app.py`) plus a new `webapp/conflict.py`. Shipped before Batch 6 as recommended (same "clear room before the next signal source" reasoning as Batches 3/5).

**Batch 10 — Dashboard/History polish (P1/P2, live UI walkthrough 2026-09-11) — not started**
- Standardize History outcome vocabulary (`Confirmed`/`Missed`/`No strong call`/`Awaiting confirmation`/`Actual not comparable`) with a legend or plainer labels (e.g. `Correct`/`Wrong`)
- Color/bar-code confidence in the History table and Dashboard cards, with a visible low-confidence threshold
- Filter/sort on the History table (event title, instrument, date range, outcome)
- Extend the drill-down "why" panel to resolved History rows, not just pending Dashboard cards
- Calendar tab nav-button crowding and legend-dot sizing
- **Carried over from Batch 9's final whole-branch review (2026-09-11, all Minor, non-blocking):**
  - History rollup panel (`webapp/static/app.js`'s `renderHistoryStats()`) renders a placeholder (`"Overall: 0 calls made, 0 no-call"` + an empty collapsed "By event type") on an empty DB instead of nothing at all — a genuine conflict with this project's own "render nothing, not a placeholder, when absent" convention. Fix: guard on `overall.correct + overall.wrong + overall.no_call === 0` and clear the container instead.
  - `loadHistoryStatsIfNeeded()` name promises the `historyLoaded`-style idempotence guard that `loadHistoryIfNeeded()` actually implements; this function has none of its own (only idempotent because its sole caller already sits behind that guard). Rename to `loadHistoryStats()` for honesty.
  - `by_event_title` is sorted twice — once server-side in Python (`webapp/app.py`), once client-side in JS (`webapp/static/app.js`) — redundant, and the two collations can disagree on non-ASCII titles. Drop the JS-side sort, keep the server-side one.
  - `loadHistoryStatsIfNeeded()`'s stats fetch has no `try/catch`/`resp.ok` check (unlike `refreshDashboard()`'s established pattern) — a failure leaves the table intact (fail-open) but throws an unhandled rejection and never retries since `historyLoaded` is already `true`.
  - The Tier1-vs-sentiment conflict rule's rationale comment is now duplicated near-verbatim in `webapp/predictions_service.py`'s call site, its docstring in `webapp/conflict.py`, and `webapp/history.py`'s field comment — trim the call-site copy to a one-line pointer at the canonical docstring.
Independent of every other batch; no urgency, ship opportunistically.

---

## 6. Explicitly out of scope / deferred by prior decisions (don't re-litigate without a reason)

- **Option B** (a more automated consolidation approach, likely overlapping with the Tier 2/3 work above) — explicitly deferred until Option A produced real comparison data. That data now exists (n=3, 1 wrong).
- **Live-fetch integration** for Cleveland Fed/BLS/ISM's own APIs — Tier 1 research stays WebSearch + human/LLM judgment by design; `predicted_direction` must never be auto-derived from a formula.
- **Retroactive backfill** of the two completed July 2026 cases into the live `tier1_predictions` table — they stay backtest-only artifacts.
