# B11 deploy runbook - dead code removal and consolidation

Branch `b11-dead-code`, applied by the controller. Times are SAST. Every command runs from the live app dir:

```
cd C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine
```

## 1. What changes

- No DB changes and no migrations. A backup is not needed, but taking one is harmless (see `docs/b7-deploy.md` section 2).
- No Windows or Claude scheduled task changes. The disabled `monday-fomc-calendar-check` SKILL.md mentions `exogenous_shocks` only in a "do not write" sentence, so it needs no edit.
- Merge `b11-dead-code` into `news-engine/batch-predictions-queries` in the live worktree (the controller does this; no push).

## 2. Stop the single engine copy

The dashboard and accumulator import modules that were removed or changed, so they need a restart. The poller, outcome-confirm and health run as fresh processes and need nothing. Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|webapp\.app|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 3. Merge, then start exactly one copy

Merge as in section 1, then:

```
schtasks /run /tn NewsEngine_AutoStart
```

## 4. Verify

- The Task 1 `git grep` for the removed names returns nothing.
- `python -c "import webapp.app, scripts.confirm_backtest_outcomes, scripts.event_study_once, ops.health"` exits 0.
- `GET http://localhost:5001/api/predictions` returns 200.
- `GET /api/health` lists `macro_calendar` with an unchanged status.
- After the next `NewsEngine_OutcomeConfirm` tick, the `job_runs` row for outcome_confirm shows exit 0 (read-only: `sqlite3 "file:ops/ops_state.db?mode=ro"`).
- `SELECT COUNT(*) FROM tier1_comparisons` (in `scoring\backtest_log.db`, read-only) stays 10 after a confirm run.

## 5. Rollback

`git revert` the merge, then restart as in sections 2 and 3. There is no data to restore.
