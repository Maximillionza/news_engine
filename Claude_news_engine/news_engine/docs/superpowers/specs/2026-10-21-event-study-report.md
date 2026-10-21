# B5 event study - report (live data, read-only)

Date: 2026-10-21. Cold study run 22:08-23:19 SAST (20:08-21:19 UTC), warm re-run 23:20 SAST with identical results, against the live `dashboard.db` and `backtest_log.db`, both opened read-only (`mode=ro`). Script: `scripts/event_study_once.py` (nowcast history: `docs/data/cleveland_nowcasts_2026.csv`; with `event_study_metrics.py`, `event_study_groups.py`, `event_study_checks.py`). Plan: `docs/superpowers/plans/2026-10-21-b5-event-study.md`. Spec: `docs/roadmap-2026-10-20.md` section B5 (E1-E4). Outputs (not in the repo): `C:\Users\Masoodt\AppData\Local\Temp\news_engine_event_study\` (`releases.csv`, `members.csv`, `conflicts.csv`, `dipstick.csv`, `summary.json`, `summary.md`, bar cache in `bars\`). All times are SAST unless marked UTC. Prices are Dukascopy BID; gold "$" is the change in the XAUUSD price, 1 $ = 100 pips (4080 -> 4090 = 1000 pips); US30 is in index points.

## 1. Bottom line

[Certain] The sample is small and every answer below is descriptive, not a tested effect: 207 USD release minutes since 2026-01-01, but only 4 conflicting clusters, 16 measurable agreeing clusters and 37 High-impact minutes with gold data.

- **Conflicting releases (question a).** [Certain] There are only 4 conflicting minutes per symbol, all of them NFP mornings, so the mover/anchor feature is **not decidable yet** under the pre-set rule (it needs 10). [Likely] In those 4, gold did not show a clear "spike then pull back": it pulled back in 1 of 4 at 5 minutes and 2 of 4 at 30 minutes, against 4 of 16 and 5 of 16 in agreeing clusters. Gold's 30-minute move followed the NFP headline in 3 of 4.
- **Agreeing releases (question b).** [Likely] Agreeing clusters move far more than single releases (gold first-minute peak 3.5 x the hourly typical move against 1.0 x), but the conflicting clusters moved even more (8.3 x). The size comes from *what* is released (CPI and NFP mornings), not from agreement. Where agreement does matter is direction: gold's 30-minute net went the implied way in 13 of 16 agreeing clusters (7 of 7 when every member pointed the same way), against 10 of 22 for single releases.
- **Typical peak.** [Certain] For High-impact minutes the gold first-minute peak has a median of $14.55 (1455 pips), a 90th percentile of $51 and a maximum of $81 (NFP, 2026-09-04); the median time to that peak is 22 seconds. The claim "$5-10 typical, max $15-20" **does not hold** on size (it holds on speed). Non-High releases are small: median $2.17, 90th percentile $6.49.
- **Chain (E2).** [Likely] Gold's inverse link to the dollar is strong in the 5 minutes after a release: same direction as the engine assumes in 88% of minutes with a real DXY move (n 95) and 100% when DXY moved 5 basis points or more (n 40), correlation -0.87. US30's inverse link is weak: 66% (n 94), correlation -0.28. The release itself pushed DXY the expected way in 78% of directional minutes (n 27).
- **Dipstick (E3).** [Certain] "T-5 days equals final in 17 of 17" is **confirmed** (17 of 17). Mid reference month (T-25 days) the final value was closer to the actual in 8 releases, the earlier value in 2, 7 tied; the call side changed in 2, and both changes moved the call to the right side.
- **Decisions (E4).** Mover/anchor: not decidable yet. B10 grading window: **5 minutes**; threshold: **1.0 x the hourly baseline** (the data's median of 0.53 x is below the floor, so today's `REACTION_MIN_MULTIPLE` stays). Owner's peak claim: does not hold.

## 2. Sample and coverage

| item | n |
|---|---|
| USD release minutes since 2026-01-01 (all already studyable) | 207 |
| minutes with 2+ events | 48 |
| fully computable multi-member: agree / conflict / all in line | 17 / 4 / 2 |
| agree with every member the same way (`all_same`) | 8 |
| single directional / single in line / single unknown | 22 / 2 / 135 |
| partial (some member without a direction) | 25 |
| minutes with a High-impact member | 38 |

[Certain] The dry run reproduces the known sample of 207 minutes and 17 / 4 / 2, with 48 multi-member minutes instead of 47. The audit snapshot predates 2026-10-20 14:15 SAST; since then 5 new release minutes arrived, one of them multi-member (2026-10-20 14:30 Building Permits + Housing Starts, "partial", no actuals yet). The total stays 207 by coincidence: the 3-minute duplicate collapse removes 5 re-stamped rows that the audit counted as their own minutes (ADP Weekly Employment Change on 2026-09-09 and 2026-10-06, three rows each, and Federal Budget Balance on 2026-09-11).

| series | n | measured | no data | 1-second bars | 1-minute fallback |
|---|---|---|---|---|---|
| XAUUSD | 207 | 204 | 3 | 200 | 4 |
| US30 | 207 | 195 | 12 | 191 | 4 |
| DXY | 207 | 201 | 6 | 199 | 2 |

No data: 2026-04-03 14:30 NFP (Good Friday, markets closed) for all three; 2026-09-05 00:00 and 2026-09-30 23:10 (weekly close and daily break); for US30 also 9 crude-inventory minutes at 22:30, inside US30's daily closure. 0 fetch errors; 652 requests on the cold run, 0 on the warm re-run (652 cache hits, identical `releases.csv`).

## 3. E1 (a) - conflicting releases

"First" is the direction of the larger first-minute move (+1 up, -1 down). "Net 5 / 30" is the price change from the release open to 5 / 30 minutes. A member's direction is what its surprise implies for that instrument (+1 up, -1 down, 0 in line). "Spike then pull back" at k minutes = the k-minute net is opposite to the first-minute direction, or more than half of the first-minute peak was given back.

| time (SAST) | symbol | members (impact, implied dir, surprise in rounding steps) | first | net 5 | net 30 | first move followed | 30-min net followed | pull back 5 / 30 |
|---|---|---|---|---|---|---|---|---|
| 2026-03-06 15:30 | XAUUSD | NFP (High, +1, 142); Retail Sales m/m (Medium, -1, 1) | +1 | +$41.55 | +$2.64 | NFP | NFP | no / yes |
| 2026-03-06 15:30 | US30 | same members, US30 dirs NFP +1, Retail Sales -1 | -1 | -74.1 pts | -396.6 pts | Retail Sales | Retail Sales | yes / no |
| 2026-05-08 14:30 | XAUUSD | Avg Hourly Earnings (High, +1, 1); NFP (High, -1, 60); Unemployment Rate (High, 0) | -1 | +$13.22 | +$14.41 | NFP | Avg Hourly Earnings | yes / yes |
| 2026-05-08 14:30 | US30 | same members | +1 | +76.9 pts | +0.9 pts | Avg Hourly Earnings | Avg Hourly Earnings | no / yes |
| 2026-07-02 14:30 | XAUUSD | Avg Hourly Earnings (High, 0); NFP (High, +1, 53); Unemployment Claims (Medium, -1, 5); Unemployment Rate (High, -1, 1) | +1 | +$62.02 | +$52.24 | NFP | NFP | no / no |
| 2026-07-02 14:30 | US30 | same members | +1 | +103.5 pts | +119.3 pts | NFP | NFP | no / no |
| 2026-08-07 14:30 | XAUUSD | Avg Hourly Earnings (High, +1, 2); NFP (High, +1, 106); Unemployment Rate (High, -1, 1) | +1 | +$50.99 | +$52.70 | AHE + NFP | AHE + NFP | no / no |
| 2026-08-07 14:30 | US30 | same members | +1 | -2.5 pts | +23.6 pts | AHE + NFP | AHE + NFP | yes / no |

Mover rules (descriptive only, n = 4 per symbol):

| rule | XAUUSD: 30-min net followed it | US30: 30-min net followed it |
|---|---|---|
| largest surprise in rounding steps wins | 3 of 4 | 2 of 4 |
| higher impact wins (decidable only when one directional member has the top impact) | 1 of 1 | 0 of 1 |
| first-minute direction = 30-min direction | 3 of 4 | 4 of 4 |

[Likely] "Largest surprise in rounding steps" is not a fair contest across titles: NFP's rounding step is 1K jobs, so its surprise is always tens to hundreds of steps against 1-5 for the others. In these 4 clusters it is the same rule as "NFP wins". [Guessing] The US30 map (weak NFP = US30 up, through `risk_sentiment`) may be the wrong sign on NFP days, which would explain US30 "following" Retail Sales on 2026-03-06.

Pull-back rate by class (rows usable at each horizon; n = rows with a first-minute direction):

| class | XAUUSD n | pull back at 5 min | pull back at 30 min | US30 n | pull back at 5 min | pull back at 30 min |
|---|---|---|---|---|---|---|
| conflict | 4 | 1 (25%) | 2 (50%) | 4 | 2 (50%) | 1 (25%) |
| agree | 16 | 4 (25%) | 5 (31%) | 16 | 6 (38%) | 10 (63%) |
| agree, all same way | 7 | 3 (43%) | 2 (29%) | 7 | 2 (29%) | 4 (57%) |
| single directional | 22 | 10 (45%) | 15 (68%) | 22 | 7 (32%) | 10 (45%) |
| single, no direction known | 133 (110 at 30) | 65 (49%) | 55 (50%) | 124 (96 at 30) | 66 (54%) | 54 (56%) |

[Likely] Conflicts do not pull back more than agreeing clusters in a way 4 rows could show; single releases pull back most for gold, because their first-minute spike is small and half of it is easily given back.

## 4. E1 (b) - agreeing releases

Median (25th-75th percentile) in multiples of the hourly typical |5-min move| (`reaction_baselines`, 75th percentile, by UTC hour). `n` is the rows at 1 minute, `n30` at 30 minutes (rows with another release inside the window are dropped). Directional net = 30-min net signed by the implied direction (positive = moved the implied way). Hit = 30-min net in the implied direction.

**XAUUSD**

| class | n | n30 | peak 1 min | peak 5 min | peak 30 min | net 5 | net 30 | directional net 30 | hit at 30 min |
|---|---|---|---|---|---|---|---|---|---|
| single directional | 22 | 22 | 0.98 (0.51-1.51) | 1.50 (1.13-2.43) | 3.01 (2.31-3.82) | 1.00 (0.34-1.50) | 1.45 (0.33-2.10) | -0.04 (-1.69-1.12) | 10 of 22 |
| agree | 16 | 16 | 3.53 (2.25-8.54) | 4.11 (2.43-9.03) | 6.09 (4.49-11.38) | 2.77 (1.82-4.74) | 2.90 (1.96-10.24) | 2.21 (1.08-5.85) | 13 of 16 |
| agree, all same way | 7 | 7 | 2.30 (2.21-6.73) | 3.68 (2.40-7.32) | 5.24 (4.45-8.54) | 3.03 (1.60-4.53) | 2.41 (2.00-3.44) | 2.41 (2.00-3.44) | 7 of 7 |
| conflict | 4 | 4 | 8.31 (5.34-10.57) | 9.72 (6.22-12.59) | 10.92 (7.18-14.54) | 9.02 (5.85-11.81) | 7.32 (2.48-11.51) | - | - |
| all in line | 2 | 2 | 6.61 (4.91-8.30) | 6.95 (5.42-8.47) | 7.09 (5.64-8.55) | 0.94 (0.68-1.20) | 2.84 (2.57-3.10) | - | - |
| single in line | 2 | 2 | 1.58 (1.04-2.11) | 2.29 (1.71-2.87) | 4.36 (2.97-5.76) | 1.98 (1.28-2.68) | 3.38 (1.90-4.86) | - | - |
| partial | 25 | 20 | 1.00 (0.44-1.51) | 1.55 (1.13-3.71) | 2.95 (2.08-5.30) | 1.33 (0.55-2.99) | 1.72 (0.91-3.62) | - | - |
| single, no direction known | 133 | 110 | 0.37 (0.28-0.60) | 0.82 (0.58-1.21) | 1.99 (1.41-2.82) | 0.45 (0.24-0.81) | 1.10 (0.48-2.00) | - | - |

**US30**

| class | n | n30 | peak 1 min | peak 5 min | peak 30 min | net 5 | net 30 | directional net 30 | hit at 30 min |
|---|---|---|---|---|---|---|---|---|---|
| single directional | 22 | 22 | 0.66 (0.49-0.98) | 1.30 (0.94-2.37) | 2.70 (2.01-4.15) | 1.11 (0.51-1.71) | 1.93 (0.95-2.93) | 0.18 (-1.38-2.27) | 12 of 22 |
| agree | 16 | 16 | 3.20 (1.94-3.80) | 4.14 (2.70-5.26) | 5.27 (3.12-7.76) | 2.75 (1.85-4.33) | 2.67 (0.54-6.20) | 0.28 (-3.20-2.06) | 10 of 16 |
| agree, all same way | 7 | 7 | 2.74 (2.12-3.70) | 3.74 (2.64-4.14) | 3.74 (2.91-6.46) | 2.35 (1.53-3.33) | 1.38 (0.47-5.86) | 0.33 (-2.47-1.00) | 4 of 7 |
| conflict | 4 | 4 | 3.85 (2.61-5.02) | 4.06 (2.92-5.09) | 6.21 (3.91-8.91) | 2.55 (1.45-3.48) | 2.97 (0.75-6.26) | - | - |
| all in line | 2 | 2 | 3.64 (3.25-4.03) | 4.57 (4.50-4.65) | 5.26 (4.84-5.68) | 2.67 (2.01-3.33) | 3.28 (1.94-4.62) | - | - |
| single in line | 2 | 2 | 1.42 (0.98-1.87) | 1.86 (1.34-2.38) | 3.92 (2.98-4.87) | 1.78 (1.23-2.32) | 2.85 (2.42-3.27) | - | - |
| partial | 25 | 20 | 0.75 (0.51-1.85) | 1.45 (0.98-3.80) | 3.46 (2.49-6.42) | 1.04 (0.32-2.37) | 1.49 (1.01-2.65) | - | - |
| single, no direction known | 124 | 101 | 0.47 (0.34-0.76) | 1.02 (0.76-1.60) | 2.66 (1.85-3.67) | 0.59 (0.29-1.17) | 1.49 (0.61-2.65) | - | - |

The agree cluster on 2026-04-03 (Good Friday NFP) has no price data, so agree is 16 here against 17 in the sample.

[Likely] The class comparison is confounded by what is released. 12 of 16 measurable agreeing clusters and all 4 conflicts are High-impact (CPI, PPI, NFP mornings); the 22 single directional releases are 9 High (mostly ISM, claims, ADP, retail sales), 11 Medium and 2 Low. Restricted to High-impact rows, gold's first-minute peak is 0.59 x for singles (n 9), 6.23 x for agree (n 12) and 8.31 x for conflict (n 4): the multi-release mornings dominate whichever way the members point. So "they all agree, so it moves harder" is not supported; "more top-tier numbers at once, so it moves harder" is.

## 5. Typical peak

First-minute peak = the larger of the move up and the move down within the first minute, from the release open. Rows with another release inside the window are dropped (High: one row, 2026-09-01 16:00, excluded at 5 and 30 minutes only).

**XAUUSD ($; pips = $ x 100)**

| group | n | median | p25 | p75 | p90 | max | median time to peak (s) | median time to the 30-min peak (s) |
|---|---|---|---|---|---|---|---|---|
| High | 37 | 14.55 (1455 pips) | 5.92 | 36.26 | 51.16 | 81.34 | 22 | 744 |
| others | 167 | 2.17 (217 pips) | 1.14 | 3.76 | 6.49 | 28.58 | 38 | 1209 |

| group | n | under $5 | $5-10 | $10-15 | $15-20 | $20 or more |
|---|---|---|---|---|---|---|
| High | 37 | 8 | 6 | 6 | 3 | 14 |
| others | 167 | 142 | 17 | 6 | 1 | 1 |

High-impact gold peaks over longer windows: 5 minutes median $21.59 (n 36), 30 minutes median $24.95 (n 36, p90 $66.17, max $96.34).

**US30 (points)**

| group | n | median | p25 | p75 | p90 | max | median time to peak (s) | median time to the 30-min peak (s) |
|---|---|---|---|---|---|---|---|---|
| High | 37 | 50.6 | 28.5 | 106.9 | 156.2 | 190.1 | 34 | 786 |
| others | 158 | 16.5 | 9.6 | 27.8 | 44.4 | 113.1 | 40 | 1263 |

**Verdict on "$5-10 within seconds, max $15-20"** (pre-set rule: High-impact gold, median 1-minute peak within $5-10, p90 at most $20, median time to peak at most 30 s): median $14.55 fails, p90 $51.16 fails, median time 22 s passes. One of three, so the claim **does not hold**. [Likely] The "within seconds" part is right (the first-minute peak comes in a median 22 s, and 13 of 37 within 10 s), but the size is understated by about half at the median and badly at the tail: 14 of 37 High-impact minutes moved $20 or more inside the first minute. [Guessing] The $5-10 range fits a gold price nearer $2,000-2,500; at 2026's $4,000-5,000 the same percentage move is twice as many dollars.

## 6. E2 - event -> USD -> instrument

DXY is Dukascopy `DOLLAR.IDX/USD` over the same 5-minute windows. A "real" DXY move is above the threshold in basis points of the DXY level.

Event -> USD (implied USD direction of single directional and agree minutes vs the DXY 5-minute sign):

| DXY threshold (bp) | n | DXY moved the implied way | share |
|---|---|---|---|
| 0 | 38 | 24 | 63% |
| 2 (headline) | 27 | 21 | 78% |
| 5 | 18 | 15 | 83% |

USD -> instrument (every measured release minute; instrument moves of exactly 0 excluded; "agree" = moved opposite to DXY, as the engine assumes for both):

| symbol | DXY threshold (bp) | n | agree | share |
|---|---|---|---|---|
| XAUUSD | 0 | 195 | 147 | 75% |
| XAUUSD | 2 | 95 | 84 | 88% |
| XAUUSD | 5 | 40 | 40 | 100% |
| US30 | 0 | 188 | 121 | 64% |
| US30 | 2 | 94 | 62 | 66% |
| US30 | 5 | 40 | 30 | 75% |

Slope of the instrument's 5-minute move on DXY's 5-minute move:

| symbol | measure | n | slope | r |
|---|---|---|---|---|
| XAUUSD | $ per DXY point | 198 | -135.2 | -0.88 |
| XAUUSD | % per % (elasticity) | 198 | -3.09 | -0.87 |
| US30 | points per DXY point | 189 | -176.8 | -0.29 |
| US30 | % per % (elasticity) | 189 | -0.34 | -0.28 |

[Likely] Against the engine's assumptions: gold inverse to the dollar is confirmed and strong (a 0.1% DXY move goes with about a 0.3% gold move in the opposite direction). US30 treated as inverse is right in direction but weak: it explains under 10% of US30's 5-minute variation (r squared about 0.08). The engine's 0.7 on US30 is a confidence weight, not a size; as a ratio of sign reliability US30 / gold is 0.66 / 0.88 = 0.75 at the 2 bp headline, close to 0.7, so the weight is not contradicted, but nothing here says US30's size should follow DXY. The event -> USD step is the weaker link for directional calls: 78% at 2 bp on 27 minutes.

## 7. E3 - Cleveland nowcast dipstick

Nowcast history: the cached `nowcasts.csv` (read-only, from the Cleveland Fed's published daily history). "T-25d" = the latest value at or before release minus 25 days; "final" = the latest strictly before the release. Calls use the Stats tolerance rule (within one rounding step of the forecast = in line, 0). "Closer" = which value was nearer the actual.

| release (SAST) | title | T-25d | final | actual | forecast | closer | call T-25d / final / actual |
|---|---|---|---|---|---|---|---|
| 2026-01-13 15:30 | CPI m/m | 0.247 | 0.205 | 0.3 | 0.3 | T-25d | 0 / 0 / 0 |
| 2026-02-13 15:30 | CPI m/m | 0.115 | 0.135 | 0.2 | 0.3 | final | -1 / -1 / -1 |
| 2026-02-13 15:30 | Core CPI m/m | 0.218 | 0.218 | 0.3 | 0.3 | tie | 0 / 0 / 0 |
| 2026-03-11 14:30 | CPI m/m | 0.222 | 0.249 | 0.3 | 0.3 | final | 0 / 0 / 0 |
| 2026-03-11 14:30 | Core CPI m/m | 0.207 | 0.207 | 0.2 | 0.2 | tie | 0 / 0 / 0 |
| 2026-04-10 14:30 | CPI m/m | 0.466 | 0.844 | 0.9 | 1.0 | final | -1 / -1 / -1 |
| 2026-05-12 14:30 | CPI m/m | 0.464 | 0.448 | 0.6 | 0.6 | T-25d | -1 / -1 / 0 |
| 2026-06-10 14:30 | CPI m/m | 0.456 | 0.459 | 0.5 | 0.5 | final | 0 / 0 / 0 |
| 2026-06-10 14:30 | Core CPI m/m | 0.226 | 0.226 | 0.2 | 0.3 | tie | 0 / 0 / -1 |
| 2026-07-14 14:30 | CPI m/m | 0.024 | -0.061 | -0.4 | -0.2 | final | +1 / +1 / -1 |
| 2026-07-14 14:30 | Core CPI m/m | 0.232 | 0.232 | 0.0 | 0.2 | tie | 0 / 0 / -1 |
| 2026-08-12 14:30 | CPI m/m | -0.010 | 0.087 | 0.1 | 0.1 | final | -1 / 0 / 0 |
| 2026-08-12 14:30 | Core CPI m/m | 0.211 | 0.211 | 0.2 | 0.2 | tie | 0 / 0 / 0 |
| 2026-09-11 14:30 | CPI m/m | 0.346 | 0.359 | 0.4 | 0.4 | final | 0 / 0 / 0 |
| 2026-09-11 14:30 | Core CPI m/m | 0.203 | 0.203 | 0.3 | 0.2 | tie | 0 / 0 / +1 |
| 2026-10-14 14:30 | CPI m/m | 0.435 | 0.531 | 0.6 | 0.6 | final | -1 / 0 / 0 |
| 2026-10-14 14:30 | Core CPI m/m | 0.202 | 0.202 | 0.3 | 0.2 | tie | 0 / 0 / +1 |

Summary per lag (n = releases with an early value, a final value and an actual):

| lag (days) | n | final closer | early closer | tie | early = final | call side changed | early call right | final call right |
|---|---|---|---|---|---|---|---|---|
| 5 | 17 | 0 | 0 | 17 | 17 | 0 | 11 | 11 |
| 15 | 17 | 7 | 2 | 8 | 8 | 1 | 10 | 11 |
| 20 | 17 | 7 | 3 | 7 | 7 | 1 | 10 | 11 |
| 25 (headline) | 17 | 8 | 2 | 7 | 7 | 2 | 9 | 11 |

[Certain] T-5 days equals the final value in 17 of 17: the audit's claim is confirmed. Core CPI m/m never changed between T-25d and the release (all 7 ties); CPI m/m changed in all 10 and the final value was nearer the actual in 8 of 10. The two side changes at T-25d (2026-08-12 and 2026-10-14 CPI m/m) both went from "below" to "in line", and the actual printed in line both times. Snapshot cross-check: the final value equals the stored `tier1_nowcast_snapshots` value in 17 of 17, but those 17 rows are the `reconstructed` backfill from the same Cleveland history, so this only checks consistency, not independence.

## 8. E4 - decision memo

Each decision applies the rule fixed in the plan before the data was seen; judgment beyond the rule is labelled.

1. **Mover/anchor: NOT DECIDABLE YET.** Rule: at least 10 conflicting clusters with full data per symbol. Found: 4 per symbol. Re-run when n reaches 10. For the record (no weight under the rule): the "largest surprise wins" rule predicted gold's 30-min net in 3 of 4 and US30's in 2 of 4; the pull-back rate in gold conflicts beat agreeing clusters by 0 points at 5 minutes and 19 points at 30 minutes (needs 20). *Judgment:* at 2026's rate (4 conflicts in 9.5 months, all NFP mornings) n = 10 is more than a year away [Guessing]; backfilling older calendar history (S-07) is the faster way to a decision. Any future mover rule should compare surprises in standard deviations, not rounding steps, or it collapses into "NFP wins".
2. **B10 grading window: 5 minutes.** Rule: the smallest k in {1, 5, 30} where the median High-impact gold peak_k is at least 60% of the median peak_30. Median peak_30 $24.95 (n 36); k = 1: $14.60 = 58.5% (fails, narrowly); k = 5: $21.59 = 86.6% (passes). Computed on the same 36 minutes for every k; using every row usable at each k gives 58.3% and 86.6%, the same answer. *Judgment:* 1 minute misses by 1.5 points on 36 minutes, so the 1-minute window is not far off; 5 minutes is the rule's answer and also what `release_reactions` already measures.
3. **B10 threshold: 1.0 x the hourly baseline (unchanged).** Rule: the median |net_5| in baseline multiples of non-High releases, never below `REACTION_MIN_MULTIPLE` (1.0). Gold: 0.53 (n 166); US30: 0.64 (n 157). Both are below the floor, so the floor applies. For contrast, High-impact |net_5| medians are 2.71 (gold, n 36) and 2.40 (US30, n 36): a 1.0 threshold separates a typical High-impact reaction from a typical quiet release.
4. **Owner's peak claim: DOES NOT HOLD** (1 of 3 conditions; section 5).
5. **Surprises.** (a) Conflicting mornings moved the most of any class. (b) Agreement predicts direction, not size, and only for gold: 13 of 16 agreeing clusters (7 of 7 all-same) moved gold the implied way over 30 minutes, against 10 of 22 single releases, a coin flip; US30 managed 10 of 16. [Likely] that gold result is the most useful thing in this study for the engine, and it rests on 16 minutes. (c) Gold follows the dollar much more tightly than the engine's flat inverse rule implies (elasticity about -3); US30 barely does. (d) Gold's first-minute peak arrives fast (median 22 s), but its 30-minute extreme comes late (median 12.4 minutes for High), so the first spike is usually not the high of the move.

## 9. Method

- **Sources.** Release rows: live `dashboard.db` `event_history`, `country = 'USD'`, 2026-01-01 to the run time, same-title rows within 3 minutes collapsed into the earliest (a later row of the run supplies forecast and actual when the kept row lacks them). Impact: the row's impact, else `EVENT_REGISTRY` (66 rows have none); a minute takes its highest member impact. Baselines: live `backtest_log.db` `reaction_baselines` (quantile 0.75, |5-min move| per UTC hour, period 2026-01-01 to 2026-10-16). Prices: Dukascopy BID, 1-second bars for [t - 2 min, t + 31 min], 1-minute bars when the seconds do not cover the window (8 symbol-minutes plus 2 DXY), source recorded per row.
- **Bar rules.** 1-second bars are sparse (a second with no tick has no bar), so nothing is looked up by exact second and nothing is interpolated. p0 = open of the first bar at or after t (at most 60 s late, else "no data"). Peaks use highs and lows of bars starting in [t, t + k) only. Net at k = close of the last bar starting before t + k, at most 120 s stale, minus p0. Time to peak = seconds from t to the start of the first bar reaching the larger extreme (multiples of 60 on 1-minute bars).
- **Directions.** Surprise side = actual vs forecast with the Stats tolerance (one rounding step of the forecast's precision); to USD through `EVENT_SURPRISE_DIRECTION`, to the instrument through `stats_methods.market_lean`. Classes: single directional / single in line / single unknown; for 2+ members partial (any member without a direction), all in line, conflict (both USD directions present), agree (in-line members do not vote); `all_same` = agree with no in-line member.
- **Contamination rule.** A row enters horizon-k statistics only when the next release minute is at least k minutes later.
- **Units.** Gold $ and pips ($1 = 100 pips); US30 points; baseline multiples divide by the baseline of t's UTC hour.
- **Spot checks.**
  - 2026-10-14 14:30 CPI, XAUUSD, recomputed by hand from the cached 1-second file (1968 bars): p0 4152.455 (bar at 14:30:00); the 60 first-minute bars run from a high of 4153.445 to a low of 4116.191, so up $0.99, down $36.26, peak $36.26 (3626 pips) down, reached 8 s after the release; the last bar before 14:35:00 is 14:34:59 with close 4114.235, so net 5 = -$38.22. All equal the study row.
  - 1-minute fallback, 2026-05-13 14:30 PPI m/m, XAUUSD: Dukascopy returned no 1-second bars (header-only cache file). The 14:30 minute bar (O 4683.555, H 4686.935, L 4675.295) gives up $3.38 and down $8.26, and the 14:34 bar's close 4682.295 gives net 5 = -$1.26. All equal the study row; time to peak is 0 s by construction at minute resolution. The High-impact 2026-07-14 CPI gold row is also a minute fallback, so its time to peak (0 s) is a resolution artefact. It moves the High median time to peak by at most one rank.
  - net 5 vs the stored `release_reactions` move (open of the 1-minute bar at t + 5 minus open at t): 2026-01-09 15:30 gold $14.19 vs $14.17; 2026-01-13 15:30 gold $13.09 vs $13.44; 2026-02-11 15:30 gold -$31.13 vs -$31.58. Over all 204 gold minutes the median gap is $0.07 (max $0.74) with no sign difference; US30 (195 minutes) median gap 0.7 points, one sign difference (2026-09-28 19:30, +0.5 vs -0.4 points). Close, not equal, as expected: the study uses the last 1-second close before t + 5 (about 14:34:59), `release_reactions` the opening tick of the 14:35 minute; p0 is identical.

## 10. Limits

- Small n: 4 conflicts, 16 agreeing clusters and 37 High-impact gold minutes. Every number is descriptive; no significance test is meaningful at this size.
- The classes are confounded with event type (section 4): agree and conflict are almost all CPI, PPI and NFP mornings.
- BID prices only; Dukascopy's feed is not the owner's broker feed (XM), and spread widening at the release is not in BID-only peaks.
- 1-second bars are sparse; 8 symbol-minutes fell back to 1-minute bars, where time to peak is only known to the minute.
- Forecasts are Forex Factory's, used as the consensus.
- The baseline is a typical 5-minute move, so 1-minute and 30-minute values in baseline multiples are scaled by a 5-minute yardstick: compare them across classes, not across horizons.
- The duplicate collapse keeps the earliest row: two ADP Weekly Employment Change minutes are studied from 14:14 instead of 14:15 (Low impact, no actuals; no effect on the High-impact figures).
- 2026-04-03 (Good Friday NFP) has no prices; the US30 daily closure removes 9 crude-inventory minutes for US30.
- The mover rule "largest surprise in rounding steps" is not comparable across titles (section 3).

## 11. Reproduce

From `Claude_news_engine/news_engine` (live databases opened read-only; nothing is written to them or to the repo):

```
python scripts/event_study_once.py --dry-run
python scripts/event_study_once.py
python scripts/event_study_once.py --offline
```

The first prints the sample block only. The second fetches about 650 Dukascopy windows at a 1.5 s pause (about 1 h 10 min cold on 2026-10-21) and writes `releases.csv`, `members.csv`, `conflicts.csv`, `dipstick.csv`, `summary.json` and `summary.md` to `C:\Users\Masoodt\AppData\Local\Temp\news_engine_event_study\`, with the bar cache in `bars\`. Re-runs read the cache (0 requests on 2026-10-21); `--offline` never touches the network. The E3 input is `nowcasts.csv` in the session scratchpad (`--nowcast-csv` to point elsewhere); when it is missing, the summary prints the exact regeneration commands and E3 is reported as missing.
