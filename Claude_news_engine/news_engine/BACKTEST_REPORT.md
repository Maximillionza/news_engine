# Backtest Report: Fundamental News Probability Engine

**Test date:** 2026-08-09
**Instrument scored:** XAUUSD (Gold)
**Events tested:** 10 major (red-folder) USD releases — NFP, CPI, PPI, FOMC
**Result:** 8/9 directional calls correct (89%), 1 no-call, 1 wrong

## Read this before the results

This backtest did **not** pull live articles from a news API. The sandbox
this was built in has no network access to news feeds or Forex Factory. So:

- **Actual outcomes are 100% real**, confirmed via web search against
  multiple independent financial news sources (Reuters, CNBC, Kitco,
  TradingKey, FXStreet, GoldSilver, BLS, Federal Reserve).
- **Pre-event "articles" are reconstructed**, not pulled. Each one is a
  paraphrased version of the real forecast/expectation framing that was
  actually being reported ahead of the release (sourced via the same web
  search), manually assigned a plausible pre-event timestamp.

This tests whether the **scoring logic** — time-decay weighting, source
trust weighting, instrument mapping, sigmoid probability transform — is
internally sound. It does not test real source timing, real article
volume, real coverage noise, or whether the lexicon sentiment scorer holds
up against genuine unfiltered news text. That validation still requires
running `scoring/backtest.py`'s live fetch path with real API/RSS access.

---

## Configuration used

All values are current defaults in `config/settings.py` — none have been
tuned yet; this run is the first data point toward tuning them.

| Parameter | Value | Meaning |
|---|---|---|
| `PRE_EVENT_WINDOW_HOURS` | 48 | Articles considered start 2 days before event time |
| `TIME_DECAY_HALF_LIFE_MINUTES` | 360 (6h) | An article's weight halves every 6 hours of age |
| `RECENT_WINDOW_HOURS` | 6 | Window used to split "recent" vs "older" for contradiction detection |
| `CONTRADICTION_MIN_MAGNITUDE` | 0.15 | Minimum instrument-score magnitude for a window to count as a real directional lean |
| Sigmoid steepness `k` | 2.5 | Controls how fast probability saturates toward 0%/100% |
| Instrument mapping (XAUUSD) | `inverse` | Gold score = −(aggregate USD sentiment) |

**Source trust weights** (0–1 scale, applied as a multiplier alongside time-decay):

| Source | Weight | Note |
|---|---|---|
| `rss_reuters_business` | 0.85 | Wire service — used for every article in this test |
| `rss_cnbc_economy` | 0.65 | Not used this run |
| `rss_cnbc_top_news` | 0.60 | Not used this run |
| `rss_investing_com_forex` | 0.55 | Not used this run |
| `alpha_vantage_news` | 0.70 | Not used — no API key, RSS-only per current decision |
| `apitube_news` | 0.70 | Not used — no API key, RSS-only per current decision |

All 30 reconstructed articles in this test were tagged as `rss_reuters_business`
(0.85 trust weight) for consistency — the real run will naturally mix
sources and weights once live RSS/API pulls are wired in.

**Sentiment scoring:** naive keyword lexicon (`scoring/sentiment.py`), not
a trained model. USD-directional axis, −1.0 (bearish USD) to +1.0 (bullish
USD). No native sentiment scores were available since RSS sources don't
provide them (only Alpha Vantage/APITube do, and those weren't used here).

---

## Event-by-event results

### 1. NFP — July, released 2026-08-07 12:30 UTC — ✅ CORRECT

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "July jobs growth expected to stay low" (30h) | −1.00 | 0.85 × 0.031 = 0.027 | dovish |
| "Economists brace for downward revisions" (20h) | 0.00 | 0.85 × 0.099 = 0.084 | — |
| "Gold cautious near highs ahead of NFP" (4h) | 0.00 | 0.85 × 0.630 = 0.535 | — |

Aggregate USD sentiment: **−0.041** → instrument score (inverse): **+0.041** → **BULLISH gold**, 55% probability, 100% confidence.

**Actual:** NFP printed −23K vs +80K expected — dollar fell to a 7-week low, gold rallied to 7-week highs. **Correct call**, though the probability (55%) was barely above a coin flip — the freshest article (4h old, dominant weight at 0.535) carried no lexicon signal at all, so the call rode almost entirely on one older "dovish" mention.

---

### 2. NFP — June, released 2026-07-02 12:30 UTC — ❌ WRONG

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "June payrolls preview: moderate growth expected" (36h) | +1.00 | 0.85 × 0.016 = 0.013 | hawkish |
| "Rate hike risk if jobs data surprises to upside" (18h) | +1.00 | 0.85 × 0.125 = 0.106 | rate hike ×2 |
| "Dollar firm ahead of jobs report" (6h) | +1.00 | 0.85 × 0.500 = 0.425 | hawkish |

Aggregate USD sentiment: **+1.000** → instrument score: **−1.000** → **BEARISH gold**, 1% probability (i.e. very confident bearish), 100% confidence.

**Actual:** NFP printed +57K vs ~113K expected — a clear miss. Gold jumped above $4,100. **Wrong call**, and the failure is diagnostic: every reconstructed headline used conditional/hedged framing ("risk if data surprises," "firm *ahead of*" the report) describing what *could* happen on a beat, not a statement that a beat had happened or was expected. The lexicon scorer matched the literal words "hawkish" and "rate hike" and scored them as if they were declarative, missing that the surrounding language was hypothetical. This is the single clearest weakness surfaced by this test.

---

### 3. NFP — May, released 2026-06-05 12:30 UTC — ✅ CORRECT

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "Gold at make-or-break level ahead of payrolls" (34h) | +1.00 | 0.85 × 0.020 = 0.017 | rate hike |
| "Consensus points to slowing job growth" (22h) | +0.40 | 0.85 × 0.079 = 0.067 | job growth ×2 |
| "Markets await confirmation of labor cooling" (5h) | +0.80 | 0.85 × 0.561 = 0.477 | higher for longer |

Aggregate USD sentiment: **+0.758** → instrument score: **−0.758** → **BEARISH gold**, 2% probability, 100% confidence.

**Actual:** NFP printed +172K vs 85K expected — a large beat. Gold fell ~2.2%, broke below $4,400. **Correct call**, and a cleaner one than case #1 — the freshest, most heavily weighted article carried real signal this time.

---

### 4. CPI — June, released 2026-07-14 12:30 UTC — ✅ CORRECT

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "Gold recovers ahead of inflation figures" (30h) | 0.00 | 0.85 × 0.031 = 0.027 | — |
| "Cooling inflation could open path for gold rally" (14h) | −0.67 | 0.85 × 0.198 = 0.169 | dovish, cooling inflation ×2 |
| "Gold fell on Iran strikes ahead of CPI print" (20h) | 0.00 | 0.85 × 0.099 = 0.084 | — |

Aggregate USD sentiment: **−0.402** → instrument score: **+0.402** → **BULLISH gold**, 88% probability, 100% confidence.

**Actual:** CPI printed −0.4% MoM vs −0.1% expected — a soft miss. Gold jumped $90 (+2.25%) to $4,091. **Correct call**, and the most confidently correct one in the set.

---

### 5. CPI — May, released 2026-06-10 12:30 UTC — ✅ CORRECT

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "Gold tumbles as hot CPI looms" (26h) | +1.00 | 0.85 × 0.050 = 0.042 | rate hike |
| "Rate-hike bets surge on strong jobs, hot CPI expected next" (15h) | +1.00 | 0.85 × 0.177 = 0.150 | hawkish |
| "Higher-than-expected core CPI could pressure gold" (40h) | 0.00 | 0.85 × 0.010 = 0.008 | — |

Aggregate USD sentiment: **+0.958** → instrument score: **−0.958** → **BEARISH gold**, 1% probability, 100% confidence.

**Actual:** CPI hit 4.2% YoY, hottest since 2023. Gold fell sharply (sources report −2.4% to −4.4% depending on measurement window). **Correct call.**

---

### 6. FOMC Rate Decision, 2026-06-17 18:00 UTC — ✅ CORRECT

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "Fed expected to hold, dot plot in focus" (30h) | +1.00 | 0.85 × 0.031 = 0.027 | hawkish |
| "Warsh's first meeting seen as hawkish test case" (40h) | +1.00 | 0.85 × 0.010 = 0.008 | hawkish ×2 |
| "Gold at $4,347 while stocks hit highs ahead of Fed" (6h) | 0.00 | 0.85 × 0.500 = 0.425 | — |

Aggregate USD sentiment: **+0.076** → instrument score: **−0.076** → **BEARISH gold**, 41% probability, 100% confidence.

**Actual:** Fed held as expected, but ~9 of 18 officials projected a 2026 hike — a hawkish dot-plot tilt. Gold fell 0.94% to $4,290.52. **Correct call**, but the weakest-margin one in the set (41% is close to a coin flip) — the freshest, dominant-weight article had zero lexicon signal, so the call leaned on two stale, low-weight "hawkish" mentions.

---

### 7. FOMC Minutes (June meeting), released 2026-07-08 18:00 UTC — ✅ CORRECT

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "Committee split nine-to-nine on 2026 hike" (24h) | 0.00 | 0.85 × 0.062 = 0.053 | hawkish, dovish (cancelled out) |
| "Weak June payrolls complicate hawkish case" (30h) | +1.00 | 0.85 × 0.031 = 0.027 | hawkish ×2 |
| "Markets brace for hawkish language in Fed minutes" (4h) | +1.00 | 0.85 × 0.630 = 0.535 | hawkish ×2 |

Aggregate USD sentiment: **+0.914** → instrument score: **−0.914** → **BEARISH gold**, 1% probability, 100% confidence.

**Actual:** Minutes showed a hawkish 9–9 split. Gold fell 0.75% to $4,075. **Correct call.**

---

### 8. CPI — March, released 2026-04-10 12:30 UTC — ✅ CORRECT

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "Inflation expected to spike on energy costs" (36h) | 0.00 | 0.85 × 0.016 = 0.013 | — |
| "Markets brace for hot inflation print" (18h) | +0.60 | 0.85 × 0.125 = 0.106 | hot inflation ×2 |
| "Fed seen looking through energy-driven inflation noise" (8h) | −1.00 | 0.85 × 0.397 = 0.337 | rate cut |

Aggregate USD sentiment: **−0.599** → instrument score: **+0.599** → **BULLISH gold**, 84% probability, **76% confidence** (the only case below 100% — the articles didn't all agree in sign).

**Actual:** CPI printed 0.9% MoM vs 1.0% expected, 3.3% YoY vs 3.4% expected — softer than feared. Gold jumped $10+. **Correct call**, and notable as the one case where the confidence metric did its job: genuine disagreement between articles ("hot inflation" vs "rate cut") correctly pulled confidence down from what would otherwise read as high-certainty.

---

### 9. CPI — April, released 2026-05-13 12:30 UTC — ✅ CORRECT

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "Inflation seen re-accelerating on energy costs" (30h) | 0.00 | 0.85 × 0.031 = 0.027 | — |
| "Hawkish new Fed chair adds to rate-hike bets" (20h) | +1.00 | 0.85 × 0.099 = 0.084 | hawkish ×2 |
| "Gold correction continues into CPI print" (10h) | 0.00 | 0.85 × 0.315 = 0.268 | — |

Aggregate USD sentiment: **+0.223** → instrument score: **−0.223** → **BEARISH gold**, 25% probability, 100% confidence.

**Actual:** CPI hit 3.8% YoY vs 3.7% expected — hotter than forecast. Gold fell despite mixed underlying drivers (also a new hawkish Fed chair narrative in play). **Correct call**, lowest-magnitude bearish call in the set (only one of three articles carried any signal).

---

### 10. PPI — February, released 2026-03-18 12:30 UTC — — NO CALL

| Article (age at scoring) | USD sentiment | Trust × time weight | Matched terms |
|---|---|---|---|
| "Producer prices expected to hold steady" (28h) | 0.00 | 0.85 × 0.039 = 0.033 | — |
| "Fed holds rates, no cuts in sight" (16h) | 0.00 | 0.85 × 0.157 = 0.134 | — |
| "Gold steady near highs ahead of producer price data" (6h) | 0.00 | 0.85 × 0.500 = 0.425 | — |

Aggregate USD sentiment: **0.000** → **NEUTRAL**, 50% probability, 0% confidence — no call made.

**Actual:** PPI printed 3.4% vs ~1.7% expected — more than double forecast. Gold fell 3.75% to $4,820. This would have been a bearish call if the engine had committed to one, but every reconstructed article was genuinely neutral in framing (no hawkish/dovish/beat/miss language at all). This isn't excluded from accuracy because it was a bad call — it's excluded because no call was made. That's arguably correct behavior for the engine (staying silent rather than guessing), but it's also very likely an artifact of my reconstruction being too thin for this specific event rather than a true reflection of what real pre-PPI coverage looks like.

---

## Aggregate results

| Metric | Value |
|---|---|
| Events tested | 10 |
| Directional calls made | 9 (90%) |
| Correct calls | 8 |
| Wrong calls | 1 |
| No-call (neutral) | 1 |
| **Accuracy on calls made** | **89%** |
| Contradiction flagged | 0 events |

Zero contradiction flags is expected here — my reconstructed articles were built as a single coherent narrative per event rather than genuinely noisy real coverage, so there was never a case where "recent" and "older" windows disagreed by more than `CONTRADICTION_MIN_MAGNITUDE`. Real live data is very likely to trigger this feature more often.

## What this run actually tells you

**Worth taking seriously:** the core mechanics work as designed. Time-decay weighting correctly favored recent articles, the inverse-USD mapping for gold produced sane bullish/bearish calls, and the confidence metric correctly dropped (case #8) when articles genuinely disagreed.

**Worth being skeptical of:** the failure in case #2 is a real, specific weakness — the lexicon scorer cannot currently distinguish "X is happening" from "X could happen if Y" or "risk of X." That's not a tuning problem, it's a scope limitation of keyword matching, and it will show up again in real data. Several "correct" calls (#1, #6, #9) were only correct by a thin margin, riding on one or two low-weight or borderline articles — a slightly different reconstruction could easily have flipped them. And the extreme probabilities (1%, 88%, 98% in the earlier smoke test) from just 2–3 signal-bearing articles confirm the sigmoid steepness (`k=2.5`) is uncalibrated and overconfident for small sample sizes.

**Bottom line:** this is a legitimate first signal that the architecture isn't broken, not evidence the model is "89% accurate." That number only becomes meaningful once it's run against real pulled articles with real timing and real noise — which is the next step in Claude Code.
