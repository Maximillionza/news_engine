# ACT — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every numeric USD release gets its actual from the official publisher within 15 minutes of its release time, automatically, with a visible alarm when that fails, plus a fill of the 3-month backlog (USD rows since 2026-07-28 with no actual).

**Architecture:** A new package `data_layer/official_actuals/` holds one small adapter per publisher (BLS, BEA, Census, EIA, Fed, TreasuryDirect, plus FRED for weekly claims), all calling HTTP through one injectable fetcher, and one registry (`OFFICIAL_SPECS`: FF title -> source, series, transform, FF formatting, release time, period rule). A gate script compares each title's official values with what is stored in `event_history` (live, read-only) and commits the per-title result to `gate_results.json`; only `verified` titles are polled. `webapp/release_poller.py` runs on its own daemon thread, started by `start_scheduler()`, polls due rows (60 s to T+15 min, 5 min to T+2 h, one catch-up pass after start or wake) and writes first-writer-wins through `store.fill_actual_if_missing`; `ops/health.py` gains an `actuals_sla` item that feeds the existing once-a-day notice, and the cloud web-fallback path is removed.

**Tech Stack:** Python 3.14, requests, sqlite3, Flask, vanilla ES modules, pytest, `node --test`.

**Spec reference:** `docs/roadmap-2026-10-20.md` §ACT (the section is added by Task 6; it does not exist yet), plus the owner decisions of 2026-10-28: actuals from the official publisher within 15 min of the release; do not reduce any existing polling (FRED fast path and hourly B8 backfill stay); no Forex Factory site access; FF stays the calendar (titles, times, forecasts); 3-month backlog; visible alarm folded into the daily health notice; retire the web fallback.

**Verified live facts (2026-10-28 15:00-18:20 UTC, read-only GETs/POSTs, live `dashboard.db` opened mode=ro):**
- Live `.env` has `BLS_API_KEY`, `BEA_API_KEY`, `EIA_API_KEY`, `CENSUS_API_KEY`, `FRED_API_KEY` (names only checked). The worktree has no `.env`, so live runs pass `--env-file`.
- **BLS v2** (one POST, 15 series, `calculations: true`): every id below resolves. Latest: `CES0000000001` M09 159044 (M08 159015, net change 29), `LNS14000000` 4.2, `CES0500000003` pct1 0.1, `CUSR0000SA0` pct1 0.6, `CUUR0000SA0` pct12 3.7, `CUSR0000SA0L1E` pct1 0.3, `CUUR0000SA0L1E` pct12 2.6, `WPSFD4` pct1 1.3, `WPSFD49104` pct1 0.7, `EIUIR` pct1 1.1, `JTS000000000000000JOL` M08 7079, `CIS1010000000000Q` Q02 0.9, `PRS85006092` Q02 1.4, `PRS85006112` Q02 1.2. These equal the stored FF-era actuals (CPI 0.6% / 3.7%, core 0.3% / 2.6%, PPI 1.3%, core PPI 0.7%, import prices 1.1%, NFP 29K, AHE 0.1%, UR 4.2%, JOLTS 7.08M). BLS returns `pct_changes` for every observation; it computes no net changes for CPI/PPI (harmless).
- **BEA NIPA**: `T10101` line 1 `A191RL` 2026Q2 2.2; `T10107` line 1 `A191RV` 6.1; `T20807` line 25 `DPCCRGM` 2026M08 0.2; `T20600` line 1 `A065RC`, line 29 `DPCERC` (levels, commas in `DataValue`). BEA echoes the key in `Request.RequestParam` (USERID): fixtures must be scrubbed.
- **GDP revision trap:** ALFRED `A191RL1Q225SBEA` shows Q2 first print 1.5 (2026-07-30), revised to 2.2 on 2026-09-30, but FF's Advance GDP row for 2026-10-29 still says previous `1.5%`. A revision-blind gate would wrongly disable GDP; the gate below explains revisions with ALFRED vintages.
- **Census EITS**: with the key, `marts`, `resconst`, `ressales`, `mtis`, `ftd`, `vip` return JSON; `advm3` needs `for=us:*`; without a key every program returns an HTML page titled `Missing Key`. Programs that exist (from `/data/timeseries/eits.json`): `marts`, `advm3`, `m3`, `resconst`, `ressales`, `vip`, `mtis`, `mwts`, `mwtsadv`, `ftdadv`, `ftd`. Confirmed codes: `marts` `44X72`/`44Y72` `MPCSM` SA, `mwts` `42` `MPCIM`. Rows carry several geographies (`resconst`, `ressales`), so the adapter must keep US-level rows only. **The key is active now**, contrary to the brief; the adapter still fails open.
- **EIA v2**: `petroleum/stoc/wstk` `WCESTUS1` 2026-10-23 410625, 10-16 412517 (MBBL), so the change is -1.9M; `natural-gas/stor/wkly` `NW2_EPG0_SWO_R48_BCF` 10-16 3644, 10-09 3567, so 77B, equal to FF's previous on the 2026-10-29 row.
- **Fed**: `https://www.federalreserve.gov/feeds/press_monetary.xml` lists "Federal Reserve issues FOMC statement" at `monetary20261028a.htm`, pubDate 18:00 GMT; the page says "target range for the federal funds rate at 3-3/4 to 4 percent" (upper 4.00%, FF forecast `4.00%`). The 2026-09-16 page has `<strong> </strong>` inside the phrase, so tags must be stripped before parsing.
- **TreasuryDirect** `TA_WS/securities/auctioned?format=json&type=Note&days=N`: the auction date field is `competitiveAuctionCloseDate`; FF's "10-y Bond Auction" includes reopenings (`securityTerm` "9-Year 11-Month", `originalSecurityTerm` "10-Year") and excludes TIPS (`type` "TIPS"). 2026-09-09: 4.834 / 2.71 equals FF previous `4.83|2.7`; 2026-10-07: 5.300 / 2.77, posted 13:04 ET.
- **DOL claims does not work as a release-time source**: the national XML report (`oui.doleta.gov/unemploy/wkclaims/report.asp`, POST level=us) has SA initial claims only through week ending 2026-09-26 on 2026-10-28 (FF has printed three later weeks). `ar539.csv` is state-level NSA, last modified Tue 2026-10-27, and `dol.gov/ui/data.pdf` returns 403. Claims therefore use FRED `ICSA` inside the poller (source `fred`), which the brief allows as the fallback.
- **Live backlog** (USD, since 2026-07-28, released by 16:00Z): 191 rows with no actual across 78 title/impact groups. Speeches, FOMC Statement/Press Conference/Projections/Minutes, Beige Book, Monetary Policy Report and President/Treasury Secretary speeches have no number. Federal Funds Rate 2026-10-28 18:00Z is still empty while the Fed page already shows 4.00%.
- `event_history` holds 0 FF-sourced actuals (`source='live'` rows never have one); stored actuals come from `fred` (126), `seeded` (64) and `live_web_fallback` (20). The gate's references are therefore those stored actuals plus FF's own `previous` strings.
- **Web fallback:** the cloud routine is not in `RemoteTrigger list` (two routines: "Gold xauusd pre new york session check" and "Daily premarket brief", both disabled) or in `C:\Users\Masoodt\.claude\scheduled-tasks` (eight tasks, none about actuals). The local half (`start_actuals_sync`, which pushes to GitHub every 30 min) still runs in the engine.
- Pointer test `tests/test_b8_deploy_doc.py` pins `webapp/actuals_sync.py:40`, `webapp/store.py:34`, `webapp/store.py:623-649`, `webapp/app.py:147`, `webapp/scheduler.py:205-209` and `config/settings.py:153/443`. All files touched here are CRLF.

## Choices made in this plan (owner can veto before Task 1)

- **Gate with revision explanation.** Official APIs (except FRED/ALFRED) return only today's revised numbers, so comparing them with first prints stored months ago fails for revised series (NFP, GDP). For each title the gate compares, for every released USD row since 2026-01-01, the official value for the row's period with the stored actual (stored actuals written by the new publisher sources are skipped), and the prior period's value with FF's `previous`. A mismatch counts as agreement only when the title's FRED twin series, read **as of that row's release date** (ALFRED vintage; `previous` also as of the day before), formats to the stored string, **and** the official series equals the twin's current values over the last 6 periods (identity check). `verified` = at least 2 comparisons and agreement >= `VERIFY_AGREEMENT_THRESHOLD` (0.8, imported from `scripts/seed_fred_history.py`). A title without a twin is compared revision-blind (Fed, Treasury, EIA natural gas, ECI, prelim wholesale and advance goods trade until a twin is verified).
- **Period rule, not "latest value".** A row's reference period is computed from its release date (`expected_period`). The poller writes only when the official data contains that exact period, so a stale API never produces a write. Delayed or two-period releases fail closed (no write, SLA alarm).
- **Backlog and catch-up never relabel a revision as a first print.** A row older than a later release of the same series is filled only for series that are not revised (Fed, Treasury, EIA weekly stocks), and only if the value also matches FF's `previous` on the next release. Other older rows are reported as "revised since release" and left to the FRED/ALFRED backfill. The latest release of a series is filled with today's value (which is still the first print, apart from a benchmark revision; noted in the deploy doc).
- **SLA colour.** `actuals_sla` is red when any overdue row has a reason other than `proprietary`. An overdue row with only `proprietary` reasons makes it amber (listed, but no daily Telegram notice for gaps that can never be fixed for free). One constant, `SLA_PROPRIETARY_STATUS = "amber"`, switches this to red. Not-mapped titles (official data, no adapter in ACT: Industrial Production, Capacity Utilization, Consumer Credit, Federal Budget Balance, HPI, Current Account, TIC) are red, as the brief asks.
- **Claims via FRED in the poller** (source `fred`), because DOL's machine-readable data lags by weeks. FRED is polled at 60 s / 5 min for the claims row only; the FRED fast path and hourly backfill stay unchanged.
- **Gate result is a committed file** (`data_layer/official_actuals/gate_results.json`), produced by a read-only live run in Task 2 and reviewed like code; the engine never runs the gate. Re-running it is a controller step (documented).
- `scripts/fill_missing_actuals.py` stays as the manual tool for proprietary releases; `--list` switches to the new missing-numeric listing. `FillReport` stays there (`webapp/actuals_backfill.py` imports it).
- Keys are read in `data_layer/official_actuals/keys.py` (after `import config.settings`, which runs `load_dotenv()`), not in `config/settings.py`, so B12's edits there cannot conflict and the B8 line pointers stay valid.
- The `cloud_web_fallback` provenance label stays in `webapp/history.py` and the History badge (it describes data, not the queue; 0 such rows exist).

## Global Constraints

- Never write an actual that the publisher has not published; a missing period, a source error or an unparseable value means no write.
- Every write goes through `store.fill_actual_if_missing` (only rows with `actual IS NULL`); never overwrite an existing actual; never touch forecast, previous, impact or country.
- `surprise_direction` = `classify_surprise()` against the stored FF forecast; never set or invent a predicted direction.
- FF stays the calendar: titles, times and forecasts come only from FF rows. Never fetch forexfactory.com or any bot-protected site.
- Do not reduce existing polling: the FRED fast path (`webapp/scheduler.py:205-209`), the hourly B8 backfill and the adaptive FF interval are unchanged.
- No new Windows or Claude scheduled task; the poller is a daemon thread inside the engine.
- Keys come only from `.env` (or `--env-file`); never print, log, commit or embed a key, also not in fixtures or error messages (errors carry the exception class name only).
- Live DB access in this batch is read-only (`mode=ro`); never touch `.worktrees/news-engine-live`, live DBs, scheduled tasks or Telegram; never push.
- Do not touch B12 files: `data_layer/tier1_events.py`, `data_layer/kalshi_feed.py`, `scripts/capture_tier1.py`, Tier 1 capture scripts, `docs/tier1-methodology.md`.
- 70/30, Stats rules, shock alerts and Market reaction unchanged; no ACE/EA/MT5 material.
- Owner-facing times in SAST (UTC+2); stored values UTC ISO. Keep CRLF in CRLF files. Type hints on every Python signature.
- Tests use temp DBs, recorded fixtures and mocks only; `tests/conftest.py` blocks the poller thread and blanks the new keys.
- Write any Python edit script that contains backslashes with the Write tool (the Bash heredoc halves them); check regexes for a stray `\b` -> 0x08.

## Review Focus

- **Stale data written as the new print** (API still shows last month before publication). Pinned by Task 2 `test_decide_fill_waits_when_expected_period_absent` and Task 3 `test_tick_writes_nothing_before_publication`.
- **Overwrite or fabrication** (an existing actual changed, a value invented when the source failed). Pinned by Task 3 `test_tick_never_overwrites_existing_actual` and `test_tick_writes_nothing_on_source_error`.
- **Revised value stored as a first print** (backlog or catch-up on an older row). Pinned by Task 2 `test_decide_fill_skips_older_row_of_revised_series` and Task 5 `test_backlog_reports_revised_since_release`.
- **Format drift** (decimals, K/M/B scale, sign, auction pair). Pinned by Task 2 `test_format_like_matches_ff_strings` (exact strings `29K`, `7.08M`, `-1.9M`, `77B`, `4.00%`, `5.30|2.8`, `0.0%`).
- **Gate false negative on revisions / false positive on scale errors.** Pinned by Task 2 `test_gate_explains_gdp_revision_with_alfred_vintage` and `test_gate_marks_wrong_scale_suspect`.
- **Polling stalls inside the 15-minute window under 429/5xx.** Pinned by Task 3 `test_backoff_never_exceeds_fast_cadence_inside_15_minutes`.
- **Wake/restart catch-up runs once, not every tick.** Pinned by Task 3 `test_catch_up_polls_missed_release_once_after_wake`.
- **Key leakage** through fixtures or error text. Pinned by Task 1 `test_errors_never_carry_url_or_key` and `test_fixtures_carry_no_key_material`.
- **Census key inactive takes the poller down.** Pinned by Task 1 `test_census_missing_key_page_raises_key_inactive` and Task 4 `test_sla_reason_key_inactive`.
- **Alarm noise / silence.** Pinned by Task 4 `test_sla_proprietary_only_is_amber` and `test_sla_red_lists_title_time_minutes_and_reason`.
- **Provenance mislabelled `live` in History.** Pinned by Task 3 `test_history_keeps_publisher_source`.
- **A test reaching the network or starting the thread.** Pinned by Task 3 `test_conftest_disables_poller`.
- **Doc pointer test broken by line shifts.** Pinned by Task 4's updated `tests/test_b8_deploy_doc.py` (runs in the full suite).

## Task 1 — Official source adapters  `[judgment]`

**Files:** create `data_layer/official_actuals/__init__.py`, `http.py`, `keys.py`, `bls.py`, `bea.py`, `census.py`, `eia.py`, `fed.py`, `treasury.py`, `fred_current.py`, `scripts/record_official_fixtures.py`, `tests/fixtures/official_actuals/*` (recorded), `tests/test_official_adapters.py`; modify `.env.example` (add the four key names with empty values and one comment line each).

**Interfaces:**
```python
# http.py
USER_AGENT = "news-engine/ACT official-actuals poller"
@dataclass(frozen=True)
class HttpResponse: status: int; text: str; headers: dict[str, str]
class SourceError(RuntimeError): ...                 # message never contains a URL, query or key
class SourceTransportError(SourceError): ...         # no HTTP answer (timeout, DNS, reset)
class SourceRateLimited(SourceError):                # HTTP 429 or 5xx
    def __init__(self, message: str, retry_after_seconds: Optional[float] = None) -> None
class KeyInactiveError(SourceError): ...             # key missing, invalid or not yet activated
Fetcher = Callable[[str, str, Optional[dict], Optional[dict]], HttpResponse]   # (method, url, params, json_body)
def requests_fetcher(timeout_seconds: float = 20.0) -> Fetcher
def check_status(resp: HttpResponse, source: str) -> None
# keys.py
@dataclass(frozen=True)
class Keys: bls: str; bea: str; census: str; eia: str; fred: str
def load_keys(env_file: Optional[Path] = None) -> Keys     # env_file: dotenv_values(path), else os.environ after config.settings
# adapters: period keys are dt.date; month -> 1st of month, quarter -> 1st month of quarter,
# week -> week-ending date, event -> ET calendar date of the event
@dataclass(frozen=True)
class BlsSeries: levels: dict[dt.date, float]; pct1: dict[dt.date, float]; pct12: dict[dt.date, float]
BLS_MAX_SERIES_PER_QUERY = 50
def fetch_bls(series_ids: Sequence[str], key: str, fetcher: Fetcher, start_year: int, end_year: int) -> dict[str, BlsSeries]
def fetch_nipa(table: str, frequency: str, years: Sequence[int], key: str, fetcher: Fetcher) -> dict[str, dict[dt.date, float]]   # SeriesCode -> values
def fetch_eits(program: str, key: str, fetcher: Fetcher, since: dt.date) -> dict[tuple[str, str], dict[dt.date, float]]      # (category_code, data_type_code), SA and US-level rows only
def fetch_eia_weekly(route: str, series_id: str, key: str, fetcher: Fetcher, length: int = 60) -> dict[dt.date, float]
def parse_target_range(html: str) -> Optional[tuple[float, float]]
def fetch_fomc_upper_bounds(fetcher: Fetcher, since: dt.date) -> dict[dt.date, float]
def fetch_auctions(original_term: str, security_type: str, fetcher: Fetcher, days: int = 400) -> dict[dt.date, tuple[float, float]]
def fetch_fred_current(series_id: str, key: str, fetcher: Fetcher, observation_start: dt.date) -> dict[dt.date, float]
```

- [ ] **Step 1: Live verification and fixture recording (read-only).** Write `scripts/record_official_fixtures.py` (Write tool). It loads keys with `load_keys(--env-file)`, calls each endpoint once, replaces every key value in the response body with `REDACTED` before saving to `tests/fixtures/official_actuals/<source>_<name>.<json|xml|html>`, and prints only status codes and latest periods. Record: BLS (the 15 series above plus `CES0000000001` 2025-2026), BEA `T10101` Q, `T10107` Q, `T20807` M, `T20600` M, EIA crude and natural gas, Fed RSS plus statement pages `monetary20261028a.htm` and `monetary20260916a.htm`, TreasuryDirect `auctioned` Note and Bond, FRED `ICSA`, Census `marts`, `advm3` (`for=us:*`), `m3`, `resconst`, `ressales`, `vip`, `mtis`, `mwts`, `mwtsadv`, `ftdadv`, `ftd`, and one keyless Census call (the `Missing Key` page). For each Census title in Task 2's registry, find the category/data-type code whose latest value equals the latest stored FF previous/actual for that title (live DB, mode=ro). Write the resolved codes, and the ones that do not resolve, into the Task 2 registry comments and report the unresolved ones; never guess a code. Run: `python scripts/record_official_fixtures.py --env-file C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/.env`.
- [ ] **Step 2: Failing tests** in `tests/test_official_adapters.py` (a fixture-backed fake `Fetcher`, no network):
  - `test_bls_parses_levels_and_pct_changes`: `CES0000000001` levels[2026-09-01] == 159044 and [2026-08-01] == 159015; `CUSR0000SA0` pct1[2026-09-01] == 0.6; `CUUR0000SA0` pct12[2026-09-01] == 3.7; `CIS1010000000000Q` levels[2026-04-01] == 0.9 (Q02 -> April); M13 rows are skipped.
  - `test_bls_batches_fifty_series_per_post`: 51 ids -> exactly 2 POSTs; the key is in `registrationkey` of each body.
  - `test_bls_daily_threshold_raises_rate_limited`: a `REQUEST_NOT_PROCESSED` body with a threshold message raises `SourceRateLimited`.
  - `test_bea_parses_quarter_and_month_periods_and_commas`: `A191RL`[2026-04-01] == 2.2; `DPCCRGM`[2026-08-01] == 0.2; `A065RC`[2026-08-01] == 27626933.0.
  - `test_bea_invalid_key_raises_key_inactive`: a BEA error body with `APIErrorCode` 3, or the live answer to a bad key (`APIErrorCode` 1, "Invalid Request - Invalid API UserId."), raises `KeyInactiveError`; code 1 with any other description and code 40 raise a plain `SourceError`.
  - `test_census_missing_key_page_raises_key_inactive`: HTML title `Missing Key` -> `KeyInactiveError`; `advm3` request carries `for=us:*`; non-US geography rows are dropped.
  - `test_eia_weekly_returns_levels_by_week_end`: crude[2026-10-23] == 410625 and [2026-10-16] == 412517; gas[2026-10-16] == 3644.
  - `test_fed_parses_upper_bound_with_tags_and_fractions`: the 10-28 page -> (3.75, 4.0); the 09-16 page (with `<strong> </strong>`) -> (3.75, 4.0); `fetch_fomc_upper_bounds` keys the 10-28 statement as date(2026, 10, 28) and ignores minutes and discount-rate items.
  - `test_treasury_includes_reopenings_and_excludes_tips`: `fetch_auctions("10-Year", "Note", ...)` has date(2026, 10, 7) == (5.3, 2.77) and date(2026, 9, 9) == (4.834, 2.71); no TIPS row.
  - `test_check_status_maps_429_and_5xx_with_retry_after`: 429 with `Retry-After: 30` -> `SourceRateLimited` with 30.0; 503 -> `SourceRateLimited`; 404 -> plain `SourceError`.
  - `test_errors_never_carry_url_or_key`: a fetcher raising `requests.ConnectionError("https://x?api_key=SECRET")` -> `SourceTransportError` whose `str()` contains neither `SECRET` nor `http`.
  - `test_fixtures_carry_no_key_material`: no file under `tests/fixtures/official_actuals/` contains `api_key=`, `registrationkey` with a non-`REDACTED` value, or a BEA `USERID` value other than `REDACTED`.
  - `test_load_keys_reads_env_file_without_exporting`: a temp env file -> `Keys` filled; `os.environ` unchanged.
- [ ] **Step 3: Run** `python -m pytest -q -p no:warnings tests/test_official_adapters.py`: FAIL (modules missing).
- [ ] **Step 4: Implement.** Each adapter is a pure parse over `fetcher(...)`; `requests_fetcher` sends `USER_AGENT` and wraps every requests exception in `SourceTransportError(type(exc).__name__)` (`from None`). `check_status` runs before parsing (429/5xx -> `SourceRateLimited` with a parsed `Retry-After`). BLS: POST JSON `{seriesid, startyear, endyear, calculations: true, registrationkey}`, values `"-"` skipped. BEA: GET `UserID, method=GetData, datasetname=NIPA, TableName, Frequency, Year=",".join(years), ResultFormat=JSON`; `TimePeriod` `2026Q2` / `2026M08`. Census: GET `get=cell_value,data_type_code,category_code,seasonally_adj,time_slot_id,geo_level_code` (plus `for=us:*` for `advm3`), `time=from YYYY-MM`, `key`; HTML `Missing Key` / `Invalid Key` -> `KeyInactiveError`; keep `seasonally_adj == "yes"` and US-level rows. EIA: GET `api_key, frequency=weekly, data[0]=value, facets[series][]=<id>, sort[0][column]=period, sort[0][direction]=desc, length`. Fed: parse RSS items titled exactly `Federal Reserve issues FOMC statement` with pubDate >= since, fetch each link, strip tags, `re.search(r"target range for the federal funds rate.*?(\d+(?:-\d/\d)?)\s+to\s+(\d+(?:-\d/\d)?)\s+percent", text, re.S)`, `3-3/4` -> 3.75; key = pubDate in America/New_York. Treasury: GET `auctioned?format=json&type=<Note|Bond>&days=<n>`; keep rows with `originalSecurityTerm == term`, `type != "TIPS"`, non-empty `highYield` and `bidToCoverRatio`; key = `competitiveAuctionCloseDate` date. FRED: wrap `FredClient(key).vintage_levels(series, today, start)` from `data_layer/fred_history.py`, mapping `FredTransportError` -> `SourceTransportError` and other Fred errors -> `SourceError`.
- [ ] **Step 5: Run** the file: PASS. **Full suites** from the app dir: `python -m pytest -q -p no:warnings` (only the known `test_combined_builder_includes_alpha_vantage_when_key_present` may fail) and `npm test`.
- [ ] **Step 6: Commit** `feat(ACT): official publisher adapters (BLS, BEA, Census, EIA, Fed, Treasury, FRED) with recorded fixtures`.

## Task 2 — Registry, fill rule, coverage lists and the verification gate  `[judgment]`

**Files:** create `data_layer/official_actuals/registry.py`, `fetch.py`, `coverage.py`, `gate_results.json` (generated), `scripts/verify_official_actuals.py`, `tests/test_official_registry.py`, `tests/test_verify_official_actuals.py`; modify `data_layer/fred_history.py` only if a public helper is needed (prefer importing `transform_at`, `values_match`, `FredClient`).

**Interfaces:**
```python
# registry.py
PUBLISHER_SOURCES = ("bls", "bea", "census", "eia", "fed", "treasury")     # new source labels; 'fred' is existing
@dataclass(frozen=True)
class OfficialSpec:
    source: str                  # one of PUBLISHER_SOURCES or "fred"
    series: str                  # adapter key, e.g. "CUSR0000SA0", "T20807:M:DPCCRGM", "marts:44X72:MPCSM",
                                 # "petroleum/stoc/wstk:WCESTUS1", "fomc_upper", "Note:10-Year", "ICSA"
    field: str                   # "level" | "pct1" | "pct12" (BLS calculations); "level" elsewhere
    transform: str               # "lin" | "chg" | "pch" | "pc1" | "auction"
    frequency: str               # "monthly" | "quarterly" | "weekly" | "event"
    unit_scale: float            # source units -> FF suffix units
    suffix: str                  # "%", "K", "M", "B", "" when the FF row has no template
    decimals: int                # used only when the FF row has no template
    release_time_et: dt.time
    min_lag_days: int = 7
    week_end_weekday: Optional[int] = None    # 5 = Saturday (claims), 4 = Friday (EIA)
    revises: bool = True
    fred_twin: Optional[tuple[str, str]] = None   # (FRED series id, transform) for the gate
OFFICIAL_SPECS: dict[str, OfficialSpec]
def expected_period(spec: OfficialSpec, release_et: dt.date) -> dt.date
def prior_period(spec: OfficialSpec, period: dt.date, known: Iterable[dt.date]) -> Optional[dt.date]
def value_for(spec: OfficialSpec, series: Mapping[dt.date, Any], period: dt.date) -> Optional[float | tuple[float, float]]
def format_like(value: float | tuple[float, float], template: Optional[str], spec: OfficialSpec) -> str
def ff_values_match(stored: Optional[str], candidate: Optional[str]) -> bool
@dataclass(frozen=True)
class FillDecision: actual: Optional[str]; reason: str     # reason "fill" or why not
def decide_fill(spec: OfficialSpec, event_time_utc: dt.datetime, forecast: Optional[str], previous: Optional[str],
                series: Mapping[dt.date, Any], later_release: bool, later_previous: Optional[str]) -> FillDecision
# fetch.py
@dataclass(frozen=True)
class FetchOutcome: data: dict[str, dict[dt.date, Any]]; errors: dict[str, SourceError]   # data keyed by series_key(spec); errors by source
def series_key(spec: OfficialSpec) -> str
def fetch_for_specs(specs: Iterable[OfficialSpec], since: dt.date, fetcher: Fetcher, keys: Keys) -> FetchOutcome
# coverage.py
GATE_RESULTS_PATH: Path      # data_layer/official_actuals/gate_results.json
def coverage_for(title: str) -> str      # "no_actual_expected" | "official" | "proprietary" | "not_mapped"
@dataclass(frozen=True)
class GateResult: status: str; matches: int; comparisons: int; identity: str
def load_gate_results(path: Optional[Path] = None) -> dict[str, GateResult]    # missing or corrupt file -> {}
def enabled_titles(gate: Mapping[str, GateResult]) -> frozenset[str]           # OFFICIAL_SPECS titles with status "verified"
def missing_numeric_rows(conn: sqlite3.Connection, start_utc: dt.datetime, end_utc: dt.datetime) -> list[sqlite3.Row]
# scripts/verify_official_actuals.py
GATE_START = dt.date(2026, 1, 1); GATE_MIN_COMPARISONS = 2; GATE_IDENTITY_PERIODS = 6
@dataclass
class TitleGate: status: str; matches: int; comparisons: int; revision_explained: int; identity: str; mismatches: list[str]
def gate_title(title: str, spec: OfficialSpec, rows: list[sqlite3.Row], series: Mapping[dt.date, Any],
               twin: Optional["TwinReader"], now: dt.datetime) -> TitleGate
def run_gate(conn: sqlite3.Connection, now: dt.datetime, fetcher: Fetcher, keys: Keys,
             fred_client: Optional[FredClient], titles: Optional[list[str]] = None) -> dict[str, TitleGate]
def results_to_json(results: Mapping[str, TitleGate], now: dt.datetime) -> dict
def coverage_markdown(results: Mapping[str, TitleGate]) -> str
```

**Registry** (titles from the live USD title list; `T` = twin; lag = `min_lag_days`; times ET; `rev` = revises):

| FF title | source / series / field / transform | freq | scale -> suffix, dec | time | lag | rev | FRED twin |
|---|---|---|---|---|---|---|---|
| Non-Farm Employment Change | bls CES0000000001 level chg | M | 1 -> K, 0 | 08:30 | 0 | yes | PAYEMS chg |
| Unemployment Rate | bls LNS14000000 level lin | M | 1 -> %, 1 | 08:30 | 0 | yes | UNRATE lin |
| Average Hourly Earnings m/m | bls CES0500000003 pct1 lin | M | %, 1 | 08:30 | 0 | yes | CES0500000003 pch |
| CPI m/m / Core CPI m/m | bls CUSR0000SA0 / CUSR0000SA0L1E pct1 | M | %, 1 | 08:30 | 7 | yes | CPIAUCSL / CPILFESL pch |
| CPI y/y / Core CPI y/y | bls CUUR0000SA0 / CUUR0000SA0L1E pct12 | M | %, 1 | 08:30 | 7 | yes | CPIAUCNS / CPILFENS pc1 |
| PPI m/m / Core PPI m/m | bls WPSFD4 / WPSFD49104 pct1 | M | %, 1 | 08:30 | 7 | yes | PPIFIS / PPIFES pch |
| Import Prices m/m | bls EIUIR pct1 | M | %, 1 | 08:30 | 7 | yes | IR pch |
| JOLTS Job Openings | bls JTS000000000000000JOL level lin | M | 0.001 -> M, 2 | 10:00 | 7 | yes | JTSJOL lin |
| Employment Cost Index q/q | bls CIS1010000000000Q level lin | Q | %, 1 | 08:30 | 7 | yes | none |
| Prelim / Revised Nonfarm Productivity q/q | bls PRS85006092 level lin | Q | %, 1 | 08:30 | 7 | yes | PRS85006092 lin (verify) |
| Prelim / Revised Unit Labor Costs q/q | bls PRS85006112 level lin | Q | %, 1 | 08:30 | 7 | yes | PRS85006112 lin (verify) |
| Advance / Prelim / Final GDP q/q | bea T10101:Q:A191RL lin | Q | %, 1 | 08:30 | 7 | yes | A191RL1Q225SBEA lin |
| Advance / Prelim / Final GDP Price Index q/q | bea T10107:Q:A191RV lin | Q | %, 1 | 08:30 | 7 | yes | A191RI1Q225SBEA lin (verify) |
| Core PCE Price Index m/m | bea T20807:M:DPCCRGM lin | M | %, 1 | 08:30 | 7 | yes | PCEPILFE pch |
| Personal Income m/m / Personal Spending m/m | bea T20600:M:A065RC / DPCERC pch | M | %, 1 | 08:30 | 7 | yes | PI / PCE pch |
| Retail Sales m/m / Core Retail Sales m/m | census marts:44X72 / 44Y72:MPCSM lin | M | %, 1 | 08:30 | 7 | yes | RSAFS / RSFSXMV pch |
| Durable Goods Orders m/m / Core Durable Goods Orders m/m | census advm3:MDM / DXT:MPCNO lin (resolved Task 1) | M | %, 1 | 08:30 | 7 | yes | DGORDER / ADXTNO pch |
| Housing Starts / Building Permits | census resconst:ASTARTS / APERMITS:TOTAL lin (resolved Task 1; STARTS has no SA rows) | M | 0.001 -> M, 2 | 08:30 | 7 | yes | HOUST / PERMIT lin |
| New Home Sales | census ressales:ASOLD:TOTAL lin (resolved Task 1) | M | 1 -> K, 0 | 10:00 | 7 | yes | HSN1F lin |
| Construction Spending m/m | census vip:XXXX:MPCT lin (resolved Task 1) | M | %, 1 | 10:00 | 7 | yes | TTLCONS pch |
| Business Inventories m/m | census mtis:TOTBUS:MPCIM lin (resolved Task 1) | M | %, 1 | 10:00 | 20 | yes | BUSINV pch |
| Final Wholesale Inventories m/m | census mwts:42:MPCIM lin (UNRESOLVED in Task 1: matches neither stored FF values nor WHLSLRIMSA, which equals mtis WHLSLR:IM; leave out) | M | %, 1 | 10:00 | 20 | yes | WHLSLRIMSA pch |
| Prelim Wholesale Inventories m/m | census mwtsadv (UNRESOLVED in Task 1: 42:MPCIM has no FF match and no twin; leave out) | M | %, 1 | 08:30 | 7 | yes | none |
| Goods Trade Balance | census ftdadv (UNRESOLVED in Task 1: CBG:BAL has no FF match, no twin; leave out) | M | 0.001 -> B, 1 | 08:30 | 7 | yes | none |
| Trade Balance | census ftd:BOPGS:BAL lin (resolved Task 1) | M | 0.001 -> B, 1 | 08:30 | 20 | yes | BOPGSTB lin |
| Factory Orders m/m | census m3:MTM:MPCNO lin (resolved Task 1; m3 also needs for=us:*) | M | %, 1 | 10:00 | 20 | yes | AMTMNO pch |
| Crude Oil Inventories | eia petroleum/stoc/wstk:WCESTUS1 chg | W, Fri | 0.001 -> M, 1 | 10:30 | 0 | no | WCESTUS1 chg |
| Natural Gas Storage | eia natural-gas/stor/wkly:NW2_EPG0_SWO_R48_BCF chg | W, Fri | 1 -> B, 0 | 10:30 | 0 | no | none |
| Federal Funds Rate | fed fomc_upper lin | event | %, 2 | 14:00 | 0 | no | DFEDTARU lin |
| 10-y Bond Auction / 30-y Bond Auction | treasury Note:10-Year / Bond:30-Year auction | event | `y|b`, 2 and 1 | 13:00 | 0 | no | none |
| Unemployment Claims | fred ICSA lin | W, Sat | 0.001 -> K, 0 | 08:30 | 0 | yes | ICSA lin |

A Census row whose code did not resolve in Task 1 is left out of `OFFICIAL_SPECS`, so `coverage_for` returns `not_mapped` and the title keeps its FRED backfill. "(verify)" twins that do not resolve on FRED become `None`.

**Coverage lists (`coverage.py`):** `NO_ACTUAL_EXPECTED` regexes: `Speaks$`, `Testifies$`, `^Beige Book$`, `Monetary Policy Report`, `Press Conference$`, `^FOMC Statement$`, `^FOMC Economic Projections$`, `^FOMC Meeting Minutes$`. `PROPRIETARY`: ISM *, * UoM *, CB Consumer Confidence, CB Leading Index m/m, Flash/Final Manufacturing PMI, Flash/Final Services PMI, Chicago PMI, NAHB Housing Market Index, NFIB Small Business Index, API Weekly Statistical Bulletin, Challenger Job Cuts y/y, RCM/TIPP Economic Optimism, ADP Non-Farm Employment Change, ADP Weekly Employment Change, Existing Home Sales, Pending Home Sales m/m, S&P/CS Composite-20 HPI y/y, Omdia Total Vehicle Sales, Philly Fed / Empire State / Richmond / Kansas City / Dallas manufacturing indices (regional surveys: no release-time machine-readable source verified). `NOT_MAPPED` (title -> publisher, kept on FRED backfill where mapped): Industrial Production m/m and Capacity Utilization Rate (Fed G.17), Consumer Credit m/m (Fed G.19), Federal Budget Balance (Treasury MTS, host not approved), HPI m/m (FHFA), Current Account (BEA ITA), TIC Long-Term Purchases (Treasury TIC). Any other title -> `not_mapped`. `missing_numeric_rows` = USD rows, `actual IS NULL`, event time in range, not `no_actual_expected`, and forecast or previous parses as a number.

- [ ] **Step 1: Failing tests** `tests/test_official_registry.py`:
  - `test_expected_period_rules`: CPI released 2026-10-14 -> 2026-09-01; NFP released 2026-09-04 -> 2026-08-01 (lag 0); JOLTS 2026-09-01 -> 2026-07-01 and 2026-09-29 -> 2026-08-01; Core PCE 2026-09-30 -> 2026-08-01; Business Inventories 2026-10-15 -> 2026-08-01; Construction Spending 2026-10-01 -> 2026-08-01; Advance GDP 2026-10-29 and Final GDP 2026-09-30 -> 2026-07-01 / 2026-04-01; Revised Productivity 2026-09-03 -> 2026-04-01; claims Thu 2026-10-29 -> Sat 2026-10-24; crude Wed 2026-10-28 -> Fri 2026-10-23; natural gas Thu 2026-10-29 -> Fri 2026-10-23; Fed 2026-10-28 -> 2026-10-28.
  - `test_format_like_matches_ff_strings`: NFP chg 29.0 with template "89K" -> `29K`; JOLTS 7079 -> `7.08M` (template "7.23M"); crude -1892 -> `-1.9M` (template "0.1M"); gas 77 -> `77B` (template "75B"); Fed 4.0 -> `4.00%` (template "4.00%"); auction (5.3, 2.77) -> `5.30|2.8` (template "4.83|2.7"); -0.04 with template "0.2%" -> `0.0%`; no template -> spec decimals and suffix; a template whose suffix differs from the spec suffix is ignored.
  - `test_ff_values_match_handles_auction_pairs`: `4.83|2.7` vs `4.834|2.71` -> True; `4.83|2.7` vs `4.83|2.9` -> False.
  - `test_decide_fill_writes_expected_period`: CPI m/m row 2026-10-14T12:30Z, forecast "0.6%", pct1 fixture -> actual `0.6%`, reason "fill".
  - `test_decide_fill_waits_when_expected_period_absent`: same row, series without 2026-09-01 -> actual None, reason "awaiting publication".
  - `test_decide_fill_skips_older_row_of_revised_series`: `later_release=True`, `revises=True` -> None, reason starts "revised since release".
  - `test_decide_fill_older_unrevised_row_needs_ff_previous_agreement`: crude row released 2026-10-21 (week 2026-10-16: 412517 - 415577 = -3060) with `later_release=True` and the next row's previous "-3.1M" (the live 2026-10-28 row) -> fill `-3.1M`; with later previous "-2.0M" -> None, "disagrees with FF previous on the next release".
  - `test_coverage_lists`: "FOMC Member Waller Speaks", "Beige Book", "FOMC Press Conference" -> `no_actual_expected`; "ISM Services PMI", "Prelim UoM Consumer Sentiment" -> `proprietary`; "Industrial Production m/m" -> `not_mapped`; "CPI m/m" -> `official`.
  - `test_missing_numeric_rows_excludes_speeches_and_text_only_and_non_usd`.
  - `test_load_gate_results_missing_or_corrupt_is_empty` and `test_enabled_titles_only_verified`.
  - `test_fetch_for_specs_one_bls_call_for_many_titles_and_errors_per_source`: CPI m/m, CPI y/y, Core CPI m/m, NFP -> one BLS fetch; an EIA `SourceRateLimited` lands in `errors["eia"]` while BLS data is returned.
- [ ] **Step 2: Failing tests** `tests/test_verify_official_actuals.py` (temp DB, fixtures, fake twin):
  - `test_threshold_is_b8s`: `verify.VERIFY_AGREEMENT_THRESHOLD is seed_fred_history.VERIFY_AGREEMENT_THRESHOLD` (0.8).
  - `test_gate_verified_when_actuals_and_previous_agree`: CPI m/m rows with stored actuals and previous equal to the fixture -> `verified`, comparisons >= 2.
  - `test_gate_explains_gdp_revision_with_alfred_vintage`: Advance GDP row 2026-07-30 actual "1.5%", official Q2 2.2, twin as of 2026-07-30 = 1.5, identity ok -> counted as agreement (`revision_explained` == 1), status `verified`; same with identity `mismatch` -> `suspect`.
  - `test_gate_marks_wrong_scale_suspect`: JOLTS spec with unit_scale 1.0 -> `suspect`, mismatch lines name the row time in SAST.
  - `test_gate_unverified_below_two_comparisons`; `test_gate_skips_rows_filled_by_publisher_sources` (a `bls` actual is not a reference); `test_gate_key_inactive_and_unavailable_statuses`.
  - `test_results_json_exact_keys`: top level {"generated_at_utc", "threshold", "titles"}; each title {"status", "matches", "comparisons", "revision_explained", "identity", "mismatches"}.
  - `test_main_opens_db_read_only_and_never_prints_keys` (capsys contains no fake key value).
- [ ] **Step 3: Run** both files: FAIL.
- [ ] **Step 4: Implement.** `expected_period`: monthly/quarterly = the latest period whose last day <= `release_et - min_lag_days`; weekly = the latest `week_end_weekday` date <= `release_et - min_lag_days`; event = `release_et`. `value_for`: `lin` -> value; `chg` -> value minus prior period value; `pch` -> (v / prior - 1) * 100; `pc1` -> vs the same period a year earlier; `auction` -> the tuple; missing points -> None. `format_like`: scale, then decimals and suffix from the template (strip commas; the suffix is the trailing `%`/`K`/`M`/`B`) when its suffix equals `spec.suffix`, else spec defaults; a value that rounds to zero has no minus sign (same rule as `fred_history.format_value`); auction -> `f"{y:.{d1}f}|{b:.{d2}f}"` with decimals from each template part. `decide_fill` order: value missing -> "awaiting publication"; `later_release and spec.revises` -> "revised since release (first print not available from <source>)"; `later_previous` parses and does not match -> "disagrees with FF previous on the next release"; else fill with `forecast` (then `previous`) as the template. `fetch_for_specs` groups specs by source request (one BLS call with all series; one BEA call per table/frequency; one Census call per program; one EIA/FRED call per series; one Fed call; one Treasury call per type) and fetches from `since - 400 days` for y/y and change transforms. Gate (`gate_title`): references from rows released at or after `GATE_START` and before `now`; actual refs skipped when `row["source"] in PUBLISHER_SOURCES`; previous ref period = `prior_period`; `TwinReader.value_asof(series_id, transform, period, vintage_date)` = `transform_at(FredClient.vintage_levels(...), period, transform)`; identity = official vs twin current values over the last `GATE_IDENTITY_PERIODS` common periods, formatted with the title's latest FF template, share >= threshold -> "ok"; status `unavailable` on `SourceError`, `key_inactive` on `KeyInactiveError`. `main(argv)`: `--db` (opened `file:...?mode=ro`), `--env-file`, `--title` (repeatable), `--write-results` (writes `GATE_RESULTS_PATH` with `results_to_json`, sorted keys, LF), `--markdown PATH` (writes `coverage_markdown`: title | source | series | gate status | agreement m/n | identity); prints the per-title report in SAST; exit 0, 2 when the DB is missing.
- [ ] **Step 5: Run** both files: PASS. **Full suites**.
- [ ] **Step 6: Live gate run (read-only).** `python scripts/verify_official_actuals.py --db C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/webapp/dashboard.db --env-file C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/.env --write-results --markdown docs/superpowers/specs/2026-10-28-act-coverage.md`. Keep the printed report for the final summary (verified / suspect / unverified counts and every non-verified title with its first mismatch).
- [ ] **Step 7: Commit** `feat(ACT): title registry, fill rule, coverage lists and the verification gate (live gate results)` including `gate_results.json` and the coverage markdown.

## Task 3 — Release-time poller inside the engine  `[integration]`

**Files:** create `webapp/release_poller.py`, `tests/test_release_poller.py`, `webapp/static/js/history/source-badge.js`, `webapp/static/js/history/source-badge.test.js`; modify `ops/state.py` (job name, table, two functions), `webapp/scheduler.py` (end of `start_scheduler` only), `webapp/history.py` (both source chains and the line-208 comment), `webapp/static/js/history/table.js` (use `sourceBadge`), `tests/conftest.py`, `tests/test_webapp_scheduler.py`, `tests/test_ops_state.py`, `tests/test_webapp_history.py`.

**Interfaces:**
```python
# ops/state.py
JOB_NAMES += ("actuals_poller",)
# schema: CREATE TABLE IF NOT EXISTS official_source_status (source TEXT PRIMARY KEY, last_ok_utc TEXT, last_error_utc TEXT, last_error TEXT)
def record_source_status(conn: sqlite3.Connection, source: str, ok: bool, now: dt.datetime, error: Optional[str] = None) -> None
@dataclass(frozen=True)
class SourceStatus: source: str; last_ok_utc: Optional[dt.datetime]; last_error_utc: Optional[dt.datetime]; last_error: Optional[str]
def get_source_status(conn: sqlite3.Connection) -> dict[str, SourceStatus]
# webapp/release_poller.py
POLLER_ENABLED = True                     # tests/conftest.py sets False
FAST_POLL_SECONDS = 60; SLOW_POLL_SECONDS = 300
FAST_WINDOW = dt.timedelta(minutes=15); HANDOVER_AFTER = dt.timedelta(hours=2); CATCHUP_LOOKBACK = dt.timedelta(days=7)
IDLE_SLEEP_SECONDS = 300; WAKE_GAP_SECONDS = 120
FAST_BACKOFF_CAP_SECONDS = 60; SLOW_BACKOFF_CAP_SECONDS = 900; JITTER_SECONDS = 10
BLS_DAILY_BUDGET = 450
@dataclass
class PollerState:
    last_polled: dict[tuple[str, str], dt.datetime] = field(default_factory=dict)   # (title, event_time_utc iso)
    failures: dict[str, int] = field(default_factory=dict)
    retry_at: dict[str, dt.datetime] = field(default_factory=dict)
    last_tick_utc: Optional[dt.datetime] = None
    catchup_due: bool = True
    bls_day: Optional[dt.date] = None
    bls_calls: int = 0
@dataclass
class TickReport: filled: list[tuple[str, str, str, str]]; waiting: list[tuple[str, str, str]]; errors: dict[str, str]
FetchFn = Callable[[list[OfficialSpec], dt.date], FetchOutcome]
def poll_due(release_utc: dt.datetime, last_polled: Optional[dt.datetime], now: dt.datetime) -> bool
def backoff_seconds(failures: int, in_fast_window: bool, rand: Callable[[], float] = random.random,
                    retry_after: Optional[float] = None) -> float
def run_tick(conn: sqlite3.Connection, ops_conn: sqlite3.Connection, now: dt.datetime, state: PollerState,
             fetch: FetchFn, enabled: frozenset[str]) -> TickReport
def next_sleep_seconds(conn: sqlite3.Connection, now: dt.datetime, state: PollerState, enabled: frozenset[str]) -> float
def start_release_poller(db_path: Optional[Path] = None, *, fetch: Optional[FetchFn] = None,
                         clock: Callable[[], dt.datetime] = ..., sleep: Callable[[float], None] = time.sleep) -> Optional[threading.Thread]
```

- [ ] **Step 1: Failing tests** `tests/test_release_poller.py` (temp dashboard DB and ops DB, fake `fetch`, fixed clocks; release 2026-10-29T12:30Z unless noted):
  - `test_poll_due_cadence`: due at 12:30:00 (never polled); not due at 12:30:30 after a 12:30:00 poll; due at 12:31:00; at 12:45:00 due after 60 s; at 12:46:00 after a 12:45:00 poll not due until 12:50:00; at 14:30:01 never due (handed over); before 12:30:00 never due.
  - `test_tick_fills_with_publisher_source_and_classified_direction`: Core PCE m/m row (forecast "0.3%"), fetch returns 2026-09-01 = 0.4 -> actual `0.4%`, source `bea`, `surprise_direction` == "higher" (what `classify_surprise` returns for 0.4 vs 0.3).
  - `test_tick_writes_nothing_before_publication`: data only through 2026-08-01 -> actual stays NULL, row in `waiting` with "awaiting publication", source status ok.
  - `test_tick_never_overwrites_existing_actual`: row already filled `fred` "0.3%" -> unchanged, no second write; a row filled between fetch and write (simulate) -> `fill_actual_if_missing` False, reported, not retried.
  - `test_tick_writes_nothing_on_source_error`: fetch errors {"bea": SourceRateLimited} -> no write, `official_source_status.bea.last_error_utc` == now, `failures["bea"]` == 1.
  - `test_tick_only_polls_enabled_titles_and_usd_rows`: a `suspect` title and a non-USD row with the same title are never fetched.
  - `test_tick_batches_bls_titles_into_one_fetch_call`: CPI m/m, CPI y/y, Core CPI m/m, Core CPI y/y due together -> `fetch` called once with four specs.
  - `test_backoff_never_exceeds_fast_cadence_inside_15_minutes`: failures 1..6 with `in_fast_window=True` and rand 1.0 -> each <= 60 + 10; with `Retry-After` 600 -> still <= 70; `in_fast_window=False` grows 60, 120, 240, 480, 900, 900 (+ jitter).
  - `test_rate_limited_source_is_retried_inside_window`: 429 at 12:31, 12:32 and 12:33 -> polls continue each minute; success at 12:34 fills and resets failures.
  - `test_catch_up_polls_missed_release_once_after_wake`: `last_tick_utc` 08:00Z, now 15:00Z (gap > sleep + 120 s), row released 12:30Z still NULL -> polled once at 15:00; the next tick at 15:01 does not poll it; a row released 9 days ago is never polled.
  - `test_catch_up_on_start`: a fresh `PollerState` polls released rows from the last 7 days once.
  - `test_bls_daily_budget_skips_slow_window_only`: `bls_calls` == 450 -> a 13:00Z (slow window) BLS row is skipped, a 12:35Z (fast window) row is still polled.
  - `test_next_sleep_seconds`: a due fast-window row -> <= 60; nothing within the next 5 minutes -> 300; a release in 90 s -> 90.
  - `test_heartbeat_and_thread_never_dies`: one loop iteration with a fetch raising `RuntimeError` records the `actuals_poller` heartbeat and keeps running; the log line contains only the class name.
  - `test_conftest_disables_poller`: under pytest `start_release_poller()` returns None.
  - `test_history_keeps_publisher_source` (in `tests/test_webapp_history.py`): a resolved row with source `bls` shows `source == "bls"`, not `live`.
- [ ] **Step 2: Failing tests** elsewhere: `tests/test_webapp_scheduler.py::test_start_scheduler_starts_release_poller_once` (monkeypatched `start_release_poller` called exactly once); ops-state tests `test_record_source_status_upserts_ok_and_error` and `test_actuals_poller_is_a_known_job`; `source-badge.test.js`: `sourceBadge("bls")` -> ` <span class="meta-text-sm">(BLS)</span>`, `bea` -> `(BEA)`, `census` -> `(Census)`, `eia` -> `(EIA)`, `fed` -> `(Fed)`, `treasury` -> `(Treasury)`, `seeded` / `live_web_fallback` / `cloud_web_fallback` unchanged, `live` and `fred` -> "".
- [ ] **Step 3: Run** `python -m pytest -q -p no:warnings tests/test_release_poller.py tests/test_webapp_scheduler.py` and `npm test`: FAIL.
- [ ] **Step 4: Implement.** `run_tick`: reset the BLS counter on a new UTC day; select candidate rows `country='USD' AND actual IS NULL AND event_title IN enabled AND julianday(event_time_utc) BETWEEN julianday(now - HANDOVER_AFTER) AND julianday(now)`, plus, when `state.catchup_due`, rows from `now - CATCHUP_LOOKBACK` to `now - HANDOVER_AFTER` (then clear the flag); keep rows where `poll_due(...)` (catch-up rows: not polled since the wake), whose source is not in backoff (`retry_at`) unless the row is inside `FAST_WINDOW` and 60 s have passed since its last poll, and BLS rows only within budget or inside `FAST_WINDOW`; call `fetch(specs, since)` once; per source: on error set `failures`, `retry_at = now + backoff_seconds(...)`, `record_source_status(ok=False, error=type name)`; on success reset and record ok, count BLS calls; per row `decide_fill(...)` with `later_release` / `later_previous` from the next USD row of the same title (and of any title sharing `series_key`); on "fill" call `store.fill_actual_if_missing(conn, id, actual, classify_surprise(event), spec.source, now)`; stamp `last_polled` for every polled row. `start_release_poller` (no-op when `POLLER_ENABLED` is False or already started): daemon thread named `actuals-poller`, its own `store.get_connection(db_path)` and `ops_state.get_connection()` per iteration, `enabled = enabled_titles(load_gate_results())` read once at start, `fetch` default = `lambda specs, since: fetch_for_specs(specs, since, requests_fetcher(), load_keys())`; each iteration: wake check (`now - last_tick > planned_sleep + WAKE_GAP_SECONDS` -> `catchup_due`), `run_tick`, `touch_heartbeat("actuals_poller")`, print fills as `[release_poller] filled <title> <SAST> = <actual> (<source>)`, sleep `next_sleep_seconds`; the whole body in `except Exception` that prints the class name only. `webapp/scheduler.py`: after `thread.start()` in `start_scheduler`, a function-local `from webapp.release_poller import start_release_poller` (comment: lazy so importing the scheduler does not load the adapters; it also keeps the B8 doc's line pointers valid) and `start_release_poller()`. `webapp/history.py`: in both chains insert `else event.source if event.source in PUBLISHER_SOURCES` after the `cloud_web_fallback` branch, before `fred`; update the line-208 comment. `tests/conftest.py`: `monkeypatch.setattr("webapp.release_poller.POLLER_ENABLED", False)` and blank `keys` values (patch `data_layer.official_actuals.keys.load_keys` to return empty `Keys`).
- [ ] **Step 5: Run** the files: PASS. **Full suites** (`python -m pytest -q -p no:warnings`, `npm test`).
- [ ] **Step 6: Commit** `feat(ACT): release-time poller thread (60 s to T+15, 5 min to T+2 h, catch-up on wake, backoff) with publisher provenance`.

## Task 4 — 15-minute SLA alarm and web-fallback retirement  `[integration]`

**Files:** modify `ops/health.py`, `tests/test_ops_health.py`, `scripts/fill_missing_actuals.py`, `tests/test_fill_missing_actuals.py`, `webapp/app.py`, `webapp/store.py`, `tests/test_webapp_store.py`, `docs/b8-deploy.md` (U2 bullet only), `tests/test_b8_deploy_doc.py`; delete `webapp/actuals_sync.py`, `tests/test_actuals_sync.py`.

**Interfaces:**
```python
# ops/health.py
ACTUALS_SLA_AFTER = dt.timedelta(minutes=15)
ACTUALS_SLA_LOOKBACK = dt.timedelta(hours=24)
POLLER_STALE_AFTER = dt.timedelta(minutes=10)
SLA_PROPRIETARY_STATUS = "amber"
_ACTUALS_SLA_LABEL = "Actuals within 15 min"
def overdue_reason(title: str, release_utc: dt.datetime, now: dt.datetime, gate: Mapping[str, GateResult],
                   sources: Mapping[str, SourceStatus], poller_last_tick: Optional[dt.datetime]) -> str
def _actuals_sla_check(now: dt.datetime, conns: dict[str, sqlite3.Connection],
                       gate: Optional[Mapping[str, GateResult]] = None) -> HealthItem
```
Reasons, first match wins: `not mapped`; `proprietary`; `gate: <status>` (title in `OFFICIAL_SPECS` but not verified, or no gate result: `gate: not run`); `key inactive` (last source error is `KeyInactiveError`); `poller not running` (heartbeat older than `POLLER_STALE_AFTER` or missing); `source down` (last error after the release time and newer than the last ok); `awaiting publication`.

- [ ] **Step 1: Failing tests** in `tests/test_ops_health.py` (NOW = 2026-10-20 10:00Z fixture style):
  - `test_item_keys_and_order_are_stable`: `EXPECTED_KEYS` gains `"actuals_sla"` right after `"calendar_refresh"`.
  - `test_sla_ok_when_nothing_overdue`: a release 10 minutes ago, still NULL -> ok; a row released 25 h ago -> outside lookback, ok.
  - `test_sla_red_lists_title_time_minutes_and_reason`: Goods Trade Balance released 2026-10-20T08:30Z (10:30 SAST), NULL, title gate `suspect` -> red, detail `1 overdue: Goods Trade Balance 10:30 SAST, 90 min late (gate: suspect)`.
  - `test_sla_proprietary_only_is_amber`: an "ISM Services PMI" row overdue -> amber with reason `proprietary`; plus a not-mapped row -> red.
  - `test_sla_excludes_no_actual_expected_and_text_only`: "FOMC Member Waller Speaks" and a row with NULL forecast and previous -> ok.
  - `test_sla_reason_key_inactive`, `test_sla_reason_source_down`, `test_sla_reason_poller_not_running`, `test_sla_reason_awaiting_publication`.
  - `test_health_notice_includes_overdue_actuals`: with only `actuals_sla` red, `maybe_send_health_notice(send=fake)` sends once and the text contains `Actuals within 15 min: 1 overdue: ...`.
  - `test_sla_check_failure_is_amber`: a corrupt gate file / raising query -> amber "check failed", others intact.
- [ ] **Step 2: Failing tests (retirement):** `tests/test_fill_missing_actuals.py::test_list_uses_missing_numeric_rows` (`--list` prints rows from `coverage.missing_numeric_rows`, no speech titles); `tests/test_webapp_store.py`: remove the three `get_events_with_stale_missing_actual` tests and their `__main__` calls; a new static test `test_web_fallback_is_retired` (in `tests/test_scripts_archive.py` style): `webapp/actuals_sync.py` does not exist, `webapp/app.py` has no `actuals_sync`, `webapp/store.py` has no `get_events_with_stale_missing_actual`; `tests/test_b8_deploy_doc.py` EXPECTED: drop `webapp/actuals_sync.py:40`, `webapp/store.py:34`, `webapp/store.py:623-649`; `webapp/app.py:147` -> the new line of `get_event_history(conn, title)` (146 after the import removal; read it, do not assume).
- [ ] **Step 3: Run** the touched test files: FAIL.
- [ ] **Step 4: Implement.** Health: `_actuals_sla_check` reads `coverage.missing_numeric_rows(dash, now - ACTUALS_SLA_LOOKBACK, now - ACTUALS_SLA_AFTER)`, `load_gate_results()` (or the injected `gate`), `ops_state.get_source_status(ops)` and the `actuals_poller` job run; entries `f"{title} {HH:MM} SAST, {minutes} min late ({reason})"` oldest first via `_list_detail(f"{n} overdue", entries)`; status red if any reason is not `proprietary`, else `SLA_PROPRIETARY_STATUS`; `last_success_utc` = poller heartbeat; `expected_every_seconds` 900; inserted in `build_health` after `job("calendar_refresh")`. No new Telegram type: the existing `health_notice_text` prints the detail. Retirement: delete `webapp/actuals_sync.py` and `tests/test_actuals_sync.py`; in `webapp/app.py` remove the import, the `start_actuals_sync()` call and "actuals-sync" from the waitress comment; in `webapp/store.py` remove `get_events_with_stale_missing_actual` and the now-unused `EVENT_SURPRISE_DIRECTION` import (grep first: `grep -rn "store import" --include=*.py . | grep EVENT_SURPRISE_DIRECTION` must be empty); `scripts/fill_missing_actuals.py --list` -> `coverage.missing_numeric_rows(conn, now - 92 days, now)` printed in SAST, docstring updated (manual tool for proprietary releases; the cloud queue is retired); `docs/b8-deploy.md` U2 bullet 2 becomes "The web fallback queue (retired by ACT, 2026-10-28) admitted only the 19 titles in `EVENT_SURPRISE_DIRECTION` within 48 h." and the app pointer is updated.
- [ ] **Step 5: Run** the touched files: PASS. **Full suites**.
- [ ] **Step 6: Commit** `feat(ACT): 15-minute actuals SLA health item; retire the cloud web-fallback queue`.

## Task 5 — Backlog backfill script and live dry run  `[integration]`

**Files:** create `scripts/backfill_official_actuals.py`, `tests/test_backfill_official_actuals.py`.

**Interfaces:**
```python
DEFAULT_SINCE = dt.date(2026, 7, 28)
OUTCOMES = ("filled", "would fill", "already filled", "no actual expected", "proprietary", "not mapped",
            "gate disabled", "key inactive", "source error", "awaiting publication",
            "revised since release", "disagrees with FF previous")
@dataclass
class BacklogReport:
    per_title: dict[str, Counter]           # title -> outcome -> count
    details: list[str]                      # one line per fill / would-fill, SAST + stored UTC
def run_backlog(conn: sqlite3.Connection, now: dt.datetime, fetch: FetchFn, gate: Mapping[str, GateResult],
                since: dt.date = DEFAULT_SINCE, apply: bool = False, titles: Optional[list[str]] = None) -> BacklogReport
def format_report(report: BacklogReport, apply: bool) -> str
def main(argv: Optional[list[str]] = None) -> int
```

- [ ] **Step 1: Failing tests** (temp DB, fake fetch):
  - `test_dry_run_writes_nothing_and_reports_per_title`: rows for CPI m/m (NULL), Federal Funds Rate 2026-10-28 (NULL, forecast "4.00%"), FOMC Member Barkin Speaks, ISM Services PMI, Industrial Production m/m, a gate-`suspect` title and a filled row -> outcomes `would fill` 2, `no actual expected` 1, `proprietary` 1, `not mapped` 1, `gate disabled` 1, `already filled` 1; DB unchanged.
  - `test_apply_fills_first_writer_wins_and_rerun_writes_zero`: `--apply` fills 2 with sources `bls` / `fed` and `classify_surprise` directions; a second run reports `filled` 0 and `already filled` 2.
  - `test_backlog_reports_revised_since_release`: JOLTS row 2026-09-01 with a later JOLTS row 2026-09-29 -> `revised since release`; the 2026-09-29 row -> `would fill`.
  - `test_unrevised_series_fills_older_rows_when_ff_previous_agrees`: crude rows 2026-10-14 and 2026-10-21 with the next row's previous matching -> both `would fill`; a mismatch -> `disagrees with FF previous`.
  - `test_source_error_and_key_inactive_outcomes`.
  - `test_main_dry_run_opens_db_read_only`, `test_main_exit_codes` (0 ok; 2 DB missing), `test_report_shows_sast_and_totals`.
- [ ] **Step 2: Run**: FAIL.
- [ ] **Step 3: Implement.** Select USD rows released between `since` and `now - ACTUALS_SLA_AFTER`; classify each with `coverage_for`, gate status and `decide_fill` (same `later_release` / `later_previous` lookup as the poller; share one helper in `registry.py` or `coverage.py` rather than duplicating it); one `fetch` for all needed specs; dry run opens the DB `mode=ro`; `--apply` writes with `store.fill_actual_if_missing` only (no backup here: the controller backs up `dashboard.db` first). `main`: `--db`, `--env-file`, `--since`, `--title` (repeatable), `--apply`, `--report PATH` (folder checked before any fetch, exit 4 if missing). The report ends with totals per outcome and the limitation line: "Official APIs serve today's revised numbers; older rows of revised series are left to the FRED/ALFRED backfill."
- [ ] **Step 4: Run**: PASS. **Full suites**.
- [ ] **Step 5: Live dry run (read-only).** `python scripts/backfill_official_actuals.py --db C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/webapp/dashboard.db --env-file C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/.env`. Record the totals per outcome and the per-title lines for the final summary (do not commit the output).
- [ ] **Step 6: Commit** `feat(ACT): backlog backfill script for official actuals (dry run by default)`.

## Task 6 — Docs: deploy runbook, coverage, inventory, roadmap  `[mechanical]`

**Files:** create `docs/actuals-deploy.md`, `tests/test_actuals_deploy_doc.py`; modify `docs/feature-inventory-2026-09-11.md` (one row), `docs/roadmap-2026-10-20.md` (new `### ACT. Release-time official actuals` section after B12, a batch-table row, and the status line "ACT built on branch actuals-release-poller (not merged)"; the controller reconciles status lines).

- [ ] **Step 1: Failing test** `tests/test_actuals_deploy_doc.py`: backup name `dashboard.db.pre_act_` present; "Dry run" appears before the first `--apply`; the rerun expectation `filled 0` present; a `## ... Rollback` heading exists; no `%TEMP%`, `$env:` or `\"`; every `scripts/*.py` named exists; the key check lists only names (`BLS_API_KEY`, `BEA_API_KEY`, `CENSUS_API_KEY`, `EIA_API_KEY`, `FRED_API_KEY`) and never prints a value; the 2026-10-29 12:30Z verification lists Advance GDP q/q, Advance GDP Price Index q/q, Core PCE Price Index m/m, Unemployment Claims, Personal Income m/m, Personal Spending m/m.
- [ ] **Step 2: Run**: FAIL.
- [ ] **Step 3: Write `docs/actuals-deploy.md`** (B10 runbook layout, commands from the live app dir, SAST with UTC):
  1. What changes (poller thread, SLA item, web-fallback queue removed, new sources `bls`/`bea`/`census`/`eia`/`fed`/`treasury`, claims via FRED; no schema change in `dashboard.db`; new table `official_source_status` in `ops_state.db` created on first connect; no scheduled-task or Telegram-type change).
  2. Backup: `python -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" webapp/dashboard.db webapp/dashboard.db.pre_act_<date>`.
  3. Stop the single engine copy (the B10 PowerShell commands).
  4. Merge `actuals-release-poller` into `news-engine/batch-predictions-queries`; fast-forward the live worktree; no push.
  5. Keys present (names only): `python -c "from data_layer.official_actuals.keys import load_keys; k=load_keys(); print({n: bool(getattr(k, n)) for n in ('bls','bea','census','eia','fred')})"` -> all True.
  6. Backlog: dry run, then `--apply`, then rerun (expect `filled 0`); quote the Task 5 live dry-run totals as the expected order of magnitude.
  7. Start exactly one copy (`schtasks /run /tn NewsEngine_AutoStart`); confirm `/api/health` has `actuals_sla` and the log shows `[release_poller]` lines; Federal Funds Rate 2026-10-28 is filled `4.00%` (source `fed`) by the start-up catch-up if the backlog did not already fill it.
  8. Verify on 2026-10-29 12:30Z (14:30 SAST): by 12:45Z every listed title is filled with its source (query given, mode=ro); a title that is gate-disabled (see the coverage table) is listed as such, not counted as a failure; `actuals_sla` is ok, or names exactly the gate-disabled titles.
  9. Web fallback: the engine no longer starts the git sync. No Claude routine or local scheduled task for it exists (RemoteTrigger list and `scheduled-tasks` checked 2026-10-28); the controller confirms on claude.ai's routines page and disables one there if found. The git-ignored clone `webapp/.actuals_sync/` may be deleted after the merge.
  10. Re-running the gate (new titles or after a code change): the Task 2 command with `--write-results`, then review, commit, merge and restart one copy (the poller reads the gate file once at start).
  11. Known limits: proprietary titles (list), not-mapped titles (list), DOL lag, Census key state, benchmark revisions, the stale FF GDP previous.
  12. Rollback: stop, revert the merge, restart one copy; restore `dashboard.db.pre_act_<date>` only to undo backlog fills (it loses rows written since the backup); to undo only ACT's fills: `UPDATE event_history SET actual=NULL, surprise_direction=NULL, source='live' WHERE source IN ('bls','bea','census','eia','fed','treasury')` (only ACT writes these labels; count first with SELECT; `updated_at_utc` is no filter because every FF upsert bumps it; claims fills carry `fred` and stay).
  Include the coverage table from `docs/superpowers/specs/2026-10-28-act-coverage.md` (title -> source -> gate result) verbatim.
- [ ] **Step 4: Inventory row** "Release-time official actuals" (files, Built on branch actuals-release-poller, not merged; detail: sources, cadence, SLA rule, gate summary counts, backlog dry-run totals, known gaps, deploy doc link).
- [ ] **Step 5: Run** the doc test: PASS. **Full suites**.
- [ ] **Step 6: Commit** `docs(ACT): deploy runbook, coverage table, inventory row and roadmap status`.
