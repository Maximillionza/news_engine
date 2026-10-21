# B4 deploy runbook - ops health and waste

Branch `b4-ops-health`, applied by the controller. Times are SAST. Every command runs from the live app dir:

```
cd C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine
```

## 1. What changes at merge, with no step

- The 5 scheduled launchers now run `python -m ops.run_job`: every log line is timestamped (`YYYY-MM-DD HH:MM:SS SAST`) and each log rotates at 1 MB to `<name>.log.1` (one backup). Each run's exit code is recorded for the health check.
- No Windows task re-registration: every NewsEngine_* action already points at a `.bat`/`.vbs` inside the live worktree, so the launcher edits take effect when the merge lands.
- `ops/ops_state.db` is created on first use (job runs, heartbeats, the once-per-day health-notice ledger).
- `source_health` (feed backoff) and the near-miss indexes are created by `alerting/store.py` on the next poll.

## 2. Backups first

Outcomes are written, near-misses are deleted and macro rows are added. Use the SQLite backup API (safe while the poller writes). Set `<date>` to today (`YYYY-MM-DD`):

```
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" scoring\backtest_log.db scoring\backtest_log.db.pre_b4_<date>
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" alerting\shock_alerts.db alerting\shock_alerts.db.pre_b4_<date>
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" webapp\dashboard.db webapp\dashboard.db.pre_b4_<date>
```

## 3. Stop every engine copy (both duplicates)

Two full copies have been running (AutoStart task at logon plus the desktop `News Engine.bat`). Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 4. Merge

Merge `b4-ops-health` into `news-engine/batch-predictions-queries` and update the live worktree (the controller's usual fast-forward).

## 5. Start exactly one copy

```
schtasks /run /tn NewsEngine_AutoStart
```

Prove the guard: `python webapp\app.py` and `python scripts\run_accumulator.py` each print `already running` and `$LASTEXITCODE` is 3. The step 3 queries (without `Stop-Process`) must list exactly one `app.py` and one `run_accumulator.py`.

## 6. Verify

- `Get-Content alerting\poll_once.log -Tail 5`: lines start `YYYY-MM-DD HH:MM:SS SAST`.
- After the next 15-minute outcome run, `scripts\confirm_outcomes_scheduled.log.1` holds the old 3.7 MB log and the new log shows `Auto-confirm: 0 confirmed, <n> final no-reaction, <m> left for review.` (n = the below-threshold rows, about 28; m = rows with no price data), then `Nothing awaiting confirmation` on later runs unless m > 0.
- `SELECT COUNT(*) FROM outcomes WHERE actual_move_note LIKE '%no reaction after 3 days, final (auto)'` (in `scoring\backtest_log.db`) equals n.
- `Invoke-RestMethod http://127.0.0.1:5001/api/health` returns `overall` and the item list, and the dashboard shows the health strip.
- `SELECT MAX(event_date), COUNT(*) FROM macro_calendar` (in `webapp\dashboard.db`) shows dates past today, and `data_layer\.last_macro_calendar_refresh_at` exists (the first scheduler iteration refreshes; the live worktree has no marker today).
- `SELECT COUNT(*), MIN(seen_at_utc) FROM shock_near_misses` (in `alerting\shock_alerts.db`) falls each poll until the oldest row is within 30 days (500 rows per poll).
- One Telegram health notice arrives the same UTC day if anything is red. Expected: `tier1_research` for PPI m/m 2026-10-15 until it leaves the 7-day window, and `classifier:claude` while its credits are exhausted.

## 7. Rollback

Stop as in step 3, revert the merge, restart one copy; restore a backup only if needed. The final no-reaction rows can be removed without a restore:

```
DELETE FROM outcomes WHERE actual_move_note LIKE '%no reaction after 3 days, final (auto)'
```

(The next confirm run re-finalises them unless the code is reverted.)

## 8. O7 root cause - the macro calendar stopped refreshing

[Certain] `scripts/refresh_macro_calendar.py` is self-gated ("safe to invoke on any schedule") but nothing ever invoked it: no Windows task, no Claude task, no caller in code. It ran once by hand on 2026-08-16T10:48Z (all 21 rows share that `recorded_at_utc`; the shared checkout's marker file holds the same instant) with a 35-day window, so the last row is 2026-09-17. Later `updated_at_utc` stamps (to 2026-09-18) are the scheduler's Forex Factory confirmations, not refreshes. The live worktree has no marker file. It was not an external failure (the FRED key is present).

Fix: the webapp scheduler now calls the self-gated refresh every iteration, and a run that writes nothing no longer marks itself done (it retries after 6 hours). The health check (O6) now shows a stale or exhausted macro calendar.

## 9. Acceptance (roadmap B4)

- The confirm log stops repeating "28 left".
- The health check flags Tier 1, the classifier and `macro_calendar` (pinned by `test_health_flags_the_three_known_silent_failures`).
- One unattended ShockPoll run and one unattended OutcomeConfirm run are each logged with timestamps after deploy.
