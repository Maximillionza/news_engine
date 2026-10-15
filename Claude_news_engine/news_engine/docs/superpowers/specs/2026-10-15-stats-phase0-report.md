# Stats tab - Phase 0 feasibility report

Date: 2026-10-15. Script: `scripts/stats_phase0_news_input.py` (read-only; opens the live `backtest_log.db` with `mode=ro`). Read this before Task 8.

Bottom line: the January 2026 start for Tier 1 **is achievable for CPI and Core CPI (m/m and y/y)** using the Cleveland Fed's own published nowcast history, which does exist as machine-readable JSON (the spec's "no downloadable archive" was wrong). News input clears the 50% coverage bar under rule R3, but almost all of that coverage comes from the accumulator fallback, not the print call.

## 1. News input coverage

Script output (live DB, 2026-10-15):

```
print calls: {'lower': 2, 'in_line': 38, 'higher': 3}  takes-a-side: 5/43
XAUUSD accumulator calls: {'bearish': 156, 'neutral': 56, 'bullish': 252}  takes-a-side: 408/464
occurrences with an accumulator XAUUSD prediction: 52
```

Print call takes a side in 5 of 43 rows (11.6%), confirming the spec's weakness note. The XAUUSD accumulator takes a side in 408 of 464 rows (87.9%), but those 464 rows are repeated re-scorings of only 52 occurrences.

**Does R3 give a non-zero lean for at least 50% of occurrences since 2026-08-10? Yes.** I extended the script (still read-only, flagged here as requested) to apply R3 per occurrence (title + event time), using the latest row scored at or before the event time, so no post-event rows leak in:

| Population | Non-zero R3 lean |
|---|---|
| all occurrences with any news row (52, includes one not yet held) | 36/52 = 69.2% |
| held already (event time <= now) | 36/51 = 70.6% |
| held and title has an `EVENT_SURPRISE_DIRECTION` entry (the only ones R3 can ever lean on) | 36/41 = 87.8% |

Where the lean comes from (last population): accumulator fallback 35, print call 1, none 5. So R3 in practice is "the accumulator, mapped to a surprise side". The print call almost never decides it.

Things Task 8 must keep in mind:
- Nine titles can never get a lean because they have no surprise map: Core Retail Sales m/m, FOMC Economic Projections, FOMC Meeting Minutes, FOMC Press Conference, FOMC Statement, Fed Chairman Warsh Speaks, Federal Funds Rate, Final GDP q/q, Prelim Benchmark Payrolls Revision. They should show "n/a", not 0.
- "Non-zero" is a low bar. Among the 44 occurrences where the pre-event accumulator took a side, strength `|2p-1|` has median 0.125 and maximum 0.80; 33 of 44 are below 0.2. The news part of Combined will usually be small, even though it is rarely exactly zero.
- Coverage by distinct occurrence is 52 for the whole period (24 titles, Unemployment Claims alone is 9). Per-event-type hit rates will be tiny samples; the spec's "scale from prior occurrences" (`MIN_HISTORY_FOR_SCALE = 3`) will leave most titles without a scale for a while.
- Nine accumulator rows (across 9 occurrences) were scored after their event time; the script excludes them. The Task 8 query must use the same `scored_at_utc <= event_time_utc` guard.

R3 does not need changing on coverage grounds. If the owner wants to revisit it, that needs sign-off before any results are viewed.

## 2. Nowcast history

**Option chosen: (1) exportable history found.** Evidence gathered in the built-in browser on 2026-10-15:

- The page `https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting` has "Download CSV" buttons (ids `btn-NowcastDownload-quarter`, `-month`, `-year`) and loads three public JSON files for its charts. I did **not** click Download CSV and saved no file; I fetched the JSON in page memory only to inspect its structure.
- Endpoints (same-origin GET, no auth, status 200):
  - `https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json` (about 7.6 MB, month-over-month)
  - `.../nowcast_year.json` (about 7.6 MB, year-over-year)
  - `.../nowcast_quarter.json` (about 5.0 MB, quarterly annualised)
- Coverage: monthly and yearly files hold 160 charts, one per reference month, from 2013-7 to 2026-10. The quarterly file holds 54 quarters, 2013:Q3 to 2026:Q4.
- Structure (FusionCharts format): per chart, a `categories` list of as-of dates ("MM/DD", business days) with vertical-line markers naming the release ("CPI Jul", "PCE Jun"), and eight series: CPI, Core CPI, PCE, Core PCE nowcasts (one value per as-of date) plus four "Actual ..." series carrying only the first-release actual, placed on the release date. **The values are by as-of date**, not only final: for example the July 2026 CPI chart has one nowcast per business day from 07/01 to 08/11, then the actual on 08/12.
- The page's dataset metadata lists the three monthly/yearly/quarterly parts under CC BY 4.0 (`https://creativecommons.org/licenses/by/4.0/`), so cite the Cleveland Fed.
- The Cleveland Fed's FAQ states the chart shows the first available release as the actual, and nowcasts updated every business day around 10:00 a.m. Eastern.

Last as-of value before the release (release-day slot holds the actual, so the day before is the last pre-release snapshot), selected checks:

| Release (CPI for) | Last nowcast, as-of | CPI m/m nowcast | CPI m/m actual | Core CPI m/m nowcast | Core actual |
|---|---|---|---|---|---|
| 2026-01-13 (Dec) | 01/12 | 0.205 | 0.307 | 0.216 | 0.239 |
| 2026-03-11 (Feb) | 03/10 | 0.249 | 0.267 | 0.207 | 0.216 |
| 2026-08-12 (Jul) | 08/11 | 0.087 | 0.074 | 0.211 | 0.215 |
| 2026-09-11 (Aug) | 09/10 | 0.359 | 0.396 | 0.203 | 0.290 |
| 2026-10-14 (Sep) | 10/13 | 0.531 | 0.649 | 0.202 | 0.335 |

Every CPI and Core CPI release from 2026-01-13 through 2026-10-14 has a pre-release as-of value, and so does Core PCE for each release in the same window (I checked reference months 2025-10 to 2026-9). Y/y series exist in the yearly file with the same layout (for example Aug 2026 CPI y/y: last nowcast 3.376, actual 3.397).

Honest limits:
- **Point-in-time not proven for older history.** The sources do not say whether past daily values are exactly what was published that day or a later re-run. One independent check supports it for 2026: our own hand-logged note from 2026-09-07/09-11 cites the live tool at +0.36% m/m and 3.38% y/y for August CPI, and the chart's 09/10 values are 0.359 and 3.376. That is one data point. The reconstructed rows should be labelled "Cleveland Fed published history, as-of date", and Task 8 should store the as-of date it used.
- **The Fed's own wording is "first available release"** for the actuals; our `event_history` actuals may differ slightly. Score against our own actual as the spec says.
- **Oct 2025 CPI was never released** (federal shutdown); the Fed notes a special treatment for the Oct 2025 base. This affects y/y nowcasts for the 2025-10 to 2026-10 windows, not the January start for m/m.
- Release-day edge: on the CPI release day the nowcast slot is blank, so "last snapshot before release" is the previous business day, as the spec intends.
- Nowcast exists only for CPI, Core CPI, PCE, Core PCE (m/m, y/y, quarterly). Nothing here helps PPI, NFP, FOMC, GDP, ISM or Retail Sales; those stay hand-logged per spec 6.2.

Option 2 (rebuild from FRED/ALFRED + EIA) is available as a fallback but is not needed. Series pages checked in the browser today: `CPIAUCSL` (ALFRED shows release-date vintages for it), `GASREGW` (EIA weekly regular gasoline, FRED), `DCOILBRENTEU` (EIA daily Brent, FRED). `CPILFESL`, `PCEPI`, `PCEPILFE` were not opened; their IDs are from memory ([Likely]). A rebuild would be an approximation, not the Fed's number.

## 3. Consequence for the backfill start date

The January start is achievable for the nowcast-based Tier 1 events: CPI and Core CPI (m/m and y/y), with the first reconstructed release being 2026-01-13 (December CPI). Core PCE is also covered (releases on 2026-01-22, 02-20, 03-13 and monthly after). It needs no new modelling; Task 8 reads the published JSON and keeps the as-of date per row. Needed adjustments:

1. Spec section 8 says "no downloadable archive"; the owner should correct it with the endpoint finding above.
2. Backfilled rows are `kind='reconstructed'`, label wording "Cleveland Fed published nowcast history (as-of date)", not "reconstructed approximation"; the approximation label applies only if option 2 is ever used.
3. Task 8 should fetch each JSON once, cache the raw file outside the repo or in the DB with a timestamp and hash, and respect CC BY 4.0 attribution in the UI source line. No backfill code was written in this task.
4. PPI, NFP, FOMC, GDP, ISM and Retail Sales have no nowcast equivalent, so they have no backdated Tier 1 before live capture began; the January start applies only to the CPI family (and the Core PCE family if wanted).

Fallback if the owner decides the history is not point-in-time enough: option 3 (backdated Tier 1 starts when live capture began, with the UI saying so). That decision is the owner's; the evidence above is why it is not forced.
