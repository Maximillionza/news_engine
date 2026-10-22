# B7 deploy runbook - same incident, one voice

Branch `b7-same-incident`, applied by the controller. Times are SAST. Every command runs from the live app dir:

```
cd C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine
```

This changes article scoring: from the restart onward re-coverage of one incident votes once in the accumulator, so expect lower article counts on some events. The restart time is the change date (record it in step 5).

## 1. What changes at merge, with no step

- The 2-minute poller (a fresh process per tick) migrates `alerting\shock_alerts.db` on its first tick: three nullable columns (`incident_id`, `incident_role`, `incident_rule`) and the `seen_urls` table, backfilled from the last 72 h of alerts. Old alerts read as their own incident. Follow-ups stop pushing (except on a severity rise or direction flip, which push once as "Update to incident #N").
- Article scoring excludes same-incident re-coverage from the accumulator restart onward. Expect one material-change prediction row per active event on the first cycle, because `article_count` drops.
- No Windows or Claude scheduled task changes. Nothing outside the repo needs deploying.

## 2. Backup first

Use the SQLite backup API (safe while the poller and accumulator write), for both databases. Set `<date>` to today (`YYYY-MM-DD`):

```
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" alerting\shock_alerts.db alerting\shock_alerts.db.pre_b7_<date>
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" scoring\backtest_log.db scoring\backtest_log.db.pre_b7_<date>
```

## 3. Stop the single engine copy

Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|webapp\.app|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 4. Merge

Merge `b7-same-incident` into `news-engine/batch-predictions-queries` and fast-forward the live worktree (the controller's usual step).

## 5. Start exactly one copy

```
schtasks /run /tn NewsEngine_AutoStart
```

Record the restart time in UTC and SAST in the feature inventory B7 row (the "Change date" placeholder). Article-sentiment reviews use data from this instant only.

## 6. Verify

- `PRAGMA table_info(shock_alerts)` (in `alerting\shock_alerts.db`) lists `incident_id`, `incident_role`, `incident_rule`.
- `SELECT COUNT(*) FROM seen_urls` is greater than 0 after the next poll tick if any alert was detected in the last 72 h (the one-time backfill); otherwise it becomes greater than 0 after the next new alert.
- The poll log shows `incident #<n> follow_up (...) -- stored, no push` the next time a story is re-covered.
- `/api/shock-alerts` rows carry `incident_id`.
- After the next recorded prediction, `SELECT reason, COUNT(*) FROM prediction_article_contributions WHERE recorded_at_utc >= '<restart UTC>' GROUP BY 1` (in `scoring\backtest_log.db`) may show `same_incident`; the accumulator's `recorded` log line carries `same_incident excluded: <n>` when n > 0.

## 7. Rollback

Stop as in step 3, revert the merge, restart one copy. The new columns and table stay (nothing reads them after the revert); restore the `pre_b7` backups only if needed.

Before any later redeploy of B7, run `DROP TABLE seen_urls` (in `alerting\shock_alerts.db`, with the engine stopped) so the one-time 72 h backfill runs again when the table is recreated; otherwise alerts detected during the rollback window have no URL memory (accept that 72 h gap only knowingly).
