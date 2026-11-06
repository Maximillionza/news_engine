# Fix-five deploy runbook - History cut, engine wake-up, budget count, FRED window, Stats Tier 1

Branch `news-engine/fix-five`, built from `458ea64`. Owner approval 2026-11-06, evidence from that day's NFP (release 15:30 SAST, 13:30 UTC). Times are SAST (UTC+2), stored UTC. `<date>` is the deploy date, `YYYY-MM-DD`.

Every step below is applied at deploy by the controller. Nothing in this branch has touched the live worktree, a live database, a Windows task, a Claude task or Telegram. Every command runs from the live app dir:

```
cd C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine
```

## 1. What changes

- Fix 1, History: the "NE Prediction", its grade, the print call and the "why" panel use only rows scored strictly before the release. An occurrence with no pre-release row shows no prediction. Post-release rows stay stored. Measured on a live copy: the headline goes from 44/96 to 40/96 and 9 outcomes change.
- Fix 2, engine wake-up: `compute_accumulator_interval_seconds()` never sleeps past the start of the next unresolved event's final hour, with a 60-second floor. The budget constants are unchanged.
- Fix 3, budget count: one `check_log` row per accumulator run, not one per event. `DAILY_CHECK_BUDGET_THRESHOLD` stays 20.
- Fix 4, FRED window: `realtime_end` stops at FRED's own today (America/Chicago), so a row from the last 3 days no longer gets HTTP 400. The hourly backfill fills what it skipped; a dry run on a live copy would fill 1 row (ADP Non-Farm Employment Change 2026-11-04 = 86K), first-writer-wins.
- Fix 5, Stats: market-implied Tier 1 rows show direction word, implied number and verdict, for example `hotter · 75K · Right` and `in line · 3.2% · No call`, and the Tier 1 chart plots the implied number. Display only: Right/Wrong counts, the in-line baseline, `mean_miss`, Combined, and formula and judgment rows are unchanged. On a live copy the scoreboard and every graded field were identical before and after, and 3 Tier 1 chart points were added (Advance GDP q/q, ISM Manufacturing PMI, NFP).

No DB migration. No table, column or index changes, in any of the databases, and nothing to re-derive or backfill by hand. No Windows task, Claude task, setting or Telegram change.

## 2. Stop the single engine copy

PowerShell only. Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|webapp\.app|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 3. Backup

After the stop, with the sqlite backup API, one copy per database to `<db>.pre_five_<date>`:

```
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" webapp/dashboard.db webapp/dashboard.db.pre_five_<date>
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" scoring/backtest_log.db scoring/backtest_log.db.pre_five_<date>
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" alerting/shock_alerts.db alerting/shock_alerts.db.pre_five_<date>
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" ops/ops_state.db ops/ops_state.db.pre_five_<date>
```

## 4. Merge

On the live branch (no push). A true fast-forward would leave no merge commit to revert, so the merge is explicit:

```
git merge --no-ff news-engine/fix-five
```

Note the merge commit sha for the rollback.

## 5. Restart

PowerShell or cmd:

```
schtasks /run /tn NewsEngine_AutoStart
```

Git Bash:

```
MSYS_NO_PATHCONV=1 schtasks /run /tn NewsEngine_AutoStart
```

## 6. Checks

Hard-refresh the dashboard first, so the browser takes the new `webapp/static/js` files.

- `GET http://localhost:5001/api/health` answers and nothing new is red.
- History: Average Hourly Earnings 2026-11-06 shows bullish and Missed, not the post-release bearish. The headline reads about 40/96 rather than 44/96; it moves by whatever has released since the 2026-11-06 copy.
- Stats, Combined sub-tab: NFP 2026-11-06 reads `hotter · 75K · Right`, Advance GDP q/q 2026-10-29 reads `in line · 3.2% · No call`. Tier 1 sub-tab, same rows: `hotter · 75K` and `in line · 3.2%` with the verdict in the Result column.
- Stats chart, Non-Farm Employment Change, Tier 1 only: a green point at 75 for 2026-11. Advance GDP q/q: a grey point near 3.18, because an in-line call is not graded.
- Stats scoreboard: compare against the page before deploy; the only movement allowed is a new release. On the 2026-11-06 copy: Tier 1 13 of 21, News 0 of 2, Combined 12 of 18.
- Federal Funds Rate rows read `bearish` and `neutral` with no number and no chart point. These are FedWatch rows with no stored median; this is correct, not a fault.
- `check_log` grows by one row per run: after two accumulator runs with active events, `SELECT checked_at_utc FROM check_log ORDER BY id DESC LIMIT 4` shows one stamp per run. Read it from a copy or with `mode=ro`.
- The first hourly FRED backfill after restart logs no 400 for `ADPMNUSNERSA`, and ADP Non-Farm Employment Change 2026-11-04 fills if it is still empty.

Expect for the first 24 hours: rows written before the deploy still count in the rolling 24-hour budget at one per event, so the 3-hour back-off can still trip. Fix 2 keeps that from crossing a final hour. It clears as those rows age out.

## 7. Rollback

With the engine stopped (step 2): `git revert -m 1 <merge sha>` on the live branch, then restart as in step 5.

The database backups are not part of a code rollback. This branch changes no schema and rewrites no stored row, so the reverted code reads the databases as they are, and restoring a `.pre_five_<date>` copy would discard every row written since the deploy. Restore one over its original only if that database itself was damaged, with the engine stopped.
