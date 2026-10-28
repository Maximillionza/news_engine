# B10 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every shock alert's stored lean, at every severity, is graded against what XAUUSD and US30 actually did over 5 minutes, timed from both first publication and detection, against the normal 5-minute move for that UTC hour (the Market reaction baselines). Results are shown on the Shock Alerts tab with hit rates per incident and overall, each with n. Also in this batch: the minute-bar helpers move out of a one-off script into `data_layer/` (C4), and finished one-off scripts are archived (C5).

**Architecture:** `data_layer/minute_bars.py` (new) holds the Dukascopy 1-minute fetch/cache and the bar/baseline helpers. The hourly reaction job and the new `alerting/lean_grading.py` both import it. Grades go in a new append-only table `shock_alert_grades` in `shock_alerts.db`, one row per alert × tracked symbol × anchor, keyed so a rerun writes nothing. The weekly `alerting/reality_check.py` job (same scheduled task, same entry point) grades whatever is due and records one summary row that `ops/health.py` shows. A one-time `scripts/backfill_shock_grades.py` (dry run first) grades past alerts at deploy. `/api/shock-alerts` gains a date range, the grades and a hit-rate summary, and the tab renders them.

**Tech Stack:** Python 3.14, sqlite3, pandas (already used by the reaction job), dukascopy_python, Flask, vanilla ES modules, pytest, `node --test`.

**Spec reference:** `docs/roadmap-2026-10-20.md` §B10 (K11-K14; C4 and C5 moved here from B11), plus these owner decisions:
- Grade over a 5-minute window. The move threshold stays at 1.0 × the hourly baseline (B5 event study, `docs/superpowers/specs/2026-10-21-event-study-report.md`).
- Reuse the Market reaction hourly baselines (`reaction_baselines` in `backtest_log.db`, quantile 0.75, written by `scripts/compute_release_reactions.py` and the monthly `NewsEngine_ReactionBaselines` task). Do not create a second baseline definition.
- Grade only the lean stored on the alert; never invent or alter one. Owner units: $1 = 100 pips on XAUUSD.
- Starting point to report against: 14 of 26 leans correct at 5 minutes. Medium alerts (56 of 75 at the 2026-10-20 sweep) have never been graded.
- Market reaction stays a separate tab and feature. Severity, lean assignment, B7 incident linking, B2 freshness bands and the Telegram format are unchanged.

**Verified source facts (2026-10-28, base ad1e8a1, live DBs read with mode=ro):**
- `shock_alerts.db` has 84 alerts (2026-09-17 to 2026-10-28): High 15, Medium 65, Low 4. All 84 have a publication time (column, or the `sources[0]` fallback in the reader). Publication-to-detection lag runs from 0.4 to 465 min and is never negative.
- `affected_symbols` stored leans: XAUUSD buy 25, mixed 11, none (pre-2026-10-05 rows) 24, absent on 24 alerts; US30 sell 28, buy 1, mixed 18, none 37. Follow-ups (B7) store `mixed`.
- `dashboard.db` `tracked_symbols` = XAUUSD, US30. `reaction_baselines` has 24 hours per symbol at quantile 0.75, period end 2026-10-16T18:00Z.
- `scripts/compute_release_reactions.py` imports `phase0.fetch_bars`, `phase0.WINDOW_MIN`, `phase0.spec_baseline_moves` and `phase0.read_usd_events` from `scripts/market_reaction_phase0.py`. `scripts/event_study_groups.py` imports `quantile` from it, and `scripts/event_study_once.py` imports `_parse_utc` from phase0.
- `alerting/reality_check.py` uses `MAGNITUDE_THRESHOLDS` (XAUUSD 10.0, US30 150.0) for the `reality_mismatch` flag. It runs weekly as `python -m ops.run_job --job shock_reality_check ... -- -m alerting.reality_check` (`alerting/scripts/reality_check_hidden.vbs`).
- With `core.autocrlf=true`, every touched file is CRLF in the working tree and LF in the index.

## Choices made in this plan (owner can veto before Task 1)

- **Anchors.** `published` = the alert's `first_published_utc` (the B2/B7 value with URL memory; the reader falls back to `sources[0]`). `detected` = `detected_at_utc`. A publication time more than 7 days before detection is treated as unknown: verdict `no_data`. This guards the bar fetch range and never triggers on live data (max lag 465 min).
- **Timing.** The anchor is rounded **up** to the whole UTC minute, so nothing before the anchor is used. The move is open(bar at m+5) − open(bar at m), using Dukascopy BID bars matched to the exact minute, the same rule as the reaction job. A missing bar means `no_data`; a neighbouring bar is never substituted. The baseline hour is the UTC hour of m.
- **Verdict precedence:** `no_lean` (stored lean is not `buy`/`sell`, or the symbol is absent from `affected_symbols`; the measured move is still stored), then `no_data`, then `no_baseline`, then `no_move` (|move| ≤ 1.0 × baseline, the reaction job's `classify_reaction` rule, so an equal move is `no_move`), then `right`/`wrong` by sign.
- **K12 fallback = verdict `no_baseline`.** There is no fixed-dollar fallback. `MAGNITUDE_THRESHOLDS` is deleted. The weekly `reality_mismatch` flag now counts a symbol as "moved" only when its 5-minute detection move beats that hour's baseline. The 30-minute move is still stored but no longer compared, because no 30-minute baseline exists. The 81 alerts already stamped keep their old flag; nothing is rewritten.
- **Baseline vintage.** Every alert is graded against the **latest** stored baselines, the same as the reaction job's incremental mode. Each grade row stores the value it used, so a later monthly refresh never changes a grade.
- **Pending vs no_data.** A cell is not written while m+5 is later than the last bar the feed returned, or later than now − 10 min. This mirrors the reaction job's `skipped_pending`: weekend alerts wait for Monday's bars, then read `no_data`. A symbol whose fetch fails writes nothing that run, and the job exits 1. A symbol with no Dukascopy mapping is permanent: it gets `no_data`, or `no_lean` where there is no lean.
- **Hit rate** = right / (right + wrong), with n = right + wrong. `no_move`, `no_lean`, `no_data` and `no_baseline` are shown as counts, never in n. The per-incident figure covers that incident's alerts inside the requested range.
- **Range.** `?from=YYYY-MM-DD&to=YYYY-MM-DD` takes SAST calendar days, inclusive, with a maximum span of 366 days. The default is today SAST and the 6 days before, which differs from the old rolling now − 7 days by up to one day. The lag column shows the existing `age_minutes` (detection minus first publication, floored, clamped at 0); there is no duplicate key.
- **C5 archived scripts stay runnable.** Their path roots go up one level and their imports point at `data_layer.minute_bars` or `scripts.archive.*`. Their existing tests are repointed, not deleted, so coverage is unchanged. Production code never imports them, and a guard test enforces that.
- **Grading cadence** stays weekly (Sunday 20:00 SAST, the existing task). New alerts show "not graded yet" until then. No scheduled-task change.

## Global Constraints

- Live system read-only: nothing under `.worktrees/news-engine-live` is modified. Live DBs are opened only with `mode=ro` URIs. No Windows or Claude scheduled-task edits, no Telegram (mocked), no push.
- Nothing outside the repo is deployed by the build. The controller runs the backup, migration and backfill per `docs/b10-deploy.md`. No scheduled-task text changes.
- `shock_alerts.db` changes are additive only: two new tables in `_SCHEMA` (`CREATE TABLE IF NOT EXISTS`), with no ALTER on `shock_alerts` and no rewrite of any alert column.
- Grade writes are `INSERT OR IGNORE` on the primary key, so a rerun writes 0. `backtest_log.db` and `dashboard.db` are only ever opened read-only by shock grading.
- The reaction job's behaviour and output are unchanged (parity golden, Task 1). Its `.bat`/`.vbs`/`.ps1` paths are unchanged.
- No production module (alerting, webapp, ops, scoring, data_layer, config, scripts outside `scripts/archive`) imports `scripts.archive.*` or `scripts.market_reaction_phase0`.
- Do not touch `webapp/stats_*`, `tests/test_reaction_service.py`, scoring, 70/30, severity, lean assignment, incident linking, freshness or Telegram code.
- Route payloads have exact key-set tests. Times shown to the owner are in SAST; stored values are UTC ISO and compared with `julianday()`.
- Style: type hints on every signature, `from __future__ import annotations`, the surrounding comment density, and dated `B10 (2026-10-28)` comments at changed rules. Every new script gets `if __name__ == "__main__"`.
- Line endings: Edit preserves CRLF; new files may be written LF (autocrlf normalises). No regexes are planned. If one is added, write it with the Write tool and assert `b"\x08" not in` the module bytes.
- After every task, run from the app dir: `python -m pytest -q -p no:warnings` and `npm test`. Only `tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present` may fail.

## Review Focus

- **Reaction job drift from the C4 move** → `test_reaction_job_output_unchanged_by_c4`, `test_cache_dir_unchanged` (Task 1).
- **Archived script broken or still imported by production** → `test_no_production_module_imports_archive_or_one_offs`, `test_archived_scripts_load_standalone`, `test_every_archived_script_has_a_readme_line` (Task 2).
- **Look-ahead or off-by-one anchor minute** (floor instead of ceil, wrong baseline hour at :59) → `test_anchor_minute_rounds_up`, `test_baseline_hour_is_hour_of_rounded_minute` (Task 3).
- **Neighbour bar used for a missing bar** → `test_missing_bar_is_no_data_never_neighbour` (Task 3).
- **Threshold off (≥ vs >), or the fixed $10/150 thresholds still in use** → `test_move_equal_to_baseline_is_no_move`, `test_magnitude_thresholds_removed` (Tasks 3 and 4).
- **Lean invented or altered** (mixed graded as a direction, alert row rewritten) → `test_mixed_and_absent_leans_are_no_lean_with_move`, `test_grading_never_writes_alert_rows` (Task 3).
- **Rerun not idempotent, or pending bars frozen as no_data** → `test_rerun_writes_zero`, `test_pending_cells_are_not_written` (Task 3).
- **Live baseline or dashboard DB written** → `test_baselines_and_symbols_read_only` (Task 3), `test_backfill_dry_run_opens_every_db_read_only` (Task 4).
- **Hit rate counting non-calls** → `test_summary_counts_only_right_wrong_in_n` (Task 3), `hitRateText` tests (Task 5).
- **SAST range edges wrong** → `test_range_is_sast_days_inclusive` (Task 5).
- **Serializer dropping or adding keys** → `test_shock_alert_route_row_key_set_is_exact`, `test_grade_and_summary_key_sets_are_exact` (Task 5).
- **Health status changed by the summary** → `test_shock_reality_check_status_unchanged_by_grading_run` (Task 4).
- **A test reaching the default DB paths** (the weekly job now loads dashboard/backtest paths when no args are given) → `test_explicit_args_never_touch_default_paths` (Task 4).

---

## Task 1 — C4: shared minute-bar helpers  `[integration]`

**Files:** `data_layer/minute_bars.py` (new), `scripts/compute_release_reactions.py`, `scripts/market_reaction_phase0.py` (imports the moved helpers back, so nothing is duplicated), `tests/test_minute_bars.py` (new), `tests/fixtures/b10_reaction_parity_golden.json` (new), `tests/test_market_reaction_phase0.py` (the 3 `spec_baseline_*` tests move to `test_minute_bars.py`).

**Interfaces (`data_layer/minute_bars.py`; moved code keeps its behaviour and docstrings):**
- `UTC`, `WINDOW_MIN = 5`, `CACHE_DIR = Path(tempfile.gettempdir()) / "market_reaction_phase0_cache"` (the same directory, so the existing month cache is reused).
- `Bars = Union[pd.Series, Mapping]`, `FetchBars = Callable[[str, dt.datetime, dt.datetime], Bars]`.
- `aware_utc(value: dt.datetime, name: str) -> dt.datetime` (was `crr._aware_utc`), `parse_utc(text: str) -> dt.datetime` (was `phase0._parse_utc`).
- `to_opens(bars: Bars) -> dict[dt.datetime, float]` plus the private `_Opens`/`_as_opens`; `price_at_minute(bars: Bars, when: dt.datetime) -> Optional[float]`; `quantile(values: list[float], q: float) -> Optional[float]` (all from crr).
- `weekdays(opens: dict) -> list[dt.date]`; `spec_baseline_moves(opens: dict, hour: int, release_minutes: set, window_min: int = WINDOW_MIN, grid: Optional[tuple] = None) -> list[float]` (from phase0).
- `read_usd_events(conn: sqlite3.Connection) -> list[tuple]`, `month_chunks(start: dt.datetime, end: dt.datetime) -> list[tuple[dt.datetime, dt.datetime]]`, `fetch_bars(symbol: str, start: dt.datetime, end: dt.datetime, pause_s: float = 2.0) -> dict[dt.datetime, float]` (from phase0; `dukascopy_python` is still imported inside the function).
- `compute_release_reactions.py` imports these names from `data_layer.minute_bars`. `WINDOW = dt.timedelta(minutes=minute_bars.WINDOW_MIN)` and `default_fetch_bars = minute_bars.fetch_bars`. The names `to_opens`, `price_at_minute`, `quantile` and `_aware_utc` stay importable from crr (existing tests use them), and the docstrings no longer mention phase0.

**Steps:**
- [ ] Write `tests/test_minute_bars.py::test_reaction_job_output_unchanged_by_c4`. It builds a tmp `dashboard.db` (`webapp.store.get_connection(tmp)` + `insert_event_history_if_absent(..., country="USD")`) with USD `event_history` rows at 2026-03-03 12:30 and 13:30, a same-title duplicate 2 minutes after 12:30, and a 2026-03-07 Saturday row. It also builds synthetic `{minute: open}` bars for XAUUSD and US30 over 2026-03-02..03-04 12:00-14:10, with one missing bar at 13:35 for US30. It runs `crr.run(dash, bt, fake_fetch, "backfill", now=2026-03-04T09:00Z, symbols=["US30","XAUUSD"], since=2026-01-01)` into a tmp bt DB, then `crr.run(..., "incremental", refresh_baselines=True)`. The snapshot is both result dicts plus every `release_reactions` and `reaction_baselines` row without `id`/`computed_at_utc`, ordered by natural key. The assertion is `snapshot == json.load(golden)`. A `--write-golden` flag under `if __name__ == "__main__"` writes the fixture.
- [ ] On the **untouched** code, run `python tests/test_minute_bars.py --write-golden`, then run the test (PASS). Commit the test and golden alone: `test(B10): reaction job parity golden before C4`. This is a characterization test, so it is green by design and must predate the move.
- [ ] Add failing tests: `test_cache_dir_unchanged` (path equality above); `test_crr_uses_shared_helpers` (`crr.default_fetch_bars is minute_bars.fetch_bars`; `"market_reaction_phase0" not in` the crr source); `test_fetch_bars_caches_completed_months_only` (fake `dukascopy_python` via `monkeypatch.setitem(sys.modules, ...)`, `CACHE_DIR` patched to tmp, `pause_s=0`: a finished month writes one pickle and the second call makes 0 fetches; the current month is never cached); `test_parse_utc_naive_is_utc`; and the 3 moved `spec_baseline_*` tests against `minute_bars`.
- [ ] Run `python -m pytest -q tests/test_minute_bars.py` → FAIL (module missing).
- [ ] Implement: move the code and repoint crr and phase0. `scripts/market_reaction_phase0.py` imports `fetch_bars`, `spec_baseline_moves`, `read_usd_events`, `parse_utc as _parse_utc`, `WINDOW_MIN` and `CACHE_DIR` from minute_bars and drops its copies.
- [ ] Run `tests/test_minute_bars.py tests/test_compute_release_reactions.py tests/test_market_reaction_phase0.py` → PASS, golden unchanged (`git diff --exit-code tests/fixtures`). Full suites → PASS.
- [ ] Commit `refactor(B10 C4): minute-bar helpers move to data_layer/minute_bars.py`.

## Task 2 — C5: archive the one-off scripts  `[mechanical]`

**Files:** `git mv` into `scripts/archive/`: `market_reaction_phase0.py`, `audit_fa_probes.py`, `audit_shock_impact.py`, `migrate_adp_title_rename.py`, `migrate_country_backfill.py`, `migrate_gdp_title_rename.py`, `stats_phase0_news_input.py`, `compare_fred_lookahead.py`, `event_study_once.py`, `event_study_groups.py`, `event_study_metrics.py`, `event_study_checks.py`. New: `scripts/archive/README.md`, `tests/test_scripts_archive.py`. Repointed: `tests/test_market_reaction_phase0.py`, `tests/test_event_study_{once,groups,metrics,checks}.py`, `tests/test_dead_code_removed.py`, `tests/test_migrate_country_backfill.py`, `tests/test_migrate_gdp_title_rename.py`, `tests/test_calendar_feed.py` (probe import), `tests/test_subject_rules.py` (probe import). Comment paths: `config/settings.py:90`, `data_layer/fred_calendar_feed.py:13`, `webapp/store.py:215`.

**Rules:**
- In each moved file, the app-root expression goes up one level: `parents[1]` → `parents[2]`, `.parent.parent` → `.parents[2]`, `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` → three `dirname`s. In `event_study_once.py`, `REPO_ROOT` goes `parents[3]` → `parents[4]` and `DEFAULT_NOWCAST_CSV` goes `parents[1]` → `parents[2]`.
- Imports inside moved files: `from scripts.event_study_x` → `from scripts.archive.event_study_x`. `from scripts.compute_release_reactions import quantile` → `from data_layer.minute_bars import quantile`. `from scripts.market_reaction_phase0 import _parse_utc` → `from data_layer.minute_bars import parse_utc as _parse_utc`.
- `scripts/archive/README.md`: one line per file: `name.py` — what it was for, which batch or date, and why it is archived. Add a header: "Not imported by production code; kept runnable from the app dir as `python scripts/archive/<name>.py`."
- Kept in `scripts/` (production entry points and re-runnable tools): every file run by a `.bat`/`.vbs`/`.ps1` or imported by app/scheduler/alerting code, plus `register_*.ps1`, `seed_fred_history.py`, `b6_contamination_report.py`, `b8_rescore_report.py`, `refresh_macro_calendar.py`, `confirm_backtest_outcomes.py`, `compute_release_reactions.py` and the rest not listed above.

**Steps:**
- [ ] Write the failing `tests/test_scripts_archive.py`:
  - `test_no_production_module_imports_archive_or_one_offs`: `ast` walk of every `*.py` under `alerting/ webapp/ ops/ scoring/ data_layer/ config/ scripts/` (excluding `scripts/archive/`). No `Import`/`ImportFrom` module starts with `scripts.archive`, and none equals `scripts.market_reaction_phase0` or any archived stem (`from scripts import market_reaction_phase0` included).
  - `test_archived_scripts_load_standalone`: for each archived file, `subprocess.run([sys.executable, "-c", <spec_from_file_location + exec_module>], cwd=tmp_path, env without PYTHONPATH)` returns 0. This proves each path root resolves to the app dir.
  - `test_every_archived_script_has_a_readme_line`: each archived stem appears in `scripts/archive/README.md`.
  - `test_scheduled_entry_points_stay_in_scripts`: every `scripts\X.py` and `scripts/X.py` named in `scripts/*.bat|*.vbs|*.ps1` and `alerting/scripts/*` exists under `scripts/`.
  - `test_event_study_repo_root_is_git_root`: `scripts.archive.event_study_once.REPO_ROOT == APP.parents[1]`, i.e. the folder that holds `Claude_news_engine`.
- [ ] Run → FAIL.
- [ ] `git mv` the 12 files, apply the rules, repoint the tests (`scripts.X` → `scripts.archive.X`), update the 3 comment paths and write the README.
- [ ] Run `tests/test_scripts_archive.py` plus every repointed test file → PASS. Full suites → PASS, with the same test count as before the task.
- [ ] Commit `chore(B10 C5): archive one-off scripts to scripts/archive`.

## Task 3 — K11/K12: grade storage and the grading engine  `[judgment]`

**Files:** `alerting/store.py`, `alerting/lean_grading.py` (new), `tests/test_alerting_lean_grading.py` (new), `tests/test_alerting_store.py`.

**Interfaces:**
- `_SCHEMA` additions in `alerting/store.py` (both `CREATE TABLE IF NOT EXISTS`, so old DBs gain them at connect):
  ```sql
  CREATE TABLE IF NOT EXISTS shock_alert_grades (
      alert_id INTEGER NOT NULL, symbol TEXT NOT NULL, anchor TEXT NOT NULL, window_minutes INTEGER NOT NULL,
      lean TEXT, anchor_utc TEXT, p0 REAL, p_end REAL, move REAL, baseline REAL,
      baseline_multiple REAL NOT NULL, moved INTEGER, verdict TEXT NOT NULL, graded_at_utc TEXT NOT NULL,
      PRIMARY KEY (alert_id, symbol, anchor, window_minutes));
  CREATE TABLE IF NOT EXISTS shock_grading_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT, run_at_utc TEXT NOT NULL, source TEXT NOT NULL,
      counts_json TEXT NOT NULL, summary_line TEXT NOT NULL);
  ```
- `alerting/store.py` functions:
  - `record_grade(conn: sqlite3.Connection, grade: "Grade", graded_at_utc: dt.datetime) -> bool` (INSERT OR IGNORE; True if inserted; commits).
  - `graded_keys(conn: sqlite3.Connection) -> set[tuple[int, str, str, int]]` (an empty set when the table is absent, for a read-only dry run on a pre-migration DB).
  - `list_grades(conn: sqlite3.Connection, alert_ids: list[int]) -> dict[int, list[dict]]` (each dict has the table's columns; ordered by symbol, then anchor `published` before `detected`).
  - `list_all_alerts(conn: sqlite3.Connection) -> list[ShockAlertRow]` (by `julianday(detected_at_utc)` ascending).
  - `list_alerts_between(conn: sqlite3.Connection, start_utc: dt.datetime, end_utc: dt.datetime) -> list[ShockAlertRow]` (`julianday >= start AND < end`, newest first).
  - `record_grading_run(conn: sqlite3.Connection, run_at_utc: dt.datetime, source: str, counts: dict, summary_line: str) -> int`.
  - `latest_grading_run(conn: sqlite3.Connection) -> Optional[dict]` (keys `run_at_utc` (aware datetime), `source`, `counts`, `summary_line`; None when the table is absent or empty).
- `alerting/lean_grading.py`:
  - Constants: `ANCHORS = ("published", "detected")`, `GRADE_WINDOW_MINUTES = 5`, `VERDICTS = ("right", "wrong", "no_move", "no_lean", "no_data", "no_baseline")`, `PENDING_MARGIN = dt.timedelta(minutes=10)`, `MAX_PUBLICATION_LAG = dt.timedelta(days=7)`. The multiple comes from `webapp.reaction_rules.REACTION_MIN_MULTIPLE` (1.0) and the quantile from `REACTION_BASELINE_QUANTILE` (0.75); neither is redefined.
  - `@dataclass(frozen=True) class Grade`: `alert_id: int`, `symbol: str`, `anchor: str`, `window_minutes: int`, `lean: Optional[str]`, `anchor_utc: Optional[dt.datetime]`, `p0: Optional[float]`, `p_end: Optional[float]`, `move: Optional[float]`, `baseline: Optional[float]`, `baseline_multiple: float`, `moved: Optional[bool]`, `verdict: str`.
  - `anchor_minute(when: dt.datetime) -> dt.datetime` (ceiling to a whole UTC minute; an exact minute is unchanged).
  - `anchor_time(alert: ShockAlertRow, anchor: str) -> Optional[dt.datetime]`.
  - `stored_lean(alert: ShockAlertRow, symbol: str) -> Optional[str]` (the stored value verbatim, or None when the symbol or the key is absent).
  - `grade_cell(alert_id: int, symbol: str, anchor: str, when: Optional[dt.datetime], lean: Optional[str], opens: Optional[dict[dt.datetime, float]], baselines: dict[int, float]) -> Grade` (`opens=None` means the symbol has no Dukascopy mapping). `moved` = `classify_reaction(move, baseline) in ("buy", "sell")`, or None when that returns None.
  - `is_pending(when: Optional[dt.datetime], last_bar: Optional[dt.datetime], now: dt.datetime) -> bool`.
  - `grade_pending_alerts(conn: sqlite3.Connection, symbols: list[str], baselines_by_symbol: dict[str, dict[int, float]], fetch_bars: FetchBars, now: dt.datetime, *, dry_run: bool = False, resolve: Optional[Callable[[str], Optional[str]]] = None) -> dict` → `{"written": int, "pending": int, "already_present": int, "fetch_failed": dict[str, str], "counts": summarize_grades(<grades written>)}`. Per symbol, the todo cells are the (alert, anchor) pairs not in `graded_keys`. Cells with no anchor time are graded at once. Bars are fetched once per symbol, from the earliest todo anchor minute to now; a fetch failure or empty result writes nothing for that symbol. Grading never touches `shock_alerts` rows.
  - `empty_counts() -> dict` with keys `n, right, wrong, hit_rate, no_move, no_lean, no_data, no_baseline`. `summarize_grades(grades: Iterable[Grade | Mapping]) -> dict` → `{"overall": {anchor: counts}, "by_symbol": {symbol: {anchor: counts}}}`; `hit_rate` = right/n rounded to 4 places, None when n = 0.
  - `summarize_incidents(alerts: list[ShockAlertRow], grades_by_alert: dict[int, list[dict]]) -> list[dict]`: keys `incident_id, headline, first_detected_utc, alerts, published, detected`, newest incident first. The headline comes from the incident's earliest alert in the list.
  - `format_summary_line(result: dict) -> str`, exact form: `graded {written}: right {r}, wrong {w}, no_move {m}, no_lean {l}, no_data {d}, no_baseline {b}; hit rate {pct} ({r} of {n}); detected {pct_d} ({r_d} of {n_d}); pending {p}`. The counts sum both anchors; pct is `62.5%` or `n/a`. A non-empty `fetch_failed` appends `; fetch failed: XAUUSD`.
  - `open_readonly(path: Path) -> sqlite3.Connection` (`mode=ro` URI, `sqlite3.Row`). `load_baselines(bt_db: Path, symbols: list[str]) -> dict[str, dict[int, float]]` (via `backtest_store.get_latest_reaction_baselines(conn, s, REACTION_BASELINE_QUANTILE)`; `{}` per symbol when the table is absent). `load_tracked_symbols(dash_db: Path) -> list[str]` (`webapp.store.list_tracked_symbols`).

**Steps:**
- [ ] Failing tests in `tests/test_alerting_lean_grading.py`. Synthetic opens and a `FakeFetch`; alerts via `store.record_alert` on `:memory:` with explicit `first_published_utc`; baselines `{12: 1.0, 13: 2.0}` for XAUUSD:
  - `test_anchor_minute_rounds_up`: 12:30:40 → 12:31; 12:30:00 → 12:30.
  - `test_baseline_hour_is_hour_of_rounded_minute`: detected 12:59:30 uses hour 13 (2.0); detected 12:58:30 uses hour 12.
  - `test_right_wrong_by_sign`: lean `buy`, opens 12:31 = 100.0 and 12:36 = 101.5, baseline 1.0 → `right`, `move == 1.5`, `moved is True`; lean `sell` with the same bars → `wrong`.
  - `test_move_equal_to_baseline_is_no_move`: move 1.0 against baseline 1.0 → `no_move`, `moved is False`.
  - `test_missing_bar_is_no_data_never_neighbour`: no 12:36 bar but a 12:37 bar → `no_data`, `p_end is None`.
  - `test_no_baseline_for_hour`: hour 15 absent → `no_baseline` (no fixed-threshold fallback).
  - `test_mixed_and_absent_leans_are_no_lean_with_move`: lean `mixed`, None, and a symbol absent from `affected_symbols` → `no_lean`, with `move` still set when bars exist.
  - `test_published_and_detected_anchors_graded_separately`: published 12:20:10, detected 12:30:40 → two rows with `anchor_utc` 12:21 and 12:31 and different moves. A publication time 8 days before detection → published `no_data`.
  - `test_pending_cells_are_not_written`: detected such that m+5 is after the last fake bar → not written, `pending == 1`; after adding bars and rerunning → written.
  - `test_rerun_writes_zero`: second `grade_pending_alerts` → `written == 0`, `already_present > 0`, table row count unchanged.
  - `test_every_alert_gets_every_symbol_and_anchor`: 3 alerts (High, Medium, Low; one with only US30 in `affected_symbols`) × `["US30", "XAUUSD"]` → 12 rows.
  - `test_fetch_failure_writes_nothing_for_that_symbol`: XAUUSD fetch raises → `fetch_failed == {"XAUUSD": ...}` and only US30 rows are written.
  - `test_unresolvable_symbol_is_no_data`: `resolve` returns None → rows with `no_data` (or `no_lean` when there is no lean), and no fetch call.
  - `test_grading_never_writes_alert_rows`: `SELECT * FROM shock_alerts` is identical before and after.
  - `test_summary_counts_only_right_wrong_in_n`: grades right 5, wrong 3, no_move 4, no_lean 6, no_data 1 on `detected` → `n == 8`, `hit_rate == 0.625`, the others as counts; an empty anchor → `n == 0`, `hit_rate is None`.
  - `test_incident_summary_groups_by_incident_id`: two alerts on incident 12 plus one standalone alert → two entries, with counts summed for incident 12.
  - `test_format_summary_line_exact`: the exact string for a fixed result.
  - `test_baselines_and_symbols_read_only`: `load_baselines` and `load_tracked_symbols` on tmp DBs; the files' mtimes and bytes are unchanged, and a write through `open_readonly` raises `sqlite3.OperationalError`.
  - `tests/test_alerting_store.py::test_grade_tables_created_on_old_db`: a tmp DB with the pre-B10 schema gains both tables at `get_connection`, and the `shock_alerts` columns are unchanged.
- [ ] Run → FAIL.
- [ ] Implement as specified. Grade rows are written per cell with one commit per alert.
- [ ] Run → PASS. Full suites → PASS.
- [ ] Commit `feat(B10 K11/K12): grade shock-alert leans against hourly baselines`.

## Task 4 — Weekly job, K14 health line and the backfill script  `[integration]`

**Files:** `alerting/reality_check.py`, `ops/health.py`, `scripts/backfill_shock_grades.py` (new), `tests/test_alerting_reality_check.py`, `tests/test_ops_health.py`, `tests/test_backfill_shock_grades.py` (new).

**Interfaces:**
- `alerting/reality_check.py`: delete `MAGNITUDE_THRESHOLDS`. `run_reality_check(conn: Optional[sqlite3.Connection] = None, *, symbols: Optional[list[str]] = None, baselines_by_symbol: Optional[dict[str, dict[int, float]]] = None, fetch_bars: Optional[FetchBars] = None, now: Optional[dt.datetime] = None) -> dict`. A None argument is loaded from the live default paths through `lean_grading.load_tracked_symbols(webapp.store.DB_PATH)`, `load_baselines(backtest_store.DB_PATH, ...)` and `minute_bars.fetch_bars`. It first calls `grade_pending_alerts`, then `store.record_grading_run(conn, now, "weekly", result["counts"], line)`, then runs the existing mismatch loop. The mismatch loop's per-symbol threshold is `baselines[symbol].get(anchor_minute(detected).hour)`; a missing value skips the symbol. A symbol is "cleared" when `classify_reaction(move_5min, threshold) in ("buy", "sell")`, and the 30-minute move is recorded but not compared. The returned dict adds `"grading": result` and `"summary_line": line`. `main() -> int` prints the existing line and `[lean_grading] <line>`, and returns 1 when `fetch_failed`, else 0. The module ends with `raise SystemExit(main())`.
- `ops/health.py`: `_shock_reality_check_check(now: dt.datetime, conns: dict[str, sqlite3.Connection]) -> HealthItem` replaces `job("shock_reality_check")` in `build_health`. It builds the `_job_check` item, then appends `last grading <SAST>: <summary_line>` to `detail` when `alerting_store.latest_grading_run(conns["alerts"])` returns a row. The status is unchanged.
- `scripts/backfill_shock_grades.py`: `main(argv: Optional[list[str]] = None) -> int` with flags `--apply` (default dry run), `--alerts-db PATH`, `--bt-db PATH`, `--dash-db PATH`. `LIVE_ENV_VAR = "SHOCK_GRADES_LIVE"`: without `--alerts-db` and with the variable not `1`, it prints REFUSING and returns 2 before opening anything. A dry run opens all three DBs with `lean_grading.open_readonly`. `--apply` opens alerts through `store.get_connection(path)`, which migrates, and records a run with source `"backfill"`. bt and dash are always read-only. Output covers per anchor and symbol verdict counts, `written`, `pending`, `already_present`, fetch failures and the `format_summary_line` line, plus `overall 5-minute detection-anchored hit rate: <pct> (<r> of <n>); starting point before B10: 14 of 26`. It returns 1 on any fetch failure.

**Steps:**
- [ ] Failing tests:
  - Rewrite the existing tests in `tests/test_alerting_reality_check.py` to pass `symbols`, `baselines_by_symbol={"XAUUSD": {h: 10.0 for h in range(24)}}` and a fake `fetch_bars`. They keep patching `get_price_at` and keep their assertions; only the threshold source changes, and a 30-minute-only move no longer clears.
  - `test_magnitude_thresholds_removed`: `not hasattr(reality_check, "MAGNITUDE_THRESHOLDS")`.
  - `test_mismatch_uses_hourly_baseline`: High alert, 5-minute move 3.0, baseline 2.0 → no mismatch; baseline 4.0 → mismatch.
  - `test_missing_baseline_skips_symbol_not_mismatch_signal`.
  - `test_run_records_one_grading_run_and_summary_line`: one `shock_grading_runs` row (source `weekly`) whose `summary_line` equals the printed line.
  - `test_main_exit_code_1_on_fetch_failure`.
  - `test_explicit_args_never_touch_default_paths`: monkeypatch `lean_grading.load_tracked_symbols`, `lean_grading.load_baselines` and `minute_bars.fetch_bars` to `pytest.fail`, then run one scenario with all four keyword args. Every test in this file must pass all four, so none can reach a default (live-path) DB.
- [ ] `tests/test_ops_health.py`: `test_shock_reality_check_detail_carries_last_grading_line` (the detail contains `last grading` and the line) and `test_shock_reality_check_status_unchanged_by_grading_run` (same status with and without a run row; no table → detail unchanged).
- [ ] `tests/test_backfill_shock_grades.py`:
  - `test_refuses_live_default_without_flag` (exit 2; `sqlite3.connect` is never called).
  - `test_backfill_dry_run_opens_every_db_read_only` (spy on `sqlite3.connect`: every call is a `mode=ro` URI; 0 rows written; a pre-B10 alerts DB without the grade table works).
  - `test_apply_writes_then_rerun_writes_zero` (the second apply prints `graded 0`).
  - `test_output_reports_starting_point` (stdout contains `starting point before B10: 14 of 26`).
- [ ] Run → FAIL.
- [ ] Implement as specified.
- [ ] Run → PASS. Full suites → PASS.
- [ ] Read-only measurement against live: `python scripts/backfill_shock_grades.py --alerts-db <live>/alerting/shock_alerts.db --bt-db <live>/scoring/backtest_log.db --dash-db <live>/webapp/dashboard.db`. This is a dry run, and every DB is opened `mode=ro`; the only writes are bar-cache pickles in the OS temp dir. Paste the counts and the detection-anchored figure into `docs/b10-deploy.md` §6 as "expected at deploy (build-time dry run <date>)" in Task 6.
- [ ] Commit `feat(B10 K14): weekly job grades leans, logs and records a summary; backfill script`.

## Task 5 — K13: route range, grades, summary and the Shock Alerts tab  `[integration]`

**Files:** `webapp/app.py`, `webapp/static/js/api.js`, `webapp/static/js/shock-alerts/grading.js` (new), `webapp/static/js/shock-alerts/grading.test.js` (new), `webapp/static/js/shock-alerts/table.js`, `webapp/static/index.html`, `webapp/static/style.css`, `tests/test_app_shock_alerts_route.py`.

**Interfaces:**
- `webapp/app.py`:
  - `SHOCK_RANGE_DEFAULT_DAYS = 7` and `SHOCK_RANGE_MAX_DAYS = 366`.
  - `_shock_range(args: Mapping[str, str], now: dt.datetime) -> tuple[dt.date, dt.date]`, which raises `ValueError` on a bad format, from > to, or a span over 366 days. Any of these gives a 400 with `{"error": ...}`.
  - UTC bounds: from 00:00 SAST up to (to + 1 day) 00:00 SAST, via `config.settings.LOCAL_TZ`.
  - The route uses `list_alerts_between`, `list_grades` and `lean_grading.summarize_grades`/`summarize_incidents`.
  - Response keys are exactly `{"rows", "range", "summary"}`:
    - `range` = `{"from", "to"}`.
    - Each row = the existing 22 keys plus `"grades"`, a list of dicts with exact keys `{"symbol", "anchor", "window_minutes", "lean", "anchor_utc", "move", "baseline", "verdict"}`.
    - `summary` has exact keys `{"window_minutes", "symbols", "overall", "by_symbol", "incidents", "ungraded_alerts"}`. `symbols` = tracked symbols seen in the grades, sorted, falling back to `["US30", "XAUUSD"]`. `ungraded_alerts` = rows in range with no grades.
- `grading.js` (pure, no DOM):
  - `lagText(row)` gives `+7 min`, or `—` when unknown.
  - `moveText(symbol, move)`: XAUUSD gives `+123 pips` (move × 100, rounded); US30 gives `+45.3 pts`; null gives `—`.
  - `verdictCellHtml(grade)` gives the lean, a verdict badge (`verdict-right|wrong|no_move|no_lean|no_data|no_baseline`, label with underscores as spaces) and the move. Everything is escaped.
  - `hitRateText(counts)`.
  - `gradingTableHtml(rows, symbols)` builds the columns Detected (SAST), Severity, Headline, Incident, Lag, Polarity, Country, then `<SYM> published` and `<SYM> detected` per symbol. A row with no grades shows `not graded yet`.
  - `summaryHtml(summary)` shows overall per anchor with n, by symbol, and an incident table (incident #, headline, alerts, published and detected hit rates with n).
  - `rangeQuery(from, to)`.
- `api.js`: `fetchShockAlerts(range = {})` calls `/api/shock-alerts` plus `rangeQuery`.
- `table.js` / `index.html`:
  - Add a range form `#shock-range` (two `type="date"` inputs and a Show button) and containers `#shock-grading-summary` and `#shock-grading-table` above the existing cards. Cards are unchanged.
  - A Show click re-fetches; the initial load stays once-only.
  - The empty notice reads `No shock alerts in this date range.`

**Steps:**
- [ ] Failing Python tests in `tests/test_app_shock_alerts_route.py`:
  - Update `EXPECTED_ROW_KEYS` with `"grades"` and add `test_response_top_level_keys_exact`.
  - `test_grade_and_summary_key_sets_are_exact`: seed one alert and two grade rows via `store.record_grade`, then assert every key set above.
  - `test_range_is_sast_days_inclusive`: alerts at 2026-10-19T21:59Z (10-19 23:59 SAST) and 2026-10-19T22:00Z (10-20 00:00 SAST); `?from=2026-10-20&to=2026-10-20` returns only the second.
  - `test_default_range_is_today_and_six_days_before_sast`.
  - `test_bad_range_is_400`: `from=2026-13-01`; from > to; a 367-day span.
  - `test_summary_hit_rate_per_incident_and_overall`: right 2 and wrong 1 on detected for incident 5 → incident `detected.n == 3`, `hit_rate == 0.6667`; overall the same; a `no_move` grade counted in `no_move` and not in n.
- [ ] Failing `grading.test.js` (`node --test`):
  - `lagText({age_minutes: 7}) === "+7 min"` and `lagText({age_minutes: null}) === "—"`.
  - `moveText("XAUUSD", 1.234) === "+123 pips"`, `moveText("XAUUSD", -0.5) === "-50 pips"`, `moveText("US30", 45.25) === "+45.3 pts"`, `moveText("US30", null) === "—"`.
  - `hitRateText({n: 8, right: 5, wrong: 3, hit_rate: 0.625, no_move: 4, no_lean: 6, no_data: 1, no_baseline: 0}) === "62.5% (5 of 8) · no move 4 · no lean 6 · no data 1 · no baseline 0"`; with n 0 it reads `n/a (0 of 0) · …`.
  - `verdictCellHtml` escapes `<b>` in the lean and carries the class `verdict-no_move` with label `no move`.
  - `gradingTableHtml` headers include `Lag`, `Polarity`, `Country`, `XAUUSD published` and `US30 detected`; an ungraded row shows `not graded yet`.
  - `summaryHtml` contains `Incident #12` and `(2 of 3)`.
  - `rangeQuery("2026-10-01", "2026-10-28") === "?from=2026-10-01&to=2026-10-28"` and `rangeQuery("", "") === ""`.
- [ ] Run `python -m pytest -q tests/test_app_shock_alerts_route.py` and `npm test` → FAIL.
- [ ] Implement as specified. New JS must be strict UTF-8 (`tests/test_static_js_utf8.py`); write `—` and `·` as literal UTF-8.
- [ ] Run → PASS. Full suites → PASS.
- [ ] Manual check (not live): run the worktree app on a temp copy of the alerts DB with seeded grades and confirm the tab renders at phone width. Never use the live DBs.
- [ ] Commit `feat(B10 K13): shock tab shows lean verdicts, lag, hit rates and a date range`.

## Task 6 — Docs: deploy runbook, inventory, roadmap status  `[mechanical]`

**Files:** `docs/b10-deploy.md` (new), `tests/test_b10_deploy_doc.py` (new), `docs/feature-inventory-2026-09-11.md` (the B10 row at line 53, plus one new feature row after the B7 row), `docs/roadmap-2026-10-20.md` (append to the top `> Status` line only). Do not touch the B9 lines.

**`docs/b10-deploy.md` sections**, shell-agnostic `python` one-liners and forward slashes as in `docs/b8-deploy.md`, run from the live app dir:
1. What changes:
   - Two new tables in `shock_alerts.db`, created at the first connect after merge (poller tick or webapp).
   - The weekly `NewsEngine_ShockRealityCheck` now grades leans, and its mismatch flag uses hourly baselines.
   - The tab gains grades, a date range and hit rates.
   - Twelve scripts move to `scripts/archive/`.
   - No scheduled-task, Telegram or scoring change.
2. Backup: `python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" alerting/shock_alerts.db alerting/shock_alerts.db.pre_b10_<date>`.
3. Stop the single engine copy (the same two PowerShell lines as B7/B8, with the verify step).
4. Merge `b10-shock-grading` into `news-engine/batch-predictions-queries` and fast-forward the live worktree.
5. Start exactly one copy (`schtasks /run /tn NewsEngine_AutoStart`). Verify with `PRAGMA table_info(shock_alert_grades)`, or run the step 6 apply, which also migrates.
6. Backfill:
   - Run the dry run (the command from Task 4 with live relative paths) and record the counts. Compare them with the build-time expected counts pasted here.
   - Run `--apply`, record `written` and the detection-anchored figure next to "14 of 26".
   - Rerun `--apply`: it must print `graded 0`.
   - Acceptance query: `SELECT COUNT(*) FROM shock_alerts a WHERE (SELECT COUNT(*) FROM shock_alert_grades g WHERE g.alert_id = a.id) < 4` returns only alerts listed as pending.
7. Verify:
   - `python scripts/compute_release_reactions.py --incremental --dry-run --bt-db scoring/backtest_log.db --dash-db webapp/dashboard.db` exits 0.
   - `/api/shock-alerts?from=2026-09-17&to=<today>` shows `summary.overall.detected.n`.
   - `/api/health` shows the `last grading` detail.
   - After the next Sunday 20:00 SAST run, `reality_check.log` carries a `[lean_grading] graded` line.
8. Rollback: stop as in step 3, revert the merge and restart one copy. The new tables stay unread. Restore `pre_b10` only if needed. Reverting also restores the scripts from the archive.

**Steps:**
- [ ] Failing `tests/test_b10_deploy_doc.py`:
  - The doc contains `shock_alerts.db.pre_b10_`, the dry run appears before `--apply`, `graded 0` appears, `14 of 26` appears, and a `Rollback` heading exists.
  - The doc does not contain `%TEMP%` or `$env:`.
  - Every `scripts/...py` path the doc names exists.
- [ ] Run → FAIL. Write the doc with the Task 4 build-time numbers.
- [ ] Inventory row 53 → `built on branch b10-shock-grading`. The new feature row summarises K11-K14, C4 and C5, with links to this plan and `docs/b10-deploy.md` (the controller marks it live after deploy). The roadmap `> Status` line gets ` B10 built on branch b10-shock-grading (not merged).` appended.
- [ ] Full suites → PASS. Commit `docs(B10): deploy runbook, inventory and roadmap status`.
