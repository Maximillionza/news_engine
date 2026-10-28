# B10 deploy runbook - shock-alert lean grading

Branch `b10-shock-grading`, applied by the controller. Times are SAST (UTC+2), stored UTC. `<date>` is `YYYY-MM-DD`.

Shell: step 3 needs Windows PowerShell (5.1). Every other command is a plain `python` call with forward-slash paths and no shell variables, so it runs unchanged in PowerShell, cmd or Git Bash. Every command runs from the live app dir:

```
cd C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine
```

## 1. What changes

- Two new tables in `shock_alerts.db` (`shock_alert_grades`, `shock_grading_runs`), created at the first connect after the merge (poller tick or webapp). No ALTER on `shock_alerts`; no alert row is rewritten.
- The weekly `NewsEngine_ShockRealityCheck` task now grades leans (5-minute move from first publication and from detection, against the Market reaction hourly baselines), records one summary row, and its `reality_mismatch` flag uses the hourly baselines instead of the fixed $10 / 150-point thresholds.
- The Shock Alerts tab gains lean verdicts, lag, hit rates (per incident and overall, each with n) and a date range.
- Twelve one-off scripts move to `scripts/archive/`; the minute-bar helpers move to `data_layer/minute_bars.py`. The reaction job's output is unchanged.
- No scheduled-task, Telegram or scoring change.
- The weekly `NewsEngine_ShockRealityCheck` job now exits 1 when a Dukascopy bar fetch fails (nothing is written for that symbol; it is retried next week). After 9 days with no success the health item turns red and can appear in the existing daily health notice (no new Telegram message type).

## 2. Backup

```
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" alerting/shock_alerts.db alerting/shock_alerts.db.pre_b10_<date>
```

## 3. Stop the single engine copy

PowerShell only. Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|webapp\.app|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 4. Merge

Merge `b10-shock-grading` into `news-engine/batch-predictions-queries` and fast-forward the live worktree. No push.

## 5. Start exactly one copy

```
schtasks /run /tn NewsEngine_AutoStart
```

Verify the migration with `PRAGMA table_info(shock_alert_grades)`:

```
python -c "import sqlite3; print(sqlite3.connect('file:alerting/shock_alerts.db?mode=ro', uri=True).execute('PRAGMA table_info(shock_alert_grades)').fetchall())"
```

It must list columns. (Running the step 6 apply also migrates.)

## 6. Backfill

Dry run first. Every database is opened read-only; the only writes are bar-cache files in the OS temp dir:

```
python scripts/backfill_shock_grades.py --alerts-db alerting/shock_alerts.db --bt-db scoring/backtest_log.db --dash-db webapp/dashboard.db
```

Record the per-anchor verdict counts and the detection-anchored hit rate, and compare them with the build-time expectation below.

Expected at deploy (build-time dry run): not recorded. The build session was not permitted to run the live read-only dry run, so the controller runs it here and pastes the counts and the `overall 5-minute detection-anchored hit rate` line into this section. Starting point before B10: 14 of 26 leans correct at 5 minutes; medium alerts had never been graded. The new overall 5-minute detection-anchored hit rate will differ from the old "14 of 26": the old figure counted High alerts only, used the fixed $10 / 150-point thresholds and the detection anchor only, while the new one covers every severity and both symbols and uses that hour's 75th-percentile baseline (far below $10 on gold in most hours), so n grows and fewer cells read `no_move`.

Live dry-run counts (controller, at deploy 2026-10-28; apply identical): published right 5, wrong 6, no_move 29, no_lean 114, no_data 14, no_baseline 0; detected right 4, wrong 6, no_move 30, no_lean 114, no_data 14, no_baseline 0; graded 336, hit rate 42.9% (9 of 21), overall 5-minute detection-anchored hit rate 40.0% (4 of 10). Rerun: written 0. Acceptance query: 0.

Then apply:

```
python scripts/backfill_shock_grades.py --apply --alerts-db alerting/shock_alerts.db --bt-db scoring/backtest_log.db --dash-db webapp/dashboard.db
```

Record `written` and the detection-anchored figure next to "14 of 26". Rerun the same `--apply` command: it must print `graded 0`.

Acceptance query. It should return 0, except for alerts detected within about 15 minutes before the apply or after the bar feed's last bar (their bars are not yet available). Each such alert contributes up to 4 to the apply output's `pending` count, because `pending` counts cells (2 symbols x 2 anchors per alert) while this query counts alerts:

```
python -c "import sqlite3; print(sqlite3.connect('file:alerting/shock_alerts.db?mode=ro', uri=True).execute('SELECT COUNT(*) FROM shock_alerts a WHERE (SELECT COUNT(*) FROM shock_alert_grades g WHERE g.alert_id = a.id) < 4').fetchone())"
```

## 7. Verify

- Reaction job unchanged and still runnable (exits 0):

```
python scripts/compute_release_reactions.py --incremental --dry-run --bt-db scoring/backtest_log.db --dash-db webapp/dashboard.db
```

- `GET http://localhost:5001/api/shock-alerts?from=2026-09-17&to=<date>` shows `summary.overall.detected.n`.
- `GET http://localhost:5001/api/health` shows the `last grading` detail on the `shock_reality_check` item.
- After the next Sunday 20:00 SAST run, `reality_check.log` carries a `[lean_grading] graded` line.

## 8. Rollback

Stop as in step 3, revert the merge and restart one copy. The new tables stay in `shock_alerts.db` unread, which is harmless. Restore `shock_alerts.db.pre_b10_<date>` only if needed (it loses alerts written since the backup). Reverting also puts the archived scripts back where they were.
