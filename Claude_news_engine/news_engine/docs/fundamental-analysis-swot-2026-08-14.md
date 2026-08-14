# News Engine — Fundamental Analyst SWOT & Prioritised Recommendations

**Prepared:** 2026-08-14
**Reviewer stance:** Professional forex fundamental analyst, assessing `news_engine`'s scoring *logic* — not its code quality — as a decision-support system for XAUUSD (and secondarily US30) directional bias ahead of major USD releases.
**Method:** Direct read of `scoring/probability_engine.py`, `webapp/scoring_service.py`, `scoring/backtest_accumulator.py`, `scoring/print_direction.py`, `scoring/outcome_classifier.py`, `scoring/sentiment.py`, `webapp/trend.py`, `data_layer/calendar_feed.py`, `data_layer/kalshi_feed.py`, `config/settings.py`, `BACKTEST_REPORT.md`, and the 2026-08-14 session handover. Every claim below is traceable to a specific file/constant, not inferred from documentation alone.

---

## 1. Executive Summary

The engine is a **multi-source triangulation model**, not a single-signal sentiment scraper: article text sentiment, structured precursor surprises (ADP→NFP, PPI→CPI), this-occurrence print-direction inference, historical beat/miss streaks, and Kalshi prediction-market pricing are all blended onto one USD-directional axis with independently tuned trust weights (0.3 → 0.95) and a shared weighted-average/agreement/coverage math core (`scoring/probability_engine.py:385-432`). That architecture is genuinely more sophisticated than what most retail-facing "news trading" tools do, and the code is unusually honest about its own limitations — nearly every simplification (US30's `risk_sentiment` mapping, precursor "already priced in" blindness, untuned sigmoid steepness) is flagged inline as a named, dated, open question rather than silently shipped as fact.

The core weakness is not architectural — it is **evidentiary**. The only accuracy figure that exists (`BACKTEST_REPORT.md`, 89% on 9 calls) was run against 30 *reconstructed/paraphrased* articles, not live-pulled ones, and its own single documented failure (NFP, June 2026) is a structural blind spot in the default-path lexicon scorer — it cannot distinguish "X is happening" from "X could happen if Y," and scored hedged/conditional language ("rate hike risk IF data surprises") as a flat declarative signal. That failure mode has never been retested against real news flow, and the contextual upgrades that would fix it (FinBERT, Claude) are built but **off by default** (`config/settings.py:36-37`).

A second, currently-open correctness bug (documented in the 2026-08-14 handover) has the dashboard's primary gauge — the essence-only `direction` field — stuck on `"pending"` for events that have already resolved, because the persisted `prediction_runs` row isn't recomputed when a fallback script updates `event_history` after the fact. This is a live, user-facing defect, not a design limitation, and it sits ahead of every enhancement below.

---

## 2. SWOT

### 2.1 Strengths

**S1 — Multi-source triangulation on one coherent axis.**
Article sentiment, precursor surprises, print-direction inference, trend streaks, and Kalshi market pricing all resolve to the same -1..+1 USD-directional axis and flow through identical weighted-average/agreement/coverage math (`ArticleContribution`, `PrecursorContribution`, `PrintCallContribution`, `TrendStreakContribution`, `KalshiMarketContribution` are deliberately duck-typed to share this pipeline, `scoring/probability_engine.py:63-136`). This is a real triangulation model, not five independent opinions bolted together with no common calibration.

**S2 — Trust hierarchy reflects genuine epistemic quality, not arbitrary tuning.**
Kalshi (0.95) > precursor structured print (0.90) > this-occurrence print inference (0.50) > historical trend streak (0.30) — real money priced directly on the exact outcome outranks a structured-but-different-event surprise, which outranks text inference about an unprinted number, which outranks a pattern over past events. That ordering is fundamentally sound fundamental-analysis practice: hard data > inferred data > historical prior.

**S3 — Confidence is explicitly decoupled from probability, and the decoupling is correctly motivated.**
`_agreement_and_coverage()` (`scoring/probability_engine.py:393-432`) was rewritten specifically because a single signal-bearing article among a dozen silent ones was producing 100% "confidence" — a textbook false-certainty bug. Confidence now requires both agreement (do the sources that spoke agree?) *and* coverage (did enough of the bundle actually speak?). This is a materially better design than most sentiment-scoring systems, which conflate the two.

**S4 — Contradiction detection surfaces regime change instead of averaging it away.**
`_detect_contradiction()` compares recent vs. older article windows and flags — rather than silently blends — a narrative flip (`scoring/probability_engine.py:462-501`). This is the correct fundamental-analyst instinct: a market narrative that has visibly shifted in the last 6 hours should never read the same as one that's been stable for two days, even if the time-weighted average happens to land in the same place.

**S5 — Kalshi integration is real, live-verified, and appropriately the highest-trust tier.**
Not a theoretical "prediction markets could help" note — the integration is live against Kalshi's real API, with three real bugs found and fixed through live verification (wrong endpoint, month-lag ticker convention, misclassified date-ticketed series). A liquidity floor (`MIN_KALSHI_OPEN_INTEREST = 10.0`) protects the highest-weight signal from being driven by a thin, easily-skewed price. This is the single most defensible signal source in the system, because it prices real capital directly against the exact event being scored.

**S6 — Honest, dated self-documentation of every simplification.**
The US30 `risk_sentiment` mapping, the precursor trust weight, the sigmoid `k`, `SURPRISE_SENSITIVITY` — every one of these carries an inline comment naming it as an unvalidated placeholder and specifying exactly what would justify revisiting it ("worth revisiting if US30 backtest accuracy comes out weak"). This materially lowers the risk of the system being trusted beyond what it has actually earned — a rare discipline.

**S7 — Fail-open, provenance-tracked design.**
Every external dependency (FF calendar, Alpha Vantage, Kalshi, dashboard-DB cross-reads) fails open with a logged reason rather than crashing the scoring cycle, and every value written to the database carries a `source` column (`'live'` / `'seeded'` / `'live_web_fallback'`) so a reader can always tell whether a number is real-time, backfilled, or manually researched. For a system whose entire value proposition is "trustworthy directional read," that audit trail is not a nicety — it's load-bearing.

### 2.2 Weaknesses

**W1 — The only documented accuracy figure was not earned against real data.**
`BACKTEST_REPORT.md` explicitly and repeatedly states its "89% accuracy" is against 30 hand-paraphrased articles with manually assigned timestamps, built in a sandbox with no live network access, and closes by warning "not evidence the model is '89% accurate.'" That warning is correct and should be treated as load-bearing: **no accuracy claim currently exists that was earned against genuine, noisy, real-timed news flow.**

**W2 — The lexicon's one documented failure is a structural blind spot, not a fluke.**
Case #2 in the backtest (June NFP) was scored BEARISH gold at 99% confidence and was wrong, because `scoring/sentiment.py`'s keyword matcher has no conditional/hedged-language handling — "rate hike risk IF data surprises to upside" matched "rate hike" and "hawkish" as flat declaratives. This is the *default* path (native sentiment is rare from RSS sources; FinBERT/LLM tiers are opt-in and off — `ENABLE_FINBERT_SENTIMENT`/`ENABLE_LLM_SENTIMENT` both default false). The exact failure mode that produced the one wrong call on record is still live in production today.

**W3 — Extreme probabilities are demonstrably an artifact of small sample size, not conviction.**
Multiple backtest cases hit 1%/88%/98% probability from 2-3 signal-bearing articles (`_score_to_probability`'s `k=2.5` is explicitly flagged as "needs tuning" and the report's own conclusion calls it "uncalibrated and overconfident for small sample sizes"). Confidence (agreement×coverage) discounts the *probability* pulled toward 50%, but nothing discounts the underlying sigmoid's willingness to output 99%+ certainty from a 2-article sample — these are two different failure modes and only one is mitigated.

**W4 — A live, user-facing correctness bug is currently open on the primary dashboard gauge.**
Per the 2026-08-14 handover: essence-only `direction` shows `"pending"` for CPI m/m / PPI m/m / Core CPI m/m even though real actuals exist, because `prediction_runs` is written once per scheduler cycle against calendar data that had `actual=None` at the time, and nothing recomputes it once `event_history` is later backfilled. This is not a modeling limitation — it is the system displaying a wrong/stale primary signal to a user who may act on it.

**W5 — Single, fragile, informally-scraped calendar dependency.**
The entire event-timing spine (`data_layer/calendar_feed.py`) rests on `nfs.faireconomy.media`'s unofficial JSON feed, whose own publisher guidance is "fetch once a week, don't poll" — a guidance this project already breached three times this session even with a defensive 600-second cooldown now in place. There is no confirmed free fallback (Trading Economics, FMP, and NewsAPI's production tier were all live-verified as paid this session). A single feed change, block, or extended outage stalls the entire pipeline with no graceful degradation path beyond "keep stale data."

**W6 — Alpha Vantage's 25/day quota is thin relative to what a genuinely busy macro week requires.**
`DAILY_CHECK_BUDGET_THRESHOLD = 20` backs the accumulator off to a 3-hour floor once 20 of the daily 25 credits are spent — reasonable engineering, but it means a week stacking NFP + CPI + FOMC (a realistic monthly occurrence) can silently degrade the accumulator's freshest, most valuable signal (the final-hour tier is exempt, but the leadup isn't) exactly when it matters most.

**W7 — Trust weights and sensitivity constants are placeholders, not calibrated parameters.**
`SOURCE_TRUST_WEIGHTS`, `PRECURSOR_TRUST_WEIGHT`, `PRINT_CALL_TRUST_WEIGHT`, `TREND_STREAK_TRUST_WEIGHT`, `RISK_SENTIMENT_DAMPENING`, `SURPRISE_SENSITIVITY`, and the sigmoid `k` are all explicitly commented as "needs tuning against backtest results" / "unvalidated simplification." None have been fit against outcome data — they are analyst-intuition starting points, which is a defensible v1 posture, but currently indistinguishable in the code from calibrated values to anyone not reading the comments.

**W8 — No macro-backdrop cross-check independent of headline text.**
Every contribution in the system ultimately derives from either article language or a single event's forecast-vs-actual — there is no DXY level, real-yield differential, Fed funds futures pricing, or cross-asset risk gauge acting as an independent check on the headline-driven read. A fundamental analyst would never take a CPI-day gold call purely from press framing without also checking where 2yr yields and the dollar index are already positioning — this system currently has no equivalent.

**W9 — Precursor and trend-streak contributions can't distinguish "already priced in" from "genuine surprise."**
`PRECURSOR_TRUST_WEIGHT`'s own comment admits this: "a beat that's already fully priced in shouldn't move markets the same as a genuine surprise, which this can't tell apart." A market that has spent two days pricing in a strong ADP print will not react to CPI beating in the same direction with the same magnitude this system assumes.

### 2.3 Opportunities

**O1 — The fix for W2 already exists in the codebase, just switched off.**
`scoring/finbert_sentiment.py` and `scoring/llm_sentiment.py` were built precisely to catch hedged/conditional language the lexicon can't — this is not a research gap, it's a config flag (`ENABLE_FINBERT_SENTIMENT`, `ENABLE_LLM_SENTIMENT`) and a validation exercise away from closing the single worst documented failure mode in the system.

**O2 — Kalshi's real, live-confirmed coverage is larger than what's wired in.**
`config/settings.py`'s comments confirm real Kalshi markets exist for Unemployment Claims, Advance GDP q/q, Prelim UoM Consumer Sentiment, Challenger Job Cuts, PPI m/m, Retail Sales m/m, and FOMC — 7 more events on top of the 9 already resolvable — blocked only by date-ticketed (vs. month-ticketed) resolution logic not yet built. FOMC in particular is arguably the single highest-impact USD event this system tracks and currently has zero market-based confirmation.

**O3 — A growing, real confirmed-outcome dataset (`confirm_backtest_outcomes.py` / `outcome_classifier.py`) is the direct path to replacing every placeholder constant in W7 with a fitted one.** The infrastructure to do this already exists; it just needs enough accumulated real occurrences to regress against.

**O4 — Confidence and probability are computed but not yet turned into a sizing decision.** A probability+confidence pair is a directional read, not a trade — adding an EV/Kelly-fraction layer converts this from a dashboard number into an actionable, risk-scaled signal.

**O5 — The two-pipeline separation (essence-only vs. article-based) is architecturally clean enough to extend safely.** A macro-backdrop cross-check (W8) or an alternate calendar source (W5) can be added as new, isolated inputs without destabilizing either existing pipeline, given the established read-only/fail-open cross-pipeline pattern already in use.

### 2.4 Threats

**T1 — Regulatory/ToS exposure on the calendar feed.** `nfs.faireconomy.media` is an unofficial, reverse-engineered feed with explicit "fetch once a week" guidance this project is already exceeding (even with the new cooldown). It can be rate-limited, altered, or blocked without notice or recourse, and there is currently no verified-free fallback.

**T2 — Exogenous shocks can dominate price action and the system has no explicit flag for it.** The backtest's own CPI-day case (#4) notes "Gold fell on Iran strikes ahead of CPI print" as a confounding, non-calendar-driven move the engine had no way to distinguish from calendar-driven sentiment. On days with competing macro/geopolitical stories, a calendar-clean directional call can be actively wrong for reasons the system has no visibility into.

**T3 — Self-reinforcing signal risk in the trend-streak contribution.** `TrendSignal` is derived from this system's own historical prediction/outcome record (`webapp/store.py`'s `event_history`, read back by `_read_trend_signal()`). If any structural bias exists elsewhere in the pipeline (a mistuned lexicon term, a wrong trust weight), a persistent streak in the *outcome* data could reflect that systematic bias rather than genuine market behavior, and the trend-streak contribution would then feed the bias back into future live predictions — a genuine echo-chamber risk once enough occurrences accumulate.

**T4 — Data-budget exhaustion is a live risk during exactly the periods that matter most (T6/W6).** Multiple high-impact events clustering in the same week is a real, common calendar pattern (e.g. FOMC week often overlaps CPI/PPI), and Alpha Vantage's 25/day quota was explicitly engineered around, not eliminated.

**T5 — Live accuracy is currently unproven, and the one number that exists (89%) is at real risk of being over-relied upon precisely because it's the only number that exists.** The report itself flags this, but the risk is behavioral, not technical: a user glancing at "89% backtested accuracy" without reading the caveats is the most likely real-world failure mode of this whole assessment.

---

## 3. Recommendations — Ranked

Ranking criteria, in order: **(1) addresses a confirmed critical flaw, (2) highest expected impact on real directional accuracy or user trust, (3) best fit for the existing architecture (lowest structural risk to implement).** Each item states the flaw/opportunity it targets and the concrete implementation anchor.

### Priority 0 — Critical flaws (fix before any live trading reliance)

**R1. Close the "pending direction" stale-gauge bug (targets W4).**
The dashboard's primary card-level directional gauge is currently wrong for resolved events. This is the single most urgent item — a user reading `"pending"` when a real, confirmed actual exists is a direct, observable misinformation risk, not a modeling nuance. The read-time-merge approach already agreed with the user (`webapp/app.py`'s `/api/predictions`, recomputing on the fly when `event_history` has resolved but `prediction_runs` hasn't) should be implemented and the exact mechanics re-confirmed per the handover's own note before shipping, since it is a genuine architectural precedent change (routes computing scores on the fly).

**R2. Turn on and validate the contextual sentiment tier as the real default, not an opt-in flag (targets W2, the one confirmed wrong call).**
`ENABLE_FINBERT_SENTIMENT` / `ENABLE_LLM_SENTIMENT` exist specifically to solve the hedged-language failure that produced the system's only documented wrong call. Leaving them off by default means the system is knowingly running with its one proven blind spot active. This requires: (a) re-running the backtest's failure case (and a handful of similarly hedged real headlines) through FinBERT/Claude to confirm the fix actually holds, then (b) making the contextual tier the default path with the lexicon strictly as final fallback, matching the tiering the code already documents as intended.

**R3. Add a sample-size-aware ceiling on probability, independent of the agreement×coverage confidence discount (targets W3).**
`agreement × coverage` correctly discounts *confidence* when sources disagree or are silent, but does nothing to stop the sigmoid itself outputting 99%+ *probability* from 2-3 articles. A minimum-article-count-gated probability cap (e.g. no probability beyond ~75-80% until `article_count` + weighted precursor/Kalshi contributions clear a real threshold) directly targets the exact overconfidence pattern the backtest report itself calls out as its own biggest concern.

### Priority 1 — Highest impact

**R4. Extend Kalshi to date-ticketed series, prioritising FOMC (targets O2, partially T3 by adding an independent check).**
FOMC is the highest-impact USD event this system tracks and currently has zero market-based confirmation — every other major indicator has a real-money cross-check available except the one that moves markets hardest. This is bounded, well-scoped engineering work (date-based ticker resolution, already anticipated in the code's structure) against a highest-trust-weight (0.95) payoff.

**R5. Add an independent macro-backdrop veto/confirm signal — DXY level/trend and a short-tenor real-yield or Fed-funds-futures read (targets W8, T2).**
This is the most consequential *design* gap, not an implementation detail: every current contribution derives from headline text or a single event's own surprise. A fundamental analyst would never trade a calendar print in isolation from where the dollar and rates markets are already positioned. Concretely: pull a DXY or 2yr yield delta over the pre-event window and use it as either (a) a confidence multiplier (agree with the calendar-driven read → higher confidence; strongly diverge → flag, don't just override) or (b) a hard veto threshold on extreme, thin-sample probability calls (also helps R3). This also gives the system a partial answer to T2 (exogenous-shock days) that it currently has none of.

**R6. Establish a genuinely free (or reliably-licensed) secondary calendar source, or formally accept and document the single-source risk with an explicit staleness/outage policy (targets W5, T1).**
The session's own research already ruled out Trading Economics, FMP, and NewsAPI's production tier. If no free alternative survives live verification, the honest recommendation is not "keep searching" (already explicitly decided against by the user this session) but to make the single-source dependency an explicit, monitored risk with a defined "how stale is too stale to score" policy, rather than an implicit one.

### Priority 2 — Good fit, real value, lower urgency

**R7. Build an EV/Kelly-fraction position-sizing layer on top of probability + confidence (targets O4).**
Converts the engine from "directional read" to "sized signal" — the natural next step once R1-R3 make the underlying probability/confidence numbers trustworthy. Should explicitly gate on confidence, not just probability, given S3's design intent.

**R8. Recalibrate trust weights and sensitivity constants against `confirm_backtest_outcomes.py`'s accumulating real dataset once sample size supports it (targets W7).**
Every constant in W7 already has an inline "revisit once real backtest data exists" comment — this is executing on the system's own stated intent, not a new idea. Should wait for a large-enough real (not seeded/reconstructed) sample to avoid overfitting three months of quiet data.

**R9. Add an explicit "competing story" flag when non-calendar geopolitical/market-shock language is detected in the same article window (targets T2).**
A lightweight addition (a small negative-signal or "shock" lexicon distinct from the USD-directional one) that would let the system self-report "this call may be contaminated by a non-calendar event" rather than silently absorbing it into the sentiment average, as happened in the backtest's Iran-strikes case.

**R10. Add a periodic self-check on the trend-streak contribution to detect echo-chamber drift (targets T3).**
Since `TrendSignal` is derived from the system's own prediction/outcome history, periodically compare trend-streak-driven calls' real accuracy against non-trend-driven calls' accuracy. If the trend-fed subset underperforms, that's a direct signal the streak is reflecting a systematic bias elsewhere in the pipeline rather than genuine market repetition — worth a standing check once R8's dataset is large enough to support it.

---

## 4. Bottom Line

This is a well-architected, honestly-documented triangulation model with one live correctness bug (R1), one proven and still-active blind spot (R2), and one demonstrated overconfidence pattern (R3) standing between it and being trustworthy enough to size real risk against. None of the three are architectural rewrites — all are scoped, bounded fixes against code that already exists or is one flag away from existing. The highest-value work *after* those three is closing the system's only real design gap: it has no signal that isn't ultimately derived from calendar prints and article text, with no independent cross-check against where the dollar and rates markets are already positioned (R5) — that is the difference between a headline-reaction model and a genuine fundamental-analysis system.
