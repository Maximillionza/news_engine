# Stats tab: Brent line + deterministic nowcast capture (branch stats-oil)

Status: DONE_WITH_CONCERNS (concerns listed at the end).

## Commits
- 4285b8c feat(stats): Brent crude feed from FRED DCOILBRENTEU (fail-open, 6h cache, no lookahead helper)
- a8749bb feat(stats): serve Brent at the nowcast snapshot vs the day before release (information only)
- effcfdd feat(stats): show Brent crude (information only, 0% weight) in the CPI readings panel
- d750fda feat(stats): deterministic live nowcast capture from the Cleveland Fed JSON for the scheduler
- 2543c4e docs(stats): record the live backfill, the Brent line and the scheduled nowcast capture

## Part 1: Brent beside the nowcast
- data_layer/brent_feed.py: parse_observations (skips FRED ".", None, bad dates, non-finite or non-positive prices, sorts ascending), brent_on_or_before (latest obs <= day, never later), get_brent_series(api_key, http_get, clock) with 6h TTL cache, fail-open (no key / HTTP error / exception / bad JSON / no usable obs -> None, never raises). Same pattern as macro_backdrop: FRED_API_KEY from config.settings, requests.get on /series/observations. Extras: a failed refresh keeps serving the last good series; a failure is remembered for 5 min so a dead feed is not hammered; returns a copy of the cached list.
- stats_service: RowDetail.brent; build_rows(..., brent_series_fn=None) (None -> brent_feed.get_brent_series resolved at call time). The series is fetched lazily, at most once per build_rows, and only when a CPI-family row has a nowcast snapshot. Any lookup failure -> brent None, row intact. snapshot_price = Brent on or before the snapshot as-of date; release_price = Brent on or before release date minus one day; change_pct rounded to 2 dp.
- app.py _detail_dict serves `brent` (explicit keys). Tests: DETAIL_KEYS includes "brent", BRENT_KEYS exact set asserted, the hand-logged detail equality includes "brent": None, plus a route test for the null case. Route and service test files get an autouse fixture so no test can reach FRED.
- UI (info.js brentLine, shown for rows that have a nowcast value, both Tier 1 and Combined views): "Brent crude (information only, 0% weight): $90.00 on 2026-10-12 at the nowcast snapshot -> $92.50 on 2026-10-13 before release (+2.78%) - source FRED/EIA"; "Brent not available" when null or both prices missing; one-sided text when only one price exists. Escaped by the existing li escaping. 6 new JS tests.
- RED evidence: test_brent_feed.py collection ImportError (cannot import brent_feed); test_stats_service.py 11 failed / 39 passed before implementation (TypeError unexpected kwarg brent_series_fn, AttributeError RowDetail.brent); route tests 3 failed / 12 passed before the serializer change; info.test.js Brent assertions failed before brentLine.
- GREEN: test_brent_feed 30 passed; stats_service 50 passed; routes + service + feed 95 passed.

## Part 2: scripts/capture_nowcast_from_cleveland.py
- latest_nowcasts(json_data, release_dates) is pure. release_dates = iterable of (title, release_utc). Returns a list of dicts {event_title, release_utc, value, value_date, reason}. Reuses SERIES_MAP, SOURCE, _series, _slot_dates from cleveland_nowcast_to_csv (imported, no refactor; that module's tests stay green). Chart choice: reference month = month before the release month (year rolls over for January). Takes the last non-blank slot dated strictly before the release day. Skipped (value None + reason) when: no chart for the month, the Fed chart already shows an actual, newest value unparseable or non-finite (no fallback to an older slot), no value before the release day, malformed chart, non-CPI-family title. A non-list document raises ValueError.
- run(dash_conn, bt_conn, now, fetch=None, dry_run=False): USD only, release strictly after now and <= now+48h. Nothing due -> message "No CPI-family release within 48 hours: nothing to capture." WITHOUT calling fetch. Fetch/shape problems -> FetchError. Calls capture(..., as_of_utc=now, source="Cleveland Fed Inflation Nowcasting (CC BY 4.0)"); capture's after-release ValueError becomes a skip. Summary {"captured": [(title, release_iso, value)], "skipped": [(title, release_iso, reason)], "dry_run", "message"}.
- Default fetch: one GET, 60 s timeout, descriptive User-Agent, raise_for_status.
- CLI: --dry-run (does not even open the backtest DB), --dash-db, --bt-db. dashboard.db opened read-only via open_dash_readonly imported from backfill_tier1_reconstructed (mode=ro). Exit codes: 0 ok / nothing due, 1 fetch failure (message on stderr, nothing written), 2 a due release had to be skipped (my addition so the scheduler notices).
- Tests (34): pure parsing (last non-blank, middle blanks not zero-filled, release-day slot never used, Dec->Jan rollover, missing chart, already-released chart, unparseable / nan / inf, malformed chart, non-CPI title, non-list); run (captures both series with as_of == now and kind live; nothing due -> no fetch; exactly-48h edge included; non-USD/NULL ignored; non-CPI ignored; dry-run writes nothing and works with bt_conn None; fetch failure and wrong-shape -> FetchError and zero rows; unparseable skipped; stale skipped; lookahead refusal path; real capture() refuses after-release; same-instant rerun dedupes, later rerun adds a newer snapshot and the newer one is scored; naive now rejected); default fetch args; CLI dry-run / capture / nothing-due / fetch-failure exit 1 / exit 2 / read-only dash handle.
- RED: collection ImportError (cannot import capture_nowcast_from_cleveland from scripts). GREEN: 34 passed; cleveland_nowcast_to_csv + capture_nowcast_snapshot tests still pass (62 together).
- Not run against live DBs or the network. Only `--help` was executed on the script.

## Part 3: docs
Single-line change to the Stats row of docs/feature-inventory-2026-09-11.md (file is CRLF, preserved; git diff shows 1 line changed). Backfill sentence now says applied to live 2026-10-15 with the backup path; added "Brent line (built)" and "Scheduled capture (wired)" (run daily by a Claude scheduled task); script list extended; removed the Brent known-gap and the scheduled-capture known-gap; reworded the brief-card gap that depended on scheduled capture. It also states that gasoline is NOT shown (the spec said "Brent / gasoline"; the owner asked only for Brent).

## Verification
- pytest: `1062 passed, 1 deselected, 1 warning in 133.97s (0:02:13)` (with the specified --deselect). Without the deselect, test_combined_builder_includes_alpha_vantage_when_key_present fails (pre-existing, unrelated).
- node: tests 125 / pass 121 / fail 4; the 4 failures are exactly calendar/render, dashboard/card, dashboard-poll, symbol-picker.

## Deviations and concerns
1. Existing test seam changed: test_one_failing_row_degrades... monkeypatches `_build_one` with a fixed 5-arg signature; I added `brent_series=None` to its stub because `_build_one` now takes a sixth argument.
2. Snapshot-price cap: the snapshot lookup date is min(as-of date, release date - 1). A live snapshot stamped on the release day itself would otherwise read the release-day price. Slight departure from the literal "on or before the snapshot as-of date"; tested.
3. Staleness guard (not in the brief): run() skips a Fed value dated more than 5 days before now (or more than 1 day in the future), because the snapshot is stamped as of the fetch time. Skipped releases make the CLI exit 2.
4. [Guessing] The real unreleased chart has an all-blank "Actual" series and no release marker (as in the Phase 0 description and the October fixture); I key the chart by reference month (release month - 1) instead of locating a release marker. Irregular releases where CPI is not published in the following month would be skipped with "no chart" rather than mis-matched. The first live run should be `--dry-run` to confirm the real file has the expected chart.
5. brent_feed fetches observations from 2025-12-01 onward (no limit); if the stats history ever starts earlier, OBSERVATION_START needs moving.
6. The default stats routes call the real feed (cached 6 h, 10 s timeout) the first time a request touches a CPI row with a snapshot, so the first Stats load after a restart can wait up to 10 s if FRED is slow. It needs FRED_API_KEY in the live environment, otherwise the line says "Brent not available".
7. The spec header (2026-10-15-stats-tab-design.md) still lists the Brent line and scheduled capture as "Not built"; not touched (outside the brief).
8. Working tree is CRLF (autocrlf); existing files kept CRLF; new files written LF (git will warn).

## Fix round (coordinator review follow-ups)

Commits:
- 0e9a919 fix(stats): capture script confirms the chart belongs to the release and treats null slots as blank
- 387c24e fix(stats): one shared Brent fetch for concurrent callers; never log the FRED URL or key
- 0c4b0a9 fix(stats): chart and scoreboard routes skip Brent; a malformed series degrades only the Brent line
- 614a270 docs(stats): scheduled capture is built, not yet registered; spec header lists the Brent line and capture script as built

1. Chart selection (capture script). After month arithmetic picks the chart: reads Actual series first (non-blank anywhere -> skip "already shows an actual (marked D, ours R)", reusing the converter's idea of finding the release day from the Actual slot); then requires first date label <= release day, release day <= last label + 45 days (MAX_DAYS_PAST_CHART), and at least one non-blank value in the series being read. Each failure is a skip with a reason, so the CLI exits 2. Blank = None, "", "None" (any case), whitespace, applied to nowcast and actual series. 12 new tests (delayed release beyond 45 days skipped; exactly 45 accepted; chart starting after the release skipped (via patched _slot_dates, since month arithmetic makes it otherwise unreachable); all-blank / all-None; None vs "" vs "None" vs " " trailing slots; None in Actual not counted as released; released chart reason names the marked date). RED: 9 failed before the change. The existing Dec->Jan rollover test is kept. Fixture note: my SEP test chart had labels that did not start in its reference month (previously masked because the Actual check ran first); fixed.
2. Brent fetch. brent_feed holds a lock across cache check + fetch, so concurrent callers share one request (test: 4 barrier-synchronised threads, 1 request). /api/stats/chart and /api/stats/scoreboard pass brent_series_fn=lambda: None (test: neither calls the Brent source, events still does). RED: 3 failed before.
3. Logging. brent_feed prints only type(exc).__name__ and the HTTP status when present; tests prove neither the key nor the URL appears (ConnectionError with the URL in its message; HTTP error with response.status_code 500). macro_backdrop untouched.
4. _build_one wraps _brent_detail in try/except (logger.warning, brent=None). Test with four garbage series ([None], bad tuple types, 3-tuple, a string): row stays scored and Tier 1 intact.
5. Docs. Stats row (CRLF, 2 small phrase edits): "Scheduled capture (script built and tested; scheduling not yet registered)" with "to be registered by the owner-approved scheduler update; the first run must be --dry-run"; brief-card gap now says the capture script supplies a nowcast once scheduled. Spec header (CRLF): "Built since: the Brent line ... and the deterministic capture script ... (registering it as a scheduled task is still pending). Not built: the Tier 1 Source filter ... and the workbook indicator lists ...".

Line endings: a test file I appended to with a shell heredoc (test_app_stats_routes.py, CRLF) was normalised back to CRLF; git diff is clean.

Verification:
- pytest (exact command): `1082 passed, 1 deselected, 1 warning in 103.68s (0:01:43)`
- node (all webapp JS tests): tests 125 / pass 121 / fail 4 (same 4 known jsdom files; stats JS tests all pass).
- Capture script not run against the network or any live DB.
