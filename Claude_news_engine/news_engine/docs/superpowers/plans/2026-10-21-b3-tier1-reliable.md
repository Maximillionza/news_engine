# B3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every covered USD release gets a Tier 1 call BEFORE it happens. CPI m/m and Core CPI m/m get a deterministic formula call (Cleveland Fed nowcast vs forecast), captured by Windows tasks that catch up after a sleeping PC. Judgment events get a "late check" log when their call is stale. The dashboard never shows a call logged after the release, and its conflict flag says which kind of Tier 1 it compared against.

**Architecture:** A new zero-import module `data_layer/tier1_events.py` holds `TIER1_EVENTS` (title -> tier) and the Tier 1 timing rules; the capture script, the new research CLI and the Stats tab all read it. `scripts/capture_nowcast_from_cleveland.py` gains `--window-hours` and, after each live snapshot, writes one `tier1_predictions` row per tracked instrument through a small pure module `webapp/tier1_formula.py`. Two per-user Windows tasks run it (weekly 8-day window, daily 48h window). The Claude research task stops writing ad-hoc Python: it runs `scripts/tier1_research.py plan | record-call | record-late-check`, which apply the title list, the as-of rules and the new append-only `tier1_late_checks` table.

**Tech Stack:** Python 3 / SQLite / Flask, pytest; vanilla ES modules + `node --test`; PowerShell 5.1 + VBS/BAT launchers.

**Spec:** `docs/roadmap-2026-10-20.md` §B3 (T2-T8), plus these owner decisions:
- Formula tier = CPI m/m, Core CPI m/m (Cleveland nowcast). Market-implied tier exists as a value but has no titles yet (Kalshi is B12). Judgment tier = the 14 other titles listed in Task 1.
- No T-12h capture for CPI: the nowcast freezes 10-14 days before release (T-5d == final in 17/17).
- Formula call: surprise side of nowcast vs forecast with the Stats tolerance (one rounding step of the forecast's precision); in line -> neutral, above -> hotter, below -> cooler; per instrument via `webapp.stats_methods.market_lean` (buy -> bullish, sell -> bearish, mixed -> neutral); confidence "Likely"; source "Cleveland Fed nowcast (formula)"; at most one row per (title, event_time, instrument) per distinct nowcast value.
- Late check (judgment only): log first; the first pre-release call stands and is never changed.
- Out of scope: Kalshi market-implied calls and Core PCE / y/y formula (B12), health checks (B4).

Audit evidence: T1-01..T1-10, SCH-01..SCH-04, S-06.

App dir for every command: `.worktrees/b3-tier1-reliable/Claude_news_engine/news_engine`. Full suite = `python -m pytest -q -p no:warnings` (baseline 1509 passed, 1 env-only failure) + `npm test` (baseline 210/210). Known env-only failure (no `.env` in a worktree): `tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present` — ignore it; everything else must pass.

## Global Constraints

- **Live system off-limits:** no change to `.worktrees/news-engine-live`, any live `*.db`, Windows scheduled tasks, Claude scheduled tasks (`C:\Users\Masoodt\.claude\scheduled-tasks` is read-only), or Telegram. No push.
- **Outside-repo changes are text in the repo only:** the new SKILL.md text, task registration and the release-eve retirement live in `docs/tier1-b3-deploy.md` and `scripts/register_tier1_tasks.ps1`, applied at deploy by the controller. Never run the `.ps1`.
- **Tests:** temp / `:memory:` DBs, injected `fetch` and `now`; no network (`tests/conftest.py` already blanks Telegram/Ollama/Anthropic).
- **DB writes are append-only and idempotent:** `tier1_late_checks` is CREATE IF NOT EXISTS inside `backtest_store.get_connection()` (both branches); no UPDATE/DELETE anywhere.
- **As-of rule everywhere:** a Tier 1 row or late check stamped after `event_time_utc` is never displayed or used. Compare instants with SQLite `julianday()`, never raw strings (same as `webapp/stats_service.py`).
- **Times:** stored UTC ISO; owner-facing text in SAST via `config.settings.LOCAL_TZ` (format `%Y-%m-%d %H:%M SAST`). Windows triggers are machine-local (the PC runs SAST).
- **Style:** type hints on every Python signature; match surrounding comment density; routes keep exact key-set tests.
- **Line endings:** every touched existing file is CRLF; keep CRLF (`.bat`/`.vbs`/`.ps1` new files CRLF too). Regexes written from a heredoc: check for a 0x08 byte (`od -c`) if you use `\b`.
- **Commits:** one per task; message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **The as-of guard silently breaks fixtures, or is defeated by string comparison.** Many tests call `record_tier1_prediction()` without `logged_at_utc` (so "logged now", 2026-10) for a 2026-09 event; after the guard those rows vanish. Fix the fixture (`logged_at_utc=event_time - dt.timedelta(days=1)`), never weaken the guard. Naive vs `+00:00` stamps must compare as instants.
   - Pinned by `test_tier1_bulk_ignores_a_row_logged_after_the_release`, `test_tier1_bulk_compares_naive_and_offset_stamps_as_instants` (Task 1) and `test_predictions_hides_a_tier1_row_logged_after_the_release` (Task 5).
2. **Formula rows multiply.** Every run has a new as-of, so a naive writer adds a row per run per instrument.
   - Pinned by `test_formula_rows_are_written_once_per_distinct_nowcast` (Task 2).
3. **Wrong sign for an instrument, or a guessed call when the forecast is missing.** Gold is inverse, US30 risk-sentiment, USDJPY direct; in line must be neutral; no readable forecast must write nothing (not "neutral").
   - Pinned by `test_formula_direction_per_instrument`, `test_formula_in_line_is_neutral_for_every_instrument` (Task 2) and `test_run_without_a_forecast_writes_no_tier1_row_and_reports_it` (Task 2).
4. **Formula and judgment drift apart.** A formula title without a `SERIES_MAP` entry would never be captured; the research task re-logging CPI would overwrite the formula call on the dashboard.
   - Pinned by `test_formula_titles_equal_the_cleveland_series_map` (Task 2), `test_plan_lists_only_judgment_titles` and `test_record_call_refuses_a_formula_title` (Task 4).
5. **A late check changes the call of record, or fires on every run.**
   - Pinned by `test_record_late_check_never_writes_tier1_predictions` (Task 1) and the `test_late_check_reason_*` cases (Task 1).
6. **The Windows tasks do not catch up after sleep, or use the wrong window.**
   - Pinned by `test_register_tier1_tasks_script_has_both_tasks_with_start_when_available` and `test_tier1_bat_passes_192_hours_for_weekly_and_48_by_default` (Task 3).

## Plan decisions (beyond the spec text)

- The as-of guard also applies to `get_latest_tier1_prediction_for_occurrence`, so `scoring/tier1_comparison.py` can no longer grade a post-release row, and to the History tab (it shares the bulk read).
- The research task gets a CLI (`scripts/tier1_research.py`) instead of free-hand Python: fixed commands can be pre-approved (the stall cause in T1-01/SCH-02), and "the first pre-release call stands" and the late-check rule are enforced in code, not in prompt text.
- Late-check staleness is measured from the newest reading (call or late check), and the 24h check fires at most once per occurrence and only when the newest reading predates the 24h window; otherwise every Mon/Thu run after day 5 would log a check.
- Formula row dedupe follows the spec (per distinct nowcast value): a revised forecast with an unchanged nowcast does not write a new row.
- A missing forecast writes no formula row (never a guessed neutral); it is reported, and becomes exit 2 inside 24h of the release.

---

### Task 1: Tier 1 registry, as-of guard and late-check storage (T2, T6 store side, T7 storage) — *integration*

**Files:**
- Create: `data_layer/tier1_events.py`, `tests/test_tier1_events.py`
- Modify: `scoring/backtest_store.py`, `webapp/stats_service.py` (one line), `tests/test_backtest_store.py`, plus fixture-only fixes in any test the guard breaks

**Interfaces:**
- `data_layer/tier1_events.py` (imports only `datetime` and `typing`):
  - `TIER1_FORMULA = "formula"`, `TIER1_MARKET_IMPLIED = "market_implied"`, `TIER1_JUDGMENT = "judgment"`, `TIER1_TIERS: tuple[str, ...]`.
  - `TIER1_EVENTS: dict[str, str]` in this order: `"CPI m/m"`, `"Core CPI m/m"` -> formula; `"PPI m/m"`, `"Non-Farm Employment Change"`, `"FOMC Meeting Minutes"`, `"FOMC Statement"`, `"Federal Funds Rate"`, `"Prelim GDP q/q"`, `"Advance GDP q/q"`, `"Final GDP q/q"`, `"GDP q/q"`, `"Core PCE Price Index m/m"`, `"ISM Manufacturing PMI"`, `"ISM Services PMI"`, `"Retail Sales m/m"`, `"Core Retail Sales m/m"` -> judgment. Comment: market_implied is reserved for B12 (Kalshi).
  - `TIER1_FORMULA_SOURCE = "Cleveland Fed nowcast (formula)"`, `TIER1_FORMULA_CONFIDENCE = "Likely"` (comment: a published model output, primary-sourced but a model, so never "Certain").
  - `TIER1_RESEARCH_LOOKAHEAD = dt.timedelta(days=8)`, `LATE_CHECK_STALE_AFTER = dt.timedelta(days=5)`, `LATE_CHECK_WINDOW = dt.timedelta(hours=24)`, `LATE_CHECK_REASONS = ("stale_call", "release_within_24h")`.
  - `def tier1_titles(tier: str) -> list[str]` — titles of that tier in dict order; `ValueError` for an unknown tier.
  - `def tier1_row_tier(source: str) -> str` — `"formula"` when `source == TIER1_FORMULA_SOURCE`, else `"judgment"` (a pre-B3 LLM row for CPI is judgment).
  - `def late_check_reason(newest_reading_utc: dt.datetime, event_time_utc: dt.datetime, now_utc: dt.datetime, has_window_check: bool) -> Optional[str]` — all aware. Rule: `now >= event` -> None; `event - now <= 24h` -> `"release_within_24h"` only if `not has_window_check and newest_reading < event - 24h`, else None; otherwise `"stale_call"` if `now - newest_reading > 5 days`, else None. `newest_reading` = the later of the call's `logged_at_utc` and the newest late check's `checked_at_utc`.
- `scoring/backtest_store.py`:
  - Schema: `tier1_late_checks(id INTEGER PRIMARY KEY AUTOINCREMENT, event_title TEXT NOT NULL, instrument TEXT NOT NULL, event_time_utc TEXT NOT NULL, call_of_record_id INTEGER NOT NULL, call_direction TEXT NOT NULL, outcome TEXT NOT NULL CHECK (outcome IN ('same','changed')), new_value TEXT NOT NULL, new_confidence TEXT NOT NULL, new_direction TEXT NOT NULL, source TEXT NOT NULL, reason TEXT NOT NULL CHECK (reason IN ('stale_call','release_within_24h')), checked_at_utc TEXT NOT NULL)`. Comment: append-only log; never changes the call of record (owner ruling 2026-10-21).
  - `@dataclass class Tier1LateCheckRow` with exactly those columns.
  - `get_latest_tier1_predictions_bulk(...)` and `get_latest_tier1_prediction_for_occurrence(conn, event_title, instrument, event_time_utc, source: Optional[str] = None)` add `AND julianday(logged_at_utc) <= julianday(event_time_utc)`; the single getter also filters `source = ?` when `source` is given. Docstrings say why (T1-03: post-release rows are hindsight).
  - `def record_tier1_late_check(conn, event_title: str, instrument: str, event_time_utc: dt.datetime, new_value: str, new_confidence: str, new_direction: str, source: str, reason: str, checked_at_utc: Optional[dt.datetime] = None) -> int` — the call of record is `get_latest_tier1_prediction_for_occurrence(...)` (the row the dashboard shows); `ValueError` when there is none, when `checked_at` is naive or after `event_time_utc`, or when confidence / direction / reason is invalid (reuse `_VALID_TIER1_CONFIDENCE` and `Direction`). `outcome = "same" if new_direction == call.predicted_direction else "changed"`. Plain INSERT; never touches `tier1_predictions`.
  - `def get_tier1_late_checks_for_occurrence(conn, event_title: str, instrument: str, event_time_utc: dt.datetime) -> list[Tier1LateCheckRow]` — ascending by `checked_at_utc`, matched with `julianday(event_time_utc) = julianday(?)`.
  - `def get_latest_tier1_late_checks_bulk(conn, event_titles: list[str], instruments: list[str]) -> dict[tuple[str, str, str], Tier1LateCheckRow]` — same key normalisation as the Tier 1 bulk (`fromisoformat(...).isoformat()`), newest `checked_at_utc` wins.
- `webapp/stats_service.py`: `NOWCAST_EVENTS = frozenset(tier1_titles(TIER1_FORMULA))`.

**Steps:**
- [ ] Write failing tests in `tests/test_tier1_events.py`:
  - `test_tier1_events_has_16_titles_2_formula_14_judgment_0_market_implied` — exact title lists above; every value in `TIER1_TIERS`.
  - `test_tier1_titles_rejects_an_unknown_tier`.
  - `test_tier1_row_tier_formula_only_for_the_formula_source` — `"Cleveland Fed nowcast (formula)"` -> formula; `"BLS/ISM"` -> judgment.
  - `test_late_check_reason_*` with call logged `2026-11-02T06:00Z`, release `2026-11-12T13:30Z`: now `11-05T06:00Z` -> None; now `11-09T06:06Z` -> `"stale_call"`; now `11-11T14:00Z` -> `"release_within_24h"`; same with `has_window_check=True` -> None; now = release -> None; call logged `11-11T20:00Z`, now `11-12T06:00Z` -> None; newest reading a late check at `11-09T06:06Z`, now `11-10T06:00Z` -> None (fresh reading resets staleness).
- [ ] Write failing tests in `tests/test_backtest_store.py`:
  - `test_tier1_bulk_ignores_a_row_logged_after_the_release` — release `2026-11-12T13:30Z`; row A bullish logged `11-10T08:00Z`, row B bearish logged `11-12T14:00Z` -> bulk returns A; with only B -> key absent; a row logged exactly at the release is kept.
  - `test_tier1_bulk_compares_naive_and_offset_stamps_as_instants` — event stored naive `2026-11-12T13:30:00`, logged `2026-11-12T13:31:00+00:00` -> excluded; logged `2026-11-12T15:29:00+02:00` (13:29Z) -> kept.
  - `test_single_tier1_getter_has_the_same_as_of_guard_and_a_source_filter`.
  - `test_record_late_check_outcome_same_and_changed` — call bullish; new bullish -> `"same"`; new bearish -> `"changed"`; both rows kept (append-only), `call_of_record_id` = the call's id.
  - `test_record_late_check_never_writes_tier1_predictions` — `tier1_predictions` row count and the bulk result unchanged after two late checks.
  - `test_record_late_check_refuses_no_call_naive_or_post_release_time_and_bad_values` — each raises `ValueError`.
  - `test_latest_late_checks_bulk_newest_wins_per_occurrence`.
- [ ] Run `python -m pytest -q -p no:warnings tests/test_tier1_events.py tests/test_backtest_store.py` — expect FAIL.
- [ ] Implement as specified. Add the table to `_SCHEMA` (no migration helper needed: CREATE IF NOT EXISTS runs in both branches). Switch `stats_service.NOWCAST_EVENTS`.
- [ ] Run the two files — expect PASS.
- [ ] Run the full suite. For every newly failing test that logged a Tier 1 row "now" for a past event, pass `logged_at_utc=<event_time> - dt.timedelta(days=1)` (fixture only; list the touched tests in the commit body). The guard stays as is.
- [ ] Commit: `feat(B3): Tier 1 registry, as-of guard on Tier 1 reads, append-only late-check log`.

---

### Task 2: Formula capture writes the dashboard Tier 1 row; `--window-hours` (T4 script side, T5) — *judgment*

**Files:**
- Create: `webapp/tier1_formula.py`, `tests/test_tier1_formula.py`
- Modify: `scripts/capture_nowcast_from_cleveland.py`, `tests/test_capture_nowcast_from_cleveland.py`

**Interfaces:**
- `webapp/tier1_formula.py` (pure except `record_formula_calls`):
  - `SIDE_LABELS = {1: "hotter than forecast", 0: "in line with forecast", -1: "cooler than forecast"}`.
  - `def surprise_side(nowcast: float, forecast_text: Optional[str]) -> Optional[int]` — `stats_rules.parse_number` + `tolerance` + `side`; None when the forecast is unreadable.
  - `def formula_direction(event_title: str, side: int, symbol: str) -> str` — `market_lean` mapped `{"buy": "bullish", "sell": "bearish", "mixed": "neutral"}`.
  - `def formula_value_text(nowcast: float, forecast_text: str, side: int, value_date: dt.date, captured_at_utc: dt.datetime) -> str` — exactly `f"Cleveland Fed nowcast {nowcast:.4f}% vs forecast {forecast_text}: {SIDE_LABELS[side]} (Fed value dated {value_date.isoformat()}, captured {captured_at_utc.astimezone(LOCAL_TZ):%Y-%m-%d %H:%M} SAST)"`.
  - `def nowcast_in_value_text(text: str) -> Optional[float]` — regex `^Cleveland Fed nowcast (-?\d+\.\d{4})% vs forecast `; None if no match.
  - `def record_formula_calls(bt_conn: Optional[sqlite3.Connection], event_title: str, release_utc: dt.datetime, nowcast: float, forecast_text: Optional[str], value_date: dt.date, symbols: list[str], now_utc: dt.datetime, dry_run: bool = False) -> dict` — returns `{"written": [(symbol, direction)], "unchanged": [symbol], "pending": Optional[str]}`. No readable forecast -> nothing written, `pending = "no readable forecast yet"`. Per symbol: skip as unchanged when `get_latest_tier1_prediction_for_occurrence(bt_conn, title, symbol, release_utc, source=TIER1_FORMULA_SOURCE)` exists and `nowcast_in_value_text(row.value) == round(nowcast, 4)`; otherwise `record_tier1_prediction(..., confidence=TIER1_FORMULA_CONFIDENCE, source=TIER1_FORMULA_SOURCE, logged_at_utc=now_utc)`. `dry_run` -> report every symbol as would-write, touch nothing.
- `scripts/capture_nowcast_from_cleveland.py`:
  - `_due_releases(dash_conn, now, window: dt.timedelta = WINDOW)` reads titles from `tier1_titles(TIER1_FORMULA)` instead of `SERIES_MAP`, and returns the forecast text too: `list[tuple[str, dt.datetime, Optional[str]]]` (callers of `latest_nowcasts` pass `(title, release)` pairs).
  - `run(dash_conn, bt_conn, now, fetch=None, dry_run=False, window: dt.timedelta = WINDOW) -> dict` — summary gains `"tier1_rows": [(title, release_iso, symbol, direction, "written"|"unchanged")]` and `"tier1_pending": [(title, release_iso, reason)]`. Tracked symbols come from `webapp.store.list_tracked_symbols(dash_conn)` (read once, only when something is due). After each successful `capture()` call `record_formula_calls`. New constant `MISSING_FORECAST_ALERT_WITHIN = dt.timedelta(hours=24)`: a pending reason for a release that close to `now` also goes to `"skipped"` (exit 2); earlier it only prints (the next daily run retries).
  - Message uses the window: `f"No CPI-family release within {hours:g} hours: nothing to capture."`.
  - CLI `--window-hours` (type=float, default 48; `parser.error` when <= 0 or > 240). `main` prints one `  TIER1 {title} {symbol}: {direction} ({written|unchanged|would write})` line per row and `  TIER1 PENDING {title} release {iso}: {reason}`. Module docstring updated (window, dashboard row).

**Steps:**
- [ ] Write failing tests in `tests/test_tier1_formula.py`:
  - `test_surprise_side_uses_one_rounding_step_of_the_forecast` — `(0.47, "0.3%") -> 1`, `(0.359, "0.4%") -> 0`, `(0.26, "0.3%") -> 0`, `(0.15, "0.3%") -> -1`, `(0.4, None) -> None`, `(0.4, "n/a") -> None`.
  - `test_formula_direction_per_instrument` — CPI m/m side +1: XAUUSD bearish, US30 bearish, EURUSD bearish, USDJPY bullish; side -1 flips each.
  - `test_formula_in_line_is_neutral_for_every_instrument` — side 0 -> neutral for all four.
  - `test_value_text_round_trips_the_nowcast_and_shows_sast` — `0.5307`, `"0.3%"`, +1, `2026-11-10`, captured `2026-11-11T05:00Z` -> text contains `"0.5307%"`, `"hotter than forecast"`, `"2026-11-11 07:00 SAST"`; `nowcast_in_value_text(text) == 0.5307`; a judgment text -> None.
  - `test_formula_rows_are_written_once_per_distinct_nowcast` — symbols `["US30", "XAUUSD"]`: first call writes 2 rows; same nowcast an hour later -> 0 new rows, both unchanged; nowcast `0.5310` -> 2 new rows. A pre-existing judgment row for the same occurrence does not count as a formula row.
  - `test_record_formula_calls_without_a_forecast_writes_nothing`.
  - `test_formula_rows_use_likely_and_the_formula_source`.
- [ ] Add failing tests in `tests/test_capture_nowcast_from_cleveland.py` (existing tests keep passing: their dash DB has no tracked symbols):
  - `test_formula_titles_equal_the_cleveland_series_map` — `set(tier1_titles(TIER1_FORMULA)) == set(SERIES_MAP)`.
  - `test_run_writes_dashboard_rows_per_tracked_symbol` — tracked XAUUSD and US30, fixture forecast `"0.3%"`, DATA as today: CPI m/m (0.47) -> both bearish; Core CPI m/m (0.26) -> both neutral; 4 rows, `logged_at_utc == NOW`, all `< RELEASE`.
  - `test_run_twice_with_the_same_nowcast_adds_snapshots_but_not_tier1_rows` — second run at `NOW + 1h`: snapshots 4, tier1 rows still 4.
  - `test_run_without_a_forecast_writes_no_tier1_row_and_reports_it` — forecast NULL: release 31.5h away -> `tier1_pending` non-empty and exit 0 via `main`; release 7.5h away -> also in `skipped`, exit 2. Snapshot still captured in both.
  - `test_window_hours_192_includes_a_release_8_days_out_and_48_excludes_it` — release `NOW + 191h`.
  - `test_cli_rejects_a_non_positive_window`.
  - `test_cli_dry_run_reports_tier1_rows_and_writes_nothing`.
- [ ] Run both files — expect FAIL.
- [ ] Implement as specified.
- [ ] Run both files — expect PASS; run the full suite.
- [ ] Commit: `feat(B3): formula capture writes the dashboard Tier 1 row; --window-hours`.

---

### Task 3: Windows tasks for the formula capture (T4) — *mechanical*

**Files:**
- Create: `scripts/tier1_capture_scheduled.bat`, `scripts/tier1_capture_scheduled.vbs`, `scripts/register_tier1_tasks.ps1`, `tests/test_tier1_task_scripts.py`

**Interfaces:**
- `.bat` (copy `reaction_compute_scheduled.bat`): `cd /d "%~dp0.."`, `PYTHONIOENCODING=utf-8`; `set WINDOW=48`, `if /i "%1"=="weekly" set WINDOW=192`; runs `python scripts\capture_nowcast_from_cleveland.py --window-hours %WINDOW% --bt-db scoring\backtest_log.db --dash-db webapp\dashboard.db`, appending start/finish (with `%ERRORLEVEL%`) lines to `scripts\tier1_capture_scheduled.log`.
- `.vbs` (copy `reaction_compute_scheduled.vbs`): hidden launcher, passes its first argument through.
- `.ps1` (copy the header and principal/settings of `register_reaction_tasks.ps1`; no XML trick): `New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)`; `NewsEngine_Tier1Weekly` = `New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 07:00`, action `wscript.exe //B "<vbs>" weekly`; `NewsEngine_Tier1Daily` = `New-ScheduledTaskTrigger -Daily -At 07:00`, action `wscript.exe //B "<vbs>"`; both `Register-ScheduledTask ... -Force`. Header comment: times are machine-local (SAST); applied at deploy by the controller; re-run after moving the repo; WakeToRun deliberately not set (owner's machine setting).

**Steps:**
- [ ] Write failing static tests `tests/test_tier1_task_scripts.py` (read the files as bytes; nothing is executed):
  - `test_register_tier1_tasks_script_has_both_tasks_with_start_when_available` — contains `NewsEngine_Tier1Weekly`, `NewsEngine_Tier1Daily`, `-StartWhenAvailable`, `-DaysOfWeek Monday`, `-Daily`, `-At 07:00` (twice), `tier1_capture_scheduled.vbs`, and no `schtasks`.
  - `test_tier1_bat_passes_192_hours_for_weekly_and_48_by_default` — `set WINDOW=48`, `"%1"=="weekly" set WINDOW=192`, `--window-hours %WINDOW%`, both explicit `--bt-db`/`--dash-db` paths, the log path.
  - `test_tier1_task_scripts_use_crlf` — every `\n` is preceded by `\r` in all three files.
- [ ] Run — expect FAIL. Create the three files (CRLF). Run — expect PASS; full suite.
- [ ] Commit: `feat(B3): Windows task scripts for the weekly and daily formula capture`.

---

### Task 4: Research CLI for judgment events — plan, record-call, record-late-check (T5 skip, T7) — *integration*

**Files:**
- Create: `scripts/tier1_research.py`, `tests/test_tier1_research.py`

**Interfaces** (`main(argv: Optional[list[str]] = None, now: Optional[dt.datetime] = None) -> int`; `--dash-db` (opened with `open_dash_readonly`) and `--bt-db` on every subcommand; exit 0 ok, 2 refused with a one-line reason on stderr):
- `plan [--days 8]` — prints JSON (indent 2) to stdout: a list ordered by event time of `{"event_title", "event_time_utc", "event_time_sast", "tier": "judgment", "instruments": {SYMBOL: {...}}}` for USD `event_history` rows whose title is in `tier1_titles(TIER1_JUDGMENT)` and `now < event_time <= now + days`. Per tracked symbol: `{"status": "needs_call"}`; or `{"status": "late_check_due", "reason": ..., "call": {...}}`; or `{"status": "covered", "call": {...}}`. `call` = `{"id", "value", "confidence", "source", "predicted_direction", "logged_at_utc"}` of the call of record. The reason comes from `late_check_reason(newest_reading, event_time, now, has_window_check)` using `get_tier1_late_checks_for_occurrence`.
- `record-call --event --release --instrument --value --confidence --source --direction` — refuses: title not judgment tier (message names the formula capture for formula titles), instrument not tracked, `--release` without an offset (reuse `capture_nowcast_snapshot.parse_aware`), `now >= release`, or a pre-release call already exists ("the first pre-release call stands; use record-late-check"). Else `record_tier1_prediction(..., logged_at_utc=now)`; prints the id.
- `record-late-check` (same arguments) — refuses unless the plan rule says it is due now (prints "not due"); else `record_tier1_late_check(..., reason=<computed>, checked_at_utc=now)`; prints `late check <id>: <same|changed> (<reason>)`.

**Steps:**
- [ ] Write failing tests (temp DB files; `now` injected; tracked XAUUSD and US30):
  - `test_plan_lists_only_judgment_titles` — events CPI m/m, Core CPI m/m, PPI m/m, Final GDP q/q, a Medium non-Tier-1 title and a non-USD PPI m/m within 8 days -> only the USD PPI m/m and Final GDP q/q appear.
  - `test_plan_window_is_8_days_and_excludes_past_events` — 191h in, 193h out, 1 minute ago out.
  - `test_plan_status_needs_call_covered_and_late_check_due` — with the Task 1 timestamps: no row -> needs_call; row logged 3 days ago -> covered; 7 days ago -> late_check_due/stale_call; release 23h away and call 3 days old -> late_check_due/release_within_24h.
  - `test_record_call_refuses_a_formula_title` — `CPI m/m` -> exit 2, stderr mentions the formula capture, no row.
  - `test_record_call_refuses_a_second_pre_release_call_and_a_past_release` — exit 2 each, row count unchanged.
  - `test_record_late_check_records_changed_without_touching_the_call` — due stale call bullish, new bearish -> exit 0, output contains `changed (stale_call)`, `tier1_predictions` unchanged.
  - `test_record_late_check_refuses_when_not_due` — right after one stale check -> exit 2 "not due".
  - `test_unknown_instrument_and_naive_release_are_refused`.
- [ ] Run — expect FAIL. Implement. Run — expect PASS; full suite.
- [ ] Commit: `feat(B3): Tier 1 research CLI (plan / record-call / record-late-check)`.

---

### Task 5: Dashboard shows the tier, the late check and which Tier 1 the conflict used (T2 display, T6 route, T7 display, T8) — *integration*

**Files:**
- Modify: `webapp/conflict.py`, `webapp/predictions_service.py`, `webapp/history.py`, `webapp/static/js/dashboard/card-view-model.js`, `webapp/static/js/dashboard/card.js`, tests `tests/test_webapp_predictions_service.py`, `tests/test_webapp_app.py`, `tests/test_webapp_history.py`, `webapp/static/js/dashboard/card-view-model.test.js`, `webapp/static/js/dashboard/card.test.js`

**Interfaces:**
- `compute_tier1_sentiment_conflict(sentiment_direction, tier1_direction, tier1_tier: Optional[str] = None) -> Optional[dict]` — the dict is now exactly `{"sentiment_direction", "tier1_direction", "tier1_tier"}` (conflict.py stays zero-import; the caller passes the string).
- `_tier1_prediction_dict(tier1_row, late_check_row=None) -> dict` — exactly `{"value", "confidence", "source", "predicted_direction", "tier", "late_check"}`; `tier = tier1_row_tier(tier1_row.source)`; `late_check` = `{"outcome", "new_direction", "checked_at_utc"}` only when `late_check_row.call_of_record_id == tier1_row.id`, else None.
- `build_predictions_payload`: one `get_latest_tier1_late_checks_bulk` call in its own fail-open try/except (log a warning, use `{}`); conflict call passes `tier1_pred["tier"]`. `history.py`: both conflict calls pass `tier1_row_tier(tier1_row.source) if tier1_row is not None else None`; its `_tier1_prediction_dict(tier1_row)` calls get `late_check=None`.
- JS: `buildTier1PredictionViewModel` adds `tierLabel` (`formula` -> `"formula"`, `judgment` -> `"judgment"`, `market_implied` -> `"market-implied"`, else null) and `lateCheckChangedLabel` (`directionLabel(late_check.new_direction)` when `late_check?.outcome === "changed"`, else null). `tier1PredictionTemplate` header becomes `🧮 Tier 1 [${tierLabel}] (${symbolForCard}): <b>…</b>` (no brackets when null) plus `<div class="tier1-late-check meta-text-sm">late check: changed, now ${lateCheckChangedLabel}</div>` when set. `buildTier1SentimentConflictViewModel` adds `tierLabel` (same map); text `⚠ Tier 1 (${tierLabel}) vs. sentiment disagree: …` (no parentheses when null).

**Steps:**
- [ ] Update / add failing Python tests:
  - `tests/test_webapp_predictions_service.py`: opposing calls with `tier1_tier="formula"` -> `{"sentiment_direction": "bearish", "tier1_direction": "bullish", "tier1_tier": "formula"}`; without it -> `"tier1_tier": None`; the None/neutral cases unchanged.
  - `tests/test_webapp_app.py`: the existing exact `tier1_prediction` dict gains `"tier": "judgment", "late_check": None`; the conflict dict gains `"tier1_tier": "judgment"`. New `test_predictions_tier1_prediction_key_set_is_exact`, `test_predictions_hides_a_tier1_row_logged_after_the_release` (only a post-release row -> `tier1_prediction is None`, no conflict), `test_predictions_conflict_names_the_formula_tier` (row with source `"Cleveland Fed nowcast (formula)"` -> `tier1_tier == "formula"` and `tier == "formula"`), `test_predictions_shows_a_changed_late_check_for_the_call_of_record`.
  - `tests/test_webapp_history.py`: exact `tier1_prediction` dicts gain the two keys; `tier1_conflict` gains `"tier1_tier"`.
- [ ] Update / add failing JS tests: `[formula]` appears in the Tier 1 header for a formula row and no `[` for a row without tier; `late check: changed, now SELL` renders only for `outcome: "changed"`; the conflict line reads `Tier 1 (judgment) vs. sentiment disagree`.
- [ ] Run `python -m pytest -q -p no:warnings tests/test_webapp_predictions_service.py tests/test_webapp_app.py tests/test_webapp_history.py` and `npm test` — expect FAIL.
- [ ] Implement as specified.
- [ ] Run — expect PASS; full suites.
- [ ] Commit: `feat(B3): dashboard shows Tier 1 tier, changed late checks and the conflict's Tier 1 source`.

---

### Task 6: Methodology export, deploy runbook, inventory and roadmap (T3, T4/T5/T7 deploy text) — *judgment*

**Files:**
- Create: `scripts/export_tier1_methodology.py`, `docs/tier1-methodology.md`, `docs/tier1-b3-deploy.md`, `tests/test_export_tier1_methodology.py`
- Modify: `docs/feature-inventory-2026-09-11.md`, `docs/roadmap-2026-10-20.md`

**Interfaces:**
- `export_tier1_methodology.py`: `def render(workbook_path: Path) -> str` and `main(argv=None) -> int` (`--check` exits 1 when `docs/tier1-methodology.md` differs from `render()`). Reads every `POC_*` sheet with `openpyxl` (read-only, `data_only=True`). `SECTIONS: dict[str, dict]` maps sheet -> `{"titles": [...], "rule": str, "rejected": [str], "confidence": str}`, hand-written from the sheet and today's SKILL.md bullets. Per sheet, output: `## <sheet>` / covered titles with their tier from `TIER1_EVENTS` / **Rule** / **Rejected or not verified** / **Confidence rules** / then every data row verbatim as `- **<Tier>** — <Indicator>: <Mechanism> (Lag: …; Confidence: …; Evidence: …)` and the closing note paragraph. `POC_Sub_Event_Consolidation` gets a section with no titles. The intro states the source workbook, that the export is regenerated with the script, and the formula rule and "Likely" confidence of Task 2.
- `docs/tier1-b3-deploy.md` (applied at deploy by the controller; nothing in it runs during the build):
  1. After merge, from the live worktree: `python scripts/capture_nowcast_from_cleveland.py --dry-run --window-hours 192`, then run `powershell -ExecutionPolicy Bypass -File scripts\register_tier1_tasks.ps1`; confirm with `Get-ScheduledTask NewsEngine_Tier1*` (StartWhenAvailable True).
  2. After the first NewsEngine_Tier1Daily run logs exit 0 or "nothing to capture": disable Claude task `tier1-nowcast-release-eve` (retired; the Windows tasks replace it).
  3. Replace `C:\Users\Masoodt\.claude\scheduled-tasks\tier1-cpi-ppi-autoresearch\SKILL.md` with the full text in the doc's "New SKILL.md" section, and pre-approve `python scripts/tier1_research.py` (plan / record-call / record-late-check) for that task.
  4. Rollback: `Unregister-ScheduledTask NewsEngine_Tier1Weekly/Daily`, re-enable release-eve, restore the old SKILL.md (kept in the doc's "Previous SKILL.md" section).
- "New SKILL.md" = today's file copied verbatim with only these changes:
  - `description:` -> `Twice-weekly (Mon/Thu 08:06 SAST) Tier 1 research with an 8-day lookahead for upcoming USD JUDGMENT releases (PPI/NFP/FOMC/GDP/Core PCE/ISM/Retail): logs a researched call when none exists and a late check when a call is stale or the release is within 24h. CPI m/m and Core CPI m/m are formula-captured by Windows tasks, not researched here.`
  - OBJECTIVE paragraph -> `OBJECTIVE: Keep scoring/backtest_store.py's tier1_predictions table current for upcoming USD releases whose Tier 1 tier is "judgment" in data_layer/tier1_events.py (TIER1_EVENTS is the single source of truth for which titles this task covers; never use a title list from this prompt). CPI m/m and Core CPI m/m are tier "formula": the Windows tasks NewsEngine_Tier1Weekly and NewsEngine_Tier1Daily capture the Cleveland Fed nowcast and write their Tier 1 rows deterministically, so this task never researches or logs them. Methodology: docs/tier1-methodology.md (plain-text export of the workbook's POC sheets; the workbook itself is docs/News_Engine_Causation_Matrix_v2.xlsx).`
  - STEP 1 and STEP 2 -> `STEP 1 — Get the work list: run python scripts/tier1_research.py plan. It prints JSON with one entry per upcoming judgment occurrence in the next 8 days and, per tracked instrument, a status: "needs_call" (no pre-release call yet), "late_check_due" (with reason stale_call or release_within_24h and the call of record) or "covered". Do not query the databases yourself; the plan already applies the tracked-instrument list, the title list and the as-of rules. If the list is empty or everything is covered, say so and stop.`
  - The CPI bullet in STEP 3 -> `- CPI m/m / Core CPI m/m: NOT researched by this task (formula tier, captured by the Windows tasks). If either ever appears in the plan output, stop and report it as a bug.`; the STEP 3 lead-in says to read the event's section of docs/tier1-methodology.md.
  - SUB-READING CONSOLIDATION scope -> `(applies to PPI m/m, Core PCE Price Index m/m, and Retail Sales m/m/Core Retail Sales m/m …)` (the CPI case evidence sentences stay).
  - STEP 4 -> `STEP 4 — Persist (only through the CLI, one command per instrument; the value, confidence and source are the same for every instrument, the direction can differ): for "needs_call" run python scripts/tier1_research.py record-call --event "<title>" --release <event_time_utc from the plan> --instrument <SYMBOL> --value "<what you found and why>" --confidence <Certain|Likely|Guessing> --source "<sources with URLs>" --direction <bullish|bearish|neutral>. For "late_check_due" research the same way and run python scripts/tier1_research.py record-late-check with the same arguments: it records "same" or "changed" against the call of record and never changes that call (owner ruling: the first pre-release call stands). A refused command (exit 2) is reported, never worked around.`
  - STEP 5 adds `which late checks were recorded (same/changed, with the new reading)`.
  - HARD CONSTRAINTS bullet on code edits -> `Do not modify any file. This task only runs scripts/tier1_research.py (plan, record-call, record-late-check); it never writes to a database any other way.`
- Inventory: B3 row in the roadmap table -> `built on branch b3-tier1-reliable (not merged)`; scheduled-task table gains `NewsEngine_Tier1Weekly` (Mon 07:00, `scripts/tier1_capture_scheduled.vbs weekly`, SWA True, registered at deploy) and `NewsEngine_Tier1Daily` (daily 07:00, SWA True); release-eve note -> `to be disabled at B3 deploy`; a feature row describing Tasks 1-5 (formula rule, confidence Likely, dedupe rule, as-of guard, late checks, CLI, conflict tier label). Roadmap status line appends `B3 built on branch b3-tier1-reliable 2026-10-21 (not merged)`.

**Steps:**
- [ ] Write failing tests (`pytest.importorskip("openpyxl")`):
  - `test_every_poc_sheet_has_a_section_and_every_tier1_title_is_covered_once` — the sheet set in the workbook equals `SECTIONS`' keys; each `TIER1_EVENTS` title appears in exactly one section.
  - `test_render_is_deterministic_and_the_committed_doc_is_current` — `render()` twice is equal and equals `docs/tier1-methodology.md`.
  - `test_rejected_indicators_are_named` — rendered text names ADP (NFP), consumer confidence (Retail Sales), unadjusted same-month CPI (Core PCE).
- [ ] Run — expect FAIL. Write the script and `SECTIONS`, generate the doc, write `docs/tier1-b3-deploy.md` (copy the current SKILL.md from the read-only path; never edit that path), update the inventory and roadmap (CRLF preserved).
- [ ] Run — expect PASS; full suites.
- [ ] Commit: `docs(B3): Tier 1 methodology export, deploy runbook, inventory and roadmap`.
