# News Engine — Fundamental Analyst Review

**Prepared:** 2026-09-11 (SAST)
**Reviewer stance:** Senior fundamental analyst assessing `news_engine` as a decision-support system for XAUUSD (primary) and US30 (secondary) directional bias ahead of major USD releases — is the design effective, and what does the real evidence say, not the claimed evidence.
**Method:** Direct read of `scoring/probability_engine.py`, `config/settings.py`, `scoring/outcome_classifier.py`, `BACKTEST_REPORT.md`, the 2026-08-14 internal SWOT, plus original SQL queries against the live `scoring/backtest_log.db` (`predictions`, `outcomes`, `tier1_predictions` tables) and a git-log diff of scoring/config commits made since the SWOT. Real accuracy figures below are computed directly from the database, not quoted from prior documentation.

---

## 1. Bottom line

The architecture is sound: a multi-source triangulation model (article sentiment, precursor surprises, print-direction inference, trend streaks, Kalshi pricing, macro-backdrop/COT/oil-shock/equity-risk cross-checks) blended onto one USD-directional axis with a defensible trust hierarchy, confidence explicitly decoupled from probability, and unusually honest inline documentation of every unvalidated simplification. That part hasn't changed and isn't in question.

The evidence behind it does not support "high probability" as a general claim. The only widely-quoted figure — 89% — was earned against 30 fabricated articles, not live data. Pulling the real, live-confirmed outcomes directly from the database gives **73% accuracy on 30 directional calls (n=40 event/instrument pairs, 10 no-calls)** as of this review, up from 68%/22 calls a few days prior. That headline number is not representative of what matters: it is carried almost entirely by lower-impact labor/growth prints, while the two events you'd actually risk the most capital on — CPI and FOMC — have either zero directional calls ever made (CPI) or a 0% hit rate (FOMC, n=2). A newly added second prediction system (Tier 1 Causation-Matrix) made its first live call at maximum stated confidence and was wrong, on the same event the original engine correctly called.

**Verdict: not yet trustworthy enough to size real risk against, on a per-category basis, for the events that matter most.** The lower-impact categories showing high accuracy are also low-sample and shouldn't be over-read either.

---

## 2. Real accuracy: claimed vs. live

| | Reconstructed backtest (`BACKTEST_REPORT.md`) | Live-confirmed, first pull (this session, turn 1) | Live-confirmed, current |
|---|---|---|---|
| Sample | 30 fabricated articles, 10 events | 314 live scoring runs, 32 confirmed pairs | 341 live scoring runs, 40 confirmed pairs |
| Directional calls | 9 | 22 | 30 |
| Correct | 8 | 15 | 22 |
| **Accuracy** | **89%** | **68%** | **73%** |

The 89% figure is explicitly disclaimed by its own report as not evidence of real accuracy — articles were paraphrased and manually timestamped in a network-isolated sandbox. The 73% figure is real but small-sample (binomial 95% CI roughly 55–86% on n=30) and the improvement from 68%→73% is fully explained by four new PPI outcomes landing correct (see §3), not by any code fix.

---

## 3. Accuracy by event category (live-confirmed only, current)

Query: last pre-event prediction snapshot per (event_title, instrument, event_time_utc), joined against `outcomes` where `source='live'` (Dukascopy-confirmed, not manually seeded).

| Category | Correct | Wrong | No-call | Calls made | Accuracy |
|---|---|---|---|---|---|
| **CPI (m/m, y/y, core)** | 0 | 0 | 8 | 0 | n/a — never once called a direction |
| **FOMC Meeting Minutes** | 0 | 2 | 0 | 2 | **0%** |
| PPI (incl. Core PPI) | 4 | 4 | 0 | 8 | 50% |
| NFP (Non-Farm Employment Change) | 1 | 1 | 0 | 2 | 50% |
| Average Hourly Earnings m/m | 1 | 1 | 0 | 2 | 50% |
| Unemployment Rate | 2 | 0 | 0 | 2 | 100% |
| Jobless Claims | 6 | 0 | 1 | 6 | 100% |
| Prelim GDP q/q | 2 | 0 | 0 | 2 | 100% |
| ISM Manufacturing PMI | 1 | 0 | 0 | 1 | 100% |
| Fed Chairman Warsh Speaks | 2 | 0 | 0 | 2 | 100% |
| Prelim Benchmark Payrolls Revision | 2 | 0 | 0 | 2 | 100% |
| Core PCE Price Index m/m | 1 | 0 | 1 | 1 | 100% |
| **Total** | **22** | **8** | **10** | **30** | **73%** |

**Reading this correctly:** the 100%-accuracy rows are all n=1 or n=2 — a coin flip called correctly twice is not a demonstrated edge. The categories with enough sample to say anything (PPI n=8, CPI n=8-attempts-but-zero-calls) are the ones that actually matter for position sizing, and neither supports a high-probability claim. PPI's earlier 0/4 read (first pull, before four more outcomes resolved) has already regressed to 50% — a caution that cuts both ways: don't trust a clean 0% any more than you'd trust a clean 100% at this sample size.

---

## 4. Root-caused failures (from `top_contributions_json`, not inference)

**FOMC Meeting Minutes (2026-08-19, both instruments, wrong):** driven by a single article (`article_count=1`), `usd_sentiment=-0.63`, producing 80% probability and 100% confidence — both at their respective ceilings. This is not a cap failure; `THIN_SAMPLE_PROBABILITY_CAP=0.80` worked exactly as coded. The bug is that the cap is a flat step regardless of *how* thin the sample is — n=1 gets the same ceiling as n=2. Separately, `_agreement_and_coverage()` cannot penalize "only one voice existed" — with one contribution, agreement=1.0 and coverage=1.0 trivially, so confidence hit its own ceiling too. Two related but distinct gaps in the same call.

**CPI (all titles, 2026-08-12, `article_count=89`, zero calls):** `top_contributions_json` is empty despite 89 articles in the window — meaning essentially none cleared the sentiment threshold to register as a contribution at all. `EVENT_RELEVANCE_KEYWORDS_BY_TITLE` only filters the FOMC family; CPI gets zero topic filtering, so 89 "articles" may be diluting real CPI-specific coverage with generic macro noise, or the lexicon/FinBERT combination may not fire on typical pre-CPI headline framing ("inflation data due Wednesday") the way it fires on NFP's more declarative language. **Not yet distinguished — needs the raw article titles pulled before picking a fix.**

**PPI (2026-08-13, 0/4 at the time, now 4/8 overall): undiagnosable for the original failure.** `top_contributions_json` is `null` for that run — it predates the column being populated. The September 10 PPI release (correct, 4/4) does have the column populated and shows a clean `bearish` read matching the actual outcome; no similar diagnosis is possible for the August miss.

---

## 5. New since the 2026-08-14 internal SWOT (14 commits reviewed)

Most Priority-0/1 items from the internal SWOT (`docs/fundamental-analysis-swot-2026-08-14.md`) have already been actioned: FinBERT is now default-on (R2), the thin-sample probability cap exists (R3), macro-backdrop/COT/equity-risk/oil-shock checks are wired in as confidence-only dampeners (R5 and the "fundamental signals batch"), and Kalshi's date-ticketed series are partially extended (R4). What follows is new information this review surfaced that the SWOT does not cover:

- **A second, parallel prediction system now exists and contradicted the original engine on its first real test.** Commits `e404f73`/`6ce779b`/`f0beb9e`/`a5b2dcd`/`b811109` added a "Tier 1 Causation-Matrix" pathway — manually/LLM-researched forecasts with their own confidence label (`Certain`/`Guessing`), persisted in a new `tier1_predictions` table and now rendered on the dashboard alongside the sentiment engine's own call. On the Sept 10 PPI release, Tier 1 called `bullish` at **`Certain`** confidence (logged 2026-09-07, "second consecutive confirming month" thesis citing ISM Prices Paid); the actual outcome was `bearish`. The sentiment/article engine, on the same event, correctly called `bearish`. Two systems disagreed on your dashboard; the one claiming maximum confidence was wrong. Nothing found in the reviewed commits reconciles or flags a Tier 1 vs. accumulator contradiction the way `reconcile_group()` already does for co-released events within the sentiment engine alone.
- **A real data-integrity bug was found and fixed (commit `b985c3e`, Sept 3), with a caveat.** `event_history` had no country dimension, so foreign releases sharing a generic FF title with a US one (Australia's "CPI m/m", UK's "Retail Sales m/m"/"Unemployment Rate", Germany's "PPI m/m", etc.) could be miscounted as USD precursor data by title-only lookups. Fixed going forward — `get_precursor_events_for()` now hard-requires `country == "USD"`. **Caveat:** any precursor-driven score computed before Sept 3 (essentially everything reviewed for CPI←PPI or NFP←ADP linkage in this and prior reviews) was potentially exposed. There is no practical way to retroactively tell which specific historical calls were affected — treat pre-Sept-3 precursor-linked calls as somewhat less trustworthy evidence than face value, not because the logic was wrong but because an input to it could have been contaminated.
- **CPI and FOMC: no new outcomes since the prior pull.** Both remain exactly as diagnosed above — zero calls ever on CPI, 0/2 on FOMC. No commit reviewed touches either failure mode directly.

---

## 6. Recommended fixes, ranked

### P0 — justified by concrete evidence pulled this session

1. **Scale the thin-sample probability cap by signal count, not a flat step.** Currently n=1 and n=2 both get the same 0.80 ceiling. Make it graduated — e.g. n=1 → 0.60, n=2 → 0.70, n=3+ → current logic. Directly targets the FOMC Meeting Minutes miss.
2. **Give confidence an absolute-sample-size floor, independent of agreement×coverage.** `_agreement_and_coverage()` cannot distinguish "1 of 1 agree" from "10 of 10 agree" — both hit 1.0. Multiply confidence by a saturating function of raw signal count (e.g. `min(1.0, signal_count / MIN_CONFIDENT_SAMPLE)`, `MIN_CONFIDENT_SAMPLE` ≈ 4–5), applied alongside the existing multipliers. Same shape as the existing confidence dampeners in `score_bundle()`.
3. **Diagnose CPI's zero-signal problem before touching anything else on CPI.** Pull the raw article titles from the 89-article Aug-12 window (not in `top_contributions_json` since nothing qualified as a contribution). Determine whether it's topic dilution (extend `EVENT_RELEVANCE_KEYWORDS_BY_TITLE` to CPI/Core CPI) or a lexicon/FinBERT framing gap specific to CPI headlines (a scoring fix, not a filtering one). These need different fixes — don't guess which.
4. **Backfill or accept the `top_contributions_json` gap for pre-instrumentation rows.** The August PPI miss is currently undiagnosable because the column didn't exist yet. Not fixable retroactively without re-scoring, but should be flagged so no conclusion is drawn about that specific miss beyond "unknown cause."
5. **Extend contradiction detection to cover Tier 1 vs. the sentiment engine's own call**, not just co-released events within the sentiment engine. The Sept 10 PPI divergence (Tier 1 `Certain`/wrong vs. sentiment `bearish`/right) is exactly the kind of contradiction `reconcile_group()` was built to surface — it just doesn't look at Tier 1 yet. This is a scoped extension of code that already exists, not new architecture.

### P1 — validate what's already built

6. **Confirm FinBERT actually catches the conditional-language failure it was built for.** Feed the original June-NFP failure headline ("rate hike risk IF data surprises") plus the PPI/CPI near-misses through `scoring/finbert_sentiment.py` directly and confirm no flat-declarative misread. Ten-minute check against existing code.
7. **Don't size risk off CPI, FOMC, or PPI category accuracy yet** — sample sizes (0, 2, 8) are too small to support any conclusion, including the encouraging-looking ones elsewhere in the table.
8. **Re-derive or explicitly flag any historical precursor-linked call made before 2026-09-03** given the country-contamination fix — can't retroactively confirm which were affected, but shouldn't be cited as clean evidence without that caveat attached.

### P2 — lower urgency

9. **Log which confidence multiplier(s) fired on a given call** (macro-backdrop, COT, equity-risk, oil-shock, chain-conflict) in the same audit trail `top_contributions_json` provides for articles — otherwise the next miss in one of these newer signal paths will be as undiagnosable as the August PPI case was.
10. **Prioritize Kalshi's date-ticketed extension for FOMC** (SWOT R4, still open) — FOMC is simultaneously your highest-impact tracked event and currently your worst-performing one (0/2, both thin-sample-driven); a real-money market read is the most direct available check against a repeat of the single-article 80% failure mode.

---

## 7. What would move this from "logically sound" to "tradeable"

In order: close the two thin-sample gaps in probability and confidence (P0 #1–2, both are small, scoped code changes against logic that already exists); resolve the CPI dead-zone (P0 #3) since it currently contributes nothing on your most-traded print; extend contradiction detection to the new Tier 1 layer (P0 #5) before that layer's confidence label is trusted at face value on a live dashboard; then let the confirmed-outcome dataset grow past double digits per category — especially CPI and FOMC — before treating any category's accuracy as a real, tradeable edge rather than noise.
