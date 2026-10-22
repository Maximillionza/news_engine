# B6 deploy runbook - article read: stop wrong-sign evidence

Branch `b6-article-wrong-sign`, applied by the controller. Times are SAST. Every command runs from the live app dir:

```
cd C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine
```

This is a scoring change: from the restart onward FOMC and CPI calls are voted on by fewer, better articles, so expect thinner samples and lower confidence on some calls. The restart time is the change date (record it in step 5).

## 1. What changes at merge, with no step

- Scoring rules: foreign central bank articles are excluded, FOMC needs a Fed co-term, FOMC and CPI need an on-subject title, same-URL articles are counted once, precursor trust uses the authored influence-link weights, and non-USD rows give no surprise.
- The new table `prediction_article_contributions` is created by `get_connection()` on the accumulator's first cycle after the restart (append-only; roughly 10 MB a month at current volume).
- No Windows scheduled task or Claude scheduled task changes. Nothing outside the repo needs deploying.

## 2. Backup first

Use the SQLite backup API (safe while the accumulator writes). Set `<date>` to today (`YYYY-MM-DD`):

```
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" scoring\backtest_log.db scoring\backtest_log.db.pre_b6_<date>
```

## 3. Stop the single engine copy

Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|webapp\.app|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 4. Merge

Merge `b6-article-wrong-sign` into `news-engine/batch-predictions-queries` and update the live worktree (the controller's usual fast-forward).

## 5. Start exactly one copy

```
schtasks /run /tn NewsEngine_AutoStart
```

The accumulator loads the new code on this start. Record the restart time in UTC and SAST in the feature inventory B6 row (the "Change date" placeholder). The review on 2027-01-15 uses data from this instant only (roadmap risk 4).

## 6. Verify

- The accumulator log shows `[event_context] <event>: excluded <n> (...)` lines (for example `[event_context] FOMC Statement: excluded 7 (foreign_cb=2, no_fed_coterm=1, off_subject=3, duplicate_url=1)`).
- `SELECT status, reason, COUNT(*) FROM prediction_article_contributions GROUP BY 1, 2` (in `scoring\backtest_log.db`) grows after the next recorded prediction.
- `python scripts\b6_contamination_report.py --db scoring\backtest_log.db --verify-since <restart UTC ISO>` prints `0` (exit 0). Repeat after a week: that is the roadmap acceptance. Exit 2 means the table is missing (the accumulator has not run a cycle yet, or the code did not load).

## 7. Rollback

Stop as in step 3, revert the merge, restart one copy. The new table can stay (nothing reads it after the revert); restore the `pre_b6` backup only if needed.
