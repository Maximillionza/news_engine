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

## 5. Learning Module Content Outline

### Section 1: What Is a Financial Market (4–6 slides)
- Markets overview: Forex, Metals, Crypto, Stocks
- Who participates and why
- Supply and demand drives price (simplified)
- Quiz: 3 conceptual questions

### Section 2: Reading a Candlestick Chart (5–7 slides)
- OHLC explanation with illustrated candle
- Bullish vs bearish candles
- Timeframes explained (5M, 15M, 1H, 4H, D1)
- How to read left-to-right
- Quiz: 3 questions (including "what does this candle tell us")

### Section 3: Market Structure (5–7 slides)
- Uptrend: higher highs and higher lows
- Downtrend: lower highs and lower lows
- Range: equal highs and lows
- Key levels: support and resistance
- Quiz: 3 questions (including structure identification from chart)

### Section 4: What Is a Confluence (6–8 slides)
- Definition: independent signals agreeing on direction
- Why one signal is insufficient
- Introduction to each of the 5 setups (brief — depth through practice)
- What makes a setup valid vs a trap
- Quiz: 3 questions on confluence concept

### Section 5: Risk Management (7–8 slides)
- Stop Loss: what it is, why it is non-negotiable
- Take Profit: what it is
- Lot size explained (what 0.01 lots means on EURUSD)
- Pip value calculation: worked example ("0.01 lot on EURUSD = $0.10 per pip")
- Risk per trade %: the 1% rule explained
- Worked example: "$500 account. 1% risk = $5. SL is 50 pips. Max lot size = 0.01 lots."
- Quiz: 3 questions including a calculation

### Section 6: Margin and Leverage (5–6 slides)
- What leverage means (amplification in both directions)
- What margin is (collateral, not a fee)
- Why TradeWise starts at 1:10 (low leverage = learning)
- What a margin call is and how to avoid it
- Quiz: 3 questions

### Section 7: What Is a Trading Plan (4–5 slides)
- Why a plan removes emotion from decisions
- The three questions: What do I trade? When? How much risk?
- Career Mode as the practice environment for developing answers
- Quiz: 3 questions

**Estimated completion time:** 40–55 minutes.  
**All slide illustrations must be produced before module is built.** Minimum 30 illustrations total.
