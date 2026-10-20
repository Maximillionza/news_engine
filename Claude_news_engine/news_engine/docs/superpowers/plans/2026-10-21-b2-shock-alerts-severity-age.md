# B2 Shock alerts I — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Non-US events stop alerting High with buy/sell leans, every alert shows how old the story was when it was caught, and a classifier outage produces one visible Telegram notice a day.

**Architecture:** `alerting/store.py` gains six nullable columns on `shock_alerts` (added by an idempotent migration at connect) and a one-row-per-UTC-day `classifier_outage_notices` table. One merged table in a new `alerting/transmission.py` replaces both the channel table and the lean table, and adds the Fed-only FX leans and the bullion-tariff channel. `poll_once.py` reads country / US link from the classifier (or from a fixed rule-tier map) and caps no-US-link alerts at Medium with no lean. It also passes a freshness line and a cap note to Telegram. The API and the Shock Alerts tab show the same fields.

**Tech Stack:** Python 3 / SQLite / Flask, pytest; vanilla ES modules + `node --test`.

**Spec:** `docs/roadmap-2026-10-20.md` §B2 (K1-K8), plus these owner decisions:
- Freshness bands: Fresh <= 5 min, Delayed <= 15, Stale <= 60, Very stale > 60.
- Freshness is shown on every alert; nothing is suppressed for age.
- Provider order: Ollama first, Claude as fallback.
- At most one "classifier down" notice per UTC day.

Audit evidence: SA-01/02/03/06/07 and TX-2.

App dir for every command: `.worktrees/b2-shock-alerts/Claude_news_engine/news_engine`. Full suite = `python -m pytest -q -p no:warnings` (baseline 1326 passed) + `npm test` (baseline 205/205).

## Global Constraints

- **Migration:** idempotent, and it runs inside `store.get_connection()` (both the `:memory:` branch and the first-open branch). The live poller picks the code up on merge.
- **NULL means unknown:** every reader treats NULL in a new column as "unknown", which keeps today's behaviour: no cap, no age shown unless it can be derived from `sources_json[0]`.
- **Tests never touch the network or live data:**
  - LLM calls and Telegram are mocked.
  - `tests/conftest.py` (Task 1) blanks the Telegram config and points Ollama at a dead port.
  - Tests use temp/`:memory:` DBs only.
- **Times:** shown to the owner in SAST (`config.settings.LOCAL_TZ`); stored as UTC ISO.
- **Live system off-limits:** no change to `.worktrees/news-engine-live`, live `*.db`, scheduled tasks or real Telegram. No push.
- **Line endings:** every touched existing file is CRLF; keep CRLF. New files may be LF.
- **Commits:** each commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Out of scope:** URL memory / incident linking (B7), lean grading / `reality_check.py` (B10), near-miss log (B4).

## Review Focus

1. **Two processes migrating the same old DB at once.** The live poller and the webapp both hit an old-schema DB. One process's `ALTER TABLE` raises `duplicate column name` and the 2-minute poller crashes on every cycle.
   - Pinned by `test_migration_is_idempotent_on_an_old_schema_db_copy` and `test_migration_tolerates_a_concurrent_duplicate_column` (Task 1).
2. **Real network calls from tests.** Flipping the default order to Ollama-first makes every existing test that patches only `_call_claude` reach the real local Ollama, which is live on this box and may even get auto-started. A `.env` Telegram token could also send a real message.
   - Pinned by `test_guard_blanks_telegram_and_points_ollama_nowhere` (Task 1).
   - Pinned by the `claude_first` fixture and `_classify_with` patching `_call_ollama` (Task 4).
3. **The escalation path brings back a High with `us_link="none"`.** A corroborating article whose US link is unknown (for example a rule-tier hit) escalates a capped alert to High, and the stale "no US link" leans stay attached.
   - Pinned by `test_capped_alert_is_not_escalated_past_medium_by_an_article_with_unknown_us_link` and `test_global_supply_corroboration_lifts_the_cap_and_restores_leans` (Task 5).
4. **The outage notice misfires.** Two ways:
   - The budget-spent UNCLASSIFIED fallback is mistaken for an outage.
   - A failed Telegram send uses up the day's notice.

   Pinned by `test_budget_spent_fallback_never_sends_an_outage_notice` and `test_failed_notice_send_is_retried_and_success_is_once_per_utc_day` (Task 5).
5. **Freshness on awkward data.** Rows with no `first_published_utc`, garbage `sources_json`, naive timestamps or a feed clock ahead of ours (negative age) can crash the API or the tab, or show "+-3 min".
   - Pinned by `test_old_row_first_published_comes_from_first_source_or_is_none` (Task 1).
   - Pinned by `test_age_is_floored_clamped_and_naive_means_utc` (Task 6).
   - Pinned by `test_shock_alert_route_serves_freshness_for_old_rows` (Task 7).

---

### Task 1: Schema migration, new row fields, outage-notice table, test network guard (K1, K7 storage, K8 storage) — *judgment*

**Files:**
- Modify: `alerting/store.py`
- Create: `tests/conftest.py`
- Test: `tests/test_alerting_store.py`

**Interfaces (Produces):**
- `_SCHEMA` `shock_alerts` gains columns `polarity TEXT, country TEXT, us_link TEXT, capped_no_us_link INTEGER, original_severity TEXT, first_published_utc TEXT`. These are also declared in the `CREATE TABLE`.
  - Add no index on them inside `_SCHEMA`: it runs before the migration on an old DB, so an index there would fail.
- New table `classifier_outage_notices (utc_date TEXT PRIMARY KEY, sent_at_utc TEXT NOT NULL, detail TEXT)` in `_SCHEMA`.
- `_SHOCK_ALERT_ADDED_COLUMNS: tuple[tuple[str, str], ...]` (name, SQL type) and `_migrate_shock_alert_columns(conn: sqlite3.Connection) -> None`. It follows the `scoring/backtest_store.py:326-346` pattern:
  - Read `PRAGMA table_info(shock_alerts)`.
  - `ALTER TABLE ... ADD COLUMN` each missing column.
  - Swallow `sqlite3.OperationalError` only when the message contains `duplicate column name`; re-raise anything else.
  - Commit.
- `get_connection()` calls it right after `executescript(_SCHEMA)` in both branches.
- `ShockAlertRow` gains these fields, appended with default `None`:
  - `polarity: Optional[str]`, `country: Optional[str]`, `us_link: Optional[str]`
  - `capped_no_us_link: Optional[bool]`, `original_severity: Optional[str]`
  - `first_published_utc: Optional[dt.datetime]`
- `_row_to_shock_alert` reads `first_published_utc` from its column. If that is NULL, it falls back to `_first_source_published(sources: list[dict]) -> Optional[dt.datetime]`:
  - It parses `sources[0]["published_utc"]`. Index 0 is the source present at detection, because `append_source` only appends.
  - `None` on `IndexError/KeyError/TypeError/ValueError`.
  - A naive value is treated as UTC.
- `record_alert(...)` gains keyword-only `polarity=None, country=None, us_link=None, capped_no_us_link: Optional[bool]=None, original_severity=None`. It always writes `first_published_utc = published_utc.isoformat()`: at detection the alert has exactly one source, so that is the earliest. Existing callers stay valid.
- `update_alert_assessment(conn, alert_id: int, *, severity: str, polarity: Optional[str], country: Optional[str], us_link: Optional[str], capped_no_us_link: bool, original_severity: str, affected_symbols: list[dict]) -> None`. Used by Task 5's cap-lifting escalation.
- `outage_notice_sent(conn, utc_date: dt.date) -> bool` and `record_outage_notice(conn, utc_date: dt.date, sent_at_utc: dt.datetime, detail: str) -> None` (`INSERT OR IGNORE`).
- `tests/conftest.py` autouse fixture `_no_real_network(monkeypatch, tmp_path)`. It sets:
  - `alerting.notify_telegram.TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to `""`
  - `alerting.llm_classify.OLLAMA_BASE_URL` to `"http://127.0.0.1:9"`
  - `alerting.llm_classify.OLLAMA_EXECUTABLE` to `str(tmp_path / "no-ollama.exe")`
  - and it unsets `ANTHROPIC_API_KEY` with `monkeypatch.delenv(..., raising=False)`.

  Tests that patch these themselves still override them inside their own `with patch(...)`. `requests.post` is deliberately not patched globally, because other suites may rely on it.

- [ ] **Step 1: Write failing tests** in `tests/test_alerting_store.py`:
  - `test_migration_is_idempotent_on_an_old_schema_db_copy`:
    - Create a temp-file DB with the pre-B2 `CREATE TABLE shock_alerts` (copy the current 14-column literal into the test) and insert one row whose `sources_json` has `published_utc` `2026-10-06T10:07:00+00:00`.
    - Clear `store._schema_ready_paths`, call `get_connection(path)`, clear the cache, then call it again; also call `_migrate_shock_alert_columns` directly twice.
    - Assert all 6 columns exist exactly once and the old row survives with `polarity/country/us_link/capped_no_us_link/original_severity is None`.
    - Assert `first_published_utc == 2026-10-06 10:07 UTC` (derived from `sources[0]`).
  - `test_migration_tolerates_a_concurrent_duplicate_column`: a fake connection object whose `PRAGMA table_info` returns the old 14 columns and whose `ALTER` raises `sqlite3.OperationalError("duplicate column name: polarity")`. The migration returns without raising. A different `OperationalError` (`"disk I/O error"`) is re-raised.
  - `test_record_alert_round_trips_country_us_link_polarity_and_cap`: `country="RU", us_link="none", polarity="escalation", capped_no_us_link=True, original_severity="High"` read back identically, and `first_published_utc` equals `published_utc`.
  - `test_record_alert_without_new_fields_stores_unknowns_and_first_published`.
  - `test_old_row_first_published_comes_from_first_source_or_is_none`: sources `[{"published_utc": "2026-10-06T10:07:00"}, {"published_utc": "2026-10-06T09:00:00+00:00"}]` with the column NULL give 10:07 UTC (index 0, naive = UTC, not the min). `sources_json` = `"[]"` or a source missing the key gives `None`.
  - `test_update_alert_assessment_rewrites_cap_fields_and_leans`.
  - `test_outage_notice_is_one_row_per_utc_day`: `sent` is False, then record, then True for 2026-10-21; it is still False for 2026-10-22; a second record for the same day is ignored.
  - `test_guard_blanks_telegram_and_points_ollama_nowhere` (asserts the conftest values).
- [ ] **Step 2: Run** `python -m pytest tests/test_alerting_store.py -q -p no:warnings`. Expected: FAIL.
- [ ] **Step 3: Implement** as specified above. Keep the existing ready-cache comment and add one line: the cache is per process, so the 2-minute poller migrates on its first tick after the merge.
- [ ] **Step 4: Run** the store tests. Expected: PASS. Then run the full suite (both runners).
- [ ] **Step 5: Commit** `feat(alerting): store polarity, country, us_link, cap flag and first-published time on shock alerts (B2 K1)`.

### Task 2: One transmission table for channels and leans; Fed-only FX leans; no-US-link lean override (K5, K3 lean half) — *judgment*

**Files:**
- Create: `alerting/transmission.py`
- Modify: `alerting/direction.py`, `alerting/symbol_relevance.py`
- Test: `tests/test_alerting_direction.py` (rewrite the cross-table tests), `tests/test_alerting_symbol_relevance.py`

**Interfaces (Produces):**
- `transmission.Lean` (frozen dataclass `lean: str`, `why: str`), moved here from `direction.py`. `direction` re-exports it so `from alerting.direction import Lean` keeps working.
- `transmission.Transmission`, a frozen dataclass:
  - `channel: str`
  - `leans: Mapping[str, Lean]` (polarity -> Lean)
  - `us_only: bool = False`
  - `not_us_why: str = ""`
  - `headline_gate: Optional[re.Pattern[str]] = None` (the gate is used in Task 3)
- `transmission.TRANSMISSION: dict[tuple[str, str], Transmission]`, keyed `(category, symbol_class)`. It holds every current channel row plus `("energy", "oil_linked_fx")`, with channel `"oil_linkage"` and the two USDCAD leans. `transmission.OIL_LINKED_SYMBOLS = frozenset({"USDCAD"})`.
- New FX cells (`us_only=True`). Every lean is `buy`, `sell` or `mixed`, and each carries a `[convention]` tag:
  - `("central_bank", "fx_usd_base")`: hawkish `buy` ("a hawkish Fed lifts USD, so USD-base pairs rise"), dovish `sell`.
  - `("central_bank", "fx_usd_quote")`: hawkish `sell`, dovish `buy`.
  - For both, `not_us_why="which central bank is unknown or not the Fed"`.
  - `("sovereign_fiscal", "fx_usd_base"|"fx_usd_quote")`: escalation and relief are both `mixed` ("US fiscal stress can weaken USD on credit risk or lift it on haven demand"), with `not_us_why="which government is unknown or not the US"`.
- `direction.NO_US_LINK_WHY = "no direct US or global-supply link"`.
- `direction.lean_for(category: str, polarity: str, symbol_class: str, country: Optional[str] = None, us_link: Optional[str] = None) -> Lean` applies these rules in order:
  1. `us_link == "none"` -> `Lean("mixed", NO_US_LINK_WHY)`
  2. `polarity == "unclear"` -> the existing unclear lean
  3. no table entry -> `_MIXED_UNKNOWN`
  4. `us_only` and `country != "US"` -> `Lean("mixed", not_us_why)`
  5. otherwise `leans.get(polarity, _MIXED_UNKNOWN)`
- `direction.describe_impacts(impacts, category: str, polarity: str, country: Optional[str] = None, us_link: Optional[str] = None) -> list[dict]` has the same dict shape as today.
- `symbol_relevance.affected_symbols(category: str, tracked_symbols: list[str], headline: str = "") -> list[SymbolImpact]` reads `TRANSMISSION`. The USDCAD-under-energy special case is checked first, as today. `_CATEGORY_SYMBOL_CLASS_CHANNELS` and `_LEAN_TABLE` are deleted. `scripts/audit_fa_probes.py`'s call stays valid.

- [ ] **Step 1: Write failing tests** in `tests/test_alerting_direction.py`:
  - Freeze the pre-merge tables as test literals `_PRE_MERGE_CHANNELS` (category -> {class: channel}, copied from `symbol_relevance.py` today) and `_PRE_MERGE_LEANS` ((category, polarity, class) -> (lean, why), copied from `direction._LEAN_TABLE`). `test_unclear_polarity_is_always_mixed_never_a_guess` iterates `TRANSMISSION` instead of `_LEAN_TABLE`. Replace the two tests that imported `_CATEGORY_SYMBOL_CLASS_CHANNELS` / `_LEAN_TABLE` with:
    - `test_merged_table_keeps_every_pre_merge_channel`: for every cell, `TRANSMISSION[(cat, cls)].channel` matches; there are no extra keys except `("energy","oil_linked_fx")` and those added in Task 3.
    - `test_merged_table_keeps_every_pre_merge_lean`: every `_PRE_MERGE_LEANS` cell gives the same `lean_for(...).lean` and `why`, with `country=None, us_link=None`.
    - `test_every_transmission_has_a_deliberate_lean_for_each_relevant_polarity`: there is no FX exemption any more. central_bank -> hawkish/dovish, all others -> escalation/relief.
  - `test_fed_hawkish_lifts_usd_base_and_drops_usd_quote`: `lean_for("central_bank","hawkish","fx_usd_base",country="US").lean == "buy"`, `fx_usd_quote` -> `"sell"`, and dovish is the reverse.
  - `test_non_fed_or_unknown_central_bank_fx_is_mixed`: for `country` in `(None, "GB", "XX")`, the lean is `mixed` and `why == "which central bank is unknown or not the Fed"`.
  - `test_sovereign_fiscal_fx_is_mixed_even_for_the_us`.
  - `test_no_us_link_overrides_every_cell`: for every key in `TRANSMISSION` and every polarity in `POLARITIES`, `lean_for(..., us_link="none") == Lean("mixed", "no direct US or global-supply link")`.
  - `test_unknown_or_linked_us_link_keeps_todays_lean`: `us_link` in `(None, "direct", "global_supply")` gives the same lean as no argument, for every pre-merge cell.
  - Keep: `test_rule_polarity`, `test_normalize_polarity`, `test_lean_for_known_cells` (change the `fx_usd_quote` row to pass `country=None` and keep `mixed`), the unclear and unknown-combination tests, and the describe_impacts tests.
  - In `test_alerting_symbol_relevance.py`, add `test_usdcad_is_oil_linked_under_energy_and_usd_base_under_central_bank`: energy -> channel `oil_linkage`, class `oil_linked_fx`; central_bank -> `usd_relationship`, class `fx_usd_base`.
- [ ] **Step 2: Run** `python -m pytest tests/test_alerting_direction.py tests/test_alerting_symbol_relevance.py -q -p no:warnings`. Expected: FAIL (import errors, then the new FX cells).
- [ ] **Step 3: Implement.** Move each lean row verbatim, keeping its `[convention]` / `[Layer2]` tags and the shared `_GOLD_RATES_CONTESTED` / `_RELIEF_GOLD_MIXED` constants, into the `Transmission` entries. Move the module docstrings' provenance notes with them. `affected_symbols` iterates the tracked symbols as today and reads `TRANSMISSION.get((category, cls))`.
- [ ] **Step 4: Run** these tests, then `tests/test_alerting_poll_once.py`. Expected: PASS and behaviour unchanged. Then run the full suite.
- [ ] **Step 5: Commit** `refactor(alerting): one transmission table for channels and leans; Fed-only FX leans; no-US-link lean (B2 K5)`.

### Task 3: Bullion-tariff channel (K6) — *mechanical*

**Files:**
- Modify: `alerting/transmission.py`, `alerting/symbol_relevance.py`, `alerting/taxonomy.py`
- Test: `tests/test_alerting_symbol_relevance.py`, `tests/test_alerting_direction.py`, `tests/test_alerting_triage.py`

**Interfaces (Produces):**
- `transmission.BULLION_HEADLINE = re.compile(r"\b(?:gold|bullion|precious metals?)\b", re.IGNORECASE)`.
- New entry `("trade_policy", "metal")`:
  - `Transmission(channel="tariff_bullion", headline_gate=BULLION_HEADLINE, ...)`
  - escalation and relief both `Lean("mixed", "tariffs on bullion can move gold either way via the COMEX-London premium [convention]")`.
- `affected_symbols` skips any entry whose `headline_gate` does not `search(headline)`.
- `taxonomy.CATEGORY_SIGNAL_KEYWORDS["trade_policy"]` gains `"tariffs on gold", "tariff on gold", "gold tariff", "tariffs on bullion", "tariff on bullion", "bullion tariff"`. This is a triage-only addition so that a gold-bar tariff headline is caught at all. Today none of the trade_policy keywords would match "US slaps tariffs on gold bars". It is not a hard rule, so the LLM still judges severity.

- [ ] **Step 1: Write failing tests:**
  - `test_gold_bar_tariff_headline_reaches_xauusd_via_tariff_bullion`: `affected_symbols("trade_policy", ["XAUUSD","US30"], headline="US slaps tariffs on imported gold bars")` gives `{"XAUUSD": "tariff_bullion", "US30": "risk_sentiment"}`.
  - `test_diesel_export_ban_reaches_us30_only`: `headline="Russia extends diesel export ban to year-end"` gives `["US30"]`.
  - `test_bullion_gate_is_a_word_match`: "Goldman Sachs warns on tariffs" does not reach XAUUSD; "Tariffs on Precious Metals widen" and "BULLION tariff talk" do.
  - `test_no_headline_means_no_bullion_channel`: the default `headline=""` gives US30 only.
  - Direction: `lean_for("trade_policy","escalation","metal").lean == "mixed"` and `"COMEX" in why`; same for relief.
  - Triage: `triage_article(<"US slaps tariffs on gold bars">)` returns category `trade_policy`, `rule_tier_hit is False`.
- [ ] **Step 2: Run** these three test files. Expected: FAIL.
- [ ] **Step 3: Implement** the entry, the gate check and the keywords. Update `test_merged_table_keeps_every_pre_merge_channel`'s allowed-extra-keys set to include `("trade_policy","metal")`.
- [ ] **Step 4: Run.** Expected: PASS. Then run the full suite.
- [ ] **Step 5: Commit** `feat(alerting): tariffs on gold or bullion reach XAUUSD with a mixed lean (B2 K6)`.

### Task 4: Classifier country and US link, real-feed polarity examples, Ollama-first order, rule-tier map (K2, K4, K8 order) — *judgment*

**Files:**
- Create: `alerting/us_link.py`
- Modify: `alerting/llm_classify.py`, `config/settings.py`
- Test: `tests/test_alerting_llm_classify.py`, new `tests/test_alerting_us_link.py`

**Interfaces (Produces):**
- `settings.CLASSIFIER_PROVIDER_ORDER: tuple[str, ...] = ("ollama", "claude")`, with a comment giving the owner decision and the 2026-10-21 date (Anthropic credits exhausted). Update the block comment above the Claude/Ollama settings and the `llm_classify` module docstring to match.
- `llm_classify._providers()` builds `{"claude": (...), "ollama": (...)}` and returns entries in `CLASSIFIER_PROVIDER_ORDER` order, skipping unknown names.
- `ClassificationResult` gains:
  - `country: Optional[str] = None` (ISO-2 or `"XX"`; None = unknown)
  - `us_link: Optional[str] = None` (`"direct"|"global_supply"|"none"`; None = unknown)
  - `all_providers_failed: bool = False`, set True only in `classify_candidate`'s all-failed return.
- `us_link.US_LINKS = ("direct", "global_supply", "none")`.
- `us_link.normalize_country(raw) -> Optional[str]`:
  - Strip and uppercase.
  - Synonyms `{"USA": "US", "U.S.": "US", "U.S": "US", "UNITED STATES": "US", "GLOBAL": "XX", "MULTIPLE": "XX"}`.
  - Accept only `^[A-Z]{2}$`; everything else is None.
- `us_link.normalize_us_link(raw) -> Optional[str]`: lowercase, spaces and hyphens become `_`, and the result must be in `US_LINKS`; otherwise None.
- `us_link.reconcile(country, us_link) -> Optional[str]`: `country == "US"` means `"direct"`. US territory or actors are "direct" by definition, so a model's `"none"` or omission for a US event is overridden. Otherwise the input passes through.
- `llm_classify._extract_country_and_us_link(text: str) -> tuple[Optional[str], Optional[str]]` is best-effort like `_extract_polarity`. Any exception gives `(None, None)`, and it never fails the classification.
- `us_link._RULE_COUNTRY_US_LINK: dict[str, tuple[Optional[str], Optional[str]]]` has one entry for every `HARD_RULE_PATTERNS` phrase:
  - Every `strait of hormuz *` pattern, `bab el-mandeb closed`, `suez canal blocked` and all three `opec+ *` patterns: `("XX", "global_supply")`.
  - `oil export ban`: `(None, "global_supply")`.
  - `fed chair fired`, `fed chair resigns`: `("US", "direct")`.
  - All others: `(None, None)`. These are `tanker attacked`, `pipeline attack`, war/invasion, `emergency rate decision`, `unscheduled rate cut/hike`, `sovereign default`, `credit rating downgraded` and `retaliatory tariffs announced`, because the phrase does not name the actor.
  - Deliberate deviation: the brief's example mapped unscheduled rate cut/hike to US/direct. The phrase does not name the Fed, and US/direct would give USD pairs a firm buy/sell lean on, say, a Turkish emergency hike. Change one line if the owner wants it.
- `us_link.rule_country_us_link(matched_keywords: Iterable[str]) -> tuple[Optional[str], Optional[str]]`: first known pattern wins, `(None, None)` if none.
- `us_link.cap_severity(severity: str, us_link: Optional[str]) -> tuple[str, bool]`: `"none"` -> `(min(severity, "Medium") by rank, True)`; otherwise `(severity, False)`.
- `us_link.cap_note(original_severity: Optional[str], capped: Optional[bool]) -> Optional[str]`:
  - Not capped -> None.
  - Original was High -> `"Capped High -> Medium: no direct US or global-supply link"`.
  - Otherwise -> `"No buy/sell lean: no direct US or global-supply link"`.
- **Prompt changes (`_build_prompt`):**
  - A country line: ISO 3166-1 alpha-2 of where it happens or the main actor, `"XX"` for global or several countries.
  - A US-link guide whose three definitions match K2 word for word in substance.
  - The rule `If us_link is "none", severity is at most "Medium".`
  - Three us_link examples that are not the acceptance headlines: `"Fed chair signals emergency cut -> US, direct"`, `"Tanker struck near Strait of Hormuz -> XX, global_supply"`, `"Protesters clash with police in Lima -> PE, none"`.
  - K4 polarity examples, added to the existing four: `"Oil prices fall as traders watch ceasefire talks -> relief"`, `"Trump waives broad new Russia sanctions -> relief"`, `"Brent oil touches $110 as Iran escalates Hormuz attacks -> escalation"`.
  - The JSON shape gains `"country": "<ISO-2 code or XX>", "us_link": "direct"|"global_supply"|"none"`.

- [ ] **Step 1: Write failing tests.**
  - **Test isolation first:** in `tests/test_alerting_llm_classify.py`, add fixture `claude_first`, which patches `llm_classify.CLASSIFIER_PROVIDER_ORDER` to `("claude","ollama")`. Apply it to every existing chain test whose meaning is Claude-specific:
    - claude success / failure / unusable / cooldown / retry-after-cooldown
    - the two SDK-unavailable tests
    - all-fail and invalid-category

    Change `_classify_with` to patch `_call_ollama` (and `_call_claude` with `side_effect=AssertionError`).
  - New tests in `test_alerting_llm_classify.py`:
    - `test_default_order_is_ollama_then_claude`: `[p[0] for p in _providers()] == ["ollama","claude"]`. With Ollama returning `_GOOD`, Claude is never called and `provider == "ollama"`.
    - `test_ollama_failure_falls_back_to_claude`.
    - `test_unknown_provider_name_in_order_is_skipped`.
    - `test_country_and_us_link_are_parsed`: `'{"category":"geopolitical_conflict","severity":"High","polarity":"escalation","country":"ru","us_link":"None","rationale":"x"}'` gives `("RU","none")`.
    - `test_country_is_normalized_best_effort`, parametrized: `"USA"`/`"United States"` -> `"US"` and us_link `"direct"` via reconcile; `"Russia"` -> None; `"global"` -> `"XX"`; `"us_link": "global supply"` -> `"global_supply"`.
    - `test_missing_or_garbled_country_and_us_link_are_unknown_and_never_fail_classification`, three bodies: missing, `null`, nonsense. Each gives `(None, None)`, `classification_failed is False`, and category/severity are kept.
    - `test_all_providers_failed_sets_the_outage_flag` (and `country`/`us_link` stay None).
    - `test_prompt_asks_for_country_and_us_link_and_caps_none_at_medium`: `'"country"'`, `'"us_link"'`, `"global_supply"`, `"XX"` and `'at most "Medium"'` are all in the prompt.
    - `test_prompt_carries_real_feed_polarity_examples`: `"Trump waives broad new Russia sanctions -> relief"` and `"Brent oil touches $110 as Iran escalates Hormuz attacks -> escalation"` are in the prompt.
    - `test_prompt_fits_the_ollama_context`: `len(prompt) / 3 + 200 < OLLAMA_NUM_CTX`.
  - New `tests/test_alerting_us_link.py`:
    - `test_every_hard_rule_pattern_has_a_deliberate_country_and_us_link`: the key set equals the union of `HARD_RULE_PATTERNS`; values are in `US_LINKS + (None,)`.
    - `test_rule_map_examples`: hormuz -> `("XX","global_supply")`, `opec+ agrees to cut` -> `("XX","global_supply")`, `fed chair fired` -> `("US","direct")`, `declares war` -> `(None, None)`.
    - `test_cap_severity`: High/none -> (`"Medium"`, True); Low/none -> (`"Low"`, True); High/None, High/direct, High/global_supply -> (`"High"`, False).
    - `test_cap_note_wording`.
- [ ] **Step 2: Run** `python -m pytest tests/test_alerting_llm_classify.py tests/test_alerting_us_link.py -q -p no:warnings`. Expected: FAIL.
- [ ] **Step 3: Implement** as specified. `classify_candidate` attaches `country, us_link = reconcile(...)` to the success result.
- [ ] **Step 4: Run.** Expected: PASS. Then run the full suite.
- [ ] **Step 5: Commit** `feat(alerting): classifier reports country and US link, real-feed polarity examples, Ollama first (B2 K2 K4 K8)`.

### Task 5: Wire the cap, the new fields, the escalation path and the daily outage notice into the poller (K3, K1 wiring, K8 notice) — *integration*

**Files:**
- Modify: `alerting/poll_once.py`, `alerting/notify_telegram.py`
- Test: `tests/test_alerting_poll_once.py`, `tests/test_alerting_notify_telegram.py`

**Interfaces (Consumes):**
- From Task 1: `store.record_alert` kwargs, `store.update_alert_assessment`, `store.outage_notice_sent`, `store.record_outage_notice`.
- From Task 2: `direction.describe_impacts(..., country=, us_link=)`.
- From Task 3: `affected_symbols(..., headline=)`.
- From Task 4: `ClassificationResult.country/us_link/all_providers_failed`, `us_link.rule_country_us_link`, `cap_severity`, `cap_note`.

**Interfaces (Produces):**
- `notify_telegram._post_text(text: str) -> bool`: the existing retry loop, extracted unchanged.
- `notify_telegram.send_notice(text: str) -> bool`: plain text through `_post_text`, never raises.
- `notify_telegram.send_alert(..., cap_note: Optional[str] = None)`: when given, the cap note is its own line after the Affects block.
- **`poll_once._process_matched`:**
  - It takes `raw_severity` and `country, us_link` from the rule map (rule tier), the classification (LLM), or `(None, None)` (failed or budget fallback). Then `severity, capped = cap_severity(raw_severity, us_link)`.
  - A new alert is recorded with `polarity, country, us_link, capped_no_us_link=capped, original_severity=raw_severity`, and leans come from `describe_impacts(affected_symbols(category, tracked, headline=article.title), category, polarity, country=country, us_link=us_link)`.
  - The push gets `cap_note=cap_note(raw_severity, capped)`.
  - `_should_push` is unchanged, so a capped Medium is still pushed with `TELEGRAM_MIN_SEVERITY="Low"`.
- **`poll_once._maybe_escalate(conn, webapp_conn, alert_id, new_category, raw_new_severity, new_rationale, new_classification_failed=False, *, polarity=None, country=None, us_link=None)`:**
  - `effective = us_link if us_link is not None else existing.us_link`, so an unknown link inherits the stored one.
  - `new_severity, _ = cap_severity(raw_new_severity, effective)`, then the existing never-downgrade compare.
  - When escalating:
    - If `existing.capped_no_us_link` and `effective in ("direct","global_supply")`, the cap is lifted. Recompute leans for `existing.headline` and call `store.update_alert_assessment(..., capped_no_us_link=False, original_severity=raw_new_severity)`.
    - Otherwise call `store.set_severity` as today.
  - Push with the (possibly recomputed) affected symbols.
- **`poll_once._maybe_notify_classifier_down(conn, detail: str, now: dt.datetime) -> None`:**
  - Called from `_process_matched` only when `classification.all_providers_failed`, after the alert's own push.
  - If `store.outage_notice_sent(conn, now.date())` it returns.
  - Otherwise it sends `notify_telegram.send_notice(...)`. The text: "⚠️ Shock classifier down: every provider failed (<detail, cut to 300 chars>). Alerts keep going out as UNCLASSIFIED until it recovers. This notice is sent at most once per UTC day."
  - It calls `store.record_outage_notice` only if the send returned True.

- [ ] **Step 1: Write failing tests** in `tests/test_alerting_poll_once.py`, reusing `_run_tracking_xau_us30` (extend it to return `(stored_alert, send)` and to accept `classification` and `triage`):
  - **Acceptance replay** `test_no_us_link_events_are_not_high_and_carry_no_lean`, parametrized over:
    - ("Russia's Yandex says data centre in Vladimir area shut down after drone attack", "geopolitical_conflict", "RU")
    - ("Russia builds major new drone attack base", "geopolitical_conflict", "RU")
    - ("Houthi attack on Yemeni government military camp", "energy", "YE")
    - ("Unrest spreads across France as protesters clash with police", "geopolitical_conflict", "FR")

    The mocked classification is `severity="High", polarity="escalation", provider="ollama", us_link="none"` with that country. Assert:
    - stored `severity == "Medium"`, `original_severity == "High"`, `capped_no_us_link is True`, `us_link == "none"`, and `country` stored.
    - every stored lean is `"mixed"` with `lean_why == "no direct US or global-supply link"`.
    - the push has `args[2] == "Medium"`, `kwargs["cap_note"]` contains `"no direct US or global-supply link"`, and there is no `"buy"`/`"sell"` in the pushed leans.
  - `test_unknown_us_link_keeps_todays_high_and_leans`: the same Yandex headline with `us_link=None` stays High, XAUUSD buy / US30 sell, `capped_no_us_link is False`.
  - `test_global_supply_high_keeps_its_leans`.
  - `test_rule_tier_hit_stores_its_mapped_country_and_us_link`: Hormuz is stored as `XX`/`global_supply`/`escalation`, High.
  - `test_gold_bar_tariff_alert_reaches_xauusd_with_a_mixed_lean`: the trade_policy classification (High, escalation, `"US"`, `"direct"`) of "US slaps tariffs on imported gold bars" stores XAUUSD with channel `tariff_bullion`, lean `mixed`, and US30 `sell`.
  - `test_diesel_export_ban_alert_reaches_us30_only`.
  - `test_capped_alert_is_not_escalated_past_medium_by_an_article_with_unknown_us_link`: an existing capped RU alert (Medium, `us_link="none"`, capped) plus a rule-tier/unknown-link High corroboration leaves it Medium, with no push.
  - `test_global_supply_corroboration_lifts_the_cap_and_restores_leans`: the same existing alert plus a classification that is High, escalation, `"XX"`, `"global_supply"` gives High, `capped_no_us_link False`, XAUUSD `buy` / US30 `sell` stored and pushed, and `is_escalation=True`.
  - `test_outage_notice_sent_once_per_utc_day`: two cycles on the same day with `all_providers_failed=True` give `send_notice` called once and one row. A cycle with `now` patched to the next UTC day sends again.
  - `test_failed_notice_send_is_retried_and_success_is_once_per_utc_day`: `send_notice` returns False and then True gives two calls, then no more that day.
  - `test_budget_spent_fallback_never_sends_an_outage_notice` (with `LLM_CYCLE_BUDGET_SECONDS=0`).
  - In `test_alerting_notify_telegram.py`:
    - `test_cap_note_is_its_own_line`.
    - `test_send_notice_posts_plain_text_and_never_raises`: 200 gives True; a `RequestException` gives False after the retries; the posted `text` equals the input.

  Patch `alerting.poll_once.notify_telegram.send_notice` in every new poll test. `now` in poll_once comes from `dt.datetime.now(dt.timezone.utc)`. Make it patchable via a module-level `_utcnow()` seam.
- [ ] **Step 2: Run** `python -m pytest tests/test_alerting_poll_once.py tests/test_alerting_notify_telegram.py -q -p no:warnings`. Expected: FAIL.
- [ ] **Step 3: Implement** as specified. Keep the existing `_maybe_escalate` docstring and extend it with the inherit-the-stored-link rule and why: otherwise a hard-rule corroboration would bring back a no-US-link High.
- [ ] **Step 4: Run.** Expected: PASS. All pre-existing poll_once tests stay green unchanged. Then run the full suite.
- [ ] **Step 5: Commit** `feat(alerting): cap no-US-link alerts at Medium with no lean, escalation path, daily classifier-down notice (B2 K3 K8)`.

### Task 6: Freshness band on Telegram (K7, push side) — *integration*

**Files:**
- Create: `alerting/freshness.py`
- Modify: `config/settings.py`, `alerting/notify_telegram.py`, `alerting/poll_once.py`
- Test: new `tests/test_alerting_freshness.py`, `tests/test_alerting_notify_telegram.py`, `tests/test_alerting_poll_once.py`

**Interfaces (Produces):**
- Settings, next to `TELEGRAM_MIN_SEVERITY`, with a comment citing the owner decision of 2026-10-21: `SHOCK_FRESH_MAX_MINUTES = 5`, `SHOCK_DELAYED_MAX_MINUTES = 15`, `SHOCK_STALE_MAX_MINUTES = 60`.
- `freshness.age_minutes(first_published_utc: Optional[dt.datetime], detected_at_utc: dt.datetime) -> Optional[int]`:
  - None if the first argument is None.
  - A naive datetime is treated as UTC.
  - The result is the floor of the minutes, clamped to `>= 0` (a feed clock ahead of ours reads +0).
- `freshness.freshness_band(age: Optional[int]) -> Optional[str]`: `<= 5` gives `"Fresh"`, `<= 15` `"Delayed"`, `<= 60` `"Stale"`, otherwise `"Very stale"`; None gives None.
- `freshness.freshness_line(first_published_utc, detected_at_utc) -> Optional[str]`:
  - Format: `"Published 14:42 SAST · +2 min · Fresh"`, with the time in `LOCAL_TZ`, `%H:%M`.
  - When the SAST date of publication differs from the SAST date of detection, it shows `"Published 20 Oct 14:42 SAST · …"`.
  - None when the age is None.
- `send_alert(..., freshness_line: Optional[str] = None)`: a line directly under the headline.
- `poll_once`: computes `detected_at` once and uses it for `record_alert` and for `freshness_line(article.published_utc, detected_at)`. Escalation pushes use `freshness_line(existing.first_published_utc, existing.detected_at_utc)`. The alert is always sent; age never suppresses it.

- [ ] **Step 1: Write failing tests:**
  - `test_bands_at_their_edges`, parametrized: 0, 5 -> Fresh; 6, 15 -> Delayed; 16, 60 -> Stale; 61, 465 -> Very stale.
  - `test_age_is_floored_clamped_and_naive_means_utc`:
    - published 12:40:00, detected 12:45:59 gives 5 (Fresh).
    - published 12:50, detected 12:45 gives 0.
    - a naive 12:40 equals the aware 12:40 UTC.
  - `test_line_shows_published_time_in_sast_minutes_and_band`: published 2026-10-21 12:40Z, detected 12:42Z gives exactly `"Published 14:40 SAST · +2 min · Fresh"`.
  - `test_line_adds_the_date_when_the_story_is_from_an_earlier_day` (the #56 shape: 465 min, Very stale).
  - `test_no_first_published_means_no_line`.
  - Telegram: `test_freshness_line_sits_under_the_headline`, where the sent text contains `"+2 min"`, `"SAST"` and `"Fresh"` on the line after the headline.
  - Poll: `test_pushed_alert_carries_its_freshness_line`: the article was published 3 minutes before the patched `_utcnow()`, so `kwargs["freshness_line"]` ends with `"+3 min · Fresh"`. Also `test_escalation_push_shows_the_original_story_age`.
- [ ] **Step 2: Run** these three test files. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS. Then run the full suite.
- [ ] **Step 5: Commit** `feat(alerting): published time, age and freshness band on every shock-alert push (B2 K7)`.

### Task 7: API serializer and Shock Alerts tab (K7 display, K1/K3 display) — *integration*

**Files:**
- Modify: `webapp/app.py` (`get_shock_alerts`), `webapp/static/js/shock-alerts/table.js`
- Create: `webapp/static/js/shock-alerts/alert-meta.js`, `webapp/static/js/shock-alerts/alert-meta.test.js`
- Test: `tests/test_app_shock_alerts_route.py`

**Interfaces (Produces):**
- Each row in `/api/shock-alerts` gains exactly these keys:
  - `polarity`, `country`, `us_link`
  - `capped_no_us_link` (bool or null), `original_severity`
  - `first_published_utc` (ISO or null)
  - `age_minutes` (int or null, via `freshness.age_minutes`), `freshness_band` (str or null)
- The full key set is: `id, headline, sources, detected_at_utc, category, severity, classification_method, rationale, affected_symbols, delivery_status, reality_mismatch, polarity, country, us_link, capped_no_us_link, original_severity, first_published_utc, age_minutes, freshness_band`.
- `alert-meta.js`, pure, no DOM:
  - `freshnessText(row) -> string`: `""` when `first_published_utc` or `age_minutes` is null. Otherwise `` `Published ${HH:MM} SAST · +${age_minutes} min · ${freshness_band}` ``, with the time formatted by `Intl.DateTimeFormat("en-GB", {timeZone: "Africa/Johannesburg", hour: "2-digit", minute: "2-digit", hourCycle: "h23"})`.
  - `contextTagsText(row) -> string`: joins the known parts `Where: RU`, `US link: none` (underscores become spaces) and `Polarity: escalation` with `" · "`; `""` when all are null.
  - `capBadgeHtml(row) -> string`: when `capped_no_us_link === true`, a span reading `capped: no US or global-supply link`, plus ` (classifier said High)` when `original_severity` differs from `severity`; otherwise `""`. Escaped with `escapeHtml`.
- `table.js` card:
  - the cap badge after the severity header;
  - a `meta-text-sm` line with `contextTagsText` when non-empty;
  - the freshness text appended to the existing detection-time line.

- [ ] **Step 1: Write failing tests:**
  - `test_shock_alert_route_row_key_set_is_exact`: `set(row) ==` the 19 keys above.
  - `test_shock_alert_route_serves_new_fields`: recorded with RU/none/escalation/capped/original High and published 12:40, detected 12:42. The row has `age_minutes == 2`, `freshness_band == "Fresh"` and the values round-tripped.
  - `test_shock_alert_route_serves_freshness_for_old_rows`:
    - An alert whose new columns are set to NULL by a direct `UPDATE` (simulating a pre-B2 row) has `first_published_utc` from `sources[0]` and `age_minutes` computed, while `country/us_link/polarity/capped_no_us_link` are null.
    - With `sources_json='[]'`, `first_published_utc`, `age_minutes` and `freshness_band` are all null and the status is 200.
  - Keep the two existing route tests unchanged.
  - `alert-meta.test.js`:
    - `"2026-10-21T12:42:00+00:00"` with age 2 / Fresh gives `"Published 14:42 SAST · +2 min · Fresh"`.
    - An old row (null fields) gives `""` from all three functions.
    - The tags join correctly and `global_supply` renders as `"global supply"`.
    - The cap badge shows `(classifier said High)` only when severities differ.
    - An injected `<script>` in `country` is escaped in the badge/tag HTML path.
- [ ] **Step 2: Run** `python -m pytest tests/test_app_shock_alerts_route.py -q -p no:warnings` and `npm test`. Expected: FAIL.
- [ ] **Step 3: Implement** the serializer and the JS. The serializer imports `alerting.freshness`.
- [ ] **Step 4: Run.** Expected: PASS. Then run the full suite. Optionally, eyeball the tab with a local Flask run against a temp copy DB, never the live DB.
- [ ] **Step 5: Commit** `feat(webapp): shock-alert API and tab show story age, country, US link and the no-US-link cap (B2 K7)`.

### Task 8: Docs — *mechanical*

**Files:**
- Modify: `docs/feature-inventory-2026-09-11.md`, `docs/roadmap-2026-10-20.md` (both CRLF)

- [ ] **Step 1:** In the feature inventory, add a B2 row describing what was built:
  - six new columns with an idempotent migration (NULL = unknown);
  - classifier country/us_link plus the rule-tier map;
  - the no-US-link cap (Medium, no lean, `capped_no_us_link`, and an escalation path that lifts the cap only on a direct/global_supply corroboration);
  - real-feed polarity examples;
  - the merged `alerting/transmission.py` with Fed-only FX leans;
  - the `tariff_bullion` channel plus triage keywords;
  - freshness bands (5/15/60) on Telegram, the API and the tab;
  - Ollama-first `CLASSIFIER_PROVIDER_ORDER` and the once-per-UTC-day classifier-down notice;
  - the noted deviation: unscheduled rate cut/hike maps to unknown, not US.

  In the "Roadmap 2026-10-20" table, set B1 to `done 2026-10-21` and B2 to `built on branch b2-shock-alerts`.
- [ ] **Step 2:** In `docs/roadmap-2026-10-20.md`, change the status line to `> Status 2026-10-21: approved by owner ('proceed'); B1 done 2026-10-21; B2 built on branch b2-shock-alerts (not yet merged). Progress is tracked in the feature inventory.`
- [ ] **Step 3:** Run the full suite once more (expect 1326 + new tests passing, npm 205 + new tests passing). Then commit `docs: feature inventory and roadmap status for B2 shock alerts`.

---

## Self-review against the spec

- **Every K-item has a task:**
  - K1: Tasks 1 and 5
  - K2: Tasks 4 and 5
  - K3: Task 2 (leans) and Task 5 (severity, flag, escalation)
  - K4: Task 4
  - K5: Task 2
  - K6: Task 3
  - K7: Tasks 1, 6 and 7
  - K8: Task 4 (order) and Task 5 (notice)
- **Every acceptance test is placed:**
  - The four replay headlines: Task 5.
  - Gold-bar tariff reaches XAUUSD with a mixed lean: Tasks 3 and 5.
  - Diesel export ban reaches US30 only: Tasks 3 and 5.
  - Telegram shows SAST time, +N min and the band: Task 6.
  - Idempotent migration on an old-schema copy: Task 1.
  - Outage notice at most once per day: Task 5.
- **Names stay consistent across tasks:** `capped_no_us_link`, `original_severity`, `first_published_utc`, `us_link`, `CLASSIFIER_PROVIDER_ORDER`, `NO_US_LINK_WHY`, `cap_note`, `freshness_line`, `all_providers_failed`, `send_notice`.
- **Live-week metric:** "0 High alerts with `us_link=none`" is guaranteed structurally. `cap_severity` runs on both the new-alert path and the escalation path, and an unknown link inherits the stored one. The new-field fill rate can be read from the columns. Reporting it is a post-merge check, not code.
