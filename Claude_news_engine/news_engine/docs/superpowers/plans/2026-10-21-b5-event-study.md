# B5 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A once-off, read-only fact-finding study that answers the owner's co-release questions (does price spike then pull back when same-minute releases conflict; does it move harder when they all agree), tests the event -> USD -> instrument chain, re-runs the Tier 1 CPI dipstick, and ends in a decision memo (mover/anchor go or no-go, the B10 grading window and threshold, whether "$5-10 peak within seconds, max $15-20" holds). No live writes, no scheduled job, no UI.

**Architecture:** Three pure modules hold every calculation and are unit-tested on fixtures: `scripts/event_study_metrics.py` (per-window price measures from OHLC bars), `scripts/event_study_groups.py` (release members, same-minute clusters, implied directions, group summaries) and `scripts/event_study_checks.py` (E2 chain statistics, E3 dipstick). `scripts/event_study_once.py` is the only I/O: it opens the live `dashboard.db` and `backtest_log.db` with sqlite `mode=ro`, fetches Dukascopy 1-second BID bars per release window through an on-disk cache in `%LOCALAPPDATA%\Temp\news_engine_event_study\`, and writes CSV/JSON/Markdown outputs there. The run task executes it against live data and writes the owner report with real numbers.

**Tech Stack:** Python 3, sqlite3 (URI `mode=ro`), pandas, `dukascopy_python` 4.0.1, pytest.

**Spec:** `docs/roadmap-2026-10-20.md` §B5 (E1-E4), plus these owner decisions:
- E1: every USD release minute since 2026-01-01 in `event_history`, same-title rows within 3 minutes collapsed (as `scripts/compute_release_reactions.py release_minute_sets`), for XAUUSD and US30; Dukascopy `INTERVAL_SEC_1` BID for [t-2 min, t+31 min], 1-minute OHLC fallback, the source recorded. p0 = first bar open at/after t; for k = 1, 5, 30 min: peak up = max(high in [t, t+k)) - p0, peak down = p0 - min(low in [t, t+k)), time to peak (s); net at 5 and 30 min; first-minute direction = sign of the larger first-minute excursion. Units: $, owner pips ($1 = 100 pips, 4080 -> 4090 = 1000 pips), US30 points, and multiples of the hourly baseline (`reaction_baselines`, quantile 0.75, |5-min move|). Implied direction per member: actual vs forecast (Stats tolerance rule) through `EVENT_SURPRISE_DIRECTION` -> USD, and `stats_methods.market_lean` -> instrument.
- Questions, with n for every group: (a) conflicting clusters: spike then pull back (first-minute direction opposite to the 5/30-min net, or retrace > 50% of the first-minute peak)? which member did the first move follow vs the 30-min net? (b) all hot / all cool: bigger move (peak and net, baseline multiples) than singles and conflicts? Plus the 1-minute peak and time-to-peak distribution, High-impact vs others, against "$5-10 typical, $15-20 max". Known sample: ~207 release minutes, 47 with 2+ events, 23 fully computable (17 agree, 4 conflict, 2 all in line): results are descriptive and small-sample, and the report says so.
- E2: DXY in the same windows: (i) implied USD direction vs DXY 5-min sign (non-trivial moves only); (ii) sign agreement and slope of XAUUSD / US30 5-min move on DXY 5-min move, against the engine's assumptions (gold inverse; US30 `risk_sentiment` treated as inverse with `RISK_SENTIMENT_DAMPENING = 0.7`).
- E3: Cleveland nowcast history, every 2026 CPI m/m and Core CPI m/m release: T-25d value vs final pre-release value vs actual; final closer / earlier closer / tie; call side changes (Stats tolerance rule); confirm or refute "T-5d equals final in 17/17".
- E4: decision memo in the report.
- Data access: live DBs strictly read-only (`mode=ro`); outputs and bar cache only under `C:\Users\Masoodt\AppData\Local\Temp\news_engine_event_study\`; Dukascopy pause 1-2 s between requests; unit tests use fixtures only.

Audit evidence: E-01, E-02, E-03, T1-10 (`explore_B.json`).

App dir for every command: `.worktrees/b5-event-study/Claude_news_engine/news_engine`. Full suite = `python -m pytest -q -p no:warnings` (baseline 1675 passed, 1 env-only failure) + `npm test`. Known env-only failure (no `.env` in a worktree): `tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present`; ignore it, everything else must pass.

## Global Constraints

- **Live system off-limits:** no change to `.worktrees/news-engine-live`; its two DBs are opened only through `event_study_once.open_readonly` (`mode=ro`). No Windows or Claude scheduled task, no Telegram, no push.
- **Nothing outside the repo needs deploying:** the study is run by hand once; no task registration, no SKILL.md change.
- **Outputs outside the repo:** every file the script writes (bar cache, CSV, JSON, Markdown) goes under `--out-dir` (default `C:\Users\Masoodt\AppData\Local\Temp\news_engine_event_study`); an out-dir inside the repo is refused before anything is opened.
- **Tests:** fixtures and temp DBs only; the Dukascopy fetch and `time.sleep` are injected; no test touches the network or a live path.
- **Times:** computed in UTC (baseline hour = UTC hour of t); every owner-facing time (CSV `t_sast` column, report) in SAST via `config.settings.LOCAL_TZ`, `%Y-%m-%d %H:%M SAST`.
- **Never interpolate:** a missing bar is missing; 1-second bars are sparse (a second with no tick has no bar; probe 2026-10-14 12:28Z: DXY 972 bars in 33 min), so prices are looked up as first-at/after or last-before with a gap limit, never by exact second.
- **Style:** type hints on every signature, surrounding comment density, `from __future__ import annotations`, `sys.path.insert(0, parents[1])` like the other scripts; row dicts have exact key-set tests.
- **Line endings:** new and touched files CRLF (all neighbours are CRLF). Write any script containing backslashes with the Write tool; check regexes for a 0x08 byte if `\b` is used.
- **Commits:** one per task on `b5-event-study`; message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Peak, net or time-to-peak computed on the wrong bars.** Including the pre-release bars or the bar after t+30 min, using the open instead of high/low, an exact-second lookup on sparse 1-second data, or a net price taken from a stale bar.
   - Pinned by `test_measure_window_reference_fixture`, `test_bars_after_horizon_and_before_t_are_ignored`, `test_p0_more_than_60s_after_t_is_no_data`, `test_net_needs_a_bar_within_120s` (Task 1).
2. **Unit mistakes in the owner's terms.** $1 must be 100 pips (4080 -> 4090 = 1000 pips); US30 in points; baseline multiples divide by the UTC-hour baseline, never the SAST hour.
   - Pinned by `test_owner_units_gold_pips_and_us30_points`, `test_baseline_uses_utc_hour` (Tasks 1, 4).
3. **Cluster classes that do not reproduce the known sample.** Duplicate rows counted twice, a duplicate's actual lost, in-line members mis-classed, unmapped titles silently treated as in line.
   - Pinned by `test_duplicate_within_3_minutes_collapses_and_keeps_actual`, `test_cluster_classes`, `test_unmapped_title_is_partial_not_in_line` (Task 2), and the dry-run sample check in Task 5.
4. **Contaminated windows inflating "bigger move" answers.** Another release inside [t, t+k) must drop that row from horizon-k statistics.
   - Pinned by `test_rows_with_next_release_inside_horizon_are_excluded` (Task 2).
5. **Writing to live data or the repo.** A read-write connection to a live DB, a cache or output file inside the repo.
   - Pinned by `test_open_readonly_refuses_writes`, `test_out_dir_inside_repo_refused`, `test_run_study_writes_only_under_out_dir` (Task 4).
6. **Re-runs that hammer Dukascopy or cache a not-yet-complete window.** Cache hits must skip both the fetch and the pause; a failed fetch is not cached.
   - Pinned by `test_cache_hit_skips_network_and_pause`, `test_recent_window_not_cached`, `test_fetch_error_not_cached_and_counted` (Task 4).
7. **Dipstick off by a day.** "As of" values are end-of-day stamps (D 23:59:59 UTC); the T-25d value is the latest as-of at or before release - 25 days, the final the latest strictly before the release.
   - Pinned by `test_dipstick_row_reference_fixture` (Task 3).

## Plan decisions (beyond the spec text)

- **Duplicate rows:** a collapsed duplicate run keeps its earliest row (as `collapse_same_title_duplicates`); if that row lacks a readable forecast or actual, the first row of the same run that has both supplies them, so a direction is not lost to a calendar re-stamp.
- **Cluster classes** follow `market_reaction_phase0.classify_cluster` semantics on USD direction: in-line members do not vote. Size 1: `single_directional` / `single_in_line` / `single_unknown`. Size 2+: `partial` (any member not computable), `all_in_line`, `conflict` (both +1 and -1 present), `agree`. `all_same` marks an agree cluster where every member is hot (or every member cool), which is the owner's literal "all hot / all cool"; the report shows agree and the `all_same` subset. If the dry run does not reproduce 17 / 4 / 2, the report gives both counts and the reason.
- **Impact group per minute:** the highest member impact (High > Medium > Low > Unknown) from `event_history.impact`, falling back to `config.settings.EVENT_REGISTRY[title]["impact"]` when the row has none (66 rows are NULL). "High" vs "others".
- **Net price** = close of the last bar starting before t+k, at most 120 s before t+k. This differs from `release_reactions` (open at t+5 minus open at t, 1-minute bars); the report's method section says so.
- **Retrace** at k = 5 and 30: `1 - first_min_dir * net_k / first_min_peak`; "spike then pull back" at k = net_k sign opposite to the first-minute direction, or retrace > 0.5. Measured in conflicting clusters and, as the control the question needs, in agree clusters and single releases.
- **Contamination rule:** a row enters horizon-k statistics only when the next release minute is at least k minutes after t.
- **Mover candidates for (a):** for each conflicting cluster the report lists which members the first move and the 30-min net followed, and checks two simple rules a later feature could use: "largest surprise in rounding steps wins" and "higher impact wins".
- **E2 "non-trivial":** |DXY 5-min move| / DXY p0 above 0, 2 and 5 basis points (three rows, 2 bp is the headline); instrument rows with a zero move are excluded. The slope is reported in % per % (elasticity) so gold and US30 are comparable; the engine's 0.7 is a confidence weight, not a magnitude, so the closest comparison is US30's sign-agreement rate vs gold's, shown side by side.
- **E3 input:** the cached `nowcasts.csv` is used read-only when present; when missing, the script does not download anything: E3 is reported as "missing" with the exact regeneration commands (fetch `nowcast_month.json` by hand, then `scripts/cleveland_nowcast_to_csv.py ... --dash-db <live dashboard.db>` into the temp folder). Lags reported: 5, 15, 20, 25 days (25 is the headline "mid reference month"); `tier1_nowcast_snapshots` is used only as a cross-check of the final value.
- **E4 rules fixed before the data is seen** (Task 5 applies them as written and states any judgment beyond them):
  - Mover/anchor **GO** only if, per symbol, at least 10 conflicting clusters have full data AND one mover rule predicts the 30-min net in at least 70% of them AND the spike-then-pull-back rate in conflicts beats agree clusters by at least 20 points. Fewer than 10 conflicts = **not decidable yet** (re-run when n reaches 10); otherwise NO-GO.
  - **B10 window:** the smallest k in {1, 5, 30} min where the median High-impact XAUUSD peak_k is at least 60% of the median peak_30. **Threshold:** the median |net_k| in baseline multiples of non-High releases at that window, never below the current `REACTION_MIN_MULTIPLE` (1.0).
  - **Owner's claim** holds if, for High-impact XAUUSD minutes, the median 1-minute peak is within $5-10, the 90th percentile is at most $20 and the median time to peak is at most 30 s; "partly" if two of three; otherwise it does not hold.

---

### Task 1: Window metrics from OHLC bars — *judgment*

**Files:**
- Create: `scripts/event_study_metrics.py`, `tests/test_event_study_metrics.py`

**Interfaces:**
- Constants: `HORIZONS_MIN: tuple[int, ...] = (1, 5, 30)`, `NET_HORIZONS_MIN: tuple[int, ...] = (5, 30)`, `P0_MAX_LAG = dt.timedelta(seconds=60)`, `NET_MAX_GAP = dt.timedelta(seconds=120)`, `PIPS_PER_DOLLAR_XAU = 100`, `RETRACE_LIMIT = 0.5`.
- `@dataclass(frozen=True) class Bar: ts: dt.datetime; open: float; high: float; low: float; close: float` (ts = aware UTC bar start).
- `def bars_from_frame(df: pd.DataFrame) -> list[Bar]` — Dukascopy frame (UTC `DatetimeIndex`, columns open/high/low/close) to bars sorted by ts; rows with a non-finite value dropped; naive index raises `ValueError`; empty frame -> `[]`.
- `def first_open_at_or_after(bars: list[Bar], t: dt.datetime, max_lag: dt.timedelta = P0_MAX_LAG) -> Optional[tuple[float, int]]` — (open, lag seconds) of the first bar with `ts >= t`, None if none within `max_lag`.
- `def close_before(bars: list[Bar], when: dt.datetime, max_gap: dt.timedelta = NET_MAX_GAP) -> Optional[float]` — close of the last bar with `ts < when`, None if that bar starts before `when - max_gap`.
- `def excursion(bars: list[Bar], t: dt.datetime, p0: float, k_min: int) -> tuple[float, float, Optional[int], int]` — (up, down, time-to-peak s, peak side) over bars with `t <= ts < t + k`; side +1 when up > down, -1 when down > up, 0 on a tie; time to peak = seconds from t to the start of the first bar reaching the larger extreme (None on a tie of zeros).
- `METRIC_KEYS: tuple[str, ...]` = `status, bar_source, resolution_s, p0, p0_lag_s, up_1, down_1, peak_1, ttp_1_s, side_1, up_5, down_5, peak_5, ttp_5_s, side_5, up_30, down_30, peak_30, ttp_30_s, side_30, net_5, net_30, first_min_dir, first_min_peak, retrace_5, retrace_30, spike_pullback_5, spike_pullback_30`.
- `def measure_window(bars: list[Bar], t: dt.datetime, bar_source: str, resolution_s: int) -> dict[str, Any]` — keys exactly `METRIC_KEYS`; `status` "ok" or "no_data" (no p0); with no_data every measure is None. `first_min_dir` = `side_1`, `first_min_peak` = `peak_1`; retrace/spike per "Plan decisions" (None when `first_min_dir == 0`, `first_min_peak == 0` or net is None).
- `def choose_bars(sec_bars: list[Bar], min_bars: list[Bar], t: dt.datetime) -> tuple[str, int, list[Bar]]` — ("sec1", 1, sec) when sec has p0 and `close_before(t + 30 min)`; else ("min1", 60, min) under the same test; else whichever has p0 (sec first); else ("none", 0, []).
- `def owner_units(symbol: str, delta: float) -> tuple[float, str]` — XAUUSD `(delta * 100, "pips")`, US30 `(delta, "points")`, DXY `(delta, "index points")`; other symbols `ValueError`.
- `def baseline_multiple(value: Optional[float], baseline: Optional[float]) -> Optional[float]` — None when either is None or baseline <= 0.

**Reference fixture** (t = 2026-03-12 12:30:00 UTC; offset s from t: open, high, low, close): -2: 4079.0, 4079.2, 4078.8, 4079.1 | 0: 4080.0, 4081.0, 4079.5, 4080.5 | 7: 4080.5, 4089.0, 4080.4, 4088.0 | 40: 4088.0, 4088.5, 4084.0, 4085.0 | 90: 4085.0, 4090.0, 4083.0, 4084.0 | 290: 4084.0, 4084.5, 4082.0, 4083.0 | 600: 4083.0, 4083.0, 4068.0, 4072.0 | 1790: 4072.0, 4073.0, 4071.0, 4071.5 | 1850: 4071.5, 4100.0, 4071.0, 4099.0.

- [ ] **Step 1: failing tests** in `tests/test_event_study_metrics.py`:
  - `test_measure_window_reference_fixture`: p0 4080.0, p0_lag_s 0; up_1 9.0, down_1 0.5, peak_1 9.0, ttp_1_s 7, side_1 +1, first_min_dir +1; up_5 10.0, down_5 0.5, ttp_5_s 90; up_30 10.0, down_30 12.0, peak_30 12.0, side_30 -1, ttp_30_s 600; net_5 3.0, net_30 -8.5; retrace_5 == pytest.approx(2/3), spike_pullback_5 True; retrace_30 == pytest.approx(1 + 8.5/9), spike_pullback_30 True.
  - `test_bars_after_horizon_and_before_t_are_ignored`: the 4100.0 high at +1850 s and the 4078.8 low at -2 s never appear in any up/down.
  - `test_measure_window_exact_key_set`: `set(result) == set(METRIC_KEYS)` for ok and no_data.
  - `test_p0_more_than_60s_after_t_is_no_data`: first bar at +75 s -> status "no_data", every measure None.
  - `test_net_needs_a_bar_within_120s`: no bar in [t+3 min, t+5 min) -> net_5 None, retrace_5 None, spike_pullback_5 None.
  - `test_first_minute_tie_has_no_direction`: up_1 == down_1 -> first_min_dir 0, spike flags None.
  - `test_choose_bars_falls_back_to_minute_bars`: empty sec -> ("min1", 60, ...); both empty -> ("none", 0, []); minute bars give ttp in multiples of 60.
  - `test_bars_from_frame_drops_nan_and_rejects_naive_index`.
  - `test_owner_units_gold_pips_and_us30_points`: `owner_units("XAUUSD", 4090.0 - 4080.0) == (1000.0, "pips")`; `owner_units("US30", 25.0) == (25.0, "points")`; `owner_units("EURUSD", 1.0)` raises ValueError.
  - `test_baseline_multiple`: (3.0, 1.5) -> 2.0; (3.0, 0.0) -> None; (None, 1.5) -> None.
- [ ] **Step 2:** `python -m pytest tests/test_event_study_metrics.py -q -p no:warnings` -> FAIL (module missing).
- [ ] **Step 3: implement** `scripts/event_study_metrics.py` (pure; module docstring states the bar rules: sparse 1-second bars, first-at/after p0, last-before net with gap limit, horizon windows half-open [t, t+k)).
- [ ] **Step 4:** the test file -> PASS.
- [ ] **Step 5:** full suites (pytest + `npm test`) green apart from the known env-only failure.
- [ ] **Step 6:** commit `feat(B5): event-study window metrics (peaks, timing, net, retrace, owner units)`.

---

### Task 2: Members, clusters and group summaries — *judgment*

**Files:**
- Create: `scripts/event_study_groups.py`, `tests/test_event_study_groups.py`

**Interfaces:**
- `@dataclass(frozen=True) class Member: title: str; when_utc: dt.datetime; forecast: Optional[str]; actual: Optional[str]; impact: Optional[str]`.
- `def collapse_members(rows: list[Member]) -> list[Member]` — kept rows from `webapp.reaction_rules.collapse_same_title_duplicates`; a kept row lacking a readable forecast/actual (`stats_rules.parse_number`) takes them from the first row of its run (same title, within `DUPLICATE_WITHIN` of the kept time) that has both.
- `def surprise_side(m: Member) -> Optional[int]` — `stats_rules.side(actual, forecast, tolerance(forecast))`, None when unreadable.
- `def surprise_steps(m: Member) -> Optional[float]` — |actual - forecast| / tolerance.
- `def usd_direction(m: Member) -> Optional[int]` — None when the side is None or the title is not in `EVENT_SURPRISE_DIRECTION`; 0 in line; else +1 USD up / -1 USD down.
- `def instrument_direction(m: Member, symbol: str) -> Optional[int]` — None when `usd_direction` is None; 0 in line; else `market_lean(title, side, symbol)` buy +1 / sell -1 (mixed -> None).
- `def effective_impact(m: Member) -> str` — "High" / "Medium" / "Low" / "Unknown" (row impact, case-insensitive, else `EVENT_REGISTRY`).
- `@dataclass(frozen=True) class Cluster: minute: dt.datetime; members: tuple[Member, ...]`; `def build_clusters(members: list[Member]) -> list[Cluster]` — grouped by UTC minute (seconds dropped), sorted.
- `def cluster_class(c: Cluster) -> str`, `def all_same(c: Cluster) -> bool`, `def cluster_impact(c: Cluster) -> str`, `def cluster_instrument_direction(c: Cluster, symbol: str) -> Optional[int]` (common non-zero direction for `single_directional` / `agree`, else None).
- `def next_release_gap_min(minute: dt.datetime, all_minutes: list[dt.datetime]) -> Optional[float]` — minutes to the next release minute, None if none.
- `RELEASE_ROW_KEYS: tuple[str, ...]` = `t_utc, t_sast, symbol, n_members, titles, cluster_class, all_same, impact, implied_dir, baseline, next_release_gap_min` + `METRIC_KEYS` + `peak_1_x, peak_5_x, peak_30_x, abs_net_5_x, abs_net_30_x, dir_net_30_x, peak_1_owner, peak_5_owner, peak_30_owner, owner_unit, dxy_bar_source, dxy_p0, dxy_net_5, dxy_net_30`.
- `def build_release_row(c: Cluster, symbol: str, metrics: dict[str, Any], baseline: Optional[float], gap_min: Optional[float], dxy: dict[str, Any]) -> dict[str, Any]` — keys exactly `RELEASE_ROW_KEYS`; `_x` = `baseline_multiple`, `dir_net_30_x` = implied_dir x net_30 / baseline; `t_sast` formatted `%Y-%m-%d %H:%M SAST`; `titles` joined with " | ".
- `def summarize(values: list[float]) -> dict[str, Optional[float]]` — keys `n, mean, p25, median, p75, p90, max`; quantiles via `compute_release_reactions.quantile`.
- `def usable(row: dict[str, Any], k_min: int) -> bool` — status ok and (`next_release_gap_min` is None or >= k).
- `def magnitude_table(rows: list[dict], symbol: str) -> dict[str, dict]` — per class (`single_directional`, `agree`, `agree_all_same`, `conflict`, `single_in_line`, `all_in_line`, `partial`, `single_unknown`): `summarize` of peak_1_x, peak_5_x, peak_30_x, abs_net_5_x, abs_net_30_x, dir_net_30_x, plus `implied_hit_30` (n, hits: sign(net_30) == implied_dir); each measure only over `usable` rows for its horizon.
- `def pullback_table(rows: list[dict], symbol: str) -> dict[str, dict]` — per class: n with a first-minute direction, n spike_pullback_5, n spike_pullback_30.
- `def conflict_detail(c: Cluster, row: dict[str, Any], symbol: str) -> dict[str, Any]` — keys `t_sast, symbol, members` (list of {title, impact, instrument_dir, surprise_steps}), `first_min_dir, net_5_sign, net_30_sign, first_followed, net30_followed` (title lists), `largest_surprise_title, first_followed_largest, net30_followed_largest, highest_impact_title, net30_followed_highest_impact` (None when impacts tie), `spike_pullback_5, spike_pullback_30`.
- `def peak_distribution(rows: list[dict], symbol: str) -> dict[str, dict]` — per impact group ("High", "others"): `summarize` of peak_1 ($ / points), peak_5, ttp_1_s, ttp_30_s; for XAUUSD band counts of peak_1 in $: `lt5, 5_10, 10_15, 15_20, 20_plus` (lower bound inclusive).

- [ ] **Step 1: failing tests** in `tests/test_event_study_groups.py`:
  - `test_duplicate_within_3_minutes_collapses_and_keeps_actual`: "CPI m/m" at 12:30 (actual None) and 12:32 (actual "0.4", forecast "0.3") -> one member at 12:30 with actual "0.4"; a 12:34 row of the same title stays a second member.
  - `test_directions_cpi_and_claims`: CPI m/m 0.4 vs 0.3 -> side +1, usd +1, XAUUSD -1, US30 -1, surprise_steps 1.0; Unemployment Claims "230K" vs "220K" -> usd -1, XAUUSD +1; CPI m/m "0.3" vs "0.3" -> 0 everywhere.
  - `test_cluster_classes`: {CPI hot, Claims high} -> "conflict"; {CPI hot, Core CPI m/m in line} -> "agree" with `all_same` False; {CPI hot, Core CPI hot} -> "agree", `all_same` True; {two in line} -> "all_in_line"; single CPI hot -> "single_directional".
  - `test_unmapped_title_is_partial_not_in_line`: {CPI hot, "Some Unmapped Index" with numbers} -> "partial"; alone -> "single_unknown".
  - `test_effective_impact_falls_back_to_registry`: impact None + "Non-Farm Employment Change" -> "High"; unknown title -> "Unknown"; cluster impact = highest.
  - `test_build_release_row_exact_keys_and_units`: keys == `RELEASE_ROW_KEYS`; with peak_1 9.0 and baseline 1.5, `peak_1_x == 6.0`, `peak_1_owner == 900.0`, `owner_unit == "pips"`; 12:30 UTC -> `t_sast` "2026-03-12 14:30 SAST".
  - `test_rows_with_next_release_inside_horizon_are_excluded`: gap 10 min -> included for k 1 and 5, excluded for k 30; gap None -> included everywhere.
  - `test_conflict_detail_follows`: conflict {CPI m/m "0.5" vs "0.3" (XAUUSD -1, steps 2.0), Unemployment Claims "221K" vs "220K" (XAUUSD +1, steps 1.0)} with first_min_dir +1, net_30 -2.0 -> first_followed ["Unemployment Claims"], net30_followed ["CPI m/m"], largest_surprise_title "CPI m/m", net30_followed_largest True, first_followed_largest False.
  - `test_peak_distribution_bands`: XAUUSD High peak_1 values [4.99, 5.0, 10.0, 15.0, 20.01] -> bands lt5 1, 5_10 1, 10_15 1, 15_20 1, 20_plus 1; `summarize([1, 2, 3, 4])` median 2.5, p25 1.75, n 4.
- [ ] **Step 2:** run the file -> FAIL.
- [ ] **Step 3: implement** `scripts/event_study_groups.py` (pure; imports `webapp.stats_rules`, `webapp.stats_methods.market_lean`, `webapp.reaction_rules`, `config.settings`, `scripts.event_study_metrics`).
- [ ] **Step 4:** run -> PASS.
- [ ] **Step 5:** full suites green.
- [ ] **Step 6:** commit `feat(B5): event-study clusters, implied directions and group summaries`.

---

### Task 3: Chain (E2) and dipstick (E3) helpers — *mechanical*

**Files:**
- Create: `scripts/event_study_checks.py`, `tests/test_event_study_checks.py`

**Interfaces:**
- `DXY_THRESHOLDS_BPS: tuple[float, ...] = (0.0, 2.0, 5.0)`; `HEADLINE_DXY_BPS = 2.0`; `ENGINE_SIGN = {"XAUUSD": -1, "US30": -1}` (gold inverse; US30 `risk_sentiment` flips like inverse in `market_lean`).
- `def bps(move: Optional[float], p0: Optional[float]) -> Optional[float]` — move / p0 x 10,000.
- `def event_usd_agreement(rows: list[tuple[int, Optional[float], Optional[float]]], threshold_bps: float) -> dict[str, Any]` — rows = (implied USD dir, dxy_net_5, dxy_p0); counts only dir in (+1, -1) and |bps| > threshold; keys `threshold_bps, n, n_match, share` (share None when n = 0).
- `def usd_instrument_agreement(rows: list[tuple[Optional[float], Optional[float], Optional[float]]], engine_sign: int, threshold_bps: float) -> dict[str, Any]` — rows = (dxy_net_5, dxy_p0, inst_net_5); instrument move 0 or None excluded; agree when sign(inst) == engine_sign x sign(dxy); same keys with `n_agree`.
- `def ols(xs: list[float], ys: list[float]) -> Optional[dict[str, float]]` — keys `slope, intercept, r, n`; None when n < 3 or var(x) == 0.
- `@dataclass(frozen=True) class NowcastPoint: as_of_utc: dt.datetime; value: float`.
- `def load_nowcast_csv(path: Path) -> dict[tuple[str, dt.datetime], list[NowcastPoint]]` — columns of `cleveland_nowcast_to_csv.CSV_COLUMNS`; key (event_title, release_utc); points sorted by as_of.
- `def value_as_of(points: list[NowcastPoint], cutoff: dt.datetime) -> Optional[float]` (latest as_of <= cutoff); `def final_value(points: list[NowcastPoint], release: dt.datetime) -> Optional[float]` (latest as_of < release).
- `LAGS_DAYS: tuple[int, ...] = (5, 15, 20, 25)`; `HEADLINE_LAG_DAYS = 25`.
- `DIPSTICK_KEYS` = `title, release_utc, release_sast, lag_days, early, final, actual, forecast, early_equals_final, closer, early_side, final_side, actual_side, side_changed, early_hit, final_hit`.
- `def dipstick_row(title: str, release: dt.datetime, points: list[NowcastPoint], forecast_text: Optional[str], actual_text: Optional[str], lag_days: int) -> dict[str, Any]` — keys exactly `DIPSTICK_KEYS`; `closer` "final" / "early" / "tie" (distances within 1e-12) / None (a value missing); sides by `stats_rules.side` with `tolerance(forecast_text)`.
- `def summarize_dipstick(rows: list[dict[str, Any]]) -> dict[str, int]` — keys `n, final_closer, early_closer, ties, early_equals_final, side_changed, early_hits, final_hits` (n counts rows with early, final and actual all present).

- [ ] **Step 1: failing tests** in `tests/test_event_study_checks.py`:
  - `test_event_usd_agreement_thresholds`: DXY p0 100.0; rows (+1, 0.01, 100) [1 bp], (+1, 0.03, 100), (-1, 0.03, 100), (0, 0.05, 100), (+1, None, 100) -> at 2 bp n 2, n_match 1, share 0.5; at 0 bp n 3.
  - `test_usd_instrument_agreement_inverse`: (0.03, 100, -2.0) agree, (0.03, 100, +1.0) disagree, (0.03, 100, 0.0) excluded -> n 2, n_agree 1.
  - `test_ols_exact_and_degenerate`: xs [1, 2, 3], ys [2, 4, 6] -> slope 2.0, intercept 0.0, r 1.0, n 3; xs [1, 1, 1] -> None; two points -> None.
  - `test_dipstick_row_reference_fixture`: release 2026-03-11 12:30Z; points 2026-02-09T23:59:59Z 0.20, 2026-02-14T23:59:59Z 0.25, 2026-03-01T23:59:59Z 0.30, 2026-03-10T23:59:59Z 0.31; forecast "0.3", actual "0.3", lag 25 -> early 0.20 (the 02-14 point is after the 02-14 12:30 cutoff), final 0.31, closer "final", early_side -1, final_side 0, actual_side 0, side_changed True, early_hit False, final_hit True; keys == `DIPSTICK_KEYS`; `release_sast` "2026-03-11 14:30 SAST".
  - `test_dipstick_tie_when_early_equals_final`: release 2026-03-11 12:30Z, points 2026-03-01T23:59:59Z 0.30 and 2026-03-10T23:59:59Z 0.30, lag 5 (cutoff 03-06 12:30) -> early 0.30, final 0.30, closer "tie", early_equals_final True.
  - `test_final_value_excludes_release_day_stamp`: a point at the release instant is not final.
  - `test_load_nowcast_csv_round_trip` (tmp file with the five CSV columns, two titles).
- [ ] **Step 2:** run -> FAIL.
- [ ] **Step 3: implement** `scripts/event_study_checks.py` (pure, stdlib + `webapp.stats_rules`).
- [ ] **Step 4:** run -> PASS.
- [ ] **Step 5:** full suites green.
- [ ] **Step 6:** commit `feat(B5): event-study chain and Tier 1 dipstick helpers`.

---

### Task 4: Study runner (read-only I/O, bar cache, outputs) — *integration*

**Files:**
- Create: `scripts/event_study_once.py`, `tests/test_event_study_once.py`

**Interfaces:**
- Constants: `LIVE_DASH_DB = Path(r"C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine\webapp\dashboard.db")`, `LIVE_BT_DB` (same root, `scoring\backtest_log.db`), `DEFAULT_OUT_DIR = Path(r"C:\Users\Masoodt\AppData\Local\Temp\news_engine_event_study")`, `DEFAULT_NOWCAST_CSV = Path(r"C:\Users\Masoodt\AppData\Local\Temp\claude\C--Users-Masoodt-Documents-Claude-Projects-Claude-news-engine-news-engine\1652784f-1d74-4be3-8ee5-c3ecae49ef30\scratchpad\nowcasts.csv")`, `SYMBOLS = ("XAUUSD", "US30")`, `SERIES = SYMBOLS + ("DXY",)`, `START = 2026-01-01T00:00Z`, `BEFORE = 2 min`, `AFTER = 31 min`, `SETTLE = 10 min` (a minute is studied once t + AFTER + SETTLE <= now), `CACHE_MIN_AGE = 1 h`, `DEFAULT_PAUSE_S = 1.5`, `REPO_ROOT = Path(__file__).resolve().parents[3]`.
- `def open_readonly(path: Path) -> sqlite3.Connection` — `f"{path.resolve().as_uri()}?mode=ro"`, `uri=True`, `row_factory = sqlite3.Row`; `FileNotFoundError` when the file does not exist (checked first, so sqlite never creates it).
- `def assert_outside_repo(out_dir: Path) -> None` — `ValueError` when `out_dir.resolve()` is `REPO_ROOT` or inside it.
- `def read_members(dash_conn: sqlite3.Connection, since: dt.datetime, until: dt.datetime) -> list[Member]` — `SELECT event_title, event_time_utc, forecast, actual, impact FROM event_history WHERE country = 'USD'`, parsed with `market_reaction_phase0._parse_utc`, filtered in Python to [since, until], then `collapse_members` (collapse runs on all USD rows first, then the filter, so a run straddling `since` is judged once).
- `def read_baselines(bt_conn: sqlite3.Connection, symbol: str) -> dict[int, float]` — `backtest_store.get_latest_reaction_baselines(conn, symbol, REACTION_BASELINE_QUANTILE)`; `{}` when the table is missing.
- `def baseline_for(baselines: dict[int, float], t: dt.datetime) -> Optional[float]` — by `t.astimezone(UTC).hour`.
- `def dukascopy_instrument(series: str) -> str` — DXY from `data_layer.discovery_detector._DETECTOR_INSTRUMENT_MAP["DXY"]`, others `data_layer.dukascopy_feed._resolve_dukascopy_instrument`.
- `FetchFn = Callable[[str, str, dt.datetime, dt.datetime], pd.DataFrame]` (instrument, interval, lo, hi); `def dukascopy_fetch(instrument: str, interval: str, lo: dt.datetime, hi: dt.datetime) -> pd.DataFrame` (BID side; the only network code).
- `class BarCache` — `__init__(self, root: Path, fetch: FetchFn, now: dt.datetime, pause_s: float = DEFAULT_PAUSE_S, sleep: Callable[[float], None] = time.sleep, offline: bool = False)`; `get(self, series: str, interval_tag: str, t: dt.datetime) -> Optional[list[Bar]]` with `interval_tag` "sec1" / "min1"; cache file `root / "bars" / f"{series}_{t:%Y%m%dT%H%MZ}_{interval_tag}.csv"` (columns ts, open, high, low, close; header-only = fetched, no data); a hit reads the file and neither fetches nor sleeps; a miss fetches [t - BEFORE, t + AFTER], sleeps `pause_s` after every network call, and writes the file only when `t + AFTER <= now - CACHE_MIN_AGE`; an exception returns None, increments `errors` and writes nothing; `offline=True` returns None on a miss. Counters: `network_requests`, `cache_hits`, `errors`.
- `def measure_series(cache: BarCache, series: str, t: dt.datetime) -> dict[str, Any]` — sec1 first; min1 fetched only when `choose_bars` would reject sec1; returns `measure_window(...)` output.
- `def run_study(dash_conn: sqlite3.Connection, bt_conn: sqlite3.Connection, cache: BarCache, nowcast_csv: Path, out_dir: Path, since: dt.datetime, until: dt.datetime, limit: Optional[int] = None, dry_run: bool = False) -> dict[str, Any]` — builds clusters, measures XAUUSD / US30 / DXY per release minute, builds rows, aggregates with Tasks 2-3, writes `releases.csv` (`RELEASE_ROW_KEYS`), `members.csv` (`t_utc, t_sast, title, impact, forecast, actual, surprise_side, surprise_steps, usd_dir, xauusd_dir, us30_dir, cluster_class`), `conflicts.csv` (flattened `conflict_detail`), `dipstick.csv` (`DIPSTICK_KEYS`), `summary.json` and `summary.md`; returns the summary. `dry_run` fetches nothing and returns only the sample block.
- Summary keys: `run_at_utc, sources, sample, coverage, magnitudes, pullbacks, conflicts, peaks, chain, dipstick, fetch`. `sample` = minutes, minutes_multi, per class counts, fully computable multi-member (agree / conflict / all_in_line), High minutes; `coverage` = per series ok / no_data and sec1 / min1 counts; `chain` = per threshold `event_usd_agreement`, per symbol and threshold `usd_instrument_agreement`, per symbol `ols` on $ and on % moves; `dipstick` = per lag `summarize_dipstick` plus `t5_equals_final` (n, equal) and `snapshot_check` (n compared, n equal to the latest pre-release `tier1_nowcast_snapshots` value), or `{"status": "missing", "regenerate": <exact commands>}`; `fetch` = cache counters.
- `def render_markdown(summary: dict[str, Any]) -> str` — one table per summary block, every table with an n column, times in SAST.
- `def main(argv: Optional[list[str]] = None) -> int` — args `--dash-db` (default `LIVE_DASH_DB`), `--bt-db` (default `LIVE_BT_DB`), `--nowcast-csv`, `--out-dir`, `--since` (default 2026-01-01), `--limit`, `--pause`, `--dry-run`, `--offline`; prints the summary Markdown; exit 0, 2 on a refused out-dir or missing DB.

- [ ] **Step 1: failing tests** in `tests/test_event_study_once.py` (fixture `dashboard.db` built with `webapp.store.get_connection(tmp)` then closed; fixture `backtest_log.db` via `backtest_store.get_connection(tmp)` + `backtest_store.record_reaction_baseline`; a fake `FetchFn` that builds frames from a dict and counts calls; a fake sleep recording calls):
  - `test_open_readonly_refuses_writes`: INSERT raises `sqlite3.OperationalError`; a missing path raises `FileNotFoundError` and creates no file.
  - `test_out_dir_inside_repo_refused`: `REPO_ROOT / "tmp"` raises; `main([... "--out-dir", str(REPO_ROOT / "x")])` returns 2 and opens no DB.
  - `test_cache_hit_skips_network_and_pause`: two `get` calls for an old window -> fetch called once, sleep called once, `cache_hits == 1`.
  - `test_recent_window_not_cached`: now = t + 40 min -> no cache file written; a second `get` fetches again.
  - `test_fetch_error_not_cached_and_counted`: fetch raises -> None, `errors == 1`, no file.
  - `test_sec1_missing_falls_back_to_min1_and_records_source`: empty sec1 frame -> row `bar_source == "min1"`, `resolution_s == 60`.
  - `test_baseline_uses_utc_hour`: baselines {12: 2.0, 14: 9.0}, t 12:30 UTC -> baseline 2.0.
  - `test_run_study_end_to_end_on_fixture_dbs`: rows = CPI m/m 2026-03-11 12:30 hot, CPI m/m duplicate 12:32, Unemployment Claims 2026-03-11 12:30 high (conflict cluster), Retail Sales m/m 2026-04-15 12:30 hot (single), a EUR row and a 2025-12-30 USD row (both ignored) -> `releases.csv` has 4 rows (2 minutes x 2 symbols) with header == `RELEASE_ROW_KEYS`; `members.csv` 3 rows; `summary["sample"]["minutes"] == 2`; `conflicts.csv` 2 rows; summary keys exact.
  - `test_run_study_writes_only_under_out_dir`: file listing of the fixture DB folder unchanged (no `-journal`/new files beside the DBs) and every created path under out_dir.
  - `test_dry_run_makes_no_fetch`: fetch never called; `sample` present.
  - `test_missing_nowcast_csv_reports_regeneration`: `summary["dipstick"]["status"] == "missing"`, the text contains `cleveland_nowcast_to_csv.py` and `--dash-db`; E1 outputs still written.
  - `test_render_markdown_has_n_columns`: every Markdown table header row contains "n".
- [ ] **Step 2:** run -> FAIL.
- [ ] **Step 3: implement** `scripts/event_study_once.py`; module docstring: purpose, read-only guarantee, outputs location, usage, expected run time (about 3 x the number of release minutes requests at 1.5 s pause; roughly 30-45 min cold, seconds warm).
- [ ] **Step 4:** run -> PASS.
- [ ] **Step 5:** full suites green.
- [ ] **Step 6:** commit `feat(B5): read-only event-study runner with bar cache and outputs`.

---

### Task 5: Run the study on live data, write the report, update docs — *judgment*

**Files:**
- Create: `docs/superpowers/specs/2026-10-21-event-study-report.md`
- Modify: `docs/feature-inventory-2026-09-11.md` (roadmap progress row "B5 Measure first (read-only study)": `built on branch b5-event-study (study run <date>; report docs/superpowers/specs/2026-10-21-event-study-report.md)`; one new feature-table row for the study scripts in the style of the B3/B4 rows: what was built, "Built on branch b5-event-study (read-only study; nothing deployed)", key findings in one paragraph), `docs/roadmap-2026-10-20.md` (status line 3: append `; B5 built on branch b5-event-study 2026-10-21 (study run against live data read-only; report docs/superpowers/specs/2026-10-21-event-study-report.md)`)

- [ ] **Step 1: dry run and sample check.** `python scripts/event_study_once.py --dry-run`. Compare with the known sample (about 207 minutes, 47 multi-member, 23 fully computable: 17 agree, 4 conflict, 2 all in line; minutes after 2026-10-21 are not yet studyable). Explain any difference in the report (date range, the duplicate collapse, the agree definition).
- [ ] **Step 2: full run** in the background: `python scripts/event_study_once.py` (live DBs read-only; outputs in `C:\Users\Masoodt\AppData\Local\Temp\news_engine_event_study\`). Then re-run once to confirm the cache: `fetch.network_requests` should be 0 or only the uncached recent windows.
- [ ] **Step 3: spot checks** (record in the report's method section): the 2026-10-14 12:30 UTC (14:30 SAST) CPI release, XAUUSD peak_1 and net_5 recomputed by hand from the cached 1-second CSV; one min1-fallback row, if any, checked against its bars; `net_5` vs the stored `release_reactions` move for 3 minutes (expected close, not equal; say why).
- [ ] **Step 4: write the report** for the owner, plain English first, then tables with n, then method and limits. Sections:
  1. *Bottom line* (5-8 sentences: the answer to each question, how sure, and the small-sample warning).
  2. *E1 (a) conflicting releases*: per-cluster table (time SAST, members with impact and implied direction, first-minute direction, 5/30-min net, followed by first move, followed by 30-min net, spike-then-pull-back), then the pull-back rate by class (conflict vs agree vs single) with n.
  3. *E1 (b) agreeing releases*: magnitude table per class and symbol (median and p25-p75 of peak_1/5/30 and |net_5|/|net_30| in baseline multiples, the agree `all_same` subset, implied-direction hit rate at 30 min), every cell with n.
  4. *Typical peak*: XAUUSD 1-minute peak in $ and pips (High vs others: n, median, p25, p75, p90, max, band counts, median time to peak in seconds); US30 in points; verdict on "$5-10 within seconds, max $15-20" by the pre-set rule.
  5. *E2 chain*: event -> USD agreement at 0 / 2 / 5 bp with n; USD -> XAUUSD and USD -> US30 sign agreement and elasticity (slope, r, n); comparison with the engine's assumptions (gold inverse; US30 inverse with 0.7).
  6. *E3 dipstick*: per-release table (release SAST, T-25d, final, actual, forecast, closer, call side early / final / actual) for both titles; summary per lag 5 / 15 / 20 / 25; T-5d = final confirmed or refuted with counts; snapshot cross-check.
  7. *E4 decision memo*: mover/anchor go / no-go / not decidable yet, B10 window and threshold, the owner's claim, surprises; each by the pre-set rules in "Plan decisions", with any judgment beyond them labelled.
  8. *Method* (sources, bar rules, units, baseline, cluster classes, contamination rule, differences from `release_reactions`), *Limits* (small n, descriptive only, BID-only, sparse 1-second bars, Dukascopy vs the owner's broker feed, Forex Factory forecasts as the consensus, the baseline dividing 1- and 30-min values by a 5-min typical move), *Reproduce* (the exact commands and the output folder).
  Confidence tags `[Certain]` / `[Likely]` / `[Guessing]` on non-trivial claims. All times SAST.
- [ ] **Step 5: update docs** as listed under Files (CRLF kept).
- [ ] **Step 6:** full suites green (docs-only change, run anyway).
- [ ] **Step 7:** commit `docs(B5): event-study report with live results, inventory and roadmap status`.
