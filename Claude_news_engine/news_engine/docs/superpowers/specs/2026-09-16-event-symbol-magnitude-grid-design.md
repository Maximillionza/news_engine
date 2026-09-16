# Event → Symbol Magnitude Grid — Design Spec (Phase 2)

## Context

Phase 1 (`data_layer/event_symbol_relevance.py`, shipped 2026-09-16) answers
"does this Tier 1 event genuinely reach this specific symbol" across a
9-event-type × 12-symbol grid — 94 cells resolved `RELEVANT`, 0
`NOT_RELEVANT`, 14 honestly `UNVERIFIED`. It deliberately stopped at
relevance; it says nothing about *how much* a relevant event typically
moves a given symbol.

This spec is Phase 2: a magnitude tier for each of the 94 `RELEVANT`
cells. Phase 3 (wiring any of this into live scoring, the dashboard, or
the scheduled task) remains explicitly out of scope — confirmed with the
user this session ("let's wait").

## Why not a single precise number

Phase 1's own citations already show why a single number per cell would
misrepresent reality: NFP alone produced real, cited moves ranging from
roughly 85 pips on USDJPY to a 907-point Dow session depending on the
specific occurrence. A fixed "NFP moves USDJPY by exactly N pips" number
would be fabricating a precision the real world doesn't have. A **tier**
— Low / Medium / High, each with real supporting citations — represents
what's actually knowable: a typical range, not a false-precision average.

## Why not a continuously-recomputed score

Same reasoning the user already settled during Phase 1's brainstorm,
carried forward unchanged: magnitude, like relevance, is a property of
an event *type* reacting with a *symbol*, not something that needs
recomputing day to day. A CPI-on-EURUSD magnitude tier doesn't need to
be "refreshed" every morning the way a live multi-factor score would —
it's the same kind of static, hand-curated, cited answer Phase 1 already
produced, one layer deeper.

## Scope

**Only the 94 cells Phase 1 already resolved `RELEVANT`.** The 14
`UNVERIFIED` relevance cells are out of scope until their own relevance
is resolved first — magnitude is meaningless to research for a cell
that doesn't yet have a confirmed "yes" on relevance. `NOT_RELEVANT` is
currently empty (0 cells) and stays out of scope for the same reason.

## Data model

New file: `data_layer/event_symbol_magnitude.py`. Deliberately a
**separate module from `event_symbol_relevance.py`**, not an edit to
it — Phase 1's 108 entries already went through real review (including
two real fix rounds) and a final whole-plan review; keeping magnitude in
its own file means none of that already-verified content is touched or
put at risk by Phase 2's own edits.

```python
from dataclasses import dataclass
from enum import Enum


class MagnitudeTier(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNVERIFIED = "unverified"  # relevance is confirmed real (Phase 1's
                                 # RELEVANT), but no real evidence pins
                                 # down a typical magnitude -- honest,
                                 # not a guess, same three-state
                                 # discipline Phase 1 already proved out


@dataclass(frozen=True)
class MagnitudeJudgment:
    tier: MagnitudeTier
    citation: str  # required, non-empty for every tier -- for
                    # LOW/MEDIUM/HIGH, the real occurrence(s) that
                    # justify the tier; for UNVERIFIED, an honest note
                    # on what wasn't found


# Keyed EXACTLY like event_symbol_relevance.py's _RELEVANCE_TABLE --
# (event_type, symbol) -- but populated only for cells where
# event_symbol_relevance.get_relevance(event_type, symbol).status is
# RELEVANT. All 94 such keys are present explicitly by the time this
# table is complete -- same exhaustive-for-its-scope discipline Phase 1
# used, scoped to Phase 1's own RELEVANT subset rather than the full 108.
_MAGNITUDE_TABLE: dict[tuple[str, str], MagnitudeJudgment] = {}


def get_magnitude(event_type: str, symbol: str) -> MagnitudeJudgment:
    """
    Returns the real, sourced magnitude tier for (event_type, symbol).
    Raises KeyError for any pair not in this table -- including a pair
    that's a real Phase 1 key but was NOT_RELEVANT or UNVERIFIED there
    (magnitude is only ever researched for a confirmed-RELEVANT pair).
    Never fabricates a tier for a pair it doesn't recognize.
    """
    return _MAGNITUDE_TABLE[(event_type, symbol)]
```

## Tier definitions — the ruler, not a source of truth

`[Guessing, flagged explicitly]` A uniform percentage-of-typical-move
band across all three instrument shapes (FX pairs, metals, indices),
since expressing everything in the same unit (% move) is what makes a
Low/Medium/High tier comparable across a currency pair, gold, and an
equity index at all:

- **LOW**: a typical real occurrence moves the symbol under ~0.3%
- **MEDIUM**: a typical real occurrence moves the symbol roughly
  0.3%–0.8%
- **HIGH**: a typical real occurrence moves the symbol over ~0.8%

These bands are a reasoned starting ruler (general market-convention
reasoning about typical FX/metals/index daily volatility), not
independently re-derived from this project's own historical data before
population begins — flagging that honestly rather than presenting them
as more rigorously sourced than they are. Population tasks should
sanity-check emerging classifications against this project's own
`scoring/backtest_log.db` `outcomes` table (many real move-size
percentages are already logged there and in Phase 1's own citations) and
flag to the controller if the bands themselves look wrong for a specific
instrument class once real data is in hand — this is exactly the kind of
plan-vs-evidence conflict a running SDD execution is expected to rule on
itself, not stall over.

Each individual cell's tier assignment still requires its own real,
cited evidence for that specific (event, symbol) pair's typical move —
the bands above are only the measuring stick applied to that evidence,
never a substitute for it.

## Population — real research, same discipline as Phase 1

For each of the 94 `RELEVANT` cells: start from Phase 1's own citation
for that cell (many already contain a real, quantified move size —
e.g. "+0.34%", "USD/JPY -85 pips", "S&P 500 -0.51%" — directly reusable
as Phase 2 evidence with no new research needed). Where Phase 1's
citation is qualitative only (a real event confirmed relevant, but no
number was needed for that phase), do real, fresh research the same way
— `scoring/backtest_log.db`'s `outcomes` table first (exact, timestamped,
real historical moves), then real WebSearch for the rest, applying the
same hard-won lesson from Phase 1's ISM Manufacturing PMI task: prefer
this project's own internal outcome data over an external news article's
causal-attribution claim on a multi-driver trading day, and
independently re-verify any external citation's date/numbers/narrative
before trusting it. A cell with no real, citable magnitude evidence
after this process is `UNVERIFIED`, not a guess.

Given the volume (94 cells), population should be sequenced as its own
set of real research tasks in the implementation plan, grouped by event
type (mirroring Phase 1's own task breakdown) rather than one
undifferentiated step.

## Output — a real reference document, same pattern as Phase 1

`docs/event-symbol-magnitude.md`, generated FROM the Python table by a
small script (`scripts/generate_event_symbol_magnitude_doc.py`), never
hand-duplicated — with a drift-guard test asserting the generator's live
output matches the committed file byte-for-byte, the same fix Phase 1's
final review added after finding this gap in Phase 1's own first pass.

## Testing

- `get_magnitude()` raises `KeyError` for any pair not in the table,
  including a real Phase 1 pair that isn't `RELEVANT` there.
- Every one of the 94 real `RELEVANT` `(event_type, symbol)` pairs from
  Phase 1 is present in `_MAGNITUDE_TABLE` — a completeness test scoped
  to Phase 1's own `RELEVANT` subset (not the full 108), and asserting
  `len(_MAGNITUDE_TABLE) == 94` exactly, so a stray/typo'd key is
  caught the same way Phase 1's own final-review fix caught that gap.
- The completeness test also asserts no key exists in `_MAGNITUDE_TABLE`
  that is NOT `RELEVANT` in Phase 1's table — enforcing the scope
  boundary structurally, not just by convention.
- The markdown generator's drift-guard test (byte-for-byte match against
  the committed file), same pattern as Phase 1's final-review fix.

## Non-goals (explicitly out of scope for this spec)

- **Live wiring** into `predictions_service.py`, the dashboard, or the
  `tier1-cpi-ppi-autoresearch` scheduled task — Phase 3, deferred by
  explicit user decision this session ("let's wait"), same as Phase 1.
- **Resolving Phase 1's 14 `UNVERIFIED` relevance cells.** Those stay
  `UNVERIFIED` in Phase 1's own table; Phase 2 does not attempt to
  research their relevance as a side effect of researching magnitude
  elsewhere.
- **Any change to `data_layer/event_symbol_relevance.py`.** Phase 2 only
  ever reads from it (via `get_relevance()`), never edits it.
- **A numeric/continuous magnitude value.** The tier system above is the
  whole of Phase 2's output shape — no percentage-range field, no
  computed statistic, per the "why not a single precise number"
  reasoning above.
