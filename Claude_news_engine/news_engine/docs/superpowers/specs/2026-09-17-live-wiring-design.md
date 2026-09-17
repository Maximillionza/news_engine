# Event → Symbol Relevance/Magnitude Live Wiring — Design Spec (Phase 3)

## Context

Phase 1 (`data_layer/event_symbol_relevance.py`, shipped 2026-09-16) and
Phase 2 (`data_layer/event_symbol_magnitude.py`, shipped 2026-09-16) built
two static, hand-cited reference tables — relevance (108 cells: 94
`RELEVANT`, 0 `NOT_RELEVANT`, 14 `UNVERIFIED`) and magnitude (94 cells
scoped to the `RELEVANT` subset: 34 `MEDIUM`, 29 `LOW`, 22 `HIGH`, 9
`UNVERIFIED`). Both were built explicitly as reference-only deliverables;
neither has ever touched `predictions_service.py`, the dashboard, or the
`tier1-cpi-ppi-autoresearch` scheduled task. This spec is Phase 3: wiring
both tables into the live system for the first time.

The motivating case, stated by the user at the very start of this
three-phase project, is not dashboard decoration: "the event is not
traded when it has a low probability of moving that particular symbol in
any meaningful way." Phase 3's design centers this — helping identify
low-value trades to avoid — rather than defaulting to "add a badge
somewhere" without asking what changes for a real trading decision.

## Existing precedent this phase reuses

`webapp/predictions_service.py` already computes `tier1_confidence_downgrade`
live, today driven only by Tier 2/3 exogenous shocks via
`_get_todays_exogenous_shocks()` / `_first_exposing_shock()`
(`data_layer/exposure.py`). That mechanism: applies exactly one
confidence-tier downgrade, never compounds past one tier, never touches
`predicted_direction`. Rendered on the dashboard via
`webapp/static/js/dashboard/card.js`'s `tier1ConfidenceDowngradeTemplate()`
/ `otherEventTier1DowngradeMarkerTemplate()`. Phase 3 extends this same
mechanism with a second real trigger rather than inventing a new one.

## The title-to-methodology-label mapping gap

Both reference tables key on the 9 Tier 1 **methodology** labels (e.g.
`"FOMC Rate Decision"`, `"GDP q/q"`, `"Retail Sales m/m"`), while the live
system (the scheduled task's Step 1, and anything matching real calendar
event titles) uses 14 exact **calendar titles**. A live event title must be
resolved to its methodology-label row key before either table can be
consulted. This mapping mirrors the exact grouping already documented in
both prior specs' Global Constraints sections:

```python
# data_layer/event_title_mapping.py

EVENT_TITLE_TO_METHODOLOGY: dict[str, str] = {
    "FOMC Meeting Minutes": "FOMC Rate Decision",
    "FOMC Statement": "FOMC Rate Decision",
    "Federal Funds Rate": "FOMC Rate Decision",
    "Prelim GDP q/q": "GDP q/q",
    "Advance GDP q/q": "GDP q/q",
    "GDP q/q": "GDP q/q",
    "Retail Sales m/m": "Retail Sales m/m",
    "Core Retail Sales m/m": "Retail Sales m/m",
    "CPI m/m": "CPI m/m",
    "PPI m/m": "PPI m/m",
    "Non-Farm Employment Change": "Non-Farm Employment Change",
    "Core PCE Price Index m/m": "Core PCE Price Index m/m",
    "ISM Manufacturing PMI": "ISM Manufacturing PMI",
    "ISM Services PMI": "ISM Services PMI",
}


def resolve_methodology_label(calendar_title: str) -> str | None:
    """
    Returns the methodology label a live calendar title maps to, or None
    if the title isn't one of the 14 mapped Tier 1 titles. Never guesses
    a mapping for an unrecognized title.
    """
    return EVENT_TITLE_TO_METHODOLOGY.get(calendar_title)
```

Any calendar title not in this table is simply not looked up — same as
today's behavior, no downgrade, no label.

## Confidence-side wiring

Extend `predictions_service.py`'s downgrade computation with a second
trigger, alongside the existing exogenous-shock trigger. For a tracked
symbol's event: resolve the calendar title to its methodology label via
`resolve_methodology_label()`; if resolved, look up
`get_relevance(methodology_label, symbol)` and, only if relevance is
`RELEVANT`, `get_magnitude(methodology_label, symbol)`.

- A `NOT_RELEVANT` relevance judgment earns one confidence-tier downgrade.
- A `LOW` magnitude judgment (only reachable when relevance is
  `RELEVANT`) earns one confidence-tier downgrade.
- `UNVERIFIED` relevance and `UNVERIFIED` magnitude are both neutral —
  no downgrade. Unresearched is not evidence of unimportant, matching
  the philosophy both tables already apply internally
  (`treat_as_relevant()` defaults `UNVERIFIED` → `True`).
- This new trigger and the existing exogenous-shock trigger share the
  same one-tier floor and never-compound-past-one-tier rule already
  enforced by `_downgrade_one_tier()` — whichever trigger(s) fire, the
  result is never more than one tier down.
- A resolved methodology label whose `(methodology_label, symbol)` pair
  is not a key in `_RELEVANCE_TABLE` at all (`get_relevance()` raises
  `KeyError`) is treated identically to `UNVERIFIED` — neutral, no
  downgrade, no badge. This is a real, expected case: a tracked symbol
  paired with a mapped event type that simply isn't one of the 108 keyed
  pairs. The lookup wrapper catches `KeyError` and returns a neutral
  result rather than letting it propagate — this is a normal, anticipated
  input, not a bug to raise on.
- `predicted_direction` is never touched by this or any path in this
  system, unconditionally.
- A calendar title with no mapping, or an untracked symbol, is not
  looked up at all — unchanged from today's behavior.

## Label-side wiring

A new badge, separate from (and additional to) the existing
`tier1_confidence_downgrade` badge, rendered wherever that badge already
appears (dashboard card, sibling rows, History) using the same
warning-badge visual language already established for shocks and
conflicts (the orange "needs attention" style). Real, honest text per
state:

- `NOT_RELEVANT` relevance → "Not confirmed relevant to this symbol"
- `LOW` magnitude → "Low expected impact"
- `UNVERIFIED` (either table) → "Relevance/magnitude not yet researched"
  — visibly distinct from a confident finding, never silently suppressed
- `RELEVANT` + `MEDIUM`/`HIGH` magnitude, no mapping, or an unkeyed
  `(methodology_label, symbol)` pair (`KeyError` from either table) →
  no badge, unchanged from today

The label and the confidence downgrade are computed from the same lookup
but rendered independently — a `NOT_RELEVANT` or `LOW` result always
shows both the downgrade (confidence side) and the plain-language badge
(label side); an `UNVERIFIED` result shows only the badge, never a
downgrade.

## Scope

Only the 12 symbols and 9 event types (14 mapped calendar titles) both
tables actually cover. Anything else — an untracked symbol, an
unmapped calendar title, an event type outside the 9 — is not looked up:
no downgrade, no badge, behavior identical to today.

## Testing

- `resolve_methodology_label()`: all 14 real mapped titles resolve to
  their correct methodology label; an unmapped title returns `None`.
- Confidence-side: a real `NOT_RELEVANT` case downgrades one tier (none
  currently exist in Phase 1's table — test constructs a synthetic
  `NOT_RELEVANT` fixture entry, not a real table mutation); a real `LOW`
  magnitude case downgrades one tier; a real `UNVERIFIED` case (either
  table) applies no downgrade; a case already downgraded by an exogenous
  shock is not compounded further by this new trigger firing too.
- Label-side: each of the four real states renders its correct badge
  text; a `RELEVANT`/`MEDIUM` or `RELEVANT`/`HIGH` case renders no badge.
- Scope: an untracked symbol or unmapped title triggers neither downgrade
  nor badge; a mapped title + tracked symbol whose pair is absent from
  the relevance table (`KeyError`) also triggers neither, same as
  `UNVERIFIED`.
- `predicted_direction` is asserted unchanged across every new test case.

## Non-goals (explicitly out of scope for this spec)

- **Any change to `data_layer/event_symbol_relevance.py` or
  `event_symbol_magnitude.py`.** Phase 3 only ever reads from both via
  their existing `get_relevance()` / `get_magnitude()` functions.
- **Resolving any `UNVERIFIED` cell in either table.** Both stay exactly
  as shipped; Phase 3 does not research relevance or magnitude as a side
  effect of wiring.
- **A continuously-recomputed score.** This remains a discrete,
  event-triggered read at the moment an event fires — not a standing
  daily-updating score, per the user's explicit rejection of that model
  during Phase 1's brainstorm.
- **Touching `predicted_direction`** via any code path introduced here.
- **Extending the scheduled task's live research prompt.** This spec
  wires the two existing static tables into the confidence/label
  pipeline; it does not change what the `tier1-cpi-ppi-autoresearch` task
  itself researches or writes.
