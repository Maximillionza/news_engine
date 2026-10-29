# ACT deploy runbook - release-time official actuals

Branch `actuals-release-poller`, applied by the controller. Times are SAST (UTC+2), stored UTC. `<date>` is `YYYY-MM-DD`.

Shell: step 3 needs Windows PowerShell (5.1). Every other command is a plain `python` call with forward-slash paths and no shell variables, so it runs unchanged in PowerShell, cmd or Git Bash. Every command runs from the live app dir:

```
cd C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine
```

## 1. What changes

- A poller thread (`actuals-poller`, started by `start_scheduler()`) fills the actual of every verified numeric USD release from the official publisher: every 60 s until 15 minutes after the release, every 5 minutes until 2 hours after, then one catch-up pass after a start or a wake from sleep. It writes only through `store.fill_actual_if_missing` (first writer wins, never an overwrite) and only when the publisher's data contains the exact reference period.
- New provenance labels in `event_history.source`: `bls`, `bea`, `census`, `eia`, `fed`, `treasury`. Weekly Unemployment Claims are filled from FRED (`ICSA`, source `fred`) because DOL's machine-readable data lags by weeks. The FRED fast path, the hourly B8 backfill and the adaptive Forex Factory interval are unchanged.
- A new health item `actuals_sla` ("Actuals within 15 min") on `/api/health`, folded into the existing once-a-day Telegram health notice (no new message type). Red when a numeric release is more than 15 minutes overdue for a reason other than a proprietary source; amber when only proprietary titles are overdue.
- The cloud web-fallback queue is retired: the engine no longer starts the git sync (`webapp/actuals_sync.py` is deleted). `scripts/fill_missing_actuals.py` stays as the manual tool for proprietary releases.
- No schema change in `dashboard.db`. One new table, `official_source_status`, in `ops_state.db`, created on the first connect after the merge. No scheduled-task or Telegram-type change.
- Only titles with gate status `verified` are polled (`data_layer/official_actuals/gate_results.json`, committed, read once at engine start). Coverage is in section 11.
- Keys are read from `.env`: `BLS_API_KEY`, `BEA_API_KEY`, `CENSUS_API_KEY`, `EIA_API_KEY`, `FRED_API_KEY`. A missing or not-yet-active key fails open (no write, a `key inactive` reason in the SLA item), never a fabricated value.

## 2. Backup

```
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" webapp/dashboard.db webapp/dashboard.db.pre_act_<date>
```

## 3. Stop the single engine copy

PowerShell only. Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|webapp\.app|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 4. Merge

Merge `actuals-release-poller` into `news-engine/batch-predictions-queries` and fast-forward the live worktree. No push.

## 5. Keys present

Names only; no value is printed. All five must report `True`:

```
python -c "from data_layer.official_actuals.keys import load_keys; k=load_keys(); print({n: bool(getattr(k, n)) for n in ('bls','bea','census','eia','fred')})"
```

Mapping: `bls` = `BLS_API_KEY`, `bea` = `BEA_API_KEY`, `census` = `CENSUS_API_KEY`, `eia` = `EIA_API_KEY`, `fred` = `FRED_API_KEY`. A `False` means that publisher's titles will not fill (add the key to `.env`, then restart). A key that is present but not yet activated (Census) also fails open and shows as `key inactive` in the SLA item.

## 6. Backlog

Dry run first. The database is opened read-only; official APIs are called with read-only requests:

```
python scripts/backfill_official_actuals.py --db webapp/dashboard.db
```

Expected at deploy (build-time live dry run, 2026-10-29, read-only): `would fill 25, already filled 64, no actual expected 76, proprietary 66, not mapped 15, gate disabled 6, revised since release 6`. The 25 are Crude Oil Inventories, Natural Gas Storage, 10-y and 30-y Bond Auctions and Federal Funds Rate rows (Fed 2026-09-16 and 2026-10-28, both `4.00%`), plus Core Durable Goods Orders m/m and New Home Sales of 2026-10-27. Rows of revised series (for example JOLTS, GDP) are reported as `revised since release` and left to the FRED/ALFRED backfill, because the publishers serve today's revised numbers, not the first print. Re-count before applying; the numbers move as new releases land.

Then apply:

```
python scripts/backfill_official_actuals.py --apply --db webapp/dashboard.db
```

Rerun the same `--apply` command: it must print `filled 0` (every row is now `already filled`).

## 7. Start exactly one copy

```
schtasks /run /tn NewsEngine_AutoStart
```

Confirm:

- `GET http://localhost:5001/api/health` lists the `actuals_sla` item.
- The engine log shows `[release_poller]` lines (a catch-up pass at start, then `filled <title> <SAST> = <actual> (<source>)` per fill).
- Federal Funds Rate 2026-10-28 20:00 SAST (18:00Z) is filled `4.00%` with source `fed`. The start-up catch-up fills it if the backlog did not already.

## 8. Verify the first release (2026-10-29 12:30Z = 14:30 SAST)

By 12:45Z (14:45 SAST) these titles must be filled, each with the source shown in the coverage table:

- Core PCE Price Index m/m (source `bea`)
- Personal Income m/m (source `bea`)
- Personal Spending m/m (source `bea`)
- Unemployment Claims (source `fred`)
- Advance GDP q/q and Advance GDP Price Index q/q (source `bea`) are gate `unverified` (no comparable history yet), so they are gate-disabled: they stay empty and are listed as such by `actuals_sla`. That is not a failure; fill them with `scripts/fill_missing_actuals.py` or re-run the gate (section 10) after the release.

Query (read-only):

```
python -c "import sqlite3; c=sqlite3.connect('file:webapp/dashboard.db?mode=ro', uri=True); [print(r) for r in c.execute('SELECT event_title, event_time_utc, actual, source FROM event_history WHERE country=? AND event_time_utc LIKE ? ORDER BY event_title', ('USD', '2026-10-29T12:30%'))]"
```

`actuals_sla` must be ok, or name exactly the gate-disabled titles.

## 9. Web fallback

The engine no longer starts the git sync. No Claude routine or local scheduled task for it exists (RemoteTrigger list and `C:/Users/Masoodt/.claude/scheduled-tasks` checked 2026-10-28); the controller confirms on claude.ai's routines page and disables one there if found. The git-ignored clone `webapp/.actuals_sync/` may be deleted after the merge.

## 10. Re-running the gate

Needed for new titles, for gate-`unverified` titles once they have history, or after a code change to the registry. Read-only against the live database:

```
python scripts/verify_official_actuals.py --db webapp/dashboard.db --write-results --markdown docs/superpowers/specs/2026-10-28-act-coverage.md
```

Review the diff of `gate_results.json`, commit, merge and restart one copy: the poller reads the gate file once at start.

## 11. Coverage and known limits

Gate result per title (`Agreement` = comparisons that matched the stored actual or FF previous, including revision-explained ones; `Identity` = whether the official series equals its FRED twin over the last 6 periods, `none` when there is no twin):

| Title | Source | Series | Gate status | Agreement | Identity |
|---|---|---|---|---|---|
| 10-y Bond Auction | treasury | Note:10-Year | verified | 2/2 | none |
| 30-y Bond Auction | treasury | Bond:30-Year | verified | 2/2 | none |
| Advance GDP Price Index q/q | bea | T10107:Q:A191RV | unverified | 0/0 | ok |
| Advance GDP q/q | bea | T10101:Q:A191RL | unverified | 0/0 | ok |
| Average Hourly Earnings m/m | bls | CES0500000003 | verified | 20/20 | ok |
| Building Permits | census | resconst:APERMITS:TOTAL | suspect | 2/4 | ok |
| Business Inventories m/m | census | mtis:TOTBUS:MPCIM | verified | 4/4 | ok |
| CPI m/m | bls | CUSR0000SA0 | verified | 19/19 | ok |
| CPI y/y | bls | CUUR0000SA0 | verified | 20/20 | ok |
| Construction Spending m/m | census | vip:XXXX:MPCT | verified | 3/3 | ok |
| Core CPI m/m | bls | CUSR0000SA0L1E | verified | 17/19 | ok |
| Core CPI y/y | bls | CUUR0000SA0L1E | verified | 15/16 | ok |
| Core Durable Goods Orders m/m | census | advm3:DXT:MPCNO | verified | 2/2 | ok |
| Core PCE Price Index m/m | bea | T20807:M:DPCCRGM | verified | 18/18 | ok |
| Core PPI m/m | bls | WPSFD49104 | verified | 19/20 | ok |
| Core Retail Sales m/m | census | marts:44Y72:MPCSM | verified | 20/20 | ok |
| Crude Oil Inventories | eia | petroleum/stoc/wstk:WCESTUS1 | verified | 9/9 | none |
| Durable Goods Orders m/m | census | advm3:MDM:MPCNO | suspect | 1/2 | ok |
| Employment Cost Index q/q | bls | CIS1010000000000Q | unverified | 0/0 | none |
| Factory Orders m/m | census | m3:MTM:MPCNO | verified | 3/3 | ok |
| Federal Funds Rate | fed | fomc_upper | verified | 2/2 | none |
| Final GDP Price Index q/q | bea | T10107:Q:A191RV | unverified | 1/1 | ok |
| Final GDP q/q | bea | T10101:Q:A191RL | unverified | 1/1 | ok |
| Housing Starts | census | resconst:ASTARTS:TOTAL | verified | 4/4 | ok |
| Import Prices m/m | bls | EIUIR | verified | 19/19 | ok |
| JOLTS Job Openings | bls | JTS000000000000000JOL | verified | 3/3 | ok |
| Natural Gas Storage | eia | natural-gas/stor/wkly:NW2_EPG0_SWO_R48_BCF | verified | 8/8 | none |
| New Home Sales | census | ressales:ASOLD:TOTAL | verified | 2/2 | ok |
| Non-Farm Employment Change | bls | CES0000000001 | verified | 20/20 | ok |
| PPI m/m | bls | WPSFD4 | verified | 20/20 | ok |
| Personal Income m/m | bea | T20600:M:A065RC | verified | 2/2 | ok |
| Personal Spending m/m | bea | T20600:M:DPCERC | verified | 2/2 | ok |
| Prelim GDP Price Index q/q | bea | T10107:Q:A191RV | unverified | 0/0 | ok |
| Prelim GDP q/q | bea | T10101:Q:A191RL | verified | 2/2 | ok |
| Prelim Nonfarm Productivity q/q | bls | PRS85006092 | unverified | 0/0 | ok |
| Prelim Unit Labor Costs q/q | bls | PRS85006112 | unverified | 0/0 | ok |
| Retail Sales m/m | census | marts:44X72:MPCSM | verified | 21/22 | ok |
| Revised Nonfarm Productivity q/q | bls | PRS85006092 | unverified | 1/1 | ok |
| Revised Unit Labor Costs q/q | bls | PRS85006112 | unverified | 1/1 | ok |
| Trade Balance | census | ftd:BOPGS:BAL | verified | 3/3 | ok |
| Unemployment Claims | fred | ICSA | verified | 84/84 | ok |
| Unemployment Rate | bls | LNS14000000 | verified | 20/20 | ok |

Known limits:

- Proprietary titles have no free release-time source and are never polled: ISM, University of Michigan, S&P Global and Flash/Final PMIs, regional Fed surveys, CB Consumer Confidence and Leading Index, Chicago PMI, NAHB, NFIB, API, Challenger, ADP, Existing and Pending Home Sales, S&P/CS HPI, RCM/TIPP, Omdia. They are amber in `actuals_sla` and stay on `scripts/fill_missing_actuals.py`.
- Official data but no ACT adapter (red in `actuals_sla`): Industrial Production, Capacity Utilization, Consumer Credit, Federal Budget Balance, HPI, Current Account, TIC Long-Term Purchases, Final and Prelim Wholesale Inventories, Goods Trade Balance. Census codes for the wholesale and advance goods trade programs were unresolved in the build.
- Gate `suspect` (Building Permits, Durable Goods Orders m/m) and `unverified` titles are not polled until a gate re-run verifies them.
- DOL's national claims data lags FF by weeks, so Unemployment Claims use FRED `ICSA`.
- The Census key must be active; an inactive key shows as `key inactive` and writes nothing.
- Benchmark revisions: the latest release of a series is filled with today's value, which is the first print unless the series was benchmark-revised since.
- Forex Factory's own GDP `previous` is stale after a revision (it still shows the first print), which is why the gate explains revisions with ALFRED vintages.

## 12. Rollback

Stop as in step 3, revert the merge and restart one copy. The new `official_source_status` table stays in `ops_state.db` unread, which is harmless. To undo only ACT's fills, count first, then clear (only ACT writes these labels; claims fills carry `fred` and stay; `updated_at_utc` is no filter because every Forex Factory upsert bumps it):

```
python -c "import sqlite3; print(sqlite3.connect('file:webapp/dashboard.db?mode=ro', uri=True).execute('SELECT COUNT(*) FROM event_history WHERE source IN (?,?,?,?,?,?)', ('bls','bea','census','eia','fed','treasury')).fetchone())"
```

```
UPDATE event_history SET actual=NULL, surprise_direction=NULL, source='live' WHERE source IN ('bls','bea','census','eia','fed','treasury')
```

Restore `webapp/dashboard.db.pre_act_<date>` only to undo the backlog fills as a whole (it loses every row written since the backup).
