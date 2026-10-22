# B9a — Implementation Plan

**Goal:** Four display-only Stats fixes: an honest chart when a method has no calls (and grey, not red, for pending calls), correct pre-12-Aug wording, an informational Tier 1 vs News agree/disagree chip on Combined rows, and a label saying which Tier 1 tier (formula / market-implied / judgment) produced each row's Tier 1 call.

**Architecture:** Two new `StatsRow` fields (`agreement`, `tier1_tier`) are computed in `webapp/stats_service.py::_build_one` from values the row already has (both `MethodCall.side` values; the snapshot-vs-hand-logged branch and the hand-logged row's `source`), serialized by `webapp/app.py::_stats_row_dict`, and rendered by the pure string builders in `webapp/static/js/stats/rows.js`. The chart fix is confined to `buildChartSvg` in `webapp/static/js/stats/chart.js`; the wording fix is string-only. Nothing in `_call`, `combine`, `build_chart`, `build_scoreboard`, verdicts or counts changes.

**Spec reference:** `docs/roadmap-2026-10-20.md` §B9 items ST3, ST4, ST5 and §B12 item T12, pulled forward as B9a under the owner's smaller-task rule. Owner decision 2026-10-20: Combined gets an INFORMATIONAL agree/disagree marker; 70/30 unchanged; never a "conflicting" status. ST1/ST2 (scoring) stay in B9 after B8 and are out of scope.

**Verified source facts (2026-10-22, base 9a4367e):**
- Stats Tier 1 call comes from exactly two places in `_build_one` (stats_service.py ~299-327): (a) `get_scored_nowcast_snapshot` for titles in `NOWCAST_EVENTS` (= `tier1_titles(TIER1_FORMULA)`, the Cleveland nowcast, kinds live/reconstructed); else (b) `_hand_logged_tier1_before` reading `tier1_predictions` (selects `source`; `source` is `NOT NULL` in the schema). A tracked title with neither has `tier1 = None`. So: snapshot -> `"formula"`; hand-logged -> `tier1_row_tier(source)` (same helper and rule as `predictions_service._tier1_prediction_dict`, so a pre-B3 LLM CPI row reads `judgment`); no call -> `None`. `"market_implied"` has no writer yet (B12 T10); the UI still maps it.
- Live DB (read-only, mode=ro): `tier1_nowcast_snapshots` holds only `reconstructed` CPI/Core CPI rows; `tier1_predictions` holds 5 distinct hand-researched sources (incl. two pre-B3 "Cleveland Fed Inflation Nowcasting tool..." LLM rows, which are judgment by the helper).
- The rows route is `/api/stats/events` (the spec's "/api/stats payload"); its key-set test is `tests/test_app_stats_routes.py::ROW_KEYS` / `CALL_KEYS`.
- `MethodCall.side` is deliberately not served (app.py comment above `_method_dict`); this plan keeps it that way and serves only the derived `agreement`.

## Global Constraints

- Display-only: no change to any call, verdict, accuracy, scoreboard count, 70/30 weight, alerting or DB schema.
- `/api/stats/events` rows gain exactly `agreement` and `tier1_tier`; `CALL_KEYS`, `DETAIL_KEYS` and every existing value unchanged.
- The words "conflict" / "conflicting" never appear in the Stats UI strings added here.
- A 0 ("in line") side or a missing side is never a disagreement (same rule as `webapp/conflict.py`).
- `tier1_tier` is None whenever the row has no Tier 1 call; never inferred from the title alone.
- Keep CRLF in every touched file (all targets are CRLF); vanilla ES modules + `node --test`; type hints on Python signatures.
- Never touch the live worktree, live DBs, scheduled tasks or Telegram; never push.
- Tests: `python -m pytest -q -p no:warnings` and `npm test` from the app dir; only `tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present` may fail (no `.env` in the worktree).

## Review Focus

- **Agreement treats in-line as disagreement** (side 0 vs ±1) -> pinned by `test_agreement_rule_truth_table` (Task 2).
- **New fields leak into scoring** (scoreboard or combined call differs) -> `test_agreement_and_tier_do_not_change_combined_or_scoreboard` (Task 2).
- **Guessed tier label** (e.g. "formula" for a CPI row with no snapshot, or a label on a no-call row) -> `test_tier1_tier_follows_the_source_actually_used` (Task 2) and `tier tag is absent when tier1_tier is null` (Task 3).
- **Payload drift** (extra or renamed keys, method dict gains `side`) -> updated `ROW_KEYS` + unchanged `CALL_KEYS` in `test_events_route_serves_every_field_the_tab_renders` (Task 2).
- **Pending call still red / no-calls chart silent** -> `pending (null-verdict) dots and segments are grey` and `a method with no calls keeps forecast and actual and says so` (Task 1).
- **"conflict" wording sneaks in** -> `agreement chip never uses the word conflict` (Task 3).
- **Old disclaimer string survives somewhere** -> grep step in Task 1.

---

## Task 1 — ST3 chart + ST4 wording  `[mechanical]`

**Files:** `webapp/static/js/stats/chart.js`, `webapp/static/js/stats/chart.test.js`, `webapp/static/js/stats/rows.js` (line ~132 only), `webapp/static/js/stats/rows.test.js` (lines ~82, ~325), `webapp/app.py` (`STATS_DISCLAIMERS["pre_news"]`), `webapp/stats_service.py` (`NEWS_START_UTC` comment), `tests/test_app_stats_routes.py` (line ~89).

**Interfaces:**
- `chart.js`: new module constants `GREY = "#9e9e9e"` and `METHOD_NAME = { tier1: "Tier 1", news: "News sentiment", combined: "Combined" }` (the sub-tab button labels in `webapp/static/index.html`). `buildChartSvg(chart, opts)` signature unchanged.
- `STATS_DISCLAIMERS["pre_news"] = "No news predictions exist for releases before 12 Aug 2026. Combined for these months is Tier 1 only."`
- `sentimentRowHtml` pre-news text: `"No news predictions before 12 Aug 2026"`.
- `NEWS_START_UTC` comment: `# first release day with a news prediction (articles exist from 2026-08-10)`. Value unchanged.

**Steps:**
- [ ] Add failing tests to `chart.test.js`:
  - `a method with no calls keeps forecast and actual and says so`: `buildChartSvg({ method: "news", unit: "%", points: pts.map(p => ({ ...p, predicted: null, verdict: null })) })` contains `data-line="forecast"`, `data-line="actual"`, zero `data-predicted`, and `No News sentiment calls for this selection`; same with `method: "tier1"` -> `No Tier 1 calls for this selection`.
  - `pending (null-verdict) dots and segments are grey`: points `[{predicted:0.4, verdict:"right"}, {predicted:0.5, verdict:null}]` (plus forecast/actual/label) -> the `data-predicted="seg"` line and the second `data-predicted="dot"` use `#9e9e9e`; no `#c62828` anywhere.
  - Existing `right segments are green and wrong segments are red` still passes unchanged.
- [ ] Update the old-string assertions: `rows.test.js` lines ~82 and ~325 to `"No news predictions before 12 Aug 2026"`; `tests/test_app_stats_routes.py` ~89 to the new `pre_news` text.
- [ ] Run `npm test` and `python -m pytest -q -p no:warnings tests/test_app_stats_routes.py` -> FAIL.
- [ ] Implement: in `buildChartSvg` replace both `verdict === "right" ? GREEN : RED` with a local `colourFor(verdict)` returning GREEN for `"right"`, RED for `"wrong"`, GREY otherwise. After the SVG is closed, if `pts.every(p => p.predicted == null)` append `<div class="meta-text-sm">No ${escapeHtml(METHOD_NAME[chart.method] || "predicted")} calls for this selection</div>`. The empty-points message stays as is. Update the header comment (grey = pending). Change the three strings above.
- [ ] `git grep -n "No news articles exist\|No articles before"` returns nothing outside `docs/` history.
- [ ] Run both suites -> PASS (known alpha_vantage failure excepted).
- [ ] Commit: `feat(B9a): ST3 no-calls chart note and grey pending calls; ST4 pre-12-Aug wording` + Co-Authored-By line.

## Task 2 — ST5 + T12 server fields  `[integration]`

**Files:** `webapp/stats_service.py`, `webapp/app.py` (`_stats_row_dict`), `tests/test_stats_service.py`, `tests/test_app_stats_routes.py`.

**Interfaces:**
- `stats_service.agreement_for(tier1_side: Optional[int], news_side: Optional[int]) -> Optional[str]`: `"agree"` when both non-zero and equal, `"disagree"` when both non-zero and different, else `None`.
- `StatsRow` gains, after `impact_bucket` (defaults keep every positional constructor valid):
  - `agreement: Optional[str] = None   # 'agree' | 'disagree' | None; informational only, never read by scoring`
  - `tier1_tier: Optional[str] = None  # TIER1_FORMULA | TIER1_MARKET_IMPLIED | TIER1_JUDGMENT of the call actually used; None = no Tier 1 call`
- Import `tier1_row_tier` alongside the existing `data_layer.tier1_events` import.
- `_stats_row_dict` adds `"agreement": r.agreement, "tier1_tier": r.tier1_tier`. `_method_dict` unchanged (side stays unserved).

**Steps:**
- [ ] Add failing tests to `tests/test_stats_service.py`:
  - `test_agreement_rule_truth_table` (parametrized): `(1,1)->"agree"`, `(-1,-1)->"agree"`, `(1,-1)->"disagree"`, `(-1,1)->"disagree"`, `(0,1)`, `(1,0)`, `(0,0)`, `(None,1)`, `(1,None)`, `(None,None)` -> `None`.
  - `test_tier1_tier_follows_the_source_actually_used`: (a) CPI m/m with a `record_nowcast_snapshot(..., "cleveland", "reconstructed")` -> `tier1_tier == "formula"`; (b) PPI m/m with `record_tier1_prediction(..., source="BLS", ...)` (as in `test_hand_logged_tier1_direction_is_scored_by_side_when_there_is_no_nowcast`) -> `"judgment"`; (c) CPI m/m with NO snapshot but a hand-logged row whose source is `TIER1_FORMULA_SOURCE` -> `"formula"`, and with any other source -> `"judgment"`; (d) CPI m/m with neither -> `tier1_tracked is True and tier1 is None and tier1_tier is None`; (e) untracked title -> `None`; (f) not-scoreable row -> `agreement is None and tier1_tier is None`.
  - `test_row_agreement_uses_both_sides`: build a row with a nowcast snapshot and a news call (seed prior prints for scale + a `record_print_prediction_if_changed` call, as the `full_client` fixture in `tests/test_app_stats_routes.py` does); assert the fixture precondition `row.tier1.side != 0 and row.news.side != 0`, then `row.agreement == svc.agreement_for(row.tier1.side, row.news.side)`; and a row with `news is None` -> `agreement is None`.
  - `test_agreement_and_tier_do_not_change_combined_or_scoreboard`: on the rows from the previous fixture, `svc.build_scoreboard(rows) == svc.build_scoreboard([replace(r, agreement=None, tier1_tier=None) for r in rows])`; each row's `combined` equals the `_call(...)` of `forecast + combine(s1, sn).surprise` (i.e. `row.combined.surprise == row.detail.combined_surprise == 0.7*s1 + 0.3*sn` to 1e-12); and `build_chart(rows, "combined")` is identical for both lists.
- [ ] In `tests/test_app_stats_routes.py`: `ROW_KEYS` gains `"agreement", "tier1_tier"`; `test_events_route_serves_every_field_the_tab_renders` asserts `row["tier1_tier"] == "formula"` and `row["agreement"] is None` (news is None there), and `set(row["tier1"]) == CALL_KEYS` (unchanged, no `side`); `test_events_route_serves_real_news_and_combined_calls` asserts `row["agreement"] in ("agree", "disagree")` and the existing combined/scoreboard values it already pins are untouched.
- [ ] Run pytest on both files -> FAIL.
- [ ] Implement in `_build_one`: a local `tier1_tier: Optional[str] = None`; set `TIER1_FORMULA` in the snapshot branch (the snapshot IS the Cleveland formula input; `NOWCAST_EVENTS` is defined from `TIER1_FORMULA`), `tier1_row_tier(logged["source"])` in the hand-logged branch, leave None otherwise. After `news` is built: `agreement = agreement_for(None if tier1 is None else tier1.side, None if news is None else news.side)`. Pass both as keywords to the final `StatsRow(...)`. Add `agreement_for` near `_call` with a docstring citing the conflict.py neutral rule and the owner decision (informational; Combined stays 70/30). Leave `_not_scoreable` positional (defaults give None).
- [ ] Update the module comment above `_method_dict` in app.py: side is still not served; `agreement` is the only thing derived from it.
- [ ] Run full pytest -> PASS; `npm test` -> PASS.
- [ ] Commit: `feat(B9a): serve informational Tier 1/News agreement and Tier 1 tier on Stats rows` + Co-Authored-By line.

## Task 3 — ST5 + T12 rendering  `[mechanical]`

**Files:** `webapp/static/js/stats/rows.js`, `webapp/static/js/stats/rows.test.js`.

**Interfaces (rows.js):**
- `export const TIER_LABEL = { formula: "formula", market_implied: "market-implied", judgment: "judgment" };`
- `export function tierTag(row)` -> `' <span class="meta-text-sm tier-tag">' + label + '</span>'` when `TIER_LABEL[row.tier1_tier]` exists, else `""`.
- `export const AGREEMENT_TITLE = { agree: "Tier 1 and News point the same way", disagree: "Tier 1 and News point opposite ways; informational only, Combined is still 70/30" };`
- `export function agreementChip(agreement)` -> `` ` <span class="chip chip-none" title="${escapeHtml(AGREEMENT_TITLE[a])}">${a}</span>` `` for `"agree"` / `"disagree"`, else `""`. `chip-none` is the existing neutral chip (same as the reconstructed tag); no CSS change.
- `tier1RowHtml`: append `tierTag(row)` inside the Tier 1 call cell (the `<td>` holding `predicted`, before the leans div). Not added to not-scoreable / not-tracked rows.
- `combinedRowHtml`: Tier 1 cell becomes `cell(row.tier1) + (row.tier1 ? tierTag(row) : "")`; Combined cell appends `agreementChip(row.agreement)` after `flag` when `row.tier1_tracked`.

**Steps:**
- [ ] Add failing tests to `rows.test.js`:
  - `tier tag shows the served tier`: `tier1RowHtml({...tracked, tier1_tier: "formula"})` includes `>formula<`; `combinedRowHtml({...combinedBase, tier1_tier: "market_implied"})` includes `>market-implied<`; `"judgment"` -> `>judgment<`.
  - `tier tag is absent when tier1_tier is null`: no `tier-tag` for `tier1_tier: null` or an unknown value such as `"guess"`.
  - `agreement chip renders agree and disagree with their tooltips`: `combinedRowHtml({...combinedBase, agreement: "agree"})` includes `>agree<` and `title="Tier 1 and News point the same way"`; `"disagree"` includes `>disagree<` and `title="Tier 1 and News point opposite ways; informational only, Combined is still 70/30"`.
  - `no agreement chip when agreement is null`: output equals the same row's output from before (compare against `combinedRowHtml` with `agreement` deleted) and contains no `>agree<`/`>disagree<`.
  - `agreement chip never uses the word conflict`: `/conflict/i` matches none of the agree/disagree outputs nor `Object.values(AGREEMENT_TITLE)`.
  - `the combined call cell is unchanged by the marker`: the substring for the Combined call (`num(predicted)` + verdict chip) is present and identical with `agreement` set or null.
- [ ] Run `npm test` -> FAIL.
- [ ] Implement as in Interfaces; keep CRLF.
- [ ] Run `npm test` and full pytest -> PASS.
- [ ] Commit: `feat(B9a): Stats rows show Tier 1 tier and an informational agree/disagree chip` + Co-Authored-By line.

## Task 4 — Docs  `[mechanical]`

**Files:** `docs/feature-inventory-2026-09-11.md`, `docs/roadmap-2026-10-20.md`, new `docs/b9a-deploy.md` (CRLF, matching `docs/b11-deploy.md`).

**Steps:**
- [ ] Feature inventory roadmap table (~line 52, 55): B9 row status becomes `agreed; ST3-ST5 done in B9a; ST1-ST2 pending after B8`; B12 row status becomes `agreed, not started; T12 done in B9a`.
- [ ] Roadmap status line (line 3): append ` B9a (B9 ST3-ST5 + B12 T12) built on branch b9a-stats-display.`
- [ ] Write `docs/b9a-deploy.md`, sections: **1. What changes** — no DB changes, no migrations, no Windows or Claude scheduled-task changes; merge `b9a-stats-display` into `news-engine/batch-predictions-queries` in the live worktree (controller; no push). **2-3. Restart** — "Stop the single engine copy and start exactly one copy exactly as `docs/b11-deploy.md` sections 2-3" (reference, not a copy). **4. Verify** — `GET http://localhost:5001/api/stats/events` returns 200 and each row has `agreement` and `tier1_tier` keys (CPI rows from reconstructed snapshots show `tier1_tier` "formula"); hard-refresh the Stats tab (Ctrl+F5): a CPI Tier 1 row shows "formula", the pre-12-Aug notice reads the new wording, the News sub-tab chart for a title with no news calls shows "No News sentiment calls for this selection". **5. Rollback** — `git revert` the merge, restart as in section 2-3; no data to restore.
- [ ] Full pytest + `npm test` -> PASS.
- [ ] Commit: `docs(B9a): inventory, roadmap status and deploy runbook` + Co-Authored-By line.
