# USD Recurring Economic Events — Full Map & Compounding Relationships

**Prepared:** 2026-09-02
**Scope (confirmed):** USD-only. Monthly-cadence events, plus the other major recurring cadences whose influence on the monthly events is too significant to omit (FOMC ~8x/year, GDP quarterly, Unemployment Claims + COT weekly).
**Purpose:** A reference map of every recurring USD release worth tracking — including ones the engine does not currently track at any impact tier — and how they causally or informationally connect to each other, so confluence/conflict between them can be reasoned about explicitly rather than left implicit.
**Relation to the engine:** `[Engine: tracked]` = currently scored at Medium+ (dashboard cards). `[Engine: context-only]` = tracked as Low-impact data once `low-impact-context-tracking` merges (Calendar/history, no card). `[Engine: untracked]` = not in the codebase anywhere today (confirmed via grep of `config/settings.py`'s event-title dictionaries).

---

## 1. Labor market

| Event | Cadence | FF impact (typical) | Engine status |
|---|---|---|---|
| Non-Farm Employment Change (NFP) | Monthly, 1st Friday | High | `[Engine: tracked]` |
| Unemployment Rate | Monthly, same release as NFP | High | `[Engine: tracked]` |
| Average Hourly Earnings m/m | Monthly, same release as NFP | High | `[Engine: tracked]` |
| Average Hourly Earnings y/y | Monthly, same release as NFP | Medium | `[Engine: untracked]` |
| Participation Rate | Monthly, same release as NFP | Low | `[Engine: untracked]` |
| ADP Non-Farm Employment Change | Monthly, ~2 days before NFP | Medium | `[Engine: tracked]` |
| JOLTS Job Openings | Monthly, ~5-week lag | Medium | `[Engine: tracked]` |
| JOLTS Quits Rate | Monthly, same release as JOLTS | Low | `[Engine: untracked]` |
| Challenger Job Cuts | Monthly, ~1st business day | Low | `[Engine: untracked]` |
| Unemployment Claims (Initial) | **Weekly**, every Thursday | Medium | `[Engine: tracked]` |
| Continuing Claims | Weekly, same release | Low | `[Engine: untracked]` |
| Nonfarm Productivity q/q (Prelim/Final) | Quarterly | Medium | `[Engine: untracked]` |
| Unit Labor Costs q/q | Quarterly, same release | Medium | `[Engine: untracked]` |

## 2. Inflation

| Event | Cadence | FF impact (typical) | Engine status |
|---|---|---|---|
| CPI m/m | Monthly, mid-month | High | `[Engine: tracked]` |
| CPI y/y | Monthly, same release | High | `[Engine: tracked]` |
| Core CPI m/m | Monthly, same release | High | `[Engine: tracked]` |
| Core CPI y/y | Monthly, same release | High | `[Engine: tracked]` |
| PPI m/m | Monthly, ~1 week after CPI | Medium-High | `[Engine: tracked]` |
| Core PPI m/m | Monthly, same release | Medium | `[Engine: tracked]` |
| Import Prices m/m | Monthly, mid-month | Low-Medium | `[Engine: tracked]` |
| Export Prices m/m | Monthly, same release | Low | `[Engine: untracked]` |
| Core PCE Price Index m/m | Monthly, end of month | High | `[Engine: tracked]` |
| Core PCE Price Index y/y | Monthly, same release | High | `[Engine: untracked]` (title gap — worth adding) |
| Prelim UoM Inflation Expectations | Monthly, mid-month | Low-Medium | `[Engine: untracked]` |

## 3. Growth & output

| Event | Cadence | FF impact (typical) | Engine status |
|---|---|---|---|
| GDP q/q (Advance) | Quarterly | High | `[Engine: untracked]` (title-convention gap — see §5) |
| GDP q/q (Prelim) | Quarterly | High | `[Engine: tracked]` |
| GDP q/q (Final) | Quarterly | Medium | `[Engine: untracked]` |
| GDP Price Index q/q | Quarterly, same release | Low | `[Engine: untracked]` |
| ISM Manufacturing PMI | Monthly, 1st business day | High | `[Engine: tracked]` |
| ISM Manufacturing Prices | Monthly, same release | Medium | `[Engine: tracked]` |
| ISM Manufacturing Employment | Monthly, same release | Low | `[Engine: untracked]` |
| ISM Services PMI | Monthly, ~3rd business day | Medium-High | `[Engine: tracked]` |
| ISM Services Prices | Monthly, same release | Low-Medium | `[Engine: untracked]` |
| S&P Global/Markit Manufacturing PMI (Flash + Final) | Monthly, twice | Low-Medium | `[Engine: untracked]` |
| S&P Global/Markit Services PMI (Flash + Final) | Monthly, twice | Low-Medium | `[Engine: untracked]` |
| Industrial Production m/m | Monthly, mid-month | Medium | `[Engine: untracked]` |
| Capacity Utilization | Monthly, same release | Low | `[Engine: untracked]` |
| Durable Goods Orders m/m | Monthly, ~last week | Medium | `[Engine: untracked]` |
| Core Durable Goods Orders m/m (ex-transport) | Monthly, same release | Medium | `[Engine: untracked]` |
| Factory Orders m/m | Monthly, ~1-month lag | Low | `[Engine: untracked]` |

## 4. Consumer & housing

| Event | Cadence | FF impact (typical) | Engine status |
|---|---|---|---|
| Retail Sales m/m | Monthly, mid-month | Medium | `[Engine: tracked]` |
| Core Retail Sales m/m | Monthly, same release | Medium | `[Engine: untracked]` |
| Personal Income m/m | Monthly, same release as Core PCE | Low-Medium | `[Engine: untracked]` |
| Personal Spending m/m | Monthly, same release | Medium | `[Engine: untracked]` |
| CB Consumer Confidence | Monthly, last Tuesday | Medium | `[Engine: untracked]` |
| Prelim UoM Consumer Sentiment | Monthly, mid-month | Medium | `[Engine: tracked]` |
| Final UoM Consumer Sentiment | Monthly, end of month | Low | `[Engine: untracked]` |
| Housing Starts | Monthly, mid-month | Low-Medium | `[Engine: untracked]` |
| Building Permits | Monthly, same release | Low-Medium | `[Engine: untracked]` |
| Existing Home Sales | Monthly, ~20th | Low-Medium | `[Engine: untracked]` |
| New Home Sales | Monthly, end of month | Low-Medium | `[Engine: untracked]` |
| Pending Home Sales m/m | Monthly, end of month | Low | `[Engine: untracked]` |
| S&P/Case-Shiller Home Price Index y/y | Monthly, ~last Tuesday | Low | `[Engine: untracked]` |

## 5. Trade, inventories & policy

| Event | Cadence | FF impact (typical) | Engine status |
|---|---|---|---|
| Trade Balance | Monthly, ~5-week lag | Low-Medium | `[Engine: untracked]` |
| Wholesale Inventories m/m | Monthly, mid-month | Low | `[Engine: untracked]` |
| Business Inventories m/m | Monthly, mid-month | Low | `[Engine: untracked]` |
| FOMC Statement / Rate Decision | ~8x/year, ~every 6 weeks | High | `[Engine: tracked]` |
| FOMC Press Conference | Same day as Statement | High | `[Engine: tracked]` |
| FOMC Meeting Minutes | ~3 weeks after each meeting | Medium | `[Engine: untracked]` |
| CFTC COT (net speculative USD Index positioning) | **Weekly**, Fridays | N/A — not a scheduled "release" on FF, a positioning report | `[Spec'd, not yet built]` — this session's fundamental-signals-batch spec |

**Title-convention note (§3):** the engine's `EVENT_SURPRISE_DIRECTION`/history dictionaries use `"Prelim GDP q/q"` (confirmed live-matched to Forex Factory's real feed this session) — `"Advance GDP q/q"` was found to never appear on the live feed and was renamed out. If FF's own naming ever adds a genuine "Advance" release ahead of "Prelim," that's a new title requiring its own config entry, not a duplicate of the existing one.

---

## 6. How they connect — precursor chains

These are sequential relationships: an earlier release genuinely shifts the market's expectation for a later one, not just a thematic similarity.

**Labor chain (leads into NFP, in publish order):**
`JOLTS Job Openings` (5-week lag, weakest/earliest precursor — labor *demand*) → `Challenger Job Cuts` (layoff-side, same week as NFP) → `ADP Non-Farm Employment Change` (2 days before, private-payrolls proxy) → **`NFP` + `Unemployment Rate` + `Average Hourly Earnings m/m`** (the release itself, three numbers from one report that must be read together, not separately — see §7). `Unemployment Claims` (weekly, every Thursday all month) is the highest-frequency read in this whole chain — a rising 4-week average of Initial Claims heading into NFP week is often the earliest genuine tell that the month's NFP could miss, well before ADP prints.

**Inflation chain (input costs → consumer prices → Fed's own gauge):**
`ISM Manufacturing/Services Prices Paid` (a forward-looking survey sub-index, published with the PMI) → `Import Prices m/m` → `PPI m/m` / `Core PPI m/m` (producer/input-cost level) → `CPI m/m` / `Core CPI m/m` (consumer-facing, released first each cycle in FF's own calendar despite PPI conceptually leading it) → `Core PCE Price Index m/m` (the Fed's actual preferred gauge, released last each month, different basket weights than CPI — historically tends to confirm CPI's *direction* with a lag more often than it surprises independently, though basket differences, especially healthcare, can produce a genuine divergence).

**Growth/output chain:**
`S&P Global Flash PMI` (mid-month, earliest read) → `ISM Manufacturing PMI` + `ISM Services PMI` (survey-based, forward-looking) → `Industrial Production m/m` (hard output data, coincident/lagging — a PMI/IP divergence is itself a signal: strong PMI with weak IP means sentiment is running ahead of realized output) → `Durable Goods Orders` (business investment intent) → `GDP q/q` (the quarterly scorecard several of the above feed directly: Retail Sales/Personal Spending → Personal Consumption Expenditures component; Durable Goods → Business Investment component; Trade Balance → Net Exports component).

**Consumer/housing chain:**
`CB Consumer Confidence` + `UoM Consumer Sentiment` (soft, survey-based, published mid-month and end-month) → `Retail Sales m/m` (hard spending data) — a persistent divergence (confidence falling while retail sales stay firm, or vice versa) is a standing early-warning flag, not noise to average away. Separately: `Building Permits` (leading) → `Housing Starts` (coincident) → `Existing Home Sales` / `New Home Sales` (lagging, closing-driven) — this whole chain is rate-sensitive and reacts inversely to the engine's existing real-yield read (`DFII10`), so it's a natural extension candidate for the macro-backdrop pattern if housing-sector accuracy is ever prioritized.

**The policy layer sits above all of the above, not beside it:** every release in every chain above is being read by the market *through* the lens of "how does this shift the probability-weighted path to the next FOMC decision." FOMC isn't one more data point to average in — it's the thing all the other monthly data is ultimately informing a forecast of. FOMC Meeting Minutes (3 weeks after each decision) retroactively reveal how the Committee weighted the data that came in between meetings, which recalibrates how the market reads the *next* month's releases.

---

## 7. Compounding effects — confluence, conflict, and modulation

Three distinct ways multiple signals interact, worth keeping conceptually separate (this maps directly onto how the engine's own confidence math already works, and onto the confidence-modifier signals in the fundamental-signals-batch spec):

**(a) Confluence — multiple independent leads agree, raising conviction.**
Example: `ADP` beats + `Challenger Job Cuts` falls + `Initial Claims` trending down into NFP week all point the same direction (labor market strengthening) → NFP consensus itself likely already shifted higher before release, AND a genuine NFP beat on top of that confluence is a stronger, more reliable signal than the same beat arriving with no supporting precursors. This is the "several independent things agree" case the engine's existing agreement×coverage math already rewards for article sentiment — the same logic applies across events, just not wired up that way yet.

**(b) Conflict — signals genuinely disagree, and averaging them is wrong.**
Example: `ISM Manufacturing PMI` contracting while `ISM Services PMI` expands is not noise to smooth over — the US economy is services-heavy, so this is actually the *normal*, non-alarming pattern in a late-cycle expansion; both contracting together is the real recession-probability signal. Averaging the two into "PMI is roughly neutral" would erase the actual information. Same logic for `Personal Income` growing faster than `Personal Spending` (rising savings rate) — this could read as consumer caution (bearish near-term growth) or as fuel for future spending (bullish forward-looking) depending entirely on the surrounding narrative; it should never be silently netted against Retail Sales.

**(c) Modulation — one signal doesn't add directional information, it changes how much the others matter.**
This is the exact mechanic the fundamental-signals-batch spec (COT crowding, equity risk-sentiment, oil shock) formalizes: `COT` positioning doesn't say "up" or "down," it says "how much of the expected reaction is already priced in, and how vulnerable is it to unwind if the print surprises the other way." A textbook-correct hawkish CPI beat, arriving into an already-max-long-USD COT positioning read, can produce a muted or even inverted ("sell the fact") price reaction — the data was right, the positioning context is what determined the outcome. `FOMC`'s policy-reaction-layer role (§6) is the same kind of modulation at a macro scale: it's not a monthly data point competing with the others for weight, it's the frame the others are all being read inside of.

**Net practical implication for scoring design:** confluence (a) is safe to reward with higher confidence (agreement-based). Conflict (b) must be surfaced explicitly, never netted to a false-neutral average — this is exactly why `_detect_contradiction()` and the macro-backdrop disagreement check exist as flags rather than blended averages. Modulation (c) is a multiplier on confidence, not a contribution to the directional average — which is precisely why COT/equity-risk/oil-shock were spec'd as confidence dampeners rather than new directional inputs.

---

## 8. What this means for engine coverage, concretely

Not a build recommendation — this section just states the gap plainly, since that was the point of the exercise:

- **Growth/output (§3)** and **Consumer & housing (§4)** are the two categories with the most untracked-but-real events — Industrial Production, Durable Goods, Housing Starts/Permits/Sales, and the broader confidence/sentiment set are all genuinely recurring, monthly, and currently invisible to the engine at any tier (not even Low-impact context, since `low-impact-context-tracking`'s USD Low+ widen only surfaces whatever titles Forex Factory tags — these titles exist on FF's feed and would already start appearing there once that branch merges, worth confirming live once it does).
- **The precursor chains in §6** are currently informal — the engine has structured precursor contributions for ADP→NFP and PPI→CPI (`PrecursorContribution`, per the prior SWOT's S1) but nothing for the JOLTS/Challenger/Claims labor chain, the ISM Prices Paid→PPI inflation chain, or the housing/growth chains described above.
- **§7's three-way framework (confluence/conflict/modulation)** is a useful lens for evaluating *any* future signal addition, not just this session's batch — a candidate new signal should be classified as one of the three before deciding how to wire it in, rather than defaulting every new idea into "another contribution to average in."

No action items proposed here — say if you want any specific gap from this map (a chain, a category, or a single event) turned into its own brainstorm.
