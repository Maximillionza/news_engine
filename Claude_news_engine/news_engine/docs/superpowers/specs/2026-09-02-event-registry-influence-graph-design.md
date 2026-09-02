# Recurring Event Registry & Influence Graph — Design

**Date:** 2026-09-02
**Status:** Approved via conversational brainstorm (architectural path)
**Builds on:**
- `docs/fundamental-analysis-monthly-event-map-2026-09-02.md` — the ~55-event map and §6/§7's precursor chains and confluence/conflict/modulation framework this spec operationalizes.
- The fundamental-signals-batch (COT/equity-risk/oil-shock) — confirmed complete and merged into this branch's history by a peer session (verified 2026-09-02: all 6 planned tasks landed, 434/435 tests passing, matches its spec exactly). This spec does not touch that work.
- `low-impact-context-tracking` (still on its own unmerged branch) — this spec's "Low tier tracked-only, no dashboard score" requirement is the exact behavior that branch already builds (`calendar_events`/`scoring_events` split in `webapp/scheduler.py`, the `impact` column on `event_history`). **Dependency, not duplication** — see Explicitly out of scope.

## Problem

Two real gaps, confirmed by direct code inspection (not assumed):

1. **No event registry.** Nothing in the codebase tracks the full set of recurring USD events, their cadence, or an approximate next-occurrence when no real date is retrievable yet. The engine only knows about whatever Forex Factory's live "thisweek" feed currently returns, or whatever FRED release-schedule data `macro_calendar` already covers for a small subset of titles.
2. **No influence graph.** `grep`-confirmed: `config/settings.py` has zero precursor-mapping structure. Exactly two links exist (ADP→NFP, PPI→CPI), hardcoded by whichever caller manually builds and passes a `precursor_events` list into `score_bundle()` — not a config table, no tiering, no High→High links (e.g. nothing encodes "NFP's outcome shapes how the market reads the next CPI").

## Decisions (from brainstorm)

- **Register the full event map (~55 events), regardless of impact tier or whether it's scoreable today.** Titles without an `EVENT_SURPRISE_DIRECTION` entry yet are registered but their links stay dormant (can't resolve a surprise) until that config gap is closed separately.
- **Low-impact events: tracked only, no dashboard score.** Reuses the exact split `low-impact-context-tracking` already builds — this spec does not reinvent that distinction, it depends on it (or an equivalent minimal version, see Explicitly out of scope). Medium/High continue being scored exactly as designed today.
- **Cadence stored as a numeric interval in months (float), not a coarse monthly/quarterly/annual label.** FOMC is real-world ~8 meetings/year (~1.6 months apart), not literally quarterly — a coarse label would misapproximate it. Every recurring title in the map gets its own accurate average interval.
- **Next-occurrence resolution is a fallback chain, real data always wins over the estimate:** (1) Forex Factory's live calendar snapshot, if it already lists a real upcoming occurrence of this title; (2) `macro_calendar`'s existing FRED-release-schedule data, for the subset of titles it already covers; (3) the cadence-derived approximate month (last confirmed occurrence + interval), only when neither real source has an answer. Never fabricates a specific date — the approximate-month fallback is explicitly month-level, not a guessed exact date.
- **"Last confirmed occurrence" comes from `event_history`** (already-real, resolved data) — never guessed, matching this codebase's standing "confirmed data or absent" discipline.
- **Cadence-derived estimates are internal only for now — not surfaced on the Calendar tab.** The existing `macro_calendar` mechanism already handles real date-level UI estimates for the titles it covers; this coarser month-level field is for the graph's own "is this precursor due soon" bookkeeping, not a UI change.
- **The influence graph is hand-curated config, seeded from the event map's §6 chains** — not inferred, not ML-scored. Same authoring discipline as `EVENT_SURPRISE_DIRECTION`.
- **The graph is tier-agnostic in structure** — any event can link to any other event (Low→Medium, Low→High, Medium→High, High→High all use the same structure); impact tier is metadata on the node (used only to decide dashboard-score-or-not), never a structural constraint on which links are allowed.
- **Absorb and replace the 2 existing hardcoded links.** ADP→NFP and PPI→CPI become the graph's first two entries; the old caller-side hardcoding is removed — one mechanism, not two doing the same job.
- **Scoring integration = Approach B**, chosen over a full confidence-only-modulation redesign: precursor contributions keep flowing into the weighted-average direction/probability calculation exactly as they do today (preserving the two links' proven behavior). What's added is explicit **chain-conflict detection** — when 2+ of a target event's linked, confirmed precursors disagree in direction, that's flagged (a visible note, confidence discounted), rather than silently netted into one blended number the way it currently would be. Confluence (precursors agreeing) is NOT given extra explicit weight beyond what the existing agreement×coverage math already grants it — deferred until real backtest data justifies tuning it, same as every other threshold in this codebase.

## Architecture

Three new pieces, each with a clear boundary:

### 1. Event Registry — `config/settings.py`

```python
EVENT_REGISTRY: dict[str, dict] = {
    "Non-Farm Employment Change": {"impact": "High", "avg_interval_months": 1.0},
    "ADP Nonfarm Employment Change": {"impact": "Medium", "avg_interval_months": 1.0},
    "JOLTS Job Openings": {"impact": "Medium", "avg_interval_months": 1.0},
    "Challenger Job Cuts": {"impact": "Low", "avg_interval_months": 1.0},
    "FOMC Statement": {"impact": "High", "avg_interval_months": 1.6},  # real-world ~8 meetings/year, NOT literally quarterly
    "Prelim GDP q/q": {"impact": "High", "avg_interval_months": 3.0},
    # ... full ~55-event map, ported from docs/fundamental-analysis-monthly-event-map-2026-09-02.md §1-5
}
```
Title strings must exact-match what `data_layer/calendar_feed.py`'s live FF feed actually returns — several titles in the event map doc are "best-effort standard naming, not independently verified against a live feed capture" (the same caveat already flagged for `EVENT_SURPRISE_DIRECTION`'s own recent additions). The implementer verifies each new title against the live feed (or the existing `EVENT_SURPRISE_DIRECTION`/`ACCUMULATOR_MEDIUM_ALLOWLIST` dicts, for titles already confirmed there) before adding it — this spec does not assert every title string is already correct.

New function, `data_layer/event_registry.py`:
```python
def get_approximate_next_occurrence(title: str, conn) -> Optional[dt.date]:
    """
    Fallback chain: (1) a real upcoming occurrence in the current FF
    calendar snapshot, (2) macro_calendar's FRED-derived estimate if one
    exists for this title, (3) EVENT_REGISTRY's avg_interval_months added
    to the most recent CONFIRMED event_history occurrence. Returns None
    if none of the three sources have an answer — never fabricates a
    date. Month-level precision only for case (3); cases (1)/(2) return
    whatever real precision their source already has.
    """
```

### 2. Influence Graph — `config/settings.py`

```python
EVENT_INFLUENCE_LINKS: dict[str, list[tuple[str, float]]] = {
    "Non-Farm Employment Change": [
        ("ADP Nonfarm Employment Change", 0.90),  # migrated from the old hardcoded PRECURSOR_TRUST_WEIGHT link
        ("JOLTS Job Openings", 0.40),
        ("Challenger Job Cuts", 0.35),
    ],
    "CPI m/m": [
        ("PPI m/m", 0.90),  # migrated
        ("Import Prices m/m", 0.40),
    ],
    "FOMC Statement": [
        ("Non-Farm Employment Change", 0.50),   # High→High: labor strength shapes the Fed's read
        ("CPI m/m", 0.60),                       # High→High: inflation is the Committee's primary input
        ("Core PCE Price Index m/m", 0.65),      # High→High: the Fed's own preferred gauge
    ],
    # ... remaining §6 chains (growth/output, consumer/housing) — each link's
    # trust weight is an explicitly untuned starting value, same honesty as
    # PRECURSOR_TRUST_WEIGHT always carried, calibrated later against real
    # outcome data (matches the existing SWOT's W7/R8 finding).
}
```
Weights are illustrative starting values in this spec — the implementation plan finalizes the full set, porting every real link from the event map's §6, and every link's target/precursor pair must have both titles present in `EVENT_REGISTRY` (a link to an unregistered title is a config bug, not a valid dormant link).

### 3. Scoring integration — `scoring/probability_engine.py`

**Precursor discovery, generalized.** Replaces the caller-supplied `precursor_events` list with a graph-driven lookup:
```python
def get_precursor_events_for(target_title: str, conn) -> list[EconomicEvent]:
    """
    Looks up EVENT_INFLUENCE_LINKS[target_title]. For each linked
    precursor title, fetches the most recent RESOLVED (actual IS NOT
    NULL) event_history row and converts it to an EconomicEvent. Skips
    any precursor title with no resolved occurrence yet — never
    fabricates. Replaces scoring/backtest_accumulator.py's old
    hand-wired ADP/PPI-specific lookup (the exact call site the plan
    confirms and updates) with one graph-driven mechanism covering
    every registered link.
    """
```
`score_bundle()`'s existing `precursor_events: list[EconomicEvent] | None` parameter is unchanged in shape — only how the caller populates it changes (graph lookup instead of two hardcoded fetches).

**New chain-conflict check**, alongside the fundamental-signals-batch's existing `_check_*` functions:
```python
def _check_precursor_chain_conflict(
    precursor_contributions: list[PrecursorContribution],
) -> tuple[bool, str | None]:
    """
    (True, note) if 2+ precursor contributions disagree in sign (one
    USD-bullish, one USD-bearish) — a genuine conflict within THIS
    target event's own linked-precursor chain. Distinct from
    _detect_contradiction() (article-only, recent-vs-older narrative
    shift) and from _check_macro_backdrop() (compares against an
    external dollar/rates read, not against other precursors). (False,
    None) if fewer than 2 precursor contributions, or all agree.
    """
```
Wiring in `score_bundle()`: precursor contributions still flow into `all_contributions` exactly as today (Approach B — direction/probability unaffected by this spec). Additionally: `chain_conflict, chain_conflict_note = _check_precursor_chain_conflict(precursor_contributions)`; `if chain_conflict: confidence *= PRECURSOR_CHAIN_CONFLICT_CONFIDENCE_MULTIPLIER` (new, untuned constant, same style as `MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER`). New `ProbabilityResult` fields: `chain_conflict_flag: bool = False`, `chain_conflict_note: str | None = None` — surfaced on the dashboard the same visible way `oil_shock_note` already is.

## Data Flow

```
config.settings.EVENT_REGISTRY / EVENT_INFLUENCE_LINKS   [new, static config]
  → data_layer.event_registry.get_approximate_next_occurrence()  [new,
    internal bookkeeping only — no UI change]
  → scoring.probability_engine.get_precursor_events_for(target_title, conn)
    [new — replaces backtest_accumulator.py's old ADP/PPI-specific fetch]
      → queries webapp.store.event_history for each linked precursor
        title's most recent RESOLVED row (confirmed data only)
  → scoring.probability_engine.score_bundle(..., precursor_events=[...])
      → _build_precursor_contributions()   [existing, unchanged — still
        age-decays, still requires a real resolved actual]
      → all_contributions still includes precursor_contributions
        [Approach B — direction/probability path unchanged]
      → _check_precursor_chain_conflict(precursor_contributions)  [new]
      → confidence *= PRECURSOR_CHAIN_CONFLICT_CONFIDENCE_MULTIPLIER
        when 2+ linked precursors disagree
```

## Error Handling

Same fail-open contract as every other module touched this session: a missing FF/macro_calendar/event_history answer for next-occurrence returns `None`, never a guessed date. A precursor title with no resolved `event_history` row yet is simply absent from the returned list (not a zero, not a fabricated neutral value) — `_build_precursor_contributions()` already handles an empty/partial list correctly today, no change needed there. A malformed or missing `EVENT_INFLUENCE_LINKS` entry for a title with no configured links returns an empty precursor list, same as today's default.

## Testing

- `tests/test_event_registry.py` — new file: `get_approximate_next_occurrence()`'s three-tier fallback (each source tested independently and in combination), cadence-interval math (including a non-integer interval like FOMC's 1.6 months), fail-open when no source has an answer.
- `tests/test_probability_engine.py` — extended: `get_precursor_events_for()` (graph lookup, confirmed-only fetch, skip-if-unresolved), `_check_precursor_chain_conflict()` (2-agree, 2-disagree, 3-with-one-outlier, fewer-than-2 cases), and a `score_bundle()` integration test proving the two migrated links (ADP→NFP, PPI→CPI) still produce identical results to their old hardcoded behavior — this is the single most important regression test in the whole spec, since it's the proof Approach B's "don't disturb what already works" goal actually held.
- `tests/test_backtest_accumulator.py` — extended/updated wherever the old ADP/PPI-specific fetch is replaced by the graph-driven call, following whatever pattern the fundamental-signals-batch's own COT-wiring tests just established (`cot_positioning`/`cot_positioning_fetched` once-per-cycle pattern) — the graph-driven precursor lookup should follow the same once-per-cycle-not-once-per-pair fetch discipline where applicable.

## Explicitly out of scope

- **Statistical market-moving classification (the parked `NON_MARKET_MOVING` tag).** Confirmed by the user this session: Low tier stays simply "tracked, no score" using the existing impact-tier split — not the backtested classifier, which stays parked for its own future review once a month of outcome data exists.
- **Confluence as an explicit confidence boost.** Deferred — confluence already gets implicit credit via existing agreement math; an explicit chain-level boost is a future refinement once real data justifies tuning it (matches this spec's own conflict-detection asymmetry: conflict is added because it's a genuine gap, confluence isn't because it's already partially handled).
- **Surfacing cadence estimates on the Calendar tab UI.** Internal bookkeeping only, per the brainstorm decision above.
- **Merging or duplicating `low-impact-context-tracking`'s work.** This spec depends on that branch's `impact` column / `calendar_events`/`scoring_events` split existing — the implementation plan must either sequence after that branch merges, or (if the user wants this framework built first) build against a stub/minimal equivalent explicitly flagged as temporary. This decision is for the plan-writing stage, not this spec — the design here assumes the split exists, however it gets there.
- **Rate differentials / cross-central-bank divergence (N5) and the FOMC forward-guidance delta (N2)**, per the earlier alignment review's priority list — unrelated to this spec, still their own future efforts.
- **The categorized add-symbol picker** — separate, unrelated feature, still deferred per its own earlier sequencing decision.
