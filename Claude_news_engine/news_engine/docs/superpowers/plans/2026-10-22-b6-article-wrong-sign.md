# B6 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Foreign central-bank and off-topic articles stop voting on US events (FOMC and CPI families first), precursor links use their authored weights, non-USD calendar rows give no surprise, a re-stamped URL counts once, and every article behind each recorded accumulator prediction (included and excluded, with the reason) is saved so sources can later be graded by outcome. This batch changes how article-based calls are scored; the change date is logged.

**Architecture:** One new pure module, `data_layer/subject_rules.py`, holds every name list and rule (foreign central banks, Fed co-terms, the title subject rule) so B7/K-series and shock-alert country tagging can reuse it. `data_layer/event_context.py` partitions fetched articles into kept and excluded-with-reason, then drops same-URL repeats (keep the earliest); `EventNewsBundle` carries the exclusions. `scoring/probability_engine.py` takes precursor trust from `EVENT_INFLUENCE_LINKS`; `scoring/backtest_accumulator.py` writes every included and excluded article of each recorded prediction to a new append-only table in `scoring/backtest_store.py`; a read-only script measures how much of the stored history the new rules would have removed.

**Tech Stack:** Python 3.14, sqlite3 (URI `mode=ro` for the live read), `re`, `urllib.parse`, pytest; `npm test` must stay green (no JS change).

**Spec:** `docs/roadmap-2026-10-20.md` §B6 (A1-A7), plus these owner decisions:
- A1: foreign-CB exclusion in one module, applied for every event title; generic FOMC terms ('interest rate decision', 'monetary policy', 'rate hike', 'rate cut', 'central bank') need a Fed co-term (fed, fomc, federal reserve, warsh, powell, named FOMC members); audit Probe 1 ported to tests for the FOMC and CPI families (ECB/BoE/BoJ/RBA dropped, Fed/Warsh kept).
- A2 (owner decision 8: a title filter, not the LLM tier): FOMC and CPI families score only articles whose TITLE names the dollar/USD/greenback, the Fed/FOMC/Federal Reserve/Fed officials, US rates/Treasury yields, or (CPI family) US/American inflation/CPI. 'Gold edges up as October rate hike bets ease, stronger dollar cap gains' is NOT scored for FOMC. Other titles unchanged.
- A3: precursor trust = the authored `EVENT_INFLUENCE_LINKS` weight (JOLTS->NFP 0.40; ADP->NFP and PPI->CPI 0.90); 72h decay and the chain-conflict dampener unchanged.
- A4: `usd_surprise_score()` returns None for any non-USD row.
- A5: same URL under two headlines counts once (earliest kept); fix the stale redundancy comment (DOC-01).
- A6 (owner ruling 9): append-only `prediction_article_contributions`, every article (not top 3) with title, url, source, published_utc, sentiment, weight, trust, decay, included/excluded + reason; final pre-event prediction retrievable per (event_title, event_time_utc, instrument); CREATE IF NOT EXISTS.
- A7: read-only before/after report over stored `top_contributions_json`, real numbers from the live DB opened `mode=ro`.
- Out of scope: same-incident discount across 72h (B7), standardized surprise (B8), Stats News rule (B9), CB stance model (parked).

Audit evidence: AUD-P0-1, AS-01, AS-02, AS-04, DOC-01 (`explore_C.json`), DEAD-1 (`explore_A.json`).

App dir for every command: `.worktrees/b6-article-wrong-sign/Claude_news_engine/news_engine`. Full suite = `python -m pytest -q -p no:warnings` + `npm test`. Known env-only failure (no `.env` in a worktree): `tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present`; ignore it, everything else must pass. Baseline at 7a3fa45: 1736 passed, 1 env-only failure.

## Choices made in this plan (owner can veto before Task 1)

- **Bare "Bailey" / "Pill" are not matched**, only "Andrew Bailey", "Huw Pill" or the BoE name ("poison pill", "weight-loss pill" would drop real articles). The live offenders all say "BoE" or "Bank of England".
- **A foreign CB in the title always excludes**, even when the title leads with the dollar ("Dollar languishes as inflation awaited; Euro edges up on Lagarde warning"): the sign can't be pinned to the US side. A foreign CB in the summary excludes only when the title names neither the US nor the Fed.
- **Dollar-only titles that lead with another asset are off-subject** for FOMC/CPI (the gold headline); a title that names the Fed is kept whatever it leads with ("Gold miners rally as Fed signals rate cut", an existing test).
- **CPI family:** bare "CPI" counts unless the title names a foreign place; bare "inflation" does not count without a US qualifier.
- **"economic projections" stays a keyword** but is not a Fed co-term (ECB "macroeconomic projections" contains it).
- **Evidence is written for every recorded prediction** (append-only), and the final pre-event one is selected at read time: the accumulator cannot know at write time which snapshot will be the last before the release. Estimated growth ~10 MB/month at current volume.
- **Keyword misses are not recorded as exclusions** (hundreds per event); only articles that matched an event's keywords and were then dropped by a guard are.
- **JOLTS stays dormant:** "JOLTS Job Openings" has no `EVENT_SURPRISE_DIRECTION` entry, so it never produces a surprise; A3 makes its link weight 0.40 (tested with a patched direction map) but adding the direction entry is a new signal, not part of A3.
- **The print-direction call shares the filtered bundle,** so CPI print calls also lose foreign/off-subject articles (intended: same evidence, one rule).

## Global Constraints

- **Live system off-limits:** nothing under `.worktrees/news-engine-live` is modified; its `scoring/backtest_log.db` is opened only by Task 4's `open_readonly` (`mode=ro`). No Windows or Claude scheduled task, no Telegram, no push.
- **Nothing outside the repo needs deploying:** the new table is created by `get_connection()` on the accumulator's first cycle; the deploy is a backup plus a restart (`docs/b6-deploy.md`, applied at deploy by the controller).
- **Tests:** temp DBs and stub sources only; FinBERT/LLM are not called (conftest blanks them; tests that score articles set `native_sentiment` or patch `_get_article_sentiment`).
- **Regexes:** every module containing `\b` or `\W` is written with the Write tool (never a Bash heredoc); `tests/test_subject_rules.py::test_source_has_no_backspace_bytes` asserts `b"\x08" not in` the module bytes.
- **Behaviour logged:** `build_event_news_bundle` prints one line per event when anything is excluded, e.g. `[event_context] FOMC Statement: excluded 7 (foreign_cb=2, no_fed_coterm=1, off_subject=3, duplicate_url=1)`.
- **Times:** stored UTC ISO (`_utc_iso`); the report and docs show SAST (`%Y-%m-%d %H:%M SAST`).
- **Style:** type hints on every signature, `from __future__ import annotations`, surrounding comment density, dated `B6 (2026-10-22)` comments at each changed rule; row dicts and report dicts have exact key-set tests.
- **Line endings:** every touched file is CRLF today; keep CRLF, new files CRLF.
- **Commits:** one per task on `b6-article-wrong-sign`; message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Over-blocking real US coverage.** "Federal Reserve Bank of New York" read as a foreign "reserve bank of", "Bank of America" as a central bank, the pronoun "us" as the US, or "Australian dollar" as the dollar.
   - Pinned by `test_foreign_cb_ignores_us_lookalikes`, `test_us_marker_is_case_sensitive`, `test_foreign_dollar_is_not_the_dollar` (Task 1).
2. **Under-blocking the live offenders.** The real Schnabel, Pill, Breeden, Philippine and China titles must be excluded for both families with reason `foreign_cb`, not merely off-topic; the gold-led dollar title must be `off_subject` for FOMC.
   - Pinned by `test_probe1_foreign_cb_dropped[...]` (FOMC and CPI parametrized), `test_live_offender_titles_excluded`, `test_gold_led_dollar_title_not_scored_for_fomc` (Task 1).
3. **Exclusions leaking into the vote or the count.** Excluded articles must not reach `score_bundle`, `score_print_direction` or `article_count`; keyword misses (`off_topic`) are not recorded.
   - Pinned by `test_bundle_excluded_carries_reasons_not_articles`, `test_off_topic_not_in_excluded` (Task 1).
4. **Link weight lookup silently falling back.** A precursor title missing from the target's links must fall back to `PRECURSOR_TRUST_WEIGHT` only then; CPI y/y gets PPI at 0.80, not 0.90.
   - Pinned by `test_precursor_trust_uses_authored_link_weight`, `test_jolts_to_nfp_uses_0_40`, `test_unlinked_precursor_falls_back_to_global_weight` (Task 2).
5. **URL dedup keeping the wrong copy or merging blank URLs.** Earliest wins; dedup runs after the relevance partition; empty URLs never merge.
   - Pinned by `test_same_url_keeps_earliest`, `test_blank_urls_never_merge`, `test_url_dedup_runs_after_relevance` (Task 3).
6. **"Final pre-event" chosen wrongly or evidence duplicated.** A post-release prediction must not be returned; a re-record of the same prediction id inserts nothing; a non-material re-score writes no rows.
   - Pinned by `test_final_pre_event_ignores_post_release_prediction`, `test_record_contributions_idempotent`, `test_unchanged_rescore_writes_no_evidence` (Task 3).
7. **The report writing to the live DB.** Pinned by `test_open_readonly_refuses_writes` (Task 4).

---

### Task 1: Subject rules and relevance partition (A1, A2) — *judgment*

**Files:**
- Create: `data_layer/subject_rules.py`, `tests/test_subject_rules.py`
- Modify: `config/settings.py` (after `EVENT_RELEVANCE_KEYWORDS_BY_TITLE`), `data_layer/event_context.py`, `tests/test_event_context.py`

**Interfaces:**
```python
# config/settings.py
RELEVANCE_FAMILY_BY_TITLE: dict[str, str]   # built by identity from the shared keyword lists:
    # "fomc" (_FOMC_...), "cpi", "jobs", "ppi", "ism", "retail_sales", "gdp"; titles with their own list (PCE, UoM) absent
FOMC_FAMILY_TITLES: frozenset[str]          # derived: the 6 FOMC-list titles
CPI_FAMILY_TITLES: frozenset[str]           # derived: CPI m/m, CPI y/y, Core CPI m/m, Core CPI y/y
FED_OFFICIAL_SURNAMES: tuple[str, ...] = ("warsh", "powell", "waller", "bowman", "jefferson", "barr", "miran",
    "goolsbee", "kashkari", "musalem", "hammack", "bostic", "barkin", "daly", "schmid", "logan", "paulson", "kugler")
    # comment: roster as of 2026-10-22; Cook/Williams/Collins left out (Tim Cook etc.), "Fed's Cook" still matches via "fed"

# data_layer/subject_rules.py
SUBJECT_RULE_FAMILIES: tuple[str, ...] = ("fomc", "cpi")
def title_family(event_title: str) -> str                      # RELEVANCE_FAMILY_BY_TITLE.get(t, "other")
def foreign_cb_match(text: str) -> str | None                  # the matched name, lower-case; None = no foreign CB
def names_fed(text: str) -> bool
def names_us_marker(text: str) -> bool
def passes_subject_rule(title: str, family: str) -> bool       # True for families outside SUBJECT_RULE_FAMILIES
def b6_exclusion_reason(title: str, summary: str, event_title: str) -> str | None
    # order: "foreign_cb" -> "no_fed_coterm" (fomc only) -> "off_subject" (fomc, cpi); None = kept

# data_layer/event_context.py
EXCLUSION_REASONS: tuple[str, ...] = ("single_stock_blurb", "foreign_cb", "no_fed_coterm", "off_subject", "duplicate_url")
@dataclass class EventNewsBundle: ... excluded: list[tuple[NewsArticle, str]] = field(default_factory=list)
def _partition_relevant(articles: list[NewsArticle], event_title: str) -> tuple[list[NewsArticle], list[tuple[NewsArticle, str]]]
def _filter_relevant(articles: list[NewsArticle], event_title: str) -> list[NewsArticle]   # unchanged signature, wraps partition
```

Rule definitions (all case-insensitive unless stated; compiled once at module level):
- **Foreign CB names:** `ecb`, `european central bank`, `lagarde`, `schnabel`, `villeroy`, `nagel`, `boe`, `bank of england`, `andrew bailey`, `huw pill`, `breeden`, `boj`, `bank of japan`, `ueda`, `himino`, `rba`, `reserve bank of australia`, `bullock`, `snb`, `swiss national bank`, `schlegel`, `boc`, `bank of canada`, `macklem`, `rbnz`, `pboc`, `people's bank of china`, `pan gongsheng`, `riksbank`, `norges bank`, `rbi`, `bank of korea`, `banxico`, `bank of mexico`, `bundesbank`, `banque de france`, `bank of italy`, plus `(?<!federal )reserve bank of \w+`. Bare `Bailey`/`Pill` are NOT listed ("poison pill", "weight-loss pill"); the live titles carry "BoE" / "Bank of England" anyway.
- **Generic foreign CB:** `central bank(s|er|ers|'s)?` together with a foreign place token anywhere in the same text (`_FOREIGN_PLACE`: china/chinese, japan/japanese, euro zone/eurozone/euro area, europe/european, eu, uk/u.k./britain/british/england, germany/german, france/french, italy/italian, spain/spanish, swiss/switzerland, canada/canadian, australia/australian, new zealand, india/indian, brazil/brazilian, mexico/mexican, turkey/turkish, russia/russian, korea/korean, philippine(s)/filipino, indonesia(n), south africa(n), sweden/swedish, norway/norwegian, poland/polish, thailand/thai, singapore, hong kong, taiwan, israel, saudi, nigeria). Covers "Philippine central bank" and "central bank of <country>".
- **Where foreign CB is checked:** the article title always; the summary only when the title has neither `names_us_marker` nor `names_fed`. Applies to every event title.
- **Fed co-term (`names_fed`):** `\b(fed|fomc|federal reserve|federal funds|fed funds|dot plot)\b` or a `FED_OFFICIAL_SURNAMES` word; checked over title + summary for the FOMC family. Requiring it for every FOMC-family article equals requiring it for the generic matches only, because every other FOMC keyword is itself a co-term (except "economic projections", treated as generic).
- **US marker (`names_us_marker`):** case-sensitive `(?<![A-Za-z])U\.?S\.?(?![A-Za-z])` or `\bUSA\b`; case-insensitive `america(n|ns)?`, `united states`.
- **Subject rule, FOMC family (title only):** `names_fed(title)`, or US rates (`treasury|treasuries|t-bills?|t-notes?`, or a US marker followed within 0-2 words by `rates?|yields?|interest rates?|borrowing costs`), or the dollar: `dollar|usd|greenback|dxy` after removing foreign-dollar phrases (`(australian|aussie|canadian|new zealand|kiwi|hong kong|singapore|taiwan) dollars?`) AND the title does not lead with another asset (`^\W*(gold|silver|platinum|oil|crude|brent|wti|copper|bitcoin|crypto\w*|stocks?|equities|shares|wall st(reet)?|s&p( 500)?|nasdaq|dow|yen|euro|sterling|pound|yuan|asian|european|global)\b`).
- **Subject rule, CPI family:** everything the FOMC rule accepts, or US inflation (US marker / american / united states, optional `'s`, then within 0-2 words `inflation|cpi|consumer prices?|consumer price index`), or `bls|bureau of labor statistics`, or bare `cpi|consumer price index` when the title has no `_FOREIGN_PLACE` token. Bare "inflation" alone does not qualify.

- [ ] **Step 1: failing tests** in `tests/test_subject_rules.py` (pure function tests, `pytest.mark.parametrize` allowed):
  - `test_family_sets_are_exact`: `FOMC_FAMILY_TITLES == {"FOMC Meeting Minutes", "FOMC Statement", "Federal Funds Rate", "FOMC Press Conference", "FOMC Economic Projections", "Fed Chairman Warsh Speaks"}`; `CPI_FAMILY_TITLES == {"CPI m/m", "CPI y/y", "Core CPI m/m", "Core CPI y/y"}`; `title_family("Core PCE Price Index m/m") == "other"`, `title_family("PPI m/m") == "ppi"`.
  - `test_probe1_foreign_cb_dropped[fomc|cpi x 4]`: the 4 Probe 1 headlines (copied literally from `scripts/audit_fa_probes.py`) for "FOMC Statement", and CPI-relevant variants for "CPI m/m" ("ECB's Schnabel says inflation risks mean rates must rise", "Bank of England's Pill warns inflation is sticky", "Bank of Japan's Ueda sees inflation near target", "RBA warns inflation still too high") -> `b6_exclusion_reason(...) == "foreign_cb"`.
  - `test_fed_headlines_kept[fomc|cpi]`: ("Fed signals faster rate cuts as US growth slows", "Federal Reserve officials see easing ahead") and ("Warsh says inflation fight is not over", "") kept for "FOMC Statement"; ("US CPI rises 0.4% in September, hotter than forecast", "") and ("Fed's Waller says inflation still too high", "") kept for "CPI m/m" (reason None).
  - `test_live_offender_titles_excluded`: for both "FOMC Statement" and "CPI m/m" -> "foreign_cb": "Interest rates must rise further on inflation risks, ECB's Schnabel tells Bloomberg - Reuters", "BoE's Pill says a rate hike need not be start of long series - Reuters", "Bank of England's Breeden says cost-cutting by firms helping central bank - Reuters", "'Godzilla El Niño' is wreaking havoc with Philippine central bank's inflation forecasts", "China's slower loan growth is the new normal, central bank governor says - reuters.com", "Dollar languishes as inflation awaited; Euro edges up on Lagarde warning".
  - `test_foreign_cb_ignores_us_lookalikes`: `foreign_cb_match` is None for "Bank of America CEO sees at least 10% drop in Q3 investment banking fees", "Federal Reserve Bank of New York survey shows inflation expectations rise", "New York Fed's Williams says policy is well positioned", "Novo's weight-loss pill sales jump"; not None for "Reserve Bank of India holds rates".
  - `test_generic_fomc_term_needs_fed_coterm`: ("Gold retains key reserve status despite surging bond yields, central bankers say", "") for "FOMC Statement" -> "no_fed_coterm"; ("Rate cut bets rise", "Traders price a Federal Reserve cut in December") passes the co-term step (reason is "off_subject", from the title rule).
  - `test_gold_led_dollar_title_not_scored_for_fomc`: ("Gold edges up as October rate hike bets ease, stronger dollar cap gains", "Traders trimmed bets on a Federal Reserve hike") for "FOMC Meeting Minutes" -> "off_subject"; with summary "" -> "no_fed_coterm".
  - `test_subject_rule_accepts_us_subjects`: FOMC accepts "Dollar firms as Fed officials push back on cuts", "Treasury yields climb after hot jobs data", "US 10-year yields hit two-month high", "Greenback slips ahead of Warsh testimony"; CPI also accepts "U.S. consumer prices rise 0.4% in September", "American inflation expectations climb", "Inflation data due Wednesday, CPI expected to ease", "BLS delays September report".
  - `test_subject_rule_rejects_off_subject`: FOMC rejects "Americans' incomes rose and poverty fell, Census Bureau says" and "AI chip stocks slump"; CPI rejects "Inflation worries weigh on us all", "Japan CPI rises 2.9%", "Euro zone inflation eases to 2.1%".
  - `test_us_marker_is_case_sensitive`: `names_us_marker("tells us nothing") is False`; True for "US", "U.S.", "USA", "American"; `names_us_marker("USD rallies") is False`.
  - `test_foreign_dollar_is_not_the_dollar`: CPI rejects "Canadian dollar firms after inflation data"; FOMC rejects "Australian dollar jumps as rate hike bets build".
  - `test_other_titles_only_get_foreign_cb`: `b6_exclusion_reason("US payrolls jump 250,000; rate cut bets fade", "", "Non-Farm Employment Change") is None`; `b6_exclusion_reason("BoE's Bailey says UK hiring slows", "", "Non-Farm Employment Change") == "foreign_cb"`.
  - `test_summary_foreign_cb_only_without_us_title`: ("Markets steady", "The ECB held rates") for "Retail Sales m/m" -> "foreign_cb"; ("US retail sales jump 0.6%", "Elsewhere the ECB held rates") -> None.
  - `test_source_has_no_backspace_bytes`: `b"\x08" not in Path("data_layer/subject_rules.py").read_bytes()`.
  - `test_audit_probe1_now_drops_all`: `from scripts.audit_fa_probes import probe_foreign_cb_sign`; every returned line starts with "DROP".
- [ ] **Step 1b: failing tests** in `tests/test_event_context.py`:
  - `test_bundle_excluded_carries_reasons_not_articles`: FOMC Statement bundle from ("Fed signals hawkish tilt in FOMC minutes", ""), ("ECB signals faster rate cuts as euro zone stalls", "Lagarde said the central bank is ready to ease further."), ("Gold edges up as October rate hike bets ease, stronger dollar cap gains", "Traders trimmed bets on a Federal Reserve hike") -> `bundle.articles` titles == [the Fed title]; `sorted(r for _, r in bundle.excluded) == ["foreign_cb", "off_subject"]`.
  - `test_off_topic_not_in_excluded`: Unemployment Claims bundle: "Apple to change app data consent rules, German regulator says" is in neither `articles` nor `excluded`; ("First Solar stock heads into the open after a 4.42 percent drop", "US jobless claims and housing data are due today.") is in `excluded` as "single_stock_blurb".
  - `test_exclusion_reason_vocabulary`: `EXCLUSION_REASONS` equals the tuple above.
  - Re-point `test_relevance_keyword_match_is_case_insensitive_and_checks_summary_too` to "Retail Sales m/m" with title "Markets steady ahead of release", summary "Traders await the RETAIL SALES report" (the old FOMC version is now correctly `off_subject`; comment says so). Add it and the new tests to the `__main__` runner.
- [ ] **Step 2:** `python -m pytest tests/test_subject_rules.py tests/test_event_context.py -q -p no:warnings` -> FAIL.
- [ ] **Step 3: implement.** settings additions with a dated B6 comment block (and a one-line pointer above `_FOMC_RELEVANCE_KEYWORDS`: keyword list unchanged, the co-term and subject rules live in `data_layer/subject_rules.py`). `subject_rules.py` module docstring cites AUD-P0-1/AS-04, the live examples and owner decision 8, and states the limits (title-only subject rule; FinBERT still reads tone, not subject: the structural fix is the parked CB stance model). `_partition_relevant`: per article, keyword miss -> skipped (not recorded); else blurb -> "single_stock_blurb"; else `b6_exclusion_reason(title, summary, event_title)`; keep the fail-closed no-keywords branch and its warning. `build_event_news_bundle` uses the partition, stores `excluded`, prints the one-line summary when non-empty.
- [ ] **Step 4:** run both files -> PASS; `python scripts/audit_fa_probes.py` shows Probe 1 all DROP.
- [ ] **Step 5:** full suites green apart from the known env-only failure. Any other test that breaks because its FOMC/CPI headline lacks a US subject is re-pointed or its headline given a real US subject, with a comment; list them in the commit body.
- [ ] **Step 6:** commit `feat(B6): foreign-CB exclusion, Fed co-term and title subject rule for FOMC/CPI articles`.

---

### Task 2: Link weights, country guard, stale comments (A3, A4, DOC-01) — *integration*

**Files:**
- Modify: `scoring/probability_engine.py`, `data_layer/calendar_feed.py`, `webapp/scoring_service.py` (comment only), `config/settings.py` (comments only), `scripts/audit_fa_probes.py`, `tests/test_probability_engine.py`, `tests/test_calendar_feed.py`, `tests/test_webapp_scoring_service.py`

**Interfaces:**
```python
# scoring/probability_engine.py
def _precursor_link_weight(target_title: str | None, precursor_title: str) -> float
    # EVENT_INFLUENCE_LINKS[target_title] weight for precursor_title; PRECURSOR_TRUST_WEIGHT when target is None,
    # has no links, or does not list this precursor
def _build_precursor_contributions(precursor_events: list[EconomicEvent], as_of: dt.datetime,
                                   target_title: str | None = None) -> list[PrecursorContribution]
# score_bundle passes target_title=bundle.event.title; signature of score_bundle unchanged

# data_layer/calendar_feed.py
EconomicEvent.usd_surprise_score(self) -> Optional[float]   # None first when self.country != "USD"
```

- [ ] **Step 1: failing tests.**
  - `tests/test_probability_engine.py`: replace `test_event_influence_links_weight_is_stored_but_not_consumed_by_scoring` with `test_precursor_trust_uses_authored_link_weight`: Challenger Job Cuts y/y (f 20K, a 35K) with `target_title="Non-Farm Employment Change"` -> `trust_weight == 0.35`, `combined_weight == 0.35 * time_weight`.
  - `test_jolts_to_nfp_uses_0_40`: `_precursor_link_weight("Non-Farm Employment Change", "JOLTS Job Openings") == 0.40`; with `patch.dict(EVENT_SURPRISE_DIRECTION, {"JOLTS Job Openings": "higher_bullish"})` a JOLTS event (f 7.2M, a 7.6M) builds one contribution with `trust_weight == 0.40`.
  - `test_adp_and_ppi_links_stay_0_90`: ADP->"Non-Farm Employment Change" and PPI m/m->"CPI m/m" -> 0.90; PPI m/m->"CPI y/y" -> 0.80.
  - `test_unlinked_precursor_falls_back_to_global_weight`: target None, target with no links ("Retail Sales m/m" + "PPI m/m"), and an unlisted precursor all -> `PRECURSOR_TRUST_WEIGHT`.
  - `test_score_bundle_passes_target_title_to_precursors`: CPI y/y bundle with a PPI m/m precursor -> `result.precursor_contributions[0].trust_weight == 0.80`.
  - Existing `test_get_precursor_events_for_*` regression and the chain-conflict tests stay unchanged and green (ADP/PPI at 0.90 keep them identical).
  - `tests/test_calendar_feed.py::test_non_usd_row_has_no_surprise`: `EconomicEvent("CPI m/m", "JPY", "High", t, forecast="0.2%", actual="0.4%").usd_surprise_score() is None`; the same row with "USD" > 0.
  - `tests/test_webapp_scoring_service.py::test_non_usd_event_gets_no_fabricated_score`: JPY CPI m/m with an actual through `score_event_for_symbol(..., classify_symbol("XAUUSD"))` -> `probability is None` and `raw_score is None`.
  - `tests/test_calendar_feed.py::test_audit_probe3_handles_no_surprise`: `scripts.audit_fa_probes.probe_surprise_scale()` runs and its JPY line ends with `usd_surprise_score=None`.
- [ ] **Step 2:** run the three test files -> FAIL.
- [ ] **Step 3: implement.** `_precursor_link_weight` + the new parameter; `score_bundle` passes `bundle.event.title`. Country guard as the first line of `usd_surprise_score()` with a docstring line ("a foreign print under a US title is not a USD surprise; B6 A4"). `scoring_service` NOTE gains case (3) non-USD row (unreachable today: `scoring_events` is USD-only). Probe 3 formats None as `None`. Comments: replace the `EVENT_INFLUENCE_LINKS` paragraph "float weight is EXPLICITLY NOT consumed" with "since B6 (2026-10-22) the weight IS the precursor's trust weight (probability_engine._precursor_link_weight); PRECURSOR_TRUST_WEIGHT is only the fallback for unlinked pairs"; update the `PRECURSOR_TRUST_WEIGHT` comment to match; fix `REDUNDANCY_TERM_OVERLAP_THRESHOLD`'s comment to "Jaccard overlap of significant title+summary words" (DOC-01; the `_is_likely_redundant` docstring is already correct).
- [ ] **Step 4:** run -> PASS.
- [ ] **Step 5:** full suites green.
- [ ] **Step 6:** commit `feat(B6): authored influence-link weights as precursor trust; non-USD rows give no surprise`.

---

### Task 3: Same-URL dedup and full evidence table (A5, A6) — *integration*

**Files:**
- Modify: `data_layer/news_feed.py`, `data_layer/event_context.py`, `scoring/probability_engine.py`, `scoring/backtest_store.py`, `scoring/backtest_accumulator.py`
- Test: `tests/test_scoring_smoke.py` (or `tests/test_event_context.py`), `tests/test_backtest_store.py`, `tests/test_backtest_accumulator.py`

**Interfaces:**
```python
# data_layer/news_feed.py
def normalize_url(url: str) -> str     # strip; lower-case scheme+host; drop fragment, trailing "/", utm_* params; "" stays ""
def dedupe_same_url(articles: list[NewsArticle]) -> tuple[list[NewsArticle], list[NewsArticle]]
    # (kept, dropped); per normalized non-empty URL keep the earliest published_utc (tie: higher trust); input order kept

# scoring/probability_engine.py
@dataclass class ArticleContribution: ... redundancy_discounted: bool = False   # set True in _apply_redundancy_discounts

# scoring/backtest_store.py
CREATE TABLE IF NOT EXISTS prediction_article_contributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER NOT NULL,            -- predictions.id this evidence produced
    event_title TEXT NOT NULL, event_time_utc TEXT NOT NULL, instrument TEXT NOT NULL,
    title TEXT NOT NULL, url TEXT NOT NULL,    -- '' when the feed gave none
    source TEXT NOT NULL,                      -- publisher (NewsArticle.source)
    source_type TEXT NOT NULL,                 -- SOURCE_TRUST_WEIGHTS key (AS-02 caveat)
    published_utc TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('included', 'excluded')),
    reason TEXT,                               -- excluded: EXCLUSION_REASONS; included: NULL or 'redundancy_discount'
    usd_sentiment REAL, trust_weight REAL, time_weight REAL, combined_weight REAL, weight_pct REAL,  -- NULL when excluded
    matched_terms_json TEXT,                   -- sentiment tier tag(s), e.g. ["<finbert:positive:0.91>"]
    recorded_at_utc TEXT NOT NULL,
    UNIQUE(prediction_id, status, title, url)
);
CREATE INDEX IF NOT EXISTS idx_pac_occurrence ON prediction_article_contributions (event_title, event_time_utc, instrument);
@dataclass class PredictionArticleContribution: (one field per column; matched_terms parsed to list[str])
def record_prediction_article_contributions(conn: sqlite3.Connection, prediction_id: int, event_title: str,
        event_time_utc: dt.datetime, instrument: str, rows: list[dict]) -> int      # rows inserted; INSERT OR IGNORE
def get_prediction_article_contributions(conn: sqlite3.Connection, prediction_id: int) -> list[PredictionArticleContribution]
    # ORDER BY status, combined_weight DESC NULLS LAST, id
def get_final_pre_event_article_contributions(conn: sqlite3.Connection, event_title: str, instrument: str,
        event_time_utc: dt.datetime) -> list[PredictionArticleContribution]
    # latest predictions row for the occurrence with scored_at_utc <= event_time_utc (same isoformat the predictions
    # table uses), then its rows; [] when none

# scoring/backtest_accumulator.py
def _build_article_contribution_rows(contributions: list, excluded: list[tuple]) -> list[dict]
    # keys exactly: title, url, source, source_type, published_utc, status, reason, usd_sentiment, trust_weight,
    #   time_weight, combined_weight, weight_pct, matched_terms
```

- [ ] **Step 1: failing tests.**
  - `test_same_url_keeps_earliest`: same URL at T-3h "CNBC: Fed officials split" and T-1h "CNBC: Fed officials split, dollar slips" -> kept is the T-3h copy, dropped the T-1h one.
  - `test_normalize_url_variants`: "https://WWW.CNBC.com/a/b/#live" == "https://www.cnbc.com/a/b" == "https://www.cnbc.com/a/b?utm_source=rss"; differing paths stay different.
  - `test_blank_urls_never_merge`: two articles with url "" -> both kept.
  - `test_url_dedup_runs_after_relevance` (event_context): FOMC Statement, same URL: earlier copy "Live: Apple event recap" (off-topic, no keyword), later ("Live: Fed holds rates, FOMC statement", "Federal Reserve policy") -> the Fed copy is kept; same URL with two relevant copies ("Fed officials split at FOMC meeting" at T-3h, "Fed officials split at FOMC meeting, dollar slips" at T-1h, both summary "Federal Reserve policy") -> the T-3h copy kept, the T-1h copy in `bundle.excluded` as "duplicate_url".
  - `tests/test_backtest_store.py::test_contributions_table_created_additively`: `get_connection` on a temp DB built with the old `_SCHEMA` minus the new table -> table and index exist; existing rows untouched.
  - `test_record_contributions_idempotent`: record 3 rows (2 included, 1 excluded) for prediction 1 -> returns 3; same call again -> returns 0 and the table has 3 rows; a row with an invalid status raises `sqlite3.IntegrityError`.
  - `test_final_pre_event_ignores_post_release_prediction`: predictions at T-2h (rows a), T-10min (rows b), T+5min (rows c) -> returns b's rows only; an occurrence with no prediction -> [].
  - `test_contribution_row_dataclass_fields`: returned objects expose `matched_terms` as a list and NULL weights as None for excluded rows.
  - `tests/test_backtest_accumulator.py::test_article_contribution_row_keys_exact`: `set(row) ==` the 13 keys above for both an included and an excluded row; included `weight_pct` values sum to 100 (+-0.2); a redundancy-discounted contribution has `reason == "redundancy_discount"`.
  - `test_every_article_recorded_with_prediction`: bundle of 5 articles (`native_sentiment` set) + 1 excluded ("foreign_cb"), instruments XAUUSD and US30 -> after `score_and_record_event`, each new prediction id has 5 included + 1 excluded rows (not 3).
  - `test_unchanged_rescore_writes_no_evidence`: a second `score_and_record_event` with an identical bundle records no prediction and adds no contribution rows.
  - `test_evidence_write_failure_keeps_prediction`: `record_prediction_article_contributions` patched to raise -> the prediction row exists, a WARNING is printed, no exception escapes.
- [ ] **Step 2:** run the touched test files -> FAIL.
- [ ] **Step 3: implement.** `dedupe_same_url` in `news_feed.py` (docstring: AS-01, feeds re-stamp; a live-blog URL keeps its first relevant headline; title dedup unchanged). `build_event_news_bundle`: window -> `_partition_relevant` -> `dedupe_same_url` (dropped appended to `excluded` as "duplicate_url") -> `deduplicate_articles`; the Task 1 summary print moves after the URL step so it counts `duplicate_url`. Schema + functions in `backtest_store.py` (append-only docstring citing owner ruling 9 and AS-02; `_utc_iso` for writes). Accumulator: after `record_prediction` returns the id, build rows from `result.contributions` and `bundle.excluded` and record them in a try/except that prints `[backtest_accumulator] WARNING: evidence write failed ...`. Comment on `TOP_CONTRIBUTIONS_LIMIT` that the full list now lives in the new table; `top_contributions_json` unchanged (the History/Stats UI reads it).
- [ ] **Step 4:** run -> PASS.
- [ ] **Step 5:** full suites green.
- [ ] **Step 6:** commit `feat(B6): same-URL article dedup and append-only per-prediction article evidence table`.

---

### Task 4: Read-only contamination report (A7) — *integration*

**Files:**
- Create: `scripts/b6_contamination_report.py`, `tests/test_b6_contamination_report.py`, `docs/superpowers/specs/2026-10-22-b6-contamination-report.md`

**Interfaces:**
```python
def open_readonly(db_path: Path) -> sqlite3.Connection         # file:...?mode=ro URI; FileNotFoundError if missing
def summarize(conn: sqlite3.Connection) -> dict                 # {"families": {family: FamilyStats}, "examples": {...}, "totals": {...}}
    # FamilyStats keys exactly: rows, rows_with_contributions, contributions, unique_contributions, removed_by_reason,
    #   removed_unique, removed_nonzero, rows_touched, rows_all_removed, occurrences_touched, same_url_pairs
    # examples: {family: {reason: [up to 5 titles]}}; totals: same keys as FamilyStats summed
def count_foreign_cb_included(conn: sqlite3.Connection, since_utc: str) -> int
    # included rows in prediction_article_contributions recorded since `since_utc` whose title foreign_cb_match()es
def render_markdown(summary: dict, db_label: str, generated_sast: str) -> str
def main(argv: list[str] | None = None) -> int   # --db PATH (default scoring/backtest_log.db), --verify-since ISO
```
Method: every `predictions` row with `top_contributions_json` (source 'live'); each stored contribution is re-run through `b6_exclusion_reason(title, "", event_title)` (summary is not stored, so `no_fed_coterm` is an upper bound) plus a same-URL check within the row; family from `title_family`. `contributions` and `removed_by_reason` count every stored entry; `unique_contributions` and `removed_unique` count distinct (event_title, event_time_utc, url or title). "Nonzero" = `abs(usd_sentiment) >= 0.05`. `rows_all_removed` = rows where every stored contribution would go.

- [ ] **Step 1: failing tests** on a temp DB with fixture rows (one FOMC row holding the Schnabel title +0.75, a Fed title and the gold-led dollar title; one CPI row with the Schnabel title twice at the same URL; one NFP row with a clean title):
  - `test_summary_keys_exact`: FamilyStats key set as above for every family present.
  - `test_counts_by_reason`: fomc `removed_by_reason == {"foreign_cb": 1, "no_fed_coterm": 1}` (the gold-led title with no stored summary has no Fed co-term, so the co-term step fires before the subject step), fomc `removed_nonzero == 2` (fixture sentiments: Schnabel +0.75, gold-led +0.94, Fed title -0.40), cpi `same_url_pairs == 1` and `removed_by_reason == {"foreign_cb": 2}`, `unique_contributions` for cpi == 1, jobs `removed_unique == 0`.
  - `test_open_readonly_refuses_writes`: an INSERT through `open_readonly` raises `sqlite3.OperationalError`; a missing path raises `FileNotFoundError`.
  - `test_count_foreign_cb_included`: 1 included foreign-CB row after `since`, 1 before, 1 excluded -> 1.
  - `test_render_markdown_has_family_table_and_caveats`: output contains "| Family |", "top-3 only", "title only", "SAST".
  - `test_main_prints_markdown`: `main(["--db", tmp])` returns 0.
- [ ] **Step 2:** run -> FAIL.
- [ ] **Step 3: implement** the script (module docstring: read-only, no network, live DB via `mode=ro`, the two caveats; `__main__` block with a working example invocation).
- [ ] **Step 4:** run -> PASS.
- [ ] **Step 5: run against live data (read-only):** `python scripts/b6_contamination_report.py --db C:\Users\Masoodt\Documents\Claude\Projects\.worktrees\news-engine-live\Claude_news_engine\news_engine\scoring\backtest_log.db`. Write `docs/superpowers/specs/2026-10-22-b6-contamination-report.md`: plain-English summary first (how many FOMC-family and CPI-family calls carried foreign-CB or off-subject evidence, and how many calls lose all top evidence: those become thin-sample calls), the family table, examples per reason, caveats (top 3 only so an undercount; title only so `no_fed_coterm` an upper bound; precursor/Kalshi not stored), cross-check against the audit's figures (45 rows / 17 occurrences with foreign-CB titles; 92 of 137 FOMC-family uniques with no Fed term) and explain any gap, and the post-deploy acceptance query (`--verify-since <deploy UTC>` must print 0 after a week).
- [ ] **Step 6:** full suites green; commit `feat(B6): read-only before/after contamination report with live numbers`.

---

### Task 5: Docs, change-date log and deploy note — *mechanical*

**Files:**
- Modify: `docs/feature-inventory-2026-09-11.md`, `docs/roadmap-2026-10-20.md`
- Create: `docs/b6-deploy.md`

- [ ] **Step 1:** feature inventory: roadmap table row B6 -> `built on branch b6-article-wrong-sign (2026-10-22; scoring change: article relevance rules, link weights, non-USD surprise guard; change date logged)`; add a §2a row "Article read: foreign-CB exclusion, Fed co-term, FOMC/CPI title subject rule, same-URL dedup, authored link weights, non-USD surprise guard, full per-prediction article evidence (B6)" with status **Built (branch, not merged)**, where = the touched files, and the report's headline numbers plus "Scoring change effective from the deploy time; the 2027-01-15 review uses post-change data only (roadmap risk 4)".
- [ ] **Step 2:** roadmap status line: append `B6 built 2026-10-22 on branch b6-article-wrong-sign (not merged; scoring change, report docs/superpowers/specs/2026-10-22-b6-contamination-report.md).`
- [ ] **Step 3:** `docs/b6-deploy.md` (applied at deploy by the controller), modelled on `docs/b4-deploy.md`: (1) what changes at merge (scoring rules, new table created on the first accumulator cycle, no Windows/Claude task change); (2) backup `scoring\backtest_log.db` to `backtest_log.db.pre_b6_<date>` with the sqlite backup-API one-liner; (3) stop the single engine copy (B4 step 3 commands); (4) merge; (5) start exactly one copy (`schtasks /run /tn NewsEngine_AutoStart`) so the accumulator loads the new code, and record the restart time in UTC and SAST in the inventory row (the change date); (6) verify: the accumulator log shows `[event_context] ... excluded` lines; `SELECT status, reason, COUNT(*) FROM prediction_article_contributions GROUP BY 1, 2` grows after the next recorded prediction; `python scripts\b6_contamination_report.py --verify-since <restart UTC ISO>` prints 0 (repeat after a week: roadmap acceptance); (7) rollback: stop, revert the merge, restart one copy; the new table can stay (nothing reads it).
- [ ] **Step 4:** full suites green (docs only); commit `docs(B6): inventory, roadmap status and deploy note`.
