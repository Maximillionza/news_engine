# FIX deploy runbook - audit fixes and actuals follow-ups

Branch `news-engine/fix-audit`, built from `news-engine/batch-predictions-queries` at 3583159. Spec: `docs/superpowers/specs/2026-11-03-fix-audit-spec.md` (owner approval 2026-11-03 09:00 SAST). Plan: `docs/superpowers/plans/2026-11-03-fix-audit.md`. Times are SAST (UTC+2), stored UTC. `<date>` is `YYYY-MM-DD`.

Every step below is applied at deploy by the controller, never by an implementer. Nothing in this branch has touched the live worktree, a live database, a Windows task, a Claude task or Telegram.

Shell: steps 2 and 7 and the `Get-ScheduledTask` check in step 11 need Windows PowerShell (5.1). Steps 3 to 6 and the `git revert` in step 12 are plain `python` or `git` calls with forward-slash paths, so they run unchanged in PowerShell, cmd or Git Bash. Step 10 calls `schtasks`, and Git Bash rewrites its `/`-prefixed arguments into file paths, so step 10 gives a separate Git Bash form. Steps 8 and 9 are file edits. Every command runs from the live app dir:

```
cd C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine
```

## 1. What changes

- Article relevance (T1): whole-word keyword matching in every keyword list, a US-subject rule for every event family, and asset-led / foreign-currency headlines excluded on every scoring path. New exclusion reasons reach the evidence table. `scripts/relevance_replay.py` is the read-only replay.
- Evidence floor (T3, owner ruling R1): a News lean is a call only if `abs(lean) >= 0.2` and it rests on at least `NEWS_CALL_MIN_ARTICLES = 3` included, non-zero-sentiment articles. Expected effect: most News rows become no-call until article supply improves. The Combined blend (70/30) is unchanged.
- One in-line definition (T2, R2): `data_layer/surprise_side.py`; `webapp/stats_rules.py` re-exports it. `scripts/rederive_surprise_direction.py` relabels stored `surprise_direction` (label only, never an actual).
- Hard-rule shock-alert guards (T4): denials, price reports and commentary are rejected; an unknown `us_link` leaves the rule tier and waits for the classifier. 12 of the 23 hard-rule phrases now wait for the classifier, so every past rule alert changes route.
- Actuals follow-ups (T5): corrected Empire State FRED id, Existing Home Sales first prints (FRED poller, 2% `previous` tolerance), Census advance titles (Goods Trade Balance, Prelim Wholesale Inventories), one retry for FRED 5xx / timeout, FRED error text without URL or key.
- Tier 1 capture (T6): `macro_calendar` fallback for unconfirmed dates (DST-safe release time, phantom rows dropped), refresh of a market row when the forecast changes, FedWatch tier per registry, battery and stagger settings in `scripts/register_tier1_tasks.ps1`.
- Health and alerts (T7, R3): switched-off titles show amber "not covered (switched off)" in `actuals_sla`; Tier 1 research heartbeat and late-check items; new `tier1_research.py alert` command that sends one Telegram notice and records it for the health panel.
- No schema change to the three dashboard databases. The one new table, `research_alerts` in `ops/ops_state.db`, is created idempotently on first connect.

## 2. Stop the single engine copy

PowerShell only. Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|webapp\.app|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 3. Backup

After the stop, with the sqlite backup API, one copy per database to `<db>.pre_fix_<date>`:

```
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" webapp/dashboard.db webapp/dashboard.db.pre_fix_<date>
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" scoring/backtest_log.db scoring/backtest_log.db.pre_fix_<date>
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" alerting/shock_alerts.db alerting/shock_alerts.db.pre_fix_<date>
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" ops/ops_state.db ops/ops_state.db.pre_fix_<date>
```

## 4. Merge

On the live branch (no push). A true fast-forward would leave no merge commit to revert, so the merge is explicit:

```
git merge --no-ff news-engine/fix-audit
```

Note the merge commit sha for the rollback.

## 5. Re-derive surprise labels

Dry run first and read the counts, then apply, then a third run must show 0. The build-time dry run on a live copy shows 29 rows to change: 28 of the 59 `in_line` rows (10 to higher, 18 to lower) plus 1 Prelim GDP q/q row going from NULL to `in_line`. No higher or lower row changes.

```
python scripts/rederive_surprise_direction.py --db webapp/dashboard.db
python scripts/rederive_surprise_direction.py --db webapp/dashboard.db --apply --report .
python scripts/rederive_surprise_direction.py --db webapp/dashboard.db
```

## 6. Backlog actuals

Dry run and read the lists, apply, then run the dry run again: it must fill 0. Build-time dry run on a live copy (2026-11-04), seven fills:

- Empire State Manufacturing Index: 7.6 (2026-09-15), 25.5 (2026-10-15), both from the FRED/ALFRED pass.
- Goods Trade Balance: -132.6B (2026-09-30, FRED/ALFRED pass), -134.9B (2026-10-28, Census).
- Prelim Wholesale Inventories m/m: 0.7% (2026-09-30, FRED/ALFRED pass), 0.6% (2026-10-28, Census).
- Existing Home Sales: 3.99M (2026-10-13, FRED), the latest row only. The 2026-09-10 row stays empty with `revised since release`.

The August rows of the first three titles (Empire 2026-08-17, the other two 2026-08-27) have a NULL country. Both passes read USD rows only, so those rows stay empty and no August value appears in the lists. That is expected, not a mismatch. A release after 2026-11-04 can add a fill to this list.

```
python scripts/backfill_official_actuals.py --db webapp/dashboard.db --env-file .env --fred-backfill
python scripts/backfill_official_actuals.py --db webapp/dashboard.db --env-file .env --fred-backfill --apply --report backfill-report.txt
python scripts/backfill_official_actuals.py --db webapp/dashboard.db --env-file .env --fred-backfill
```

Steps 5 and 6 leave two report files in the live app dir, `rederive_surprise_direction_<stamp>.txt` and `backfill-report.txt`. Neither is tracked by git. Delete both once they have been read.

## 7. Task re-registration

PowerShell. Applies the battery and stagger settings:

```
powershell -ExecutionPolicy Bypass -File scripts/register_tier1_tasks.ps1
```

## 8. Allow rule for the alert command

Back up `C:\Users\Masoodt\Documents\Claude\Projects\Claude_news_engine\news_engine\.claude\settings.local.json`, then add this to `permissions.allow`, next to the existing tier1_research.py record-late-check rule:

```
Bash(python C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/scripts/tier1_research.py alert:*)
```

## 9. SKILL.md update (SOURCE POLICY)

File: `C:/Users/Masoodt/.claude/scheduled-tasks/tier1-cpi-ppi-autoresearch/SKILL.md`. Back it up as `SKILL.md.bak_<date>` first. After the "RUN BLOCKED" bullet of the SOURCE POLICY section add exactly:

```
- ALERT DELIVERY: each "RELIABILITY ALERT:", "SECURITY ALERT:" or "RUN BLOCKED:" line is also sent once with python C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/scripts/tier1_research.py alert --kind <reliability|security|blocked> --event "<event title, or run when it concerns the whole run>" --message "<the same line without its label>". If this command is refused, keep the line in the report and stop.
```

Then replace BOTH occurrences of `(plan, record-call, record-late-check)` with `(plan, record-call, record-late-check, alert)` and `the three full-path tier1_research.py subcommands` with `the four full-path tier1_research.py subcommands`.

## 10. Restart

PowerShell or cmd:

```
schtasks /run /tn NewsEngine_AutoStart
```

Git Bash:

```
MSYS_NO_PATHCONV=1 schtasks /run /tn NewsEngine_AutoStart
```

## 11. Checks

- `GET http://localhost:5001/api/health` shows `tier1_alerts` ok, and `tier1_research` amber until the next plan run.
- Stats shows `n=` beside News calls; below-floor leans show as no-call.
- The first Existing Home Sales release after deploy fills through the release poller (source `fred`).
- The first Empire State release after deploy fills through the hourly FRED/ALFRED backfill, at least an hour after release (source `fred`). Empire is classed proprietary, so the poller never reads it.
- `Get-ScheduledTask` for the Tier 1 tasks shows the battery settings (starts on battery, no stop on battery) and the staggered Monday time.
- One test alert is not sent to Telegram unless the owner asks.

## 12. Rollback

With the engine stopped (step 2): `git revert -m 1 <merge sha>` on the live branch; restore the four `.pre_fix_<date>` database backups over their originals; restore `SKILL.md` from its `.bak_<date>` and `settings.local.json` from its backup; re-run the previous `scripts/register_tier1_tasks.ps1` (from the reverted tree); restart as in step 10.
