# CONTENT_SPEC.md — TradeWise Content Specification

**Version:** 0.2  
**Owner:** Masood  
**Must be validated by a live trader before dataset curation begins.**

---

## 1. The 5 Core Confluence Setups

A confluence is two or more independent signals agreeing on direction. No single signal is sufficient.

---

### Setup 1: Key Level + Candlestick Confirmation
**Stage introduced:** 1 (Sessions 1–50)

**Components:**
- Component A: Price at a key level (support or resistance). Minimum 2 prior touches visible on 5M chart.
- Component B: Reversal candlestick at that level. Valid patterns: bullish engulfing, bearish engulfing, pin bar, hammer, shooting star. Must close within 10 pips of the level.

**Valid BUY:** Touch of support + bullish engulfing or pin bar at the level.  
**Valid SELL:** Touch of resistance + bearish engulfing or shooting star at the level.

**Trap version:** Price approaches level but confirming candle is a doji or ambiguous body. No clean signal. Correct: No Trade.

---

### Setup 2: Trend Continuation + Fibonacci Retracement
**Stage introduced:** 2 (Sessions 51–150)

**Components:**
- Component A: Clear 1H trend (3+ swing points confirming direction)
- Component B: Price retraces to 50% or 61.8% Fibonacci of most recent impulse on 5M
- Component C (optional, strengthens): Candlestick confirmation at Fib level

**Valid BUY:** 1H uptrend + pullback to 50/61.8% Fib + bullish candle.  
**Valid SELL:** 1H downtrend + retrace to 50/61.8% Fib + bearish candle.

**Trap version:** Price hits Fib level but 1H trend is ambiguous (ranging). No HTF context. Correct: No Trade.

---

### Setup 3: Market Structure Break + Retest
**Stage introduced:** 2 (Sessions 100–150)

**Components:**
- Component A: Clear break of prior swing high (BUY) or swing low (SELL) on 5M. Close beyond the swing by 10+ pips.
- Component B: Price returns to retest the broken level.
- Component C: Candlestick confirmation at retest.

**Valid BUY:** Prior resistance broken → retest from above → bullish confirmation.  
**Valid SELL:** Prior support broken → retest from below → bearish confirmation.

**Trap version:** Aggressive return through the level post-break (false break / liquidity sweep). Retest is actually continuation of the break. Correct: No Trade.

**Dataset curation note:** `trigger_candle_index` must be placed at the retest confirmation candle — not at the break candle.

---

### Setup 4: Multi-Timeframe Confluence
**Stage introduced:** 3 (Sessions 151–300)

**Components:**
- Component A: Key level on 1H chart (visible when user toggles to 1H)
- Component B: Market structure shift on 5M at that 1H level
- Component C: Candlestick confirmation on 5M

**Valid BUY:** 1H key support + 5M structure shift upward + 5M bullish candle.  
**Valid SELL:** 1H key resistance + 5M structure shift downward + 5M bearish candle.

**Trap version:** 1H level present but 5M structure has not shifted. Price still making lower highs against 1H support. Correct: No Trade.

---

### Setup 5: Compression Breakout
**Stage introduced:** 3 (Sessions 200–300)

**Components:**
- Component A: Narrowing range (lower highs + higher lows) visible over 10+ candles on 5M
- Component B: Breakout candle — closes outside compression with body ≥ 1.5× average body size of compression period
- Component C: Breakout direction aligns with 15M trend or momentum

**Valid BUY:** Compression + bullish breakout close above range + 15M trend is up or neutral.  
**Valid SELL:** Compression + bearish breakout close below range + 15M confirms.

**Trap version:** Breakout wick but no close outside range. Or breakout directly against strong 1H trend. Correct: No Trade.

---

## 2. Trap Setup Library

| Trap Type | Description | First Appears |
|---|---|---|
| Ambiguous candle | Doji or inside bar at a level — no directional signal | Stage 1 |
| False break | Price breaks a level intracandle but close is back inside | Stage 1 |
| Counter-trend entry | Valid-looking setup against a strong HTF trend | Stage 2 |
| Open space | Price between levels with no identifiable structure | Stage 2 |
| Early entry | Pattern forming but not yet confirmed | Stage 2 |
| News simulation | Sharp directional move with no structure basis (volatility spike) | Stage 3 |

**Trap frequency by stage:**

| Stage | Trap % of decision points |
|---|---|
| 1 | 10% |
| 2 | 25% |
| 3 | 35% |
| 4 | 40% |

---

## 3. Arcade Challenge Content Requirements

### Candlestick Pattern Library (minimum)
Patterns the app must be able to show and ask about:
- Single candle: Doji, Hammer, Shooting Star, Marubozu (bullish/bearish), Spinning Top
- Two candle: Bullish Engulfing, Bearish Engulfing, Bullish Harami, Bearish Harami, Tweezer Tops/Bottoms
- Three candle: Morning Star, Evening Star, Three White Soldiers, Three Black Crows

For each pattern: a pre-rendered candle illustration (SVG or image asset) + correct answer + 3 distractor options + 1-sentence explanation.

### Bollinger Band Question Library
Questions must cover:
- Price at upper band: what does this indicate?
- Price at lower band: what does this indicate?
- Band squeeze (bands narrowing): volatility contracting, breakout likely
- Band expansion: volatility increasing, momentum move
- Price returning to midline from extremes: mean reversion signal

### Reversal vs Pullback Library
Minimum 30 chart examples. Must include:
- Clear reversals (trend change with structure evidence)
- Clear pullbacks (retracements within intact trend)
- Ambiguous cases (Stage 2+ only)

---

## 4. Dataset Curation Requirements

**MVP minimum:** 20 Career Mode datasets. Each dataset:
- Named: `INSTRUMENT_TIMEFRAME_CONDITION_NUMBER` (e.g. `EURUSD_5M_RANGING_003`)
- Market condition: at least 4 of each condition (trending_up, trending_down, ranging, compression, high_vol)
- Stage distribution: at least 2 Stage-1-only (pure foundation, no traps)
- Trap sessions: at least 3 is_trap_session = true datasets (mostly No Trade correct)
- Minimum 60 total unique decision points tagged across all datasets

**Per decision point required fields (see DATA_SCHEMA.md):**
All fields must be populated before a dataset is marked `active = true`.

**Coaching card content must be written before dataset activation.** Use this template:

*Win card (Stage 1):*
"Good trade. This was a [Setup Name]. [Component A description]. [Component B description] confirmed the direction. Notice how [one observation about what made this setup clear]."

*Loss card (Stage 1):*
"This was still a [Setup Name] setup. The direction was [correct/incorrect] based on the signals. The trade moved against you because [brief explanation]. Review the [timeframe] to see if [higher context clue] suggested caution."

*Correct No Trade:*
"Good discipline. This was a [Trap Type]. [One sentence on why no setup was valid]. Sitting out a bad trade is as valuable as winning a good one."

*Incorrect No Trade:*
"This was a valid [Setup Name]. No points lost — skipping a valid setup is always safe. Next time, look for [the key component that confirmed this setup]."

---

## 5. Course Catalogue Content Outline (restructured v0.4)

The 7 original sections are regrouped into a **5-course catalogue**. Mapping shown for traceability — no content requirement below is new relative to v0.2 except where marked **[NEW]**. Full lesson prose, quiz Qs/answers, and image briefs are maintained in `COURSE_CATALOGUE.md` (generated from this outline) rather than duplicated here.

| Course | Tier | Maps to v0.2 sections | Lessons |
|---|---|---|---|
| 1. Market Foundations | Basic, free | Sections 1–3 | 9 |
| 2. Confluence & Setups | Intermediate, free | Section 4 + the 5 core setups (§1 above) | 5 |
| 3. Risk & Money Management | Intermediate, free | Sections 5–6 | 4 |
| 4. Trading Plans & Discipline | Intermediate, free | Section 7 + No-Trade discipline (LEARNING_THEORY.md §4) | 4 |
| 5. Multi-Timeframe Mastery & Advanced Strategies | Advanced, paywalled | Setups 4–5 (§1 above) + trap library depth + **[NEW]** expectancy/R-multiples, strategy-framework primer | 5 |

**Course 1 — Market Foundations** (Basic) — **[REVISED v0.4]** expanded from 4 to 9 lessons, BabyPips-style plain-language pacing, after feedback that the original 4-lesson version read as intermediate rather than basic
1. Trading Terms Every Beginner Needs to Know — pip, bid/ask/spread, long vs short (glossary primer, avoids assuming prior jargon)
2. What Is a Financial Market — markets overview (Forex, Metals, Crypto, Stocks), participants, supply and demand
3. What Is a Candle — OHLC, bullish vs bearish, what a wick tells you
4. Types of Candles — Marubozu, Doji, Spinning Top
5. Candle Formations — what turns a shape into a signal (context/trend), single-candle vs multi-candle formations
6. Most Common Candle Patterns — Bullish/Bearish Engulfing, Hammer, Shooting Star, Morning Star, Evening Star
7. Timeframes & Chart Navigation — 5M/15M/1H/4H/D1, reading left-to-right
8. Trends & Ranges — uptrend, downtrend, range
9. Support & Resistance — key levels, in context

**Course 2 — Confluence & Setups** (Intermediate)
1. What Is a Confluence — independent signals agreeing on direction, why one signal is insufficient
2. Setup 1: Key Level + Candlestick Confirmation
3. Setup 2: Trend Continuation + Fibonacci Retracement
4. Setup 3: Market Structure Break + Retest
5. Spotting Traps — ambiguous candles, false breaks, counter-trend entries (Stage 1–2 trap library)

**Course 3 — Risk & Money Management** (Intermediate)
1. Stop Loss & Take Profit — what they are, why SL is non-negotiable
2. Lot Size & Pip Value — worked example: "0.01 lot on EURUSD = $0.10 per pip"
3. The 1% Risk Rule — worked example: "$500 account, 1% risk = $5, 50-pip SL → max 0.01 lots"
4. Margin & Leverage — amplification, margin as collateral, why TradeWise starts at 1:10, margin calls

**Course 4 — Trading Plans & Discipline** (Intermediate)
1. Why a Trading Plan Removes Emotion
2. The Three Questions — what to trade, when, how much risk
3. The Power of "No Trade" — overtrading as the top cause of retail losses (LEARNING_THEORY.md §4)
4. Reading Your Own Performance — plain-language intro to the Career Readiness Rating (FR-035), with the same disclaimer language used everywhere else it appears

**Course 5 — Multi-Timeframe Mastery & Advanced Strategies** (Advanced, paywalled)
1. Setup 4: Multi-Timeframe Confluence
2. Setup 5: Compression Breakout
3. Advanced Trap Library — false breaks / liquidity sweeps, counter-trend traps, news-simulation spikes (Stage 3 traps)
4. **[NEW]** Session Risk Budgeting & Expectancy — R-multiples, why a single trade shouldn't exceed 2% risk (ties to LEARNING_THEORY.md Stage 3 risk-budget concept)
5. **[NEW]** Intro to Strategy Frameworks — a teaser primer on the strategy families sold in full via the Strategies Pack ($9.99, MONETISATION.md §2.1): ICT-inspired concepts, SMC structure, momentum continuation

Each lesson: 3-question quiz, 2/3 to pass, unlimited retries (unchanged from v0.2 FR-006). Each course ends with a **Test Your Knowledge** prompted-tagging assessment — see §6.

**Estimated completion time:** Basic + 3 Intermediate ≈ 55–70 minutes combined (increased from v0.2 by Course 1's 4→9 lesson expansion). Advanced course: additional 20–25 minutes.
**All slide illustrations must be produced before a course is built.** Minimum 34 illustrations for the free tier (increased from v0.2's 30 by Course 1's expansion), plus a further ~12 for the Advanced course.

---

## 6. Test Your Knowledge — Prompted Multi-Label Content Requirements **[REVISED v0.4]**

Each course's Test Your Knowledge assessment presents **one image at a time**, each paired with up to 5 candidate labels; the user selects every label that genuinely applies to that image — most images have exactly one correct label, but several are deliberately built with two correct labels at once (e.g. a chart showing both a downtrend *and* a support bounce), to train the idea that a single chart can carry more than one true observation. This replaced an earlier one-label-per-target drag-and-drop board after user feedback that the board read as too "list format" — the prompted, one-item-at-a-time flow is closer to how BabyPips-style quizzes present a single chart and ask what's on it.

Scoring is **judgment accuracy**, not item-pass/fail: every label decision (correctly selecting an applicable label, or correctly leaving a non-applicable one unselected) counts toward the total. Pass threshold is 70% of all label decisions across the assessment (PRD.md FR-036).

| Course | Images | Candidate-label pool(s) | Items with 2 correct labels | Minimum items |
|---|---|---|---|---|
| Market Foundations | Single candles, chart snippets, named patterns | Candle types (Bullish/Bearish/Doji/Marubozu/Spinning Top); structure + levels (Uptrend/Downtrend/Range/Support/Resistance); timeframes; named patterns | 4 (Marubozu example, support/resistance-in-context, both timeframe examples) | 14 |
| Confluence & Setups | Chart snapshots, one per setup + trap examples | 3 setups + Fib/structure-break sub-labels; 4 trap types + No Setup | 2 (Setup 2 chart also shows the Fib level; Setup 3 chart also shows the structure break) | 10 |
| Risk & Money Management | Definition cards, worked-example scenario cards | Term pairs per item (SL/TP/Margin/Leverage/etc.); sizing-scenario labels | 0 | 10 |
| Trading Plans & Discipline | Scenario cards | Trade / No Trade / Wait for Confirmation / Missing Setup Component / Counter-Trend Risk | 4 (each No Trade scenario also names *why*) | 8 |
| Multi-Timeframe Mastery & Advanced Strategies | Chart snapshots, risk-budget scenario cards, framework definitions | Setups 4–5 + 3 trap types; risk-budget/R-multiple outcomes; 3 framework names | 0 | 12 |

Each label set carries a 1-sentence explanation shown in the post-assessment review (reuse the coaching-card tone and template from §4 above). Item banks must be finalised before a course's Test Your Knowledge is marked `active = true`, mirroring the dataset-activation rule in §4.

**Future enhancement, not yet scoped or built:** a spatial variant using real chart snapshots, where instead of tagging the whole image, the user clicks the specific location on the chart where a prompted concept appears (e.g. "click the candle that completes the Bullish Engulfing pattern"). This is a materially different interaction (coordinate-based hit-testing against an authored answer region per image) and needs its own FR and DATA_SCHEMA design before being built — logged here per the user's explicit instruction to defer it.
