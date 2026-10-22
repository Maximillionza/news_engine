# B7 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Follow-up coverage of one event, under a new headline or a re-stamped URL, neither re-alerts nor adds lean: in shock alerts (a follow-up is stored and labelled on its incident, pushed only when severity rises or direction flips) and in article sentiment (re-coverage of one incident votes once). A re-stamped URL keeps its original age. This batch changes article scoring; the change date is logged.

**Architecture:** `alerting/store.py` gains three nullable incident columns and a `seen_urls` table (URL memory, 72 h), migrated additively at connect. A new pure `data_layer/entities.py` extracts named places/actors from a small gazetteer; a new `alerting/incident.py` holds the linking rules (URL rule, entity rule, storm veto, direction check, update reason) and is called by `alerting/poll_once.py` after the existing similarity dedup. `scoring/probability_engine.py` reuses the entity extraction to exclude same-incident article re-coverage before aggregation, and `scoring/backtest_accumulator.py` records those exclusions in B6's evidence table with reason `same_incident`.

**Tech Stack:** Python 3.14, sqlite3, `re`, `difflib`, pytest; vanilla ES modules + `node --test` for the tab.

**Spec:** `docs/roadmap-2026-10-20.md` §B7 (K9, K10, A9), plus these owner decisions:
- Follow-ups are LINKED AND LABELLED, never suppressed in a way that could bury a genuine escalation: a follow-up of an existing incident is stored on that incident (visible on the tab) with NO Telegram push and NO new lean, UNLESS severity rises or polarity flips; then push once as "Update to incident #N: <headline>" with the B2 freshness line.
- URL memory window 72 h. Old alerts have NULL `incident_id` and are their own incident.
- Acceptance: #54/#55, #71/#72, #33/#39, #12/#13 link as one incident; #41/#43 and #46/#52 do not; a same-severity same-polarity follow-up sends no push; a severity rise sends exactly one "Update to incident #N"; a re-stamped URL keeps its original age; article re-coverage of one incident counts once in the accumulator.
- Out of scope: direction grading (B10), Stats (B9), standardized surprise (B8).

Audit evidence: SA-04, AS-01 (`explore_C.json`).

App dir for every command: `.worktrees/b7-same-incident/Claude_news_engine/news_engine`. Full suite = `python -m pytest -q -p no:warnings` + `npm test`. Known env-only failure (no `.env` in a worktree): `tests/test_news_sources.py::test_combined_builder_includes_alpha_vantage_when_key_present`; ignore it, everything else must pass. Baseline at cbefa15: 1810 passed + 1 env-only failure; `npm test` 222 pass.

## Choices made in this plan (owner can veto before Task 1)

- **Entity window 24 h** (owner range 24-48 h): the tighter end, because a looser energy/geopolitical rule once buried a tanker strike under Hormuz talks. The URL rule covers re-stamps up to 72 h (#33/#39 at 62 h, #71/#72 at 26 h).
- **The URL rule also needs a shared entity or a similar headline** (difflib >= 0.6, the existing dedup threshold), on top of same family, no storm conflict and no opposite direction. Defence in depth for live-blog URLs: #41/#43 share no entity, so they stay apart even if the classifier says "unclear" for both. Failure mode is under-linking, i.e. today's behaviour, and the age still comes from URL memory.
- **Direction check falls back to the headline's price move** when either polarity is unknown/"unclear" (pre-B2 rows are NULL): "Oil rises ..." vs "Oil prices fall ..." counts as opposite.
- **Generic actors are not incident entities:** the US, Trump, the White House and the Fed are left out of the gazetteer (they appear in most alerts of their family, so they identify no incident). Capitals used as metonyms map to their country (Moscow/Kremlin -> russia, Riyadh -> saudi arabia, Tehran -> iran, Beijing -> china, Kyiv/Kiev -> ukraine). Ambiguous names (Chad, Georgia, Jordan, Niger) are left out. No capitalised-token fallback and no new classifier JSON fields: deterministic, testable, works on hard-rule hits and on the 42/75 failed-classification alerts.
- **Storm veto everywhere:** two `natural_disaster_supply_chain` headlines naming different storms never link, by URL, entity or the existing similarity dedup (the 2026-10-09 Simon article was merged into Isaias by similarity; that is how #46 got Simon's URL).
- **Severity rise is measured against the incident's highest stored severity**, also in the existing dedup escalation path, so a Medium follow-up row cannot be "escalated" back to the High the incident already pushed.
- **Polarity flip** compares with the incident's most recent known polarity (headline move as fallback). Under the URL rule an opposite direction never links (it is a different story on a reused URL and alerts normally); under the entity rule it links and pushes an update.
- **A failed classification never triggers an update push** (its severity is a fallback guess, same rule as today's `_maybe_escalate`); it is stored as a follow-up.
- **Silent follow-up rows keep their affected symbols with lean "mixed"** and why "follow-up of incident #N: no new lean"; an update row carries its own leans.
- **Re-stamped age:** a URL seen on an alert in the last 72 h gives the candidate that sighting's first publication time, unless the story is positively different (other family, storm conflict, opposite direction): then the article's own time is used (#43 keeps its own age, #39 gets 3 Oct).
- **`seen_urls` is backfilled once** from the sources of alerts detected in the last 72 h when the table is first created, so URL memory works from the first poll after deploy.
- **A9 excludes, not discounts:** a later article with the SAME non-empty entity set, no opposite USD sentiment and significant-word overlap >= 0.25 is excluded (count once), recorded as `excluded` / `same_incident` with its `usd_sentiment` kept for audit. Within one event bundle the event itself plays the role of category family. Same URL is already handled by B6's `duplicate_url`. Macro articles naming no gazetteer entity are never touched.

**Known limits (left as they are):** B6's article same-URL dedup still keeps only the earliest copy of a live-blog URL whatever its direction (sentiment is not known at bundle time); the similarity-dedup path (ratio >= 0.6 within 24 h) still appends an opposite-direction headline silently, as today; the weekly reality check still runs on follow-up rows (B10 grades incidents).

**Open owner question (not built):** SA-04 also recommended pushing a follow-up that is a hard-rule hit (e.g. "Iran threatens Hormuz" High, then "Strait of Hormuz closed" High, same polarity: under the owner rule this is a silent follow-up). If approved, it is one extra branch in `incident.update_reason` ("hard rule: <pattern>") when no row of the incident is `rule_tier`; not built until the owner says so.

## Global Constraints

- **Live system off-limits:** nothing under `.worktrees/news-engine-live` is modified; its `alerting/shock_alerts.db` is read only by the Task 2 fixture snippet (`mode=ro`). No Windows or Claude scheduled task, no Telegram (mocked), no push.
- **Nothing outside the repo needs deploying:** the migration runs at connect (poller every 2 min, webapp); the deploy is backups plus one engine restart (`docs/b7-deploy.md`, applied at deploy by the controller).
- **Migration:** additive and idempotent; `ALTER TABLE ... ADD COLUMN` through `_SHOCK_ALERT_ADDED_COLUMNS` (duplicate-column race swallowed); no index on a migrated column in `_SCHEMA`; `seen_urls` and its index are created by `_SCHEMA`.
- **Tests:** in-memory/temp DBs and mocks only (conftest blanks Telegram/Ollama/Anthropic); article sentiment is pinned with `native_sentiment`.
- **Regexes:** `data_layer/entities.py` and `alerting/incident.py` are written with the Write tool, never a Bash heredoc; each test file asserts `b"\x08" not in` the module bytes.
- **Behaviour logged:** one `[poll_once]` line per linked follow-up/update; the accumulator's `recorded` line carries `same_incident excluded: <n>` when n > 0.
- **Times:** stored UTC ISO; Telegram/tab/docs show SAST.
- **Style:** type hints on every signature, `from __future__ import annotations`, surrounding comment density, dated `B7 (2026-10-22)` comments at each changed rule; route rows and evidence rows keep exact key-set tests.
- **Line endings:** every touched file is CRLF today; keep CRLF, new files CRLF.
- **Commits:** one per task on `b7-same-incident`; message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Over-linking distinct events** (burying a new event as a silent follow-up): live-blog URL with opposite stories, two different storms, a Trump-only overlap, an entity match after the 24 h window, and a central-bank story linked into an energy incident.
   - Pinned by `test_live_pairs_that_must_not_link[41-43-*]`, `test_storm_pair_does_not_link`, `test_trump_only_overlap_does_not_link`, `test_entity_rule_window_is_24h`, `test_family_is_respected` (Task 2); `test_similar_headline_different_storm_does_not_merge` (Task 2).
2. **Under-linking the real pairs:** the four live pairs must link with fixtures copied verbatim from the live DB.
   - Pinned by `test_live_pairs_link[...]` (Task 2) and the end-to-end `test_riyadh_follow_up_is_stored_not_pushed` (Task 3).
3. **Burying a genuine escalation:** severity rise and direction flip must push exactly once; comparison is against the incident maximum, not the matched row.
   - Pinned by `test_severity_rise_pushes_exactly_one_update`, `test_direction_flip_pushes_an_update`, `test_dedup_escalation_is_measured_against_the_incident_max` (Task 3); `test_update_reason_cases` (Task 2).
4. **Wrong age either way:** a re-stamp must look old (#39: +3715 min, Very stale); a new story on a reused live-blog URL must keep its own age (#43).
   - Pinned by `test_restamped_url_keeps_first_publication`, `test_new_story_on_reused_url_keeps_own_age` (Task 2); `test_follow_up_row_stores_original_first_published` (Task 3).
5. **Live migration:** old DB with concurrent openers, NULL `incident_id` readers, the one-time backfill not duplicating, prune bounded.
   - Pinned by `test_b7_migration_is_idempotent_on_an_old_db`, `test_null_incident_id_reads_as_own_incident`, `test_seen_urls_backfill_runs_once_from_last_72h`, `test_prune_seen_urls_is_bounded` (Task 1).
6. **Existing poll tests silently linking** because every `_article()` shares `https://example.com/a`.
   - Pinned by Task 3 Step 0 (title-derived URL default) and the whole existing file staying green.
7. **A9 over- or under-discounting:** macro articles with no entities untouched; new entity or opposite sentiment kept; earliest keeps full weight; evidence rows keep the B6 key set.
   - Pinned by `test_same_incident_recoverage_counts_once`, `test_new_entity_is_not_discounted`, `test_opposite_sentiment_is_not_discounted`, `test_articles_without_entities_are_never_excluded` (Task 5); `test_contribution_rows_record_same_incident` (Task 5).
8. **Leans on silent follow-ups:** every affected symbol on a follow-up row is "mixed"; the update row keeps real leans.
   - Pinned by `test_riyadh_follow_up_is_stored_not_pushed`, `test_severity_rise_pushes_exactly_one_update` (Task 3).

---

### Task 1: Store migration and URL memory (K9 storage, K10 columns) — *integration*

**Files:**
- Modify: `alerting/store.py`, `config/settings.py` (beside `TOPIC_DEDUP_WINDOW_HOURS`), `tests/test_alerting_store.py`

**Interfaces:**
```python
# config/settings.py
INCIDENT_URL_WINDOW_HOURS = 72.0     # B7 K9: URL memory -- a URL attached to an alert this recently marks a follow-up candidate and keeps its first age; also the seen_urls retention
INCIDENT_ENTITY_WINDOW_HOURS = 24.0  # B7 K10: same family + shared named place/actor links only this recently (owner range 24-48 h, tighter end)

# alerting/store.py
_SHOCK_ALERT_ADDED_COLUMNS += (("incident_id", "INTEGER"), ("incident_role", "TEXT"), ("incident_rule", "TEXT"))
INCIDENT_ROLES: tuple[str, ...] = ("follow_up", "update")   # NULL = the incident's first alert
SEEN_URL_RETENTION = dt.timedelta(hours=INCIDENT_URL_WINDOW_HOURS)
SEEN_URL_PRUNE_BATCH = 500
# _SCHEMA adds:
#   CREATE TABLE IF NOT EXISTS seen_urls (url TEXT NOT NULL, alert_id INTEGER NOT NULL, first_seen_utc TEXT NOT NULL,
#       first_published_utc TEXT, PRIMARY KEY (url, alert_id));
#   CREATE INDEX IF NOT EXISTS idx_seen_urls_first_seen ON seen_urls(first_seen_utc);
# and the three columns in CREATE TABLE shock_alerts.

@dataclass ShockAlertRow: + incident_id: Optional[int] = None   # reader fills the row's own id when the column is NULL
                          + incident_role: Optional[str] = None
                          + incident_rule: Optional[str] = None # "url" | "entity:<a,b>"
@dataclass class SeenUrl: url: str; alert_id: int; first_seen_utc: dt.datetime; first_published_utc: Optional[dt.datetime]

def record_alert(..., *, polarity=..., ..., original_severity=...,
                 incident_id: Optional[int] = None, incident_role: Optional[str] = None,
                 incident_rule: Optional[str] = None, first_published_utc: Optional[dt.datetime] = None) -> int
    # incident_id None -> the new row's own id (set in the same transaction); first_published_utc None -> published_utc
def list_incident_alerts(conn: sqlite3.Connection, incident_id: int) -> list[ShockAlertRow]
    # WHERE incident_id = ? OR (incident_id IS NULL AND id = ?) ORDER BY detected_at_utc
def remember_url(conn: sqlite3.Connection, url: str, alert_id: int, seen_at_utc: dt.datetime,
                 published_utc: Optional[dt.datetime]) -> None
    # key = data_layer.news_feed.normalize_url(url); blank -> no-op; INSERT OR IGNORE keeps the first sighting
def lookup_seen_url(conn: sqlite3.Connection, url: str, since_utc: dt.datetime) -> list[SeenUrl]   # newest first_seen first
def prune_seen_urls(conn: sqlite3.Connection, now: dt.datetime, retention: dt.timedelta = SEEN_URL_RETENTION,
                    max_rows: int = SEEN_URL_PRUNE_BATCH) -> int
def _backfill_seen_urls(conn: sqlite3.Connection, now: dt.datetime) -> int
    # alerts detected in the last 72 h: sources[0] -> first_seen = detected_at; later sources -> first_seen = their published_utc;
    # first_published = each source's published_utc. Called by get_connection only when seen_urls did not exist before _SCHEMA ran.
```

- [ ] **Step 1: failing tests** in `tests/test_alerting_store.py`:
  - `test_b7_migration_is_idempotent_on_an_old_db`: a file DB created with the B2 `shock_alerts` DDL (no incident columns, no `seen_urls`) and one row; `get_connection` twice (clearing `store._schema_ready_paths` in between) -> `PRAGMA table_info` has `incident_id`, `incident_role`, `incident_rule`; `seen_urls` exists; no error. Extend `test_migration_tolerates_a_concurrent_duplicate_column` to the three new columns.
  - `test_null_incident_id_reads_as_own_incident`: raw INSERT with `incident_id` NULL -> `get_alert(id).incident_id == id`, `incident_role is None`; `list_incident_alerts(conn, id)` returns exactly that row.
  - `test_record_alert_defaults_incident_to_own_id`: plain `record_alert` -> `incident_id == id`; with `incident_id=7, incident_role="follow_up", incident_rule="url", first_published_utc=<T0>` -> all stored, `first_published_utc == T0` while `sources[0]["published_utc"]` is the article's own time.
  - `test_list_incident_alerts_orders_by_detection`: root + two follow-ups (inserted out of order) -> ids in detection order; a row of another incident is absent.
  - `test_remember_url_keeps_first_sighting`: same URL + alert twice (second later) -> one row, first times unchanged; `"https://X.com/a/?utm_source=t#frag"` and `"https://x.com/a"` are one key; a second alert id adds a second row; blank URL inserts nothing.
  - `test_lookup_seen_url_respects_window`: rows first seen 71 h and 73 h before `now`; `lookup_seen_url(conn, url, now - 72h)` returns only the 71 h row; two rows return newest first.
  - `test_prune_seen_urls_is_bounded`: 600 rows older than 72 h + 3 recent -> `prune_seen_urls(conn, now)` returns 500, then 100, then 0; the 3 recent rows remain.
  - `test_seen_urls_backfill_runs_once_from_last_72h`: old-schema file DB with alert A (detected 10 h ago, 2 sources) and alert B (detected 100 h ago) -> after connect `seen_urls` holds A's two normalized URLs (sources[0] first_seen == A.detected_at, source[1] first_seen == its published), none of B's; delete one row, reconnect with a cleared ready-cache -> still deleted (backfill only runs when the table is created).
- [ ] **Step 2:** `python -m pytest tests/test_alerting_store.py -q -p no:warnings` -> FAIL.
- [ ] **Step 3: implement** as in Interfaces. `get_connection`: check `sqlite_master` for `seen_urls` before `executescript(_SCHEMA)`; after `_migrate_shock_alert_columns`, call `_backfill_seen_urls(conn, now)` only if it was absent (two racing processes both backfilling is harmless: INSERT OR IGNORE). `record_alert` inserts, then `UPDATE ... SET incident_id = COALESCE(?, id)` on the new id before the single commit. Docstrings: dated B7 notes; `record_alert`'s B2 docstring line about `first_published_utc` updated (callers may pass the URL-memory first publication). `prune_seen_urls` docstring: bounded like `prune_near_misses`; update that function's "The only DELETE in the alerting store" line.
- [ ] **Step 4:** run the file -> PASS.
- [ ] **Step 5:** full suites green apart from the known env-only failure.
- [ ] **Step 6:** commit `feat(B7): shock_alerts incident columns and 72h URL memory (seen_urls)`.

---

### Task 2: Entities and incident linking rules (K10 rules, K9 age) — *judgment*

**Files:**
- Create: `data_layer/entities.py`, `alerting/incident.py`, `tests/test_entities.py`, `tests/test_alerting_incident.py`, `tests/fixtures/b7_live_alert_pairs.json`
- Modify: `alerting/dedup.py`, `tests/test_alerting_dedup.py`

**Interfaces:**
```python
# data_layer/entities.py  (pure; shared by alerting/incident.py and scoring/probability_engine.py)
INCIDENT_GAZETTEER: dict[str, tuple[str, ...]]   # canonical -> lower-case aliases (demonyms, metonym capitals, spelling variants)
def incident_entities(text: str) -> frozenset[str]

# alerting/dedup.py
def storm_names(headline: str) -> set[str]       # renamed from _storm_names (public: incident.py uses it)

# alerting/incident.py
CATEGORY_FAMILY: dict[str, str] = {"energy": "energy_geopolitical", "geopolitical_conflict": "energy_geopolitical"}
OPPOSITE_POLARITY: dict[str, str] = {"escalation": "relief", "relief": "escalation", "hawkish": "dovish", "dovish": "hawkish"}
@dataclass(frozen=True) class IncidentCandidate:
    headline: str; category: str; polarity: Optional[str]; url: str
    published_utc: dt.datetime; detected_at_utc: dt.datetime
@dataclass(frozen=True) class IncidentLink:
    incident_id: int; alert_id: int; rule: str      # "url" | "entity:<sorted comma list>"
def category_family(category: str) -> str          # CATEGORY_FAMILY.get(c, c)
def headline_move(headline: str) -> Optional[str]  # "up" | "down" | None (neither or both)
def opposite_direction(polarity_a: Optional[str], headline_a: str, polarity_b: Optional[str], headline_b: str) -> bool
def storm_conflict(headline_a: str, headline_b: str) -> bool   # both name storms and the sets are disjoint
def find_incident(conn: sqlite3.Connection, cand: IncidentCandidate) -> Optional[IncidentLink]
def effective_first_published(conn: sqlite3.Connection, cand: IncidentCandidate) -> dt.datetime
def incident_max_severity(rows: list[ShockAlertRow]) -> str
def update_reason(rows: list[ShockAlertRow], severity: str, polarity: Optional[str], headline: str,
                  classification_failed: bool) -> Optional[str]
    # "severity rose: Medium -> High" | "direction changed: escalation -> relief" | "direction changed: up -> down" | None
```

Rule definitions:
- **Gazetteer** (word-boundary match on the lower-cased headline with `’` -> `'`, longest alias first, compiled once): countries and demonyms in shock news (iran/iranian, iraq/iraqi, israel/israeli, saudi arabia/saudi/saudis/riyadh, uae/united arab emirates/emirati/abu dhabi/dubai, qatar/qatari, kuwait, oman/omani, yemen/yemeni, lebanon/lebanese/beirut, syria/syrian/damascus, egypt/egyptian, libya/libyan, turkey/turkish/türkiye, russia/russian/russians/moscow/kremlin, ukraine/ukrainian/kyiv/kiev, belarus, china/chinese/beijing, taiwan/taiwanese, japan/japanese, north korea/north korean/pyongyang, south korea/south korean/seoul, india/indian, pakistan/pakistani, venezuela/venezuelan, mexico/mexican, canada/canadian, brazil/brazilian, nigeria/nigerian, eu/european union, uk/britain/british); places (hormuz/strait of hormuz, red sea, bab el-mandeb, suez/suez canal, black sea, panama canal, taiwan strait, gaza, west bank, crimea, kharkiv, odesa/odessa, abqaiq, ras tanura, basra, kharg); actors (houthi/houthis, hezbollah, hamas, opec/opec+, iea, nato, iaea, aramco, putin, zelensky/zelenskiy/zelenskyy, netanyahu, khamenei, xi jinping, erdogan, maduro, kim jong un, mbs/mohammed bin salman). Not listed (comment says why): US/U.S./American/Washington, Trump, White House, Fed/Federal Reserve/FOMC, and the ambiguous Chad, Georgia, Jordan, Niger.
- **Headline move:** up = `rise|rises|rose|rising|jump(s|ed)?|surge(s|d)?|climb(s|ed)?|gain(s|ed)?|rall(y|ies|ied)|soar(s|ed)?|spike(s|d)?`; down = `fall(s|ing)?|fell|drop(s|ped)?|slide(s)?|slid|slump(s|ed)?|tumble(s|d)?|plunge(s|d)?|sink(s)?|sank|ease(s|d)?|decline(s|d)?|retreat(s|ed)?`, whole words.
- **opposite_direction:** both polarities known (not None/"unclear") -> `OPPOSITE_POLARITY.get(a) == b`; otherwise both headline moves known and different.
- **Veto** (`_vetoed(cand, row)`): `category_family` differs, or `storm_conflict`.
- **URL rule** (first): for each `store.lookup_seen_url(conn, cand.url, cand.detected_at_utc - 72h)` row, newest first, its alert (`store.get_alert`; skip if missing): not vetoed, not `opposite_direction`, and (`incident_entities` overlap non-empty, or `difflib` headline ratio >= `dedup.SIMILARITY_THRESHOLD`) -> `IncidentLink(row.incident_id, row.id, "url")`.
- **Entity rule** (second): candidate entities non-empty; for each `store.list_recent_alerts(conn, cand.detected_at_utc - 24h)` (newest first) not vetoed with a non-empty overlap -> `IncidentLink(row.incident_id, row.id, "entity:" + ",".join(sorted(overlap)))`. Opposite direction is allowed here (it becomes an update push).
- **effective_first_published:** the seen rows of the URL (72 h) whose alert is not vetoed and not `opposite_direction` -> min of each row's `first_published_utc or first_seen_utc` and the candidate's own `published_utc`; no such row -> `cand.published_utc`.
- **update_reason:** `classification_failed` -> None. Severity rank above `incident_max_severity(rows)` -> `f"severity rose: {max} -> {severity}"`. Else the incident's latest known polarity (most recent row whose polarity is in OPPOSITE_POLARITY) vs a known candidate polarity: opposite -> `f"direction changed: {old} -> {new}"`. Else, if either polarity is unknown, `headline_move` of the candidate vs the most recent row headline with a move: different -> `f"direction changed: {old} -> {new}"`. Else None.
- **dedup.find_existing_alert:** skip an existing alert when `category == "natural_disaster_supply_chain"` and the storm names conflict (both similarity and topic branches).

- [ ] **Step 0: fixture.** Create `tests/fixtures/b7_live_alert_pairs.json` with this read-only snippet (write it with the Write tool to `<scratchpad>/b7_copy_live_fixtures.py`, never into the repo; run from the app dir as `python <scratchpad>/b7_copy_live_fixtures.py tests/fixtures/b7_live_alert_pairs.json`; validated against the live DB on 2026-10-22):
  ```python
  import json, sqlite3, sys
  LIVE = "C:/Users/Masoodt/Documents/Claude/Projects/.worktrees/news-engine-live/Claude_news_engine/news_engine/alerting/shock_alerts.db"
  conn = sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True)
  conn.row_factory = sqlite3.Row
  out = {}
  for alert_no in (12, 13, 33, 39, 41, 43, 46, 52, 54, 55, 71, 72):
      row = conn.execute("SELECT headline, category, detected_at_utc, sources_json FROM shock_alerts WHERE id = ?", (alert_no,)).fetchone()
      out[str(alert_no)] = {"headline": row["headline"], "category": row["category"],
                            "detected_at_utc": row["detected_at_utc"], "sources": json.loads(row["sources_json"])}
  with open(sys.argv[1], "w", encoding="utf-8", newline="\r\n") as fh:
      json.dump(out, fh, indent=1, ensure_ascii=True)
      fh.write("\n")
  ```
  Expect source counts 12:1, 13:4, 33:2, 39:1, 41:4, 43:2, 46:2, 52:3, 54:1, 55:1, 71:3, 72:1; #46's second source URL equals #52's first.
- [ ] **Step 1: failing tests** in `tests/test_entities.py`:
  - `test_entities_of_live_headlines`: from the fixture, #12 and #13 -> `{"iran", "hormuz"}`; #33 -> `{"ukraine", "russia"}`; #39 -> `{"ukraine", "russia", "zelensky"}`; #54 and #55 -> `{"saudi arabia"}`; #71 -> `{"russia"}`; #72 -> `{"russia", "zelensky"}`; #41 -> `{"houthi", "saudi arabia"}`; #43 -> `{"iea"}`; #46 -> `frozenset()`; #52 -> `{"mexico"}`.
  - `test_generic_actors_are_not_entities`: `incident_entities("Trump says Fed must cut as US dollar slides; White House weighs response") == frozenset()`.
  - `test_word_boundaries`: "Omaha refinery" -> no `oman`; "Iranian drones hit tanker" -> `{"iran"}`; "Kremlin’s warning" -> `{"russia"}`; "Zelenskyy" and "Zelenskiy" -> `{"zelensky"}`; "OPEC+ agrees to cut" -> `{"opec"}`.
  - `test_source_has_no_backspace_bytes` (entities.py).
- [ ] **Step 1b: failing tests** in `tests/test_alerting_incident.py` (helper `_seed(conn, n, polarity=None, severity=None, incident_id=None)`: `record_alert` from fixture #n's sources[0] and `detected_at_utc` (severity from arg or "Medium"), `append_source` for the other sources, `remember_url` for every source with first_seen = detected_at for sources[0], else its published; helper `_cand(n, polarity=None)` builds an `IncidentCandidate` from fixture #n):
  - `test_live_pairs_link[12-13|54-55|71-72|33-39]`: `_seed(first)`, `find_incident(conn, _cand(second))` -> `incident_id == first_id`, `rule == "url"`.
  - `test_live_pairs_that_must_not_link[41-43-unclear|41-43-polarity]`: (None, None) and ("escalation", "relief") -> `find_incident(...) is None`.
  - `test_storm_pair_does_not_link`: `_seed(46)` (its seen URLs include #52's URL) -> `find_incident(conn, _cand(52)) is None`.
  - `test_entity_rule_window_is_24h`: `_seed(54)`; candidate "Explosion reported near Riyadh oil facility" (geopolitical, other URL) at #54 detection + 23 h -> rule `"entity:saudi arabia"`; at + 25 h -> None.
  - `test_family_is_respected`: energy candidate "Saudi oil exports disrupted after Riyadh attack" + 2 h links to #54 (geopolitical); the same headline as `central_bank` -> None.
  - `test_trump_only_overlap_does_not_link`: `_seed(71)`; "Trump threatens new tariffs on Iran" (geopolitical, other URL, + 2 h) -> None.
  - `test_url_rule_needs_entity_or_similar_headline`: `_seed(12)`; same URL, energy, "Crude traders brace for volatile week" -> None.
  - `test_restamped_url_keeps_first_publication`: `_seed(33)`; `effective_first_published(conn, _cand(39)) == 2026-10-03T20:17:10Z`; `freshness.age_minutes(that, #39 detected) == 3715` and band `"Very stale"`.
  - `test_new_story_on_reused_url_keeps_own_age`: `_seed(41, polarity="escalation")`; `_cand(43, "relief")` -> `effective_first_published == 2026-10-07T18:18:47Z`. Also #52 after `_seed(46)` -> its own `2026-10-09T21:49:43Z`.
  - `test_headline_move_and_opposite_direction`: `headline_move(#41) == "up"`, `headline_move(#43) == "down"`, `headline_move("Oil rises as stocks fall") is None`; `opposite_direction("escalation", "", "relief", "")` True; `("hawkish", "", "escalation", "")` False; `(None, #41, "unclear", #43)` True.
  - `test_update_reason_cases`: rows [root Medium "escalation"] -> `update_reason(rows, "High", "escalation", h, False) == "severity rose: Medium -> High"`; `("Medium", "escalation")` -> None; `("Medium", "relief")` -> `"direction changed: escalation -> relief"`; `("Medium", "unclear", "Oil prices fall ...")` with root headline "Oil rises ..." and root polarity None -> `"direction changed: up -> down"`; `classification_failed=True` with "High" -> None; rows [root High, follow-up Medium] with "High" -> None.
  - `test_source_has_no_backspace_bytes` (incident.py).
- [ ] **Step 1c: failing test** in `tests/test_alerting_dedup.py`: `test_similar_headline_different_storm_does_not_merge`: existing #46 headline (natural_disaster_supply_chain, detected 1 h ago) -> `find_existing_alert("Hurricane Simon strengthens as US Gulf Coast prepares for landfall - Reuters", ...) is None` (ratio 0.954 today merges it); `"Hurricane Isaias strengthens further as US Gulf Coast braces for landfall - Reuters"` still returns #46's id.
- [ ] **Step 2:** `python -m pytest tests/test_entities.py tests/test_alerting_incident.py tests/test_alerting_dedup.py -q -p no:warnings` -> FAIL.
- [ ] **Step 3: implement** as in Rule definitions. Module docstrings cite SA-04, the live pairs and the owner decision, and state the limits (headline-only entities, gazetteer coverage, no LLM key). `incident.py` imports `store`, `dedup`, `data_layer.entities`; it never writes.
- [ ] **Step 4:** run the three files -> PASS.
- [ ] **Step 5:** full suites green apart from the known env-only failure.
- [ ] **Step 6:** commit `feat(B7): incident linking rules (URL memory + named entities) with live-pair fixtures`.

---

### Task 3: Poll wiring, Telegram update text, escalation guard — *integration*

**Files:**
- Modify: `alerting/poll_once.py`, `alerting/notify_telegram.py`, `tests/test_alerting_poll_once.py`, `tests/test_alerting_notify_telegram.py`

**Interfaces:**
```python
# alerting/notify_telegram.py
def send_alert(..., freshness_line: Optional[str] = None,
               update_of_incident: Optional[int] = None, update_reason: Optional[str] = None) -> bool
    # update_of_incident set: line 1 is the normal severity prefix (never "ESCALATION"), line 2 is
    # f"Update to incident #{n}: {headline}", then the freshness line, then f"Why pushed: {update_reason}" when given

# alerting/poll_once.py
@dataclass(frozen=True) class _Assessment:
    category: str; severity: str; raw_severity: str; method: str; rationale: Optional[str]
    polarity: str; country: Optional[str]; us_link: Optional[str]; capped: bool; classification_failed: bool
def _record_follow_up(conn, webapp_conn, article: NewsArticle, link: incident.IncidentLink, a: _Assessment,
                      first_published: dt.datetime, detected_at: dt.datetime) -> int
FOLLOW_UP_LEAN_WHY = "follow-up of incident #{n}: no new lean"
```

Flow of `_process_matched` after the severity cap (one `detected_at`):
1. Dedup match (unchanged) -> `append_source`, then `store.remember_url(conn, article.url, existing_id, detected_at, article.published_utc)`, then `_maybe_escalate`, outage notice, return.
2. `cand = incident.IncidentCandidate(...)`; `first_published = incident.effective_first_published(conn, cand)`; `link = incident.find_incident(conn, cand)`.
3. Link -> `_record_follow_up(...)`: `rows = store.list_incident_alerts(conn, link.incident_id)`; `reason = incident.update_reason(rows, a.severity, a.polarity, article.title, a.classification_failed)`; role `"update"` if reason else `"follow_up"`; affected = full leans for an update, else the same symbols with `lean="mixed"`, `lean_why=FOLLOW_UP_LEAN_WHY.format(n=link.incident_id)`; `record_alert(..., incident_id=link.incident_id, incident_role=role, incident_rule=link.rule, first_published_utc=first_published)`; `remember_url`; update and `_should_push(severity, False)` -> `send_alert(..., update_of_incident=link.incident_id, update_reason=reason, freshness_line=freshness_line(first_published, detected_at), cap_note=...)` and its delivery status; silent -> `set_delivery_status(conn, id, "follow_up")`. One log line: `[poll_once] incident #<n> <role> (<rule>): <headline!r> -- update pushed (<reason>)` or `-- stored, no push`. Outage notice still runs.
4. No link -> today's new-alert path with `first_published_utc=first_published` and `freshness_line(first_published, detected_at)`, then `remember_url`.
5. `run_poll_cycle` calls `store.prune_seen_urls(conn, now)` after `prune_near_misses`.
6. `_maybe_escalate`: return early when the capped new severity does not rank above `incident.incident_max_severity(store.list_incident_alerts(conn, existing.incident_id))` (replaces the comparison with `existing.severity`; docstring updated).

- [ ] **Step 0:** `_article(title, url=None)` defaults to `"https://example.com/" + slug(title)` (comment: B7 links alerts sharing a URL; distinct test stories need distinct URLs). Run the file: still green.
- [ ] **Step 1: failing tests** in `tests/test_alerting_poll_once.py` (helper `_live_cycle(conn, webapp, n, severity, polarity, category=None, send=None)`: one cycle with fixture #n's sources[0] as the article, `_utcnow` patched to #n's `detected_at_utc`, real dedup, LLM path via `_triage_result` + `_classification`):
  - `test_riyadh_follow_up_is_stored_not_pushed`: #54 High escalation, then #55 High escalation -> `send.call_count == 1`; second row `incident_id == first.id`, `incident_role == "follow_up"`, `incident_rule == "url"`, `delivery_status == "follow_up"`, every affected symbol `lean == "mixed"` with `lean_why == f"follow-up of incident #{first.id}: no new lean"`; `first_published_utc == 2026-10-10T14:29:39Z`.
  - `test_same_severity_follow_ups_send_no_push[12-13|71-72]`: Medium/Medium -> one push, two rows, one incident.
  - `test_severity_rise_pushes_exactly_one_update`: #33 Medium escalation, #39 High escalation -> `send.call_count == 2`; second call kwargs `update_of_incident == id33`, `update_reason == "severity rose: Medium -> High"`, `freshness_line == "Published 3 Oct 22:17 SAST · +3715 min · Very stale"`; row role `"update"`, its symbols carry real leans (not all "mixed"). Then #39's article re-run 1 h later, High escalation -> `send.call_count` stays 2.
  - `test_follow_up_row_stores_original_first_published`: after #33 -> #39, row 2 `first_published_utc == 2026-10-03T20:17:10Z` and the route-facing `freshness.freshness_band(age_minutes(...)) == "Very stale"`.
  - `test_direction_flip_pushes_an_update`: #54 High escalation, then "Riyadh airport reopens as Saudi authorities say blast contained" (geopolitical, new URL, + 3 h) High relief -> second push `update_reason == "direction changed: escalation -> relief"`, `incident_rule == "entity:saudi arabia"`.
  - `test_live_blog_pair_alerts_twice`: #41 High escalation, #43 Medium relief -> 2 pushes, neither with `update_of_incident`; #43 row is its own incident with `first_published_utc == 2026-10-07T18:18:47Z`.
  - `test_storm_pair_alerts_twice`: #46 seeded through the store (both its source URLs remembered), then #52 cycle High -> pushed, `update_of_incident is None`, own incident.
  - `test_failed_classification_follow_up_is_silent`: #54 then #55 with every provider failed -> no second push, row role `"follow_up"`.
  - `test_dedup_escalation_is_measured_against_the_incident_max`: root High; follow-up row Medium in the same incident; dedup patched to the follow-up's id; corroborating High -> `send` not called, follow-up severity unchanged. A root Medium with a High corroboration still escalates (existing tests stay green).
  - `test_dedup_match_remembers_the_url`: dedup match -> `lookup_seen_url` returns the matched id.
  - `test_cycle_prunes_seen_urls`: `store.prune_seen_urls` spy called once per cycle.
- [ ] **Step 1b: failing tests** in `tests/test_alerting_notify_telegram.py`:
  - `test_update_push_names_the_incident_and_why`: capture the posted text; lines[0] starts with the HIGH prefix, lines[1] == `"Update to incident #33: EXCLUSIVE: Ukraine will hit Russian refineries in response to Moscow's 'new doctrine' of airstrikes, Zelenskiy says - Reuters"`, the freshness line follows, a line `"Why pushed: severity rose: Medium -> High"` is present, "ESCALATION" is absent.
  - `test_plain_alert_text_is_unchanged`: no update args -> text identical to today's format (headline on line 2).
- [ ] **Step 2:** run both files -> FAIL.
- [ ] **Step 3: implement** the flow above; dated `B7 (2026-10-22)` comments; module docstring of `poll_once.py` gains one paragraph on incidents (linked and labelled, never suppressed; push only on severity rise or direction flip).
- [ ] **Step 4:** run both files -> PASS.
- [ ] **Step 5:** full suites green apart from the known env-only failure.
- [ ] **Step 6:** commit `feat(B7): follow-ups stored on their incident; push once as "Update to incident #N" on severity rise or direction flip`.

---

### Task 4: Shock Alerts tab and API labels — *mechanical*

**Files:**
- Modify: `webapp/app.py` (`get_shock_alerts`), `tests/test_app_shock_alerts_route.py`, `webapp/static/js/shock-alerts/alert-meta.js`, `webapp/static/js/shock-alerts/alert-meta.test.js`, `webapp/static/js/shock-alerts/table.js`

**Interfaces:**
```python
# /api/shock-alerts row gains: "incident_id": int (own id for a first/old alert), "incident_role": "follow_up" | "update" | None,
#                              "incident_rule": "url" | "entity:<a,b>" | None
```
```js
// alert-meta.js
export function incidentLabelText(row)   // escaped text; "" for the incident's first alert
// "Follow-up of incident #12 · same article URL · no push, no new lean"
// "Follow-up of incident #54 · shared: saudi arabia · no push, no new lean"
// "Update to incident #33 · same article URL"
```

- [ ] **Step 1: failing tests:**
  - `tests/test_app_shock_alerts_route.py`: `EXPECTED_ROW_KEYS` gains the three keys (exact set test); `test_shock_alert_route_serves_incident_fields`: a root and a follow-up (`incident_id=root, incident_role="follow_up", incident_rule="url"`) -> served values match; a raw NULL-incident row is served with `incident_id == id`, role and rule None.
  - `alert-meta.test.js`: `incidentLabelText` returns the three strings above for (role follow_up, rule url), (follow_up, entity:saudi arabia), (update, url); `""` for `{id: 12, incident_id: 12, incident_role: null}` and for a row without the keys; a rule containing `<b>` comes back escaped.
- [ ] **Step 2:** `python -m pytest tests/test_app_shock_alerts_route.py -q -p no:warnings` and `npm test` -> FAIL.
- [ ] **Step 3: implement:** route adds the keys; `table.js` renders `incidentLabelText(row)` as its own `meta-text-sm` line under the headline when non-empty. No grouping or sorting change.
- [ ] **Step 4:** both -> PASS.
- [ ] **Step 5:** full suites green apart from the known env-only failure.
- [ ] **Step 6:** commit `feat(B7): Shock Alerts tab and API show incident id and follow-up/update labels`.

---

### Task 5: Same-incident exclusion for articles (A9) — *judgment*

**Files:**
- Modify: `config/settings.py` (beside `REDUNDANCY_*`), `scoring/probability_engine.py`, `scoring/backtest_accumulator.py`, `scoring/backtest_store.py` (comment only), `tests/test_probability_engine.py`, `tests/test_backtest_accumulator.py`

**Interfaces:**
```python
# config/settings.py
SAME_INCIDENT_MIN_WORD_OVERLAP = 0.25    # B7 A9: Jaccard of significant title+summary words also required (two "China" stories are not one incident)
SAME_INCIDENT_SENTIMENT_EPSILON = 0.05   # |usd_sentiment| below this has no direction; opposite directions above it are a new development

# scoring/probability_engine.py
def _is_same_incident(earlier: ArticleContribution, later: ArticleContribution) -> bool
    # incident_entities(title + " " + summary) equal and non-empty, AND not (both |s| >= eps with opposite signs),
    # AND Jaccard(_significant_words) >= SAME_INCIDENT_MIN_WORD_OVERLAP; no time limit (the bundle window is 72 h)
def _apply_same_incident_exclusions(contributions: list[ArticleContribution]) -> tuple[list[ArticleContribution], list[ArticleContribution]]
    # earliest published first; compared only against already-kept contributions; returns (kept, excluded)
@dataclass ProbabilityResult: + same_incident_excluded: list[ArticleContribution] = field(default_factory=list)

# scoring/backtest_accumulator.py
def _build_article_contribution_rows(contributions: list, excluded: list[tuple],
                                     same_incident: list = ()) -> list[dict]
    # same_incident rows: status "excluded", reason "same_incident", usd_sentiment kept, every weight field None, matched_terms []
```

In `score_bundle`, `_apply_same_incident_exclusions` runs right after `_build_contributions` and before `_apply_redundancy_discounts`, so excluded articles reach neither aggregation, agreement, the contradiction check, the thin-sample count nor `article_count`.

- [ ] **Step 1: failing tests** in `tests/test_probability_engine.py` (articles with `native_sentiment`, summary "", in one bundle):
  - `test_same_incident_recoverage_counts_once`: "Iran seizes oil tanker in Strait of Hormuz" (t0, +0.4), "Tanker seized by Iran near Hormuz as oil jumps" (t0 + 30 h, +0.3), "Iran holds seized tanker in Hormuz, oil tanker crew detained" (t0 + 50 h, +0.35) -> `article_count == 1`, `[c.article.title for c in result.same_incident_excluded]` == the two later titles, and `aggregate_usd_sentiment` equals the result for the first article alone.
  - `test_new_entity_is_not_discounted`: second article "Iran and Israel trade strikes after Hormuz tanker seizure" (+0.4) -> kept, `same_incident_excluded == []`.
  - `test_opposite_sentiment_is_not_discounted`: second "Tanker seized by Iran near Hormuz as oil jumps" with -0.4 -> kept.
  - `test_low_word_overlap_is_not_discounted`: "China imposes export curbs on rare earths" / "China retaliates with tariffs on US farm goods" (both `{"china"}`, overlap < 0.25) -> both kept.
  - `test_articles_without_entities_are_never_excluded`: "Fed watchers brace for a hot CPI print", "US inflation expected to cool in September CPI", "Traders eye CPI as Fed weighs cuts" (same sign, within 6 h) -> none excluded, `article_count == 3`.
  - `test_same_incident_runs_before_redundancy_discount`: "Oil tanker seized in Strait of Hormuz, shipping sources say" (t0) and "Oil tanker seized in Strait of Hormuz by Iran, shipping sources say" (t0 + 10 min, entity sets `{"hormuz"}` vs `{"hormuz", "iran"}`) -> both kept, the second `redundancy_discounted is True`, `same_incident_excluded == []`.
- [ ] **Step 1b: failing tests** in `tests/test_backtest_accumulator.py`:
  - `test_contribution_rows_record_same_incident`: one same-incident contribution -> a row with `status == "excluded"`, `reason == "same_incident"`, `usd_sentiment == 0.3`, `combined_weight is None`, `weight_pct is None`; row key set equals the existing B6 row key set; included rows' `weight_pct` still sum to 100 over included rows only.
  - `test_record_prediction_stores_same_incident_rows`: through `score_and_record_event` with a stub source returning the three Iran/Hormuz articles (relevance keywords patched for the event) -> `get_prediction_article_contributions` has 2 rows with reason `same_incident`; the recorded log line contains `same_incident excluded: 2`.
- [ ] **Step 2:** run both files -> FAIL.
- [ ] **Step 3: implement.** Settings with a dated B7 comment (AS-01, owner "count once"). `backtest_store.py`: the `reason` field comment lists `same_incident` (no schema change). `score_and_record_event` passes `result.same_incident_excluded` into the rows builder and appends `(same_incident excluded: n)` to the `recorded` print when n > 0. The B6 `redundancy_discount` behaviour is otherwise unchanged.
- [ ] **Step 4:** run both files -> PASS.
- [ ] **Step 5:** full suites green apart from the known env-only failure. Any existing scoring test whose articles now collapse as one incident gets distinct stories (headline change, with a comment); list them in the commit body.
- [ ] **Step 6:** commit `feat(B7): article re-coverage of one incident counts once (same_incident exclusion)`.

---

### Task 6: Docs — *mechanical*

**Files:**
- Create: `docs/b7-deploy.md`
- Modify: `docs/feature-inventory-2026-09-11.md`, `docs/roadmap-2026-10-20.md`

- [ ] **Step 1: `docs/b7-deploy.md`** (applied at deploy by the controller; same shape as `docs/b6-deploy.md`, times SAST):
  1. What changes at merge with no step: the 2-minute poller (fresh process per tick) migrates `alerting/shock_alerts.db` on its first tick (three nullable columns, `seen_urls` table backfilled from the last 72 h of alerts); old alerts read as their own incident; follow-ups stop pushing; article scoring excludes same-incident re-coverage from the accumulator restart onward (expect one material-change prediction row per active event on the first cycle, because `article_count` drops). No Windows or Claude scheduled task changes.
  2. Backups first (SQLite backup API, both DBs): `alerting\shock_alerts.db` -> `alerting\shock_alerts.db.pre_b7_<date>` and `scoring\backtest_log.db` -> `scoring\backtest_log.db.pre_b7_<date>`, with the same one-line `python -c "... s.backup(d) ..."` command as B6.
  3. Stop the single engine copy (B6 step 3 commands verbatim).
  4. Merge `b7-same-incident` into `news-engine/batch-predictions-queries` and fast-forward the live worktree.
  5. Start exactly one copy: `schtasks /run /tn NewsEngine_AutoStart`. Record the restart time (UTC and SAST) in the feature inventory B7 row as the change date.
  6. Verify: `PRAGMA table_info(shock_alerts)` lists `incident_id`, `incident_role`, `incident_rule`; `SELECT COUNT(*) FROM seen_urls` > 0 after the next poll tick; the poll log shows `incident #<n> follow_up (...) -- stored, no push` the next time a story is re-covered; `/api/shock-alerts` rows carry `incident_id`; after the next recorded prediction `SELECT reason, COUNT(*) FROM prediction_article_contributions WHERE recorded_at_utc >= '<restart UTC>' GROUP BY 1` may show `same_incident`.
  7. Rollback: stop as in step 3, revert the merge, restart one copy; the new columns and table stay (unread after the revert); restore the `pre_b7` backups only if needed.
- [ ] **Step 2: feature inventory:** batch table row `B7 Same incident, one voice | Correctness | built on branch b7-same-incident (not merged; scoring change on deploy)`; a feature row after the B6 article-read row: "Same incident, one voice: URL memory (72 h), incident linking (URL + named place/actor, storm veto), follow-ups stored and labelled with push only on severity rise / direction flip, same-incident article exclusion (B7; files ...)" | **Built (branch, not merged)** | "**Change date (deploy restart, UTC / SAST): <to be recorded at deploy>.** Detail: `docs/b7-deploy.md`".
- [ ] **Step 3: roadmap:** status line (line 3) appends "B7 built on branch b7-same-incident (not merged)"; the B7 line of the batch table's last column notes `built on branch b7-same-incident`.
- [ ] **Step 4:** full suites green; `git diff --stat` touches only the three docs.
- [ ] **Step 5:** commit `docs(B7): deploy runbook, inventory and roadmap status`.
