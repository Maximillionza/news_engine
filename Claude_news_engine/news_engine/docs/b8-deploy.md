# B8 deploy runbook - surprise metric and event history

Branch `b8-surprise-metric`, applied by the controller. Times are SAST (UTC+2), stored UTC. Every command runs from the live app dir, `<date>` is `YYYY-MM-DD`:

```
cd C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine
```

## 1. What changes

- `event_history` gains rows (source `fred`, forecast NULL) for 2026 High-impact USD releases that are missing, and missing actuals are filled on existing rows. No schema change.
- Scoring change: dashboard essence calls and precursor contributions use the standardized surprise (surprise divided by the indicator's own typical miss, from prior surprises only) from the restart time onward. Fewer than 6 prior surprises falls back to the old percent method. `classify_surprise`, Stats rules, `agreement`/`tier1_tier` and 70/30 are unchanged.
- The scheduler runs a FRED backfill for Medium/Low titles at most hourly.
- No scheduled-task or Telegram change. The first scheduler cycle may write new `prediction_runs` rows for this week's resolved events whose score moved.

## 2. Stop the single engine copy

Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|webapp\.app|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 3. Backup

Use the SQLite backup API:

```
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" webapp\dashboard.db webapp\dashboard.db.pre_b8_<date>
```

Verify the `event_history` row count is equal in both files:

```
python -c "import sqlite3; [print(p, sqlite3.connect('file:'+p+'?mode=ro', uri=True).execute('SELECT COUNT(*) FROM event_history').fetchone()[0]) for p in ('webapp/dashboard.db','webapp/dashboard.db.pre_b8_<date>')]"
```

## 4. Merge

Merge `b8-surprise-metric` into `news-engine/batch-predictions-queries` and fast-forward the live worktree. No push.

## 5. Dry run

```
python scripts\seed_fred_history.py --report %TEMP%\b8_seed_dryrun.txt
```

Nothing is written. If it exits 3 / prints "FRED under maintenance": stop here, start the engine on the merged code (step 8) and retry the seed later; nothing was written. Otherwise review the report:

- Every High title is verified. A suspect or unavailable title is listed for the owner and left out.
- Insert and fill counts look sane.
- New release minutes are the expected New York release times (shown in SAST with the UTC value beside it).

## 6. Apply

```
python scripts\seed_fred_history.py --apply --report %TEMP%\b8_seed_apply.txt
```

It also makes its own `pre_b8` backup and prints the path. Record the apply time (UTC and SAST).

## 7. Verify idempotency

Rerun:

```
python scripts\seed_fred_history.py --apply
```

It must print "inserted 0, filled 0". Record these counts before and after the apply in the deploy note:

```
python -c "import sqlite3; print(sqlite3.connect('file:webapp/dashboard.db?mode=ro', uri=True).execute(\"SELECT COUNT(*), SUM(actual IS NOT NULL) FROM event_history WHERE country='USD' AND event_time_utc >= '2026-01-01'\").fetchone())"
```

## 8. Start exactly one copy

```
schtasks /run /tn NewsEngine_AutoStart
```

Within the first cycle the log shows either `[actuals_backfill] filled N` or nothing (no error). `GET http://localhost:5001/api/predictions` and `GET /api/stats/events` return 200.

## 9. Re-score report after seed

```
python scripts\b8_rescore_report.py --out %TEMP%\b8_rescore_after_seed.md
```

Read-only. Tell the owner the direction-change count.

## 10. Log the scoring change

The controller records "B8 scoring change live since <SAST time>" in the roadmap status line and the inventory row. Reviews of essence calls and precursor contributions use data from that instant only.

## 11. Rollback

Stop as in step 2, `git revert` the merge, restart. Seeded rows can stay (they are real first prints) or be removed with:

```
DELETE FROM event_history WHERE source='fred' AND recorded_at_utc >= '<apply UTC ISO>'
```

Filled actuals are kept by first-writer-wins either way. Restore the `pre_b8` backup only if needed.

## U2 root cause

`data_layer/calendar_feed.py:383` reads `actual=item.get("actual") or None`, but the FairEconomy weekly JSON never carries an actual: 0 of 585 `source='live'` rows have one, and the snapshot of 2026-10-27 shows actual None on all 26 events including ones already released. Every actual therefore comes from a fallback, and both fallbacks are gated to a handful of mostly-High titles:

- The FRED fast path (`webapp/scheduler.py:205-209`) only covers the 10 titles in `config/settings.py:153` `FRED_SERIES_ID_BY_EVENT_TITLE`, and only while the release is still in FF's this-week feed.
- The web fallback queue only admits the 19 titles in `EVENT_SURPRISE_DIRECTION` (`webapp/store.py:34` import, queue filter at `webapp/store.py:621-647`) within 48 h (`webapp/actuals_sync.py:40`).
- Medium and Low titles have no path at all.

2026 USD past rows with an actual (2026-10-27): High 31/42, Medium 3/40, Low 2/166.

## Revisions (U4)

Every FRED-sourced value is the first print from the ALFRED vintage dated the release day (what the market reacted to), never FRED's latest revision. `previous` is the prior period as published that day (revised). NFP and Retail Sales headlines are computed inside that vintage (new level minus/over the revised prior level), which is how BLS/Census publish them. Revisions to earlier months are not folded into the surprise (no consensus for revisions exists here). The existing same-day fast path (`fred_actuals.get_actual_from_fred`, latest vintage, release week only) is kept: on release day it returns the same first print.

## Not covered

- GDP (three estimates per quarter), ISM, UoM, Conference Board, S&P PMIs, auctions and speeches: no exact free FRED series or no number.
- The web-fallback cloud routine has written 0 rows ever (0 `cloud_web_fallback` rows). It is a Claude scheduled task, outside B8; owner to decide.
- FRED has no consensus forecasts, so seeded rows carry actual + previous only and do not deepen any indicator's sigma.

## OPEN QUESTION (owner): JOLTS surprise direction

Should a JOLTS surprise direction exist (higher openings = USD bullish?) so the existing JOLTS -> NFP 0.40 link (`config/settings.py:443`) can ever contribute? No direction is set until the owner decides; JOLTS actuals are now filled but carry no `surprise_direction`.
