# Instrument-Selective Exogenous Confidence Downgrade — Design Spec

**Date:** 2026-09-12
**Status:** Approved (brainstorming session, same day)

## Problem

Batch 6 (`docs/superpowers/specs/2026-09-11-tier2-tier3-exogenous-context-design.md`)
shipped exogenous-shock detection and a confidence-only downgrade: when
any of `DETECTOR_SERIES` (DXY, UST_BOND, XAUUSD, US30) shows an
unexplained real move, **every** tracked instrument's Tier 1 rows get a
uniform one-tier confidence downgrade, regardless of what actually caused
the shock or whether that cause's documented transmission mechanism has
anything to do with a given instrument.

This project's own workbook (`docs/News_Engine_Causation_Matrix_v2.xlsx`)
already contains two sheets built for exactly this gap:

- **`Layer1_Event_to_USD`** (18 rows) — real, dated, sourced exogenous
  events with their quantified USD/rate/yield effect (Treasury buyback
  cap changes, Fed-succession turmoil, OPEC+ supply decisions, the
  2026-02 Iran-war oil shock, government shutdowns, tariff truces).
- **`Layer2_Asset_Transmission`** (15 rows) — per-instrument-class
  transmission mechanisms, several explicitly correcting textbook
  assumptions with real evidence (gold's broken inverse-real-yield
  relationship since 2024; silver's non-stable monthly beta to gold
  despite tracking it annually; Bitcoin's regime-switching, not stable,
  Nasdaq correlation; USDCAD's independent oil-price channel).

Both sheets are documented-only — zero code consumes them. This spec
wires them in, narrowly: making the existing confidence downgrade
**instrument-selective** instead of blanket, using real, cited evidence
from these two sheets. It does not touch `predicted_direction`, and does
not add a new live-fetch dependency — this is a refinement of Batch 6's
existing mechanism, not a new subsystem.

## Goals

1. A detected shock's category (already computed by Batch 6's scheduled
   research step and stored in `exogenous_shocks.taxonomy_category`)
   determines which tracked instruments' confidence actually gets
   downgraded, instead of downgrading every tracked instrument uniformly.
2. The category→instrument-exposure judgment is hand-curated from real,
   cited Layer1/Layer2 rows — never invented, never automated from a raw
   evidence count — and confidence-gated the same way this project
   already gates `POC_Sub_Event_Consolidation` (a `Guessing`-confidence
   judgment is documented but never acted on at runtime).
3. Generalize cleanly to a future tracked symbol beyond XAUUSD/US30 —
   the exposure table is keyed by `symbol_class` (already computed by
   `webapp/symbols.py`'s `classify_symbol()`), not by hardcoded ticker.

## Non-goals

- `predicted_direction` stays manual-only, never formula-derived. This
  spec is confidence-only, exactly like Batch 6.
- No live-fetch integration for Layer1/Layer2 data — the exposure table
  is a static, versioned, hand-reviewed Python constant, not a database
  table or an API call.
- No change to detection (`data_layer/discovery_detector.py`), persistence
  (`exogenous_shocks` table), or the scheduled research trigger — all of
  Batch 6's existing mechanics are reused as-is.
- No change to the one-tier-downgrade-floor rule or the
  never-compounds-past-one-tier rule from Batch 6 — both carry over
  unchanged, just applied per-instrument instead of universally.
- Layer2's 13 documented instrument classes beyond what's actually
  tracked live (FX majors, silver, Bitcoin, oil, the 2s10s curve) are not
  wired into anything — real, useful reference data, but nothing live
  consumes them today. The exposure table only needs entries for
  `symbol_class` values `classify_symbol()` can actually produce for a
  currently-tracked or plausible-future-tracked symbol.

## Architecture

### The exposure lookup

```python
# data_layer/exposure.py

def is_exposed(taxonomy_category: Optional[str], symbol_class: str) -> bool:
    """
    True unless a real, cited, Certain-or-Likely-confidence entry in
    _NOT_EXPOSED says otherwise. Default True in every other case:
    - taxonomy_category is None (an unclassified real shock) -- zero
      curated basis to narrow anything, stays blanket per Batch 6.
    - the (category, symbol_class) pair has no entry at all -- absence
      of evidence is not evidence of non-exposure.
    - the pair HAS an entry, but its confidence is "Guessing" -- documented
      for the record, never acted on at runtime (same discipline already
      applied to POC_Sub_Event_Consolidation elsewhere in this project).
    This function can only ever narrow Batch 6's blanket-downgrade
    behavior, never widen or suppress it beyond what's positively cited.
    """
```

### The exposure table

A hand-curated dict, not a database table — a documented judgment call
reviewed by a person, versioned in git, same treatment
`_VALID_TAXONOMY_CATEGORIES` already gets in `scoring/backtest_store.py`.

```python
@dataclass(frozen=True)
class ExposureJudgment:
    exposed: bool
    confidence: str          # "Certain" | "Likely" | "Guessing" -- same 3-tier language as Tier1Prediction
    citation: str            # the real Layer1/Layer2 row(s) this judgment is built from

# Keyed by (taxonomy_category, symbol_class). symbol_class values are
# whatever webapp/symbols.py's classify_symbol() can produce: "metal",
# "index_risk", "fx_usd_base", "fx_usd_quote", "fx_cross" today, plus
# whatever new class a future tracked symbol adds (e.g. "crypto" if
# Bitcoin is ever tracked).
_NOT_EXPOSED: dict[tuple[str, str], ExposureJudgment] = {
    # Populated during implementation from a full, deliberate read of all
    # 18 Layer1 rows and all 15 Layer2 rows -- every entry cites its
    # source row(s) directly in this table, no entry without a citation.
    # Only Certain/Likely entries are ever honored by is_exposed(); a
    # Guessing entry stays documented but inert until real evidence
    # upgrades its confidence.
}
```

`taxonomy_category` values are exactly `_VALID_TAXONOMY_CATEGORIES`'s 8
strings from `scoring/backtest_store.py` (Treasury buyback, US
sovereign credit-rating action, government shutdown, Fed-independence
shock, Fed Chair transition, tariff/trade policy action, OPEC+ supply
decision, geopolitical war-driven oil supply shock) — no new categories
introduced by this spec.

### Data flow: from "first shock found" to "all of today's shocks, per instrument"

Batch 6's `webapp/predictions_service.py::_get_todays_exogenous_shock()`
returns the *first* unresolved shock found across `DETECTOR_SERIES`, and
that one shock's category/series gets shown to every instrument
uniformly. Once exposure is instrument-selective, "first found" becomes
a real bug: a second same-day shock in an exposing category could be
silently shadowed by an earlier, non-exposing shock checked first.

Fix — gather every real shock today (still small, at most 4, one per
detector series), then per instrument, find the first one it's actually
exposed to:

```python
def _get_todays_exogenous_shocks(backtest_conn) -> list[ExogenousShockRow]:
    """
    Same fail-open discipline as Batch 6's _get_todays_exogenous_shock()
    (try/except around the whole lookup, log-and-continue on failure),
    AND the same both-today-and-yesterday date check Batch 6's own final
    review already fixed (the scheduled writer logs a shock under
    YESTERDAY's date; checking only today would silently regress that
    fix). Returns every real unresolved shock found across BOTH dates and
    all of DETECTOR_SERIES, not just the first, so per-instrument
    exposure checking (below) never has a real exposing shock shadowed by
    an earlier non-exposing one.
    """

def _first_exposing_shock(
    shocks: list[ExogenousShockRow], symbol_class: str,
) -> Optional[ExogenousShockRow]:
    """
    The first shock in `shocks` this symbol_class is exposed to (per
    is_exposed()), or None if today's real shocks exist but none of
    them expose this instrument class. "First" is a display-stability
    choice only -- the one-tier-never-compounds rule (below) means which
    specific exposing shock gets shown is not load-bearing.
    """
```

`predictions_service.py`'s per-event downgrade computation replaces its
current `if tier1_prediction is not None and todays_shock is not None:`
check with a per-instrument one:

```python
todays_shocks = _get_todays_exogenous_shocks(backtest_conn)  # once per request, same as today
...
symbol_class = classify_symbol(ticker).symbol_class
exposing_shock = _first_exposing_shock(todays_shocks, symbol_class)
tier1_confidence_downgrade = None
if tier1_prediction is not None and exposing_shock is not None and event["actual"] is None:
    tier1_confidence_downgrade = {
        "original_confidence": tier1_prediction["confidence"],
        "displayed_confidence": _downgrade_one_tier(tier1_prediction["confidence"]),
        "reason": exposing_shock.headline_cause,
        "series": exposing_shock.series,
    }
```

The `_downgrade_one_tier()` function, the one-tier floor, the
never-compounds-past-one-tier behavior, and the not-yet-resolved-event
gate (`event["actual"] is None`) are all unchanged from Batch 6.

## Testing

Same three-tier discipline this project already uses for pure logic:

1. **`is_exposed()` and the exposure table** — real unit tests: a `None`
   category always returns `True`; an unlisted `(category, symbol_class)`
   pair defaults `True`; a real `Guessing`-confidence entry is documented
   but does NOT suppress exposure at runtime; a real `Certain`/`Likely`
   entry correctly returns `False`.
2. **`_first_exposing_shock()`** — unit tests with synthetic shock lists:
   correctly skips a non-exposing shock to find an exposing one later in
   the list; returns `None` when nothing in the list exposes the given
   class; returns the first exposing match when multiple shocks would
   expose the same instrument.
3. **Integration** — extend the existing downgrade tests in
   `tests/test_webapp_app.py` with a case using one REAL, cited exposure
   table entry: a real shock exists, but the specific instrument is not
   exposed to it (no downgrade for that instrument), alongside the
   existing exposed case — not a synthetic category invented for the
   test.
4. **Frontend** — no change needed. `tier1_confidence_downgrade` is
   either present or `None` per instrument exactly as today;
   `card.js`'s existing badge rendering (`tier1ConfidenceDowngradeHtml`,
   `otherEventTier1DowngradeMarkerHtml`) doesn't care why it's `None`.

## Global constraints

- `predicted_direction` is never touched by this spec, in any code path
  — confidence-only, exactly like Batch 6.
- The exposure table is a static, hand-reviewed Python constant — no new
  database table, no live-fetch dependency.
- Every entry in `_NOT_EXPOSED` must cite the real Layer1/Layer2
  workbook row(s) it's built from — no entry without a citation.
- Only `Certain`/`Likely`-confidence entries are honored by `is_exposed()`
  at runtime; `Guessing`-confidence entries are documented but inert.
- The exposure table's keys are `symbol_class` values (from
  `webapp/symbols.py::classify_symbol()`), never a hardcoded ticker —
  generalizes to a future tracked symbol without a redesign.
- The one-tier floor and never-compounds-past-one-tier rules from Batch 6
  are unchanged, just applied per-instrument.
- Building the actual `_NOT_EXPOSED` table content is implementation
  work requiring a full, deliberate read of all 18 Layer1 rows and all
  15 Layer2 rows — not to be invented from the partial sample read
  during this brainstorm.
