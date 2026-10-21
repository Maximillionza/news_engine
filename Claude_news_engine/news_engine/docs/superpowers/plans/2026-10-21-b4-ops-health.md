# B4 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Silent failures are noticed within a day (one health view, one Telegram notice per UTC day), and the pointless work stops: the 28 stuck predictions get a final grade and are never re-fetched, logs are timestamped and capped, failing RSS feeds back off, only one engine copy runs, the macro calendar refreshes again, and the near-miss log stops growing without bound. No change to how calls are scored.

**Architecture:** A new `ops/` package holds the cross-cutting pieces: `ops/state.py` (small `ops/ops_state.db`: per-job last run / last success, the once-per-day health-notice ledger), `ops/run_job.py` (the wrapper every scheduled `.bat`/`.vbs` now calls: rotates the log, timestamps every line, records success), `ops/single_instance.py` (OS file lock + port probe for `webapp/app.py` and `scripts/run_accumulator.py`) and `ops/health.py` (one function that grades every job and feed against its expected interval; served at `GET /api/health`, drawn as a dashboard strip, and turned into at most one Telegram notice per UTC day from the shock poll and the outcome job). Feed backoff and near-miss trimming live in the poller's own DB (`alerting/store.py`); the final "no reaction" outcome reuses `record_outcome`.

**Tech Stack:** Python 3 / SQLite / Flask (waitress), pytest; vanilla ES modules + `node --test` (jsdom); BAT/VBS launchers.

**Spec:** `docs/roadmap-2026-10-20.md` §B4 (O3-O8, K15), plus these owner decisions:
- O3: a prediction whose event is more than 3 days old and whose move is still below the threshold is recorded as a final "no reaction" outcome, shown as a final grade in History and never re-polled. Applies automatically on the next scheduled run after deploy.
- O5: back off first; a feed still failing after 2 weeks is reported (as a drop candidate), never dropped automatically.
- O6: at most ONE Telegram health notice per UTC day, B2 once-per-day pattern; triggered from the shock poller or the outcome job.
- O8 (found 2026-10-20): two full engine copies ran (AutoStart task at logon + desktop `News Engine.bat`), each with its own Flask scheduler. A second launch must exit cleanly without a tight restart loop; a crashed instance must not block a restart.
- K15: skip a headline already logged in the last 24h, keep 30 days, raise the threshold modestly (old 0.3, new 0.5).
- Out of scope: scoring, shock severity/leans, grading (B10), dead-code removal (B11).

Audit evidence: GR-1, DEAD-2, DEAD-4, OPS-1, OPS-2, OPS-3, SA-08, AUD-P2-10, BM-4.9.

App dir for every command: `.worktrees/b4-ops-health/Claude_news_engine/news_engine`. Full suite = `python -m pytest -q -p no:warnings` (baseline 1580 passed, 1 env-only failure) + `npm test` (baseline 216/216). Known env-only failure (no `.env` in a worktree): `tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present`; ignore it, everything else must pass.

## Global Constraints

- **Live system off-limits:** no change to `.worktrees/news-engine-live`, any live `*.db`, Windows scheduled tasks, Claude scheduled tasks (`C:\Users\Masoodt\.claude\scheduled-tasks` read-only) or Telegram (mock `send_notice` / `send_alert`). No push.
- **No outside-repo changes are needed:** every NewsEngine_* Windows task already runs a `.bat`/`.vbs` inside the live worktree (verified read-only with `Get-ScheduledTask`), so the launcher edits take effect at merge. Backups, the one-instance restart and verification go in `docs/b4-deploy.md`, applied by the controller.
- **Tests:** temp / `:memory:` DBs, injected clocks, no network. `tests/conftest.py` gains `ops.state.DB_PATH -> tmp_path / "ops_state.db"` (autouse) so no test can write the real `ops/ops_state.db`.
- **Fail-open everywhere new:** logging, heartbeats, health building and the health notice must never stop the job they run in (shock poll, outcome confirm, scheduler, accumulator). A locked log file never crashes a run.
- **DB patterns:** CREATE IF NOT EXISTS in each store's `get_connection`; `outcomes` stays append-only (`record_outcome`, plain INSERT); state tables (`job_runs`, `source_health`) are idempotent upserts; the only DELETE in B4 is the bounded near-miss prune.
- **Times:** stored UTC ISO; owner-facing text (log prefixes, notice, dashboard, detail strings) in SAST via `config.settings.LOCAL_TZ`, format `%Y-%m-%d %H:%M SAST` (log prefix adds `:%S`). Compare instants with `julianday()` in SQL, never raw strings.
- **Style:** type hints on every Python signature; match surrounding comment density; routes keep exact key-set tests; vanilla ES modules.
- **Line endings:** every touched existing file is CRLF; keep CRLF, new `.py`/`.js`/`.bat`/`.md` files CRLF too. Regexes written from a heredoc: check for a 0x08 byte (`od -c`) if you use `\b`; write any edit script containing backslashes to a file with the Write tool and run that file.
- **Commits:** one per task on `b4-ops-health`; message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **The logging wrapper takes a job down.** A locked or rotating log, a full pipe (child blocks on output nobody drains) or a wrapper bug would silence the 2-minute shock poll, which is worse than the log growth it fixes.
   - Pinned by `test_locked_log_never_breaks_the_job`, `test_large_child_output_does_not_deadlock` and `test_wrappers_route_every_scheduled_job_through_run_job` (Task 1).
2. **"Final no reaction" applied to the wrong rows.** A fetch failure (no price data) or a row 3 days old or younger must stay awaiting; a finalised row must never be fetched again.
   - Pinned by `test_fetch_failure_older_than_3_days_is_not_finalised`, `test_below_threshold_within_3_days_stays_awaiting`, `test_final_rows_are_never_re_polled` (Task 3).
3. **Single instance done wrong.** A stale lock from a crashed process blocking every restart; the second copy starting its scheduler (Forex Factory calls) before it notices; the restart loop relaunching a refused copy every 5 seconds.
   - Pinned by `test_lock_is_released_when_the_holder_dies`, `test_app_claims_single_instance_before_starting_the_scheduler`, `test_restart_loop_stops_on_exit_code_3` (Task 4).
4. **Health false alarms or false calm.** Weekly/monthly jobs that have not run since deploy shown red on day one; Tier 1 rows compared as strings; a notice every 2 minutes instead of once a day; a health error breaking the poll.
   - Pinned by `test_never_run_job_is_amber_until_red_after_tracking`, `test_missed_release_compares_naive_and_offset_stamps_as_instants`, `test_health_notice_sent_once_per_utc_day_listing_red_items_only`, `test_notice_never_raises` (Task 5).
5. **Backoff or pruning hurts the healthy path.** A healthy feed skipped because another failed; backoff logged on every cycle; a prune that deletes recent near-misses or one huge DELETE inside a 2-minute poll.
   - Pinned by `test_healthy_feed_unaffected_by_a_failing_one`, `test_backoff_enters_once_and_recovery_logs_once` and `test_prune_near_misses_keeps_30_days_and_is_bounded` (Task 2).

## Plan decisions (beyond the spec text)

- **O3 representation: an `outcomes` row with `actual_direction = "neutral"`, not a dismissal.** History (`webapp/history.py:357-360, 469-472`) grades only from `get_outcome()`; a dismissal leaves the row "pending" forever, so it cannot give the final grade the owner asked for. With a neutral outcome a bullish/bearish call reads **Missed** (the market did not move its way) and a neutral call above the shrug threshold reads Confirmed; `scoring/backtest.py` counts it the same way (neutral predictions stay "no call"). `outcome_classifier.classify` is unchanged (it still never returns neutral); the 3-day finalisation lives in the confirm script and its note says so. Dismissals stay for rescheduled/cancelled events (manual).
- **Fetch failures (no price data) are never finalised:** "no data" is not "no reaction". They stay awaiting and show as amber in the health check ("N awaiting more than 3 days").
- **O7 root cause [Certain]:** `scripts/refresh_macro_calendar.py` is self-gated ("safe to invoke on any schedule") but nothing ever invoked it: no Windows task, no Claude task, no caller in code. It ran once by hand on 2026-08-16T10:48Z (all 21 rows share that `recorded_at_utc`; the shared checkout's marker file holds the same instant) with a 35-day window, so the last row is 2026-09-17; later `updated_at_utc` stamps (to 2026-09-18) are the scheduler's Forex Factory confirmations, not refreshes. The live worktree has no marker file. Not external (FRED key present). Fix: the webapp scheduler calls the self-gated refresh every iteration; a run that writes nothing no longer marks itself done (retries after 6h); O6 shows staleness and an exhausted horizon.
- **Heartbeats, not data timestamps, for jobs that may legitimately write nothing** (outcome confirm with nothing to confirm, reaction compute with no new release, Tier 1 capture with nothing due, a quiet calendar): the wrapper records each exit code; the scheduler and accumulator loops record their own heartbeat. Data timestamps are used as a fallback where they exist.
- **A job never seen since tracking started is amber, then red** once the time since `tracking_since_utc` (first `ops_state.db` connection) passes its red threshold, so the weekly/monthly jobs are not red on deploy day but a task that never fires is still caught.
- **Feed in backoff = amber; failing 14+ days = red ("drop candidate")**, so the daily notice reports a feed only when the owner's 2-week rule is met.
- **Health notice triggered from both** the shock poll and the outcome job: each covers the other's death; the daily ledger keeps it to one notice.
- **O3 also builds the `tier1_comparisons` row** for a finalised occurrence (same hook as an auto-confirmed outcome), so a directional Tier 1 call on a no-reaction release is graded wrong there too, consistent with History.
- **The weekly shock reality check is in the health list** (not named in the spec): it is a scheduled job with one of the five logs, and a check costs one row.
- **`alerting/reality_check.py` prints a one-line summary** (it logged 0 bytes; OPS-3), so its timestamped log is useful.
- **Near-miss threshold 0.5:** live scores are discrete (1/3, 1/2, 2/3, 3/4, 1); 0.5 drops the one-word-of-three overlaps (3,479 of 8,334 rows). SA-08's 0.67 would keep only the 3/4 and full matches (173 of 8,334 rows; 2/3 = 0.667 falls just below it), too aggressive for "modestly".
- **Not changed:** `CLAUDE_COOLDOWN_MINUTES`, provider order, the classifier itself (OPS-1's billing decision is the owner's); B4 only makes the outage visible.

---

### Task 1: Ops state, job wrapper and log rotation (O4, heartbeat base) — *integration*

**Files:**
- Create: `ops/__init__.py` (empty), `ops/state.py`, `ops/run_job.py`, `tests/test_ops_state.py`, `tests/test_ops_run_job.py`
- Modify: `scripts/confirm_outcomes_scheduled.bat`, `scripts/reaction_compute_scheduled.bat`, `scripts/tier1_capture_scheduled.bat`, `alerting/scripts/poll_once_hidden.vbs`, `alerting/scripts/reality_check_hidden.vbs`, `alerting/reality_check.py`, `tests/test_alerting_reality_check.py`, `tests/conftest.py`, `.gitignore` (add `*.log.1`, `ops/*.lock`, `ops/*.pid`)

**Interfaces:**
- `ops/state.py` (stdlib imports only):
  - `DB_PATH = Path(__file__).parent / "ops_state.db"` (resolved inside `get_connection`, so the conftest patch works).
  - `JOB_NAMES: tuple[str, ...] = ("shock_poll", "shock_reality_check", "outcome_confirm", "reaction_incremental", "reaction_baselines", "tier1_capture_daily", "tier1_capture_weekly", "article_accumulator", "calendar_refresh")`.
  - Schema: `job_runs(job TEXT PRIMARY KEY, last_run_utc TEXT NOT NULL, last_exit_code INTEGER NOT NULL, last_success_utc TEXT)`; `health_notices(utc_date TEXT PRIMARY KEY, sent_at_utc TEXT NOT NULL, detail TEXT)`; `ops_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)`.
  - `def get_connection(db_path: Optional[Path | str] = None, now: Optional[dt.datetime] = None) -> sqlite3.Connection` — `row_factory = sqlite3.Row`, runs the schema, `INSERT OR IGNORE` `('tracking_since_utc', now.isoformat())`.
  - `@dataclass(frozen=True) class JobRun: job: str; last_run_utc: dt.datetime; last_exit_code: int; last_success_utc: Optional[dt.datetime]`.
  - `def record_job_run(conn, job: str, finished_utc: dt.datetime, exit_code: int) -> None` — `ValueError` for a job not in `JOB_NAMES`; upsert; `last_success_utc` set only when `exit_code == 0`, otherwise kept.
  - `def get_job_runs(conn) -> dict[str, JobRun]`; `def get_tracking_since(conn) -> dt.datetime`.
  - `def touch_heartbeat(job: str, now: Optional[dt.datetime] = None, db_path: Optional[Path] = None) -> None` — `record_job_run(..., exit_code=0)`; swallows every exception after one `[ops.state] WARNING: ...` print.
  - `def health_notice_sent(conn, utc_date: dt.date) -> bool`; `def record_health_notice(conn, utc_date: dt.date, sent_at_utc: dt.datetime, detail: str) -> None` (INSERT OR IGNORE; mirrors `alerting/store.py` `outage_notice_sent` / `record_outage_notice`).
- `ops/run_job.py`:
  - `LOG_MAX_BYTES = 1_000_000`, `LOG_BACKUPS = 1`.
  - `def timestamp_prefix(now_utc: dt.datetime) -> str` — `now_utc.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S SAST")`.
  - `def rotate_if_needed(log_path: Path, max_bytes: int = LOG_MAX_BYTES, backups: int = LOG_BACKUPS) -> bool` — when size >= `max_bytes`: shift `.N` files up (dropping beyond `backups`) and `os.replace(log, log.1)`; returns True if rotated; any `OSError` -> False plus one stderr warning (another process holding the file is normal).
  - `def _open_log(log_path: Path) -> Optional[TextIO]` — append mode, UTF-8; None (plus one stderr warning) on `OSError`. The test seam for a locked log.
  - `def run_logged(job: str, log_path: Path, child_args: list[str], *, max_bytes: int = LOG_MAX_BYTES, backups: int = LOG_BACKUPS, clock: Callable[[], dt.datetime] = <utc now>, ops_db: Optional[Path] = None) -> int` — rotate; open the log for append (`OSError` -> keep going without a log); write `"{prefix} [run_job] {job} starting: python {args}"`; `subprocess.Popen([sys.executable, "-u", *child_args], stdout=PIPE, stderr=STDOUT, text=True, encoding="utf-8", errors="replace", env=os.environ | {"PYTHONIOENCODING": "utf-8"})`; read line by line until EOF (this drains the pipe), write `"{prefix} {line.rstrip()}"` per line and flush; a write `OSError` drops the log for the rest of the run but keeps draining; after `wait()` write `"{prefix} [run_job] {job} finished (exit {code})"`; `record_job_run` fail-open; return the child's code (a child that cannot start -> logged, recorded as exit 1, returns 1).
  - `def main(argv: Optional[list[str]] = None) -> int` — usage `python -m ops.run_job --job NAME --log PATH -- <python args>`: split argv at the first `--`; argparse on the part before (`--job` with `choices=JOB_NAMES`, `--log` required); missing `--` or nothing after it -> `parser.error` (exit 2). `if __name__ == "__main__": sys.exit(main())`.
- Launchers (keep their REM/comment headers, update the wording; `cd /d "%~dp0.."` and `set PYTHONIOENCODING=utf-8` stay; the `echo [%DATE% %TIME%] ... >> log` lines and every `>>` go, the wrapper writes the start/finish lines; each `.bat` ends `exit /b %ERRORLEVEL%`):
  - `confirm_outcomes_scheduled.bat`: `python -m ops.run_job --job outcome_confirm --log scripts\confirm_outcomes_scheduled.log -- scripts\confirm_backtest_outcomes.py --auto --list`
  - `reaction_compute_scheduled.bat`: `set JOB=reaction_incremental`, and `reaction_baselines` in the `baselines` branch; `python -m ops.run_job --job %JOB% --log scripts\reaction_compute_scheduled.log -- scripts\compute_release_reactions.py %MODE% --bt-db scoring\backtest_log.db --dash-db webapp\dashboard.db`
  - `tier1_capture_scheduled.bat`: `set JOB=tier1_capture_daily`, `tier1_capture_weekly` in the `weekly` branch; `python -m ops.run_job --job %JOB% --log scripts\tier1_capture_scheduled.log -- scripts\capture_nowcast_from_cleveland.py --window-hours %WINDOW% --bt-db scoring\backtest_log.db --dash-db webapp\dashboard.db`
  - `poll_once_hidden.vbs`: `cmd = "cmd /c cd /d """ & projectRoot & """ && """ & pythonPath & """ -m ops.run_job --job shock_poll --log alerting\poll_once.log -- -m alerting.poll_once"` (`logPath` variable removed).
  - `reality_check_hidden.vbs`: same shape, `--job shock_reality_check --log alerting\reality_check.log -- -m alerting.reality_check`.
- `alerting/reality_check.py`: `def run_reality_check(conn=None) -> dict` returns `{"checked": int, "mismatches": int, "no_price_data": int}` (`_check_alert` returns which of the three happened); `__main__` prints `[reality_check] checked {checked} alert(s): {mismatches} mismatch(es), {no_price_data} without price data`.

**Steps:**
- [ ] Write failing tests in `tests/test_ops_state.py`:
  - `test_record_job_run_keeps_last_success_across_a_failure` — exit 0 at `2026-10-21T09:00Z`, exit 2 at `09:15Z` -> `last_exit_code == 2`, `last_run_utc == 09:15Z`, `last_success_utc == 09:00Z`.
  - `test_record_job_run_rejects_an_unknown_job` — `ValueError`.
  - `test_tracking_since_is_set_once` — first connection `now=2026-10-21T08:00Z`, second `now=2026-10-22T08:00Z` -> still `2026-10-21T08:00Z`.
  - `test_health_notice_ledger_is_one_row_per_utc_day` — record twice for `2026-10-21` -> one row; `health_notice_sent` True for that day, False for `2026-10-22`.
  - `test_touch_heartbeat_never_raises` — `db_path` = a directory -> returns None, nothing raised.
- [ ] Write failing tests in `tests/test_ops_run_job.py` (child args are `-c` snippets, `clock` fixed at `2026-10-21T09:45:21Z`, `ops_db` in `tmp_path`):
  - `test_every_child_line_gets_a_sast_timestamp` — child prints `alpha`, `beta` -> log has `2026-10-21 11:45:21 SAST alpha` and `... beta`; every line matches `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} SAST `; first line contains `[run_job] outcome_confirm starting`, last `finished (exit 0)`.
  - `test_child_exit_code_is_returned_logged_and_recorded` — `sys.exit(2)` -> returns 2; log has `finished (exit 2)`; `job_runs` exit 2, `last_success_utc` None.
  - `test_stderr_and_tracebacks_reach_the_log` — child raises `RuntimeError("boom")` -> log contains `RuntimeError: boom`, return code 1.
  - `test_log_over_limit_rotates_to_one_backup` — log prefilled with 1,000,000 bytes, existing `.log.1` containing `old` -> after a run `.log.1` is the 1,000,000-byte file, the new log only holds this run, no `.log.2`.
  - `test_log_under_limit_is_appended_not_rotated` — 10-byte log keeps its first 10 bytes, no `.log.1`.
  - `test_locked_log_never_breaks_the_job` — monkeypatch `ops.run_job.os.replace` to raise `PermissionError` and `ops.run_job._open_log` to return None -> `run_logged` returns 0 and `job_runs` records a success.
  - `test_large_child_output_does_not_deadlock` — child prints 20,000 lines of 100 chars -> returns 0 within the test's default timeout; log has 20,002 lines.
  - `test_main_rejects_unknown_job_and_missing_separator` — `main(["--job", "nope", "--log", x, "--", "-c", "pass"])` and `main(["--job", "shock_poll", "--log", x])` each raise `SystemExit` with code 2.
  - `test_wrappers_route_every_scheduled_job_through_run_job` — read bytes of the 3 `.bat` and 2 `.vbs`: each contains the exact `-m ops.run_job --job ... --log ...` command above (both job names for the two two-mode `.bat`s), no line runs python with `>>`, and every line ends `\r\n` (no bare `\n`).
- [ ] Add to `tests/test_alerting_reality_check.py`: `test_run_returns_counts` — one High alert with no move (mismatch), one alert without price data -> `{"checked": 2, "mismatches": 1, "no_price_data": 1}`.
- [ ] Run `python -m pytest -q -p no:warnings tests/test_ops_state.py tests/test_ops_run_job.py tests/test_alerting_reality_check.py` — expect FAIL.
- [ ] Implement as specified; add the conftest patch (`monkeypatch.setattr("ops.state.DB_PATH", tmp_path / "ops_state.db")` inside the existing autouse fixture) and the `.gitignore` lines.
- [ ] Run the three files — expect PASS. Then the full suites.
- [ ] Commit: `feat(B4): ops job wrapper - timestamped, size-rotated logs and per-job run records (O4)`.

---

### Task 2: Shock poller — feed backoff (O5) and near-miss trim (K15) — *integration*

**Files:**
- Create: `alerting/source_backoff.py`, `tests/test_alerting_source_backoff.py`, `tests/test_rss_sources.py`
- Modify: `data_layer/rss_sources.py`, `alerting/store.py`, `alerting/poll_once.py`, `alerting/taxonomy.py`, `tests/test_alerting_store.py`, `tests/test_alerting_poll_once.py`

**Interfaces:**
- `data_layer/rss_sources.py`: `class RSSParseError(ValueError)`; `RSSNewsSource.fetch(self, query: str, since_utc: dt.datetime, limit: int = 50, *, raise_on_parse_error: bool = False)` and `_parse_rss(..., raise_on_parse_error: bool = False)` — with the flag a parse error raises `RSSParseError(f"failed to parse feed '{self.name}': {exc}")`; without it today's print-and-empty behaviour is unchanged (the accumulator's `fetch_from_all_sources` keeps it).
- `alerting/source_backoff.py` (pure):
  - `FEED_BACKOFF_AFTER_FAILURES = 3`, `FEED_BACKOFF_BASE = dt.timedelta(minutes=10)`, `FEED_BACKOFF_MAX = dt.timedelta(hours=6)`, `FEED_DROP_REVIEW_AFTER = dt.timedelta(days=14)`.
  - `def backoff_delay(consecutive_failures: int) -> Optional[dt.timedelta]` — None below 3; else `min(BASE * 2 ** (n - 3), MAX)`.
  - `def in_backoff(health: Optional[SourceHealth], now: dt.datetime) -> bool` — `backoff_until_utc` set and `now < backoff_until_utc`.
  - `def is_drop_candidate(health: Optional[SourceHealth], now: dt.datetime) -> bool` — `failing_since_utc` set and `now - failing_since_utc >= 14 days`.
- `alerting/store.py`:
  - Table `source_health(source TEXT PRIMARY KEY, consecutive_failures INTEGER NOT NULL DEFAULT 0, failing_since_utc TEXT, backoff_until_utc TEXT, last_success_utc TEXT, last_failure_utc TEXT, last_error TEXT)` in `_SCHEMA`; indexes `idx_near_miss_headline_seen ON shock_near_misses(headline, seen_at_utc)` and `idx_near_miss_seen ON shock_near_misses(seen_at_utc)` (existing columns, so safe in `_SCHEMA`).
  - `@dataclass class SourceHealth` with those columns (datetimes parsed with `_parse_utc`, None kept).
  - `def get_source_health(conn, source: str) -> Optional[SourceHealth]`; `def list_source_health(conn) -> list[SourceHealth]`.
  - `def record_source_success(conn, source: str, now: dt.datetime) -> Optional[SourceHealth]` — returns the previous row when it had failures (so the caller can log recovery), else None; resets failures to 0 and `failing_since`/`backoff_until` to NULL, sets `last_success_utc`.
  - `def record_source_failure(conn, source: str, now: dt.datetime, error: str, backoff_until: Optional[dt.datetime]) -> SourceHealth` — increments, keeps the first `failing_since_utc` of the streak, sets `last_failure_utc`, `last_error = error[:300]`, `backoff_until_utc`.
  - `NEAR_MISS_REPEAT_WINDOW = dt.timedelta(hours=24)`, `NEAR_MISS_RETENTION = dt.timedelta(days=30)`, `NEAR_MISS_PRUNE_BATCH = 500`.
  - `record_near_miss(...) -> Optional[int]` — returns None without inserting when the same headline has a row with `seen_at_utc >= seen_at - 24h`.
  - `def prune_near_misses(conn, now: dt.datetime, retention: dt.timedelta = NEAR_MISS_RETENTION, max_rows: int = NEAR_MISS_PRUNE_BATCH) -> int` — deletes at most `max_rows` of the oldest rows with `julianday(seen_at_utc) < julianday(cutoff)`; returns the count.
- `alerting/taxonomy.py`: `NEAR_MISS_LOG_THRESHOLD = 0.5` with a comment: was 0.3 until B4 (2026-10-21); scores are word-overlap fractions (1/3, 1/2, 2/3, 3/4, 1), 0.3 logged single-word overlaps (3,479 of 8,334 live rows).
- `alerting/poll_once.py` `run_poll_cycle`:
  - Per feed: `health = store.get_source_health(conn, name)`; `in_backoff(health, now)` -> skip silently (no fetch, cursor untouched). Otherwise `fetch(query="", since_utc=since, limit=50, raise_on_parse_error=True)`.
  - Failure: `n = previous failures + 1`, `delay = backoff_delay(n)`, `record_source_failure(..., backoff_until=now + delay if delay else None)`. Print `[poll_once] WARNING: fetch failed for source {name!r}: {exc}` when `n < 3`; exactly `[poll_once] source {name!r} in backoff after 3 consecutive failures, skipped until {until SAST} (last error: {exc})` when `n == 3`; nothing when `n > 3`.
  - Success: `prev = record_source_success(...)`; when `prev` had >= 3 failures print `[poll_once] source {name!r} recovered after {prev.consecutive_failures} consecutive failures (failing since {SAST})`.
  - Near misses: `record_near_miss(..., seen_at_utc=now)`; once per cycle `store.prune_near_misses(conn, now)`.

**Steps:**
- [ ] Write failing tests:
  - `tests/test_rss_sources.py::test_parse_error_raises_only_when_asked` — `requests.get` patched to return `b"<rss><channel><item>"` -> default `fetch` returns `[]`; with `raise_on_parse_error=True` -> `RSSParseError` whose message names the feed.
  - `tests/test_alerting_source_backoff.py::test_backoff_delay_doubles_from_10_minutes_and_caps_at_6_hours` — n 1, 2 -> None; 3 -> 10m; 4 -> 20m; 5 -> 40m; 8 -> 320m; 9 -> 6h; 20 -> 6h.
  - `test_drop_candidate_after_14_days_of_failing` — failing since `now - 13d 23h` -> False; `now - 14d` -> True; None health -> False.
  - `tests/test_alerting_store.py::test_source_failure_streak_and_reset` — two failures keep the first `failing_since_utc`; success returns the previous row (failures 2) and resets; a success on a clean row returns None.
  - `test_near_miss_repeat_within_24h_is_skipped` — same headline at t0 -> id, t0+23h -> None, t0+25h -> id; another headline at t0+1m -> id. (Existing `test_record_near_miss` keeps passing.)
  - `test_prune_near_misses_keeps_30_days_and_is_bounded` — 3 rows at now-31d, 1 at now-29d: `prune(max_rows=2)` -> 2, then 1, then 0; the now-29d row remains.
  - `tests/test_alerting_poll_once.py` (one fake feed `feed_a`, `_utcnow` patched to t0 = `2026-10-21T08:00Z` + 2-minute steps):
    - `test_backoff_enters_once_and_recovery_logs_once` — `feed_a` raises at t0, +2m, +4m -> `backoff_until_utc == t0+4m+10m`, the "in backoff after 3" line printed once (capsys); cycle at +6m -> fetch call count stays 3; at +15m fails again -> failures 4, backoff +20m, no new "in backoff" line; at +36m succeeds -> "recovered after 4 consecutive failures" printed once, row reset, next cycle fetches normally.
    - `test_healthy_feed_unaffected_by_a_failing_one` — feeds `feed_a` (always raises) and `feed_b` (returns one article): over 5 cycles `feed_b` fetched 5 times, its cursor advances, its row has 0 failures and `last_success_utc` = last cycle.
    - `test_parse_error_counts_as_a_failure` — fetch raises `RSSParseError` -> failures 1; assert the poller passed `raise_on_parse_error=True`.
    - `test_near_miss_below_new_threshold_is_not_logged` — `NEAR_MISS_LOG_THRESHOLD == 0.5`; triage near-miss score 1/3 -> no row; 0.5 -> one row; the same 0.5 headline next cycle -> still one row.
    - `test_poll_cycle_prunes_old_near_misses` — a row at t0-31d is gone after one cycle.
- [ ] Run the five test files — expect FAIL.
- [ ] Implement as specified. The existing `test_one_source_fetch_failure_does_not_block_others` must still pass unchanged.
- [ ] Run the five files — expect PASS. Then the full suites.
- [ ] Commit: `feat(B4): RSS feed backoff with once-only enter/recover logs; near-miss repeat skip, 30-day retention, threshold 0.3->0.5 (O5, K15)`.

---

### Task 3: Final "no reaction" outcome after 3 days (O3) — *judgment*

**Files:**
- Modify: `scripts/confirm_backtest_outcomes.py`, `tests/test_confirm_backtest_outcomes.py`, `tests/test_webapp_history.py`

**Interfaces:**
- `scripts/confirm_backtest_outcomes.py`:
  - `FINAL_NO_REACTION_AFTER = dt.timedelta(days=3)`; `FINAL_NO_REACTION_NOTE_SUFFIX = "; no reaction after 3 days, final (auto)"`.
  - `def is_final_no_reaction(result, event_time_utc: dt.datetime, now: dt.datetime, threshold_pct: float) -> bool` — `result.direction is None and result.move_pct is not None and abs(result.move_pct) < threshold_pct and now - event_time_utc > FINAL_NO_REACTION_AFTER`. The caller passes `CLEAR_MOVE_THRESHOLD_PCT`, imported next to `classify` in the existing lazy import block (bare/`--list` runs must stay free of the Dukascopy import); `outcome_classifier.py` is untouched.
  - `def run_auto_confirm_phase(conn, now: Optional[dt.datetime] = None) -> dict` — keys `auto_confirmed`, `final_no_reaction`, `left_for_review`, `suggestions`; passes `now` to `get_predictions_awaiting_outcome`; a final row -> `record_outcome(conn, title, instrument, event_time, "neutral", result.note + FINAL_NO_REACTION_NOTE_SUFFIX)` then `_try_record_tier1_comparison(..., "neutral", same note)`, printed `  [final] {instrument} / {title}: {note}`; not added to `suggestions`; `left_for_review = len(awaiting) - auto_confirmed - final_no_reaction`.
  - `main()` summary line: `Auto-confirm: {a} confirmed, {f} final no-reaction, {l} left for review.`
  - Docstring of the module and of `run_auto_confirm_phase`: the 3-day rule, why neutral outcome (History grades only outcomes) and that fetch failures are never finalised.

**Steps:**
- [ ] Write failing tests in `tests/test_confirm_backtest_outcomes.py` (classify patched as in the existing tests; below-threshold result = `ClassificationResult(direction=None, move_pct=0.05, note="Dukascopy: +0.05% in 30min, below 0.15% threshold")`):
  - `test_below_threshold_older_than_3_days_is_recorded_final_neutral` — event `2026-08-20T12:30Z`, now `2026-10-21T09:00Z` -> outcome `actual_direction == "neutral"`, `actual_move_note == "Dukascopy: +0.05% in 30min, below 0.15% threshold; no reaction after 3 days, final (auto)"`; summary `final_no_reaction == 1`, `left_for_review == 0`, the key not in `suggestions`.
  - `test_below_threshold_within_3_days_stays_awaiting` — event `now - 2d 23h` and exactly `now - 3d` -> no outcome, both in `suggestions`, `left_for_review == 2`.
  - `test_fetch_failure_older_than_3_days_is_not_finalised` — `move_pct=None` at `now - 10d` -> no outcome, `left_for_review == 1`.
  - `test_final_rows_are_never_re_polled` — run twice with the same now -> classify call count for that row is 1; second summary all zeros.
  - `test_clear_move_is_still_auto_confirmed_regardless_of_age` — bullish 0.34% at `now - 10d` -> outcome "bullish", note without the suffix.
- [ ] Write failing tests in `tests/test_webapp_history.py` (same fixture shape as `test_text_only_event_confirmed_outcome_judged_correctly`):
  - `test_final_no_reaction_outcome_grades_a_directional_call_missed_and_a_neutral_call_confirmed` — FOMC Statement text-only: XAUUSD bullish 0.5 confidence + neutral outcome -> `"Missed"`; a second instrument (US30) neutral 0.5 confidence + neutral outcome -> `"Confirmed"`.
  - `test_a_dismissal_leaves_history_pending` — same event, `record_dismissal` instead -> `outcome is None`, `unjudged_reason == "pending"` (documents why O3 is not a dismissal).
- [ ] Run `python -m pytest -q -p no:warnings tests/test_confirm_backtest_outcomes.py tests/test_webapp_history.py` — expect the new confirm tests to FAIL (the dismissal / grading History tests may already pass: they pin existing behaviour this task relies on).
- [ ] Implement as specified.
- [ ] Run the two files — expect PASS. Then the full suites.
- [ ] Commit: `feat(B4): final no-reaction outcome after 3 days for below-threshold predictions; never re-polled (O3)`.

---

### Task 4: Macro calendar refresh (O7), single instance (O8), loop heartbeats — *integration*

**Files:**
- Create: `ops/single_instance.py`, `tests/test_ops_single_instance.py`
- Modify: `scripts/refresh_macro_calendar.py`, `webapp/scheduler.py`, `scoring/backtest_accumulator.py`, `webapp/app.py`, `scripts/run_accumulator.py`, `scripts/_restart_loop.bat`, `scripts/run_engine.bat` (comment only: a second launch exits with code 3), `tests/test_refresh_macro_calendar.py`, `tests/test_webapp_scheduler.py`, `tests/test_backtest_accumulator.py`

**Interfaces:**
- Consumes: `ops.state.touch_heartbeat(job, now=None, db_path=None)` (Task 1).
- `scripts/refresh_macro_calendar.py` `run()`: when `written == 0` print `[refresh_macro_calendar] WARNING: FRED returned no release dates for any title - not marking the refresh done; will retry.` and return 0 WITHOUT `_record_refresh`. Docstring: the scheduler now calls it (O7 root cause one paragraph).
- `webapp/scheduler.py`:
  - `MACRO_RETRY_AFTER_FAILURE = dt.timedelta(hours=6)`; module state `_macro_retry_not_before: Optional[dt.datetime] = None`.
  - `def maybe_refresh_macro_calendar(now: Optional[dt.datetime] = None) -> Optional[int]` — None while `now < _macro_retry_not_before`; else lazily `import scripts.refresh_macro_calendar` and return `run()`; a result of 0 or any exception (printed as `[scheduler] WARNING: macro calendar refresh failed: ...`) sets `_macro_retry_not_before = now + 6h` (exception -> returns None); -1 (not due / no key) leaves it alone.
  - `def run_scheduler_iteration(tracked_symbols_provider: Callable[[], list[str]], previous_events: Optional[list[EconomicEvent]]) -> tuple[int, Optional[list[EconomicEvent]]]` — today's loop body unchanged (returns `(interval, previous_events)`), plus: `touch_heartbeat("calendar_refresh")` when `run_scoring_cycle` returned a list; then `maybe_refresh_macro_calendar()` in its own try/except on every iteration. `_loop` becomes `interval, previous_events = run_scheduler_iteration(...); time.sleep(interval)`.
- `scoring/backtest_accumulator.py`: `def run_accumulator_iteration(instruments: list[str]) -> int` — today's `_loop` body (returns the interval) plus `touch_heartbeat("article_accumulator")` when `run_accumulator_cycle` returned a list (not None, not an exception). `_loop` calls it then sleeps. No scoring code changes.
- `ops/single_instance.py`:
  - `ALREADY_RUNNING_EXIT_CODE = 3`; `LOCK_DIR = Path(__file__).parent` (files `ops/<name>.lock`, `ops/<name>.pid`).
  - `class InstanceLock` (holds the open lock file; `def release(self) -> None`).
  - `def try_acquire(name: str, lock_dir: Path = LOCK_DIR) -> Optional[InstanceLock]` — open `<name>.lock` in `a+`, `seek(0)`, non-blocking exclusive lock on byte 0 (`msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)` on Windows, `fcntl.flock(fd, LOCK_EX | LOCK_NB)` elsewhere); on `OSError` close and return None; on success write `os.getpid()` to `<name>.pid`. Comment: the OS releases the lock when the process dies, so a crashed instance never leaves a stale lock (no PID-liveness guessing, no PID-reuse risk).
  - `def running_pid(name: str, lock_dir: Path = LOCK_DIR) -> Optional[int]` — the `.pid` content; None on any error.
  - `def port_in_use(port: int, host: str = "127.0.0.1") -> bool` — `socket.connect_ex` with a 0.5 s timeout == 0.
  - `def claim_or_exit(name: str, *, port: Optional[int] = None, lock_dir: Path = LOCK_DIR) -> InstanceLock` — lock busy, or (after locking) `port_in_use(port)` -> release, print `[{name}] another instance is already running (PID {pid or 'unknown'}) - exiting without starting (exit 3)`, `raise SystemExit(ALREADY_RUNNING_EXIT_CODE)`.
- `webapp/app.py` `__main__`: right after the two `reconfigure` calls and BEFORE `_ensure_defaults()` / `start_scheduler(...)`: `_INSTANCE_LOCK = claim_or_exit("webapp", port=5001)` (module-level name so the lock lives as long as the process).
- `scripts/run_accumulator.py` `main()`: first statement `instance_lock = claim_or_exit("accumulator")` (held by `main`'s never-returning frame).
- `scripts/_restart_loop.bat`: after `python %1`, `set EXITCODE=%ERRORLEVEL%`; `if "%EXITCODE%"=="3"` -> echo `[restart-loop] %DATE% %TIME% - %1 is already running in another window; not restarting. This window can be closed.` and `exit /b 3`; the existing restart echo uses `%EXITCODE%`; `goto loop` otherwise unchanged.

**Steps:**
- [ ] Write failing tests:
  - `tests/test_refresh_macro_calendar.py::test_run_does_not_mark_refreshed_when_fred_returns_nothing` — `get_upcoming_release_dates` patched to `[]`, `FRED_API_KEY` patched non-empty, marker in `tmp` -> `run(force=True)` returns 0, marker file absent, `is_due()` True.
  - `tests/test_webapp_scheduler.py`:
    - `test_iteration_heartbeats_and_refreshes_macro_on_success` — `run_scoring_cycle` patched to return `[]` -> `touch_heartbeat` called once with `"calendar_refresh"`, `maybe_refresh_macro_calendar` called once.
    - `test_iteration_on_failed_fetch_refreshes_macro_but_does_not_heartbeat` — returns None -> interval `SCHEDULER_INTERVAL_SECONDS`, no heartbeat, macro refresh still called.
    - `test_macro_refresh_exception_never_breaks_the_iteration` — refresh raises -> iteration returns normally.
    - `test_macro_refresh_retries_after_6_hours_not_every_cycle` — `run` patched to return 0: called at t0, not at t0+1h (returns None), called again at t0+6h; with `run` returning 21 it is called every time (still self-gated by `is_due` inside `run`).
  - `tests/test_backtest_accumulator.py::test_accumulator_iteration_heartbeats_only_on_a_completed_cycle` — `run_accumulator_cycle` -> `[]` (DB helpers patched to a tmp DB) -> heartbeat `"article_accumulator"`; -> None -> no heartbeat and interval `ACCUMULATOR_FALLBACK_INTERVAL_SECONDS`.
  - `tests/test_ops_single_instance.py`:
    - `test_acquire_release_reacquire` — in-process: acquire -> lock; release; acquire again -> lock.
    - `test_lock_is_released_when_the_holder_dies` — start a child Python (`-c`, `sys.path` = app dir) that acquires `"t"` in `tmp_path`, prints `LOCKED`, sleeps 60 s; parent `try_acquire("t", tmp_path)` -> None and `running_pid("t", tmp_path) == child.pid`; `child.kill(); child.wait()`; parent `try_acquire` -> a lock.
    - `test_claim_or_exit_exits_3_when_the_lock_is_held` — `try_acquire` monkeypatched to None -> `SystemExit` code 3; stdout contains `already running`.
    - `test_claim_or_exit_exits_3_when_the_port_is_bound_and_frees_the_lock` — listen on `127.0.0.1:0`, `claim_or_exit("w", port=<that port>, lock_dir=tmp_path)` -> `SystemExit` 3; `try_acquire("w", tmp_path)` afterwards succeeds.
    - `test_app_claims_single_instance_before_starting_the_scheduler` — in the text of `webapp/app.py` after `if __name__ == "__main__":`, `claim_or_exit("webapp", port=5001)` occurs before `_ensure_defaults()` and `start_scheduler(`; in `scripts/run_accumulator.py`, `claim_or_exit("accumulator")` occurs before `start_accumulator(`.
    - `test_restart_loop_stops_on_exit_code_3` — `_restart_loop.bat` bytes: `set EXITCODE=%ERRORLEVEL%` right after `python %1`, an `if "%EXITCODE%"=="3"` branch with `exit /b 3` before `goto loop`, CRLF throughout.
- [ ] Run the four test files — expect FAIL.
- [ ] Implement as specified.
- [ ] Run the four files — expect PASS. Then the full suites.
- [ ] Commit: `fix(B4): webapp scheduler refreshes the FRED macro calendar (never scheduled since 2026-08-16); single-instance engine processes; scheduler/accumulator heartbeats (O7, O8)`.

---

### Task 5: Health check — `/api/health`, dashboard strip, daily Telegram notice (O6) — *judgment*

**Files:**
- Create: `ops/health.py`, `tests/test_ops_health.py`, `tests/test_app_health_route.py`, `webapp/static/js/health/health-strip.js`, `webapp/static/js/health/health-strip.test.js`
- Modify: `webapp/app.py`, `webapp/static/index.html`, `webapp/static/app.js`, `webapp/static/js/api.js`, `webapp/static/style.css`, `alerting/poll_once.py`, `scripts/confirm_backtest_outcomes.py`, `tests/test_alerting_poll_once.py`, `tests/test_confirm_backtest_outcomes.py`

**Interfaces:**
- Consumes: `ops.state` (`get_job_runs`, `get_tracking_since`, `health_notice_sent`, `record_health_notice`), `alerting.store.list_source_health`, `alerting.source_backoff.in_backoff / is_drop_candidate` (Task 2), job names (Task 1), `scripts.refresh_macro_calendar._LAST_MACRO_REFRESH_FILE`, `data_layer.tier1_events.tier1_titles`, `data_layer.rss_sources.FREE_PREVIEW_FEEDS`, `config.settings.CLASSIFIER_PROVIDER_ORDER / CLAUDE_COOLDOWN_MINUTES / OLLAMA_COOLDOWN_MINUTES / LOCAL_TZ`, `scoring.backtest_store.get_predictions_awaiting_outcome`, `alerting.notify_telegram.send_notice`.
- `ops/health.py`:
  - `@dataclass(frozen=True) class HealthItem: key: str; label: str; status: str  # "ok" | "amber" | "red"; last_success_utc: Optional[dt.datetime]; age_seconds: Optional[float]; expected_every_seconds: int; detail: str`.
  - `MACRO_MARKER_PATH: Path` = the refresh script's marker (patchable). `MISSED_RELEASE_LOOKBACK = dt.timedelta(days=7)`. `PROVIDER_METHOD = {"claude": "llm", "ollama": "llm_ollama"}`.
  - `def build_health(now: dt.datetime, *, dash_conn, bt_conn, alerts_conn, ops_conn, macro_marker_path: Optional[Path] = None) -> list[HealthItem]` — items in exactly this key order: `shock_poll, outcome_confirm, reaction_incremental, reaction_baselines, tier1_capture_daily, tier1_capture_weekly, tier1_research, nowcast_live, shock_reality_check, article_accumulator, calendar_refresh, macro_calendar`, then `classifier:<p>` per `CLASSIFIER_PROVIDER_ORDER`, then `feed:<name>` per `FREE_PREVIEW_FEEDS`. Each check is wrapped: an exception makes that item amber with `detail = "check failed: <exc>"`, never the whole build.
  - Threshold rule (age = now - last success): `ok` if age <= amber_after, `amber` if <= red_after, else `red`. Never-run heartbeat job: age measured from `tracking_since_utc`, status at most amber until it passes red_after (detail `no successful run since tracking started {SAST}`).

    | key | label | expected | amber after | red after | last success from |
    |---|---|---|---|---|---|
    | shock_poll | Shock poll | 2 min | 10 min | 30 min | `job_runs` |
    | outcome_confirm | Outcome confirm | 15 min | 45 min | 2 h | `job_runs`; also amber when `get_predictions_awaiting_outcome(bt, now)` has rows with event older than 3 days (`"{n} awaiting more than 3 days (no price data)"`) |
    | reaction_incremental | Market reaction (hourly) | 1 h | 3 h | 6 h | `job_runs` |
    | reaction_baselines | Market reaction baselines (monthly) | 31 d | 32 d | 35 d | max(`job_runs`, `MAX(reaction_baselines.computed_at_utc)`) |
    | tier1_capture_daily | Tier 1 formula capture (daily) | 24 h | 26 h | 50 h | `job_runs` |
    | tier1_capture_weekly | Tier 1 formula capture (weekly) | 7 d | 8 d | 9 d | `job_runs` |
    | shock_reality_check | Shock reality check (weekly) | 7 d | 8 d | 9 d | `job_runs` |
    | article_accumulator | Article accumulator | 12 h | 13 h | 25 h | max(`job_runs`, `MAX(check_log.checked_at_utc)`, `MAX(predictions.scored_at_utc)`) |
    | calendar_refresh | Forex Factory calendar | 12 h | 13 h | 25 h | max(`job_runs`, `calendar_snapshot.fetched_at_utc`) |
    | macro_calendar | Macro calendar (FRED) | 29 d | 30 d | 31 d | marker file, else `MAX(macro_calendar.recorded_at_utc)`; red regardless when `MAX(event_date) < now.date()` (detail `no macro_calendar rows after {date}`) |

  - `tier1_research` (expected 24 h) and `nowcast_live` (expected 24 h) use the missed-release rule: USD `event_history` occurrences with `now - 7d <= event_time <= now` whose title is in `tier1_titles(TIER1_JUDGMENT)` / `tier1_titles(TIER1_FORMULA)`, missing a `tier1_predictions` row (any instrument) / a `kind='live'` `tier1_nowcast_snapshots` row with `julianday(logged_at_utc|as_of_utc) <= julianday(event_time_utc)` for that title and instant -> red, detail `missed: {title} {SAST}` (first 3, then `and {n} more`). `tier1_research` is amber when a judgment occurrence in `(now, now + 24h]` has no row yet (`due within 24h without a call: ...`). Otherwise ok; last success = newest judgment `tier1_predictions.logged_at_utc` / `tier1_late_checks.checked_at_utc` (resp. newest live snapshot `recorded_at_utc`), informational only.
  - `classifier:<p>` (expected 24 h): last success = newest `shock_alerts.detected_at_utc` with `classification_method == PROVIDER_METHOD[p]`; last failure = `provider_cooldown.until_utc - <p>_COOLDOWN_MINUTES`. Failure within 24 h and (no success, or success older than 24 h) -> red `failing; last success {SAST|never}; cooling down until {SAST}`; failure and success both within 24 h -> amber `intermittent failures in the last 24h`; else ok.
  - `feed:<name>` (expected 2 min) from `source_health`: no row -> amber `no poll recorded yet`; `is_drop_candidate` -> red `failing since {SAST} (14+ days): candidate to drop (owner decision)`; `in_backoff` -> amber `in backoff until {SAST} after {n} consecutive failures`; failures > 0 -> amber `{n} consecutive failure(s)`; else ok.
  - `def overall_status(items: list[HealthItem]) -> str` — worst of red > amber > ok.
  - `def health_item_dict(item: HealthItem) -> dict` — exactly `{"key","label","status","last_success_utc","age_seconds","expected_every_seconds","detail"}` (ISO string or None; age rounded to whole seconds or None).
  - `def open_health_connections() -> tuple[sqlite3.Connection, sqlite3.Connection, sqlite3.Connection, sqlite3.Connection]` — (dashboard, backtest, alerts, ops), each via its store's `get_connection()`; closes the opened ones if a later open fails.
  - `def health_notice_text(red_items: list[HealthItem], now: dt.datetime) -> str` — `"🩺 News engine health ({SAST}): {n} item(s) need attention\n- {label}: {detail}\n...\nFull list on the dashboard. Sent at most once per UTC day."`
  - `def maybe_send_health_notice(now: Optional[dt.datetime] = None, *, send: Optional[Callable[[str], bool]] = None, connections: Optional[tuple] = None) -> bool` — never raises (catch-all prints `[ops.health] WARNING: ...` and returns False). Returns False when the UTC day's notice is already recorded (checked first, before building), when nothing is red, or when `send` (default `notify_telegram.send_notice`) returns False; records the day only after a successful send; closes connections it opened.
- `webapp/app.py`: `_health_connections = ops.health.open_health_connections` seam + `_health_conns()` context manager (same ownership rule as `_stats_conns`), `_health_clock = lambda: dt.datetime.now(dt.timezone.utc)`; `GET /api/health` -> `{"generated_at_utc": iso, "overall": str, "items": [health_item_dict(...)]}`.
- `alerting/poll_once.py`: `def main() -> None` — `run_poll_cycle()` then `maybe_send_health_notice()`; `__main__` calls `main()`.
- `scripts/confirm_backtest_outcomes.py` `main()`: when `--auto`, call `maybe_send_health_notice()` right after the summary print (before the early "Nothing awaiting" return).
- Frontend:
  - `api.js`: `export function fetchHealth()` -> `fetchJson("/api/health")`.
  - `js/health/health-strip.js`: `export function formatAge(seconds)` (null -> `"never"`, < 60 -> `"{s}s"`, < 3600 -> `"{round(s/60)}m"`, < 86400 -> `"{(s/3600).toFixed(1)}h"`, else `"{(s/86400).toFixed(1)}d"`); `export function healthStripModel(payload)` -> `{overall, chips}` where chips are the non-ok items, red first then amber, payload order within each, `text = "{label}: {detail}"` or `"{label}: last success {formatAge(age)} ago"` when detail is empty; `export function renderHealthStrip(el, payload)` (strip class `health-strip {overall}`; no chips -> `All jobs and feeds healthy`; chip `<span class="health-chip {status}">` with `escapeHtml` text); `export function renderHealthUnavailable(el)` (amber, `Health check unavailable`).
  - `index.html`: `<div id="health-strip" class="health-strip" role="status" aria-live="polite"></div>` as the first child of `#view-dashboard`. `app.js`: `refreshAll` also awaits `refreshHealth()` (fetch -> render; any error -> `renderHealthUnavailable`). `style.css`: `.health-strip`, `.health-chip.red` (#c62828), `.health-chip.amber` (#ef6c00), ok text #2e7d32, matching `.feed-staleness` sizes.

**Steps:**
- [ ] Write failing tests in `tests/test_ops_health.py` (in-memory dashboard/backtest/alerts DBs, tmp `ops` DB, tmp marker path, `now = 2026-10-20T10:00Z` unless stated):
  - `test_health_flags_the_three_known_silent_failures` — fixture: `event_history` USD `PPI m/m` `2026-10-15T12:30Z` and `CPI m/m` `2026-10-14T12:30Z`; the newest `tier1_predictions` row logged `2026-09-13`; no live snapshots; `macro_calendar` rows up to `2026-09-17`, all recorded `2026-08-16T10:48Z`, no marker; `provider_cooldown` claude until `2026-10-20T09:55Z`; `shock_alerts` newest `llm` on `2026-10-14`, `llm_ollama` rows on `2026-10-19` and `2026-10-20`; all job heartbeats fresh -> `tier1_research` red with `PPI m/m` in detail, `nowcast_live` red with `CPI m/m`, `macro_calendar` red with `2026-09-17`, `classifier:claude` red, `classifier:ollama` ok, `shock_poll` ok, overall red.
  - `test_job_heartbeat_statuses_follow_amber_and_red_thresholds` — shock_poll last success 5 min -> ok, 15 min -> amber, 31 min -> red.
  - `test_never_run_job_is_amber_until_red_after_tracking` — tracking since `now - 1d`, no `tier1_capture_weekly` run -> amber with `no successful run`; tracking since `now - 10d` -> red.
  - `test_missed_release_compares_naive_and_offset_stamps_as_instants` — release stored `2026-10-15T12:30:00` (naive), call logged `2026-10-15T14:29:00+02:00` -> not missed; logged `2026-10-15T14:31:00+02:00` -> missed.
  - `test_tier1_research_amber_when_a_release_within_24h_has_no_call`.
  - `test_outcome_confirm_amber_when_a_prediction_waits_more_than_3_days`.
  - `test_feed_states_backoff_amber_and_two_weeks_failing_red` — backoff -> amber; failing since `now - 15d` -> red with `candidate to drop`; clean -> ok; no row -> amber.
  - `test_classifier_intermittent_failures_are_amber`.
  - `test_macro_calendar_red_when_horizon_exhausted_even_if_recently_refreshed` — marker `now - 1d`, max event_date `2026-10-19` -> red.
  - `test_one_failing_check_does_not_break_the_others` — dash conn closed -> those items amber `check failed`, job items still graded.
  - `test_item_keys_and_order_are_stable` — the exact key list above (classifier `ollama` then `claude`; feeds `reuters_business, cnbc_top_news, cnbc_economy, investing_com_forex`).
  - `test_provider_method_map_matches_poll_once` — `PROVIDER_METHOD == alerting.poll_once._METHOD_BY_PROVIDER`.
  - `test_health_notice_sent_once_per_utc_day_listing_red_items_only` — red + amber items: first call sends once, text contains the red labels and not the amber one, ledger row written; second call the same UTC day -> no send; next UTC day -> sends again.
  - `test_failed_send_leaves_the_day_open` — send `[False, True]` -> second call sends and records.
  - `test_no_red_items_sends_nothing`; `test_notice_never_raises` — `build_health` patched to raise -> returns False.
- [ ] Write failing tests in `tests/test_app_health_route.py` (`_health_connections` and `_health_clock` monkeypatched to the fixture connections and clock, `ops.health.MACRO_MARKER_PATH` to a tmp path, so the worktree's own files are never read): `test_health_route_exact_keys` — top keys `{"generated_at_utc", "overall", "items"}`, every item's keys exactly the seven above, `overall == "red"` for the fixture; `test_health_route_on_empty_dbs_returns_200` — fresh empty DBs -> 200, no exception, statuses only from {ok, amber, red}.
- [ ] Add to `tests/test_alerting_poll_once.py`: `test_poll_main_runs_the_cycle_then_the_health_notice` (both patched; call order asserted). Add to `tests/test_confirm_backtest_outcomes.py`: `test_auto_run_triggers_the_health_notice_even_with_nothing_awaiting`.
- [ ] Write failing `webapp/static/js/health/health-strip.test.js`: `formatAge` (null -> `never`, 45 -> `45s`, 90 -> `2m`, 7200 -> `2.0h`, 172800 -> `2.0d`); `healthStripModel` orders red before amber and drops ok items, all-ok -> no chips; `renderHealthStrip` (jsdom) escapes `<b>` in a detail and sets class `health-strip red`; `renderHealthUnavailable` sets amber text `Health check unavailable`.
- [ ] Run `python -m pytest -q -p no:warnings tests/test_ops_health.py tests/test_app_health_route.py tests/test_alerting_poll_once.py tests/test_confirm_backtest_outcomes.py` and `npm test` — expect FAIL.
- [ ] Implement as specified.
- [ ] Run the same — expect PASS. Then the full suites.
- [ ] Commit: `feat(B4): health check for every job and feed - /api/health, dashboard strip, one Telegram notice per UTC day (O6)`.

---

### Task 6: Deploy runbook, inventory and roadmap — *mechanical*

**Files:**
- Create: `docs/b4-deploy.md`
- Modify: `docs/feature-inventory-2026-09-11.md`, `docs/roadmap-2026-10-20.md`

**Steps:**
- [ ] Write `docs/b4-deploy.md` (CRLF; SAST; every command from the live app dir `C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine`), sections:
  1. **What changes at merge, with no step:** the 5 launchers now run `python -m ops.run_job` (timestamped lines, 1 MB rotation to `.log.1`); no Windows task re-registration (all NewsEngine_* actions already point at the live worktree's `.bat`/`.vbs`); new `ops/ops_state.db` is created on first use; `source_health` and the near-miss indexes are created by `alerting/store.py`.
  2. **Backups first** (outcomes are written, near-misses deleted, macro rows added): for each of `scoring\backtest_log.db`, `alerting\shock_alerts.db`, `webapp\dashboard.db` run `python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" <db> <db>.pre_b4_<date>` (the SQLite backup API, safe while the poller writes).
  3. **Stop every engine copy** (both duplicates): stop the restart-loop windows first, then the Python processes, else the loop restarts them in 5 s:
     `Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -match '_restart_loop\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }`
     `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'webapp\\app\.py|run_accumulator\.py|run_all\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }`
     Verify both queries now list nothing and `netstat -ano | findstr :5001` is empty.
  4. **Merge** `b4-ops-health` into `news-engine/batch-predictions-queries` and update the live worktree (controller's usual fast-forward).
  5. **Start exactly one copy:** `schtasks /run /tn NewsEngine_AutoStart`. Then prove the guard: `python webapp\app.py` and `python scripts\run_accumulator.py` each print `already running` and `$LASTEXITCODE` is 3; the step 3 queries list exactly one `app.py` and one `run_accumulator.py`.
  6. **Verify** (with the expected output): `Get-Content alerting\poll_once.log -Tail 5` lines start `YYYY-MM-DD HH:MM:SS SAST`; after the next 15-minute run `scripts\confirm_outcomes_scheduled.log.1` holds the old 3.7 MB log and the new log shows `Auto-confirm: 0 confirmed, <n> final no-reaction, <m> left for review.` (n = the below-threshold rows, about 28; m = rows with no price data), then `Nothing awaiting confirmation` on later runs unless m > 0; `SELECT COUNT(*) FROM outcomes WHERE actual_move_note LIKE '%no reaction after 3 days, final (auto)'` equals n; `Invoke-RestMethod http://127.0.0.1:5001/api/health` returns `overall` and the item list, and the dashboard shows the strip; `SELECT MAX(event_date), COUNT(*) FROM macro_calendar` shows dates past today and `data_layer\.last_macro_calendar_refresh_at` exists (the first scheduler iteration refreshes, the live worktree has no marker); `SELECT COUNT(*), MIN(seen_at_utc) FROM shock_near_misses` falls each poll until the oldest row is within 30 days (500 rows per poll); one Telegram health notice arrives the same UTC day if anything is red (expected: `tier1_research` for PPI m/m 2026-10-15 until it leaves the 7-day window, and `classifier:claude` while its credits are exhausted).
  7. **Rollback:** stop as in step 3, revert the merge, restart one copy; restore a backup only if needed. The final no-reaction rows can be removed without a restore: `DELETE FROM outcomes WHERE actual_move_note LIKE '%no reaction after 3 days, final (auto)'` (the next run re-finalises them unless the code is reverted).
  8. **O7 root cause** — the paragraph from this plan's decisions, and that O6 now shows a stale or exhausted macro calendar.
  9. **Acceptance (roadmap B4):** the confirm log stops repeating "28 left"; the health check flags Tier 1, the classifier and `macro_calendar` (pinned by `test_health_flags_the_three_known_silent_failures`); one unattended ShockPoll and OutcomeConfirm run each logged with timestamps after deploy.
- [ ] Feature inventory: roadmap table row `B4 Ops health and waste` -> `built on branch b4-ops-health (not merged; deploy steps in docs/b4-deploy.md)`; a new feature row "Ops health and waste (roadmap B4)" in the same style as the B3 row (files: `ops/`, `alerting/source_backoff.py`, launchers, `/api/health`, `health-strip.js`; rules: 3-day final no-reaction as a neutral outcome and why not a dismissal, log format and 1 MB/1 backup rotation, backoff 3 failures / 10 min doubling / 6 h cap / 14-day drop candidate, health thresholds table, once-per-UTC-day notice, single-instance exit code 3, macro refresh in the scheduler with the root cause, near-miss 24 h repeat skip / 30 days / threshold 0.3 -> 0.5); scheduled-tasks table: the five task rows note "runs via `ops.run_job` (timestamped, rotated log)", and add the in-process macro calendar refresh (webapp scheduler, self-gated 29 days).
- [ ] Roadmap status line: append `; B4 built on branch b4-ops-health (not merged)`.
- [ ] Run the full suites (docs only, expect unchanged PASS) and confirm the three docs are CRLF (`file docs/b4-deploy.md ...`).
- [ ] Commit: `docs(B4): deploy runbook, inventory and roadmap status`.
