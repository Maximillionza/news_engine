# Event → Symbol Magnitude Grid Implementation Plan (Phase 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static, hand-curated Low/Medium/High/Unverified magnitude tier for each of Phase 1's 94 `RELEVANT` (event type, symbol) cells, plus a generated human-readable rendition of it.

**Architecture:** One new data module (`data_layer/event_symbol_magnitude.py`) holds a table scoped exactly to Phase 1's 94 `RELEVANT` keys — never edited, only read via `event_symbol_relevance.get_relevance()`. Population is 9 research tasks (one per event type, using that event type's real `RELEVANT` symbol subset — Phase 1 was not uniformly 12/12), reusing Phase 1's own citations where they already contain a real quantified move size. A generator script and its drift-guard test are built in the scaffolding task this time, not bolted on at the end the way Phase 1's final review had to add them.

**Tech Stack:** Python, `pytest`, no new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-16-event-symbol-magnitude-grid-design.md`

## Global Constraints

- Never fabricate a `LOW`/`MEDIUM`/`HIGH` tier assignment — an unresearched or genuinely inconclusive cell is `UNVERIFIED`, not a guess.
- The table is a static hand-curated Python constant — never a database table, never a live fetch.
- Reuse Phase 1's own citation for a cell where it already contains a real quantified move size (many do — see each task's own real citation dump below) rather than re-researching from scratch.
- Carry forward Phase 1's hard-won lesson from its ISM Manufacturing PMI task: prefer this project's own internal `scoring/backtest_log.db` outcome data over an external news article's causal-attribution claim on a multi-driver trading day; independently re-verify any external citation's date/numbers/narrative before trusting it — this exact defect pattern cost two full fix rounds in Phase 1.
- This phase produces a reference table only. Do not touch `webapp/predictions_service.py`, any dashboard file, `webapp/symbols.py`, or `tier1-cpi-ppi-autoresearch`'s live scheduled-task prompt. `data_layer/event_symbol_relevance.py` is read-only — only ever call `get_relevance()`, never edit its table.
- The magnitude table is scoped exactly to the 94 real `RELEVANT` `(event_type, symbol)` pairs Phase 1 already resolved — never the full 108, and never a pair that's `NOT_RELEVANT` or `UNVERIFIED` in Phase 1.
- The tier boundaries below (roughly under 0.3% / 0.3–0.8% / over 0.8%) are an explicitly-flagged best-effort starting ruler from the spec, not independently re-derived before population. If real logged move data makes a boundary look wrong for a specific instrument class (e.g. gold's normal daily range vs. a currency pair's), rule on it yourself and record the ruling — this is the kind of plan-vs-evidence judgment an SDD execution is expected to make, not stall over.
- The 12 symbol columns are exactly the ones `webapp/static/js/dashboard/symbol-picker.js`'s `CATEGORIES` constant defines: `XAUUSD`, `XAGUSD`, `US30`, `US500`, `NAS100`, `EURUSD`, `GBPUSD`, `USDJPY`, `USDCHF`, `AUDUSD`, `NZDUSD`, `USDCAD`.
- Research sourcing order, every task: (1) the corresponding cell's own Phase 1 citation in `data_layer/event_symbol_relevance.py` — read it directly, most already contain a real number; (2) `scoring/backtest_log.db`'s `outcomes`/`tier1_predictions` tables for real, timestamped historical moves not already surfaced in (1); (3) real WebSearch for the rest, independently re-verified per the lesson above. A cell with no real, citable magnitude evidence after this stays `UNVERIFIED` with an honest one-line note — a correct, expected outcome for some cells, not a failure.

**Real, current `RELEVANT` symbol lists per event type** (queried directly from `data_layer/event_symbol_relevance.py` on 2026-09-16 — Phase 1 was NOT uniformly 12/12; total 94):

- CPI m/m (12): XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD
- PPI m/m (12): XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD
- Non-Farm Employment Change (12): XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD
- FOMC Rate Decision (12): XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD
- GDP q/q (10): XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, USDJPY, USDCHF, AUDUSD, NZDUSD
- Core PCE Price Index m/m (12): XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD
- ISM Manufacturing PMI (10): XAUUSD, XAGUSD, US30, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD
- ISM Services PMI (4): XAUUSD, EURUSD, GBPUSD, USDJPY
- Retail Sales m/m (10): XAUUSD, XAGUSD, US30, US500, EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD

---

### Task 1: Schema, scaffolding, generator, and drift-guard test

**Files:**
- Create: `data_layer/event_symbol_magnitude.py`
- Create: `scripts/generate_event_symbol_magnitude_doc.py`
- Test: `tests/test_event_symbol_magnitude.py`
- Test: `tests/test_generate_event_symbol_magnitude_doc.py`

**Interfaces:**
- Produces: `MagnitudeTier` (Enum: `LOW`, `MEDIUM`, `HIGH`, `UNVERIFIED`), `MagnitudeJudgment` (frozen dataclass: `tier: MagnitudeTier`, `citation: str`), `_MAGNITUDE_TABLE: dict[tuple[str, str], MagnitudeJudgment]` (starts empty — populated by Tasks 2-10), `get_magnitude(event_type: str, symbol: str) -> MagnitudeJudgment`, `render_markdown_table() -> str` (in the generator script), `main()` (in the generator script, writes the doc).
- Consumes: `data_layer.event_symbol_relevance`'s `EVENT_TYPES`, `SYMBOLS`, `RelevanceStatus`, `get_relevance()` — read-only, to validate scope.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_event_symbol_magnitude.py
"""
Tests for data_layer/event_symbol_magnitude.py -- Phase 2's static
reference grid answering "how much does a relevant Tier 1 event
typically move a given symbol". See docs/superpowers/specs/2026-09-16-
event-symbol-magnitude-grid-design.md. Scoped exactly to the 94
(event_type, symbol) pairs data_layer/event_symbol_relevance.py already
resolved RELEVANT -- never the full 108.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.event_symbol_magnitude as esm
import data_layer.event_symbol_relevance as esr


def test_get_magnitude_raises_keyerror_for_a_pair_outside_the_94_scope():
    print("=== get_magnitude: raises KeyError for a pair outside the 94-pair RELEVANT scope ===")
    try:
        esm.get_magnitude("Not A Real Event", "XAUUSD")
        raise AssertionError("expected KeyError for an event_type outside the table")
    except KeyError:
        pass
    print("PASS\n")


def test_magnitude_tier_has_exactly_four_members():
    print("=== MagnitudeTier: exactly LOW/MEDIUM/HIGH/UNVERIFIED, no more no less ===")
    assert {m.name for m in esm.MagnitudeTier} == {"LOW", "MEDIUM", "HIGH", "UNVERIFIED"}
    print("PASS\n")


if __name__ == "__main__":
    test_get_magnitude_raises_keyerror_for_a_pair_outside_the_94_scope()
    test_magnitude_tier_has_exactly_four_members()
    print("All event_symbol_magnitude scaffolding tests passed.")
```

```python
# tests/test_generate_event_symbol_magnitude_doc.py
"""
Tests for scripts/generate_event_symbol_magnitude_doc.py. The
drift-guard test (byte-for-byte match against the committed doc) is
scaffolded from Task 1 this time, not added only after a final review
finds the gap the way Phase 1's was.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generate_event_symbol_magnitude_doc import render_markdown_table, _OUTPUT_PATH


def test_render_markdown_table_matches_the_committed_doc_exactly():
    print("=== render_markdown_table: live output matches docs/event-symbol-magnitude.md byte-for-byte ===")
    live = render_markdown_table()
    with open(_OUTPUT_PATH, encoding="utf-8") as f:
        committed = f.read()
    assert live == committed, "the generated doc is out of sync with the real table -- re-run scripts/generate_event_symbol_magnitude_doc.py"
    print("PASS\n")


if __name__ == "__main__":
    test_render_markdown_table_matches_the_committed_doc_exactly()
    print("All generator tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_event_symbol_magnitude.py tests/test_generate_event_symbol_magnitude_doc.py -v`
Expected: FAIL with `ModuleNotFoundError` for both files (neither module exists yet)

- [ ] **Step 3: Write the implementation**

```python
# data_layer/event_symbol_magnitude.py
"""
Phase 2 of a three-phase plan (see docs/superpowers/specs/2026-09-16-
event-symbol-magnitude-grid-design.md): a static, hand-curated
magnitude tier for each of Phase 1's 94 RELEVANT (event_type, symbol)
cells -- LOW/MEDIUM/HIGH (cited) or honestly UNVERIFIED where no real
evidence pins down a typical move size. Same discipline as
data_layer/exposure.py and data_layer/event_symbol_relevance.py -- a
real Python constant, never a database table or a live fetch.

This is a REFERENCE TABLE ONLY. Nothing here is wired into live
scoring, the dashboard, or the tier1-cpi-ppi-autoresearch scheduled
task -- that's phase 3, explicitly deferred by user decision.

Scoped EXACTLY to the 94 pairs data_layer.event_symbol_relevance's
get_relevance() already resolved RELEVANT as of 2026-09-16 -- never
edited here, only read. A pair that's NOT_RELEVANT or UNVERIFIED in
that module has no entry here and never will until its own relevance
is resolved first.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MagnitudeTier(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNVERIFIED = "unverified"  # relevance is confirmed real (Phase 1's
                                 # RELEVANT), but no real evidence pins
                                 # down a typical magnitude -- honest,
                                 # not a guess


@dataclass(frozen=True)
class MagnitudeJudgment:
    tier: MagnitudeTier
    citation: str  # required, non-empty for every tier -- for
                    # LOW/MEDIUM/HIGH, the real occurrence(s) that
                    # justify the tier (often reused directly from
                    # event_symbol_relevance's own citation for that
                    # cell); for UNVERIFIED, a short honest note on
                    # what wasn't found


# Populated by Tasks 2-10 below -- every one of the 94 real RELEVANT
# (event_type, symbol) pairs from data_layer.event_symbol_relevance
# must be present by the time Task 11 runs its completeness test.
# Deliberately scoped to exactly that 94-pair subset, never the full
# 108 -- a pair that's NOT_RELEVANT or UNVERIFIED in that module has no
# key here.
_MAGNITUDE_TABLE: dict[tuple[str, str], MagnitudeJudgment] = {}


def get_magnitude(event_type: str, symbol: str) -> MagnitudeJudgment:
    """
    Returns the real, sourced magnitude tier for (event_type, symbol).
    Raises KeyError for anything outside the 94-pair RELEVANT scope --
    this never fabricates a judgment for a pair it doesn't recognize,
    including a real Phase 1 pair that was NOT_RELEVANT or UNVERIFIED
    there (magnitude is only ever researched for a confirmed-RELEVANT
    pair).
    """
    return _MAGNITUDE_TABLE[(event_type, symbol)]
```

```python
# scripts/generate_event_symbol_magnitude_doc.py
"""
Renders data_layer/event_symbol_magnitude.py's _MAGNITUDE_TABLE to
docs/event-symbol-magnitude.md -- generated FROM the Python table so
the two can never drift out of sync (enforced from Task 1 by
tests/test_generate_event_symbol_magnitude_doc.py's byte-for-byte
drift-guard test, unlike Phase 1 where this test was only added during
the final whole-plan review). Run this after any change to the table's
content.

Usage: python scripts/generate_event_symbol_magnitude_doc.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.event_symbol_magnitude as esm
import data_layer.event_symbol_relevance as esr

_TIER_SYMBOL = {
    esm.MagnitudeTier.LOW: "\u25cb Low",
    esm.MagnitudeTier.MEDIUM: "\u25d1 Medium",
    esm.MagnitudeTier.HIGH: "\u25cf High",
    esm.MagnitudeTier.UNVERIFIED: "? Unverified",
}

_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "event-symbol-magnitude.md")


def render_markdown_table() -> str:
    lines = [
        "# Event -> Symbol Magnitude Grid",
        "",
        "Generated from `data_layer/event_symbol_magnitude.py` -- do not "
        "hand-edit this file, edit the Python table and re-run "
        "`scripts/generate_event_symbol_magnitude_doc.py` instead. Phase 2 "
        "of 3: a typical-move-size TIER for each of Phase 1's real RELEVANT "
        "cells (see `docs/event-symbol-relevance.md`), not a precise number "
        "-- and not yet wired into live scoring or the dashboard (phase 3). "
        "See `docs/superpowers/specs/2026-09-16-event-symbol-magnitude-grid-design.md`.",
        "",
    ]
    for event_type in esr.EVENT_TYPES:
        relevant_symbols = [s for s in esr.SYMBOLS if esr.get_relevance(event_type, s).status == esr.RelevanceStatus.RELEVANT]
        if not relevant_symbols:
            continue
        lines.append(f"## {event_type}")
        lines.append("")
        lines.append("| Symbol | Magnitude | Citation |")
        lines.append("|---|---|---|")
        for symbol in relevant_symbols:
            judgment = esm.get_magnitude(event_type, symbol)
            tier_text = _TIER_SYMBOL[judgment.tier]
            citation = judgment.citation.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {symbol} | {tier_text} | {citation} |")
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

- [ ] **Step 4: Run the scaffolding/schema tests to verify they pass**

Run: `python -m pytest tests/test_event_symbol_magnitude.py -v`
Expected: 2 passed

- [ ] **Step 5: Generate an empty doc and confirm the drift-guard test passes against it**

Run: `python scripts/generate_event_symbol_magnitude_doc.py` — this writes `docs/event-symbol-magnitude.md` with no event-type sections yet (the table is empty, so every event type's `relevant_symbols` list still has entries but every `get_magnitude()` call would raise `KeyError` — since the table is empty, the loop body's `esm.get_magnitude(event_type, symbol)` call WILL raise. To generate a valid empty-table doc for this step, temporarily confirm by running `python -c "from scripts.generate_event_symbol_magnitude_doc import render_markdown_table; render_markdown_table()"` and observe it raises `KeyError` — this is EXPECTED and correct at this point (Step 5 is only reachable after at least Task 2 populates real data). Skip actually running the generator in Task 1 — instead just confirm the two files import cleanly with no syntax errors:

Run: `python -c "import scripts.generate_event_symbol_magnitude_doc; import data_layer.event_symbol_magnitude; print('imports OK')"`
Expected: `imports OK`

The drift-guard test itself (`test_render_markdown_table_matches_the_committed_doc_exactly`) will be exercised for real starting in Task 2, once the table has real content and a real doc exists to compare against. For Task 1, confirm only the KeyError-scaffolding and enum-membership tests pass — do not attempt to run the generator or the drift-guard test yet.

- [ ] **Step 6: Commit**

```bash
git add data_layer/event_symbol_magnitude.py scripts/generate_event_symbol_magnitude_doc.py tests/test_event_symbol_magnitude.py tests/test_generate_event_symbol_magnitude_doc.py
git commit -m "feat: scaffold the event-symbol magnitude grid (schema, empty table, generator, drift-guard test)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Populate CPI m/m's 12 magnitude entries

**Files:**
- Modify: `data_layer/event_symbol_magnitude.py` (`_MAGNITUDE_TABLE`)
- Test: `tests/test_event_symbol_magnitude.py` (append)

**Interfaces:**
- Consumes: `MagnitudeTier`, `MagnitudeJudgment`, `_MAGNITUDE_TABLE`, `get_magnitude` from Task 1.
- Produces: 12 real entries keyed `("CPI m/m", <symbol>)` for the full 12-symbol RELEVANT set: XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD.

**Research procedure:** First, read each symbol's real Phase 1 citation directly — run `python -c "import data_layer.event_symbol_relevance as esr; [print(s, ':', esr.get_relevance('CPI m/m', s).citation, '\n') for s in ['XAUUSD','XAGUSD','US30','US500','NAS100','EURUSD','GBPUSD','USDJPY','USDCHF','AUDUSD','NZDUSD','USDCAD']]"` — many already contain a real quantified move (a %, a pip count, a point move); classify that cell's tier directly from it (using the Global Constraints' bands: under ~0.3% = LOW, ~0.3-0.8% = MEDIUM, over ~0.8% = HIGH) rather than re-researching. Where a Phase 1 citation is qualitative only, check `scoring/backtest_log.db`'s `outcomes` table (`event_title LIKE '%CPI%'`) for a real logged move, then real WebSearch for the rest — same sourcing discipline as Phase 1, independently re-verifying any external article per the ISM Manufacturing PMI lesson in the Global Constraints. UNVERIFIED with an honest note if no real evidence pins down a tier.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_magnitude.py`:

```python
def test_cpi_mm_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== CPI m/m: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("CPI m/m", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"CPI m/m x {symbol} has an empty citation"
    print("PASS\n")
```

Add the new test's call to the `if __name__ == "__main__":` block.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_cpi_mm_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("CPI m/m", <symbol>)` entries to `_MAGNITUDE_TABLE` in `data_layer/event_symbol_magnitude.py`, following the research procedure above.

- [ ] **Step 4: Run test to verify it passes, then regenerate the doc and confirm the drift-guard test passes**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_cpi_mm_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: PASS

Run: `python scripts/generate_event_symbol_magnitude_doc.py` (this will still raise `KeyError` for every event type after CPI m/m in `EVENT_TYPES` order that has no entries yet — this is EXPECTED until Task 10 finishes all 9 blocks. For Task 2 only, temporarily comment out or work around this by testing generation is not yet meaningfully runnable end-to-end — skip running the generator/drift-guard test in Tasks 2-9; it becomes runnable for real only once all 9 event types are populated, in Task 10's own steps.)

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_magnitude.py tests/test_event_symbol_magnitude.py
git commit -m "feat: populate CPI m/m's event-symbol magnitude entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Populate PPI m/m's 12 magnitude entries

**Files:**
- Modify: `data_layer/event_symbol_magnitude.py` (`_MAGNITUDE_TABLE`)
- Test: `tests/test_event_symbol_magnitude.py` (append)

**Interfaces:** Same as Task 2. 12-symbol RELEVANT set: XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD.

**Research procedure:** Same as Task 2, substituting `'PPI m/m'` for the event_type in the citation-reading command and `outcomes` query.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_magnitude.py`:

```python
def test_ppi_mm_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== PPI m/m: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("PPI m/m", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"PPI m/m x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_ppi_mm_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("PPI m/m", <symbol>)` entries.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_ppi_mm_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_magnitude.py tests/test_event_symbol_magnitude.py
git commit -m "feat: populate PPI m/m's event-symbol magnitude entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Populate Non-Farm Employment Change's 12 magnitude entries

**Files:**
- Modify: `data_layer/event_symbol_magnitude.py` (`_MAGNITUDE_TABLE`)
- Test: `tests/test_event_symbol_magnitude.py` (append)

**Interfaces:** Same as Task 2. 12-symbol RELEVANT set: XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD.

**Research procedure:** Same as Task 2, substituting `'Non-Farm Employment Change'`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_magnitude.py`:

```python
def test_nfp_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== Non-Farm Employment Change: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("Non-Farm Employment Change", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"NFP x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_nfp_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("Non-Farm Employment Change", <symbol>)` entries.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_nfp_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_magnitude.py tests/test_event_symbol_magnitude.py
git commit -m "feat: populate NFP's event-symbol magnitude entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Populate FOMC Rate Decision's 12 magnitude entries

**Files:**
- Modify: `data_layer/event_symbol_magnitude.py` (`_MAGNITUDE_TABLE`)
- Test: `tests/test_event_symbol_magnitude.py` (append)

**Interfaces:** Same as Task 2. 12-symbol RELEVANT set: XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD.

**Research procedure:** Same as Task 2, substituting `'FOMC Rate Decision'`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_magnitude.py`:

```python
def test_fomc_rate_decision_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== FOMC Rate Decision: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("FOMC Rate Decision", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"FOMC Rate Decision x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_fomc_rate_decision_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("FOMC Rate Decision", <symbol>)` entries.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_fomc_rate_decision_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_magnitude.py tests/test_event_symbol_magnitude.py
git commit -m "feat: populate FOMC Rate Decision's event-symbol magnitude entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Populate GDP q/q's 10 magnitude entries

**Files:**
- Modify: `data_layer/event_symbol_magnitude.py` (`_MAGNITUDE_TABLE`)
- Test: `tests/test_event_symbol_magnitude.py` (append)

**Interfaces:** Same shape as Task 2, but a 10-symbol RELEVANT set — GDP q/q's real RELEVANT list is: XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, USDJPY, USDCHF, AUDUSD, NZDUSD. Do NOT include GBPUSD or USDCAD — those are `UNVERIFIED` in Phase 1's own relevance table for GDP q/q, out of this table's scope entirely.

**Research procedure:** Same as Task 2, substituting `'GDP q/q'` and the 10-symbol list above.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_magnitude.py`:

```python
def test_gdp_qq_has_all_10_relevant_magnitude_entries_with_real_shape():
    print("=== GDP q/q: all 10 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("GDP q/q", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"GDP q/q x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_gdp_qq_has_all_10_relevant_magnitude_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 10 real entries**

Add 10 real, cited `("GDP q/q", <symbol>)` entries — exactly the 10-symbol list above, not GBPUSD/USDCAD.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_gdp_qq_has_all_10_relevant_magnitude_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_magnitude.py tests/test_event_symbol_magnitude.py
git commit -m "feat: populate GDP q/q's event-symbol magnitude entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Populate Core PCE Price Index m/m's 12 magnitude entries

**Files:**
- Modify: `data_layer/event_symbol_magnitude.py` (`_MAGNITUDE_TABLE`)
- Test: `tests/test_event_symbol_magnitude.py` (append)

**Interfaces:** Same as Task 2. 12-symbol RELEVANT set: XAUUSD, XAGUSD, US30, US500, NAS100, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD.

**Research procedure:** Same as Task 2, substituting `'Core PCE Price Index m/m'`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_magnitude.py`:

```python
def test_core_pce_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== Core PCE Price Index m/m: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("Core PCE Price Index m/m", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"Core PCE x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_core_pce_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 12 real entries**

Add 12 real, cited `("Core PCE Price Index m/m", <symbol>)` entries.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_core_pce_has_all_12_relevant_magnitude_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_magnitude.py tests/test_event_symbol_magnitude.py
git commit -m "feat: populate Core PCE's event-symbol magnitude entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: Populate ISM Manufacturing PMI's 10 magnitude entries

**Files:**
- Modify: `data_layer/event_symbol_magnitude.py` (`_MAGNITUDE_TABLE`)
- Test: `tests/test_event_symbol_magnitude.py` (append)

**Interfaces:** Same shape as Task 2, but a 10-symbol RELEVANT set — ISM Manufacturing PMI's real RELEVANT list is: XAUUSD, XAGUSD, US30, EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD. Do NOT include US500 or NAS100 — those are `UNVERIFIED` in Phase 1's relevance table for this event type (the exact cells Phase 1's own two fix rounds resolved to honest UNVERIFIED after two independently-disproved external citations), out of this table's scope.

**Research procedure — extra caution on this event type specifically:** Phase 1's ISM Manufacturing PMI task is the one that cost two real fix rounds for citing a news article's date/numbers/driver claim that turned out to be wrong on a big multi-factor trading day. XAUUSD, XAGUSD, and US30's Phase 1 citations for this event type were eventually resolved using internal `scoring/backtest_log.db` evidence rather than an external article — check whether those same internal rows (or others) already contain a usable magnitude figure before reaching for any external source. For the FX majors, apply the same independent-verification discipline as every other task.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_magnitude.py`:

```python
def test_ism_manufacturing_has_all_10_relevant_magnitude_entries_with_real_shape():
    print("=== ISM Manufacturing PMI: all 10 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("ISM Manufacturing PMI", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"ISM Manufacturing PMI x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_ism_manufacturing_has_all_10_relevant_magnitude_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 10 real entries**

Add 10 real, cited `("ISM Manufacturing PMI", <symbol>)` entries — exactly the 10-symbol list above, not US500/NAS100.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_ism_manufacturing_has_all_10_relevant_magnitude_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_magnitude.py tests/test_event_symbol_magnitude.py
git commit -m "feat: populate ISM Manufacturing PMI's event-symbol magnitude entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: Populate ISM Services PMI's 4 magnitude entries

**Files:**
- Modify: `data_layer/event_symbol_magnitude.py` (`_MAGNITUDE_TABLE`)
- Test: `tests/test_event_symbol_magnitude.py` (append)

**Interfaces:** Same shape as Task 2, but a 4-symbol RELEVANT set — ISM Services PMI's real RELEVANT list is only: XAUUSD, EURUSD, GBPUSD, USDJPY. This is the smallest task in the plan.

**Research procedure:** Same as Task 2, substituting `'ISM Services PMI'` and the 4-symbol list above. All 4 of Phase 1's citations for this event type are external-news-based (no internal DB rows exist for ISM Services), independently verified clean in Phase 1's own review — read them directly and classify the tier from the real numbers already there.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_magnitude.py`:

```python
def test_ism_services_has_all_4_relevant_magnitude_entries_with_real_shape():
    print("=== ISM Services PMI: all 4 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
    for symbol in symbols:
        judgment = esm.get_magnitude("ISM Services PMI", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"ISM Services PMI x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_ism_services_has_all_4_relevant_magnitude_entries_with_real_shape -v`
Expected: FAIL with `KeyError`

- [ ] **Step 3: Research and add the 4 real entries**

Add 4 real, cited `("ISM Services PMI", <symbol>)` entries.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_event_symbol_magnitude.py::test_ism_services_has_all_4_relevant_magnitude_entries_with_real_shape -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_symbol_magnitude.py tests/test_event_symbol_magnitude.py
git commit -m "feat: populate ISM Services PMI's event-symbol magnitude entries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: Populate Retail Sales m/m's 10 magnitude entries, then run the generator for the first real time

**Files:**
- Modify: `data_layer/event_symbol_magnitude.py` (`_MAGNITUDE_TABLE`)
- Test: `tests/test_event_symbol_magnitude.py` (append)
- Create (generated): `docs/event-symbol-magnitude.md`

**Interfaces:** Same shape as Task 2, but a 10-symbol RELEVANT set — Retail Sales m/m's real RELEVANT list is: XAUUSD, XAGUSD, US30, US500, EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCAD. Do NOT include NAS100 or USDCHF — those are `UNVERIFIED` in Phase 1's relevance table for this event type, out of scope.

This is the LAST of the 9 population tasks — after this, all 94 real entries exist, and the generator can be run for real for the first time.

**Research procedure:** Same as Task 2, substituting `'Retail Sales m/m'` and the 10-symbol list above.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_event_symbol_magnitude.py`:

```python
def test_retail_sales_has_all_10_relevant_magnitude_entries_with_real_shape():
    print("=== Retail Sales m/m: all 10 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("Retail Sales m/m", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"Retail Sales m/m x {symbol} has an empty citation"
    print("PASS\n")
```

Add its call to `__main__`, and also add the completeness tests below to the same file:

```python
def test_every_one_of_the_94_real_relevant_combinations_is_present():
    print("=== Completeness: all 94 real RELEVANT (event_type, symbol) combinations from Phase 1 are present ===")
    missing = []
    total_relevant = 0
    for event_type in esr.EVENT_TYPES:
        for symbol in esr.SYMBOLS:
            if esr.get_relevance(event_type, symbol).status != esr.RelevanceStatus.RELEVANT:
                continue
            total_relevant += 1
            try:
                esm.get_magnitude(event_type, symbol)
            except KeyError:
                missing.append((event_type, symbol))
    assert total_relevant == 94, f"expected exactly 94 real RELEVANT pairs in Phase 1's table, found {total_relevant} -- Phase 1's own table changed, or this count is stale"
    assert missing == [], f"missing {len(missing)} of 94 real RELEVANT entries: {missing[:5]}{'...' if len(missing) > 5 else ''}"
    print("PASS\n")


def test_magnitude_table_has_exactly_94_entries_no_stray_keys():
    print("=== Completeness: _MAGNITUDE_TABLE has exactly 94 entries -- no stray/typo'd keys ===")
    assert len(esm._MAGNITUDE_TABLE) == 94, f"expected exactly 94 entries, found {len(esm._MAGNITUDE_TABLE)}"
    print("PASS\n")


def test_no_magnitude_key_is_a_non_relevant_phase1_pair():
    print("=== Scope boundary: every key in _MAGNITUDE_TABLE is RELEVANT in Phase 1's own table ===")
    bad = [key for key in esm._MAGNITUDE_TABLE if esr.get_relevance(*key).status != esr.RelevanceStatus.RELEVANT]
    assert bad == [], f"found {len(bad)} magnitude entries for a pair that isn't RELEVANT in Phase 1: {bad}"
    print("PASS\n")
```

Add these three new tests' calls to `__main__` as well.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_event_symbol_magnitude.py -v`
Expected: `test_retail_sales_has_all_10_relevant_magnitude_entries_with_real_shape` FAILs with `KeyError`; the three new completeness tests FAIL too (missing entries — Retail Sales m/m's 10 aren't populated yet, so `total_relevant == 94` may already hold but `missing` will list Retail Sales m/m's 10 pairs, and `len(_MAGNITUDE_TABLE)` will be 84, not 94)

- [ ] **Step 3: Research and add the 10 real entries**

Add 10 real, cited `("Retail Sales m/m", <symbol>)` entries — exactly the 10-symbol list above, not NAS100/USDCHF.

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest tests/test_event_symbol_magnitude.py -v`
Expected: all pass, including the three completeness tests (94/94 present, `len == 94`, no stray keys)

- [ ] **Step 5: Generate the real doc for the first time and run its drift-guard test**

Run: `python scripts/generate_event_symbol_magnitude_doc.py`
Expected: `Wrote .../docs/event-symbol-magnitude.md`

Run: `python -m pytest tests/test_generate_event_symbol_magnitude_doc.py -v`
Expected: PASS (the drift-guard test now has a real committed file to compare against)

- [ ] **Step 6: Run the full project suite**

Run: `python -m pytest -q`
Expected: all tests pass, including every test added across this plan

- [ ] **Step 7: Commit**

```bash
git add data_layer/event_symbol_magnitude.py tests/test_event_symbol_magnitude.py docs/event-symbol-magnitude.md tests/test_generate_event_symbol_magnitude_doc.py
git commit -m "feat: populate Retail Sales m/m's event-symbol magnitude entries, generate the real doc

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Final step (whole-plan, not a task)

After Task 10, update `docs/feature-inventory-2026-09-11.md` per its own standing maintenance rule: a new row noting the event-symbol magnitude grid is shipped (phase 2 of 3 — live wiring, phase 3, remains explicitly deferred), where it lives (`data_layer/event_symbol_magnitude.py`, `docs/event-symbol-magnitude.md`), the real tier distribution (LOW/MEDIUM/HIGH/UNVERIFIED counts out of 94), and — honestly — that the LOW/MEDIUM/HIGH boundary values themselves are a reasoned starting ruler, not independently re-derived from this project's own historical data, per the spec's own explicit caveat.
