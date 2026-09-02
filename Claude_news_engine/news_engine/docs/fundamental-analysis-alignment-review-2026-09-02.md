# News Engine — Fundamental Analysis Alignment Review

**Prepared:** 2026-09-02
**Supersedes/extends:** `docs/fundamental-analysis-swot-2026-08-14.md` (that doc's SWOT structure and internal-code findings are not re-derived here — this review confirms what shipped since, then widens the lens to established FX fundamental-analysis practice the prior doc didn't cover).
**Method:** Direct read of `scoring/probability_engine.py`, `data_layer/macro_backdrop.py`, `data_layer/fred_actuals.py`, `data_layer/kalshi_feed.py`, `config/settings.py`, `webapp/scheduler.py`, plus this session's own history, cross-checked against standard institutional FX fundamental-analysis frameworks (rate-differential/carry theory, central-bank reaction functions, cross-asset risk sentiment, positioning data).

---

## 1. What's shipped since 2026-08-14 (verified against current code, not assumed)

The prior SWOT's Priority 0/1 list is almost entirely closed:

| Prior finding | Status | Evidence |
|---|---|---|
| R1 — stale "pending" gauge bug | **Shipped** | Direction hysteresis + recompute logic, this session |
| R2 — FinBERT default-on (was opt-in) | **Shipped** | `config/settings.py:126`: `ENABLE_FINBERT_SENTIMENT` defaults `"1"` now, not `"0"` |
| R3 — thin-sample probability ceiling | **Shipped** | `_apply_thin_sample_cap()`, `scoring/probability_engine.py:534` |
| R4 — Kalshi date-ticketed series incl. FOMC | **Shipped** | `KALSHI_DATE_TICKETED_SERIES_BY_EVENT_TITLE`, `config/settings.py:538` |
| R5 — macro-backdrop cross-check (DXY/real yield) | **Shipped, then extended** | `data_layer/macro_backdrop.py` — DTWEXBGS + DFII10 (2026-08-16), oil/DCOILWTICO added as lowest-priority fallback (2026-08-19) |
| R6 — secondary source for the calendar spine | **Partially shipped** | `data_layer/fred_actuals.py` (2026-08-26) gives FRED as a fallback for the **actual** value specifically — the exact failure mode that triggered it ("missing/late actual values... not a first time occurrence"). The **schedule/forecast spine** (event dates, forecast figures) is still FF-only; you explicitly chose to keep FF rather than replace it this session. |
| W7 — placeholder trust weights uncalibrated | **Still open** | No backtest-driven recalibration yet — correctly gated on accumulated real outcome data, which is still building |
| R7 — EV/Kelly sizing layer | **Not built** | Still a dashboard read, not a sized signal |
| R9 — competing-story/shock flag | **Not built** | No lexicon or flag for "this call may be contaminated by a non-calendar event" |

Also shipped, not in the original SWOT: direction hysteresis (flip-flop damping), the recently-resolved/sort-order display fixes, and — pending merge — Low-impact event context tracking (calendar/history visibility with no gauge, feeding the macro-backdrop read but excluded from scoring).

**Bottom line on the old list:** the three critical flaws (W2/W3/W4) and the biggest design gap (W8/R5) are closed. The engine today is materially closer to a real fundamental-analysis system than it was three weeks ago, and it closed them in the right order (correctness bugs and the independent macro cross-check before sizing/calibration work that depends on trustworthy inputs).

---

## 2. Where it stands against standard FX fundamental-analysis practice

A professional FX fundamental read for a USD pair typically triangulates five families of signal. Mapping the engine against each:

**(a) Scheduled data surprises (forecast vs. actual)** — ✅ well covered. `EVENT_SURPRISE_DIRECTION`, print-direction lexicon, FRED actuals fallback, precursor contributions (ADP→NFP, PPI→CPI). This is the engine's strongest area and matches how a data-driven desk actually trades releases.

**(b) Central-bank reaction function / forward guidance** — ⚠️ partial. FOMC Statement/Press Conference are tracked and now have Kalshi confirmation, but there's no dot-plot delta, no Fed funds futures-implied rate-path read, no parsing of *hawkish/dovish shift relative to the prior statement* (only the current article-sentiment lexicon, which treats "hawkish"/"dovish" as flat vocabulary hits, not a change from the last meeting). `[Likely]` this is the single highest-value gap for FOMC-week accuracy specifically, since institutional FX desks trade the *delta* in guidance, not the guidance's absolute tone.

**(c) Rate differentials / carry** — ⚠️ proxied, not direct. `DFII10` (US real yield) is tracked in isolation. What's actually missing is the **differential** — US real yield *minus* the equivalent for whichever currency is on the other side of the pair. For XAUUSD this matters less (gold has no foreign-currency leg), but it matters a great deal if this engine is ever extended to a real FX pair (EURUSD, GBPUSD) rather than just gold/US30. `[Certain]` — for the two instruments currently tracked, this gap is low-priority; it becomes a hard requirement the moment a currency pair is added.

**(d) Cross-asset risk sentiment (equities, credit spreads, VIX)** — ❌ not covered. US30's `risk_sentiment` mapping treats USD-bearish as a flat proxy for risk-on, dampened by a static 0.7 multiplier — there's no actual equity-market read (SPX trend, VIX level) feeding it. A real risk-on/risk-off read checks multiple asset classes agreeing, not one USD proxy standing in for all of them. This is the same category of gap R5 closed for the dollar/rates axis, just not yet extended to the risk axis.

**(e) Positioning data (COT, options skew)** — ❌ not covered at all. No CFTC Commitment of Traders data, no options-market positioning read. This is a standard fundamental-analysis input (`config/settings.py`/codebase-wide grep confirms zero references) precisely because it answers a question nothing else in the system answers: **is this move already crowded/exhausted, or is positioning still light?** Kalshi (S5 in the prior SWOT) answers "what does the market expect the print to be" — COT answers "how much of that expectation is already positioned for," which is a different and complementary question. A crowded long-USD position ahead of a hawkish-leaning CPI print can produce a "sell the fact" reaction the engine's current inputs would read as bullish-confirming and get backwards.

**(f) Cross-central-bank policy divergence** — ❌ not covered, and structurally out of scope as currently built. The whole engine is USD-directional-axis-only (`aggregate_usd_sentiment`); it has no read on what the ECB/BOJ/BOE are doing. For XAUUSD (priced in USD globally) this matters less. It would matter if the tracked-symbol list ever grows beyond USD-quoted pairs.

---

## 3. Alignment verdict

`[Likely]`, not `[Certain]` — this is a judgment call, not a measurable fact: **the engine is well-aligned with fundamental analysis for what it currently scopes (USD-directional bias into XAUUSD/US30 around scheduled data), and the alignment has materially improved since the last review.** It is not yet a complete fundamental-analysis system in the institutional sense — it has no positioning read (COT), no forward-guidance-delta read, and no genuine cross-asset risk-sentiment check — but none of those gaps contradict anything the system currently does; they're additive, not corrective. That's a materially different situation than 2026-08-14, when W2-W4 were active correctness problems.

---

## 4. New recommendations, ranked

Same ranking criteria as before: (1) fixes a real remaining gap, (2) expected impact on directional accuracy given what's actually traded (XAUUSD/US30 gold/dollar/rates axis), (3) fit with existing architecture.

**N1 — COT positioning as a confidence modifier, not a new directional signal.**
CFTC releases COT data weekly (Friday, for the prior Tuesday) — free, no API key required (cftc.gov, or the `sod-cftc`-style CSV feeds). Don't feed it into the directional axis directly (weekly data is too stale to drive a same-day call); use it the way R5's macro-backdrop read is already used — as a confidence multiplier / extreme-positioning flag. Concretely: if net speculative USD-length is at a multi-month extreme in the direction the engine's other signals agree on, that's a "this move may be crowded, discount confidence" flag, not a confirming one — the opposite of how most of the other signals combine. This is the most direct answer to the one category of professional fundamental analysis totally absent from the system today.

**N2 — FOMC guidance-delta read, not just guidance-presence.**
Currently FOMC Statement/Press Conference get article-sentiment + Kalshi, same as any other event. What's missing is comparing THIS statement's language against the LAST one — a hawkish-relative-to-prior read is a stronger, more standard fundamental signal than an absolute hawkish/dovish tone read. Implementation-wise this is closer to the print-direction lexicon's pattern (compare against a baseline) than a new data source — the baseline is the prior statement's own text, which the engine could store and diff.

**N3 — Extend the macro-backdrop cross-check to a genuine risk-sentiment leg for US30 (closes the gap in (d) above).**
Add an equity-index trend read (S&P 500 or a broad risk proxy, also free via FRED — `SP500` series exists) to `data_layer/macro_backdrop.py` the same way oil was added: lowest-priority, USD-relationship-aware, never overriding the dollar/yield read, but giving US30's `risk_sentiment` mapping an actual cross-asset confirmation instead of a static dampened proxy off the USD axis alone. This is the natural continuation of R5/W8's own architecture, not a new pattern.

**N4 — A lightweight geopolitical/exogenous-shock flag (this is the prior SWOT's parked R9, still open and still relevant).**
Given oil is now tracked as an inflation-expectations proxy, a sudden oil spike disconnected from any scheduled release is itself a usable "something exogenous is happening" signal the engine could surface (not act on) — cheaper to build than a full shock-lexicon and reuses data already being pulled.

**N5 — Rate differentials / cross-central-bank policy divergence.**
Promoted from "not recommended yet" — confirmed in scope on your side: valuable ahead of tracking real currency pairs (EURUSD, GBPUSD, etc.), where it stops being optional. For XAUUSD/US30 alone this has no leg to stand on (no foreign-currency side to differential against); it becomes load-bearing the moment a currency pair is added. Needs: (a) the equivalent real-yield/policy-rate series for each new pair's non-USD currency (ECB deposit rate + Bund real yield for EUR, BOE bank rate + Gilt real yield for GBP, etc. — all free via FRED or the respective central bank's own published series), (b) a genuine differential computed against `DFII10`, not a second isolated read, and (c) a lightweight central-bank reaction-function read per currency (rate-decision surprise, forward guidance tone) mirroring what N2 builds for the Fed. This is the largest single piece of new work on this list — budget it as its own effort once currency-pair tracking is actually being scoped, not bolted on early.

---

## 5. Consolidated priority list

Ordered by (1) value against what's tracked *today*, (2) structural fit, (3) effort. N5 is listed where it will actually matter — gated on currency-pair tracking landing first — not by pretending it's free to build now.

| # | Item | Targets | Effort | Ships value... |
|---|---|---|---|---|
| 1 | **N1 — COT positioning as a confidence modifier** | Positioning gap (zero coverage today) | Low — free weekly CFTC data, slots into the existing confidence-multiplier pattern | Immediately, for XAUUSD/US30 as-is |
| 2 | **N3 — Risk-sentiment leg (equity read) for US30** | Cross-asset risk sentiment gap | Low-Medium — same proven pattern as R5's DXY/real-yield/oil additions, one more FRED series (`SP500`) | Immediately, for US30 specifically |
| 3 | **N4 — Exogenous-shock flag** | Non-calendar shock blind spot (T2/R9, still open) | Low — reuses oil data already pulled, a threshold check not a new source | Immediately, cheap enough to ride with #1 or #2 |
| 4 | **N2 — FOMC forward-guidance delta** | Reaction-function gap | Medium-High — needs a stored prior-statement baseline and a diff mechanism, not just a new pull | Immediately, highest single-event payoff (FOMC) |
| 5 | **N5 — Rate differentials / cross-central-bank divergence** | Structural gap for any future currency pair | High — a new differential-computation layer plus a new data source per currency | **Once currency-pair tracking is being scoped** — sequence this as part of that effort, not before it |

Nothing here is scoped to a plan yet. Say which one (or which cluster) you want taken further and I'll brainstorm/spec it properly before any build — recommend starting with #1-#3 as a batch, since they're independent, low-risk, and all extend patterns the codebase already trusts.
