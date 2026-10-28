# B9 — Implementation Plan

**Goal:** The Stats tab stops crediting "in line" guesses as skill: the News side follows the pre-registered lean rule (never "in line"; abstains below |lean| 0.2), and the scoreboard shows an "always in line" baseline and directional-only accuracy, each with n.

**Architecture:** A pure `news_side(lean)` in `webapp/stats_methods.py` decides the News side; `webapp/stats_service.py::_build_one` builds the News `MethodCall` with that side forced (the number `forecast + lean × scale` is still computed and shown, never used for the side), and records a row-level `news_call`. `build_scoreboard` adds per-method `directional`, a News `no_call` count and a top-level `in_line_baseline`, all derived from rows already built; `combine()` and every stored table are untouched. The pure JS builders in `webapp/static/js/stats/rows.js` / `info.js` render the call word, the no-call count, the directional column and the baseline row.

**Spec reference:** `docs/roadmap-2026-10-20.md` §B9 items ST1, ST2 (ST3-ST5 shipped in B9a — not redone) and owner decision 5 (pre-registered 2026-10-20): **News side = sign(lean) when |lean| ≥ 0.2, otherwise no call; the scale only draws the number.** Ruling 3 (unmapped titles get no news call) and the owner rule "never set or fabricate a predicted direction for scoring" stand.

**Verified source facts (2026-10-28, base ad1e8a1):**
- Today `_build_one` (stats_service.py ~347-363) builds News only when `sn = news_surprise(lean, scale)` is not None, and `_call` derives its side from `side(forecast + sn, forecast, tol)`, so a 0.0 scale or a small `lean × scale` always lands in the one-step "in line" band.
- Live DBs (read-only, `mode=ro`), all USD titles, graded News readings: **31 = 25 in line / 2 higher / 4 lower** under the current rule; the ST1 rule on the same leans gives **23 no call / 2 higher / 6 lower**. CPI m/m alone has only 2 graded News readings (leans 0.102, 0.147): **before 2 in line, after 2 no call**. Live leans that exist without a scale (fewer than 3 priors): ISM Manufacturing PMI 2026-09-01 (-0.324, graded), Prelim UoM 2026-10-09 (0.2, pending), Core PCE 2026-10-29 (-0.2, pending).
- Fixture arithmetic below was computed with the base code (`_cpi_history` + Jul/Aug/Sep rows, see Task 1).
- `MethodCall.side` is deliberately not served (app.py comment above `_method_dict`); the call word reaches the UI only through the new row field `news_call`.

## Global Constraints

- Combined number unchanged: `combine(s1, sn)` with `sn = lean × scale` exactly as today, including when News abstains; `combine`, `news_surprise`, `news_scale`, `news_lean`, `TIER1_WEIGHT`, `NEWS_WEIGHT` are not edited.
- `NEWS_CALL_MIN_LEAN = 0.2` is pre-registered: named constant, comment says so, never tuned; comparison `abs(lean) >= NEWS_CALL_MIN_LEAN - 1e-9` (float noise only, so p = 0.6 gives a call).
- News never has side 0. A lean of None (or a title cleared by ruling 3) means no News `MethodCall` at all, as today.
- No DB writes, no schema change, no change to `scoring/`, `data_layer/`, stored predictions or `predicted_direction` anywhere. Stats derives a display side only.
- Tier 1 and Combined sides/verdicts unchanged; no "conflict"/"conflicting" anywhere; `agreement_for` unchanged (it naturally recomputes from the new News side); `tier1_tier` unchanged.
- Payloads: `/api/stats/events` rows gain exactly `news_call`; `CALL_KEYS`, `DETAIL_KEYS`, chart payload unchanged. Scoreboard gains exactly `methods.*.directional`, `methods.news.no_call`, top-level `in_line_baseline`; every existing key and the footnote keep their values' meaning.
- Percent rule: every new accuracy uses `MIN_SCORED_FOR_PERCENT` (hidden under 20); counts always served.
- Market reaction tab, shock alerts, ACE/EA/MT5: untouched.
- CRLF kept in every touched file (all targets are CRLF, including new docs); type hints on Python signatures; vanilla ES modules + `node --test`.
- Never touch the live worktree (read-only reference), live DBs except `mode=ro` reads, scheduled tasks, Telegram; never push.
- Tests from the app dir: `python -m pytest -q -p no:warnings` and `npm test`; only `tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present` may fail.

## Review Focus

- **Combined number drifts** (News side change leaks into the blend, or an abstaining News is dropped from the blend) -> `test_combined_number_unchanged_by_st1` golden pin, passes before and after (Task 1).
- **News still says "in line"** (side 0 from a 0.0 scale) -> `test_zero_scale_news_takes_the_lean_side_not_in_line` (Task 1).
- **Threshold off by float noise** (p = 0.6 -> 0.19999999999999996 abstains) or wrong boundary -> `test_news_side_pre_registered_threshold` (Task 1).
- **No-call graded as wrong or as in line** -> `test_news_no_call_is_excluded_from_accuracy_and_counted` (Task 2) and `test_st1_news_sides_and_agreement` (Task 1).
- **Scale decides the side by its absence** (lean ≥ 0.2 with < 3 priors dropped) -> `test_unsized_news_lean_still_calls_a_side` (Task 1).
- **Fabricated stored direction / DB write** -> `test_st1_writes_nothing_to_either_db` (Task 1).
- **Baseline over the wrong population** (all rows instead of each method's graded releases) or directional including in-line actuals -> `test_scoreboard_baseline_and_directional_per_method` (Task 2).
- **Payload drift** -> exact key sets in `test_events_route_serves_every_field_the_tab_renders` (Task 1) and `test_scoreboard_route_serves_the_honest_baselines_exactly` (Task 2).
- **UI contradicts the rule** (brief card or readings say "in line" for a News call whose number equals the forecast) -> `news brief card uses the call word, never in line` (Task 3) and the info.js readings test (Task 3).

---

## Task 1 — ST1: pre-registered News side (server)  `[judgment]`

**Files:** `webapp/stats_methods.py`, `webapp/stats_service.py`, `webapp/app.py` (`_stats_row_dict` only), `tests/test_stats_methods.py`, `tests/test_stats_service.py`, `tests/test_app_stats_routes.py`.

**Interfaces:**
- `stats_methods.NEWS_CALL_MIN_LEAN: float = 0.2` — comment: `# Pre-registered 2026-10-20 (owner decision 5, roadmap B9 ST1), fixed before viewing more results: do not tune.`
- `stats_methods.news_side(lean: Optional[float]) -> Optional[int]` — `None` for None or `abs(lean) < NEWS_CALL_MIN_LEAN - 1e-9`; else `1` if `lean > 0` else `-1`. Never returns 0.
- `stats_service._call(..., explicit_side: Optional[int] = None, side_fixed: bool = False) -> MethodCall` — `side_fixed=True` makes `explicit_side` the side even when it is None (a News abstention); the default path is byte-for-byte today's behaviour. The hand-logged Tier 1 call keeps its current arguments.
- `StatsRow.news_call: Optional[str] = None` — `'higher' | 'lower' | 'no_call'` when a News `MethodCall` exists, `None` when there is none. Informational, read by nothing in scoring.
- News `MethodCall.note`: `'scaled'` when the number exists (as today), `'unsized'` when the lean has a side but fewer than 3 priors (predicted/surprise/miss None).
- `app._stats_row_dict` adds `"news_call": r.news_call`.

**Steps:**
- [ ] Add the golden pin first and run it against the unchanged code -> it must PASS now (that is the "before" half of before/after equality):
  - `_honest_population(dash, bt)` helper: `_cpi_history(dash)`; then for (Jul, a "0.3%", print "higher" conf 0.2), (Aug, "0.4%", "higher" 0.1), (Sep, "0.2%", "lower" 0.5): `_event(dash, "CPI m/m", _t(m), "0.3%", a)`, `_snap(bt, "CPI m/m", _t(m), 0.4)`, `_print_call(..., scored_at=_t(m) - 1 day)`; return `build_rows(..., event_title="CPI m/m")`.
  - `_zero_scale_row(dash, bt)` helper: three USD CPI m/m priors with forecast = actual = "0.3%" (scale 0.0), Oct "0.3%"/"0.4%", `_snap(..., 0.4)`, print "higher" conf 0.8; return the Oct row.
  - `test_combined_number_unchanged_by_st1`: for `_honest_population` rows Jul/Aug/Sep, `(combined.surprise, combined.predicted, combined.verdict, combined.note)` == `(0.076, 0.376, "right", None)`, `(0.073, 0.373, "wrong", None)`, `(0.055, 0.355, "wrong", None)` (floats `approx(abs=1e-12)`); each equals `0.7 * detail.tier1_surprise + 0.3 * detail.news_surprise`; `build_scoreboard(rows)["methods"]["combined"]` `scored/right/with_news` == `3 / 1 / {"scored": 3, "right": 1}`; for `_zero_scale_row`: `detail.news_surprise == 0.0`, `combined.surprise == approx(0.07)`, `combined.predicted == approx(0.37)`, `combined.verdict == "wrong"`.
- [ ] Add failing tests:
  - `test_stats_methods.py::test_news_side_pre_registered_threshold`: `news_side(0.2) == 1`, `news_side(-0.2) == -1`, `news_side(abs(2 * 0.6 - 1)) == 1`, `news_side(0.1999) is None`, `news_side(-0.19) is None`, `news_side(0.5) == 1`, `news_side(-1.0) == -1`, `news_side(None) is None`; `NEWS_CALL_MIN_LEAN == 0.2`; no input returns 0 (loop over `[i / 100 for i in range(-100, 101)]`).
  - `test_st1_news_sides_and_agreement` on `_honest_population`: Jul `news.side == 1`, `news_call == "higher"`, `news.verdict == "wrong"` (actual in line), `agreement == "agree"`; Aug `news.side is None`, `news_call == "no_call"`, `news.verdict is None`, `news.leans == {}`, `news.predicted == approx(0.31)` (number still drawn), `agreement is None`; Sep `news.side == -1`, `news_call == "lower"`, `news.verdict == "right"`, `agreement == "disagree"`. Tier 1 verdicts Jul/Aug/Sep stay `wrong/right/wrong`.
  - `test_zero_scale_news_takes_the_lean_side_not_in_line`: `_zero_scale_row` -> `news.side == 1`, `news_call == "higher"`, `news.predicted == approx(0.3)`, `news.verdict == "right"`, `news.miss == approx(0.1)`.
  - `test_unsized_news_lean_still_calls_a_side`: two USD priors only, Oct "0.3%"/"0.4%", `_snap(..., 0.4)`, print "higher" 0.5 -> `news.side == 1`, `news.predicted is None`, `news.note == "unsized"`, `news.verdict == "right"`, `detail.news_scale is None`, `combined.note == "news_missing"` and `combined.surprise == approx(0.1)` (an unsized call never blends); same with conf 0.1 -> `news_call == "no_call"`, `news.verdict is None`.
  - `test_st1_writes_nothing_to_either_db`: on `_honest_population`'s connections, record `dash.total_changes`, `bt.total_changes` and `SELECT * FROM print_predictions/predictions/tier1_predictions` rows; run `build_rows`, `build_scoreboard`, `build_chart(rows, "news")`; all equal afterwards.
  - Update existing expectations that ST1 changes (comment each with "B9 ST1"): `test_news_call_uses_the_print_call_and_the_median_scale` verdict `"wrong"` -> `"right"` (lean 0.5 -> higher); `test_scoreboard_separates_live_reconstructed_and_with_news_populations` News `by_kind.live` `{"scored": 1, "right": 0}` -> `{"scored": 1, "right": 1}` and its comment; `test_non_usd_rows_do_not_count_toward_the_minimum_scale_history` -> `row.detail.news_scale is None and row.news.predicted is None and row.news_call == "higher"` (intent kept: the non-USD row still does not count as a prior).
  - `tests/test_app_stats_routes.py`: `ROW_KEYS` gains `"news_call"`; `client` row asserts `row["news_call"] is None`; `full_client` row asserts `row["news_call"] == "higher"`; `CALL_KEYS`/`DETAIL_KEYS` unchanged.
- [ ] Run `python -m pytest -q -p no:warnings tests/test_stats_methods.py tests/test_stats_service.py tests/test_app_stats_routes.py` -> new tests FAIL, golden pin PASSES.
- [ ] Implement:
  - `news_side` + constant as above (import into stats_service).
  - In `_build_one`, after the ruling-3 clear and `sn = news_surprise(lean, scale)`: if `lean is None` -> `news = None`, `news_call = None`; else `nside = news_side(lean)`, `news = _call(None if sn is None else forecast + sn, sn, forecast, tol, actual, title, note="scaled" if sn is not None else "unsized", explicit_side=nside, side_fixed=True)`, `news_call = {1: "higher", -1: "lower", None: "no_call"}[nside]`. Update the block comment: side from the pre-registered rule, the number only from lean × scale.
  - Leave `blended = combine(s1, sn)` and the Combined call exactly as they are.
  - Update the `MethodCall.note` comment to list `'unsized'`; add `news_call` to the `StatsRow` informational block; pass `news_call=` in the `StatsRow(...)` return; `_not_scoreable` keeps the default None.
  - `app._stats_row_dict`: add `"news_call": r.news_call`; extend the comment above `_method_dict` ("`agreement` and `news_call` are the only things derived from side that leave the server").
- [ ] Run the three files -> PASS (golden pin still PASS = after half).
- [ ] `git diff --stat` touches no file under `scoring/` or `data_layer/`; `git grep -n "INSERT\|UPDATE\|DELETE" webapp/stats_service.py webapp/stats_methods.py` returns nothing.
- [ ] Full suites (`python -m pytest -q -p no:warnings`, `npm test`) -> PASS except the known env failure. (`info.test.js` may not break yet: it reads `detail`, not `news_call`.)
- [ ] Commit: `feat(B9): ST1 pre-registered News side (|lean| >= 0.2, else no call); number unchanged` + Co-Authored-By line.

## Task 2 — ST2: honest baselines in the scoreboard (server)  `[integration]`

**Files:** `webapp/stats_service.py` (`build_scoreboard` + two private helpers), `tests/test_stats_service.py`, `tests/test_app_stats_routes.py`.

**Interfaces:**
- `_actual_side(row: StatsRow) -> Optional[int]` — `side(row.actual, row.forecast, row.tol)` when all three are present, else None.
- `_rate(scored: int, right: int) -> dict` — `{"scored", "right", "accuracy": right / scored if scored >= MIN_SCORED_FOR_PERCENT else None, "accuracy_shown": scored >= MIN_SCORED_FOR_PERCENT}`.
- `build_scoreboard(rows) -> dict` gains, per method over the SAME graded calls it already counts (`call.verdict is not None`):
  - `methods[name]["directional"] = _rate(n, k)` over graded calls whose actual side is ±1.
  - `methods["news"]["no_call"]: int` — rows with `row.status == "scored"` and `row.news is not None` and `row.news.side is None` (abstentions with an actual; pending abstentions not counted).
  - top-level `in_line_baseline[name] = _rate(n, k)`: n = that method's graded calls, k = those whose actual side is 0.
  - Existing keys and values unchanged; docstring extended (ST2, n always shown, % hidden under 20).

**Steps:**
- [ ] Add failing tests:
  - `test_scoreboard_baseline_and_directional_per_method` on `_honest_population` (Task 1 helper): `methods["tier1"]` scored/right `3/1`, `directional == {"scored": 2, "right": 1, "accuracy": None, "accuracy_shown": False}`; `methods["news"]` scored/right `2/1`, `directional` `1/1`, `no_call == 1`; `methods["combined"]` scored/right `3/1`, `directional` `0/2` i.e. `{"scored": 2, "right": 0, ...}`; `in_line_baseline == {"tier1": 1 of 3, "news": 1 of 2, "combined": 1 of 3}` (each as a full `_rate` dict, accuracy None, shown False).
  - `test_news_no_call_is_excluded_from_accuracy_and_counted`: same rows -> Aug (no call) is not in `news.scored`, not in `news.directional.scored`, not in `in_line_baseline.news.scored`; `news.mean_miss == approx((0.02 + 0.05) / 2)` (only graded calls); a pending abstention (add Nov "0.3%"/None with print conf 0.1) leaves `no_call == 1`.
  - `test_honest_rates_show_percent_from_20`: reuse the 20-release loop of `test_scoreboard_suppresses_percentages_below_20_and_shows_them_at_20` (forecast 0.3, actual 0.4, nowcast 0.4) -> `tier1.directional == {"scored": 20, "right": 20, "accuracy": 1.0, "accuracy_shown": True}`, `in_line_baseline.tier1 == {"scored": 20, "right": 0, "accuracy": 0.0, "accuracy_shown": True}`; first 19 rows -> both `accuracy None`, shown False.
  - `tests/test_app_stats_routes.py::test_scoreboard_route_serves_the_honest_baselines_exactly`: `full_client` scoreboard `?event=CPI%20m/m&month=10` -> `set(data) == {"methods", "min_for_percent", "footnote", "in_line_baseline"}`; `set(data["in_line_baseline"]) == {"tier1", "news", "combined"}`; every rate dict key set `== {"scored", "right", "accuracy", "accuracy_shown"}`; `set(methods["tier1"]) == {"scored", "right", "accuracy", "accuracy_shown", "mean_miss", "by_kind", "directional"}`, news adds `"no_call"`, combined adds `"with_news"`; values: actual 0.4 vs 0.3 is higher, so each `directional == {"scored": 1, "right": 1, ...}` and each baseline `{"scored": 1, "right": 0, ...}`, `news.no_call == 0`.
  - Update `test_scoreboard_route_serves_live_reconstructed_and_with_news_counts`: its whole-dict equality gains the `directional` (and News `no_call: 0`) entries with the values above.
- [ ] Run the two files -> FAIL.
- [ ] Implement in `build_scoreboard`: inside the existing per-call loop compute `a_side = _actual_side(row)` once; increment `dir_scored/dir_right` when `a_side` is ±1, `base_right` when `a_side == 0`; after the loop add `directional` and `in_line_baseline[name] = _rate(scored, base_right)`; count `no_call` in a separate pass for News only. Import `side` is already present.
- [ ] Run the two files -> PASS; full suites -> PASS (known env failure only).
- [ ] Commit: `feat(B9): ST2 always-in-line baseline, directional-only accuracy and News no-call count, each with n` + Co-Authored-By line.

## Task 3 — Stats UI: call word, no-call, baseline and directional  `[integration]`

**Files:** `webapp/static/js/stats/rows.js`, `webapp/static/js/stats/rows.test.js`, `webapp/static/js/stats/info.js`, `webapp/static/js/stats/info.test.js`, `webapp/static/style.css` (only if the baseline row needs a class; reuse `meta-text-sm` otherwise).

**Interfaces (rows.js, pure, all strings escaped):**
- `export const NEWS_CALL_TEXT = { higher: "calls higher", lower: "calls lower", no_call: "no call (|lean| under 0.2)" }`; `export function newsCallText(newsCall)` -> that text or `""`.
- `sentimentRowHtml(row)`: predicted cell becomes `${num(n.predicted)} · ${newsCallText(row.news_call)}` + leans; an `'unsized'` call shows `—` for the number.
- `combinedRowHtml(row)`: the News cell appends `newsCallText(row.news_call)` before the verdict chip.
- `pickNextRow(rows, now, method)`: for `method === "news"` additionally requires `row.news_call === "higher" || row.news_call === "lower"`.
- `briefCardHtml(row, method, ...)`: for `method === "news"` the expected word is `"hotter than consensus"` / `"cooler than consensus"` from `row.news_call`, never `expectedWord(...)`; other methods unchanged.
- `scoreboardHtml(sb, unit)`: header `Method | Right calls | Directional only`; each method row gets a third cell `${d.right} of ${d.scored}${pct}` from `m.directional` (default `{scored: 0, right: 0}`); the News row adds `<div class="meta-text-sm">no call on ${no_call} of ${scored + no_call} graded releases (|lean| under 0.2)</div>`; then one baseline row `<tr><td>Always in line (baseline)</td><td colspan="2">Tier 1 releases k of n (p%) · News releases k of n · Combined releases k of n</td></tr>` from `sb.in_line_baseline`; a fixed note line `Directional only: releases that came in higher or lower than forecast. Baseline: what always answering "in line" would score on the same releases.`; footnote unchanged. `%` only where `accuracy_shown`.
- `info.js` `combinedLines`: after the News lean line add `News call: higher` / `News call: lower` / `News call: none (|lean| under 0.2, pre-registered)` from `row.news_call`; replace the unsized line's `": no news call"` with `", so no number; the call still follows the lean"`.

**Steps:**
- [ ] Add failing tests to `rows.test.js`:
  - `newsCallText maps the three calls and is empty otherwise` (`"higher"`, `"lower"`, `"no_call"`, `null`, `"<b>"` -> `""`).
  - `sentiment row shows the call word and a no-call chip`: `news: {predicted: 0.31, verdict: null, leans: {}, note: "scaled"}`, `news_call: "no_call"` -> includes `no call (|lean| under 0.2)` and `No call`; a `"higher"` row with `verdict: "right"` includes `calls higher` and `Right`.
  - `news brief card uses the call word, never in line`: pending CPI row, forecast 0.3, `news: {predicted: 0.3, leans: {}}`, `news_call: "higher"` -> `briefCardHtml(row, "news", DISC)` includes `hotter than consensus` and not `in line`; `pickNextRow([sameRowWith news_call "no_call"], now, "news") === null`; the tier1 brief test at ~line 131 still passes (`in line with consensus`).
  - `scoreboard shows directional-only, the News no-call count and the always-in-line baseline with n`: SB fixture with `tier1.directional {scored: 2, right: 1}`, `news {scored: 8, right: 5, no_call: 23, directional {scored: 6, right: 4}}`, `combined.directional {scored: 25, right: 15, accuracy: 0.6, accuracy_shown: true}`, `in_line_baseline {tier1: {scored: 19, right: 6}, news: {scored: 8, right: 2}, combined: {scored: 25, right: 10, accuracy: 0.4, accuracy_shown: true}}` -> includes `Directional only`, `1 of 2`, `4 of 6`, `15 of 25 (60%)`, `no call on 23 of 31 graded releases`, `Always in line (baseline)`, `6 of 19`, `2 of 8`, `10 of 25 (40%)`, and the footnote.
  - Existing scoreboard test (old SB without the new keys) still renders and still asserts its strings; add `0 of 0` for the missing directional.
- [ ] Update `info.test.js`: the unsized test asserts `News lean +0.25` and `so no number` and no longer `no news call`; add `Combined readings name the News call` (`news_call: "lower"` -> `News call: lower`; `"no_call"` -> `News call: none (|lean| under 0.2, pre-registered)`).
- [ ] Run `npm test` -> FAIL.
- [ ] Implement as in Interfaces; `stats.js` needs no change (it already passes `sub` to `pickNextRow`/`briefCardHtml` and renders `scoreboardHtml`).
- [ ] Run `npm test` -> PASS; full pytest -> PASS (known env failure only).
- [ ] Commit: `feat(B9): Stats UI shows the News call word, no-call count, directional-only accuracy and the always-in-line baseline` + Co-Authored-By line.

## Task 4 — Docs, deploy runbook and live read-only acceptance  `[mechanical]`

**Files:** `docs/superpowers/specs/2026-10-15-stats-tab-design.md` (§4.1 and the scoreboard sentence), `docs/b9-deploy.md` (new, CRLF), `docs/feature-inventory-2026-09-11.md` (B9 line), `docs/roadmap-2026-10-20.md` (status line 3).

**Steps:**
- [ ] Stats spec §4.1, after the News bullet, add (CRLF): `- **News side (pre-registered 2026-10-20, owner decision 5, B9 ST1; fixed before viewing more results, not tuned):** side = sign(n) when |n| ≥ 0.2 (NEWS_CALL_MIN_LEAN, webapp/stats_methods.py), otherwise **no call**. News never calls "in line". The scale only sizes the plotted number PN and its miss; it never decides the side. A no-call is excluded from News accuracy and counted as "no call" with n. With fewer than 3 prior releases the side still follows the lean, without a number. Combined keeps S = 0.70·s1 + 0.30·sN on the numbers, including when News abstains. Display only: no stored prediction or predicted_direction is written or changed.` In §5 (e), after "three-method scoreboard (accuracy, `k of n`, mean miss)" add `; plus, each with n (B9 ST2): directional-only accuracy (releases whose actual came in higher or lower) and an "always in line" baseline over each method's graded releases`.
- [ ] Write `docs/b9-deploy.md` modelled on `docs/b9a-deploy.md`: §1 What changes — no DB changes, no migrations, no Windows/Claude scheduled-task changes; **scoring-display change** (Stats grading of News only; nothing stored changes); `/api/stats/events` rows gain `news_call`; `/api/stats/scoreboard` gains `directional`, `news.no_call`, `in_line_baseline`; controller merges `b9-stats-honest` (no push). §2/§3 stop and start exactly one copy exactly as `docs/b11-deploy.md` §2-§3. §4 Verify — `GET /api/stats/events?event=CPI%20m/m` returns 200, every row has `news_call`, no News row reads "in line" (count `news_call` values; on 2026-10-28 data expect 2 `no_call`, 0 higher/lower); `GET /api/stats/scoreboard` has `in_line_baseline` and `methods.*.directional`; Ctrl+F5 the Stats tab: the scoreboard shows "Directional only", the News no-call line and the "Always in line (baseline)" row; **record the restart-complete time (UTC and SAST) as the B9 scoring-display change time** in the roadmap status line and the inventory row (2027-01-15 review uses post-change data only). §5 Rollback — `git revert` the merge, restart as §2-§3; no data to restore.
- [ ] Feature inventory B9 row -> `agreed; ST3-ST5 done in B9a; ST1-ST2 built on branch b9-stats-honest (not yet merged; display-only scoring change, no DB changes)`. Roadmap line 3: append `B9 (ST1+ST2) built on branch b9-stats-honest 2026-10-28 (not yet merged).` The controller marks both live after deploy.
- [ ] Live read-only acceptance (no backslashes, so a Bash heredoc is safe): from the app dir run

```bash
python - "C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine" <<'EOF'
import sqlite3, sys
from collections import Counter
from pathlib import Path
from webapp import stats_service as svc
from webapp.stats_rules import side
def ro(p):
    c = sqlite3.connect(f"file:{Path(p).as_posix()}?mode=ro", uri=True); c.row_factory = sqlite3.Row; return c
live = Path(sys.argv[1])
rows = svc.build_rows(ro(live / "webapp" / "dashboard.db"), ro(live / "scoring" / "backtest_log.db"), brent_series_fn=lambda: None)
word = {1: "higher", -1: "lower", 0: "in line"}
for label, keep in (("CPI m/m", lambda r: r.event_title == "CPI m/m"), ("all titles", lambda r: True)):
    before, after = Counter(), Counter()
    for r in rows:
        if r.status != "scored" or not keep(r) or r.news is None:
            continue
        sn = r.detail.news_surprise
        if sn is not None:
            before[word[side(r.forecast + sn, r.forecast, r.tol)]] += 1
        after[r.news_call] += 1
    print(label, "before", dict(before), "after", dict(after))
print({k: (m["scored"], m["right"], m["directional"], m.get("no_call")) for k, m in svc.build_scoreboard(rows)["methods"].items()})
print(svc.build_scoreboard(rows)["in_line_baseline"])
EOF
```

  Expected (2026-10-28 data; live data moves): CPI m/m before `{'in line': 2}`, after `{'no_call': 2}`; all titles before 25 in line / 2 higher / 4 lower (31), after 23 no_call / 2 higher / 7 lower (32 — ISM Manufacturing PMI 2026-09-01 joins as an unsized call). Paste the actual output into the final summary. Nothing is written (both connections are `mode=ro`).
- [ ] `git diff --stat ad1e8a1` lists only the files named in Tasks 1-4; full suites PASS (known env failure only); record the pytest/npm totals for the final summary.
- [ ] Commit: `docs(B9): pre-registered News rule, honest baselines, deploy runbook and status lines` + Co-Authored-By line.
