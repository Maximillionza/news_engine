# news_engine Light Interim Audit: Interpretation and Impact Scoring

**Date:** 2026-10-29 (SAST) | **Code state:** HEAD `3583159`, live worktree `.worktrees/news-engine-live`, read-only | **Full audit:** scheduled after the weekly reset on 2026-11-03

---

## 1. Scope and method

This was a light audit that covered two sections only. Section (7) is fundamental interpretation: what a data print or news article is taken to mean for USD, gold and US30. Section (11) is news impact and relevance scoring: which articles count, how strongly they count, and how alerts get a severity.

Three Sonnet finder agents each reviewed the code from one angle: A, how releases are interpreted; B, how the news is read; and C, impact and severity scoring. A separate Sonnet refuter tried to disprove every finding rated HIGH or CRITICAL, using the code and the live databases read-only. Opus did this synthesis. Nothing was edited or committed. Where two findings overlapped they were merged, and the verifier's severity was applied. I made one spot-check to settle a conflict between findings (see A1).

**Not covered:** data ingestion and feed accuracy, actuals sourcing, the scheduler and deployment, the alert transport, the UI apart from where it displays these numbers, security and performance. No claim in this report should be read as a clean bill for those areas.

---

## 2. Executive assessment

The good news first. [Certain] The plumbing is honest. The Stats scoring is point-in-time with no lookahead. Sign conventions for US releases are economically correct. Missing data turns into "not scoreable" instead of a fabricated 0. The evidence table records why every article was kept or dropped. Small samples are flagged on the Stats tab.

The problems are in what the numbers *mean*. [Certain] The "News" lean is not a reading of the news. It is the whole accumulator blend, which includes Kalshi, the print call, the trend streak and precursors, so it partly double-counts Tier 1 (A4). [Certain] Article sentiment is FinBERT good-news/bad-news tone used directly as USD direction. As a result, hawkish Fed headlines score as USD-bearish, and "gold up" or "pound up" headlines score as USD-bullish (B1). [Certain] Outside the FOMC and CPI families, any article that contains a keyword counts. That includes Australian bank layoffs voting on US jobless claims, and "optimism" matching "ISM" (B3, B4). [Likely] One article, or no articles at all, can produce a graded News call (A3). [Certain] The system has two incompatible definitions of "in line" (A1). [Likely] Displayed probabilities and severities are uncalibrated, and on the small sample available the high-probability calls did worse than the near-50% ones (C6).

**Can these outputs be trusted for trading decisions yet? No.** Taking the layers in order:

| Layer | Verdict |
|---|---|
| Data accuracy | Mostly sound within this audit's scope. Units, signs and point-in-time joins check out; ingestion itself was not audited. |
| Analytical correctness | Partly broken. The News lean is mislabelled and mis-signed, relevance filtering is weak outside FOMC/CPI, and the surprise definition is inconsistent. |
| Market relevance | Unproven. Severity and shock leans move no more often than chance on the current sample, and US30 growth leans are at about 50%. |
| Predictive validity | Not established. n is 9 to 20 per method, there is no calibration, and the early signs are negative (News 2 of 9; high-p calls 2 of 11). |
| Trading utility | None yet. Use the tool as context and an alerting feed, not as a direction source. |

---

## 3. Fundamental-interpretation findings

| ID | Severity | Status | Bug or methodology | Title | Evidence |
|---|---|---|---|---|---|
| B1 | HIGH | Confirmed defect | Methodology | FinBERT tone is used as USD direction, so hawkish and "other asset up" headlines get the wrong sign | `scoring/finbert_sentiment.py:108-116`; `scoring/probability_engine.py:237-239, 253-255`; `config/settings.py:183, 205-211` |
| A3 | HIGH | Likely defect | Methodology | News lean strength is the probability alone and ignores article count and confidence; 0-1 articles can produce a call | `webapp/stats_methods.py:22-30, 80`; `webapp/stats_service.py:124-135, 414`; `config/settings.py:994-997` |
| A4 (+B2) | MEDIUM | Confirmed (owner-ruled design; labelling and double-count issue) | Methodology | "News" is the full accumulator blend (Kalshi, print call, trend, precursors), not articles, so it double-counts Tier 1 | `scoring/backtest_accumulator.py:566-628`; `scoring/probability_engine.py:1155-1183`; `webapp/stats_methods.py:63-83` |
| A1 (+C5) | MEDIUM | Confirmed inconsistency (design-level) | Bug | Two incompatible "in line" definitions: 5% of forecast (history/trend) vs one rounding step (Stats) | `data_layer/calendar_feed.py:253-258`; `config/settings.py:1139`; `webapp/stats_rules.py:36-40`; `webapp/stats_service.py:227, 460-464` |
| A2 | MEDIUM | Real but owner-ruled and documented | Methodology | Combined 70/30 is effectively Tier 1 x 0.7: the News term is about 0, and sub-threshold leans still enter | `webapp/stats_methods.py:33-41, 54-60`; `webapp/stats_service.py:386-400` |
| A5 | MEDIUM | Design concern | Methodology | The in-line band is set by publication precision (1K for NFP and claims), not by surprise volatility | `webapp/stats_rules.py:30-40`; `webapp/tier1_market.py:133`; `webapp/reaction_service.py:119-123` |
| A6 | MEDIUM | Requires testing | Methodology | Tier 1 formula is nearly a constant "in line" call (14 of 18); 11/17 vs a trivial 9/17 | `webapp/tier1_formula.py:38-44`; `webapp/stats_methods.py:22-30, 102-103` |
| A7 | MEDIUM | Requires testing | Methodology | Static sign map with no policy-regime logic; US30 uses the inverse-USD sign for growth data (about 48% hit) | `config/settings.py:526-558`; `webapp/symbols.py:36-37`; `scoring/probability_engine.py:739-775` |
| B5 | MEDIUM | Confirmed defect | Methodology | Low-confidence FinBERT reads (0.52) score almost like clear ones; a neutral win is a hard cliff to 0 | `scoring/finbert_sentiment.py:108-116`; `scoring/probability_engine.py:244-251` |
| B8 | MEDIUM | Likely defect | Bug | Kalshi magnitude is the YES price: a 90%-sure "lower" weighs -0.10, a 55/45 "lower" weighs -0.45 | `scoring/probability_engine.py:625`; `data_layer/kalshi_feed.py:198-208` |
| B9 | MEDIUM | Design concern | Methodology | Generic USD tone is mapped to a specific print's surprise side | `webapp/stats_methods.py:76-82`; `config/settings.py:552` |
| A8 | LOW | Confirmed defect | Bug | Hand-logged Tier 1 calls for unmapped titles (Core Retail Sales, GDP, FOMC) can never be scored | `data_layer/tier1_events.py:27-46`; `webapp/stats_service.py:356-360` |
| A9 | LOW | Design concern | Methodology | Revisions to the prior print are ignored; FedWatch judgment calls describe the level, not the surprise | `webapp/stats_rules.py`; `data_layer/calendar_feed.py` (usd_surprise_score) |
| B10 | LOW | Potential risk | Methodology | Vendor native sentiment overrides FinBERT and is not USD-specific (may be inactive) | `scoring/probability_engine.py:233-235`; `data_layer/news_feed.py:130, 180` |

### B1: FinBERT tone used as USD direction (HIGH)

- **Current approach.** FinBERT returns positive, negative or neutral with a confidence. Positive becomes +confidence and negative becomes -confidence, and that value is used directly as `usd_sentiment`. FinBERT is on by default. The lexicon, which does understand hawkish and dovish wording, runs only if FinBERT is unavailable.
- **Assumption.** Good-sounding news is USD-bullish and bad-sounding news is USD-bearish, whatever the article is about.
- **Why unreliable.** FinBERT measures tone, not policy stance or asset direction. [Certain] "Fed rate hikes are coming, but not this week" scored -0.52, a hawkish headline counted as USD-bearish, at 44.9% weight in the FOMC bundle. [Likely] "Gold edges up as rate hike bets ease", "Pound edges up as dollar softens" and "China PPI beats" all scored about +0.94 as US strength. The finder's estimate that about half of the FOMC-bundle signs are wrong is a manual judgement, not a measurement.
- **Consequence.** For FOMC, CPI and rates events the News lean can point the wrong way with high apparent magnitude. The settings comment already calls the mapping a "real simplification" to revisit if accuracy is weak, and accuracy is weak (2 of 9).
- **Correction.** Score each article against an event-specific hypothesis ("does this imply a hotter print or a more hawkish Fed?") with a stance model or LLM. At minimum, exclude headlines that lead with a non-USD asset or a foreign currency on every path, not only the dollar path, and stop using FinBERT tone for the FOMC and CPI families.
- **Validation needed.** Hand-label 100-200 stored contributions for true USD direction and report FinBERT sign agreement per family.

### A3: News lean ignores evidence weight (HIGH)

- **Current approach.** strength = |2p - 1| of the XAUUSD accumulator probability, and the result is a call when it is at least 0.2. `article_count` is fetched but only displayed.
- **Assumption.** That number measures how strongly the news points to a hotter or cooler print.
- **Why unreliable.** [Certain] The single-signal thin-sample cap is 0.60, and 2 x 0.6 - 1 = 0.2, exactly the call threshold. Any one signal therefore produces a graded call by construction. [Certain] Core PCE on 2026-10-26 and 10-27 had p = 0.6 with **zero** articles. PPI and Core PPI on 2026-10-15 got p = 0.7 from one article about the Philippine central bank. Core PCE on 2026-10-29 got p = 0.7 from one article.
- **Consequence.** A single off-topic headline carries the same standing as an 88-article read. [Likely] Five of the 9 scored News calls rest on 2 articles or fewer. The 2 of 9 result is too small to blame on this alone.
- **Correction.** Keep `NEWS_CALL_MIN_LEAN = 0.2` (pre-registered). Add a separate, pre-registered evidence floor before a lean can become a call: a minimum number of signal-bearing articles, or the lean multiplied by the stored confidence. Show n beside every News call.
- **Validation needed.** After 8-10 weeks, compare News-call accuracy for 2 or fewer articles against 10 or more, on a split fixed in advance.

### A1 (+C5): two "in line" definitions (MEDIUM, merged)

I spot-checked this because the two findings disagreed. [Certain] The Stats tab judges the actual outcome with `stats_rules.side()` and one rounding step (`webapp/stats_service.py:227, 460-464`). It does **not** read the stored 5% label, so C5's claim that the 5% band is "the Stats truth" is wrong. The 5% label in `event_history.surprise_direction` drives three things: History-tab Confirmed/Missed grading, the "in line" shrug exemption, and the trend streak that feeds the accumulator. That label is wrong for level-type series. [Certain] 27 of 57 rows labelled in_line are not in line under the Stats rule, for example Unemployment Rate 4.1% vs 4.2%, CPI y/y 3.6% vs 3.7%, ISM 54.0 vs 55.6, and Claims 200K vs 194K. The fix is one classifier used everywhere, followed by a re-derivation of the 57 rows and the trend priors. Choosing the band itself (rounding step or k x sigma) needs an owner ruling and calibration (see A5).

---

## 4. Impact and relevance scoring findings

| ID | Severity | Status | Bug or methodology | Title | Evidence |
|---|---|---|---|---|---|
| B3 | HIGH | Confirmed defect | Bug | Subject filters cover only FOMC and CPI; other families accept any keyword hit, including foreign and corporate stories | `data_layer/subject_rules.py:52, 235-257`; `data_layer/event_context.py:81-83`; `config/settings.py:780-783` |
| B4 | MEDIUM | Confirmed defect | Bug | Keywords are raw substrings: "ism" matches "optimism", "ppi" matches "dropping" | `data_layer/event_context.py:81-83`; `config/settings.py` ~715-775 |
| B6 | MEDIUM | Confirmed defect | Bug | Time decay only reorders articles; renormalising by total weight keeps stale evidence at full strength | `scoring/probability_engine.py:257-259, 648-653, 1197, 1210` |
| B7 | MEDIUM | Design concern | Methodology | Same-story protection is thin for macro coverage (no gazetteer entities; 90-minute and 0.3 redundancy rule) | `scoring/probability_engine.py:303-330, 360-394`; `data_layer/entities.py:15-19, 33-98` |
| C1 | MEDIUM | Confirmed defect | Bug | The hard-rule tier substring-matches phrases, so denials, price reports and metaphors become High alerts with a firm lean | `alerting/triage.py:92-95`; `alerting/poll_once.py:199-203`; `alerting/us_link.py:55-79, 162-170`; `alerting/direction.py:93-96` |
| C2 | MEDIUM | Requires testing | Methodology | Severity is one 3B-model label, 51% of rows are a fallback "Medium", and High is not above chance | `alerting/llm_classify.py:93-143, 343-350`; `alerting/poll_once.py:72-81` |
| C3 | MEDIUM | Design concern | Methodology | One static lean per (category, polarity) cell, so price reports and deliberations get firm buy/sell leans | `alerting/transmission.py:195-267`; `alerting/direction.py:93-102` |
| C4 | MEDIUM | Design concern | Methodology | Shock-lean hit rate has no chance benchmark, no minimum n and no interval, and double-counts anchors | `alerting/lean_grading.py:128-140, 179-180, 224-239`; `webapp/static/js/shock-alerts/grading.js:34-49` |
| C6 | MEDIUM | Requires testing | Methodology | Probability and confidence are uncalibrated tanh/product constructs; high-p calls did worse in the sample | `scoring/probability_engine.py:934-942, ~1204-1245`; `config/settings.py:1028-1069` |
| C7 | MEDIUM | Design concern | Methodology | A missing us_link is treated as linked; the cap is a cliff; bare "supply/gas/port" terms validate global_supply | `alerting/us_link.py:17-20, 162-170`; `alerting/direction.py:93`; `config/settings.py:79-85` |
| C8 | LOW | Potential risk | Methodology | Reaction baselines are UTC-hour absolute quantiles that ignore US DST and are thin in some hours | `scripts/compute_release_reactions.py:89-108`; `alerting/lean_grading.py:123` |
| C9 | INFO | Design concern | Methodology | Event-symbol relevance and magnitude tiers rest on 5-8 observations and are not wired to anything yet | `data_layer/event_symbol_magnitude.py:36-43`; `data_layer/event_symbol_relevance.py` |

### B3: no subject check outside FOMC and CPI (HIGH)

- **Current approach.** `SUBJECT_RULE_FAMILIES = ('fomc','cpi')`. Every other family gets only the foreign-central-bank name test. Keywords are matched anywhere in title plus summary. Core PCE and UoM use inline lists, so they fall into family "other".
- **Assumption.** A keyword hit plus "no foreign central bank named" means the article is about the US release.
- **Why unreliable.** Job keyword lists include generic words such as "hiring", "layoffs" and "job cuts", and nothing checks that the company or country is American. [Certain] An Unemployment Claims prediction counted "Westpac's latest job cuts not AI-driven", about an Australian bank, as its largest contributor. [Likely] Historical rows show "Venezuela oilfield hiring picks up" as 100% of a Claims prediction, and Chevron, Verizon and ConocoPhillips stories voting on PCE and Claims. The verifier could not re-confirm the ConocoPhillips and Verizon rows, so "Core PCE's current call rests on a Canadian oil layoff" stays [Likely], not [Certain].
- **Consequence.** For most tracked titles the News lean can be set by one or two unrelated corporate or foreign headlines. Combined with A3, that becomes a graded call.
- **Correction.** Add a US-subject title rule for every family (US, BLS, claims or PCE wording). Exclude non-US company layoffs and earnings. Require the keyword hit in the title, or a US marker, rather than anywhere in the summary. Fix B4 (word boundaries) in the same change. Report exclusion rates per family from the evidence table.
- **Validation needed.** Sample 50 included articles per family, label each as on-topic or not, and report precision per family before and after the change.

No HIGH findings remain in the alert-scoring area (C) after verification. All five were downgraded to MEDIUM because they affect alerts and displays, not automated trades, and because the samples are small. [Likely] C1 is still the one most worth fixing quickly: the least-checked path (rule tier) produces the strongest output (High plus a firm lean), and 2 of the 3 live rule-tier alerts were commentary rather than new shocks.

---

## 5. Known issues touched

No finder flagged anything as known. The verifiers and the evidence show these overlap with items already recorded:

- **A2:** `docs/feature-inventory-2026-09-11.md` already records that the CPI m/m news scale is 0.0, that News 30% "only shrinks Tier 1 by 0.7", and that the rule is unchanged pending an owner ruling.
- **A4/B2:** the News lean as XAUUSD accumulator output is plan rule R3 (`docs/superpowers/plans/2026-10-15-stats-tab.md:61`), which is owner-ruled. This audit critiques the labelling only.
- **A5, C4, C8:** these relate to the parked k x sigma / multi-horizon validation upgrade for the reaction threshold. That upgrade does not cover the Stats side rule (A5).
- **B1:** `config/settings.py:205-211` already calls the FinBERT-to-USD mapping a simplification to revisit.
- **B1 (filter scope):** roadmap item B6/A2 scoped the title filters to the FOMC and CPI families. The dollar-path-only scope of `_OTHER_ASSET_LEAD_PATTERN` is commented as deliberate.
- **C3:** 2/3 of shock cells have no lean, as recorded in known item B10.
- **C6:** the outcome label uses the fixed 0.15% window threshold, a known limitation.
- **C7:** the B2 us_link cap is owner-ruled, and the 3B model's weaker country and us_link fields are known.
- **C1/C5:** `docs/b9-deploy.md` notes that in_line verdicts clear for Claims, Unemployment Rate and CPI y/y, treated there as a display matter.

---

## 6. Strengths worth keeping

[Certain] The Stats path is genuinely point-in-time. Every join is gated on `scored_at`/`logged_at <= release`, and backtest mode enforces the pre-event cutoff (`event_context.py:194-195`). There is no lookahead. Forecast and actual units match (0 of 165 mismatches), and `parse_number` keeps K, M and B as published.

`EVENT_SURPRISE_DIRECTION` signs are economically correct per title, and Tier 1 and News share one sign convention. Missing data is handled honestly throughout: `usd_surprise_score` and `classify_surprise` return None, never 0; unmapped titles get no call; and the Kalshi rule refuses a call on a units mismatch or when there is no 50% crossing.

The B6 evidence table (`prediction_article_contributions`), which records every included and excluded article with its reason, is what made this audit possible. Keep it and extend it, for example with all three FinBERT class probabilities (B5). The B8 sigma surprise in `surprise_scale.py` is prior-only, floored and gated. It is the right building block for a unified surprise definition (A1, A5).

The Stats tab already does honest-sample handling: percentages hidden under 20, Wilson intervals, an always-in-line baseline, and abstentions left ungraded. The Shock tab should copy it (C4). Shock leans say "mixed" where the evidence is contested and carry provenance tags. `lean_grading` uses exact-minute bars, append-only grades and stored baselines.

---

## 7. Prioritised fixes

### Phase 1: critical corrections (cheap, deterministic, no owner re-ruling needed)

1. **B3 + B4:** add a US-subject title rule for every family and word-boundary keyword matching. Unit-test with "optimism", "dropping" and the Westpac headline.
2. **A3:** add a pre-registered evidence floor (minimum number of signal-bearing articles) before a News lean becomes a call, and show n beside each call. Leave 0.2 untouched.
3. **B1 (interim):** apply the non-USD-asset and foreign-currency lead exclusion on every path, not only the dollar path, and flag FOMC- and CPI-family News leans as low-trust until the stance model in Phase 3 exists. Owner sign-off is needed because this widens the B6/A2 scope.
4. **C1:** add negation, denial and price-report guards to the rule tier. Rule hits with an unknown us_link go through the classifier, or are capped at Medium with a "mixed" lean.
5. **A1:** use one in-line classifier for `event_history.surprise_direction` and the Stats rule, then re-derive the 57 in_line rows and the trend priors. The band choice needs an owner ruling.
6. **B8:** use Kalshi magnitude 2 x P(side) - 1 on both sides (unit test).
7. **C4 + C2 (display only):** show Wilson intervals, hide percentages under n = 20, dedupe anchors and show the 25% chance rate on the Shock tab. Exclude `llm_failed_fallback` rows from any severity rollup.
8. **A8:** mark unmapped Tier 1 titles "not scoreable" (or add reviewed sign entries).

### Phase 3: analytical improvements (this audit's scope)

- **B1:** replace tone-as-direction with an event-specific stance score (does this imply a hotter print or a more hawkish Fed?).
- **A4/B2:** store an article-only component next to the blended probability, and compute the Stats News lean from it. Keep the blend for the live dashboard.
- **B5:** use P(positive) - P(negative) as the score, and down-weight or drop reads below the confidence threshold.
- **B6:** shrink the aggregate by total_weight / (total_weight + K) and add freshness to confidence and to the call gate.
- **B7:** add a same-story key for macro headlines (event + direction + 24 h), or cap weight per source per day.
- **B9:** restrict the News lean to release-specific articles (previews, expectations) and relabel it "news-implied surprise side".
- **A7:** use per-instrument, per-class sign tables for US30 (inflation, growth, labour) and a pre-registered policy-regime flag.
- **A5:** add a sigma-scaled dead zone for market-implied and Tier 1 side calls. Pre-register the multiplier.
- **C6:** show bucket labels or the empirical hit rate per bucket instead of raw p and confidence until a monotone calibration is fitted.
- **C3 + C7:** gate leans on a concrete-event flag, treat an unknown us_link as its own cautious state, and tighten the global_supply term list.
- **A6 + A2:** report directional accuracy (excluding in-line actuals) beside every method, and state in the 2027-01-15 review that Combined cannot differ from Tier 1 while the news scale is about 0.
- **A9, C8, C9, B10:** store revisions for NFP rows, key baselines by New York hour with a minimum window count, base the magnitude tiers on measured data before wiring them in, and confirm whether the vendor sentiment sources are active.

### Needs empirical validation before changing

| Finding | What to measure |
|---|---|
| B1 | FinBERT sign agreement with 100-200 hand-labelled contributions, per event family |
| B3 / B4 | On-topic precision on 50 included articles per family, before and after the filter |
| A3 | News-call accuracy for 2 or fewer vs 10 or more articles, on a split fixed in advance, after 8-10 weeks |
| A4 / B2 | How often the article-only direction differs from the blended direction, using stored `top_contributions` |
| A1 / A5 | In-line share per title under the candidate bands (rounding step vs k x sigma), and the effect on Tier 1 and Combined accuracy |
| A2 | Replay of the 18 Combined rows with a lean-gated blend and a sigma-scaled News term; count side changes |
| A6 | Tier 1 directional hit rate vs the in-line base rate as n grows (11/17 vs 9/17 is noise today) |
| A7 | Per-class hit rates with Wilson intervals, split by rate-hike vs rate-cut regime, for XAUUSD and US30 |
| C1 / C7 | Rule-tier and global_supply precision, replayed on the 8,334-row near-miss log |
| C2 / C4 | Share of alerts per severity whose 5-minute move beats baseline, against the 25% chance rate, after 8-10 weeks |
| C6 | Reliability table of predicted p against outcome over the 942 live prediction rows once enough outcomes exist. Verifier figures: high-p calls 2 of 11 correct vs 50 of 65 for near-50% calls |
| B5, B6, B7, B9 | Sign agreement for low- vs high-confidence reads; accuracy by weight and age bucket; paraphrase repeats in about 20 bundles; release-specific vs market-wrap hit rate |

---

## 8. Appendix: refuted on verification

None. All 11 findings sent to a refuter (A1, A2, A3, B1, B2, B3, C1, C2, C4, C5, C6) survived. Eight were downgraded from HIGH to MEDIUM: A1, A2, B2, C1, C2, C4, C5 and C6. Three corrections came out of verification and the spot-check:

- **C5:** its claim that the 5% band is the Stats grading truth is wrong. Stats uses `stats_rules.side()`. The finding survives only as merged into A1.
- **C6:** the counts were corrected to 2 of 11 non-neutral high-p calls and 50 of 65 near-50% calls.
- **C2:** the High-severity moved rate was corrected to 4 of 24 cells (about 17%).
