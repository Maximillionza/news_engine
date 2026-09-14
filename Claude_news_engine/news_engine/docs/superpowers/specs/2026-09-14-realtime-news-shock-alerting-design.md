# Real-Time News-Shock Alerting — Design

**Date:** 2026-09-14
**Status:** Approved via conversational brainstorm (architectural path)
**Builds on:**
- The `tier1-cpi-ppi-autoresearch` scheduled task's Step 0 exogenous-shock detection (`data_layer/discovery_detector.py`, `scoring/backtest_store.py`'s `exogenous_shocks` table) — same "genuinely exogenous, not already explained by a scheduled calendar release" concept, applied here to live news instead of yesterday's closed price bar.
- `data_layer/news_feed.py` / `data_layer/rss_sources.py` — the existing free RSS/news article fetchers, currently wired only into pre-event sentiment scoring. This spec adds a second, independent consumer of the same sources.
- `webapp/store.py`'s `list_tracked_symbols()` — the live tracked-instrument list this spec's relevance mapping reads directly, same pattern the Tier 1 scheduled task already uses.
- `webapp/symbols.py`'s `classify_symbol()` and `scoring/probability_engine.py`'s `_check_oil_shock` — the existing usd_relationship / oil-transmission logic this spec's `symbol_relevance.py` reuses rather than re-deriving.
- `data_layer/dukascopy_feed.py`'s `get_price_at()` — the existing shared tick-fetch primitive the weekly reality check uses for price lookups (not a new fetch mechanism).
- `AdHoc_Category_Taxonomy` (`docs/News_Engine_Causation_Matrix_v2.xlsx`) — the existing 8-category exogenous taxonomy used for backward-looking backtest research. This spec deliberately defines a new, broader taxonomy sized for real-time alerting rather than forcing live headlines into the narrower 8 (see Scope boundary).

## Problem

Existing exogenous-shock detection (`discovery_detector.py`, Step 0 of the Tier 1 scheduled task) is price-first and once-daily: it notices a large *already-closed* daily price move and only then looks backward for a same-day headline cause, purely to annotate the backtest research table (`exogenous_shocks`). It cannot alert on anything — by the time it runs, the move happened a day earlier. Nothing in this codebase currently does the reverse: catch a market-moving news event as it breaks and push an alert before or as the reaction unfolds, so real shocks (a chokepoint closure, a surprise sanctions action, a Fed-independence crisis) aren't missed because no one happened to be watching a screen when they hit.

## Scope boundary

- **News-first, price-second.** This tool detects on headline content arriving in near-real-time; it never waits for a price move to trigger an alert. (The existing daily `discovery_detector.py` remains the price-first, backward-looking tool — this is a deliberate second, independent detector, not a replacement.)
- **Standalone storage.** A brand-new database (`alerting/shock_alerts.db`), deliberately *not* merged into `dashboard.db` or `backtest_log.db` until proven worth integrating — explicit decision, with the long-term intent being to fold this into the existing news_engine framework once it's earned that.
- **No Claude Code session in the loop.** The poller and the weekly reality check are plain Python scripts fired by Windows Task Scheduler. The only LLM involvement anywhere in this design is a single, per-ambiguous-candidate `anthropic.Anthropic()` API call (Haiku 4.5) — never an agentic session, never a fixed cost paid every poll cycle regardless of whether anything happened.
- **Free sources only, for v1.** `rss_sources.py`'s existing free feeds (Reuters via Google News proxy, CNBC, Investing.com forex). A paid real-time wire is an explicit, deferred future upgrade — only if real coverage gaps show up in practice, never built preemptively.
- **Advisory only.** Severity tiers and category classification are for the user's attention/triage. Nothing here places a trade, and nothing here auto-adjusts any scoring/prediction logic elsewhere in the project (`probability_engine.py`, `Tier1Prediction`, etc.).
- **Reclassification is manual.** The weekly reality check flags mismatches between an alert's assigned tier and its realized market impact; it never auto-changes a stored alert's tier, the taxonomy, or the magnitude thresholds — same "manual judgment, not a formula" discipline this project already applies to `Tier1Prediction.predicted_direction`.

## Architecture

### 1. New package — `alerting/`

```
alerting/
    __init__.py
    store.py            # standalone DB — shock_alerts table + non-match audit log
    taxonomy.py          # new broader category set + hard rule-tier patterns
    triage.py            # rule-based first pass over each article
    llm_classify.py       # single Haiku call for ambiguous candidates
    symbol_relevance.py   # category -> affected tracked symbols + channel
    dedup.py             # content-similarity + time-window fingerprinting
    notify_telegram.py    # Telegram Bot API push, High tier only
    poll_once.py          # Task Scheduler entry point — one poll cycle, exits
    reality_check.py      # Task Scheduler entry point — weekly, exits
```

#### `taxonomy.py`

```python
# Broader than AdHoc_Category_Taxonomy's 8 (those were sized for backward-
# looking backtest research on already-detected price anomalies, not for
# triaging arbitrary live headlines) -- researched from real historical
# wire-service phrasing per category, never guessed. Populated as its own
# implementation-plan task, not invented inline here.
SHOCK_CATEGORIES = [
    "energy",                      # chokepoint closures, OPEC+ moves, pipeline attacks, sanctions on exporters
    "geopolitical_conflict",       # war declarations, military strikes, escalation events
    "central_bank",                # surprise policy moves, Fed-independence shocks, emergency meetings
    "sovereign_fiscal",            # credit-rating actions, shutdowns, Treasury buyback/schedule changes
    "trade_policy",                # tariff executive actions, trade-war escalation
    "natural_disaster_supply_chain",
]

# Rule-tier: matches here skip the LLM call entirely and are always High.
# Researched real phrasing per category (chokepoint names, "declares war",
# sanctions-imposed language, etc.) -- populated as a real research task,
# not fabricated ad hoc.
HARD_RULE_PATTERNS: dict[str, list[str]] = {...}

# Softer category-signal keywords -- a match here means "plausible
# candidate," escalated to llm_classify.py for a real severity/category
# judgment rather than auto-tiered.
CATEGORY_SIGNAL_KEYWORDS: dict[str, list[str]] = {...}
```

#### `triage.py`

```python
@dataclass
class TriageResult:
    matched: bool
    category: Optional[str]
    rule_tier_hit: bool          # True => severity is High, no LLM call needed
    matched_keywords: list[str]
    near_miss_score: Optional[float]  # for the non-match audit log below

def triage_article(article: NewsArticle) -> TriageResult:
    """
    Pure function, no I/O. Checks `article` against HARD_RULE_PATTERNS
    first (unambiguous -> rule_tier_hit=True, done); then
    CATEGORY_SIGNAL_KEYWORDS (plausible category, ambiguous severity ->
    escalate to llm_classify.py); otherwise matched=False and
    near_miss_score records how close the closest category came, purely
    for the non-match audit log -- never used to alert on its own.
    """
```

#### `llm_classify.py`

```python
@dataclass
class ClassificationResult:
    category: str
    severity: str            # "High" | "Medium" | "Low"
    rationale: str
    classification_failed: bool = False   # True => caller falls back to Medium/dashboard-only

def classify_candidate(article: NewsArticle, triage: TriageResult) -> ClassificationResult:
    """
    Single anthropic.Anthropic() call (Haiku 4.5, structured output) --
    plain API call, NOT a Claude Code session, no per-cycle fixed cost.
    On any API error or malformed response: classification_failed=True,
    category=triage.category, severity="Medium" -- never dropped, never
    crashes the poll cycle.
    """
```

#### `symbol_relevance.py`

```python
@dataclass
class SymbolImpact:
    symbol: str
    channel: str      # e.g. "safe_haven", "risk_sentiment", "oil_linkage" -- human-readable, not a formula output

def affected_symbols(category: str, tracked_symbols: list[str]) -> list[SymbolImpact]:
    """
    tracked_symbols comes from webapp.store.list_tracked_symbols() at
    call time -- live, not cached, same pattern the Tier 1 scheduled task
    already uses. Reuses webapp.symbols.classify_symbol() for the
    usd_relationship baseline and scoring/probability_engine.py's
    _check_oil_shock()-style logic where a category already has real,
    coded transmission logic; falls back to a small category -> symbol-
    class lookup table for categories that logic doesn't cover yet.
    Returns [] (not fabricated) if no real relevance can be established
    for any currently-tracked symbol -- an honest "doesn't affect what
    you're tracking today" result.
    """
```

#### `dedup.py`

```python
def find_existing_alert(candidate_headline: str, category: str, conn, window_hours: float = 6.0) -> Optional[int]:
    """
    difflib-based similarity (same approach news_feed.py already imports
    for article de-duplication) against shock_alerts rows in `category`
    logged within `window_hours`. Returns the existing alert's id on a
    real match (caller appends this source as corroboration, does NOT
    fire a new push), or None (a genuinely new alert). Accepted v1
    limitation: two distinct events with similar wording in the same
    window could merge -- flagged, not solved; tune window/threshold if
    it becomes a real problem in practice.
    """
```

#### `notify_telegram.py`

```python
def send_alert(alert_row) -> bool:
    """
    Telegram Bot API push for High-tier alerts only. Retried with
    backoff on failure, but the alert row is ALWAYS persisted before this
    is ever called -- a failed push never means a lost alert, just a
    `delivery_status="failed"` flag surfaced on the dashboard for manual
    follow-up.
    """
```

### 2. Persistence — `alerting/store.py`

```sql
CREATE TABLE IF NOT EXISTS shock_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    sources_json TEXT NOT NULL,        -- list of {source, url, published_utc} -- corroborating sources appended here by dedup.py, not new rows
    detected_at_utc TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,             -- "High" | "Medium" | "Low"
    classification_method TEXT NOT NULL, -- "rule_tier" | "llm" | "llm_failed_fallback"
    rationale TEXT,
    affected_symbols_json TEXT NOT NULL, -- list of {symbol, channel} from symbol_relevance.py
    delivery_status TEXT,               -- NULL for Medium/Low; "sent" | "failed" for High
    -- reality-check fields, filled in weekly, NULL until then:
    reality_move_5min_json TEXT,
    reality_move_secondary_json TEXT,
    reality_check_at_utc TEXT,
    reality_mismatch INTEGER            -- 0/1/NULL (NULL = not yet checked, or no price data available)
);

CREATE TABLE IF NOT EXISTS shock_near_misses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    closest_category TEXT,
    near_miss_score REAL,
    seen_at_utc TEXT NOT NULL
    -- rolling log, pruned after N days -- for periodic keyword-list
    -- review, never read by the live alerting path itself
);

CREATE TABLE IF NOT EXISTS poll_cursor (
    source TEXT PRIMARY KEY,
    last_seen_utc TEXT NOT NULL         -- per-source cursor so poll_once.py never reprocesses the same articles
);
```

### 3. Poll cycle — `poll_once.py` (Task Scheduler, every 1-2 minutes)

1. For each source in `rss_sources.py`'s free feeds: fetch articles newer than `poll_cursor.last_seen_utc`. A single source's fetch failure is caught and skipped — never blocks the others (same per-series isolation as `discovery_detector.py`).
2. Each new article -> `triage_article()`. No match -> logged to `shock_near_misses` if it scored close to any category, cursor still advances, nothing else happens. Rule-tier hit or category-signal match -> continue.
3. Category-signal match (not already rule-tier) -> `classify_candidate()` (Haiku).
4. `find_existing_alert()` -> match found: append this source to the existing row's `sources_json`, done, no new push. No match -> new alert.
5. `affected_symbols()` against the live tracked-symbol list.
6. Persist the row to `shock_alerts` regardless of tier.
7. `severity == "High"` -> `send_alert()` (Telegram). Medium/Low -> dashboard-only (already persisted).
8. Update `poll_cursor` for each source successfully processed.

### 4. Weekly reality check — `reality_check.py` (Task Scheduler, weekly)

1. Query `shock_alerts` rows from the past week with `reality_check_at_utc IS NULL`.
2. For each row, for each `affected_symbols` entry: fetch price via `dukascopy_feed.get_price_at()` at `detected_at_utc`, `detected_at_utc + 5min`, and `detected_at_utc + 30min` (secondary window — catches a real reaction that built slightly slower than the 5-minute cutoff, so it isn't wrongly marked as "alert was wrong"). A fetch failure for any symbol/timestamp -> `None`, never fabricated, logged as "no data available for reality check," not treated as a mismatch.
3. Compare the realized move at each checkpoint against the per-symbol/tier magnitude thresholds (v1 defaults below). Write `reality_move_5min_json`, `reality_move_secondary_json`, `reality_check_at_utc`, and `reality_mismatch` (1 if the realized move contradicts the assigned tier — e.g. a High-tier alert with no meaningful move at either checkpoint, or a Low-tier alert that actually spiked hard) back onto the row.
4. Output a short summary report (console/file) of flagged mismatches for manual review — this step never rewrites `category`, `severity`, the taxonomy, or the thresholds itself.

**V1 magnitude thresholds (tunable, not fixed)** — set to trigger on the fast, immediate-spike pattern these events actually show, not a slow drift:

| Symbol | Window | Threshold |
|---|---|---|
| XAUUSD | 5 min | $10 |
| US30 | 5 min | 150 points |

(Percentage-matched: $10 on gold's ~$2,800-3,000/oz base ≈ 0.35%; 150pts on US30's current level is the equivalent percentage move. Both are expected to be retuned once real alert examples accumulate.)

### 5. Dashboard — read-only addition to `webapp/app.py`

One new route (e.g. `/api/shock-alerts`) opens `alerting/shock_alerts.db` directly (no schema coupling to `dashboard.db`) and returns recent rows. One new panel in the existing static frontend: High/Medium alerts shown prominently, Low collapsed behind a toggle, each row showing category, severity, rationale, sources, affected symbols, and (once available) the reality-check result.

## Error handling

- Per-source RSS fetch failure: caught, logged, skipped — never blocks the rest of the poll cycle (`discovery_detector.py`'s existing per-series isolation pattern).
- LLM classification failure (network/API error, malformed structured output): falls back to `severity="Medium"`, `classification_method="llm_failed_fallback"`, never dropped, never crashes the cycle.
- Telegram send failure: retried with backoff; the alert row is always persisted *before* the send attempt, so a push failure never means a lost alert — `delivery_status="failed"` surfaces on the dashboard for manual follow-up.
- `reality_check.py` price-fetch failure (market closed, feed gap): logged as "no data available," never forced to a mismatch/match result — same `None`-not-fabricated discipline as `compute_daily_move()`.
- Dedup false-positive risk (two distinct events with similar wording merged within the window): accepted v1 limitation, flagged not solved.
- Poll cursor write failure: next cycle re-processes safely (dedup catches any re-fired duplicates) rather than losing articles or crash-looping.

## Testing

Matches this project's existing `tests/test_*.py` convention (e.g. `test_discovery_detector.py`, `test_dukascopy_feed.py`):

- Pure logic — `triage_article()`'s keyword/pattern matching, `find_existing_alert()`'s similarity+window logic, `affected_symbols()`'s category-to-symbol mapping, and `reality_check.py`'s threshold comparison — gets real unit tests with synthetic inputs, no network, deterministic.
- I/O boundaries (RSS fetch, `classify_candidate()`, `send_alert()`, `get_price_at()`) are mocked in unit tests. A small number of real, manually-run integration checks follow this project's existing `tests/run_*.py` pattern (real pulls, not part of automated CI).
- `taxonomy.py`'s keyword lists are themselves a research deliverable (real historical wire-service phrasing per category), not fabricated — their own implementation-plan task, verified against real historical headlines for each category before being trusted in triage.
- No fabricated "pretend a shock happened" test data reaches the live alerting or reality-check path — same predict-then-check discipline as every other real signal in this project.

## Open items carried into the implementation plan (not blocking this design)

- Research and populate `taxonomy.py`'s `HARD_RULE_PATTERNS` / `CATEGORY_SIGNAL_KEYWORDS` from real historical examples per category.
- Confirm Telegram bot setup (BotFather token + chat ID) — user has asked for hands-on help with this step.
- Confirm Windows Task Scheduler entries (poll cadence, weekly reality-check timing) at implementation time.
- `shock_near_misses` pruning policy (how many days to retain) — reasonable default to propose in the plan, not fixed here.
