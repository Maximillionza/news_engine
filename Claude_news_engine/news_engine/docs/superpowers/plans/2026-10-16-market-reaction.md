# Market Reaction Sub-tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fourth Stats sub-tab, "Market reaction", that measures how XAUUSD / US30 moved in the 5 minutes after each USD release, ranks event types by how consistently they move the market, and adds a shared multi-select impact filter (High + Unrated by default) to all four Stats sub-tabs.

**Architecture:** A compute script reads Dukascopy 1-minute bars and writes append-only `release_reactions` and `reaction_baselines` tables in `backtest_log.db`; a read-only service joins those with `event_history` and the Stats rows and applies the cluster-credit rules from pure functions; routes and a new JS module render the leaderboard and drill-down. Nothing fetches prices at request time.

**Tech Stack:** Python 3 / Flask / SQLite, pandas + `dukascopy_python` (already used), pytest; vanilla ES modules + `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-16-market-reaction-design.md` (commit eb9ecf1). Read it first; it also builds on `docs/superpowers/specs/2026-10-15-stats-tab-design.md`.

## Global Constraints

- Window is **5 minutes only**: `p0` = open of the 1-minute bar starting at the release minute `t`; `p5` = open of the bar starting at `t + 5 min`. A missing bar at either end is **no data**, never interpolated. (R1, §4)
- **Reaction** = `|move| > typical × REACTION_MIN_MULTIPLE` (constant, default `1.0`); equal to typical is **no reaction**. `typical` = median `|5-minute move|` over 5-minute windows in the same UTC hour on other weekdays, excluding windows whose start minute is a USD release minute. One baseline per UTC hour; **no daylight-saving split**. (R2, R13)
- A **cluster** = all USD releases in `event_history` with the same `event_time_utc` minute, **regardless of the impact filter**. Credit labels: solo hit/miss, shared hit/miss, matched the move, overruled, no reaction, no signal, no data. An event with lean `mixed` is **no signal** and never takes credit. Shared credit is never added to solo counts. (R4, R7, §4.1)
- Implied lean reuses `stats_rules.side` + `stats_methods.market_lean`; engine calls reuse the Stats rows (`combined`, else `tier1`, else `news`). (R3)
- **No percentage under 20 releases** (counts always shown); event types under 8 releases carry a "few releases" tag. (R11)
- **No overlap handling** is built; Phase 0 only counts and reports windows containing another release minute (expected zero). (R12)
- Impact chips: High, Medium, Low, Unrated (inferred); default selection **High + Unrated**; one control shared by all four sub-tabs and sent as `impacts=High,Unrated`. Effective impact = own tag, else most common tag of the same title (tie -> higher impact), else Unrated; a row whose tag is inferred or missing is bucketed as **Unrated**. (R8-R10, §5)
- Stats is **USD events only** (`country = 'USD'`), read-only against `dashboard.db`; Market reaction writes only its two new tables. `predicted_direction` and live scoring tables are never touched. Dates shown in SAST (UTC+2); filters stay UTC-based.
- All timestamps are tz-aware UTC and normalised like `backtest_store._utc_iso`; naive datetimes raise `ValueError`.
- The compute script refuses the live backtest DB unless `--bt-db` is given or `STATS_BACKFILL_LIVE=1`, and has `--dry-run`. No network in tests.
- Existing CRLF files keep CRLF (small diffs); new files may be LF. Commit messages end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Disclaimers (exact): "Reaction is measured over 5 minutes against a typical move for that hour; it shows association, not proof that the release caused the move." and "Credit in a cluster is shared or matched, never exclusive."

## Review Focus

1. A release minute with missing bars -> "no data": no crash, not counted in any rate. (Tasks 1, 3)
2. Move exactly equal to the typical move -> no reaction; zero or missing baseline for an hour -> no data. (Task 1)
3. Cluster whose events all have lean `mixed` -> no signal for all, no credit; cluster with one leaned event + several no-signal events -> that event is solo. (Task 1)
4. Impact filter hides an event but its cluster still includes it for credit, and the drill-down notes "+N lower-impact events at the same time". (Task 4)
5. Event type with 19 releases: counts shown, percentage hidden; with 20: percentage shown. (Task 4)
6. Re-running the compute script adds nothing; a bar fetch failure writes no row; a release newer than 10 minutes is skipped. (Task 3)

---

### Task 0: Worktree and Phase 0 feasibility

**Files:**
- Create: `scripts/market_reaction_phase0.py`, `docs/superpowers/specs/2026-10-16-market-reaction-phase0-report.md`

**Interfaces:** Produces a report only; no later code depends on it.

- [ ] **Step 1: Create the worktree.** From `.worktrees/news-engine-live`: `git worktree add ../market-reaction -b market-reaction`; work from `../market-reaction/Claude_news_engine/news_engine`. Never use the shared checkout; never write to any live DB.
- [ ] **Step 2: Implement `scripts/market_reaction_phase0.py`** (read-only; dashboard DB opened `mode=ro`; bars from Dukascopy). It prints: (a) distinct USD release minutes since 2026-01-01 and, per tracked symbol (XAUUSD, US30), how many have both the `t` and `t+5` bars; list every gap; (b) number of 5-minute windows (start `t`, covering `[t, t+5)`) that contain another USD release minute (spec expects zero; list any); (c) clusters by size (1, 2, 3+), and for each cluster the count of events with a non-`mixed` implied lean using `market_lean`; (d) sanity: median `|5-min move|` for XAUUSD at 12:00-12:59 UTC on non-release 5-minute windows, compared with the same figure computed from the Shock-alert audit approach (`scripts/audit_shock_impact.py` baseline logic) over a shared window of at least 20 weekdays.
- [ ] **Step 3: Run it and write the report** (`docs/superpowers/specs/2026-10-16-market-reaction-phase0-report.md`): coverage numbers, gap list, overlap count, cluster-size table, baseline sanity result, and a plain statement of whether full history from January is achievable. State any shortfall explicitly.
- [ ] **Step 4: Commit** the script and report; **stop and show the report to the owner before Task 3 runs any backfill.**

### Task 1: Pure reaction rules

**Files:**
- Create: `webapp/reaction_rules.py`; Test: `tests/test_reaction_rules.py`

**Interfaces (Produces):**
- Constants `REACTION_MIN_MULTIPLE = 1.0`, `MIN_PERCENT_RELEASES = 20`, `FEW_RELEASES_TAG = 8`.
- `classify_reaction(move: Optional[float], typical: Optional[float], multiple: float = REACTION_MIN_MULTIPLE) -> Optional[str]` -> `"buy"` / `"sell"` / `"none"` / `None` (None when either input is None or `typical <= 0`).
- `single_outcome(lean: str, reaction: Optional[str]) -> str` -> `"hit"` / `"miss"` / `"no_reaction"` / `"no_signal"` / `"no_data"`.
- `cluster_credit(leans: dict[str, str], reaction: Optional[str]) -> dict[str, str]` — keys are event ids, values are leans `"buy"|"sell"|"mixed"`; returns a credit label per event: `solo_hit`, `solo_miss`, `shared_hit`, `shared_miss`, `matched`, `overruled`, `no_reaction`, `no_signal`, `no_data`.
- `wilson_interval(k: int, n: int, z: float = 1.96) -> Optional[tuple[float, float]]` (None for `n == 0`).
- `rate_display(k: int, n: int) -> dict` -> `{"k", "n", "percent": float|None, "interval": [lo, hi]|None, "few": bool}`; `percent` is None when `n < MIN_PERCENT_RELEASES`; `few` is `n < FEW_RELEASES_TAG`.
- `impact_info(own_tag: Optional[str], title_tags: dict[str, int]) -> dict` -> `{"bucket", "effective", "inferred"}`: `bucket` is the own tag if present else `"Unrated"`; `effective` is own tag, else the most common tag among `title_tags` (ties -> High > Medium > Low), else `"Unrated"`; `inferred` is True when own tag is missing.

- [ ] **Step 1: Write failing tests** pinning: equal-to-typical -> `"none"`; `None`/zero baseline -> `None`; positive move above typical -> `"buy"`, negative -> `"sell"`; `single_outcome` hit/miss/no_reaction/no_signal/no_data; `cluster_credit` for: one leaned event among no-signal ones -> `solo_hit` / `solo_miss`; two agreeing leaned events with a matching reaction -> both `shared_hit`, opposite -> both `shared_miss`; a conflict (`buy` + `sell`) with reaction `buy` -> the buy event `matched`, the sell event `overruled`; conflict with `"none"` -> all `no_reaction`; all-`mixed` -> all `no_signal`; reaction `None` -> leaned events `no_data`; `rate_display` at 19 vs 20 (percent hidden/shown), `few` at 7 vs 8, Wilson interval known value (k=7, n=10 -> approx (0.397, 0.892)); `impact_info`: own High -> ("High","High",False); missing with title tags {High: 5, Medium: 5} -> bucket "Unrated", effective "High", inferred True; missing with no tags -> effective "Unrated".
- [ ] **Step 2: Run to see failure** (`python -m pytest tests/test_reaction_rules.py -q`).
- [ ] **Step 3: Implement the module** with the signatures above (pure, no I/O, no imports from the webapp beyond constants).
- [ ] **Step 4: Run to verify pass; Step 5: commit** (`feat(reaction): pure reaction, credit and impact rules`).

### Task 2: Storage tables and store functions

**Files:**
- Modify: `scoring/backtest_store.py` (add to `_SCHEMA`; functions next to the nowcast snapshot ones; CRLF file)
- Test: `tests/test_backtest_store_reactions.py`

**Interfaces (Produces):**
- Table `release_reactions(id, event_time_utc TEXT, instrument TEXT, status TEXT CHECK in ('ok','no_data'), p0 REAL, p5 REAL, move REAL, move_pct REAL, typical_abs_move REAL, reaction TEXT CHECK in ('buy','sell','none') NULL, bar_source TEXT, computed_at_utc TEXT, UNIQUE(event_time_utc, instrument))` and `reaction_baselines(id, instrument, utc_hour INTEGER, median_abs_move REAL, n_windows INTEGER, period_start_utc TEXT, period_end_utc TEXT, computed_at_utc TEXT, UNIQUE(instrument, utc_hour, period_end_utc))`.
- `record_release_reaction(conn, event_time_utc: dt.datetime, instrument: str, status: str, p0=None, p5=None, typical_abs_move=None, reaction=None, bar_source="dukascopy_1m") -> int` — append-only `INSERT OR IGNORE`; `move`/`move_pct` derived from `p0`/`p5` when status is ok; UTC-normalised via `_utc_iso`.
- `get_release_reactions(conn, instrument: str) -> dict[str, sqlite3.Row]` keyed by the UTC-normalised ISO `event_time_utc`.
- `record_reaction_baseline(conn, instrument, utc_hour, median_abs_move, n_windows, period_start_utc, period_end_utc) -> int` (append-only) and `get_latest_reaction_baselines(conn, instrument) -> dict[int, float]` (latest `period_end_utc` per hour).

- [ ] **Step 1: Write failing tests:** record then get returns the row with derived `move`/`move_pct`; duplicate `(time, instrument)` is ignored not overwritten; an offset-form time is normalised and found under the UTC key; naive datetime raises `ValueError`; invalid status/reaction rejected; `no_data` rows store NULL prices; baselines: two period_ends -> latest wins per hour; existing store tests still pass.
- [ ] **Step 2: See them fail; Step 3: implement** (preserve CRLF; `executescript(_SCHEMA)` creates the tables on existing DBs; **additive only**); **Step 4: run `python -m pytest tests/test_backtest_store.py tests/test_backtest_store_snapshots.py tests/test_backtest_store_reactions.py -q`; Step 5: commit.**

### Task 3: Compute script (reactions and baselines)

**Files:**
- Create: `scripts/compute_release_reactions.py`; Test: `tests/test_compute_release_reactions.py`

**Interfaces:**
- Consumes: Task 1 `classify_reaction`; Task 2 store functions; `data_layer.dukascopy_feed._resolve_dukascopy_instrument`; `webapp.store.list_tracked_symbols`.
- Produces: `price_at_minute(bars: pd.Series, when: dt.datetime) -> Optional[float]` (exact minute bar open or None); `compute_baselines(bars: pd.Series, release_minutes: set[dt.datetime]) -> dict[int, tuple[float, int]]` (UTC hour -> (median `|5-min move|`, window count)); `reaction_for(bars, release: dt.datetime, typical: Optional[float]) -> dict` (status/p0/p5/reaction); `run(dash_conn, bt_conn, fetch_bars: Callable[[str, dt.datetime, dt.datetime], pd.Series], mode: str, now: dt.datetime, symbols: list[str], since: dt.datetime) -> dict` returning `{"written": n, "no_data": n, "skipped_recent": n, "baselines": n}`; `main()` CLI with `--backfill`, `--incremental`, `--dry-run`, `--bt-db`, `--dash-db`, `--since`.

- [ ] **Step 1: Write failing tests** (synthetic bar series, fake `fetch_bars`, in-memory DBs): baseline excludes windows starting on release minutes and uses 5-minute boundaries within each UTC hour on other weekdays, and ignores weekends; `reaction_for` buy/sell/none/no-data (missing end bar); `run --backfill` writes one row per (release minute, symbol), a missing bar writes a `no_data` row, re-running adds nothing; a release younger than 10 minutes is skipped; a fetch exception writes no row for that symbol and others still run; `--dry-run` writes nothing; the CLI refuses the default live backtest DB without `--bt-db`/`STATS_BACKFILL_LIVE=1` and never opens the backtest DB when refusing; `dashboard.db` is opened `mode=ro`.
- [ ] **Step 2: See them fail; Step 3: implement.** Bars come from `dukascopy_python.fetch(..., INTERVAL_MIN_1, OFFER_SIDE_BID, ...)` in monthly chunks, `open` column indexed by UTC timestamp; the default `fetch_bars` is the only code touching the network. Baseline period = first to last release minute fetched; one `reaction_baselines` row per hour. A reaction's `typical` is the baseline for the release's UTC hour (no baseline -> no_data).
- [ ] **Step 4: Run tests; Step 5: commit.** Real-data validation (do it, report numbers): run `--backfill --dry-run` then a real run against **temp copies** of both DBs for 2026-01-01..now, and report rows written, `no_data` count, and reaction counts per symbol. **Never run against the live backtest DB** — the live run happens in Task 7 after owner approval.

### Task 4: Reaction service and impact fields on Stats rows

**Files:**
- Create: `webapp/reaction_service.py`; Test: `tests/test_reaction_service.py`
- Modify: `webapp/stats_service.py` (add impact fields and an `impacts` filter to `build_rows`, `build_chart`, `build_scoreboard` inputs), `tests/test_stats_service.py`

**Interfaces:**
- Consumes: Task 1 rules; Task 2 `get_release_reactions`; `stats_service.build_rows` / `StatsRow`; `stats_methods.market_lean`; `stats_rules.parse_number/tolerance/side`.
- Produces:
  - `StatsRow` gains `impact: Optional[str]`, `impact_effective: str`, `impact_inferred: bool`, `impact_bucket: str`; `build_rows(..., impacts: Optional[frozenset[str]] = None)` keeps only rows whose `impact_bucket` is in `impacts` (None = no filtering).
  - `build_leaderboard(dash_conn, bt_conn, instrument: str, impacts: Optional[frozenset[str]], year: Optional[int], month: Optional[int]) -> dict` -> `{"instrument", "rows": [{"event_title","impact_effective","impact_inferred","releases","solo","shared","in_conflict","reaction": rate_display,"hit": rate_display,"avg_move_pct","engine": {"k","n"}|None,"few"}], "disclaimers": {...}}`.
  - `build_event_releases(dash_conn, bt_conn, instrument, event_title, impacts, year, month) -> dict` -> `{"event_title","releases": [{"event_time_utc","move_pct","typical_abs_move","reaction","lean","credit","cluster_size","hidden_in_cluster","cluster": [{"event_title","lean","credit"}],"engine_call": {"method","verdict"}|None}]}` (newest first).

- [ ] **Step 1: Write failing tests** (in-memory DBs): impact inheritance (CPI untagged inherits High -> bucket Unrated, effective High, inferred); `impacts` filter on `build_rows`; leaderboard counts for a seeded solo, a shared (two agreeing) and a conflict cluster with known reactions; a hidden (filtered-out) event still takes part in its cluster's credit and increments `hidden_in_cluster` for the visible one; 19 vs 20 releases percent hidden/shown; events with `mixed` lean excluded from `releases`; `no_data` minutes excluded from rates; engine column uses combined, else tier1, else news and is `None` when no calls; year/month filters; instrument without data -> empty rows, no crash.
- [ ] **Step 2: See them fail; Step 3: implement** (SELECT-only; per-row fail-open; USD rows only). Cluster key = exact `event_time_utc`. `avg_move_pct` is the mean of `move_pct` signed in the implied direction (buy +, sell -) over releases with a reaction.
- [ ] **Step 4: Run `python -m pytest tests/test_reaction_service.py tests/test_stats_service.py -q`; Step 5: commit.**

### Task 5: Routes

**Files:**
- Modify: `webapp/app.py` (CRLF file; reuse `_stats_conns()` and `_int_arg`); Test: `tests/test_app_reaction_routes.py`, update `tests/test_app_stats_routes.py`

**Interfaces (Produces):**
- `GET /api/stats/reaction/leaderboard?instrument=&impacts=&year=&month=` and `GET /api/stats/reaction/releases?instrument=&event=&impacts=&year=&month=` returning the Task 4 dicts via explicit serializers (400 when `event`/`instrument` missing/unknown; `instrument` must be a tracked symbol).
- `impacts` (comma list from High/Medium/Low/Unrated; unknown values ignored; empty -> no filtering) accepted by the existing `/api/stats/events`, `/chart`, `/scoreboard`; `/api/stats/events` rows gain `impact`, `impact_effective`, `impact_inferred`.

- [ ] **Step 1: Write failing route tests** asserting every served field exactly (set equality, as the Stats route tests do), the filters, the 400s, and that connections are closed. **Step 2: fail; Step 3: implement; Step 4: run `python -m pytest tests/test_app_reaction_routes.py tests/test_app_stats_routes.py tests/test_webapp_app.py -q`; Step 5: commit.**

### Task 6: Frontend

**Files:**
- Create: `webapp/static/js/stats/impact-filter.js`, `webapp/static/js/stats/reaction.js`, `webapp/static/js/stats/impact-filter.test.js`, `webapp/static/js/stats/reaction.test.js`
- Modify: `webapp/static/js/stats/stats.js`, `webapp/static/js/api.js`, `webapp/static/index.html`, `webapp/static/style.css` (CRLF files; small diffs)

**Interfaces:**
- Produces (pure): `DEFAULT_IMPACTS = ["High","Unrated"]`; `impactsParam(selected: string[]) -> string`; `chipsHtml(selected: string[]) -> string` (four chips labelled High, Medium, Low, "Unrated (inferred)", selected ones marked `aria-pressed="true"`); `toggleImpact(selected, name) -> string[]`; in `reaction.js`: `leaderboardRowsHtml(rows) -> string`, `releasesHtml(data) -> string`, `CREDIT_LABELS` (solo_hit "Solo hit", solo_miss "Solo miss", shared_hit/shared_miss "Shared driver"/"Shared miss", matched "Matched the move", overruled "Overruled", no_reaction "No reaction", no_signal "No signal", no_data "No data"), `clusterNoteHtml(release) -> string` ("+N lower-impact events at the same time" when `hidden_in_cluster > 0`). All dynamic text escaped (`escapeHtml` from `../format.js`).
- Behaviour: a fourth sub-tab "Market reaction" with Instrument select (tracked symbols, XAUUSD default), a fixed "Window: 5 min after release" label, Year/Month selects, the shared impact chips, the leaderboard (percent shown only when the service gives one; "few releases" tag; "k of n" always), the Wilson 95% interval as a hover tooltip (`title`) on each rate, a row click loading the drill-down, both exact disclaimers, an empty-state message, and the same impact selection applied (re-fetch) on Combined, Tier 1 and News sentiment. SAST dates via the existing `toSast` helper.

- [ ] **Step 1: Write failing node tests:** default chips = High + Unrated pressed; toggling; param string; unselecting all -> empty selection message instead of an unfiltered view; leaderboard row shows `7 of 9` with no percent when `percent` is null and the percent when present; `few` tag; each credit label; hidden-in-cluster note; XSS escaping of titles; empty state.
- [ ] **Step 2: See them fail; Step 3: implement; Step 4: `node --test webapp/static/js/stats/*.test.js` passes.**
- [ ] **Step 5: Verify in the browser** against read-only copies of the live DBs on a port other than 5001 (never stop the live dashboard): the four sub-tabs, chips default and toggling on every sub-tab, the leaderboard, a drill-down with a cluster, 375px width with no horizontal scroll, no console errors. **Step 6: commit.**

### Task 7: Docs, full verification, live backfill and scheduler hook (owner-gated parts)

- [ ] **Step 1: Docs:** add the Market reaction row to `docs/feature-inventory-2026-09-11.md` (CRLF, one line) stating exactly what is built, the sample sizes, that credit in clusters is shared, the 5-minute definition and floor of 20, what is not built, and the Phase 0 results; update the spec status line.
- [ ] **Step 2: Full suites:** `python -m pytest tests -q --deselect tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present` and `node --test "webapp/static/js/**/*.test.js"` (only the four known jsdom failures allowed: calendar/render, dashboard/card, dashboard-poll, symbol-picker).
- [ ] **Step 3 (needs the owner's approval, do not run unasked):** back up the live `backtest_log.db`, then `python scripts/compute_release_reactions.py --backfill --bt-db <live path> --dash-db <live path>`; verify counts against the Task 3 temp-copy numbers; restart the dashboard and check the tab.
- [ ] **Step 4 (needs the owner's approval):** hook `--incremental` into the existing outcome-confirm scheduled run, or create a small daily scheduled task; first run `--dry-run`.
- [ ] **Step 5: Final whole-branch review, then ask the owner how to integrate** (merge / PR / keep).
