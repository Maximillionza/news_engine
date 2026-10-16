# Market reaction - Phase 0 feasibility report

Date: 2026-10-16. Script: `scripts/market_reaction_phase0.py` (read-only; opens the live `dashboard.db` with `mode=ro`; writes nothing but a bar cache in the OS temp dir). Run at 07:21 UTC on 2026-10-16. Spec: `2026-10-16-market-reaction-design.md`. Tests: `tests/test_market_reaction_phase0.py` (15 pure-helper tests).

## Bottom line

[Certain] Full history from 2026-01-01 is achievable for the reaction measurement itself: Dukascopy 1-minute bars start 2026-01-01 23:00 UTC on both symbols, earlier than the spec's 2026-01-13 note, and the first USD release in the DB (2026-01-09 13:30 UTC) is covered. Of 201 measurable release minutes, XAUUSD has both bars for 198 (98.5%) and US30 for 190 (94.5%).

What is **not** measurable with the bars as fetched, and will stay "no data" unless the bars change: (1) the 2026-04-03 12:30 UTC Non-Farm Employment Change and Unemployment Rate release - [Likely] because it was Good Friday and markets were closed (inferred from the date, not verified; a genuine Dukascopy data hole is not ruled out) - the only High-or-inferred-High loss; (2) 8 further US30-only release minutes (all Low-impact: 7 API bulletins at 20:30, 1 Fed-speaker slot) - [Likely] inside a daily US30 closure of about 20:15-22:00 UTC, which I saw on only 2 days (2026-09-01 and 09-02) and inferred for the rest, so it is not verified for every date; (3) 2 Low-impact Fed-speaker minutes (09-04 22:00, 09-30 21:10) missing for both symbols - [Guessing] a weekly close / daily break, not verified. The expectation in R12 that no 5-minute window holds another release minute is **not met** on the raw table: 7 windows do, but 5 of them are duplicate calendar rows of one event, only 2 are real pairs of different events.

## 1. Coverage per symbol

Distinct USD release minutes since 2026-01-01: **205** (299 event rows; matches the spec's 205). 201 are measurable now; 4 are on 2026-10-16 and not yet measurable (12:30, 13:15, 18:00, 20:00 UTC). The measurable test is `t + 15 min <= now` (5-minute window plus 10 minutes of vendor latency).

| Symbol | Bars | Range (UTC) | Release minutes with both `t` and `t+5` | Gaps |
|---|---|---|---|---|
| XAUUSD | 280,961 | 2026-01-01 23:00 to 2026-10-16 07:20 | 198/201 = 98.5% | 3 |
| US30 | 271,320 | 2026-01-01 23:00 to 2026-10-16 07:20 | 190/201 = 94.5% | 11 |

A "gap" means the bar at `t` and the bar at `t+5` are both absent (every gap below is missing both; none is a single missing end). Bars are Dukascopy BID, 1 minute, fetched in calendar-month chunks (2 s pause between chunks).

### Full gap list

| Minute (UTC) | XAUUSD | US30 | Events at that minute | Likely cause |
|---|---|---|---|---|
| 2026-04-03 12:30 | gap | gap | Non-Farm Employment Change, Unemployment Rate (both seeded, impact NULL) | Good Friday: markets closed |
| 2026-09-04 22:00 | gap | gap | FOMC Member Goolsbee Speaks (Low) | Friday weekly close / daily break |
| 2026-09-30 21:10 | gap | gap | FOMC Member Goolsbee Speaks (Low) | Daily break |
| 2026-09-01 20:30 | ok | gap | API Weekly Statistical Bulletin (Low) | US30 daily closed window |
| 2026-09-09 20:30 | ok | gap | API Weekly Statistical Bulletin | same |
| 2026-09-15 20:30 | ok | gap | API Weekly Statistical Bulletin | same |
| 2026-09-22 20:30 | ok | gap | API Weekly Statistical Bulletin | same |
| 2026-09-29 20:30 | ok | gap | API Weekly Statistical Bulletin | same |
| 2026-10-06 20:30 | ok | gap | API Weekly Statistical Bulletin | same |
| 2026-10-14 20:30 | ok | gap | API Weekly Statistical Bulletin | same |
| 2026-10-15 20:30 | ok | gap | FOMC Member Hammack Speaks (Low) | same |

[Certain] on the list (it is the script's output). All causes are INFERRED, not verified. [Likely] for the US30 20:30 gaps: US30 has bars 00:00-20:14 and 22:00 onward on 2026-09-01 and 2026-09-02 (nothing 20:15-21:59), but I looked at only those 2 days and extrapolated the closure to the other 7 dates. [Likely] for Good Friday (from the date alone) and [Guessing] for the 21:10 / 22:00 break gaps (from the times alone). A genuine Dukascopy data hole is not ruled out for any of them. Three minutes are gaps in both symbols (04-03, 09-04, 09-30).

Consequence for design [Likely, given the inferred closure]: any release between about 20:15 and 22:00 UTC is probably unmeasurable on US30, which will include every API bulletin and most late Fed speakers; the tab must show "no data" there, not a zero or a miss. This is already the spec's rule (section 4).

Timestamp convention check (one-off, not in the script): for the 17 High-impact releases with complete bars, the largest one-minute jump among `open[t-3..t+4]` fell on the interval `open[t] -> open[t+1]` (the release minute itself) 8 times, on the next minute 4 times, and never on the interval before `t`. [Likely] the bars are start-labelled UTC with no one-minute or one-hour shift, as spec section 4 assumes; 17 events is a small check.

## 2. Overlap windows (R12)

Windows `[t, t+5)` containing another USD release minute: **7** (the spec expected zero). Smallest spacing between consecutive release minutes: 1 minute. [Certain] on the list; the classification below is my reading of the rows.

| Window start (UTC) | Other minute inside | Events | Kind |
|---|---|---|---|
| 2026-09-09 12:14 | 12:15, 12:16 | ADP Weekly Employment Change x3 (ids 29835, 29619, 29620) | duplicate calendar rows |
| 2026-09-09 12:15 | 12:16 | same | duplicate calendar rows |
| 2026-10-06 12:14 | 12:15, 12:16 | ADP Weekly Employment Change x3 (ids 41259, 41089, 41090) | duplicate calendar rows |
| 2026-10-06 12:15 | 12:16 | same | duplicate calendar rows |
| 2026-09-11 17:58 | 18:00 | Federal Budget Balance (ids 30910, 29638) | duplicate calendar rows |
| 2026-09-01 14:00 | 14:04 | ISM Manufacturing PMI (High) + 3 others at 14:00; RCM/TIPP Economic Optimism (Low) at 14:04 | genuine, different events |
| 2026-10-07 17:00 | 17:01 | President Trump Speaks (Medium) at 17:00; 10-y Bond Auction (Low) at 17:01 | genuine, different events |

Five of the seven windows come from one event stored under several times (a later scrape wrote the same title one or two minutes away; the unique key is title plus time, so both rows survive). They are Low-impact (ADP Weekly, Federal Budget Balance), but they also inflate the cluster table below: 5 extra rows, which turn up as separate size-1 clusters (an ADP weekly appears as three clusters instead of one on each of two days). The two genuine overlaps do contain a real confound: the 2026-09-01 ISM release (High, with JOLTS and others) has a Low-impact RCM/TIPP release four minutes later inside its 5-minute window.

Full-table same-title check (read-only, all USD rows in the current table, same title within 10 minutes; run by the controller and confirmed here): 6 pairs in total. ADP Weekly Employment Change 2026-09-09 12:14/12:15/12:16 and 2026-10-06 12:14/12:15/12:16 (4 pairs, 1 minute apart), Federal Budget Balance 2026-09-11 17:58/18:00 (2 minutes), RCM/TIPP Economic Optimism 2026-10-06 14:01/14:10 (9 minutes). All the rows involved are impact Low with no forecast or actual. **Adopted rule: same-title rows within 3 minutes of each other collapse to the earliest row before clustering; the 9-minute RCM/TIPP pair is NOT collapsed.** This evidence covers USD rows in the current table only; other countries and future scrapes were not checked, so the 3-minute rule is a judgement from six pairs, not a proven bound.

Owner's R12 ("this does not happen") holds for ordinary spacing but not for the data as stored. Per R12 no handling is built; these are listed, not handled. Decision for the owner (not made here): the duplicate rows are a calendar-data defect that would be cleaner to fix at the source than to special-case in the reaction rules, but that is outside this task.

## 3. Cluster sizes (spec 4.1)

Past events only (294 of 299 rows; 5 are in the future), 201 clusters (same exact minute), matching the spec's "47 with two or more events" closely (46 here, because one of those 47 is a future minute). Implied lean = `stats_rules.parse_number/tolerance/side` then `stats_methods.market_lean`; "non-mixed" means buy or sell. Counts are identical for XAUUSD and US30 (the symbols differ only in direction, not in whether a lean exists). "Covered" counts only events whose release minute has both bars for that symbol.

| Cluster size | Clusters | Events | Events with non-mixed lean | ... of which covered XAUUSD | ... of which covered US30 |
|---|---|---|---|---|---|
| 1 | 155 | 155 | 21 | 21 | 21 |
| 2 | 20 | 40 | 15 | 13 | 13 |
| 3+ | 26 | 99 | 35 | 35 | 35 |
| Total | 201 | 294 | 71 | 69 | 69 |

Cluster credit class per size, by leaned events in the cluster (identical for both symbols):

| Size | Solo (one leaned) | Agree (2+, same lean) | Conflict (2+, both leans) | No signal (none leaned) |
|---|---|---|---|---|
| 1 | 21 | 0 | 0 | 134 |
| 2 | 1 | 6 | 1 | 12 |
| 3+ | 10 | 6 | 3 | 7 |

[Certain] on counts. Reading it: only 71 of 294 past events (24%) have any implied lean at all, so the leaderboard rests on about 71 scoreable events spread across roughly 40 titles; most titles will sit below the 20-release percentage floor (R11) for a long time. Across clusters of two or more events there are 12 agreements, 4 conflicts and 11 with exactly one leaned event; the conflict case that R4 and R7 care about is therefore rare (4 clusters so far). The size-1 count of 155 includes up to 5 spurious clusters from duplicate rows (section 2); they have no effect on the lean counts unless a duplicate carries a surprise map, which I did not check ([Guessing] they do not, as ADP Weekly and Federal Budget Balance are low-signal titles).

## 4. Baseline sanity (XAUUSD, 12:00-12:59 UTC)

Shared window: **204 weekdays** (2026-01-02 to 2026-10-15), well above the 20 required; both methods read the same bars. "Spec method" is section 4 `typical`: 5-minute windows on 5-minute boundaries, weekdays only, windows starting on a USD release minute excluded, windows missing either bar skipped. The "audit method" is the baseline logic in `scripts/audit_shock_impact.py` (start minutes 00/15/30/45, tolerant `price_at`, release windows not excluded), with its 30-minute window shortened to 5 minutes so it is comparable.

| Method | n windows | Median abs move (USD/oz) | Mean |
|---|---|---|---|
| Spec method (5-min grid, release windows excluded) | 2,393 | **2.544** | 3.542 |
| Spec method, release windows NOT excluded | 2,448 | 2.570 | 3.745 |
| Spec method restricted to the audit's 00/15/30/45 grid | 762 | 2.530 | 3.537 |
| Audit method, shortened to 5-min windows | 816 | **2.625** | 4.144 |
| Audit method as shipped (30-min window; reference only, not comparable) | 816 | 7.060 | 10.410 |

**The two methods nearly agree on the median but not exactly: 2.544 (spec) versus 2.625 (audit, 5-min), a difference of 0.081, i.e. the spec figure is 3.1% lower.** **Only part of this 0.081 gap is isolated by the evidence.** What the runs show: excluding release windows moves the spec median by 0.026 (2.570 to 2.544), and restricting the spec method to the audit's grid moves it to 2.530, i.e. the grid is not the cause. The remaining roughly 0.095 (2.530 versus 2.625) is attributed, not proven, to the audit's inclusion of release windows plus its tolerant `price_at`; the two were never separated. [Likely] the gap is explained by the two known method differences: the audit keeps windows that contain a release (excluding releases lowers the spec median by 0.026 and the mean by 0.20, 55 windows dropped), and the audit's tolerant `price_at` accepts a bar up to 5 minutes away while the spec requires the exact minute. Restricting the spec method to the audit's grid gives 2.530, so the sampling grid is not the cause. I did not isolate the tolerant-lookup effect separately.

Sanity verdict [Likely]: the baseline is internally consistent and in the expected range (a typical gold 5-minute move around 2.5 dollars in the 12:00 UTC hour); the 30-minute audit median of 7.06 is roughly 2.7 times the 5-minute median, plausible for a random-walk-with-fat-tails (square root of 6 is about 2.4). The mean being well above the median in every row (3.5 vs 2.5) confirms fat tails, which is why the spec uses the median. Note the hour mixes US-winter (12:30Z is pre-release) and US-summer data under one baseline, as R13 chose.

## 5. Whether full history from January is achievable

Yes for the reaction table, with these stated shortfalls:

- XAUUSD: 198 of 201 release minutes measurable now; 3 not (04-03 NFP and Unemployment Rate, [Likely] because of Good Friday but not verified, and two Low-impact Fed-speaker slots, [Guessing] in a daily break). The 04-03 NFP is the only gap that touches a High (inferred) release.
- US30: 190 of 201; 11 not, mostly API bulletins at 20:30 UTC, [Likely] while the index is closed (closure seen on only 2 days, inferred for the rest). These recur weekly, so US30 will probably keep a structural "no data" for evening releases.
- Calendar-data defect: 5 duplicate rows (ADP Weekly x2 days, Federal Budget Balance x1) create near-identical releases one to two minutes apart. They do not block the measurement but they will show as separate releases with the same move unless de-duplicated upstream.
- 4 releases dated today (2026-10-16) are not yet measurable; the incremental run will pick them up.
- Bars start 2026-01-01 23:00 UTC, but event history starts 2026-01-09 13:30 UTC, so the effective start is 2026-01-09 (the DB has no earlier USD rows), not a data limit.
- Not checked: bar completeness within release windows beyond the two end bars; bid-versus-mid effects; whether Dukascopy ever revises history (they do not, to my knowledge, [Guessing]).

Stop point per brief: no backfill is run by this task; the owner should review this report before Task 3.
