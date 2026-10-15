# Stats tab (Combined / Tier 1 / News Sentiment) — design

Date: 2026-10-15. Status: draft for owner review. Author: Claude, with Masood.
Mockups reviewed with the owner in-session (v1–v3); numbers in them were sample data.

## 1. Purpose

The Stats tab exists to answer one question with evidence: **which predictor is best for news-driven
releases — Tier 1 alone, News sentiment alone, or Tier 1 with a news influence (Combined)?**
It is a measurement instrument, expected to be temporary. Success means that, after a few months,
the owner can read a scoreboard of the three methods (with sample sizes) and decide which to rely on.

Every event shows what the engine expected (forecast, predicted print, and a Buy/Sell market impact
in the style of Shock Alerts), what happened, and whether the call was right.

## 2. Decisions already made (owner)

| # | Decision |
|---|---|
| D1 | Tier 1 score is a mechanical, weighted calculation where a defensible rule exists; events without one are greyed "Not tracked by Tier 1". |
| D2 | Every economic release in the dashboard history gets a row (all 287 titles / 646 occurrences since 2026-01-09). Tier 1 is active only where a rule exists. |
| D3 | Combined = Tier 1 inputs **70%** + News sentiment **30%**. The weight is fixed in advance, never tuned on results, and **revisited on 2027-01-15** with more data. |
| D4 | Combined never has a "Conflicting" state. News is one more weighted input; Combined always lands on one call. |
| D5 | Right/wrong is decided by **direction against the Forecast**, not by closeness of the number. The size of the miss is shown separately. |
| D6 | Year and Month are separate filters (future use). |
| D7 | Tier 1 needs a backdated 2026 history. Months before 2026-08-12 have no news articles; those months are shown with a clear disclaimer and Combined falls back to Tier 1 only. |
| D8 | Percentages are always shown with the count (`8 of 10`); no percentage is shown under 20 scored events. |
| D9 | Chart: line graph of **Forecast, Actual, Predicted** by release month, filter Tier 1 only / News only / **Combined (default)**. Predicted line and dots are green when the call was right, red when wrong. |
| D10 | Oil and gasoline are **not** separate Tier 1 weights for CPI (the Cleveland nowcast already uses them — see §6). Every composite metric gets an information icon listing its components. |

## 3. Scope

In: new top-level **Stats** tab with sub-tabs Combined, Tier 1, News sentiment; read-only service and
API; a frozen table of reconstructed Tier 1 calls; component-breakdown info icons; backfill of
Tier 1 for 2026 where feasible (§8).

Out (v1): trading signals or order logic; changing `predicted_direction` or any live scoring path;
weighting oil/gasoline *shocks* in Tier 1 (§6.3 records the idea); re-tuning the 30% weight;
non-USD events beyond what the dashboard history already holds; editing the Shock Alerts tab.

## 4. Definitions (exact)

For one event occurrence with Forecast `F`, Actual `A`, and a method's Predicted `P`:

- `tol` = one rounding step of the event's published precision (0.1 for CPI m/m; derived per event
  from the number of decimals in `forecast`).
- `side(x) = 0 if |x − F| < tol, +1 if x > F ("hotter/higher/stronger"), −1 if x < F`.
- **Call is Right** iff `side(P) == side(A)`; otherwise **Wrong**. No call (method abstains, missing
  inputs, or event not scoreable) is **No call** — never counted as Right or Wrong.
- Worked example: F 3.8, P 4.0 (hotter), A 3.9 (hotter) → Right; size of miss 0.1 shown beside it.
  P 4.0 and A 3.8 (in line) → Wrong.
- **Size of miss** = `|P − A|`. The scoreboard shows mean miss next to accuracy.
- **Scoreable** = `forecast` and `actual` both present in `event_history`. Events with no numbers
  (speeches, auctions without forecasts) appear in lists as "No forecast — not scoreable".

### 4.1 Method predictions

- **Tier 1** `P1 = nowcast-derived value` (CPI family; §6). Surprise `s1 = P1 − F`.
- **News** `sN = n × scale`, where `n ∈ [−1, +1]` is the news lean (§7) and `scale` is the event's
  median historical `|A − F|`, computed only from occurrences **before** this one (no lookahead).
  The scaling is an assumption and is labelled as such on the chart. `PN = F + sN`.
- **Combined** `S = 0.70·s1 + 0.30·sN`, `PC = F + S`. If news is missing for the occurrence, `S = s1`
  and the row is flagged `news_missing` (so it is excluded from News-only and Combined-vs-News
  comparisons). If Tier 1 is not tracked for the event, Combined is **n/a** (shown as such).
- Market impact (Buy / Sell / No clear lean per tracked symbol) reuses `alerting/direction.py`'s
  lean table pattern, driven by the sign of `S`; same disclaimer: "Typical reaction, not a trade signal."

## 5. UI

Top-level tab **Stats** beside Shock Alerts. Sub-tabs:

**Combined** — (a) brief card for the next release: expected surprise, Buy/Sell per symbol, info icon
for the weighted score; (b) weighted-score panel; (c) filters Event, Year, Month, Method;
(d) the line chart; (e) three-method scoreboard (accuracy, `k of n`, mean miss); (f) table of
Forecast / Predicted / Actual / Right-Wrong per month.

**Tier 1** — filters Year, Month, Source (live and reconstructed / live only / reconstructed only).
Rows: event, date, Tier 1 call, Actual, result. Info icon on hover shows the scoring criteria
(when the event is scored, what the call is). Clicking a tracked row expands its weighted inputs with
readings, weights and the expected outcome. Untracked events: greyed row, "Not tracked by Tier 1".
Rows from the backfill carry a `reconstructed` tag.

**News sentiment** — per event: article count, lean (cool ↔ hot), what the event landed at, match.
Info icon on the lean opens its components (§7).

**Chart rules** — x = release month; y = value of the event's own unit (e.g. CPI m/m %). Lines:
Forecast (dotted grey), Actual (solid), Predicted (dashed). Predicted segments/dots green when Right,
red when Wrong; months with no call are gaps, not zeros. Colour is never the only signal: Right/Wrong
chips repeat it in the table.

**Disclaimers (required text)**
- Selecting any month before 2026-08-12 on News or Combined: "No news articles exist before 12 Aug
  2026. Combined for these months is Tier 1 only."
- Reconstructed rows: "Reconstructed after the fact from the stated rule; not a live call."
- Scoreboard: "Weights fixed at 70/30 until the 2027-01-15 review."

## 6. Tier 1 rule and composition (info icons)

### 6.1 CPI family (headline and core, m/m)
Tier 1 call = **Cleveland Fed nowcast vs Forecast**. Per the Cleveland Fed's own page the nowcast is
built from ten inputs: daily Brent crude (FT/EIA), weekly retail gasoline (EIA), and monthly
seasonally adjusted past inflation — CPI, core CPI, CPI food, CPI food at home, CPI gasoline (BLS),
and PCE, core PCE, PCE food and beverages (BEA). Core CPI nowcasts use only past core CPI.
Because Brent and gasoline are already inputs, they are **not** added as extra weights (that would
count the same oil move twice). Tier 1 therefore carries 100% on the nowcast; the Combined tab
rescales it to 70% and adds news at 30%.

The information icon beside "Cleveland Fed nowcast" lists those ten inputs with their sources.

**Freshness (owner note, 2026-10-15).** The nowcast refreshes daily, but the value *we store* is a
snapshot, and the Monday research task can be days older than a mid-week release, so oil may have
moved since. To keep Tier 1 "close to the event":
- every stored nowcast carries `nowcast_as_of_utc`, shown on the row ("nowcast as of Mon 08:06");
- a second capture runs on the release eve or morning (last nowcast before the release), and the
  **last snapshot before release is the one scored**; earlier snapshots are kept for the record;
- the click-through shows "Brent / gasoline move since the nowcast snapshot" as information at 0%
  weight — this is the owner's "closer to the event" oil and gas view, without double-counting.
Backfilled rows use the last nowcast-equivalent available before the release, with the same timestamp.

### 6.2 Other events
Where the workbook's POC sheet defines a researched indicator set but no numeric rule exists
(PPI, NFP, FOMC, GDP, Core PCE, ISM, Retail Sales), Tier 1 stays the researched, hand-logged call as
today; the click-through lists the indicators by workbook tier with their confidence tags, **no
weights are invented**. Where a numeric rule can later be defended, it replaces this and the row
becomes weighted. Every other event is greyed.

### 6.3 Oil/gas shock idea (recorded, not built)
Owner's intent was oil/gas movement *after the stored nowcast snapshot*. v1 displays it as information
at 0% weight (see Freshness above). Weighting it, or treating a large move as a shock override, needs
its own spec and evidence.

## 7. News input

The news lean `n` comes from the existing article pipeline (`scoring/sentiment`, the print-call and
accumulator predictions). Its information icon lists the components the pipeline already uses:
article sentiment, source trust weighting, time decay, contradiction flag, article count.

**Known weakness (measured 2026-10-15):** of 43 stored print calls, 38 are `in_line`, 3 higher,
2 lower. As built, the news print call rarely takes a side, so News-only and the 30% news part of
Combined will often contribute ~0. The plan must decide, before any results are viewed, whether `n`
uses the print call, the per-symbol accumulator probability (`predictions.probability`), or both;
this is fixed in advance like the weight. This is the largest risk to the stated purpose.

Coverage: article-based predictions exist from 2026-08-10 (858 rows, 24 event titles); print calls
43 rows. Earlier months have no news.

## 8. Backfill of Tier 1 for 2026

Constraints: a call written now for a past print is contaminated by hindsight unless it is produced
by a fixed rule applied to pre-release data. So only rule-based calls are backdated, labelled
`reconstructed`, scored separately from live calls, and stored **frozen**.

Feasibility gate (Phase 0, before anything else is built): the Cleveland Fed page offers an
interactive chart of past nowcasts but **no downloadable archive** (checked 2026-10-15). Options,
in order of preference:
1. find an exportable history (chart data endpoint) of nowcasts by date;
2. rebuild a point-in-time nowcast-equivalent from the same public inputs (Brent, EIA gasoline,
   BLS/BEA vintages from ALFRED) following the published model, labelled "reconstructed
   approximation — not the Fed's own number";
3. if neither is defensible, backdated Tier 1 starts when live capture began and the UI says so.
The January start is **not promised** until Phase 0 reports.

Storage (ruling R1, one table for both live and reconstructed): `tier1_nowcast_snapshots(id,
event_title, event_time_utc, nowcast_value, as_of_utc, source, kind, rule_version, inputs_json,
recorded_at_utc)` in `backtest_log.db`, where `kind` is `live` or `reconstructed`, unique on
`(event_title, event_time_utc, as_of_utc, kind)`. Append-only (`INSERT OR IGNORE`); changing the rule
creates a new `rule_version`/`as_of_utc`, never edits rows. Scoring takes the latest `as_of_utc` at or
before the release, `live` preferred over `reconstructed`.

Live capture going forward: the (enabled) Monday auto-research task must also record the nowcast
number and `nowcast_as_of_utc` as structured fields, not only free text, and a release-eve refresh
must be added (§6.1 Freshness).

## 9. Architecture

- `webapp/stats_service.py` — read-only; joins `event_history`, `predictions`, `print_predictions`,
  `tier1_predictions`, `tier1_reconstructed`, `outcomes`. Pure functions for `side()`, Right/Wrong,
  scale, Combined. Fail-open per row like the History tab.
- `webapp/metric_components.py` — static registry of components per composite metric (nowcast,
  news lean, Combined, each POC indicator set), served to the info icons; source citation per entry.
- Routes: `GET /api/stats/events`, `/api/stats/chart`, `/api/stats/scoreboard`,
  `/api/stats/components/<metric>`. Route-level tests (lesson from the History Tier 1 bug).
- Frontend: `webapp/static/js/stats/` — `chart.js`, `combined.js`, `tier1.js`, `sentiment.js`,
  `info.js`; tab wired in `index.html` / `app.js` like Shock Alerts.
- No writes to live scoring tables; reconstruction is a separate script
  `scripts/backfill_tier1_reconstructed.py`.

## 10. Testing

- Unit: `side()` tolerance cases (including the 3.8/4.0/3.9 example), Right/Wrong, no-call, scale
  without lookahead, Combined with and without news/Tier 1, 20-event percentage suppression.
- Route tests assert served JSON contains every field the JS renders.
- JS tests: chart colouring (green/red/gap), greyed rows, disclaimers per month, info icon content.
- Backfill: re-running is idempotent; a rule change writes a new version; no row references data
  dated after its release.
- Live check in the browser pane at desktop and phone width before declaring done.

## 11. Risks and open items

1. Nowcast history may not be obtainable (§8) — gates the backdated promise.
2. News print calls are 88% `in_line` (§7) — News/Combined may be uninformative until the input is chosen.
3. Small samples: ~10 CPI prints per year per series; the scoreboard shows `k of n` and suppresses
   percentages under 20 scored events, so early readings will be mostly counts.
4. Sentiment scaling `scale` is an assumption and is labelled.
5. Workbook POC sheets are qualitative; "weights" appear only where a rule is defended.

## 12. Phasing for the implementation plan

0. Feasibility: nowcast history; decision on news input source. 1. Backend service, definitions and
tests. 2. Frontend: tab, Tier 1, News, Combined with chart. 3. Reconstructed Tier 1 backfill.
4. Review 2027-01-15: weight and method comparison.
