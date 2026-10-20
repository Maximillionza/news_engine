# News Engine — Fundamental Analysis Audit: Techniques, Non-USD Blind Spots, Comparable Tools

> Imported into the live branch 2026-10-21; ACE/EA/MT5 material removed per owner ruling (out of scope for news_engine).

**Prepared:** 2026-10-16 (SAST)
**Builds on, does not repeat:** `docs/fundamental-analysis-swot-2026-08-14.md`, `docs/fundamental-analysis-alignment-review-2026-09-02.md`, `docs/fundamental-analysis-review-2026-09-11.md`, `docs/feature-inventory-2026-09-11.md`.
**Companion:** `docs/fundamental-analysis-industry-benchmark-2026-10-16.md` has the stage-by-stage benchmark against industry-standard practice, the US-only-scope triage of §7 below.
**Questions answered:** (1) which fundamental-analysis (FA) techniques the engine actually uses to assess news events, (2) which factors are missing given the engine is USD-centric, and how it could anticipate non-USD events (the "US slows soy exports to Japan → yen" case), (3) what comparable tools do that is worth copying.
**Method:** a direct read of `config/`, `data_layer/`, `scoring/`, `alerting/` and `webapp/` at commit `386728f`. I also ran three probes that push hand-written headlines and calendar rows through the engine's real code paths; they live in `scripts/audit_fa_probes.py` (no network, no DB writes, re-runnable). External research came from web searches, with sources at the end.
**Not available to this audit:** the live `scoring/backtest_log.db` / `webapp/dashboard.db` (gitignored) and `docs/News_Engine_Causation_Matrix_v2.xlsx` aren't in the checkout. So accuracy figures can't be re-pulled, and §3 cites the last real snapshot (2026-09-11). FinBERT couldn't be executed either, because torch isn't installed in this environment.

---

## 0. Bottom line

**The soy example is the wrong test case, and testing for it would teach the engine noise.** `[Likely]` In 2023 the US shipped about 2.2 Mt of soybeans to Japan, roughly two-thirds of Japan's ~3.2–3.4 Mt imports. At roughly $450/t landed, that's on the order of US$1bn a year. Japan's 2025 import bill was about US$755bn, so US soy is roughly 0.15% of it. USDJPY spot turnover is on the order of a trillion dollars a day, so a full year of that trade clears in about a minute and a half of one trading day. A soy headline only matters to the yen as a *symptom* of US–Japan trade-policy friction, never as a trade flow. The channels that actually move JPY are different: the US–Japan rate differential, BoJ policy, MoF intervention, the energy import bill (a terms-of-trade shock, because Japan imports nearly all its oil), and safe-haven/carry-unwind dynamics. The engine models **none** of them. §4 covers this in detail.

**Before any expansion, the engine already mis-reads non-USD news *inside* its USD scope.** `[Certain]` Probe 1 shows that ECB, BoE, BoJ and RBA rate headlines pass the FOMC relevance filter and are scored with the **inverted** USD sign. A hawkish BoJ reads as +0.98 USD-bullish, so the engine leans gold bearish on what is actually yen-bullish, USD-softening news. This is a live correctness defect and the highest-priority item in this audit (§2.1).

**The core surprise metric can't be compared across indicators.** `[Certain]` Probe 3 shows that the same 0.1pp CPI miss scores 0.905 on the m/m print and 0.103 on the y/y print, a 9× difference for the same information. A 0.1pp unemployment-rate miss scores −0.071, which is close to nothing. Every essence score and every precursor contribution inherits this distortion (§2.2).

**The structural limit is the single USD axis.** Every input is projected onto one USD-directional number. Anything without a USD leg is invisible: `EURJPY` is classed `fx_cross` and scored "not applicable". Anything with a foreign subject gets mis-signed. The dashboard's symbol picker already offers USDJPY, so today a USDJPY card shows half a fundamental picture with no JPY leg at all. The fix is a two-sided, per-currency model (§5), not more USD lexicon.

---

## 1. FA techniques in use — full inventory

The verdicts are mine. `Shipped/live` means it runs today; anything feeding only *confidence* (never direction) is marked "conf-only".

### 1a. Scheduled-release analysis (the engine's strongest family)

| # | Technique | Where | How it's implemented | Verdict |
|---|---|---|---|---|
| T1 | **Consensus-surprise analysis** | `data_layer/calendar_feed.py:164` (`usd_surprise_score`), `webapp/scoring_service.py:31` | `tanh(3 × (actual − forecast) / abs(forecast))`, falling back to the absolute diff when the forecast ≈ 0. It feeds the essence gauge directly and every precursor contribution | Right technique, wrong scaling — see §2.2 |
| T2 | **Indicator polarity mapping** | `config/settings.py:501` `EVENT_SURPRISE_DIRECTION` | 19 titles tagged `higher_bullish`/`higher_bearish` | Sound. Keyed by title only, with no country (§2.3) |
| T3 | **Leading-indicator / precursor chains** | `settings.py:415` `EVENT_INFLUENCE_LINKS`, `scoring/probability_engine.py:352` | Hand-curated graph (ADP→NFP, PPI→CPI, CPI→PCE, NFP/CPI/PCE→FOMC …), 72 h decay, plus a conflict dampener when precursors disagree | Right idea. The per-link weights (0.20–0.90) are **authored but not consumed**: every precursor gets the flat `PRECURSOR_TRUST_WEIGHT=0.9`, so JOLTS→NFP (authored 0.40) votes as hard as ADP→NFP (0.90). `[Certain]` — the settings comment at line 408 says so |
| T4 | **Nowcast-based consensus checking (Tier 1)** | scheduled `tier1-multi-event-autoresearch` task; `tier1_predictions` table | Cleveland Fed CPI nowcast, GDPNow, CME FedWatch, ISM Prices Paid, jobless claims, etc. These are read via WebSearch and turned into a `predicted_direction` by LLM/human judgment | Institutional-grade inputs, but not reproducible (judgment, not formula), and n is tiny (3 real cases, 1 wrong at "Certain") |
| T5 | **Market-implied expectations** | `data_layer/kalshi_feed.py`, trust 0.95, open-interest floor | Prediction-market price on the exact print, US events only | The best single input in the system. It covers only ~16 US titles |
| T6 | **Preview ("whisper") inference** | `scoring/print_direction.py`, `PRINT_SURPRISE_LEXICON` | Phrase counts ("hotter than expected", "soft jobs report") → higher/lower call, trust 0.5 | Weak. Phrase-based, and it shares the lexicon's blind spots |
| T7 | **Base-rate / beat-miss streak prior** | `webapp/trend.py`, trust 0.3, ≥3 occurrences | The event's own historical beat/miss pattern | Defensible as a weak prior. The echo-chamber risk was already flagged (SWOT T3) |
| T8 | **Sub-reading consolidation** | `webapp/reconciliation.py`, Tier 1 prompt's consolidation section | Strict unanimity across co-released titles; a manual "which sub-reading surprised more vs its own volatility" heuristic | The manual heuristic is the right idea. It's the standardized-surprise concept that T1 doesn't use |
| T9 | **Event-impact relevance and magnitude grids** | `data_layer/event_symbol_relevance.py`, `event_symbol_magnitude.py` | 9 events × 12 symbols, hand-cited, LOW/MED/HIGH tiers. Used only to downgrade Tier 1 confidence | Event-study output, but static and literature-cited rather than calibrated from the engine's own outcome DB |

### 1b. News and narrative analysis

| # | Technique | Where | How it's implemented | Verdict |
|---|---|---|---|---|
| T10 | **News sentiment** | `scoring/probability_engine.py:202`, `scoring/sentiment.py`, `finbert_sentiment.py`, `llm_sentiment.py` | Vendor-native → FinBERT (default on) → Claude (opt-in, ambiguous only) → keyword lexicon, all on one USD axis | **Entity-blind** (§2.1). FinBERT doesn't discount hedged language (the repo's own 2026-09-11 Batch 8 finding) |
| T11 | Source-credibility weighting | `settings.py:293` | Reuters 0.85 … Investing.com 0.55 | Reasonable, but uncalibrated |
| T12 | Information decay | `TIME_DECAY_HALF_LIFE_MINUTES=360` (precursors 72 h) | Exponential decay | Reasonable, but uncalibrated |
| T13 | Redundancy / novelty discount | `probability_engine.py:295` | Articles within 90 min whose matched terms overlap by ≥0.6 Jaccard are down-weighted ×0.3 | A crude novelty score. It operates on lexicon terms, not on the story/entity |
| T14 | Narrative-shift detection | `probability_engine.py:851` | Last 6 h vs older, opposite signs → flag | Good practice. It surfaces a shift instead of averaging it away |
| T15 | Topic relevance filtering | `settings.py:714`, `data_layer/event_context.py:75` | Substring keyword list per title, single-stock-blurb filter, fail-closed for uncurated titles | This is where §2.1 leaks in. FOMC keywords include bare `"central bank"`, `"rate cut"`, `"rate hike"`, `"monetary policy"` |
| T16 | **Central-bank communication analysis** | — (only lexicon words `hawkish`/`dovish`/`rate hike`…) | No stance model, no change-vs-prior-statement read, no CB attribution | **Missing.** N2 from the 2026-09-02 review is still unbuilt `[Certain]` — I grepped for any prior-statement or guidance-delta logic and found none |

### 1c. Intermarket and positioning cross-checks (all confidence-only, none can set direction)

| # | Technique | Where | Implementation | Verdict |
|---|---|---|---|---|
| T17 | Dollar and real-yield backdrop | `data_layer/macro_backdrop.py` | FRED DTWEXBGS (broad dollar) and DFII10 (10y real) 10-day trends; disagreement → confidence ×0.7 | Right check. US-only: there's no foreign yield, so no **differential** |
| T18 | Oil as an inflation proxy, plus oil-shock flag | same | WTI 10-day trend as the lowest-priority lean; a ≥4% single-day move → ×0.8 | Fine for USD. Ignores oil's *currency-specific* sign (JPY importer vs CAD/NOK exporter) |
| T19 | Equity risk-sentiment check | same, `probability_engine.py:720` | S&P 500 10-day trend vs an index read → ×0.7 | Single proxy. No VIX, credit spreads or cross-asset breadth |
| T20 | Positioning / crowding | `data_layer/cot_positioning.py` | CFTC TFF leveraged funds in **USD Index futures**, 52-week percentile, top/bottom 15% aligned → ×0.85 | Uses the wrong contract for the primary instrument. No **COMEX gold** managed-money COT and no JPY futures COT. For an XAUUSD-first engine, gold positioning is the standard crowding read |
| T21 | Precursor-chain conflict | `probability_engine.py:786` | Linked precursors disagree → ×0.75 | Good |

### 1d. Event risk (unscheduled)

| # | Technique | Where | Implementation | Verdict |
|---|---|---|---|---|
| T22 | **Statistical anomaly detection** | `data_layer/discovery_detector.py`, `exogenous_shocks` table, `data_layer/exposure.py` | A 2σ daily move vs a 20-day baseline on DXY / UST bond / XAU / US30, calendar-gated, LLM-classified into 8 categories, then a one-tier Tier 1 confidence downgrade. The exposure table has a single real entry | Sound design. All four series are USD-complex, so a yen or euro shock that doesn't move DXY by 2σ is invisible |
| T23 | **Real-time shock alerting** | `alerting/` (triage → hard rules → Haiku/Llama → symbol relevance → lean table) | 6 categories, 23 hard rules, severity and polarity from the LLM, a hand-written lean table. Alert text only, never feeds scoring | Good plumbing (latency budget, provider fallback, dedup). The taxonomy has **no country dimension**, no agriculture/food, no FX-intervention ladder, and `trade_policy` reaches only equity indices (§2.4) |

### 1e. Transmission and calibration discipline

| # | Technique | Where | Implementation | Verdict |
|---|---|---|---|---|
| T24 | **Single-axis USD transmission** | `webapp/symbols.py:36` | metal and USD-quote FX = inverse, USD-base FX = direct, index = risk_sentiment ×0.7, cross = N/A | The structural ceiling of the whole engine (§5) |
| T25 | Calibration hygiene | thin-sample caps, confidence sample floor, hysteresis, no-lookahead, Dukascopy outcome grading, `source` provenance tags | — | Better discipline than most retail tools. Keep all of it |

**Scorecard against the five families a professional FX desk triangulates** `[Likely]` (judgment): scheduled-data surprises are covered **deeply** (T1–T9), though mis-scaled. The central-bank reaction function is covered **by vocabulary only** (T16). Rate differentials are **absent**: the engine has a US real yield but no foreign leg. Cross-asset risk is **shallow** (one S&P proxy). Positioning is **shallow and on the wrong contract** for gold. And everything collapses to one USD number.

---

## 2. Defects verified during this audit

### 2.1 Foreign central-bank news is scored with the inverted USD sign — P0 `[Certain]` on the lexicon tier, `[Likely]` on FinBERT

Probe 1 (`scripts/audit_fa_probes.py`, real `_filter_relevant()` and real lexicon):

```text
KEPT usd=-1.00 correct=+ SIGN-INVERTED | ECB signals faster rate cuts as euro zone stalls
KEPT usd=-0.97 correct=+ SIGN-INVERTED | Bank of England delivers surprise rate cut
KEPT usd=+0.98 correct=- SIGN-INVERTED | Bank of Japan hawkish, signals rate hike in December
KEPT usd=+1.00 correct=- SIGN-INVERTED | RBA holds, warns rate hike possible
```

There are two causes. First, `_FOMC_RELEVANCE_KEYWORDS` (`config/settings.py:665`) contains generic terms (`"central bank"`, `"rate cut"`, `"rate hike"`, `"monetary policy"`, `"interest rate decision"`) that match any central bank. Second, `scoring/sentiment.py` treats `rate cut`/`dovish` as USD-bearish regardless of whose rates they are.

FinBERT, the default tier, maps `positive → USD-bullish` with no entity awareness (`scoring/finbert_sentiment.py:15–18`). It couldn't be executed here (no torch), but it has no mechanism that could recover the sign. `[Likely]` it inverts the same way.

Exposure: FOMC Statement, Press Conference, Minutes, Federal Funds Rate and "Fed Chairman Warsh Speaks" scores during any week with an ECB, BoE, BoJ or SNB decision. `[Likely]` that covers most FOMC weeks, since the major CBs cluster.

**Quantify it before fixing it.** Query `top_contributions_json` in the live DB for titles containing ECB, BoE, BoJ, Lagarde, Ueda, Bailey, RBA or SNB on the FOMC-family rows. This mirrors the 2026-09-17 Chipotle/TSMC audit.

### 2.2 The surprise metric isn't comparable across indicators — P0 `[Certain]`

Probe 3, real `usd_surprise_score()`:

```text
USD CPI m/m                      f= 0.2% a= 0.3% -> +0.905
USD CPI y/y                      f= 2.9% a= 3.0% -> +0.103   <- same 0.1pp information, 9x smaller
USD Core PCE Price Index m/m     f= 0.0% a= 0.1% -> +0.291   <- zero-forecast fallback uses raw units
USD Unemployment Rate            f= 4.2% a= 4.3% -> -0.071   <- a market-moving miss scores ~nothing
USD Non-Farm Employment Change   f= 150K a= 200K -> +0.762
USD ISM Manufacturing PMI        f= 49.0 a= 51.0 -> +0.122   <- a 2-point ISM beat barely registers
```

Dividing by the forecast's own level means small-denominator series (m/m inflation) saturate on any miss, while level series (UR, PMI, sentiment, y/y) barely move. The industry standard — Bloomberg ECO and the Citi/Bloomberg surprise indices — is the **standardized surprise**: `(actual − consensus) / σ`, where σ is the historical standard deviation of that series' surprises (or the survey dispersion when it's available). The engine already persists forecast/actual history per title in `event_history`, so σ can be computed locally with no new data source.

### 2.3 Calendar logic is keyed by title, not (country, title) — latent `[Certain]`

The probe's Japanese `CPI m/m` row (0.2% → 0.4%) scores **+0.995 USD**. Live paths are safe today only because `filter_relevant_events()` defaults to `countries=("USD",)` and `webapp/predictions_service.py:237,288` hardcode `country="USD"`. The same keying applies to `EVENT_SURPRISE_DIRECTION`, `EVENT_INFLUENCE_LINKS`, `PRINT_SURPRISE_LEXICON` and `EVENT_RELEVANCE_KEYWORDS_BY_TITLE`. This is the same bug class the 2026-09-03 country-scoping fix closed for precursors. It must be closed for all five dicts *before* any non-USD calendar row is admitted.

### 2.4 Shock alerting can't see non-USD or trade-flow shocks — P1 `[Certain]`

Probe 2, real `triage_article()` and `affected_symbols()`, with XAUUSD/US30/USDJPY/EURUSD/AUDUSD/EURJPY tracked:

```text
matched=False reaches=nothing  | US slows soybean exports to Japan amid shipping dispute
matched=False reaches=nothing  | China halts US soybean purchases in retaliation
matched=False reaches=nothing  | Bank of Japan raises rates to 1%, yen surges
matched=False reaches=nothing  | Japan LNG import bill soars as Hormuz tensions rise
matched=False reaches=nothing  | Iron ore price collapses as China steel output slumps
matched=True  reaches=['US30'] | Tariffs imposed on Japanese autos
```

A BoJ rate hike, one of the largest single JPY catalysts, produces no alert. Tariffs aimed at Japan reach US30 but **not USDJPY**, because `_CATEGORY_SYMBOL_CLASS_CHANNELS["trade_policy"]` (`alerting/symbol_relevance.py:52`) lists only `index_risk`. The LLM schema (`alerting/llm_classify.py`) returns category, severity and polarity, but no **country/currency**. That's why `direction.py` has to fall back to "which central bank is not known, so FX and gold stay mixed".

### 2.5 A live API key is committed — fix outside the engine `[Certain]`

`HANDOVER.md:52` contains the Alpha Vantage key in plain text (first committed in `24be1aa`, pushed to `origin`), next to a sentence saying it was never committed. Rotate the key at Alpha Vantage. Redacting the line doesn't remove it from git history.

---

## 3. Evidence status (unchanged since the last pull)

The latest real accuracy is still the 2026-09-11 snapshot: **73% on 30 directional calls**, 95% CI roughly 55–86%. CPI had 0 calls (filter dilution, since fixed), FOMC Minutes went 0/2, PPI 4/8, and about two-thirds of the sample carries the pre-2026-09-03 precursor contamination caveat. I couldn't re-pull it here. `[Certain]` none of the recommendations below should be read as "expand because the core is proven". The core isn't proven yet, and §2.1–2.2 bias the very sample it's being judged on. Fix those first, then re-pull.

---

## 4. The "soy → Japan → yen" question, answered properly

### 4.1 Why the direct channel is immaterial

| Quantity | Value | Confidence |
|---|---|---|
| Japan soybean imports | ~3.2–3.4 Mt/yr; US ~2.2 Mt (68.7%) in 2023 | `[Likely]` — Nippon.com / Iowa Soybean Assn., secondary sources disagree on the 2025 US share |
| Value of US soy to Japan | ~US$1bn/yr (2.2 Mt × ~$450/t landed) | `[Likely]` — my arithmetic, price assumption not sourced |
| Japan total imports (2025) | ~US$755bn | `[Likely]` — worldstopexports, one source |
| Share of import bill | ~0.15% | `[Likely]` — derived |
| USDJPY spot turnover | order of US$1tn/day | `[Likely]` — BIS Triennial order of magnitude, not re-verified this session |
| Energy (mineral fuels) share of Japan's imports | roughly a fifth to a quarter | `[Likely]` — not re-verified against MoF data this session |

A soy disruption is about **two orders of magnitude** smaller than an energy-price move as a terms-of-trade input to the yen. A soy story deserves JPY attention only when it signals something larger: retaliation in a US–Japan or US–China trade dispute, a shipping-lane disruption that also hits energy, or a food-inflation impulse large enough to shift BoJ expectations. The engine needs to be able to tell those cases apart. Hard-coding "soy → JPY" wouldn't do that.

### 4.2 What actually moves JPY, and whether the engine sees it

| JPY driver | Mechanism | Engine today |
|---|---|---|
| US–Japan rate differential (2y and 10y) | Carry. The dominant medium-term driver `[Likely]` | ❌ No JGB yield anywhere |
| BoJ policy and guidance | Policy-rate path (BoJ at ~1% after hikes, per Aug-2026 reporting) | ❌ Not in the calendar, not in alerting (Probe 2) |
| MoF intervention | A verbal ladder ("watching with a sense of urgency" → "won't rule out any options" → rate checks → intervention). ¥11.7tn was spent Apr–May 2026, then a reported US-coordinated action in Aug 2026 | ❌ One generic phrase (`"intervenes in currency market"`). No ladder, no speed-of-move trigger |
| Energy terms of trade | Japan imports nearly all its oil and LNG. Oil up → trade deficit wider → JPY weaker | ❌ The engine reads oil only as a *USD-bullish* inflation proxy (T18). For USDJPY the sign it needs is "JPY-bearish" |
| Safe-haven / carry unwind | Risk-off → yen-short unwinds → JPY up, often violently | ⚠️ Only an S&P 10-day trend, and only applied to indices |
| US–Japan trade policy | Tariffs, deals, retaliation → Japan growth/exports → BoJ path | ❌ `trade_policy` never reaches FX (§2.4) |
| Japan scheduled data | Tokyo CPI (leads national CPI), national CPI, Tankan, Shunto wage round, trade balance | ❌ Calendar is USD-only |
| Positioning | JPY futures COT (CFTC TFF, same API already in use) | ❌ Only the USD Index contract |

### 4.3 How an engine *anticipates* events like this

Anticipation isn't keyword detection after the fact. It takes four things the engine doesn't have yet:

1. **A transmission graph with materiality weights.** Each edge is `driver → currency` with a sign, a channel and a weight. Weights start from bilateral trade and commodity-export shares (UN Comtrade/BACI, or a Citi/Macrosynergy-style commodity terms-of-trade index) and are then **calibrated from the engine's own outcome DB**. Soy→JPY gets an edge with a ~0.0015 materiality weight, so the engine can answer "relevant but immaterial" instead of staying silent. LNG→JPY, iron ore→AUD, crude→CAD/NOK, dairy→NZD, gold/PGMs→ZAR and soy→BRL become material edges. This graph is the `Layer1_Event_to_USD` → `Layer2_Asset_Transmission` knowledge base the feature inventory lists as "documented, zero code", generalized from USD-only to per-currency.
2. **Catalyst calendars beyond the Forex Factory macro calendar.** These cover trade-policy deadlines (tariff effective dates, USTR/Section 301 timelines), commodity calendars (USDA WASDE monthly, OPEC+ meetings, EIA weekly), CB meeting calendars for every tracked currency, and Japan-specific items (BoJ meetings, Shunto, Tankan). Anticipation means knowing the date before the headline.
3. **Structured trade-policy event data.** Global Trade Alert tags 75,000+ interventions by implementing and affected jurisdiction and HS code, with impact chains. "US restricts soy exports to Japan" becomes `implementer=USA, affected=JPN, HS=1201`, a row the graph can price, not a headline the lexicon has to guess at. GTA's API needs a key; I didn't confirm pricing.
4. **Leading signals for the non-scheduled ones**, such as the MoF verbal ladder, the speed of USDJPY moves (intervention risk rises with pace, not just level), and country-level geopolitical-risk baselines (Caldara–Iacoviello GPR, 44 countries, free).

---

## 5. Proposed architecture: from a USD engine to a currency-pair engine

```text
 news item / calendar row / market move
            │
            ▼
 [1] ENTITY ATTRIBUTION      who is this about?  -> {country, institution, channel, polarity, materiality}
     (extend alerting/llm_classify.py's schema; rule fast-path for named CBs: ECB/Lagarde, BoJ/Ueda, ...)
            │
            ▼
 [2] PER-CURRENCY AXES       USD, JPY, EUR, GBP, AUD, CAD, CHF, NZD (+ a separate GOLD axis)
     each fed by: standardized surprises, CB-stance model, sentiment, rate differential legs
            │
            ▼
 [3] TRANSMISSION GRAPH      commodity / trade / policy shocks -> currency axes, weight = materiality x calibrated beta
            │
            ▼
 [4] PAIR COMPOSITION        USDJPY = USD - JPY ; EURJPY = EUR - JPY (crosses become scoreable)
                             XAUUSD = -USD + safe_haven + (-real_yield) + gold_specific (CB buying, ETF, COMEX COT)
            │
            ▼
 [5] EXISTING DISCIPLINE     thin-sample caps, confidence floor, hysteresis, provenance, outcome grading -- unchanged
```

Two building blocks. Both are small and testable on their own:

```python
import statistics


def standardized_surprise(actual: float, forecast: float, past_errors: list[float],
                          min_history: int = 8) -> float | None:
    """(actual - forecast) / sigma of this series' own past (actual - forecast). None until enough history."""
    if len(past_errors) < min_history:
        return None
    sigma = statistics.pstdev(past_errors)
    if sigma <= 0:
        return None
    return (actual - forecast) / sigma


def pair_score(base_axis: float, quote_axis: float) -> float:
    """A pair is the strength of its base currency minus the strength of its quote currency."""
    return base_axis - quote_axis
```

`standardized_surprise()` replaces the body of `usd_surprise_score()`. It keeps the existing `tanh` saturation on top, and keeps the current formula as the fallback until `min_history` is reached. `pair_score()` is what lets `classify_symbol()`'s `fx_cross → None` become a real score.

**Sequencing matters.** Ship [1] as a pure fix for §2.1 first (USD-only, no new axes). Then key all config by (country, title) (§2.3). Then add **one** foreign currency end-to-end — JPY, because USDJPY is already in the symbol picker. Generalize only after its outcomes are graded. Adding all eight currencies at once would dilute an evidence base that is still at n=30.

---

## 6. Comparable tools — what they do and what to take from them

| Tool | What it does | Lesson for this engine | Deployable here? |
|---|---|---|---|
| **RavenPack** | News analytics with a 1,200–2,000+ event taxonomy spanning macro, geopolitical and commodity events, with per-entity **relevance** and **novelty** scores. It explicitly targeted FX quant funds | Score every article per entity: *is this about the Fed?* (relevance) and *is this the first report?* (novelty). That fixes §2.1 at the root and upgrades T13 from lexicon-term overlap to story-level novelty | Pattern yes (LLM attribution), data no (paid) |
| **Citi / Bloomberg Economic Surprise Indices** | σ-standardized surprises vs the survey median, weights derived from **FX reaction to a 1σ surprise**, rolling 3-month window, time decay | (a) Standardize (§2.2). (b) Calibrate per-indicator weights from the engine's own Dukascopy outcome grades, not by hand. (c) Build a per-country surprise index, and use **US minus JP** as a USDJPY input | Yes. All the inputs are already in `event_history` |
| **LSEG MarketPsych** | News and social sentiment per **currency and country** (44–45 currencies, 200+ country macro series), incl. currency-specific topics like carry trade and peg instability | Separate axes per currency, plus topic-specific scores (carry, intervention), instead of one sentiment number | Pattern yes, data paid |
| **J.P. Morgan Macrosynergy (JPMaQS)** | Point-in-time "quantamental" indicators across dozens of currency areas, incl. a **commodity terms-of-trade** series per currency, used as an FX signal and as a filter on carry | Terms of trade is the correct generalization of "soy → yen". Weight commodity moves by each currency's export/import basket. Their point-in-time discipline matches this repo's no-lookahead rule | Concept yes; build a free proxy from FRED/Dukascopy prices + Comtrade weights |
| **Trillion Dollar Words / FOMC-RoBERTa** (ACL 2023) | Hawkish/dovish/neutral classifier trained on FOMC statements, minutes and pressers. It beats generic sentiment because "increase" flips meaning with context | Replace FinBERT on central-bank text (closes T16, and plausibly the hedged-language failure FinBERT didn't fix). The same architecture can be trained for BoJ/ECB text later | Yes for personal use. The checkpoint is **CC BY-NC 4.0** (non-commercial) |
| **Permutable AI** | LLM-built macro/geopolitical narrative signals across FX, rates and commodities, incl. "cross-market transmission". Macro policy sentiment indices are benchmarked against the 2y Treasury yield | Validate a sentiment index against the 2y yield (the market's own policy read). If they don't co-move, the sentiment is noise | Pattern yes, data paid. Claims are vendor marketing, unverified |
| **Dataminr** | First-signal event detection from 1M+ public sources. Every alert carries **entity tags and a geo-location** that clients map to their own tickers | Add `country`/`entity` to every shock alert and route by a user-editable country→symbol map instead of the fixed category→class table | Pattern yes, data paid |
| **GDELT 2.0** | Free, 15-minute global event database with CAMEO actor **country codes**, event codes and tone | A free country-tagged event stream for the shock layer. Already listed as "later" in `settings.py:1048`. Watch out: actor codes are ISO-3 but location codes are FIPS-2 | Yes, free |
| **Caldara–Iacoviello GPR** | Monthly geopolitical-risk indices, incl. **country-specific** ones for 44 economies, plus bilateral versions (Banco de España) | A regime baseline: is Japan or the US already in a high-GPR regime? Useful as a confidence modifier in the existing pattern | Yes, free |
| **Global Trade Alert** | 75,000+ trade-policy interventions tagged by implementer, affected country and HS code, with impact chains | The structured feed behind §4.3(3). It turns trade headlines into bilateral rows | API key required; pricing not confirmed |
| **USDA FAS Export Sales** | Weekly US export sales by commodity **and destination** (soy → Japan is literally a row) | The ground-truth source if a soy/ag channel is ever wanted. Per the FAS page, publication paused after the 2025-09-25 report, so check its current status before relying on it `[Guessing]` | Free, no API confirmed |

---

## 7. Prioritised recommendations

Same criteria as prior reviews: (1) correctness first, (2) value against what's tracked *today*, (3) fit with existing patterns.

| # | Item | Fixes | Effort |
|---|---|---|---|
| **P0-1** | **Foreign-CB attribution fix.** Remove the generic terms from `_FOMC_RELEVANCE_KEYWORDS` (or require a Fed-specific co-term), add a foreign-CB exclusion list (ECB/Lagarde, BoE/Bailey, BoJ/Ueda, RBA, SNB, BoC, RBNZ, PBoC), and turn Probe 1 into a regression test. Quantify historical contamination from `top_contributions_json` first | §2.1 | Low |
| **P0-2** | **Standardized surprises.** σ from `event_history` per (country, title), current formula as the fallback below 8 occurrences. Re-run the essence history to see how many past directions change | §2.2 | Low–Medium |
| **P0-3** | **Rotate the Alpha Vantage key**, then redact `HANDOVER.md:52` | §2.5 | Trivial |
| P1-4 | Key all five event dicts by (country, title). Add a test proving a JPY `CPI m/m` row can't reach the USD axis | §2.3 | Medium |
| P1-5 | Wire the influence-link weights that are already authored into precursor trust (`EVENT_INFLUENCE_LINKS` floats → `combined_weight`) | T3 | Low |
| P1-6 | Shock alerting: add `country` and `currency` to the classifier schema. Add BoJ/MoF hard rules and the intervention ladder. Route `trade_policy` to the *targeted country's* currency pair, not just indices | §2.4 | Medium |
| P1-7 | COMEX gold managed-money COT (CFTC Disaggregated report, same Socrata API pattern) alongside the USD Index read | T20 | Low |
| P2-8 | **JPY end-to-end pilot:** JPY calendar rows, US–JGB 2y/10y differential leg, JPY COT, energy terms-of-trade edge, `pair_score()` for USDJPY. Graded by outcome before any second currency is added | §4.2, §5 | High |
| P2-9 | CB-stance model (FOMC-RoBERTa) plus a statement-delta read for FOMC (the 2026-09-02 review's N2, still open) | T16 | Medium |
| P2-10 | Transmission graph as code (Layer1/Layer2 per-currency, Comtrade-weighted, outcome-calibrated) plus catalyst calendars (WASDE, OPEC+, tariff deadlines) | §4.3 | High |

Per the feature inventory's maintenance rule, none of these goes into `docs/feature-inventory-2026-09-11.md` until it's agreed for build.

---

## 8. Limits of this audit

- Accuracy figures are from 2026-09-11 and couldn't be re-pulled (no live DB in this checkout).
- §2.1 is proven on the lexicon tier. The FinBERT inversion is `[Likely]` from its documented mapping, not executed.
- The soy/JPY materiality figures are order-of-magnitude arithmetic on secondary sources. The conclusion (two orders of magnitude below energy) survives a 3× error either way, but the exact percentages don't.
- Vendor descriptions in §6 come mostly from vendors' own materials and aren't independent performance evidence.
- `docs/News_Engine_Causation_Matrix_v2.xlsx` wasn't available, so its Layer1/Layer2 rows weren't re-read for this audit.

---

## Sources

- RavenPack taxonomy and FX focus: [Euromoney — RavenPack targets FX hedgies](https://www.euromoney.com/article/27bjsstsqxhkmh0m11gnq/capital-markets/foreign-exchange-ravenpack-targets-fx-hedgies/), [Celent — RPNA 4.0](https://celent.com/news/501789114), [WatersTechnology — RavenPack eyes FX](https://waterstechnology.com/node/2143983), [WRDS RavenPack](https://wrds-www.wharton.upenn.edu/pages/about/data-vendors/ravenpack/)
- Surprise indices: [M&G — Surprise indices](https://www.mandg.com/investments/professional-investor/en-lu/insights/mandg-insights/latest-insights/2018/03/surprise-indices-a-reminder), [BSI Economics — Economic Surprise Indicator](https://bsi-economics.org/economic-surprise-indicator/), [Bank Underground — rates reacting to data surprises](https://bankunderground.co.uk/2018/01/23/stirred-not-shaken-how-market-interest-rates-have-been-reacting-to-economic-data-surprises/), [CXO Advisory — economic surprise momentum](https://www.cxoadvisory.com/equity-premium/economic-surprise-momentum)
- LSEG MarketPsych: [product page](https://www.lseg.com/en/data-analytics/financial-data/analytics/marketpsych-analytics), [brochure](https://www.lseg.com/content/dam/data-analytics/en_us/documents/brochures/lseg-marketpsych-analytics-brochure.pdf)
- Macrosynergy/JPMaQS: [Terms of trade as FX trading signal](https://macrosynergy.com/?p=43898), [J.P. Morgan Macrosynergy Quantamental System](https://www.jpmorgan.com/insights/global-research/markets/macrosynergy-quantamental-system), [Pure macro FX strategies](https://macrosynergy.com/?p=62268)
- Trillion Dollar Words: [ACL 2023 paper](https://ar5iv.labs.arxiv.org/html/2305.07972), [FOMC-RoBERTa model summary](https://www.promptlayer.com/models/fomc-roberta)
- Permutable AI: [API — macro sentiment, currencies, commodities](https://permutable.ai/api-real-time-macro-sentiment-commodities-currnecies/), [systematic traders](https://permutable.ai/systematic-traders)
- Dataminr: [financial services](https://www.dataminr.com/solutions/financial-services/)
- GDELT: [GDELT Cloud docs](https://docs.gdeltcloud.com/), [event taxonomy](https://docs.gdeltcloud.com/features/event-taxonomy), [events v2 dataset](https://baselight.app/u/gdelt/dataset/events_v2)
- Geopolitical risk: [Iacoviello — country GPR](https://www.matteoiacoviello.com/gpr_country.htm), [Banco de España bilateral GPR](https://www.bde.es/wbe/en/areas-actuacion/analisis-e-investigacion/recursos/indices-de-riesgo-geopolitico-generales-y-bilaterales-para-34-economias-6075d2451c9da91.html)
- Global Trade Alert: [API endpoints](https://globaltradealert.org/api-access/quickstart/gta-endpoints)
- USDA: [FAS Export Sales Reporting Program](https://www.fas.usda.gov/programs/export-sales-reporting-program)
- Japan soy and trade: [Nippon.com — Japan data](https://www.nippon.com/en/japan-data/h02395/), [Iowa Soybean Assn. — US soy in Japan, Dec 2025](https://www.iasoybeans.com/newsroom/article/isr-december-2025-us-soy-finds-steady-ground-in-japan), [World's Top Exports — Japan's top imports](https://www.worldstopexports.com/japans-top-10-imports/4071), [ActionForex — Japan trade data](https://www.actionforex.com/?p=654230)
- JPY drivers / intervention 2026: [WisdomTree — yen intervention buys time](https://www.wisdomtree.com/us/insights/blog/yen-intervention-buys-time-but-the-boj-holds-the-key), [futureuae — yen report](https://futureuae.com/en-US/Mainpage/Report/11210), [XTB — yen falls from 40-year highs](https://www.xtb.com/sca-en/market-analysis/news-and-research/chart-of-the-day-yen-falls-from-40-year-highs-what-s-next-03-08-2026)
