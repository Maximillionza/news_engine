# B8 deploy runbook - surprise metric and event history

Branch `b8-surprise-metric`, applied by the controller. Times are SAST (UTC+2), stored UTC. `<date>` is `YYYY-MM-DD`.

Shell: step 2 needs Windows PowerShell (5.1). Every other command is a plain `python` call with forward-slash paths and no shell variables, so it runs unchanged in PowerShell, cmd or Git Bash. Every command runs from the live app dir. Reports go to one deploy folder, `C:/Users/Masoodt/b8_deploy` (outside every git worktree), created here before step 1:

```
cd C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine
python -c "import pathlib; p = pathlib.Path('C:/Users/Masoodt/b8_deploy'); p.mkdir(exist_ok=True); print(p, p.is_dir())"
```

It must print `C:\Users\Masoodt\b8_deploy True`.

## 1. What changes

- `event_history` gains rows (source `fred`, forecast NULL, impact NULL, surprise_direction NULL) for 2026 High-impact USD releases that are missing, and missing actuals are filled on existing rows. No schema change.
- Scoring change: dashboard essence calls and precursor contributions use the standardized surprise (surprise divided by the indicator's own typical miss, from prior surprises only) from the restart time onward. Fewer than 6 prior surprises falls back to the old percent method. `classify_surprise`, Stats rules, `agreement`/`tier1_tier` and 70/30 are unchanged.
- The scheduler runs a FRED backfill for Medium/Low titles at most hourly.
- Scoring effect through the trend inputs (checked in code). `get_event_history` returns each title's 6 most recent rows (`EVENT_HISTORY_WINDOW` in `webapp/store.py`, the unchanged default). The accumulator's trend prior reads that window (`scoring/backtest_accumulator.py:332`: `_read_trend_signal` keeps rows with a `surprise_direction`, needs 3 of them, and its `compute_trend_signal` nudges live accumulator predictions), and so does the History trend text (`webapp/app.py:146`, `/api/event_history`). Seeded rows have no forecast, so no direction, so they never count as graded but do take a slot in the window:
  - A seeded gap that is more recent than older graded rows pushes them out. Live example (2026-10-27): Core PPI m/m's window is Oct, Sep, Aug, Mar, Feb, Jan, all graded; once the seed inserts the Apr-Jul releases only 3 graded rows remain (the trend prior stays on at exactly 3 but is computed from different rows; the trend text is built from fewer rows). A title pushed below 3 loses its trend prior.
  - The other way round, fills (seed and hourly backfill) give graded rows to titles that had none. Unemployment Claims (live, read-only check 2026-10-28): the 7 rows from 2026-09-10 to 2026-10-22 have no actual; the window (which also holds this week's pending 2026-10-29 row) goes from 0 graded to up to 5. That switches on its trend prior, its contribution as an NFP precursor and Stats grading of those rows.
  - Precursors (`scoring/probability_engine.py:512`, same 6-row window, most recent resolved USD row): a filled FF row carries a forecast and can now contribute. A seeded row has no forecast, so `usd_surprise_score()` is None and it contributes nothing.
  - The seed and dry run print the titles whose graded count in the window changes ("trend window ... before -> after"); step 9 lists the same against the step 3 backup, including the hourly backfill's fills.
- Seeded release minutes are new inputs for the release-reaction job (the seed prints "new release minutes for the reaction job").
- No scheduled-task or Telegram change. The first scheduler cycle may write new `prediction_runs` rows for this week's resolved events whose score moved.

OPEN QUESTION (owner): should the trend inputs skip forecast-NULL rows, so seeded rows never push graded rows out of the window? Not built; it extends B8's scope.

## 2. Stop the single engine copy

PowerShell only. Stop the restart-loop windows first, then the Python processes, otherwise the loop restarts them within 5 seconds:

```
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|webapp\.app|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Verify: re-running both `Get-CimInstance ... | Where-Object` queries (without the `Stop-Process`) lists nothing, and `netstat -ano | findstr :5001` is empty.

## 3. Backup

Use the SQLite backup API:

```
python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" webapp/dashboard.db webapp/dashboard.db.pre_b8_<date>
```

Verify the `event_history` row count is equal in both files:

```
python -c "import sqlite3; [print(p, sqlite3.connect('file:'+p+'?mode=ro', uri=True).execute('SELECT COUNT(*) FROM event_history').fetchone()[0]) for p in ('webapp/dashboard.db','webapp/dashboard.db.pre_b8_<date>')]"
```

## 4. Merge

Merge `b8-surprise-metric` into `news-engine/batch-predictions-queries` and fast-forward the live worktree. No push.

## 5. Dry run

Record the 2026 USD row count and actual count before the seed (the same command runs again in step 7):

```
python -c "import sqlite3; print(sqlite3.connect('file:webapp/dashboard.db?mode=ro', uri=True).execute('SELECT COUNT(*), SUM(actual IS NOT NULL) FROM event_history WHERE country=? AND event_time_utc >= ?', ('USD','2026-01-01')).fetchone())"
```

Then:

```
python scripts/seed_fred_history.py --report C:/Users/Masoodt/b8_deploy/b8_seed_dryrun.txt
```

Nothing is written. If it exits 3 / prints "FRED under maintenance": stop here, start the engine on the merged code (step 8) and retry the seed later; nothing was written. Exit 4 means the `--report` folder does not exist; nothing was fetched or written. Otherwise review the report:

- Every High title is verified. A suspect or unavailable title is listed for the owner and left out.
- Insert and fill counts look sane.
- New release minutes are the expected New York release times (shown in SAST with the UTC value beside it).
- "trend window" lists each title whose graded rows among its 6 most recent change (before -> after). Tell the owner which titles drop and which gain (section 1): this is a scoring effect on the accumulator's trend prior.

## 6. Apply

```
python scripts/seed_fred_history.py --apply --report C:/Users/Masoodt/b8_deploy/b8_seed_apply.txt
```

The first line is `APPLIED - rows written`. It also makes its own `pre_b8` backup and prints the path. Record the apply time (UTC and SAST) and the line `seed run recorded_at_utc (rollback key for this run's inserts): ...` exactly as printed: every row this run inserted carries that `recorded_at_utc`, and the rollback (section 11) needs it. If a later `--apply` (for example a retried title) inserts rows, record its key too.

## 7. Verify idempotency

Rerun:

```
python scripts/seed_fred_history.py --apply
```

It must print `APPLIED - nothing to write` and then `inserts: 0  fills: 0  new release minutes for the reaction job: 0` (no backup is made when nothing is written). Then record the counts after the apply next to the step 5 counts in the deploy note:

```
python -c "import sqlite3; print(sqlite3.connect('file:webapp/dashboard.db?mode=ro', uri=True).execute('SELECT COUNT(*), SUM(actual IS NOT NULL) FROM event_history WHERE country=? AND event_time_utc >= ?', ('USD','2026-01-01')).fetchone())"
```

The row count grows by the apply's inserts, the actual count by inserts plus fills.

## 8. Start exactly one copy

```
schtasks /run /tn NewsEngine_AutoStart
```

Within the first cycle the log shows either `[actuals_backfill] filled N` or nothing (no error). `GET http://localhost:5001/api/predictions` and `GET /api/stats/events` return 200.

## 9. Re-score report after seed

Run it after the first `[actuals_backfill]` pass, so the hourly backfill's fills are included:

```
python scripts/b8_rescore_report.py --before-db webapp/dashboard.db.pre_b8_<date> --out C:/Users/Masoodt/b8_deploy/b8_rescore_after_seed.md
```

Read-only (both files opened `mode=ro`). Tell the owner the direction-change count and the "Trend window changes" table (graded rows before and now, per title).

## 10. Log the scoring change

The controller records "B8 scoring change live since <SAST time>" in the roadmap status line and the inventory row. Reviews of essence calls, precursor contributions and accumulator trend priors use data from that instant only.

## 11. Rollback

Stop as in step 2, `git revert` the merge, restart. Filled actuals are kept by first-writer-wins either way. Restore the `pre_b8` backup only if needed.

Seeded rows can stay (they are real first prints) or be removed while the engine is stopped. Only rows the seed inserted may go. The rollback matches the seed insert's exact signature: source `fred`, impact NULL, forecast NULL and `recorded_at_utc` equal to the run key recorded in step 6. Never delete on source and time alone: Forex Factory rows that appear after the apply and later get a FRED actual (same-day fast path or hourly backfill) are also relabelled source `fred`, and they carry graded forecast/previous/actual that FF's current-week feed cannot rebuild. Those rows always carry an impact and keep their own `recorded_at_utc`, so they never match (tested in `tests/test_seed_fred_history.py`). A seeded row that FF later updated (impact filled in) is left alone too.

Count first (opens the DB read-only); the number must equal that run's `inserts:` count:

```
python scripts/seed_fred_history.py --rollback "<seed run recorded_at_utc>"
```

Then delete:

```
python scripts/seed_fred_history.py --rollback "<seed run recorded_at_utc>" --apply
```

It prints `deleted: N seeded rows of run ...`. Repeat both for every recorded key (one per `--apply` run that inserted rows). A key without a UTC offset or a typo is refused with exit 2 and nothing is touched.

## U2 root cause

`data_layer/calendar_feed.py:383` reads `actual=item.get("actual") or None`, but the FairEconomy weekly JSON never carries an actual: 0 of 585 `source='live'` rows have one, and the snapshot of 2026-10-27 shows actual None on all 26 events including ones already released. Every actual therefore comes from a fallback, and both fallbacks are gated to a handful of mostly-High titles:

- The FRED fast path (`webapp/scheduler.py:205-209`) only covers the 10 titles in `config/settings.py:153` `FRED_SERIES_ID_BY_EVENT_TITLE`, and only while the release is still in FF's this-week feed.
- The web fallback queue (retired by ACT, 2026-10-28) admitted only the 19 titles in `EVENT_SURPRISE_DIRECTION` within 48 h.
- Medium and Low titles have no path at all.

2026 USD past rows with an actual (2026-10-27): High 31/42, Medium 3/40, Low 2/166.

## Revisions (U4)

Every FRED-sourced value is the first print from the ALFRED vintage dated the release day (what the market reacted to), never FRED's latest revision. `previous` is the prior period as published that day (revised). NFP and Retail Sales headlines are computed inside that vintage (new level minus/over the revised prior level), which is how BLS/Census publish them. Revisions to earlier months are not folded into the surprise (no consensus for revisions exists here). The existing same-day fast path (`fred_actuals.get_actual_from_fred`, latest vintage, release week only) is kept: on release day it returns the same first print.

## Known limits (not fixed in B8)

- U2 coverage. Live read-only check (2026-10-28): 210 past Medium/Low USD rows have no actual. 53 are on FRED-mapped titles; 10 of those are older than the backfill's 45-day lookback (`BACKFILL_LOOKBACK_DAYS` in `webapp/actuals_backfill.py`) and will never fill, so at most 43 can fill, and only where FF's `previous` matches FRED. The other 157 have no path at all (see "Not covered"). A one-off long-lookback backfill for the 10 older rows is possible but not built (owner's call).
- The 22 Medium/Low series (`FRED_HISTORY_SPECS` entries without `seed=True`) are not checked at deploy: the dry run covers seed titles only. A wrong mapping only shows up as a `previous` mismatch at fill time, and the hourly backfill logs only `filled N`, not its skip reasons, so such a title silently never fills.
- Empire State Manufacturing Index maps to `GACDINA066MSFRBNY` (`data_layer/fred_history.py`), which looks like the not-seasonally-adjusted series [Likely]; FF prints the seasonally adjusted headline (`GACDISA066MSFRBNY`; Philly correctly uses `GACDFSA066MSFRBPHI`). Expect Empire State to stay unfilled (previous mismatch) until the owner confirms and corrects the series id.
- CPI y/y and Core CPI y/y use the seasonally adjusted indexes (`CPIAUCSL`, `CPILFESL`, `pc1`). BLS publishes the 12-month change from the unadjusted indexes (`CPIAUCNS`, `CPILFENS`), and the rounded figures can differ by 0.1 in some months. A seed or backfill fill would then set `surprise_direction` (the Stats grading truth) from a number that is not the headline. The verification gate partly checks itself here: stored CPI actuals with source `fred` come from the same SA series via the fast path, so they always agree. Moving both titles to the NSA series (and leaving source `fred` rows out of the agreement count) is the owner's call; the existing fast path makes the same SA choice.

## Not covered

- No FRED mapping, so no path to an actual (157 of the 210 rows above, by title count on 2026-10-28): Fed, FOMC member, Treasury and President speeches, Beige Book and the Monetary Policy Report (no number); bond auctions (10-y, 30-y); ISM Manufacturing/Services PMI and ISM Manufacturing Prices; S&P Flash and Final Manufacturing/Services PMIs; UoM Consumer Sentiment and Inflation Expectations (Prelim and Revised); CB Consumer Confidence and CB Leading Index; Chicago PMI; Richmond Manufacturing Index; NAHB Housing Market Index; NFIB Small Business Index; RCM/TIPP Economic Optimism; Challenger Job Cuts; ADP Weekly Employment Change; EIA Crude Oil Inventories and Natural Gas Storage; API Weekly Statistical Bulletin; Omdia Total Vehicle Sales; TIC Long-Term Purchases; Pending Home Sales; Goods Trade Balance, Current Account, Prelim Wholesale Inventories, Final GDP Price Index, Revised Nonfarm Productivity and Unit Labor Costs (FRED has series for some of these; not mapped in B8).
- GDP (three estimates per quarter) and the proprietary surveys above (ISM, UoM, Conference Board, S&P PMIs): no exact free FRED series.
- The web-fallback cloud routine has written 0 rows ever (0 `cloud_web_fallback` rows). It is a Claude scheduled task, outside B8; owner to decide.
- FRED has no consensus forecasts, so seeded rows carry actual + previous only and do not deepen any indicator's sigma.

## OPEN QUESTION (owner): JOLTS surprise direction

Should a JOLTS surprise direction exist (higher openings = USD bullish?) so the existing JOLTS -> NFP 0.40 link (`config/settings.py:443`) can ever contribute? No direction is set until the owner decides; JOLTS actuals are now filled but carry no `surprise_direction`.
