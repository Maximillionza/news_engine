# Event → Symbol Relevance Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static, hand-curated, 9-event-type × 12-symbol reference table answering "does this Tier 1 event genuinely reach this specific symbol" — Relevant / Not relevant / honestly Unverified — plus a generated human-readable rendition of it.

**Architecture:** One new data module (`data_layer/event_symbol_relevance.py`) holds an exhaustive 108-entry Python constant, following the same hand-curated/cited discipline `data_layer/exposure.py` already established. Population is split into 9 research tasks (one per event type), each doing real, sourced research the same way this project's other tables were built (workbook sheets first, then real WebSearch for the rest) — never fabricated. A final task adds a small generator script that renders the table to `docs/event-symbol-relevance.md`.

**Tech Stack:** Python, `pytest`, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-13-event-symbol-relevance-grid-design.md`

## Global Constraints

- Never fabricate a `RELEVANT` or `NOT_RELEVANT` citation — an unresearched or genuinely inconclusive cell is `UNVERIFIED`, not a guess.
- The table is a static hand-curated Python constant — never a database table, never a live fetch.
- This phase produces a reference table only. Do not touch `webapp/predictions_service.py`, any dashboard file, `webapp/symbols.py`'s `classify_symbol()`/`usd_relationship`, or `tier1-cpi-ppi-autoresearch`'s live scheduled-task prompt — wiring this table into live behavior is phase 3, explicitly deferred.
- The table is exhaustive: all 108 `(event_type, symbol)` keys are always present. Never simplify this into a sparse exceptions-only table the way `exposure.py`'s `_NOT_EXPOSED` is — a missing key must never be possible to confuse with an intentionally-unverified one.
- The 9 event-type row labels represent the underlying economic event, not one exact calendar title — several already cover more than one real title (see Task 1's `EVENT_TYPES` for the exact mapping). Do not confuse these with the exact calendar-title strings `tier1-cpi-ppi-autoresearch`'s Step 1 matches against — that list stays untouched, this is a parallel, deliberately coarser set of row labels.
- The 12 symbol columns are exactly the ones `webapp/static/js/dashboard/symbol-picker.js`'s `CATEGORIES` constant already defines: `XAUUSD`, `XAGUSD`, `US30`, `US500`, `NAS100`, `EURUSD`, `GBPUSD`, `USDJPY`, `USDCHF`, `AUDUSD`, `NZDUSD`, `USDCAD`.
- Research sourcing order, every task: (1) `docs/News_Engine_Causation_Matrix_v2.xlsx`'s `Layer1_Event_to_USD` and `Layer2_Asset_Transmission` sheets and the relevant `POC_*` sheet — real, already-sourced findings; (2) `C:\Users\Masoodt\.claude\scheduled-tasks\tier1-cpi-ppi-autoresearch\SKILL.md`'s "PER-INSTRUMENT QUIRKS" section — real prose already written this session; (3) real WebSearch for anything the above doesn't resolve. A cell that still has no real, citable answer after this stays `UNVERIFIED` with an honest one-line note — that is a correct, expected outcome for a meaningful fraction of cells, not a failure to research harder.

---

### Task 1: Schema, scaffolding, and the two pure functions

**Files:**
- Create: `data_layer/event_symbol_relevance.py`
- Test: `tests/test_event_symbol_relevance.py`

**Interfaces:**
- Produces: `EVENT_TYPES: tuple[str, ...]` (9 real labels), `SYMBOLS: tuple[str, ...]` (12 real tickers), `RelevanceStatus` (Enum: `RELEVANT`, `NOT_RELEVANT`, `UNVERIFIED`), `RelevanceJudgment` (frozen dataclass: `status: RelevanceStatus`, `citation: str`), `_RELEVANCE_TABLE: dict[tuple[str, str], RelevanceJudgment]` (starts empty — populated by Tasks 2-10), `get_relevance(event_type: str, symbol: str) -> RelevanceJudgment`, `treat_as_relevant(judgment: RelevanceJudgment) -> bool`.
- Consumes: nothing — this is the foundation every later task builds on.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_event_symbol_relevance.py
"""
Tests for data_layer/event_symbol_relevance.py -- the phase-1 static
reference grid answering "does this Tier 1 event genuinely reach this
specific symbol". See docs/superpowers/specs/2026-09-13-event-symbol-
relevance-grid-design.md.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.event_symbol_relevance as esr


def test_get_relevance_raises_keyerror_for_a_pair_outside_the_108_scope():
    print("=== get_relevance: raises KeyError for a genuinely unrecognized (event_type, symbol) pair ===")
    try:
        esr.get_relevance("Not A Real Event", "XAUUSD")
        raise AssertionError("expected KeyError for an event_type outside EVENT_TYPES")
    except KeyError:
        pass
    try:
        esr.get_relevance("CPI m/m", "NOTASYMBOL")
        raise AssertionError("expected KeyError for a symbol outside SYMBOLS")
    except KeyError:
        pass
    print("PASS\n")


def test_treat_as_relevant_relevant_is_true():
    print("=== treat_as_relevant: RELEVANT -> True ===")
    judgment = esr.RelevanceJudgment(esr.RelevanceStatus.RELEVANT, "real citation")
    assert esr.treat_as_relevant(judgment) is True
    print("PASS\n")


def test_treat_as_relevant_not_relevant_is_false():
    print("=== treat_as_relevant: NOT_RELEVANT -> False ===")
    judgment = esr.RelevanceJudgment(esr.RelevanceStatus.NOT_RELEVANT, "real citation")
    assert esr.treat_as_relevant(judgment) is False
    print("PASS\n")


def test_treat_as_relevant_unverified_defaults_true():
    print("=== treat_as_relevant: UNVERIFIED -> True (explicit product decision -- nothing is silently suppressed before it's actually been checked) ===")
    judgment = esr.RelevanceJudgment(esr.RelevanceStatus.UNVERIFIED, "not yet researched")
    assert esr.treat_as_relevant(judgment) is True
    print("PASS\n")


def test_event_types_and_symbols_match_the_spec_exactly():
    print("=== EVENT_TYPES and SYMBOLS match the spec's real 9x12 scope exactly ===")
    assert len(esr.EVENT_TYPES) == 9, f"expected 9 event types, got {len(esr.EVENT_TYPES)}"
    assert len(esr.SYMBOLS) == 12, f"expected 12 symbols, got {len(esr.SYMBOLS)}"
    assert set(esr.SYMBOLS) == {
        "XAUUSD", "XAGUSD", "US30", "US500", "NAS100",
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD",
    }
    print("PASS\n")


if __name__ == "__main__":
    test_get_relevance_raises_keyerror_for_a_pair_outside_the_108_scope()
    test_treat_as_relevant_relevant_is_true()
    test_treat_as_relevant_not_relevant_is_false()
    test_treat_as_relevant_unverified_defaults_true()
    test_event_types_and_symbols_match_the_spec_exactly()
    print("All event_symbol_relevance scaffolding tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_event_symbol_relevance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_layer.event_symbol_relevance'`

- [ ] **Step 3: Write the implementation**

```python
# data_layer/event_symbol_relevance.py
"""
Phase 1 of a two-phase plan (see docs/superpowers/specs/2026-09-13-event-
symbol-relevance-grid-design.md): a static, hand-curated reference table
answering "does this Tier 1 event genuinely reach this specific symbol" --
Relevant, Not relevant, or honestly Unverified where no real evidence
exists yet. Same discipline as data_layer/exposure.py -- a real Python
constant, never a database table or a live fetch, extended by hand only
on real, cited evidence.

This is a REFERENCE TABLE ONLY. Nothing here is wired into live scoring,
the dashboard, or the tier1-cpi-ppi-autoresearch scheduled task -- that
wiring is phase 3, explicitly deferred until phase 2 (magnitude/
weighting) also exists.

Row labels represent the underlying economic event, not one exact
calendar title -- several cover more than one real title the way the
existing Tier1 methodologies already group them (see EVENT_TYPES below).
Do not confuse these with tier1-cpi-ppi-autoresearch's own Step 1 exact-
title list, which stays untouched and separate.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# The 9 event types, one per existing Tier 1 methodology. Several
# represent more than one exact calendar title -- "FOMC Rate Decision"
# covers "FOMC Meeting Minutes"/"FOMC Statement"/"Federal Funds Rate";
# "GDP q/q" covers "Prelim GDP q/q"/"Advance GDP q/q"/"GDP q/q"; "Retail
# Sales m/m" covers "Retail Sales m/m"/"Core Retail Sales m/m" -- same
# grouping POC_FOMC_Rate_Decision/POC_GDP_Nowcast/POC_Retail_Sales
# already use for their own methodology, since relevance is a property
# of the underlying event, not each printed title variant.
EVENT_TYPES: tuple[str, ...] = (
    "CPI m/m",
    "PPI m/m",
    "Non-Farm Employment Change",
    "FOMC Rate Decision",
    "GDP q/q",
    "Core PCE Price Index m/m",
    "ISM Manufacturing PMI",
    "ISM Services PMI",
    "Retail Sales m/m",
)

# The 12 symbols webapp/static/js/dashboard/symbol-picker.js's CATEGORIES
# constant already defines. Extend both alongside each other if either
# ever grows -- same "extend this alongside that" convention
# data_layer/dukascopy_feed.py's _INSTRUMENT_MAP comment already uses.
SYMBOLS: tuple[str, ...] = (
    "XAUUSD", "XAGUSD",
    "US30", "US500", "NAS100",
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD",
)


class RelevanceStatus(Enum):
    RELEVANT = "relevant"          # real, sourced evidence this event reaches this symbol
    NOT_RELEVANT = "not_relevant"  # real, sourced evidence this event does NOT meaningfully reach this symbol
    UNVERIFIED = "unverified"      # no real evidence checked yet -- honest, not a guess


@dataclass(frozen=True)
class RelevanceJudgment:
    status: RelevanceStatus
    citation: str  # required, non-empty for every status -- for
                    # RELEVANT/NOT_RELEVANT, the real source; for
                    # UNVERIFIED, a short honest note on what wasn't found


# Populated by Tasks 2-10 below -- every one of the 9x12=108 keys must be
# present by the time Task 11 runs its completeness test. Deliberately
# NOT sparse: a missing key here is a plan bug, not a valid "unverified"
# representation (UNVERIFIED cells still get a real, explicit entry).
_RELEVANCE_TABLE: dict[tuple[str, str], RelevanceJudgment] = {}


def get_relevance(event_type: str, symbol: str) -> RelevanceJudgment:
    """
    Returns the real, sourced judgment for (event_type, symbol). Raises
    KeyError for anything outside the defined 9x12 scope -- this never
    fabricates a judgment for a pair it doesn't recognize; an
    unrecognized pair is a caller bug (a new event type or symbol added
    elsewhere but never added here), not a data-availability case to
    swallow into a default.
    """
    return _RELEVANCE_TABLE[(event_type, symbol)]


def treat_as_relevant(judgment: RelevanceJudgment) -> bool:
    """
    The real yes/no a future phase-3 caller would act on: RELEVANT and
    UNVERIFIED both -> True (an unverified cell defaults to "assume
    relevant" so nothing gets silently suppressed before it's actually
    been checked -- explicit product decision, 2026-09-13); NOT_RELEVANT
    -> False. A caller DISPLAYING this to a person must still show
    judgment.status separately -- never collapse UNVERIFIED into a plain
    "yes" with no distinguishing label.
    """
    return judgment.status != RelevanceStatus.NOT_RELEVANT
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_event_symbol_relevance.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: scaffold the event-symbol relevance grid (schema, empty table, pure functions)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Populate CPI m/m's 12 symbol entries

**Files:**
- Modify: `data_layer/event_symbol_relevance.py` (`_RELEVANCE_TABLE`)
- Test: `tests/test_event_symbol_relevance.py` (append)

**Interfaces:**
- Consumes: `EVENT_TYPES`, `SYMBOLS`, `RelevanceStatus`, `RelevanceJudgment`, `_RELEVANCE_TABLE` from Task 1.
- Produces: 12 real entries keyed `("CPI m/m", <symbol>)` for every symbol in `SYMBOLS`.

**Research already available to seed real entries (read these before searching further):** `Layer1_Event_to_USD`'s `2025-07-CPI`, `2026-07-CPI`, and `2026-03-CPI` rows (real, dated, sourced CPI-to-gold/DXY reactions — e.g. the 2025-07-CPI row: "gold to 1-week low ($3,331.12) as headline dominated"); the Tier1 prompt's PER-INSTRUMENT QUIRKS section (gold, silver, US30 nuance already written); `POC_CPI_Leading_Indicators`. For the FX majors, real WebSearch research is needed — check whether a real, dated case exists of a CPI surprise moving each specific pair meaningfully (start with EURUSD, the most liquid and most commonly cited in CPI-reaction coverage) before falling back to UNVERIFIED.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_cpi_mm_has_all_12_symbol_entries_with_real_shape():
    print("=== CPI m/m: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("CPI m/m", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"CPI m/m x {symbol} has an empty citation"
    print("PASS\n")
```

Add the new test's call to the `if __name__ == "__main__":` block.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_cpi_mm_has_all_12_symbol_entries_with_real_shape -v`
Expected: FAIL with `KeyError` (no entries yet)

- [ ] **Step 3: Research and add the 12 real entries**

Add to `_RELEVANCE_TABLE` in `data_layer/event_symbol_relevance.py`, immediately after the dict's opening `{`:

```python
    ("CPI m/m", "XAUUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Layer1_Event_to_USD 2025-07-CPI/2026-03-CPI/2026-07-CPI rows -- "
        "repeated, dated, sourced gold reactions to CPI surprises "
        "(e.g. 2025-07-CPI: gold to a 1-week low as headline dominated)",
    ),
    ("CPI m/m", "XAGUSD"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Same USD-inflation channel as XAUUSD (Tier1 prompt's PER-INSTRUMENT "
        "QUIRKS: silver moves off the same baseline, amplified annually "
        "though not always monthly) -- no real evidence CPI's reach to "
        "silver is itself in question, only its relative magnitude vs gold",
    ),
    ("CPI m/m", "US30"): RelevanceJudgment(
        RelevanceStatus.RELEVANT,
        "Tier1 prompt's PER-INSTRUMENT QUIRKS: equity indices react to "
        "the same rate-path news CPI feeds into, framing-dependent "
        "(soft-landing vs recession-fear) but real and documented "
        "(Evercore ISI post-rate-cut pattern already cited there)",
    ),
    # Research the remaining 9 (XAGUSD's US500/NAS100 siblings, and all 7
    # FX majors) via real WebSearch -- a real, dated case of a CPI
    # surprise moving that specific pair, or an honest UNVERIFIED entry
    # if none is found. Example UNVERIFIED shape:
    # ("CPI m/m", "NZDUSD"): RelevanceJudgment(
    #     RelevanceStatus.UNVERIFIED,
    #     "No primary-source coverage found of a CPI surprise's specific "
    #     "reaction in NZDUSD, as distinct from the general USD-majors move",
    # ),
```

Replace the comment block with the real 9 remaining entries once researched, keeping every entry's citation real and specific — never copy one symbol's citation onto another without checking that symbol's own real reaction.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_cpi_mm_has_all_12_symbol_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: populate CPI m/m's event-symbol relevance entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Populate PPI m/m's 12 symbol entries

**Files:**
- Modify: `data_layer/event_symbol_relevance.py` (`_RELEVANCE_TABLE`)
- Test: `tests/test_event_symbol_relevance.py` (append)

**Interfaces:**
- Consumes: same as Task 2.
- Produces: 12 real entries keyed `("PPI m/m", <symbol>)`.

**Research already available:** `POC_PPI_Leading_Indicators` (BLS prior PPI + ISM Prices Paid methodology); §3 "Real accuracy" review in `docs/feature-inventory-2026-09-11.md` notes a real live PPI case (Sep 10 2026 PPI miss, Tier 1 called Certain/bullish, wrong) — confirms PPI genuinely reaches gold/US30 in practice (a wrong call is still evidence the event reaches the instrument; only the direction was wrong, not the relevance). For FX majors, PPI's relevance is generally considered secondary to CPI in the same inflation-channel sense — verify with real WebSearch per pair rather than assuming.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_ppi_mm_has_all_12_symbol_entries_with_real_shape():
    print("=== PPI m/m: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("PPI m/m", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"PPI m/m x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_ppi_mm_has_all_12_symbol_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("PPI m/m", <symbol>)` entries to `_RELEVANCE_TABLE`, same research discipline as Task 2 — start from the sources named above, real WebSearch for the rest, `UNVERIFIED` with an honest note wherever no real source is found.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_ppi_mm_has_all_12_symbol_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: populate PPI m/m's event-symbol relevance entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Populate Non-Farm Employment Change's 12 symbol entries

**Files:**
- Modify: `data_layer/event_symbol_relevance.py` (`_RELEVANCE_TABLE`)
- Test: `tests/test_event_symbol_relevance.py` (append)

**Interfaces:**
- Consumes: same as Task 2.
- Produces: 12 real entries keyed `("Non-Farm Employment Change", <symbol>)`.

**Research already available:** `Layer1_Event_to_USD`'s `2026-06-NFP`, `2026-04-NFP`, `2026-07-NFP` rows — real, dated, sourced NFP reactions ("Sept 2026 hike probability 67% -> ~50%; DXY posted biggest weekly decline since April; gold best week since March" for the June 2026 miss). `POC_NFP_Leading_Indicators`. This is one of the most heavily-documented events in the workbook — real evidence for gold and USD-majors should be straightforward; check FX majors individually for real, dated cases rather than assuming uniform reach.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_nfp_has_all_12_symbol_entries_with_real_shape():
    print("=== Non-Farm Employment Change: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("Non-Farm Employment Change", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"NFP x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_nfp_has_all_12_symbol_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("Non-Farm Employment Change", <symbol>)` entries, seeded from the real logged NFP rows above, real WebSearch for the rest.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_nfp_has_all_12_symbol_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: populate NFP's event-symbol relevance entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Populate FOMC Rate Decision's 12 symbol entries

**Files:**
- Modify: `data_layer/event_symbol_relevance.py` (`_RELEVANCE_TABLE`)
- Test: `tests/test_event_symbol_relevance.py` (append)

**Interfaces:**
- Consumes: same as Task 2.
- Produces: 12 real entries keyed `("FOMC Rate Decision", <symbol>)`.

**Research already available:** `Layer1_Event_to_USD`'s `2025-10-29-FOMC`, `2025-11-FED-INDEPENDENCE`, `2025-12-FED-SUCCESSION`, `2026-05-13-FED-CHAIR-VOTE` rows. `Layer2_Asset_Transmission`'s "2s10s yield curve shape" row (real Dec 2025 curve-widening case). `POC_FOMC_Rate_Decision`. The real, live Tier1 predictions already logged for FOMC Statement/Federal Funds Rate on 2026-09-16 (`Certain` confidence, both XAUUSD and US30) are themselves real evidence FOMC reaches both. For FX majors, this is arguably the single most universally-reaching event of the 9 (a Fed decision is a primary driver of every USD-legged pair) — verify real evidence per pair rather than assuming, but expect fewer `UNVERIFIED`/`NOT_RELEVANT` results here than other event types.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_fomc_rate_decision_has_all_12_symbol_entries_with_real_shape():
    print("=== FOMC Rate Decision: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("FOMC Rate Decision", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"FOMC Rate Decision x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_fomc_rate_decision_has_all_12_symbol_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("FOMC Rate Decision", <symbol>)` entries, seeded from the real logged FOMC/Fed rows above.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_fomc_rate_decision_has_all_12_symbol_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: populate FOMC Rate Decision's event-symbol relevance entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Populate GDP q/q's 12 symbol entries

**Files:**
- Modify: `data_layer/event_symbol_relevance.py` (`_RELEVANCE_TABLE`)
- Test: `tests/test_event_symbol_relevance.py` (append)

**Interfaces:**
- Consumes: same as Task 2.
- Produces: 12 real entries keyed `("GDP q/q", <symbol>)`.

**Research already available:** `POC_GDP_Nowcast` (GDPNow + yield-curve-slope methodology). No GDP-specific row exists yet in `Layer1_Event_to_USD` as of this session — this event type has less pre-existing seed material than CPI/NFP/FOMC. Expect to rely more heavily on real WebSearch here, and expect a real, honest higher proportion of `UNVERIFIED` entries for the less-liquid FX majors (e.g. NZDUSD, AUDCAD-adjacent pairs) than for gold/US30/EURUSD.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_gdp_qq_has_all_12_symbol_entries_with_real_shape():
    print("=== GDP q/q: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("GDP q/q", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"GDP q/q x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_gdp_qq_has_all_12_symbol_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("GDP q/q", <symbol>)` entries. It is fully correct and expected for several of these to resolve `UNVERIFIED` given the thinner seed material — do not force a `RELEVANT`/`NOT_RELEVANT` verdict without a real source.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_gdp_qq_has_all_12_symbol_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: populate GDP q/q's event-symbol relevance entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Populate Core PCE Price Index m/m's 12 symbol entries

**Files:**
- Modify: `data_layer/event_symbol_relevance.py` (`_RELEVANCE_TABLE`)
- Test: `tests/test_event_symbol_relevance.py` (append)

**Interfaces:**
- Consumes: same as Task 2.
- Produces: 12 real entries keyed `("Core PCE Price Index m/m", <symbol>)`.

**Research already available:** `POC_Core_PCE` (Cleveland Fed nowcast + CPI-to-PCE weighting-adjustment methodology). Core PCE is the Fed's own preferred inflation gauge — its relevance to gold/US30/majors is plausible by the same inflation-channel logic as CPI, but verify with real sources per symbol rather than copying CPI m/m's entries wholesale; PCE's real-world market reaction is documented (in the wider financial press, not yet in this project's own workbook) as often smaller than CPI's own release since much of its signal is already priced in via the same-month CPI print.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_core_pce_has_all_12_symbol_entries_with_real_shape():
    print("=== Core PCE Price Index m/m: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("Core PCE Price Index m/m", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"Core PCE x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_core_pce_has_all_12_symbol_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("Core PCE Price Index m/m", <symbol>)` entries.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_core_pce_has_all_12_symbol_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: populate Core PCE's event-symbol relevance entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: Populate ISM Manufacturing PMI's 12 symbol entries

**Files:**
- Modify: `data_layer/event_symbol_relevance.py` (`_RELEVANCE_TABLE`)
- Test: `tests/test_event_symbol_relevance.py` (append)

**Interfaces:**
- Consumes: same as Task 2.
- Produces: 12 real entries keyed `("ISM Manufacturing PMI", <symbol>)`.

**Research already available:** `POC_ISM_Manufacturing_PMI` (5-district regional Fed survey average methodology). A manufacturing-sector survey's reach is plausibly narrower/more commodity- and growth-sensitive than a broad inflation or labor print — check real sources per symbol; a real, honest `NOT_RELEVANT` or `UNVERIFIED` result for a symbol with no manufacturing-sector linkage (e.g. a pure safe-haven pair on a day with no other signal) is a legitimate, expected outcome here, more so than for CPI/NFP/FOMC.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_ism_manufacturing_has_all_12_symbol_entries_with_real_shape():
    print("=== ISM Manufacturing PMI: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("ISM Manufacturing PMI", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"ISM Manufacturing PMI x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_ism_manufacturing_has_all_12_symbol_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("ISM Manufacturing PMI", <symbol>)` entries.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_ism_manufacturing_has_all_12_symbol_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: populate ISM Manufacturing PMI's event-symbol relevance entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: Populate ISM Services PMI's 12 symbol entries

**Files:**
- Modify: `data_layer/event_symbol_relevance.py` (`_RELEVANCE_TABLE`)
- Test: `tests/test_event_symbol_relevance.py` (append)

**Interfaces:**
- Consumes: same as Task 2.
- Produces: 12 real entries keyed `("ISM Services PMI", <symbol>)`.

**Research already available:** `POC_ISM_Services_PMI` — already documented in this project as having NO verified Tier 1 leading indicator (regional Fed services surveys checked and found weaker than Manufacturing's). That finding is about predicting the number, not about whether the number (once released) moves markets — research this event type's real market-relevance independently; do not assume the leading-indicator gap implies a relevance gap. Expect real WebSearch to be necessary for nearly every cell here, since little pre-existing seed material covers this event specifically.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_ism_services_has_all_12_symbol_entries_with_real_shape():
    print("=== ISM Services PMI: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("ISM Services PMI", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"ISM Services PMI x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_ism_services_has_all_12_symbol_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("ISM Services PMI", <symbol>)` entries. A real majority-`UNVERIFIED` result here is expected and correct, not a sign of insufficient effort — say so plainly in the task report rather than forcing verdicts.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_ism_services_has_all_12_symbol_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: populate ISM Services PMI's event-symbol relevance entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: Populate Retail Sales m/m's 12 symbol entries

**Files:**
- Modify: `data_layer/event_symbol_relevance.py` (`_RELEVANCE_TABLE`)
- Test: `tests/test_event_symbol_relevance.py` (append)

**Interfaces:**
- Consumes: same as Task 2.
- Produces: 12 real entries keyed `("Retail Sales m/m", <symbol>)`.

**Research already available:** `POC_Retail_Sales` (real-time card-spending-tracker methodology). The real, live Tier1 predictions already logged for Retail Sales m/m/Core Retail Sales m/m on 2026-09-16 (`Likely` confidence, both XAUUSD and US30) are real evidence this event reaches both. For FX majors, consumer-spending data is a real driver of USD-broad moves — check per pair with real sources.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_retail_sales_has_all_12_symbol_entries_with_real_shape():
    print("=== Retail Sales m/m: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("Retail Sales m/m", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"Retail Sales m/m x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_retail_sales_has_all_12_symbol_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("Retail Sales m/m", <symbol>)` entries, seeded from the real logged Retail Sales rows above.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_retail_sales_has_all_12_symbol_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_relevance.py tests/test_event_symbol_relevance.py
git commit -m "feat: populate Retail Sales m/m's event-symbol relevance entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 11: Completeness test, markdown generator, and the round-trip test

**Files:**
- Create: `scripts/generate_event_symbol_relevance_doc.py`
- Create: `docs/event-symbol-relevance.md` (generated output, committed)
- Test: `tests/test_event_symbol_relevance.py` (append), `tests/test_generate_event_symbol_relevance_doc.py`

**Interfaces:**
- Consumes: `EVENT_TYPES`, `SYMBOLS`, `RelevanceStatus`, `get_relevance()` from Task 1; the fully-populated `_RELEVANCE_TABLE` from Tasks 2-10.
- Produces: `render_markdown_table() -> str` in the new generator script, and the generated file itself.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_event_symbol_relevance.py`:

```python
def test_every_one_of_the_108_real_combinations_is_present():
    print("=== Completeness: all 9x12=108 real (event_type, symbol) combinations are present in the table ===")
    missing = []
    for event_type in esr.EVENT_TYPES:
        for symbol in esr.SYMBOLS:
            try:
                esr.get_relevance(event_type, symbol)
            except KeyError:
                missing.append((event_type, symbol))
    assert missing == [], f"missing {len(missing)} of 108 real entries: {missing[:5]}{'...' if len(missing) > 5 else ''}"
    print("PASS\n")
```

Add its call to `__main__`.

Create `tests/test_generate_event_symbol_relevance_doc.py`:

```python
"""
Tests for scripts/generate_event_symbol_relevance_doc.py -- confirms the
generated markdown really reflects the real table content (a status and
its real citation both appear for a real slice of cells), rather than
silently dropping anything. Not a full 108-cell check -- Task 11's own
completeness test in tests/test_event_symbol_relevance.py already covers
that the table itself has all 108 entries; this only confirms the
generator faithfully renders what's there.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.event_symbol_relevance as esr
from scripts.generate_event_symbol_relevance_doc import render_markdown_table


def test_render_markdown_table_includes_every_event_type_as_a_heading():
    print("=== render_markdown_table: every one of the 9 event types appears as its own section ===")
    output = render_markdown_table()
    for event_type in esr.EVENT_TYPES:
        assert event_type in output, f"expected a section for {event_type!r}"
    print("PASS\n")


def test_render_markdown_table_includes_a_real_cells_status_and_citation():
    print("=== render_markdown_table: a real cell's status symbol and citation text both appear ===")
    output = render_markdown_table()
    sample_event, sample_symbol = esr.EVENT_TYPES[0], esr.SYMBOLS[0]
    judgment = esr.get_relevance(sample_event, sample_symbol)
    assert sample_symbol in output
    status_symbol = {
        esr.RelevanceStatus.RELEVANT: "\u2713",      # checkmark
        esr.RelevanceStatus.NOT_RELEVANT: "\u2715",  # cross
        esr.RelevanceStatus.UNVERIFIED: "?",
    }[judgment.status]
    assert status_symbol in output, f"expected the {judgment.status} status symbol {status_symbol!r} to appear"
    assert judgment.citation in output, "expected the real citation text to appear verbatim, not summarized or dropped"
    print("PASS\n")


if __name__ == "__main__":
    test_render_markdown_table_includes_every_event_type_as_a_heading()
    test_render_markdown_table_includes_a_real_cells_status_and_citation()
    print("All generator tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_event_symbol_relevance.py::test_every_one_of_the_108_real_combinations_is_present tests/test_generate_event_symbol_relevance_doc.py -v`
Expected: the completeness test PASSES already (Tasks 2-10 filled the table) — confirm this now, since it's the real gate that Tasks 2-10 actually finished the job; the two generator tests FAIL with `ModuleNotFoundError: No module named 'scripts.generate_event_symbol_relevance_doc'`

- [ ] **Step 3: Write the generator script**

```python
# scripts/generate_event_symbol_relevance_doc.py
"""
Renders data_layer/event_symbol_relevance.py's _RELEVANCE_TABLE to
docs/event-symbol-relevance.md -- a real, human-readable rendition of the
grid, generated FROM the Python table so the two can never drift out of
sync. Run this after any change to the table's content.

Usage: python scripts/generate_event_symbol_relevance_doc.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.event_symbol_relevance as esr

_STATUS_SYMBOL = {
    esr.RelevanceStatus.RELEVANT: "\u2713 Relevant",
    esr.RelevanceStatus.NOT_RELEVANT: "\u2715 Not relevant",
    esr.RelevanceStatus.UNVERIFIED: "? Unverified",
}

_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "event-symbol-relevance.md")


def render_markdown_table() -> str:
    lines = [
        "# Event -> Symbol Relevance Grid",
        "",
        "Generated from `data_layer/event_symbol_relevance.py` -- do not "
        "hand-edit this file, edit the Python table and re-run "
        "`scripts/generate_event_symbol_relevance_doc.py` instead. "
        "Phase 1 only: this answers whether an event genuinely reaches a "
        "symbol, not by how much (phase 2), and is not yet wired into "
        "live scoring or the dashboard (phase 3). See "
        "`docs/superpowers/specs/2026-09-13-event-symbol-relevance-grid-design.md`.",
        "",
    ]
    for event_type in esr.EVENT_TYPES:
        lines.append(f"## {event_type}")
        lines.append("")
        lines.append("| Symbol | Status | Citation |")
        lines.append("|---|---|---|")
        for symbol in esr.SYMBOLS:
            judgment = esr.get_relevance(event_type, symbol)
            status_text = _STATUS_SYMBOL[judgment.status]
            citation = judgment.citation.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {symbol} | {status_text} | {citation} |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    content = render_markdown_table()
    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_event_symbol_relevance.py tests/test_generate_event_symbol_relevance_doc.py -v`
Expected: all pass

- [ ] **Step 5: Generate the real doc and run the full suite**

Run: `python scripts/generate_event_symbol_relevance_doc.py`
Expected: `Wrote .../docs/event-symbol-relevance.md`

Run: `python -m pytest -q`
Expected: all tests pass, including every test added in this plan

- [ ] **Step 6: Commit**

```bash
git add scripts/generate_event_symbol_relevance_doc.py docs/event-symbol-relevance.md tests/test_generate_event_symbol_relevance_doc.py tests/test_event_symbol_relevance.py
git commit -m "feat: generate the human-readable event-symbol relevance grid doc

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Final step (whole-plan, not a task)

After Task 11, update `docs/feature-inventory-2026-09-11.md` per its own standing maintenance rule: a new row noting the event-symbol relevance grid is shipped (phase 1 of 3 — magnitude and live wiring both explicitly deferred), where it lives (`data_layer/event_symbol_relevance.py`, `docs/event-symbol-relevance.md`), and — honestly — what fraction of the 108 cells resolved `UNVERIFIED` rather than claiming full coverage.
