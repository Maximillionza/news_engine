# Event → Symbol Relevance Grid — Design Spec

## Context

The engine currently scores every tracked Tier 1 economic event for every
tracked symbol using one mechanical rule: `webapp/symbols.py`'s
`classify_symbol()` derives a `usd_relationship` ("inverse" / "direct" /
"risk_sentiment") from a ticker's shape, and that decides *which direction*
a USD-bullish surprise pushes a given symbol. It does not decide *whether*
a given event is actually worth trading for that symbol at all — every
USD-legged symbol is treated as reachable by every USD-moving event, with
no distinction between "this event is a primary driver for this symbol"
and "this event technically touches this symbol but rarely moves it in
any meaningful way."

Two real, related pieces already exist and this design builds on both
rather than starting fresh:

- `data_layer/exposure.py` — a hand-curated, cited `_NOT_EXPOSED` table
  answering "is a *classified ad hoc shock* (OPEC+ decision, Fed
  transition, etc.) actually exposed to this *symbol class*" — keyed by
  `(taxonomy_category, symbol_class)`, class-grain, and scoped to Tier 2/3
  exogenous shocks only, not the 9 regular scheduled Tier 1 events.
- The "PER-INSTRUMENT QUIRKS" section added to the
  `tier1-cpi-ppi-autoresearch` scheduled task's prompt (2026-09-13) —
  real, sourced prose describing how individual symbols within the same
  mechanical class react differently (gold's broken inverse-to-real-yields
  rule, silver's independent industrial-demand driver, JPY's carry-trade
  layer, CHF's safe-haven overshoot, CAD's oil linkage, AUD/NZD's
  commodity linkage, US30's cut-framing ambiguity). This is real content,
  but it lives as free text inside a prompt a research step reads by
  hand each run — it isn't a structured, queryable table, and it doesn't
  cover the "does this event reach this symbol AT ALL" question directly,
  only "how does this symbol's reaction differ once it's already assumed
  relevant."

## Goal

Build a static, hand-curated, individual-symbol-grain reference table
answering, for each of the engine's 9 regular Tier 1 event types crossed
with each of the 12 symbols the dashboard's "+ Add symbol" picker already
knows about: **is this event genuinely relevant to this specific symbol**
— Relevant, Not relevant, or honestly Unverified where no real evidence
exists yet. This is phase 1 of a two-phase plan; phase 2 (how *much* a
relevant event moves a given symbol — magnitude/weighting) and phase 3
(wiring this table into the live scoring/dashboard) are both explicitly
out of scope here — see Non-goals.

## A real expectation to set before this is built

Because `classify_symbol()`'s `usd_relationship` mapping already
mechanically connects every USD-legged symbol to every USD-moving event,
there is currently no known real evidence of a *regular scheduled*
release (as opposed to an ad hoc shock like OPEC+) having zero reach to a
tracked symbol. The one real "not exposed" case found this session
(OPEC+ / metal, OPEC+ / index_risk) is a Tier 2/3 *ad hoc shock* case, not
one of the 9 scheduled event types this grid covers. This design does not
assume the grid will come back full of "Not relevant" cells — it may well
resolve mostly to "Relevant," with the real differentiation between
symbols showing up in phase 2's magnitude work rather than here. The
grid's real value in phase 1 is establishing, per cell, an honest,
sourced answer (including "Unverified" where that's the truth) rather
than the system's current implicit, unexamined assumption that
relevance is automatic.

## Scope

**Rows — 9 event types**, one per existing Tier 1 methodology (not 14
raw calendar titles; several methodologies already cover more than one
exact title, and relevance is a property of the underlying economic
event, not each title variant):

1. CPI m/m (`POC_CPI_Leading_Indicators`)
2. PPI m/m (`POC_PPI_Leading_Indicators`)
3. Non-Farm Employment Change (`POC_NFP_Leading_Indicators`)
4. FOMC rate decision — covers "FOMC Meeting Minutes", "FOMC Statement",
   "Federal Funds Rate" (`POC_FOMC_Rate_Decision`)
5. GDP q/q — covers "Prelim GDP q/q", "Advance GDP q/q", "GDP q/q"
   (`POC_GDP_Nowcast`)
6. Core PCE Price Index m/m (`POC_Core_PCE`)
7. ISM Manufacturing PMI (`POC_ISM_Manufacturing_PMI`)
8. ISM Services PMI (`POC_ISM_Services_PMI`)
9. Retail Sales m/m — covers "Retail Sales m/m", "Core Retail Sales m/m"
   (`POC_Retail_Sales`)

**Columns — the 12 symbols** the "+ Add symbol" picker
(`webapp/static/js/dashboard/symbol-picker.js`) already defines:

- Metals: XAUUSD, XAGUSD
- Indices: US30, US500, NAS100
- FX majors: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD

9 × 12 = **108 cells**, every one present explicitly (not a sparse
exceptions-only table like `exposure.py`'s — see Data model below for
why).

## Data model

New file: `data_layer/event_symbol_relevance.py`. Same hand-curated,
cited-constant discipline as `exposure.py` — a real Python structure,
never a database table or a live fetch, extended by hand as real evidence
is found.

```python
from dataclasses import dataclass
from enum import Enum


class RelevanceStatus(Enum):
    RELEVANT = "relevant"          # real, sourced evidence this event reaches this symbol
    NOT_RELEVANT = "not_relevant"  # real, sourced evidence this event does NOT meaningfully reach this symbol
    UNVERIFIED = "unverified"      # no real evidence checked yet -- honest, not a guess


@dataclass(frozen=True)
class RelevanceJudgment:
    status: RelevanceStatus
    citation: str  # required for RELEVANT/NOT_RELEVANT; a short honest
                    # note (e.g. "not yet researched") for UNVERIFIED


# Every one of the 9 event types x 12 symbols = 108 keys present
# explicitly -- deliberately NOT a sparse "only exceptions get an entry"
# table like exposure.py's _NOT_EXPOSED. A sparse table would make a
# never-checked cell indistinguishable from a confirmed one; an
# exhaustive table keeps "nobody has looked at this yet" honestly visible
# instead of silently defaulting to looking resolved.
_RELEVANCE_TABLE: dict[tuple[str, str], RelevanceJudgment] = {
    # Populated per-cell during implementation with real citations.
    # Placeholder example shape (not real data):
    # ("CPI m/m", "XAUUSD"): RelevanceJudgment(
    #     RelevanceStatus.RELEVANT,
    #     "Layer1_Event_to_USD 2026-03-CPI / 2025-07-CPI rows -- direct,
    #      repeatedly confirmed gold reaction to CPI surprises",
    # ),
}


def get_relevance(event_type: str, symbol: str) -> RelevanceJudgment:
    """
    Returns the real, sourced judgment for (event_type, symbol) if one
    exists in the table. Raises KeyError for a genuinely unknown
    (event_type, symbol) pair outside the 9x12 scope -- this function
    never fabricates a judgment for a pair it doesn't recognize; an
    unrecognized pair is a caller bug (a symbol added but never added to
    _RELEVANCE_TABLE alongside webapp/symbols.py's own METALS/INDICES
    sets and the FX-majors list -- same "extend this alongside that"
    convention data_layer/dukascopy_feed.py's _INSTRUMENT_MAP comment
    already uses), not a data-availability case to swallow into a
    default.
    """
    return _RELEVANCE_TABLE[(event_type, symbol)]


def treat_as_relevant(judgment: RelevanceJudgment) -> bool:
    """
    The real yes/no answer a future caller (phase 3, not built here)
    would act on: RELEVANT -> True, NOT_RELEVANT -> False, UNVERIFIED ->
    True (per explicit product decision: an unverified cell defaults to
    "assume relevant" so nothing gets silently suppressed before it's
    actually been checked -- but callers displaying this to a person
    must still show judgment.status separately, never collapse UNVERIFIED
    into a plain "yes" with no distinguishing label).
    """
    return judgment.status != RelevanceStatus.NOT_RELEVANT
```

## Population — real research, not fabrication

Same sourcing discipline as every other table in this project:

1. **Start from what's already sourced.** The Tier 1 prompt's
   "PER-INSTRUMENT QUIRKS" prose and the `Layer1_Event_to_USD` /
   `Layer2_Asset_Transmission` workbook sheets already contain real,
   cited evidence for a meaningful subset of cells (e.g., CPI's real,
   repeated documented effect on gold; the OPEC+/Iran-war rows'
   confirmation that an oil-driven CPI surprise reaches gold and USD).
   These seed real `RELEVANT` entries with citations pointing at their
   existing source rows — not re-researched from scratch.
2. **Real research for the rest**, per (event type, symbol) pair, via
   WebSearch and the same primary-source standard every POC sheet and
   the exposure table already hold themselves to. A cell resolves to
   `NOT_RELEVANT` only on real, sourced evidence of genuine non-reach —
   given the expectation set above, that may be rare or absent among
   these 108 cells, and that is a legitimate real finding, not a failure
   to find something that was never there.
3. **Anything that can't be resolved with real evidence in a reasonable
   research pass stays `UNVERIFIED`**, with a short honest note (e.g.
   "no primary-source coverage of Philly Fed-style regional surveys
   found for AUDUSD specifically") rather than a forced guess. A grid
   that is honestly 40% `UNVERIFIED` on day one is a correct, useful
   artifact; a grid that is 100% confidently filled by guessing is not.

Given the volume (108 cells), this is a real implementation task, likely
run subagent-driven given its size — the plan should size and sequence
that research explicitly rather than leaving "populate the table" as one
undifferentiated step.

## Output — a real reference document, not just code

The user explicitly wants something to open and read, not only a Python
import. Alongside `data_layer/event_symbol_relevance.py`, generate a
human-readable rendition of the full 9x12 grid — a markdown table (e.g.
`docs/event-symbol-relevance.md`) with each cell showing its status
(✓ Relevant / ✕ Not relevant / ? Unverified) and, on hover or in an
adjacent column, its citation — built FROM `_RELEVANCE_TABLE` (a small
generator script, not hand-duplicated content, so the two never drift
out of sync). Whether this document is also worth publishing as a
browsable Artifact (matching "The Causation Matrix" walkthrough already
published this session) is a presentation choice to make once the real
content exists, not part of this spec's data-model decisions.

## Testing

- `get_relevance()` raises `KeyError` for a genuinely unrecognized
  `(event_type, symbol)` pair (never fabricates a judgment for a pair
  outside the defined 9x12 scope).
- Every one of the 108 real `(event_type, symbol)` combinations is
  present in `_RELEVANCE_TABLE` — a table-completeness test that fails
  loudly if a cell is ever missing, rather than silently falling back to
  a KeyError at call time.
- `treat_as_relevant()`: `RELEVANT` → `True`, `NOT_RELEVANT` → `False`,
  `UNVERIFIED` → `True` (the explicit default decision above).
- The markdown-generator script's output round-trips real table content
  correctly (a cell's status and citation both appear, nothing silently
  dropped) — verified against a small real slice of the table, not the
  full 108 cells.

## Non-goals (explicitly out of scope for this spec)

- **Magnitude/weighting** ("how much" a relevant event moves a symbol) —
  phase 2, a separate future design.
- **Live wiring** into `predictions_service.py`, the dashboard, or the
  `tier1-cpi-ppi-autoresearch` scheduled task's actual behavior — phase
  3, deferred by explicit user decision ("we can plug it in once
  magnitude is built"). This spec produces a reference table only; no
  prediction, confidence, or direction anywhere in the live system
  changes as a result of this work.
- **Symbols beyond the 12 already in the picker.** A 13th symbol added to
  `symbol-picker.js` in the future would need its own row-set added here
  by hand, same "extend alongside" convention already used elsewhere in
  this codebase — not addressed by this spec.
- **Any change to `webapp/symbols.py`'s `classify_symbol()` or its
  `usd_relationship` mapping.** That mechanism is unaffected; this grid
  sits alongside it, answering a different question ("is this worth
  trading" vs. "which direction").
