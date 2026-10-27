# B8 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each USD surprise is measured against that indicator's own typical miss (surprise / sigma of its PRIOR surprises), so NFP, CPI and claims become comparable; the 2026 event history is filled from FRED/ALFRED first prints (seeded once, then kept filled for Medium and Low titles too); and a read-only report lists which past readings change direction. This batch changes how calls are made (dashboard essence calls and precursor contributions); the change date is logged.

**Architecture:** A new read-only `data_layer/fred_history.py` reads ALFRED vintages (the value as published on release day, never FRED's latest revision) for a title -> FRED series map. `scripts/seed_fred_history.py` (dry run by default, `--apply` to write, auto-backup) inserts missing 2026 High-impact USD releases and fills missing actuals, and a throttled hourly pass in `webapp/actuals_backfill.py`, called from the scheduler, keeps Medium/Low rows filled. A new `scoring/surprise_scale.py` computes sigma from prior USD rows only and attaches it to `EconomicEvent.surprise_sigma`, which `usd_surprise_score()` uses when present (fallback below 6 prior surprises); `scripts/b8_rescore_report.py` re-scores past readings read-only.

**Tech Stack:** Python 3.14, sqlite3, requests, statistics, pytest; no JS changes.

**Spec reference:** `docs/roadmap-2026-10-20.md` §B8 (U1-U5) plus these owner decisions:
- Do NOT change the Stats call rule (CPI m/m news scale 0.0 -> 23 of 31 "in line" is B9 ST1's job). Stats does not read `usd_surprise_score()` and is untouched except that seeded rows appear in it.
- Do not change B9a `agreement` / `tier1_tier` fields; 70/30 Combined unchanged; never a "conflicting" status.
- JOLTS surprise direction is the owner's decision: logged as an OPEN QUESTION in docs, no direction invented. Never set or fabricate a predicted direction for scoring.
- No ACE/EA/MT5 material. Owner-facing times in SAST (UTC+2), stored UTC ISO.
- dashboard.db is backed up before the seed; the controller applies the seed at deploy (`docs/b8-deploy.md`).

**Verified source facts (2026-10-27, base a83171f, live DB read with mode=ro):**
- 2026 USD event_history: 314 rows, 301 past, actual on 102. By impact (past rows): High 31/42, Medium 3/40, Low 2/166, untagged (hand-seeded) 66/66.
- **U2 root cause [Certain]:** `data_layer/calendar_feed.py:335` reads `actual=item.get("actual") or None`, but the FairEconomy weekly JSON never carries an actual: 0 of 585 `source='live'` rows have one, and today's snapshot shows actual None on all 26 events including ones already released. Every actual therefore comes from a fallback, and both fallbacks are gated to a handful of mostly-High titles: the FRED fast path (`webapp/scheduler.py:188-195`) only covers the 10 titles in `config/settings.py:153` `FRED_SERIES_ID_BY_EVENT_TITLE` and only while the release is still in FF's this-week feed; the web fallback queue only admits the 19 titles in `EVENT_SURPRISE_DIRECTION` (`webapp/store.py:586`) within 48 h (`webapp/actuals_sync.py:40`), and its cloud routine has written 0 rows ever (0 `cloud_web_fallback` rows). Medium/Low titles have no path at all.
- Prior surprises (forecast and actual both present, USD) today: CPI m/m 10, CPI y/y 10, NFP 9, PPI m/m 9, Retail Sales m/m 9, Core CPI y/y 8, Core CPI m/m 7, Unemployment Rate 7, Core PPI m/m 6, Unemployment Claims 6, AHE 5, ADP 4, Import Prices 4, ISM Mfg 3, Core PCE 2, ISM Services / Prelim GDP / Prelim UoM 1. FRED has no consensus forecasts, so seeded rows carry actual + previous only and do NOT deepen sigma; filled actuals on existing FF rows (e.g. 7 Unemployment Claims rows since 2026-09-10 that have forecasts) do.
- `usd_surprise_score()` is called by `webapp/scoring_service.py:38` (dashboard essence calls, via `webapp/scheduler.py:206` and `webapp/predictions_service.py:202`) and `scoring/probability_engine.py:454` (precursor contributions, events built in `get_precursor_events_for`). `classify_surprise()` (event_history `surprise_direction`, the grading truth) is NOT changed.
- JOLTS: `EVENT_INFLUENCE_LINKS` lists ("JOLTS Job Openings", 0.40) as an NFP precursor (`config/settings.py:443`), but JOLTS has no `EVENT_SURPRISE_DIRECTION` entry, so that link never contributes.
- FRED maintenance detection exists: `data_layer/fred_calendar_feed.py::is_maintenance_page` (HTML body containing "maintenance", HTTP 200); `ops/health.py:314` already reports "FRED under maintenance" for the macro calendar.
- Every touched Python/doc file is CRLF. Baseline: pytest 1923 collected (1922 pass + the env-only alpha_vantage failure), npm 231 pass.

## Choices made in this plan (owner can veto before Task 1)

- **Sigma = sample standard deviation of the last <= 24 prior surprises** (actual - forecast, `_parse_numeric` units) of the same title, `country = 'USD'` only, strictly earlier than the event (`julianday <`). Fewer than 6 -> today's percent method. **Floor: one rounding step of the forecast** (0.3% -> 0.1, 225K -> 1000), so a run of exact hits cannot make a 0.1 miss look like 5 sigma.
- **Mapping to the -1..+1 axis: `tanh(z * 0.5)`** (1 sigma -> 0.46, 2 sigma -> 0.76, 3 sigma -> 0.91). Untuned, same caveat as `SURPRISE_SENSITIVITY`. The sign of a surprise never changes (sigma > 0), so direction changes can only happen across the essence neutral band (|score| <= 0.02); the report also lists large probability shifts.
- **Revisions (U4):** every FRED-sourced value is the first print from the ALFRED vintage dated the release day (what the market reacted to). `previous` is the prior period as published that day (revised). NFP and Retail Sales headlines are computed inside that vintage (new level minus/over the revised prior level), which is exactly how BLS/Census publish them. Revisions to earlier months are not folded into the surprise (no consensus for revisions exists here). The existing same-day FRED fast path (`fred_actuals.get_actual_from_fred`, latest vintage, release-week only) is kept: on release day it returns the same first print.
- **Seeded rows:** `source='fred'` (existing provenance, so History/Stats badges and precedence are unchanged), `country='USD'`, `impact=NULL` (FRED does not rate impact; Stats infers it from the title, as for the existing hand-seeded rows), `forecast=NULL`, `surprise_direction=NULL`. Event time = the title's New York release time on the vintage date, stored UTC.
- **Mapping safety gate:** a title's FRED mapping is "verified" when >= 80% of its comparisons with stored rows agree (stored first-print actuals, and FF's `previous` against either the revised or first-print prior). Suspect titles are never written; unverified titles only with `--allow-unverified`. The hourly pass writes a fill only when FF's `previous` on that row matches.
- **GDP, ISM, UoM, CB, S&P PMIs, auctions, speeches are out:** no exact free FRED series or no number (GDP has three estimates per quarter; documented, not seeded).
- **The web fallback gate (`store.py:586`) is left as is** (WebSearch budget); the dead cloud routine is reported to the owner as a finding, not fixed here (it is a Claude scheduled task, outside B8).

## Global Constraints

- Live system off-limits: nothing under `.worktrees/news-engine-live` is modified; its `webapp/dashboard.db` is read only with `mode=ro` (Task 4 report). No Windows/Claude scheduled task, no Telegram (mocked), no push.
- Nothing outside the repo needs deploying: the seed and the post-seed report are run by the controller at deploy per `docs/b8-deploy.md`; the hourly backfill runs inside the existing scheduler thread.
- No schema change. Writes are append-only/first-writer-wins: `INSERT ... ON CONFLICT DO NOTHING` and `UPDATE ... WHERE actual IS NULL`; never `upsert_event_history` for FRED history (it overwrites forecast/previous).
- Tests use temp DBs and a fake `requests.get` only; no test needs `FRED_API_KEY` or the network.
- Non-USD rows are never scored, never part of a sigma history and never filled.
- `classify_surprise`, `EVENT_HISTORY_IN_LINE_TOLERANCE`, the essence 0.02 neutral band, Stats rules, `agreement`/`tier1_tier`, 70/30 and every route payload key set are unchanged.
- Times shown to the owner (dry run, report, docs) in SAST with the UTC value beside it; stored UTC ISO.
- Style: type hints on every signature, `from __future__ import annotations`, surrounding comment density, dated `B8 (2026-10-27)` comments at each changed rule; `if __name__ == "__main__"` on both scripts.
- Line endings: keep CRLF in every touched file; new files CRLF. No regexes are planned; if one is added, write it with the Write tool and assert `b"\x08" not in` the module bytes.
- Full suite after each task from the app dir: `python -m pytest -q -p no:warnings` and `npm test`; only `tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present` may fail.

## Review Focus

- **Look-ahead in sigma** (own row or later rows counted) -> `test_sigma_uses_only_strictly_prior_rows` (Task 3).
- **Short-history fallback off by one** (5 vs 6 priors) -> `test_fallback_below_six_prior_surprises` (Task 3).
- **Non-USD rows mis-scored or polluting sigma** -> `test_non_usd_event_never_scored_even_with_sigma`, `test_sigma_ignores_non_usd_and_null_country_rows` (Task 3), `test_backfill_ignores_non_usd_rows` (Task 2).
- **Revised data leaking in** (latest vintage instead of release-day vintage) -> `test_reading_uses_release_day_vintage_not_latest` (Task 1).
- **Seed not idempotent / duplicates an FF row a few hours or a day off** -> `test_seed_rerun_adds_zero_rows`, `test_seed_skips_release_with_row_within_3_days`, `test_seed_null_country_row_is_ambiguous` (Task 2).
- **Forecast/previous of an existing row overwritten by a fill** -> `test_fill_actual_if_missing_keeps_forecast_previous` (Task 1).
- **Wrong series/units written silently** -> `test_seed_suspect_title_not_written`, `test_backfill_skips_on_previous_mismatch` (Task 2).
- **FRED maintenance HTML (HTTP 200) parsed as data** -> `test_maintenance_page_raises` (Task 1), `test_seed_aborts_on_maintenance` (Task 2).
- **Dry run writes** -> `test_seed_dry_run_writes_nothing` (Task 2).
- **Seeded forecast-NULL rows break Stats or trends** -> `test_seeded_rows_do_not_break_stats_or_trend` (Task 2).
- **Backfill slows or breaks the scheduler cycle** -> `test_backfill_throttled_to_hourly`, `test_scheduler_cycle_survives_backfill_error` (Task 2).
- **Stats/B9a/70-30 drift** -> `test_stats_rows_unchanged_by_surprise_sigma` (Task 3).
- **Report touches the DB** -> `test_report_opens_read_only` (Task 4).

---

## Task 1 — ALFRED vintage reader and append-only store writers (U4 core)  `[integration]`

**Files:** `data_layer/fred_history.py` (new), `data_layer/calendar_feed.py` (add `tick_of`), `webapp/store.py`, `tests/test_fred_history.py` (new), `tests/test_webapp_store.py`.

**Interfaces:**
- `calendar_feed.tick_of(value: Optional[str]) -> Optional[float]`: one rounding step of a published number in `_parse_numeric` units ("0.3%" -> 0.1, "225K" -> 1000.0, "7.23M" -> 10000.0, "-78.3B" -> 1e8, "52" -> 1.0, None/"N/A" -> None).
- `fred_history.FredSeriesSpec` (frozen dataclass): `series_id: str`, `transform: str` ("pch" | "pc1" | "chg" | "lin"), `fmt: str` ("pct1" | "k0" | "m2" | "b1" | "num1"), `scale: float = 1.0` (multiplies the FRED value before formatting), `frequency: str = "monthly"` ("monthly" | "weekly"), `seed: bool = False` (U1 High-impact seed title), `release_time_et: Optional[dt.time] = None` (required when `seed`).
- `fred_history.FRED_HISTORY_SPECS: dict[str, FredSeriesSpec]`, exact FF titles:

| Title | Series | Transform | Format, scale | Seed (time ET) |
|---|---|---|---|---|
| Non-Farm Employment Change | PAYEMS | chg | k0, 1 | yes 08:30 |
| Unemployment Rate | UNRATE | lin | pct1 | yes 08:30 |
| Average Hourly Earnings m/m | CES0500000003 | pch | pct1 | yes 08:30 |
| CPI m/m / CPI y/y | CPIAUCSL | pch / pc1 | pct1 | yes 08:30 |
| Core CPI m/m / Core CPI y/y | CPILFESL | pch / pc1 | pct1 | yes 08:30 |
| PPI m/m | PPIFIS | pch | pct1 | yes 08:30 |
| Core PPI m/m | PPIFES | pch | pct1 | yes 08:30 |
| Retail Sales m/m | RSAFS | pch | pct1 | yes 08:30 |
| Core Retail Sales m/m | RSFSXMV | pch | pct1 | yes 08:30 |
| Core PCE Price Index m/m | PCEPILFE | pch | pct1 | yes 08:30 |
| Import Prices m/m | IR | pch | pct1 | yes 08:30 |
| Unemployment Claims | ICSA (weekly) | lin | k0, 0.001 | yes 08:30 |
| ADP Non-Farm Employment Change | ADPMNUSNERSA | chg | k0, 0.001 | yes 08:15 |
| JOLTS Job Openings | JTSJOL | lin | m2, 0.001 | no |
| Industrial Production m/m | INDPRO | pch | pct1 | no |
| Capacity Utilization Rate | TCU | lin | pct1 | no |
| Housing Starts / Building Permits | HOUST / PERMIT | lin | m2, 0.001 | no |
| Durable Goods Orders m/m / Core Durable Goods Orders m/m | DGORDER / ADXTNO | pch | pct1 | no |
| Factory Orders m/m | AMTMNO | pch | pct1 | no |
| Personal Income m/m / Personal Spending m/m | PI / PCE | pch | pct1 | no |
| Business Inventories m/m | BUSINV | pch | pct1 | no |
| Final Wholesale Inventories m/m | WHLSLRIMSA | pch | pct1 | no |
| Construction Spending m/m | TTLCONS | pch | pct1 | no |
| New Home Sales | HSN1F | lin | k0, 1 | no |
| Existing Home Sales | EXHOSLUSM495S | lin | m2, 1e-6 | no |
| Trade Balance | BOPGSTB | lin | b1, 0.001 | no |
| Federal Budget Balance | MTSDS133FMS | lin | b1, 0.001 | no |
| Consumer Credit m/m | TOTALSL | chg | b1, 1 | no |
| HPI m/m | HPIPONM226S | pch | pct1 | no |
| S&P/CS Composite-20 HPI y/y | SPCS20RNSA | pc1 | pct1 | no |
| Philly Fed Manufacturing Index | GACDFSA066MSFRBPHI | lin | num1 | no |
| Empire State Manufacturing Index | GACDINA066MSFRBNY | lin | num1 | no |

  Series ids marked by the gate as suspect or unavailable at the deploy dry run are dropped from the map in a follow-up commit, not guessed at.
- `class FredMaintenanceError(RuntimeError)`, `class FredFetchError(RuntimeError)`.
- `InitialRelease` (frozen): `period: dt.date`, `vintage_date: dt.date`. `VintageReading` (frozen): `title: str`, `period: dt.date`, `vintage_date: dt.date`, `actual: str`, `previous: Optional[str]` (prior period in the same vintage), `previous_first_print: Optional[str]` (prior period's own first print).
- `class FredClient`: `__init__(self, api_key: str, pace_seconds: float = 0.0, sleep: Callable[[float], None] = time.sleep) -> None`; `initial_releases(self, series_id: str, start: dt.date, end: dt.date) -> list[InitialRelease]` (`/series/observations`, `output_type=4`, `realtime_start=start`, `realtime_end=end`; cached per series); `vintage_levels(self, series_id: str, vintage_date: dt.date, observation_start: dt.date) -> list[tuple[dt.date, float]]` (`realtime_start = realtime_end = vintage_date`, `units=lin`; "." values skipped; cached per (series, vintage)). Every response is checked with `fred_calendar_feed.is_maintenance_page(resp.text)` BEFORE `raise_for_status()` (raise `FredMaintenanceError`); any other failure raises `FredFetchError`. The API key is never printed or put in an error message.
- `transform_at(levels: list[tuple[dt.date, float]], period: dt.date, transform: str) -> Optional[float]`: pch `(L_p / L_prev - 1) * 100`, pc1 against the observation 12 months earlier, chg `L_p - L_prev`, lin `L_p`; L_prev = the observation immediately before `period` in the list; None when a needed point is missing.
- `format_value(value: float, spec: FredSeriesSpec) -> str`: scale, then pct1 `f"{v:.1f}%"`, k0 `f"{v:.0f}K"`, m2 `f"{v:.2f}M"`, b1 `f"{v:.1f}B"`, num1 `f"{v:.1f}"`; a value that rounds to zero prints without a minus sign.
- `reading_for_release(client: FredClient, title: str, release: InitialRelease, prior: Optional[InitialRelease]) -> Optional[VintageReading]` (observation_start = period - 400 days; `previous_first_print` from the prior release's own vintage, a cache hit when releases are walked in order).
- `releases_between(client: FredClient, title: str, start: dt.date, end: dt.date) -> list[VintageReading]` (ascending by vintage_date) and `reading_for_event_date(client: FredClient, title: str, event_date: dt.date, max_lag_days: int = 3) -> Optional[VintageReading]` (the release whose vintage_date is in [event_date, event_date + max_lag_days]).
- `values_match(stored: Optional[str], candidate: Optional[str]) -> bool`: both parse and differ by at most half of `tick_of(stored)` (+1e-9).
- `actual_check(reading: VintageReading, row_actual: Optional[str]) -> str` and `previous_check(reading: VintageReading, row_previous: Optional[str]) -> str`: "match" | "mismatch" | "no_reference"; previous matches if it equals either `previous` or `previous_first_print`.
- `webapp/store.py`:
  - `insert_event_history_if_absent(conn: sqlite3.Connection, title: str, event_time_utc: dt.datetime, forecast: Optional[str], previous: Optional[str], actual: Optional[str], surprise_direction: Optional[str], source: str, impact: Optional[str], country: str, now: dt.datetime) -> bool` (`INSERT ... ON CONFLICT(event_title, event_time_utc) DO NOTHING`; True if inserted; commits).
  - `fill_actual_if_missing(conn: sqlite3.Connection, row_id: int, actual: str, surprise_direction: Optional[str], source: str, now: dt.datetime) -> bool` (`UPDATE event_history SET actual, surprise_direction, source, updated_at_utc WHERE id = ? AND actual IS NULL`; forecast/previous/impact/country untouched; True if a row changed; commits).
  - `find_event_history_near(conn: sqlite3.Connection, title: str, center_utc: dt.datetime, days: int = 3) -> list[sqlite3.Row]` (same title, any country, `abs(julianday(event_time_utc) - julianday(?)) <= days`).

**Steps:**
- [ ] Add failing tests to `tests/test_fred_history.py` (fake `requests.get` patched on `data_layer.fred_history.requests`, routing on `params["output_type"]` / `params["realtime_start"]`; `time.sleep` never called because tests pass `pace_seconds=0`):
  - `test_tick_of`: the six examples above.
  - `test_initial_releases_parses_output_type_4`: params include `output_type=4`, `realtime_start="2026-01-01"`; returns `InitialRelease(period=2026-09-01, vintage_date=2026-10-14)` from an observation `{"date": "2026-09-01", "realtime_start": "2026-10-14", ...}`.
  - `test_reading_uses_release_day_vintage_not_latest`: CPIAUCSL vintage 2026-10-14 levels Aug 323.000, Sep 324.938 (latest vintage, also served by the fake, says Sep 326.000) -> CPI m/m `actual == "0.6%"`; the vintage request has `realtime_start == realtime_end == "2026-10-14"`; and the PAYEMS case: vintage levels Jul 160000, Aug 160130 (Aug first print), Sep 160260 -> Sep NFP `actual == "130K"`, `previous == "130K"` revised-in-vintage, `previous_first_print` from the Aug vintage.
  - `test_transforms`: pch, pc1 (13 monthly points, 12-month lookback), chg, lin, missing prior -> None.
  - `test_format_values`: pct1 0.6 -> "0.6%", -0.04 -> "0.0%"; k0 130.0 -> "130K"; ICSA 219000 scale 0.001 -> "219K"; JTSJOL 7230 scale 0.001 m2 -> "7.23M"; BOPGSTB -78312 scale 0.001 b1 -> "-78.3B"; num1 -0.3 -> "-0.3".
  - `test_maintenance_page_raises`: status 200, text `"<html><body>FRED is down for maintenance</body></html>"` -> `FredMaintenanceError`; a 500 -> `FredFetchError`; the key is absent from both messages.
  - `test_values_match_and_checks`: "0.4%" vs "0.4%" True, vs "0.5%" False; "7.2M" vs "7.23M" True; previous matches the first-print candidate when the revised one differs; None reference -> "no_reference".
  - `test_specs_are_complete`: every `seed=True` spec has `release_time_et`; every key is an exact title string (no leading/trailing spaces).
- [ ] Add failing tests to `tests/test_webapp_store.py`: `test_insert_if_absent_does_nothing_on_conflict` (second insert returns False, original row unchanged); `test_fill_actual_if_missing_keeps_forecast_previous` (row with forecast "0.3%", previous "0.4%", actual NULL -> filled "0.6%", forecast/previous/impact/country unchanged; second fill returns False and keeps "0.6%").
- [ ] Run both files -> FAIL.
- [ ] Implement as specified. `releases_between` walks `initial_releases` in ascending order so each prior vintage is fetched once.
- [ ] Run both files -> PASS; full suites -> PASS.
- [ ] Commit: `feat(B8): ALFRED release-day vintage reader and append-only event_history writers` + `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Task 2 — Seed script (U1) and hourly Medium/Low backfill (U2)  `[integration]`

**Files:** `scripts/seed_fred_history.py` (new), `webapp/actuals_backfill.py` (new), `webapp/scheduler.py`, `tests/test_seed_fred_history.py` (new), `tests/test_actuals_backfill.py` (new), `tests/test_webapp_scheduler.py`.

**Interfaces:**
- `seed_fred_history.SeedReport` (dataclass): `inserted: list[tuple[str, str]]`, `filled: list[tuple[str, str]]`, `skipped: list[str]`, `title_status: dict[str, str]` ("verified" | "suspect" | "unverified" | "unavailable"), `agreement: dict[str, tuple[int, int]]` (matches, comparisons), `new_release_minutes: int`.
- `seed_fred_history.run_seed(conn: sqlite3.Connection, client: FredClient, now: dt.datetime, start: dt.date = dt.date(2026, 1, 1), apply: bool = False, allow_unverified: bool = False, titles: Optional[list[str]] = None, before_first_write: Optional[Callable[[], object]] = None) -> SeedReport`. Two phases: every FRED fetch and decision first, then (only when `apply`) `before_first_write()` once, then the writes. So a maintenance page or fetch error mid-run leaves the DB untouched and makes no backup.
- `seed_fred_history.backup_db(db_path: Path, now: dt.datetime) -> Path` (SQLite backup API to `<db>.pre_b8_<YYYY-MM-DD>`; refuses to overwrite an existing file, appends `_2`, `_3`).
- `seed_fred_history.main(argv: Optional[list[str]] = None) -> int`: `--db` (default `webapp/dashboard.db`), `--apply`, `--allow-unverified`, `--title` (repeatable), `--report PATH`, `--pace` (default 0.6 s, FRED's 120 requests/min). Exit 0 ok, 2 no `FRED_API_KEY`, 3 FRED under maintenance (nothing written).
- `actuals_backfill.BACKFILL_INTERVAL_SECONDS = 3600`, `BACKFILL_LOOKBACK_DAYS = 45`.
- `actuals_backfill.backfill_missing_actuals(conn: sqlite3.Connection, client: FredClient, now: dt.datetime, lookback_days: int = BACKFILL_LOOKBACK_DAYS) -> FillReport` (reuses `scripts.fill_missing_actuals.FillReport`).
- `actuals_backfill.maybe_backfill(conn: sqlite3.Connection, now: dt.datetime, client_factory: Callable[[], Optional[FredClient]] = default_client) -> Optional[FillReport]` (None when throttled or no key; never raises).

**Seed algorithm (`run_seed`):** for each title with `seed=True` (or `--title`): `releases_between(client, title, start, now.date())`; skip readings whose NY-time event is not before `now`. Event time = `dt.datetime.combine(vintage_date, release_time_et, NY_TZ)` -> UTC. Look up `find_event_history_near(conn, title, event_time, 3)`:
- a non-USD row only -> ignore it (foreign print) and treat as absent; a `country IS NULL` row -> skip, reason "ambiguous existing row" (no insert, no fill);
- a USD row -> dedup hit: record `actual_check` / `previous_check` into `agreement[title]`; if its actual is NULL, queue a fill at that row (`surprise_direction = classify_surprise(...)` from the row's own forecast);
- none -> queue an insert (`forecast=None`, `previous=reading.previous`, `actual=reading.actual`, `surprise_direction=None`, `source="fred"`, `impact=None`, `country="USD"`).

Then title status: >= 1 comparison and matches/comparisons >= 0.8 -> verified; < 0.8 -> suspect; 0 -> unverified; `FredFetchError` for the series -> unavailable. Queued writes run only when `apply` and (verified, or unverified with `allow_unverified`); a fill on a row whose `previous_check` is "mismatch" is skipped. `FredMaintenanceError` propagates (main prints "FRED under maintenance - nothing written" and exits 3). `new_release_minutes` = distinct UTC minutes of queued inserts not already present among USD rows (the weekly reaction job will price these at its next run). Output lists every insert/fill with SAST time and UTC, per-title status and agreement, and a header "DRY RUN - nothing written" unless `--apply`. `main` passes `before_first_write=lambda: backup_db(db_path, now)` and prints the backup path.

**Backfill algorithm:** rows `country = 'USD' AND actual IS NULL AND event_title IN FRED_HISTORY_SPECS` with event time in [now - lookback, now - 1 h]; `reading_for_event_date(client, title, event_date_ny)`; write with `fill_actual_if_missing(..., source="fred")` only when `previous_check == "match"`; `surprise_direction = classify_surprise(...)` (None for titles outside `EVENT_SURPRISE_DIRECTION`, e.g. JOLTS). `FredMaintenanceError` -> log `[actuals_backfill] FRED under maintenance, backfill skipped` and return the partial report; `FredFetchError` -> skip that title. `maybe_backfill` keeps a module-level `_last_run_utc` and runs at most once per `BACKFILL_INTERVAL_SECONDS`. Scheduler: call `maybe_backfill(conn, now_for_history)` after the calendar_events loop (after the FRED fast path), inside its own `try/except Exception` that logs and continues; print `[actuals_backfill] filled N` only when N > 0.

**Steps:**
- [ ] Add failing tests to `tests/test_seed_fred_history.py` (temp DB via `webapp.store.get_connection(tmp_path / "d.db")`, fake FRED from Task 1's helpers, `now = 2026-10-27T12:00Z`):
  - `test_seed_dry_run_writes_nothing`: `conn.total_changes` unchanged, row count unchanged, output contains "DRY RUN".
  - `test_seed_apply_inserts_missing_release_with_first_print` (vintage 2026-10-14 levels Jul 321.713, Aug 323.000, Sep 324.938): CPI m/m row `event_time_utc == "2026-10-14T12:30:00+00:00"`, `actual == "0.6%"`, `previous == "0.4%"`, `forecast is None`, `source == "fred"`, `country == "USD"`, `impact is None`, `surprise_direction is None`.
  - `test_seed_event_time_uses_new_york_release_time`: a 2026-01-13 CPI vintage -> `"2026-01-13T13:30:00+00:00"`; ADP vintage 2026-07-01 -> `"2026-07-01T12:15:00+00:00"`.
  - `test_seed_rerun_adds_zero_rows`: second `run_seed(apply=True)` -> `inserted == []`, `filled == []`, row count equal.
  - `test_seed_skips_release_with_row_within_3_days`: an FF USD row at 2026-10-15T12:30Z (actual NULL, forecast "0.3%", previous "0.4%") -> no insert; filled there with "0.6%", forecast kept, `surprise_direction == "higher"`.
  - `test_seed_null_country_row_is_ambiguous`: a `country NULL` CPI m/m row on the same day -> no insert, no fill, reason in `skipped`.
  - `test_seed_suspect_title_not_written`: two stored CPI m/m actuals "0.4%" where the fake vintage gives "0.9%" -> `title_status["CPI m/m"] == "suspect"`, zero CPI m/m writes, other titles still written.
  - `test_seed_unverified_title_needs_flag`: a title with no stored rows writes nothing unless `allow_unverified=True`.
  - `test_seed_aborts_on_maintenance`: `main(["--db", ..., "--apply"])` with a 200 maintenance page -> returns 3, output contains "FRED under maintenance", row count unchanged and no backup written.
  - `test_seed_missing_key_exits_without_writes`: `FRED_API_KEY` patched to "" -> returns 2.
  - `test_seed_apply_makes_backup_first`: backup file `d.db.pre_b8_2026-10-27` exists and holds the pre-seed row count.
  - `test_seeded_rows_do_not_break_stats_or_trend`: after apply, `stats_service.build_rows(conn, bt_conn)` returns the seeded CPI m/m row with `status == "not_scoreable"` and no exception; `trend.summarize_trend(get_event_history(conn, "CPI m/m"))` returns a string.
- [ ] Add failing tests to `tests/test_actuals_backfill.py`:
  - `test_backfill_fills_medium_row_when_previous_matches`: JOLTS Job Openings USD row (impact Medium, forecast "7.20M", previous "7.23M", actual NULL, 2026-10-07T14:00Z) with a JTSJOL vintage giving 7400 / prior 7230 -> `actual == "7.40M"`, `source == "fred"`, `surprise_direction is None`, forecast unchanged.
  - `test_backfill_skips_on_previous_mismatch`: FF previous "6.10M" -> nothing written, reason recorded.
  - `test_backfill_ignores_non_usd_rows`: identical rows with `country = "CAD"` and `country NULL` -> untouched, no FRED request for them.
  - `test_backfill_throttled_to_hourly`: two `maybe_backfill` calls 30 min apart -> second returns None and the fake saw no new request; a call 61 min later runs.
  - `test_backfill_maintenance_logs_and_returns`: maintenance page -> no raise, log line contains "FRED under maintenance".
- [ ] In `tests/test_webapp_scheduler.py`: `test_scheduler_cycle_survives_backfill_error` (patch `webapp.scheduler.maybe_backfill` to raise -> `run_scoring_cycle` still returns the scoring events and writes event_history).
- [ ] Run the three files -> FAIL.
- [ ] Implement as specified (scripts get the usual `sys.path.insert` header like `scripts/fill_missing_actuals.py`; `default_client()` returns None when `FRED_API_KEY` is empty).
- [ ] Run -> PASS; full suites -> PASS.
- [ ] Commit: `feat(B8): FRED/ALFRED 2026 seed (dry run first) and hourly Medium/Low actuals backfill` + Co-Authored-By line.

## Task 3 — Standardized surprise (U3)  `[judgment]`

**Files:** `config/settings.py`, `data_layer/calendar_feed.py`, `scoring/surprise_scale.py` (new), `scoring/probability_engine.py`, `webapp/scheduler.py`, `webapp/predictions_service.py`, `tests/test_surprise_scale.py` (new), `tests/test_calendar_feed.py`, `tests/test_probability_engine.py`, `tests/test_webapp_predictions_service.py`, `tests/test_webapp_scheduler.py`, `tests/test_stats_service.py`.

**Interfaces:**
- `config/settings.py` (beside `SURPRISE_SENSITIVITY`, with a B8 comment): `MIN_PRIOR_SURPRISES_FOR_SIGMA = 6`, `SURPRISE_SIGMA_MAX_HISTORY = 24`, `STANDARDIZED_SURPRISE_SENSITIVITY = 0.5`.
- `EconomicEvent` gains `surprise_sigma: Optional[float] = None` (last field, after `raw`; `_event_to_dict` unchanged so no payload changes).
- `usd_surprise_score()`: after the existing country / title / parse gates, when `self.surprise_sigma` is a positive number `raw = tanh(((actual - forecast) / self.surprise_sigma) * STANDARDIZED_SURPRISE_SENSITIVITY)`, else the existing percent method unchanged. Docstring dated B8 (2026-10-27).
- `scoring/surprise_scale.py`:
  - `prior_surprises(conn: sqlite3.Connection, title: str, before_utc: dt.datetime, limit: int = SURPRISE_SIGMA_MAX_HISTORY) -> list[float]`: `SELECT forecast, actual FROM event_history WHERE event_title = ? AND country = 'USD' AND forecast IS NOT NULL AND actual IS NOT NULL AND julianday(event_time_utc) < julianday(?) ORDER BY julianday(event_time_utc) DESC`; both parsed with `_parse_numeric`; unparseable rows skipped; the first `limit` parseable rows; returns `actual - forecast`.
  - `surprise_sigma(prior: list[float], forecast_text: Optional[str]) -> Optional[float]`: None when `len(prior) < MIN_PRIOR_SURPRISES_FOR_SIGMA`; else `max(statistics.stdev(prior), tick_of(forecast_text) or 0.0)`, None if that is not > 0.
  - `sigma_for_event(conn: sqlite3.Connection, event: EconomicEvent) -> Optional[float]`: None for `country != "USD"` or a title outside `EVENT_SURPRISE_DIRECTION`; else `surprise_sigma(prior_surprises(conn, event.title, event.event_time_utc), event.forecast)`.
  - `with_surprise_sigma(conn: sqlite3.Connection, event: EconomicEvent) -> EconomicEvent`: `dataclasses.replace(event, surprise_sigma=sigma_for_event(conn, event))`; any exception -> logged, event returned unchanged (fail open to today's method).
- Wiring: `webapp/scheduler.py::run_scoring_cycle` replaces `scoring_events` with `[with_surprise_sigma(conn, e) for e in scoring_events]` before the symbol loop; `webapp/predictions_service.py::_recompute_stale_pending(event, symbol_class, history_rows, conn: Optional[sqlite3.Connection] = None)` attaches sigma when `conn` is given, and `build_predictions_payload` passes its `conn`; `scoring/probability_engine.py::get_precursor_events_for` wraps each built precursor with `with_surprise_sigma(conn, ...)` (sigma at the precursor's own release time, local import as for `get_event_history`).

**Steps:**
- [ ] Add failing tests to `tests/test_surprise_scale.py` (temp DB; CPI m/m priors forecast "0.3%" with actuals "0.4%", "0.2%", "0.3%", "0.5%", "0.2%", "0.4%" = surprises [0.1, -0.1, 0.0, 0.2, -0.1, 0.1] at monthly times before 2026-10-14T12:30Z):
  - `test_sigma_uses_only_strictly_prior_rows`: sigma for the 2026-10-14 event == `approx(0.121106, abs=1e-6)`; adding the event's own row (actual "0.5%") and three later rows with surprises of 2.0 leaves it unchanged; a row at exactly the event time is excluded.
  - `test_fallback_below_six_prior_surprises`: with 5 priors `sigma_for_event` is None and the event's `usd_surprise_score()` == `approx(0.964028, abs=1e-6)` (today's method: tanh((0.2/0.3)*3)); with 6 priors it is `approx(0.678173, abs=1e-6)` (z = 1.651446).
  - `test_claims_become_comparable`: Unemployment Claims priors (forecast/actual) 225K/215K, 220K/215K, 202K/209K, 210K/206K, 208K/203K, 205K/206K -> sigma `approx(5887.84, abs=0.01)`; event forecast "225K" actual "219K" -> `usd_surprise_score() == approx(0.469575, abs=1e-6)` (was 0.079830).
  - `test_sigma_floor_is_one_rounding_step`: priors [0, 0, 0, 0, 0, 0.1] -> sigma == 0.1 (stdev 0.0408 floored).
  - `test_sigma_ignores_non_usd_and_null_country_rows`: GBP and NULL-country "CPI m/m" rows with surprises of 1.0 interleaved -> sigma still 0.121106.
  - `test_unparseable_and_forecast_null_rows_skipped`: a seeded-style row (forecast NULL, actual "0.6%") and a "N/A" row are not counted (5 good priors -> None).
  - `test_history_capped_at_24`: 30 priors -> only the 24 most recent are used.
  - `test_with_surprise_sigma_fails_open`: a closed connection -> event returned with `surprise_sigma is None`.
- [ ] In `tests/test_calendar_feed.py`: `test_non_usd_event_never_scored_even_with_sigma` (country "EUR", `surprise_sigma=0.12` -> None); `test_sigma_keeps_sign_and_direction_map` (higher_bearish Unemployment Rate with sigma: actual above forecast -> negative score); `test_zero_or_none_sigma_uses_percent_method`.
- [ ] In `tests/test_probability_engine.py`: `test_precursor_events_carry_prior_only_sigma` (PPI m/m precursor of CPI m/m with 6 earlier PPI rows -> `surprise_sigma` set and its contribution's `usd_sentiment` equals the z-based score; with 5 -> None and today's value).
- [ ] In `tests/test_webapp_predictions_service.py`: `test_recompute_stale_pending_uses_sigma_when_conn_given` (raw_score differs from the no-conn result and equals `usd_sign * z-score`).
- [ ] In `tests/test_webapp_scheduler.py`: `test_scoring_cycle_scores_with_sigma` (fetch_calendar patched to return an Unemployment Claims event with actual "219K", forecast "225K", the 6 claims priors in the temp DB -> persisted XAUUSD `raw_score == approx(-0.469575, abs=1e-6)`: USD +0.469575 times the "inverse" sign).
- [ ] In `tests/test_stats_service.py`: `test_stats_rows_unchanged_by_surprise_sigma` (build rows on the existing stats fixture with `EconomicEvent.usd_surprise_score` patched to raise -> identical rows: Stats never calls it, so `agreement`, `tier1_tier`, combined 70/30 values are unchanged).
- [ ] Run the touched files -> FAIL.
- [ ] Implement as specified.
- [ ] Run -> PASS; full suites -> PASS (fix any existing test that pinned a now-changed essence score only by giving it fewer than 6 priors, never by loosening an assertion).
- [ ] Commit: `feat(B8): standardized surprise from prior-only sigma with short-history fallback` + Co-Authored-By line.

## Task 4 — Re-score report (U5)  `[integration]`

**Files:** `scripts/b8_rescore_report.py` (new), `tests/test_b8_rescore_report.py` (new), `docs/superpowers/specs/2026-10-27-b8-rescore-report.md` (generated, committed).

**Interfaces:**
- `RescoreRow` (frozen dataclass): `title: str`, `event_time_utc: str`, `forecast: str`, `actual: str`, `n_prior: int`, `sigma: Optional[float]`, `z: Optional[float]`, `method: str` ("z" | "fallback"), `old_score: float`, `new_score: float`, `old_dirs: dict[str, str]`, `new_dirs: dict[str, str]`, `old_prob: dict[str, float]`, `new_prob: dict[str, float]`, `changed: bool`.
- `open_readonly(path: Path) -> sqlite3.Connection` (`file:<posix path>?mode=ro`, `uri=True`, row_factory Row).
- `rescore_rows(conn: sqlite3.Connection, symbols: tuple[str, ...] = ("XAUUSD", "US30")) -> list[RescoreRow]`: every USD row with an `EVENT_SURPRISE_DIRECTION` title and parseable forecast and actual, ascending by time; old = `score_event_for_symbol(event, classify_symbol(s))` with `surprise_sigma=None`; new = the same with `with_surprise_sigma(conn, event)`; `changed` = any symbol's direction differs.
- `render_report(rows: list[RescoreRow], generated_at: dt.datetime, db_label: str) -> str`: header (generated SAST + UTC, DB path, "read-only", constants 6 / 24 / 0.5); summary (rows, z vs fallback counts, direction changes per symbol, probability shifts >= 0.10 per symbol); "Direction changes" table (title, release SAST (UTC), forecast, actual, n prior, sigma, z, old -> new direction and probability per symbol) or the line "No direction changes."; "Largest probability shifts" (top 20); "Sigma by title" (latest n prior and sigma per title); a closing note that accumulator calls are affected only through precursor contributions and are not re-run here (they need the article bundles).
- `main(argv: Optional[list[str]] = None) -> int`: `--db` (default `webapp/dashboard.db`), `--out` (required).

**Steps:**
- [ ] Add failing tests to `tests/test_b8_rescore_report.py` (temp DB file with the 6 claims priors from Task 3 plus a claims row forecast "225K" actual "226K"):
  - `test_small_claims_miss_changes_direction`: that row has `old_dirs == {"XAUUSD": "neutral", "US30": "neutral"}` (old XAUUSD score 0.013333), `new_dirs == {"XAUUSD": "bullish", "US30": "bullish"}` (z = 0.169843, USD score -0.084718), `changed is True`, `method == "z"`.
  - `test_report_lists_direction_changes`: the rendered text has a "Direction changes" section containing "Unemployment Claims" and the SAST time; with no changes it contains "No direction changes.".
  - `test_report_opens_read_only`: `open_readonly(path).execute("INSERT INTO event_history ...")` raises `sqlite3.OperationalError`; the DB file's bytes are unchanged after `main([...])`.
  - `test_non_usd_and_unmapped_rows_excluded`: GBP rows and a JOLTS row never appear.
- [ ] Run -> FAIL; implement; run -> PASS.
- [ ] Run it read-only against the live DB: `python scripts/b8_rescore_report.py --db C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/webapp/dashboard.db --out docs/superpowers/specs/2026-10-27-b8-rescore-report.md`; confirm the live DB's modified time is unchanged; convert the output to CRLF.
- [ ] Full suites -> PASS.
- [ ] Commit: `feat(B8): read-only re-score report and pre-seed run against live` + Co-Authored-By line.

## Task 5 — Docs  `[mechanical]`

**Files:** `docs/b8-deploy.md` (new), `docs/feature-inventory-2026-09-11.md` (B8 row), `docs/roadmap-2026-10-20.md` (status line only).

**Steps:**
- [ ] Write `docs/b8-deploy.md` (CRLF, same shape as `docs/b7-deploy.md`; every command from the live app dir; `<date>` = `YYYY-MM-DD`; times SAST):
  1. **What changes:** event_history rows inserted (source 'fred', forecast NULL) and actuals filled; no schema change; scoring change: dashboard essence calls and precursor contributions use the standardized surprise from the restart time; the scheduler runs a FRED backfill at most hourly; no scheduled-task or Telegram change. The first scheduler cycle may write new `prediction_runs` rows for this week's resolved events whose score moved.
  2. **Stop** the single engine copy exactly as `docs/b11-deploy.md` section 2.
  3. **Backup** (SQLite backup API): `python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" webapp\dashboard.db webapp\dashboard.db.pre_b8_<date>`; verify `SELECT COUNT(*) FROM event_history` is equal in both (`mode=ro` one-liner given).
  4. **Merge** `b8-surprise-metric` into `news-engine/batch-predictions-queries` (no push).
  5. **Dry run:** `python scripts\seed_fred_history.py --report %TEMP%\b8_seed_dryrun.txt`. Exit 3 / "FRED under maintenance" -> stop, restart the engine on the merged code (step 8) and retry the seed later; nothing was written. Review: every High title verified (a suspect or unavailable title is listed for the owner and left out); insert/fill counts; new release minutes.
  6. **Apply:** `python scripts\seed_fred_history.py --apply --report %TEMP%\b8_seed_apply.txt` (it also makes its own `pre_b8` backup and prints the path).
  7. **Verify idempotency:** rerun `python scripts\seed_fred_history.py --apply` -> "inserted 0, filled 0"; counts before/after: `SELECT COUNT(*), SUM(actual IS NOT NULL) FROM event_history WHERE country='USD' AND event_time_utc >= '2026-01-01'` (record both numbers in the deploy note).
  8. **Start** exactly one copy as `docs/b11-deploy.md` section 3; within the first cycle the log shows either `[actuals_backfill] filled N` or nothing (no error); `/api/predictions` and `/api/stats/events` return 200.
  9. **Re-score report after seed:** `python scripts\b8_rescore_report.py --out %TEMP%\b8_rescore_after_seed.md`; tell the owner the direction-change count.
  10. **Log the scoring change:** the controller records "B8 scoring change live since <SAST time>" in the roadmap status line and the inventory row.
  11. **Rollback:** stop, `git revert` the merge, restart; seeded rows can stay (they are real first prints) or be removed with `DELETE FROM event_history WHERE source='fred' AND recorded_at_utc >= '<apply UTC ISO>'` (filled actuals are kept by first-writer-wins either way); restore `pre_b8` only if needed.
  12. **Sections "U2 root cause"** (the file:line facts from this plan), **"Revisions (U4)"** (the choice above), **"Not covered"** (GDP, ISM, UoM, CB, S&P PMIs, auctions, speeches; the web-fallback cloud routine has written 0 rows ever - owner to decide, outside B8), **"OPEN QUESTION (owner): JOLTS surprise direction"** - should a JOLTS surprise direction exist (higher openings = USD bullish?) so the existing JOLTS -> NFP 0.40 link (`config/settings.py:443`) can ever contribute? No direction is set until the owner decides; JOLTS actuals are now filled but carry no `surprise_direction`.
- [ ] Inventory B8 row -> `| B8 Surprise metric and event history | Correctness, data quality | built on b8-surprise-metric 2026-10-27, deploy pending: seed (dashboard.db, backed up first) + scoring change (standardized surprise for essence calls and precursors); Medium/Low root cause calendar_feed.py:335 (FF feed has no actuals) fixed by an hourly FRED backfill; JOLTS direction is an open owner question |` (keep column count and CRLF).
- [ ] Roadmap status line: append ` B8 built 2026-10-27 on branch b8-surprise-metric (deploy pending: FRED seed + scoring change; JOLTS direction open).`
- [ ] `git diff --stat` shows only these three docs; full suites -> PASS.
- [ ] Commit: `docs(B8): deploy runbook, inventory and roadmap status` + Co-Authored-By line.
