# News Engine — Industry-Standard Benchmark and US-Scope Deployment Triage

**Prepared:** 2026-10-16 (SAST)
**Companion to:** `docs/fundamental-analysis-audit-2026-10-16.md`. That audit inventoried the engine's techniques and its non-USD blind spots. This doc answers three follow-up questions:

1. Did that audit compare the engine to the **industry standard** for interpreting news and measuring its market impact?
2. If the scope is "news that impacts the US", is it worth deploying everything the audit recommended?
3. What else should be considered?

**Method:** the established literature and practitioner frameworks on announcement effects, central-bank communication, financial text analysis and gold price drivers (sources at the end), mapped stage by stage onto the engine's code. Two ACE files were also read for integration: `ACE/ACE_v3.14.3/Core/ASE_NewsEngine.mqh` and `ACE_v3.14.4.mq5`.

---

## 0. Direct answers

**1. Was the industry comparison in the first audit? Only partially.** `[Certain]` The audit contained:

- the technique inventory (§1)
- a one-paragraph scorecard against five FX-desk signal families
- two point comparisons: standardized surprises (§2.2) and the central-bank stance model (§6)
- a vendor-tool table (§6)

It did **not** benchmark the engine against established practice stage by stage, from how expectations are formed through to how impact is measured and acted on. §2 below adds that.

**2. Under a US-impact scope, should all of it be deployed? No.** Six of the ten recommendations survive, two survive trimmed, and two drop or defer (§3). The two that drop are the two High-effort items: the JPY pilot and the multi-currency transmission graph.

**3. The biggest new consideration isn't fundamental analysis at all.** `[Certain]` The engine's output never reaches ACE. And `[Likely]` ACE's own news blackout stops protecting it after 48 hours of uptime (§4.1–4.2). Every improvement to the engine currently improves a dashboard you read, not the EA that trades.

---

## 1. Define the scope by instruments, not by country

"News that impacts the US" is the right instinct, but the boundary has to be drawn around what moves **USD, US rates, US risk appetite and gold's own drivers**. That boundary still lets some foreign news in:

- **The dollar index is mostly Europe.** `[Certain]` ICE DXY weights are EUR 57.6%, JPY 13.6%, GBP 11.9%, CAD 9.1%, SEK 4.2% and CHF 3.6%. An ECB decision moves the dollar by construction. That is exactly why audit defect §2.1, where foreign-CB news gets the wrong USD sign, matters even under a US-only scope.
- **Gold is not a US-only asset.** `[Certain]` The World Gold Council's Gold Return Attribution Model (GRAM) splits gold returns into four driver families: economic expansion, risk & uncertainty, opportunity cost (rates and FX) and momentum. Positioning and flows sit under momentum. In 2024 the WGC had to add a geopolitical-risk proxy and **Shanghai futures positioning** to explain gold's strength. This repo's own Layer2 notes say central-bank buying has been the marginal gold driver since 2024 (`docs/feature-inventory-2026-09-11.md`, PER-INSTRUMENT QUIRKS). A strictly US-news engine can't see the biggest gold driver of the last two years.
- **Some US news moves gold without going through the dollar.** `[Certain]` In August 2025 a CBP letter said 1 kg and 100-oz gold bars were subject to reciprocal tariffs. COMEX futures jumped to a premium of more than $100/oz over London, and the move unwound after the White House said gold wouldn't be tariffed. The engine's shock alerting routes `trade_policy` only to equity indices, so it would have shown nothing for XAUUSD.

**Working scope rule:** US-scheduled data and US policy, plus (a) foreign central-bank decisions as *DXY events*, (b) gold-specific global drivers (central-bank buying, ETF flows, China/India demand, COMEX positioning), and (c) geopolitical risk.

---

## 2. Industry-standard benchmark, stage by stage

The standard way to interpret a news event and its market impact is a pipeline of eight stages. Each is benchmarked below.

Ratings: ✅ at or above standard · ⚠️ partial · ❌ below standard or absent. Ratings are my judgment, `[Likely]` overall. The evidence column is `[Certain]` (read from code).

| Stage | Industry-standard practice | Engine today | Rating |
|---|---|---|---|
| **A. Expectations before the release** | Consensus median **plus dispersion** (survey σ); nowcasts; market-implied pricing (fed funds futures/OIS for policy, options implied move for magnitude, prediction markets); tracking known consensus biases | One Forex Factory forecast string with no dispersion or survey date (`EconomicEvent.forecast`). Nowcasts only via the manual Tier 1 task. Kalshi ✅. FedWatch only manual. No implied-move read. Lexicon "whisper" inference | ⚠️ |
| **B. Surprise measurement** | **Standardized surprise** `(actual − consensus)/σ` (Andersen, Bollerslev, Diebold & Vega 2003; Citi/Bloomberg surprise indices). Prior-period **revisions** count as part of the surprise. Sub-components weighted (core vs headline; AHE and UR alongside NFP). Policy events measured as a **market-based** surprise from futures in a tight window (Kuttner 2001), split into a **target** and a **path/guidance** factor (Gürkaynak, Sack & Swanson 2005) | Percent-of-forecast with `tanh` (audit §2.2: 9× distortion for identical information). Revisions ignored. Co-released titles reconciled by strict unanimity, not weighting. FOMC has no market-based surprise and no target/path split; Kalshi covers the rate decision only | ❌ |
| **C. Reaction function / importance weighting** | Event importance estimated from **historical high-frequency reactions**, re-estimated as regimes shift (whether the Fed is focused on inflation or labor). **Asymmetry**: bad news moves prices more than good (ABDV 2003). The Fed "information effect" (Nakamura & Steinsson 2018). Importance depends on timeliness and how well a release predicts later ones (Gilbert et al. 2017) | Static, hand-cited LOW/MED/HIGH magnitude grid. Static trust weights. Authored influence-link weights unused (audit T3). No asymmetry, no regime switching | ❌ |
| **D. Text and communication interpretation** | A **finance-specific dictionary** (Loughran & McDonald 2011 showed ~¾ of general-dictionary "negative" words are not negative in finance). **CB-specific stance models** (hawkish/dovish, e.g. FOMC-RoBERTa). **Entity and relevance attribution** and **novelty** per story (RavenPack). Change versus the prior statement. Handling of conditional/hedged language | An ad-hoc 41-phrase lexicon (not Loughran-McDonald). FinBERT (generic financial sentiment, not policy stance; fails on conditionals per the repo's own 2026-09-11 test). LLM tier is opt-in. **No entity attribution** (the sign-inversion bug). Novelty via lexicon-term overlap. No statement delta | ❌ |
| **E. Cross-asset and positioning context** | 2-year yield (most policy-sensitive), real yields, broad USD, equities, **implied vol** (VIX/MOVE/gold vol), credit spreads, positioning (COT, risk reversals), flows. For gold, the four GRAM families | DTWEXBGS, 10y real yield, WTI, S&P 500, COT on the USD Index — all confidence-only. No 2y, no vol, no credit, no gold COT, no ETF or central-bank flows | ⚠️ |
| **F. Unscheduled news / event risk** | Real-time detection with **entity and geo tags**, a large event taxonomy with relevance/novelty, severity, mapping to the portfolio, plus a geopolitical-risk baseline (Dataminr, RavenPack, GPR) | Fast, well-engineered alert plumbing (latency budget, provider fallback, dedup) ✅. But only 6 categories, no country/entity, and alerts never feed scoring. The anomaly detector downgrades Tier 1 confidence | ⚠️ |
| **G. Impact measurement and validation** | Event study with tight windows (e.g. 10 min before to 20 min after for FOMC in GSS-style work); the move measured **relative to normal volatility**; **several horizons** (knee-jerk vs sustained); comparison to **naive baselines**; calibration (Brier score, reliability curve); value **after costs**; out-of-sample/walk-forward | One 30-min window with a **fixed 0.15%** threshold (`scoring/outcome_classifier.py:22-23`), not vol-scaled. Hit rate only (73%, n=30). No baseline comparison, no calibration curve, no cost-adjusted value. The shock audit script does use baseline-ranked moves ✅ | ❌ |
| **H. Turning the read into action** | Size by conviction × expected magnitude; cut risk before high-uncertainty events; account for spread and slippage; decide whether to fade or follow after the release | Dashboard only. **Not wired to ACE.** ACE uses a flat ±30-min blackout from MT5's calendar (§4.1) | ❌ |

### Where the engine is at or above standard

`[Likely]` The engine beats typical retail news tooling (calendar impact colors, generic news filters, "avoid trading 30 minutes around red events") on:

- no-lookahead discipline and provenance tags
- thin-sample probability caps and the confidence sample floor
- Kalshi integration
- the precursor graph
- contradiction flags
- alert latency engineering

That discipline is the right foundation. The gaps are concentrated in stages B, C, D, G and H.

### The structural point the benchmark exposes

`[Likely]` In the announcement-effects literature, surprises are by construction what consensus missed. Public pre-release press tone is mostly already in the consensus, so it is a weak predictor of the surprise itself. Professional desks find their edge elsewhere:

- nowcasts vs consensus (the engine's Tier 1)
- market-implied pricing vs consensus (Kalshi)
- positioning asymmetry (COT)
- regime-aware reaction functions

The engine's center of gravity is the article-sentiment pipeline, which is the **least** industry-aligned component. Its industry-aligned parts are Tier 1 and Kalshi. The live record fits that reading: PPI was 4/8, a coin flip, on n=8 as of 2026-09-11. That's consistent with, not proof of, the point.

**Implication:** treat article sentiment as one weak vote, and put engineering effort into stages B, C and G.

---

## 3. US-scope triage of the audit's ten recommendations

> **Superseded later the same day (2026-10-16):** scope was clarified. Gold is traded now, and majors, indices and commodities will be added. The triage below is kept for the record. The current status of each item is in `docs/superpowers/specs/2026-10-16-instrument-context-layer-design.md` §7: the JPY pilot becomes the second-instrument template test, and the transmission graph becomes the factor registry plus instrument exposures.

| # | Item | Under US scope | Why |
|---|---|---|---|
| P0-1 | Foreign-CB attribution fix | **Keep** | It's a live USD bug. Foreign CBs move DXY (§1). The US-scope fix is cheaper than the full one: exclude foreign-CB articles from FOMC-family scoring and surface them as DXY-relevant alerts instead of building per-currency axes |
| P0-2 | Standardized surprises | **Keep** | Pure US; stage B |
| P0-3 | Rotate the Alpha Vantage key | **Keep** | Security |
| P1-4 | (country, title) keying | **Defer** | Only needed once non-USD calendar rows are admitted. Cheap insurance meanwhile: make `usd_surprise_score()` return `None` when `country != "USD"` |
| P1-5 | Wire the influence-link weights | **Keep** | Pure US; stage C |
| P1-6 | Shock-alert country tags and routing | **Trim** | Keep the country tag (stops foreign-CB mis-attribution). Add `trade_policy → metal` (the 2025 CBP gold-bar case) and US-specific hard rules (Fed, Treasury, tariffs on gold or metals). Drop JPY/FX routing |
| P1-7 | COMEX gold managed-money COT | **Keep** | XAUUSD is the primary instrument; stage E |
| P2-8 | JPY end-to-end pilot | **Drop** | Out of scope unless USDJPY is actually traded |
| P2-9 | CB-stance model plus FOMC statement delta | **Keep, promote to P1** | FOMC is the highest-impact event and the worst-performing (0/2); stages B and D |
| P2-10 | Transmission graph plus catalyst calendars | **Trim** | Drop the multi-currency graph. Keep a **US catalyst calendar**: Treasury auctions and quarterly refunding, Fed speakers and blackout windows, tariff effective dates, debt-ceiling dates, BLS schedule changes |

---

## 4. Considerations not covered in the first audit

These are ordered by expected impact on actual trading outcomes, not on dashboard quality.

### 4.1 The engine doesn't reach the EA — decide its job first `[Certain]`

ACE's news handling is `CASE_NewsEngine` (`ACE/ACE_v3.14.3/Core/ASE_NewsEngine.mqh`). It's a binary block of ±`InpNewsBlockMinutes` (default 30) around any **high-impact** event from MT5's built-in calendar, for **any country** (`CalendarValueHistory(values, now, window, NULL, NULL)`). Nothing from the Python engine reaches it: no direction, probability, magnitude tier, shock alert or Tier 1 call.

The engine therefore needs a declared job, because the right next build depends on it:

| Job | What the engine must produce | Industry analogue |
|---|---|---|
| (a) Discretionary dashboard | Today's output, kept trustworthy (P0 fixes) | Analyst event preview |
| (b) **EA risk gate** (`[Likely]` highest ROI for an intraday EA) | Expected **magnitude** per event (implied vol, magnitude grid, shock flag) → block, widen or reduce size, event by event instead of a flat ±30 min | Systematic desks' event-risk filters |
| (c) EA directional bias | Direction plus calibrated probability, shown to beat a baseline (§4.6) | Event-driven macro strategies |

Job (c) shouldn't be wired until the stage-G validation exists. Feeding an unvalidated 73% (n=30) directional read into ACE would import the engine's uncertainty into live risk.

### 4.2 ACE's blackout likely stops working after 48 hours of uptime `[Likely]`

- `ScanUpcomingNews()` runs **once**, from `OnInit` (`ACE_v3.14.4.mq5:201`), and registers high-impact events in the next 48 h.
- Live updates are meant to arrive through `OnCalendarEvent(...)` (`ACE_v3.14.4.mq5:209`). The MQL5 book's calendar chapter says the API has **no** event callbacks of this kind; a program must poll on its own schedule (typically `EventSetTimer` plus `CalendarValueLast` with `change_id`).
- If that's right, `OnCalendarEvent` never fires. On a VPS that runs continuously, the queue empties after 48 h, and ACE then trades straight through NFP, CPI and FOMC until the next re-init.

I couldn't reach mql5.com's reference page from this environment, hence `[Likely]`, not `[Certain]`. **Check it in 30 seconds:** search the Experts log for the `high-impact events in next 48h` print. If it appears only at EA load, and no new events are registered between loads, the bug is confirmed.

Two related points:

- `[Likely]` Calendar functions are also unavailable in the Strategy Tester. If so, every ACE backtest and optimization ran **without** the news blackout, so news-spike trades are baked into the fitted parameters. Check the tester log for `registered 0`.
- The blackout is symmetric and uniform. An FOMC press conference runs roughly 60+ minutes past the statement, while a low-relevance "high-impact" foreign release gets the same 30 minutes as NFP.

### 4.3 Revisions are ignored `[Certain]`

The engine stores `previous` but never computes a revision delta. For NFP in particular, desks read the headline **and** the net two-month revision together. A +50K beat with −80K of revisions is not a beat. The fix is local: diff the stored `previous` against the prior occurrence's `actual` in `event_history`, then fold it into the standardized surprise.

### 4.4 Consensus quality and dispersion `[Certain]` that the engine has none

The same surprise is less informative when forecasters disagree widely. Bloomberg publishes the survey σ for this reason. Forex Factory gives one number with no dispersion and no survey timestamp. A free proxy is already half-integrated: Kalshi's **multi-strike** prices form an implied distribution. The README lists multi-strike blending as out of scope; it's the cheapest source of dispersion available.

### 4.5 Predict magnitude, not only direction

Options markets price the expected move of each event: an at-the-money straddle across the release is roughly the market's expected absolute move. For gold, a free daily proxy is the CBOE Gold ETF Volatility Index, GVZ (`GVZCLS` on FRED, `[Likely]` series ID). Event-level implied moves need options data. A market-priced magnitude beats the static LOW/MED/HIGH grid for both risk gating (§4.1b) and sizing. It's also more achievable than direction.

### 4.6 Validate against baselines and at the right horizon

- **Baseline.** A 73% hit rate is meaningless without a naive comparator, such as "follow the Kalshi favourite", "same sign as last month's surprise", or "always the majority historical reaction". Report skill **over** the baseline, plus Brier score and a reliability curve.
- **Horizon.** Outcomes are graded at **30 minutes** with a fixed 0.15% threshold. ACE works H1 entries under H4/D1 context and holds for hours `[Likely]`. A call that's right at 30 minutes but reverses by the H1 close is a loss to ACE. Grade at several horizons (5 min, 30 min, 4 h, NY close), and make the vol-scaled threshold `k × baseline σ` for that window.
- **Costs.** Measure value after XM's news-time spread widening and slippage. A correct call can still lose money in the first minutes.

### 4.7 Reaction-function drift

Which releases matter shifts with the Fed's focus: CPI dominated in 2022, labor data later. The static magnitude grid and trust weights will age. Once per-event n is large enough, re-estimate event "betas" on a rolling window from the engine's own graded outcomes (stage C), the way the Citi index re-derives weights from FX reactions.

### 4.8 US supply, Fed-communication and data-integrity calendars

These are US-scope inputs the engine doesn't hold:

- **Treasury auction results and quarterly refunding.** A tailing 10y or 30y auction moves real yields and therefore gold.
- **Fed speaker schedule and blackout windows.** No Fed communication from the second Saturday before a meeting until the day after it `[Certain]`. During blackout, any "Fed" headline is commentary, not policy, and should be weighted down.
- **BLS and BEA schedule integrity.** The 2025 shutdown delayed releases and paused USDA export-sales publication. Postponed or revised schedules need explicit handling. The engine has reschedule detection; extend it to "cancelled or postponed".

### 4.9 Operational load

Every new source adds a failure mode for a one-person operation. Recent examples are the Forex Factory rate limits, the Dukascopy terms-of-service exposure, and Anthropic credits running out (feature inventory, 2026-10-05). Under a US-only scope, prefer **fewer, higher-quality** inputs: FRED, CFTC, Kalshi, Treasury and Fed calendars. Breadth isn't the goal.

---

## 5. Recommended US-scope order

1. **ACE calendar polling fix** (§4.2): `EventSetTimer` plus `CalendarValueLast(change_id)` or a periodic 48 h rescan; per-event block windows; restrict to USD plus gold-relevant events. It's outside this engine, but it's the highest real-money risk found. Ship it as a new ACE version with the magic-number convention.
2. **P0-1, P0-2, P0-3** from the audit.
3. **Declare the engine's job** (§4.1). If it's job (b), build a magnitude export that ACE reads: GVZ or implied move, the magnitude grid and the shock flag, written to a file in MT5's common Files folder.
4. **Validation upgrade** (§4.6): baselines, Brier score, multi-horizon vol-scaled grading aligned to ACE's holding period.
5. **FOMC stance model plus statement delta** (promoted P2-9).
6. **Gold drivers along GRAM lines**: COMEX gold COT, central-bank purchase data, ETF flows.
7. Influence-weight wiring, trimmed alerting, revisions, the US catalyst calendar and Kalshi dispersion, in whatever order real misses point to.

Per the feature-inventory maintenance rule, none of this goes into `docs/feature-inventory-2026-09-11.md` until it's agreed for build.

---

## Sources

- Andersen, Bollerslev, Diebold & Vega (2003), *Micro Effects of Macro Announcements*, AER 93(1): [NBER w8959](https://www.nber.org/system/files/working_papers/w8959/w8959.pdf), [SSRN](https://papers.ssrn.com/abstract=313660)
- Gürkaynak, Sack & Swanson (2005), *Do Actions Speak Louder Than Words?*, IJCB: [FEDS 2004-66](https://www.doi.org/10.17016/FEDS.2004.66), [MPRA PDF](https://mpra.ub.uni-muenchen.de/820/1/ijcb05q2a2.pdf)
- Loughran & McDonald (2011), *When Is a Liability Not a Liability?*, JF: [SSRN](https://papers.ssrn.com/abstract=1331573)
- Citi/Bloomberg surprise index construction (secondary): [M&G — Surprise indices](https://www.mandg.com/investments/professional-investor/en-lu/insights/mandg-insights/latest-insights/2018/03/surprise-indices-a-reminder), [BSI Economics](https://bsi-economics.org/economic-surprise-indicator/), [Bank Underground — rates and data surprises](https://bankunderground.co.uk/2018/01/23/stirred-not-shaken-how-market-interest-rates-have-been-reacting-to-economic-data-surprises/)
- World Gold Council GRAM: [Short-term gold price drivers](https://www.gold.org/goldhub/data/short-term-gold-price-drivers), [Gold market commentary, April 2025](https://www.gold.org/goldhub/research/gold-market-commentary-april-2025), [Gold market commentary, July 2026](https://www.gold.org/goldhub/research/gold-market-commentary-july-2026)
- August 2025 gold-bar tariff episode: [Mining Weekly](https://www.miningweekly.com/article/white-house-to-clarify-tariffs-for-gold-bars-as-industry-stops-flying-bullion-to-us-2025-08-11), [Mexico Business News](https://mexicobusiness.news/mining/news/surprise-us-tariff-gold-bars-drives-gold-futures), [Qatar Tribune](https://www.qatar-tribune.com/article/189227/business/bullion-markets-breath-sigh-of-relief-as-trump-says-gold-will-not-face-tariffs)
- Event implied moves: [NYU Stern — macro surprises and implied volatility](https://www.stern.nyu.edu/sites/default/files/assets/documents/con_043248.pdf), [The expected move isn't a forecast](https://buttondown.com/Paragon-Signals/archive/the-expected-move-isnt-a-forecast/)
- MQL5 calendar has no event callback: [MQL5 book — tracking calendar changes](https://www.mql5.com/de/book/advanced/calendar/calendar_change_last)
- Cited from the literature without a fetched link this session: Kuttner (2001, JME), Nakamura & Steinsson (2018, QJE), Gilbert, Scotti, Strasser & Vega (2017, JME, `[Likely]` on exact title)
