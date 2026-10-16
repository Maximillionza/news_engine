# Market reaction sub-tab (Stats) — design

Date: 2026-10-16. Status: implemented on branch `market-reaction` (not merged, not deployed), pending the owner's approval to merge and to run the live backfill; owner answers to O1-O3 applied 2026-10-16, 75th-percentile ruling applied 2026-10-16. Author: Claude, with Masood.
Builds on the Stats tab (`docs/superpowers/specs/2026-10-15-stats-tab-design.md`). The layout mockup was approved in-session ("happy with the mockup for now"); numbers in it were sample data.

## 1. Purpose

Answer one question with evidence: **which releases actually move the market, and do they move it the way the surprise (or our call) implied?**

For each release, record how XAUUSD and US30 moved in the 5 minutes after it. Over many releases, a leaderboard shows which event types move the market consistently. Several releases often land in the same minute, so the tab also says who gets the credit when they agree and when they conflict.

## 2. Decisions already made (owner, 2026-10-16)

| # | Decision |
|---|---|
| R1 | **5-minute window only.** 30 minutes is too late to read a reaction; it is not shown. |
| R2 | "Moved the market" = the instrument moved by more than a typical 5-minute move at that time of day. Anything smaller is **no reaction**. Amended 2026-10-16 (owner): "typical" is the **75th percentile** of ordinary 5-minute moves for that instrument and UTC hour, not the median (the median made ~50% of ordinary windows count as a reaction; the 75th makes chance ~25%). |
| R3 | Score two things: (a) **surprise-implied direction** (actual vs forecast -> USD direction -> instrument direction), which works for every release since January; (b) **engine calls** (Tier 1 / News / Combined) wherever they exist. |
| R4 | Same-minute releases form a **cluster**. Agreeing events share credit; conflicting events are "matched the move" or "overruled"; a release that is alone gets solo credit. |
| R5 | Every tracked symbol, **gold (XAUUSD) by default**. |
| R6 | A fourth Stats sub-tab, **Market reaction**: event leaderboard + per-event drill-down. |
| R7 | Each event keeps **its own call**; the cluster verdict is shown beside it and never erases an individual score. |
| R8 | **Impact filter**: multi-select chips (High, Medium, Low, Unrated), **High selected by default**. |
| R9 | Impact filter applies to **all four** Stats sub-tabs (owner's assumed-agreed default; stated as an assumption). |
| R11 | **Percentage floor 20**, same as the rest of Stats: no percentage is shown for an event type with fewer than 20 releases (counts are always shown). Event types under 8 releases also carry a "few releases" tag. (Owner: "Match 20".) |
| R12 | **No overlap handling.** Releases are normally about 30 minutes apart, so a 5-minute window does not contain another release minute; no overlap flag or exclusion is built. Phase 0 counts any window that does contain another release minute and reports it; if any exist they are listed, not silently handled. (Owner: "this does not happen".) |
| R13 | **One baseline per UTC hour**; no split by US daylight-saving period. (Owner: "don't split".) |
| R10 | Releases with no impact tag **inherit the tag from the same event title** (CPI is High wherever it is tagged) and appear under **Unrated (inferred)**, switched on by default together with High (assumed-agreed default). |

## 3. Scope

In: price-reaction measurement for USD events in `event_history`; a baseline of typical 5-minute moves; cluster credit rules; leaderboard and drill-down UI; impact filter across Stats; a compute script plus an append-only table; read-only service and routes.

Out (v1): trading signals or order logic; the 30-minute window; non-USD events; changes to live scoring or to `predicted_direction`; any report/export (parked, see memory note `news-engine-stats-backlog`); intraday windows other than 5 minutes; attributing a move to one event inside a cluster beyond the credit rules.

## 4. Definitions (exact)

For release minute `t` (UTC), instrument `S`:
- `p0` = open of the 1-minute bar starting at `t`; `p5` = open of the 1-minute bar starting at `t + 5 min`. `move = p5 − p0` (price units); `move_pct = move / p0`. A missing bar at either end -> **no data** (never interpolated).
- `typical(S, hour)` = **75th percentile (`REACTION_BASELINE_QUANTILE` = 0.75, linear interpolation) of |5-minute move|** over every 5-minute window starting on a 5-minute boundary within that UTC hour, on all weekdays in the baseline period, **excluding any window whose start minute is a USD release minute** (every raw USD `event_history` minute, including same-title duplicates that are collapsed for judging). The release's own day is not excluded: one baseline row per hour cannot do that, and it is about 0.5% of windows. Computed from the same 1-minute bars; the quantile is stored on every baseline and reaction row. (Descriptive statistic over the whole period, not a prediction; stated as such.)
- **Reaction**: `|move| > typical × REACTION_MIN_MULTIPLE` (constant, default 1.0). Otherwise **no reaction**.
- **Market direction**: `buy` if `move > 0`, `sell` if `move < 0` (only when there is a reaction).
- **Implied lean** for event `E` on `S`: `side(actual vs forecast)` per the Stats rules (one-rounding-step tolerance), mapped through `EVENT_SURPRISE_DIRECTION` and `classify_symbol(S).usd_relationship` exactly as `stats_methods.market_lean` does -> `buy` / `sell` / `mixed`. `mixed` (in line, no surprise map, or no numbers) = **no signal**; such an event is listed but never scored.
- **Engine lean** for `E` on `S`: the lean of the Tier 1 / News / Combined predicted value (`market_lean` on the sign of predicted − forecast), when that call exists.
- **Hit** (single signal): lean == market direction, with a reaction. **Miss**: lean opposite to market direction, with a reaction. **No reaction**: no reaction at all (counted separately, never as a miss).

### 4.1 Clusters and credit

A **cluster** is every USD release in `event_history` with the same `event_time_utc` (exact minute), **regardless of the impact filter** — the market does not apply the filter. The filter only controls which events are listed and counted; clusters show "+N lower-impact events at the same time" when some are hidden.

Within a cluster, for instrument `S`, consider the events with a lean (`buy`/`sell`):
- **Solo**: exactly one leaned event -> it gets Hit / Miss / No reaction directly.
- **Agree** (two or more leaned events, all the same lean): each gets **Shared hit** or **Shared miss** (or No reaction). Shared credit is never added to "solo" counts and is labelled shared everywhere.
- **Conflict** (leaned events with both `buy` and `sell`): with a reaction, each event is **Matched the move** (its lean == market direction) or **Overruled** (opposite); with no reaction, all are No reaction.
- Events without a lean are shown as "no signal" and take no credit in any case.

A conflict day proves nothing alone; credit only means something when tallied per event over many releases.

### 4.2 Leaderboard metrics (per event title, per instrument, over the filtered rows)

`releases` (with a lean), `solo`, `shared`, `in conflict`; `reaction rate` = releases with a reaction / releases; `direction hit rate` = (hits + shared hits + matched) / releases with a reaction; `avg 5-min move` (mean of `move_pct` signed in the implied direction); `engine call right` = Right / scored engine calls for that event (the Stats rule), `n/a` where no calls exist. Every rate is shown with its count (`k of n`). Titles with fewer than 8 releases carry a "few releases" tag. Percentages are hidden under 20 releases (R11); counts are always shown. A Wilson 95% interval is shown on hover for hit and reaction rates.

## 5. Impact handling

`event_history.impact` is `High` / `Medium` / `Low` / NULL. At spec time 66 of 299 USD rows are NULL (seeded Jan–Aug history, including CPI, NFP, PPI, Core CPI). **Effective impact** = the row's own tag, else the **most common tag for the same event title** among tagged rows, else `Unrated`. A row whose tag was inferred carries `impact_inferred = true` and is shown under the chip "Unrated (inferred)". Chips: High, Medium, Low, Unrated (inferred). Default selection: **High + Unrated (inferred)** (so seeded CPI/NFP history is not silently hidden). The filter is a query parameter `impacts=High,Unrated` accepted by `/api/stats/events`, `/api/stats/chart`, `/api/stats/scoreboard` and the new reaction routes, and applied by the service before counting; the sub-tabs share one control.

## 6. Data and storage

- **Price source:** Dukascopy 1-minute bars (`dukascopy_python`, already used by `data_layer/dukascopy_feed.py` and the Shock-alert audit). Checked 2026-10-16: 1-minute bars for XAUUSD and US30 exist back to 2026-01-13 (61 bars for a one-hour window on both). A **Phase 0** check must confirm coverage for every release minute (205 distinct USD release minutes since 2026-01-09, 47 with two or more events) and list gaps.
- **Never fetched at request time.** A compute script writes results into a new append-only table in `backtest_log.db`:
  - `release_reactions(id, event_time_utc, instrument, status, p0, p5, move, move_pct, typical_abs_move, reaction TEXT, baseline_quantile, reaction_multiple, bar_source, computed_at_utc, UNIQUE(event_time_utc, instrument, baseline_quantile, reaction_multiple))`
  - `reaction_baselines(id, instrument, utc_hour, baseline_abs_move (the quantile value), n_windows, period_start_utc, period_end_utc, computed_at_utc, quantile, UNIQUE(instrument, utc_hour, quantile, period_end_utc))`
  Rows are versioned by quantile (and reaction rows also by reaction multiple): a 0.75 row never collides with a 0.5 row, nor a multiple-1.0 row with a 1.5 row; readers always ask for one version, writers must pass the quantile and the reaction multiple explicitly, and the version columns have no default.
  Rows are never updated; a recomputed baseline is a new row (new `period_end_utc`), and each reaction stores the `typical_abs_move` it was judged against so history is reproducible.
- **Compute script** `scripts/compute_release_reactions.py`: `--backfill` (all USD release minutes since 2026-01-01 for every tracked symbol, resumable) and `--incremental` (releases older than 10 minutes with no row). Read-only on `dashboard.db`; writes only the two new tables; `--dry-run`; refuses to run against the live backtest DB unless `--bt-db` is given or `STATS_BACKFILL_LIVE=1` (same guard as the Tier 1 backfill). Wired into the scheduler by a small hook in the existing outcome-confirm run (owner approval needed before touching any scheduled task).
- `outcomes` (30-minute auto-confirm) is **not changed**; Market reaction is independent of it. (Known weakness it does not fix: `outcomes` credits one 30-minute move to every co-released event.)

## 7. UI (per the approved mockup)

Sub-tab **Market reaction** beside News sentiment. Controls: Impact chips (shared across all four sub-tabs), Instrument (tracked symbols, XAUUSD default), Window (fixed "5 min after release", shown as text), Year, Month. Leaderboard columns: Event, Impact, Releases, Solo, Moved the market (`k of n (%)`), Avg 5-min move, Engine call right. Clicking a row opens that event's releases, newest first: date (SAST), the cluster it sat in, the instrument's move and the typical move, the implied lean, the credit label (Solo hit / Shared driver / Matched the move / Overruled / No reaction / No signal) and the engine call. Two worked cluster examples (agree, conflict) appear as expandable cards. (As built: replaced by the per-release cluster list in the drill-down, which shows every release's actual cluster with each event's lean and credit; the standalone cards were waived and are not built.) Dates are shown in SAST (UTC+2); filters stay UTC-based like the rest of Stats. Disclaimers: "Reaction is measured over 5 minutes against the 75th-percentile ordinary move for that hour; it shows association, not proof that the release caused the move." and "Credit in a cluster is shared or matched, never exclusive." Empty states and "few releases" tags as above.

## 8. Architecture

- `webapp/reaction_rules.py` (new, pure): reaction/direction classification, implied lean reuse, cluster credit, Wilson interval, effective impact.
- `webapp/reaction_service.py` (new, read-only): joins `event_history`, `release_reactions`, the Stats rows (engine calls) and returns leaderboard + drill-down payloads; fail-open per row.
- Routes `/api/stats/reaction/leaderboard` and `/api/stats/reaction/events` with explicit serializers and route-level tests asserting every field the page renders; impact params on the existing Stats routes.
- `scripts/compute_release_reactions.py` + `scoring/backtest_store.py` additions (two tables, record/get functions with UTC normalisation like the nowcast snapshots).
- Frontend: `webapp/static/js/stats/reaction.js`, `impact-filter.js` (shared chips), edits to `stats.js`, `index.html`, `api.js`.
- Stats rows gain `impact`, `impact_effective`, `impact_inferred`.

## 9. Testing

Unit: reaction threshold edges (equal to typical = no reaction), direction/sign for gold and US30, missing bars = no data, baseline is the 75th percentile and excludes windows starting on any raw USD release minute (not the release's own day, see §4), credit rules (solo / agree / conflict / no reaction / no signal), Wilson interval, effective-impact inference (tag, inferred, unrated), cluster formation ignores the impact filter. Compute script: idempotent, resumable, refuses live DB without the flag, never writes outside the two tables, handles a Dukascopy failure without writing a row. Route tests assert exact field sets. JS tests for chips (default High + Unrated), leaderboard rows, drill-down labels, empty states. Live browser check at desktop and 375px before declaring done.

## 10. Risks and open questions

1. **Small samples and multiple comparisons.** About 40 event types ranked on a few months of data will throw up false "drivers". Mitigation: counts everywhere, "few releases" tag, Wilson intervals; no ranking claim below the floor.
2. **Confounding by neighbouring releases.** Owner states releases are normally about 30 minutes apart, so a neighbouring release inside a 5-minute window should not occur (R12). Phase 0 verifies this on the real calendar and lists any exception.
3. **Time-of-day effects.** The baseline is per UTC hour (R13). It absorbs most intraday volatility patterns but not the US daylight-saving shift (12:30Z vs 13:30Z for the same local time); the owner chose not to split it.
4. **Engine calls are sparse.** News/Combined calls exist from Aug 2026; Tier 1 numeric calls only for CPI-family. The engine-call column will be `n/a` for most titles for a long time.
5. **Dukascopy coverage/latency.** Phase 0 must list missing minutes; a missing minute is "no data", never filled.
6. Former open questions O1-O3 are settled by R11-R13.

## 11. Phasing

0. Feasibility: bar coverage for every release minute, baseline sanity (compare with the Shock-alert audit method), count solo/agree/conflict clusters, and count any 5-minute window that contains another USD release minute (expected zero). 1. Pure rules + tests. 2. Tables + compute script + backfill on temp copies. 3. Service + routes + impact filter across Stats. 4. UI. 5. Live backfill, scheduler hook (with approval), docs/inventory row. Final whole-branch review before merge.

**Task 7 runbook (live backfill; each step needs the owner's go-ahead, nothing here is automatic):**

- Live DBs (in the live worktree `C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine\`): `scoring\backtest_log.db` and `webapp\dashboard.db`. Always pass BOTH paths explicitly: the code checkout's relative DB defaults point at the wrong files from any other worktree.
- Back up the live `backtest_log.db` with the sqlite backup API (`sqlite3.connect(live).backup(sqlite3.connect(backup_path))`), not a file copy of a database that may be open.
- Dry run: `python scripts/compute_release_reactions.py --backfill --dry-run --bt-db "C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine\scoring\backtest_log.db" --dash-db "C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine\webapp\dashboard.db"`.
- Expect 2 x the judged release minutes in reaction rows (392 on the 2026-10-16 temp-copy run: 196 minutes x XAUUSD, US30) and 48 baseline rows (24 hours x 2 symbols) at quantile 0.75. If the numbers differ, reconcile the difference (new releases since 10-16, bar gaps, tracked symbols) before going further; never force it.
- Run for real (same command without `--dry-run`), then re-run it and confirm `written=0` (idempotent).
- Check: `SELECT baseline_quantile, reaction_multiple, status, COUNT(*) FROM release_reactions GROUP BY 1, 2, 3` and `SELECT quantile, COUNT(*) FROM reaction_baselines GROUP BY 1`.
- The scheduler hook (`--incremental`, monthly `--refresh-baselines`) is a separate owner-approved step, not part of the backfill.
