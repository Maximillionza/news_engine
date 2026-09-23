# Event → Symbol Relevance/Magnitude Live Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the shipped `event_symbol_relevance.py` and `event_symbol_magnitude.py` reference tables into the live confidence-downgrade mechanism and dashboard, for the first time.

**Architecture:** A new pure-mapping module resolves a live calendar title to its methodology label. `predictions_service.py` gains a second, independent downgrade trigger — reusing the exact same `_downgrade_one_tier()` ceiling the existing exogenous-shock trigger already uses — plus a new, separate advisory field. The JS view-model/template layer gains one new badge, mirroring the existing `tier1_confidence_downgrade` badge's exact plumbing end to end.

**Tech Stack:** Python 3 (`dataclasses`, `enum`), pytest, vanilla JS (`lit-html`), existing `card.test.js` test harness.

**Spec:** `docs/superpowers/specs/2026-09-17-live-wiring-design.md`

## Global Constraints

- `predicted_direction` is never touched by any code path in this feature.
- This is a discrete, event-triggered read at prediction-build time — never a continuously-recomputed score.
- Never edit `data_layer/event_symbol_relevance.py` or `data_layer/event_symbol_magnitude.py` — only read via `get_relevance()` / `get_magnitude()`.
- `UNVERIFIED` (either table) and a `KeyError` from either lookup (an unkeyed pair) are both treated as neutral — no downgrade, no badge. Never presented as a confident finding, never silently guessed either.
- Scope is only the 12 symbols × 9 event types (14 mapped calendar titles) both tables cover. Anything else (unmapped title, untracked symbol, unkeyed pair) is simply not looked up — behavior identical to today.
- The one-tier floor and never-compounds-past-one-tier rule is shared, not duplicated, between the existing exogenous-shock trigger and this new trigger — both route through the same `_downgrade_one_tier()` function and the same single `tier1_confidence_downgrade` output field.
- `tier1_confidence_downgrade` is only ever computed when `event["actual"] is None` (a settled result never gets speculative context stamped onto it) — this existing gate is unchanged and applies to the new trigger too.

---

### Task 1: Event title → methodology label mapping

**Files:**
- Create: `data_layer/event_title_mapping.py`
- Test: `tests/test_event_title_mapping.py`

**Interfaces:**
- Produces: `EVENT_TITLE_TO_METHODOLOGY: dict[str, str]`, `resolve_methodology_label(calendar_title: str) -> str | None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_event_title_mapping.py
from data_layer.event_title_mapping import EVENT_TITLE_TO_METHODOLOGY, resolve_methodology_label
from data_layer.event_symbol_relevance import EVENT_TYPES


def test_every_mapped_methodology_label_is_a_real_event_type():
    for methodology_label in EVENT_TITLE_TO_METHODOLOGY.values():
        assert methodology_label in EVENT_TYPES


def test_mapping_has_exactly_14_entries():
    assert len(EVENT_TITLE_TO_METHODOLOGY) == 14


def test_resolve_methodology_label_for_all_14_real_titles():
    expected = {
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
    for calendar_title, methodology_label in expected.items():
        assert resolve_methodology_label(calendar_title) == methodology_label


def test_resolve_methodology_label_returns_none_for_unmapped_title():
    assert resolve_methodology_label("Unemployment Claims") is None
    assert resolve_methodology_label("") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_event_title_mapping.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_layer.event_title_mapping'`

- [ ] **Step 3: Write the implementation**

```python
# data_layer/event_title_mapping.py
"""
Maps a live calendar event title (webapp/store.py's `event["title"]`, as
matched by the tier1-cpi-ppi-autoresearch scheduled task's own Step 1
exact-title list) to the methodology label both data_layer/
event_symbol_relevance.py and data_layer/event_symbol_magnitude.py key
their tables on. Neither table is keyed by exact calendar title -- both
group several real titles under one methodology row (see both tables'
own module docstrings for the same grouping) -- so this mapping must
resolve a live title to its row key before either table can be
consulted (docs/superpowers/specs/2026-09-17-live-wiring-design.md).
"""
from __future__ import annotations

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
    a mapping for an unrecognized title -- unmapped means "not looked up
    at all," same as an untracked symbol.
    """
    return EVENT_TITLE_TO_METHODOLOGY.get(calendar_title)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_event_title_mapping.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add data_layer/event_title_mapping.py tests/test_event_title_mapping.py
git commit -m "feat: add calendar-title-to-methodology-label mapping for live wiring"
```

---

### Task 2: Relevance/magnitude lookup helper in `predictions_service.py`

Builds the read-only lookup helper this phase's second downgrade trigger
uses. Kept as its own task so its neutral-on-`KeyError`/`UNVERIFIED`
behavior gets its own focused test cycle before it's wired into the
larger per-event loop in Task 3.

**Files:**
- Modify: `webapp/predictions_service.py`
- Test: `tests/test_webapp_predictions_service.py` (create if it does not already exist — check first with `Read tests/test_webapp_predictions_service.py`; if it exists, add to it)

**Interfaces:**
- Consumes: `data_layer.event_title_mapping.resolve_methodology_label(calendar_title: str) -> str | None` (Task 1); `data_layer.event_symbol_relevance.get_relevance(event_type: str, symbol: str) -> RelevanceJudgment` and `RelevanceStatus` (existing); `data_layer.event_symbol_magnitude.get_magnitude(event_type: str, symbol: str) -> MagnitudeJudgment` and `MagnitudeTier` (existing)
- Produces: `_relevance_magnitude_read(calendar_title: str, symbol: str) -> Optional[str]` — returns one of `"not_relevant"`, `"low_magnitude"`, or `None` (neutral: unmapped title, `UNVERIFIED` either table, or unkeyed pair). This return value is what Task 3's downgrade trigger and badge both branch on.

- [ ] **Step 1: Write the failing tests**

First check whether `tests/test_webapp_predictions_service.py` exists:

```bash
ls tests/test_webapp_predictions_service.py
```

If it does not exist, create it with this content (imports at top).
If it does exist, append these test functions and add the import line
to its existing import block.

```python
# tests/test_webapp_predictions_service.py (new or appended)
from webapp.predictions_service import _relevance_magnitude_read


def test_relevance_magnitude_read_not_relevant_case(monkeypatch):
    # Synthetic NOT_RELEVANT fixture -- no real cell in the shipped table
    # is NOT_RELEVANT (Phase 1 shipped 0 NOT_RELEVANT cells), so this
    # patches get_relevance() to return one for this test only, per the
    # spec's explicit note that this case needs a synthetic fixture.
    from data_layer.event_symbol_relevance import RelevanceJudgment, RelevanceStatus
    import webapp.predictions_service as svc

    def fake_get_relevance(event_type, symbol):
        assert event_type == "CPI m/m"
        assert symbol == "XAUUSD"
        return RelevanceJudgment(RelevanceStatus.NOT_RELEVANT, "synthetic test fixture")

    monkeypatch.setattr(svc, "get_relevance", fake_get_relevance)
    result = _relevance_magnitude_read("CPI m/m", "XAUUSD")
    assert result == "not_relevant"


def test_relevance_magnitude_read_low_magnitude_case():
    # Real shipped cell: ("Retail Sales m/m", "USDJPY") is a real LOW-tier
    # entry per docs/event-symbol-magnitude.md -- verify against the real
    # table directly rather than mocking, since this is a real shipped case.
    from data_layer.event_symbol_relevance import get_relevance, RelevanceStatus
    from data_layer.event_symbol_magnitude import get_magnitude, MagnitudeTier
    assert get_relevance("Retail Sales m/m", "USDJPY").status == RelevanceStatus.RELEVANT
    assert get_magnitude("Retail Sales m/m", "USDJPY").tier == MagnitudeTier.LOW
    result = _relevance_magnitude_read("Retail Sales m/m", "USDJPY")
    assert result == "low_magnitude"


def test_relevance_magnitude_read_relevant_medium_or_high_is_neutral():
    # Real shipped cell: ("CPI m/m", "XAUUSD") is RELEVANT + MEDIUM.
    result = _relevance_magnitude_read("CPI m/m", "XAUUSD")
    assert result is None


def test_relevance_magnitude_read_unverified_relevance_is_neutral():
    # A real UNVERIFIED relevance cell exists in the shipped table --
    # find one live rather than hardcoding a guess at which pair.
    from data_layer.event_symbol_relevance import EVENT_TYPES, SYMBOLS, get_relevance, RelevanceStatus
    unverified_pair = None
    for event_type in EVENT_TYPES:
        for symbol in SYMBOLS:
            if get_relevance(event_type, symbol).status == RelevanceStatus.UNVERIFIED:
                unverified_pair = (event_type, symbol)
                break
        if unverified_pair:
            break
    assert unverified_pair is not None, "expected at least one real UNVERIFIED relevance cell"
    result = _relevance_magnitude_read(*unverified_pair)
    assert result is None


def test_relevance_magnitude_read_unverified_magnitude_is_neutral():
    # A real UNVERIFIED magnitude cell exists in the shipped table (9 of
    # them) -- find one live among RELEVANT pairs rather than guessing.
    from data_layer.event_symbol_relevance import EVENT_TYPES, SYMBOLS, get_relevance, RelevanceStatus
    from data_layer.event_symbol_magnitude import get_magnitude, MagnitudeTier
    unverified_pair = None
    for event_type in EVENT_TYPES:
        for symbol in SYMBOLS:
            if get_relevance(event_type, symbol).status != RelevanceStatus.RELEVANT:
                continue
            if get_magnitude(event_type, symbol).tier == MagnitudeTier.UNVERIFIED:
                unverified_pair = (event_type, symbol)
                break
        if unverified_pair:
            break
    assert unverified_pair is not None, "expected at least one real UNVERIFIED magnitude cell"
    result = _relevance_magnitude_read(*unverified_pair)
    assert result is None


def test_relevance_magnitude_read_unmapped_title_is_neutral():
    result = _relevance_magnitude_read("Unemployment Claims", "XAUUSD")
    assert result is None


def test_relevance_magnitude_read_unkeyed_pair_is_neutral():
    # "ISM Services PMI" only has real table entries for XAUUSD/EURUSD/
    # GBPUSD/USDJPY (Phase 1's own scoped population) -- US30 is a
    # mapped title + tracked symbol whose pair is genuinely absent from
    # both tables (KeyError), not UNVERIFIED.
    result = _relevance_magnitude_read("ISM Services PMI", "US30")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_webapp_predictions_service.py -v -k relevance_magnitude_read`
Expected: FAIL with `ImportError: cannot import name '_relevance_magnitude_read'`

- [ ] **Step 3: Write the implementation**

Add these imports near the top of `webapp/predictions_service.py`, alongside the existing `from data_layer.exposure import is_exposed` line (line 37):

```python
from data_layer.event_title_mapping import resolve_methodology_label
from data_layer.event_symbol_relevance import get_relevance, RelevanceStatus
from data_layer.event_symbol_magnitude import get_magnitude, MagnitudeTier
```

Add this function immediately after `_first_exposing_shock()` (after line 97, before `def _article_prediction_dict`):

```python
def _relevance_magnitude_read(calendar_title: str, symbol: str) -> Optional[str]:
    """
    Resolves calendar_title to its methodology label and consults both
    reference tables (docs/superpowers/specs/2026-09-17-live-wiring-design.md).
    Returns "not_relevant" (real NOT_RELEVANT relevance judgment),
    "low_magnitude" (RELEVANT + real LOW magnitude judgment), or None
    for every neutral case: unmapped title, UNVERIFIED in either table,
    an unkeyed (methodology_label, symbol) pair (KeyError -- a real,
    expected case, not a bug to raise on), or RELEVANT + MEDIUM/HIGH.
    Never fabricates a result for a pair it doesn't recognize.
    """
    methodology_label = resolve_methodology_label(calendar_title)
    if methodology_label is None:
        return None
    try:
        relevance = get_relevance(methodology_label, symbol)
    except KeyError:
        return None
    if relevance.status == RelevanceStatus.NOT_RELEVANT:
        return "not_relevant"
    if relevance.status != RelevanceStatus.RELEVANT:
        return None  # UNVERIFIED -- neutral, not evidence of unimportant
    try:
        magnitude = get_magnitude(methodology_label, symbol)
    except KeyError:
        return None
    if magnitude.tier == MagnitudeTier.LOW:
        return "low_magnitude"
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_webapp_predictions_service.py -v -k relevance_magnitude_read`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add webapp/predictions_service.py tests/test_webapp_predictions_service.py
git commit -m "feat: add relevance/magnitude live-lookup helper to predictions_service"
```

---

### Task 3: Second downgrade trigger + `relevance_magnitude_note` field

Wires `_relevance_magnitude_read()` (Task 2) into the same per-event loop
that already computes `tier1_confidence_downgrade` from exogenous shocks,
sharing the one-tier ceiling, and adds a new advisory output field the
badge (Task 4) will render from.

**Files:**
- Modify: `webapp/predictions_service.py:419-437` (the existing downgrade block) and `:459-477` (the event dict this block feeds)
- Test: `tests/test_webapp_predictions_service.py`

**Interfaces:**
- Consumes: `_relevance_magnitude_read(calendar_title, symbol) -> Optional[str]` (Task 2); existing `exposing_shock`, `tier1_prediction`, `_downgrade_one_tier()`, `event["actual"]`, `event["title"]`, `ticker`
- Produces: new dict key on each event entry, `"relevance_magnitude_note"`, one of `"not_relevant"`, `"low_magnitude"`, or `None` — same three values `_relevance_magnitude_read()` returns, passed straight through so Task 4's JS layer can render the correct badge text without re-deriving it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webapp_predictions_service.py`. These test the full `build_predictions_payload()` integration, so check the existing test file (or `tests/test_webapp_app.py`, which the spec's Task 2 originally extended for the exposure feature) for the exact fixture/helper pattern used to construct a minimal calendar event + symbol + backtest DB row, and follow that same pattern here rather than inventing a new one. The shape below shows the assertions required; adapt the setup calls to match whatever fixture helpers that existing file already provides for constructing a tier1 prediction row and a calendar event.

```python
def test_not_relevant_pair_downgrades_one_tier_via_relevance_magnitude(
    predictions_service_fixture,  # replace with the real fixture name used by neighboring tests in this file
):
    # Uses the synthetic NOT_RELEVANT monkeypatch technique from Task 2's
    # test -- no real NOT_RELEVANT cell is shipped -- to prove the trigger
    # fires end-to-end through build_predictions_payload().
    ...
    # Build one tracked symbol (XAUUSD), one event titled "CPI m/m",
    # a Certain-confidence tier1 prediction, actual=None, no exogenous
    # shock today. Monkeypatch get_relevance for ("CPI m/m", "XAUUSD")
    # to NOT_RELEVANT.
    # Assert: result event's tier1_confidence_downgrade["displayed_confidence"] == "Likely"
    # Assert: result event's relevance_magnitude_note == "not_relevant"
    # Assert: result event's direction / predicted_direction fields are unchanged from the tier1 prediction's own values


def test_low_magnitude_pair_downgrades_one_tier(predictions_service_fixture):
    # Real shipped cell: ("Retail Sales m/m", "USDJPY") is RELEVANT+LOW.
    # Build event titled "Retail Sales m/m", symbol USDJPY, Certain
    # confidence, actual=None, no exogenous shock today.
    # Assert: tier1_confidence_downgrade["displayed_confidence"] == "Likely"
    # Assert: relevance_magnitude_note == "low_magnitude"


def test_relevance_magnitude_trigger_does_not_compound_with_shock_trigger(
    predictions_service_fixture,
):
    # Both a real exogenous shock (exposing this symbol) AND a real
    # NOT_RELEVANT/LOW_MAGNITUDE pair fire for the same event/symbol.
    # Assert: displayed_confidence is downgraded exactly ONE tier, not two
    # (e.g. Certain -> Likely, never Certain -> Guessing).


def test_neutral_relevance_magnitude_case_produces_no_note_and_no_extra_downgrade(
    predictions_service_fixture,
):
    # Real shipped cell: ("CPI m/m", "XAUUSD") is RELEVANT+MEDIUM -- no
    # exogenous shock today either.
    # Assert: relevance_magnitude_note is None
    # Assert: tier1_confidence_downgrade is None


def test_settled_event_never_gets_relevance_magnitude_downgrade(
    predictions_service_fixture,
):
    # Same NOT_RELEVANT setup as the first test, but event["actual"] is
    # NOT None (a settled result).
    # Assert: tier1_confidence_downgrade is None
    # Assert: relevance_magnitude_note may still be computed (it's not
    # gated on actual/None -- it's an advisory fact about the pair, not a
    # speculative-context stamp) -- confirm the plan's own Task 4 design:
    # the note key equals whatever _relevance_magnitude_read returns
    # regardless of the actual/None gate, ONLY the downgrade dict itself
    # is gated. Assert relevance_magnitude_note == "not_relevant" still.
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_webapp_predictions_service.py -v -k "downgrades_one_tier or does_not_compound or no_note_and_no_extra or never_gets_relevance"`
Expected: FAIL — either a collection error (fixture doesn't exist yet, adapt per Step 1's note) or `AssertionError` since `relevance_magnitude_note` doesn't exist on the event dict yet.

- [ ] **Step 3: Write the implementation**

Replace the existing block at lines 419-437 of `webapp/predictions_service.py`:

```python
            # Confidence-only downgrade (never predicted_direction, never
            # the stored Tier1Prediction row) applied fresh per request
            # when this SPECIFIC instrument (via its symbol_class) is
            # exposed to at least one of today's real exogenous shocks —
            # per docs/superpowers/specs/2026-09-12-layer1-layer2-exposure-design.md,
            # replacing Batch 6's uniform "any shock downgrades every
            # tracked instrument" rule with a real, cited, per-instrument
            # exposure check. event["actual"] is None is unchanged from
            # Batch 6 -- a settled result never gets today's speculative
            # exogenous-shock context stamped onto it.
            exposing_shock = _first_exposing_shock(todays_shocks, symbol_class.symbol_class)
            tier1_confidence_downgrade = None
            if tier1_prediction is not None and exposing_shock is not None and event["actual"] is None:
                tier1_confidence_downgrade = {
                    "original_confidence": tier1_prediction["confidence"],
                    "displayed_confidence": _downgrade_one_tier(tier1_prediction["confidence"]),
                    "reason": exposing_shock.headline_cause,
                    "series": exposing_shock.series,
                }
```

with:

```python
            # Confidence-only downgrade (never predicted_direction, never
            # the stored Tier1Prediction row) applied fresh per request
            # when this SPECIFIC instrument (via its symbol_class) is
            # exposed to at least one of today's real exogenous shocks —
            # per docs/superpowers/specs/2026-09-12-layer1-layer2-exposure-design.md,
            # replacing Batch 6's uniform "any shock downgrades every
            # tracked instrument" rule with a real, cited, per-instrument
            # exposure check. event["actual"] is None is unchanged from
            # Batch 6 -- a settled result never gets today's speculative
            # exogenous-shock context stamped onto it.
            exposing_shock = _first_exposing_shock(todays_shocks, symbol_class.symbol_class)

            # Phase 3 (docs/superpowers/specs/2026-09-17-live-wiring-design.md):
            # a second, independent downgrade trigger reading the shipped
            # event_symbol_relevance/event_symbol_magnitude reference
            # tables. relevance_magnitude_note is computed unconditionally
            # (an advisory fact about this event/symbol pair, not a
            # speculative-context stamp) so the dashboard badge can render
            # even for a settled event; the downgrade itself stays gated
            # on event["actual"] is None exactly like the shock trigger.
            relevance_magnitude_note = _relevance_magnitude_read(event["title"], ticker)
            relevance_magnitude_downgrades = relevance_magnitude_note in ("not_relevant", "low_magnitude")

            tier1_confidence_downgrade = None
            if (tier1_prediction is not None and event["actual"] is None
                    and (exposing_shock is not None or relevance_magnitude_downgrades)):
                if exposing_shock is not None:
                    reason = exposing_shock.headline_cause
                    series = exposing_shock.series
                else:
                    reason = (
                        "not confirmed relevant to this symbol" if relevance_magnitude_note == "not_relevant"
                        else "low expected impact on this symbol"
                    )
                    series = None
                tier1_confidence_downgrade = {
                    "original_confidence": tier1_prediction["confidence"],
                    "displayed_confidence": _downgrade_one_tier(tier1_prediction["confidence"]),
                    "reason": reason,
                    "series": series,
                }
```

Then, in the `entry["events"].append({...})` block (around line 459-477), add the new field immediately after the existing `"tier1_confidence_downgrade": tier1_confidence_downgrade,` line:

```python
                "tier1_confidence_downgrade": tier1_confidence_downgrade,
                "relevance_magnitude_note": relevance_magnitude_note,
```

Note on the shared ceiling: `exposing_shock is not None or relevance_magnitude_downgrades` fires the downgrade block if *either* trigger is true, but the block always applies exactly one `_downgrade_one_tier()` call — this is what prevents compounding. If `exposing_shock` is set, it takes display precedence for `reason`/`series` (arbitrary but stable choice, same as the existing `_first_exposing_shock()`'s own "first is a display-stability choice only" comment) — which trigger is shown is not load-bearing, only that the tier drops by exactly one.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_webapp_predictions_service.py -v`
Expected: PASS (all tests in the file, including Task 2's)

- [ ] **Step 5: Run the full existing test suite to confirm no regression**

Run: `pytest tests/ -v -k "predictions_service or webapp_app"`
Expected: PASS — the existing exogenous-shock downgrade tests (from the exposure-grid feature) must still pass unchanged, since the shock branch's own behavior (reason/series from `exposing_shock`) is preserved verbatim when `exposing_shock is not None`.

- [ ] **Step 6: Commit**

```bash
git add webapp/predictions_service.py tests/test_webapp_predictions_service.py
git commit -m "feat: wire relevance/magnitude tables into tier1_confidence_downgrade"
```

---

### Task 4: Dashboard badge — view-model + template

Mirrors `tier1_confidence_downgrade`'s existing plumbing (view-model
builder → template function → wired into both card faces and the
other-events row) for the new `relevance_magnitude_note` field from
Task 3.

**Files:**
- Modify: `webapp/static/js/dashboard/card-view-model.js`
- Modify: `webapp/static/js/dashboard/card.js`
- Test: `webapp/static/js/dashboard/card.test.js`

**Interfaces:**
- Consumes: `next.relevance_magnitude_note` (Task 3's new payload field, one of `"not_relevant"`, `"low_magnitude"`, `null`)
- Produces: `buildRelevanceMagnitudeNoteViewModel(note) -> {label: string} | null` (JS); `relevanceMagnitudeNoteTemplate(vm)` and `otherEventRelevanceMagnitudeMarkerTemplate(label)` (JS); `hasRelevanceMagnitudeNote`/`relevanceMagnitudeNoteLabel` fields on the other-events row view-model

- [ ] **Step 1: Write the failing tests**

Read `webapp/static/js/dashboard/card.test.js` first to find the exact existing test pattern for `buildTier1ConfidenceDowngradeViewModel` / `tier1ConfidenceDowngradeTemplate` (search the file for `tier1ConfidenceDowngrade`) and mirror that pattern exactly — same assertion style, same import style. Add these test cases to that file:

```javascript
import { buildRelevanceMagnitudeNoteViewModel } from "./card-view-model.js";
import { relevanceMagnitudeNoteTemplate, otherEventRelevanceMagnitudeMarkerTemplate } from "./card.js";

test("buildRelevanceMagnitudeNoteViewModel returns null for null note", () => {
  expect(buildRelevanceMagnitudeNoteViewModel(null)).toBeNull();
});

test("buildRelevanceMagnitudeNoteViewModel labels not_relevant correctly", () => {
  expect(buildRelevanceMagnitudeNoteViewModel("not_relevant")).toEqual({
    label: "Not confirmed relevant to this symbol",
  });
});

test("buildRelevanceMagnitudeNoteViewModel labels low_magnitude correctly", () => {
  expect(buildRelevanceMagnitudeNoteViewModel("low_magnitude")).toEqual({
    label: "Low expected impact",
  });
});

test("buildRelevanceMagnitudeNoteViewModel labels unverified correctly", () => {
  expect(buildRelevanceMagnitudeNoteViewModel("unverified")).toEqual({
    label: "Relevance/magnitude not yet researched",
  });
});

test("relevanceMagnitudeNoteTemplate renders empty for null vm", () => {
  const html = relevanceMagnitudeNoteTemplate(null).strings.join("");
  expect(html.trim()).toBe("");
});

test("relevanceMagnitudeNoteTemplate renders the label for a real vm", () => {
  const rendered = String(relevanceMagnitudeNoteTemplate({ label: "Low expected impact" }));
  expect(rendered).toContain("Low expected impact");
});

test("otherEventRelevanceMagnitudeMarkerTemplate renders nothing when no note", () => {
  const rendered = String(otherEventRelevanceMagnitudeMarkerTemplate(null));
  expect(rendered.trim()).toBe("");
});

test("otherEventRelevanceMagnitudeMarkerTemplate renders the label when present", () => {
  const rendered = String(otherEventRelevanceMagnitudeMarkerTemplate("Not confirmed relevant to this symbol"));
  expect(rendered).toContain("Not confirmed relevant to this symbol");
});
```

If the existing test file's assertion style for `lit-html` template output differs from the `.strings.join("")` / `String(...)` pattern shown above (e.g. it uses a render-to-string helper already defined in that file), use the file's own existing helper instead — check the top of `card.test.js` for one before writing these.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx jest webapp/static/js/dashboard/card.test.js -t "RelevanceMagnitude"`
Expected: FAIL — `buildRelevanceMagnitudeNoteViewModel` / `relevanceMagnitudeNoteTemplate` / `otherEventRelevanceMagnitudeMarkerTemplate` are not exported yet.

- [ ] **Step 3: Write the implementation**

In `webapp/static/js/dashboard/card-view-model.js`, add this function immediately after `buildTier1ConfidenceDowngradeViewModel` (after line 62):

```javascript
const RELEVANCE_MAGNITUDE_NOTE_LABELS = {
  not_relevant: "Not confirmed relevant to this symbol",
  low_magnitude: "Low expected impact",
  unverified: "Relevance/magnitude not yet researched",
};

export function buildRelevanceMagnitudeNoteViewModel(note) {
  if (!note) return null;
  const label = RELEVANCE_MAGNITUDE_NOTE_LABELS[note];
  if (!label) return null;
  return { label };
}
```

Still in `card-view-model.js`, find the `buildOtherEventRowViewModel`-equivalent function (the one currently setting `hasDowngrade`/`downgradeDisplayedConfidence` around line 138-139) and add two sibling fields to its returned object:

```javascript
    hasDowngrade: !!e.tier1_confidence_downgrade,
    downgradeDisplayedConfidence: e.tier1_confidence_downgrade?.displayed_confidence ?? null,
    hasRelevanceMagnitudeNote: !!buildRelevanceMagnitudeNoteViewModel(e.relevance_magnitude_note),
    relevanceMagnitudeNoteLabel: buildRelevanceMagnitudeNoteViewModel(e.relevance_magnitude_note)?.label ?? null,
```

Find both places `tier1ConfidenceDowngrade` is built (around lines 210 and 258 — one in the pending-event view model, one in the confirmed-event view model) and add a sibling line immediately after each:

```javascript
    const tier1ConfidenceDowngrade = buildTier1ConfidenceDowngradeViewModel(next.tier1_confidence_downgrade);
    const relevanceMagnitudeNote = buildRelevanceMagnitudeNoteViewModel(next.relevance_magnitude_note);
```

and add `relevanceMagnitudeNote,` to both returned view-model objects, immediately after their existing `tier1ConfidenceDowngrade,` line. For the second occurrence (around line 258, the confirmed-event view model that uses inline calls rather than a local variable), write it as:

```javascript
    tier1ConfidenceDowngrade: buildTier1ConfidenceDowngradeViewModel(next.tier1_confidence_downgrade),
    relevanceMagnitudeNote: buildRelevanceMagnitudeNoteViewModel(next.relevance_magnitude_note),
```

In `webapp/static/js/dashboard/card.js`, add this template function immediately after `tier1ConfidenceDowngradeTemplate` (after line 87):

```javascript
export function relevanceMagnitudeNoteTemplate(vm) {
  if (!vm) return html``;
  return html`<div class="relevance-magnitude-note">
    ⚠ ${vm.label}
  </div>`;
}
```

Add this second function immediately after `otherEventTier1DowngradeMarkerTemplate` (after line 128):

```javascript
export function otherEventRelevanceMagnitudeMarkerTemplate(label) {
  if (!label) return html``;
  return html`<span class="other-event-relevance-magnitude">⚠ ${label}</span>`;
}
```

In `otherEventRowTemplate` (around line 140-148), add the new marker immediately after `otherEventTier1DowngradeMarkerTemplate`:

```javascript
function otherEventRowTemplate(row) {
  return html`<div class="other-event-row">
    <span class="other-event-title">${row.title}${row.whenLabel ? html` <span class="meta-text-sm">(${formatEventDateTime(row.whenLabel)})</span>` : html``}</span>
    ${essenceArticleTemplate(row.essenceArticle)}
    ${otherEventTier1MarkerTemplate(row.tier1Marker)}
    ${otherEventTier1ConflictMarkerTemplate(row.hasConflict)}
    ${otherEventTier1DowngradeMarkerTemplate(row.hasDowngrade, row.downgradeDisplayedConfidence)}
    ${otherEventRelevanceMagnitudeMarkerTemplate(row.relevanceMagnitudeNoteLabel)}
  </div>`;
}
```

Finally, wire `relevanceMagnitudeNoteTemplate` into both card faces immediately after `tier1ConfidenceDowngradeTemplate` — line 223 (pending face):

```javascript
          ${tier1PredictionTemplate(vm.tier1Prediction)}${tier1SentimentConflictTemplate(vm.tier1SentimentConflict)}${tier1ConfidenceDowngradeTemplate(vm.tier1ConfidenceDowngrade)}${relevanceMagnitudeNoteTemplate(vm.relevanceMagnitudeNote)}
```

and line 251 (confirmed face):

```javascript
          ${tier1PredictionTemplate(vm.tier1Prediction)}${tier1SentimentConflictTemplate(vm.tier1SentimentConflict)}${tier1ConfidenceDowngradeTemplate(vm.tier1ConfidenceDowngrade)}${relevanceMagnitudeNoteTemplate(vm.relevanceMagnitudeNote)}
```

Add the CSS class `.relevance-magnitude-note` and `.other-event-relevance-magnitude` to `webapp/static/style.css`, copying the exact declaration block already used for `.tier1-confidence-downgrade` and `.other-event-tier1-downgrade` respectively (same orange warning-badge visual language, per the spec) — find those two existing rules in `style.css` and duplicate each with the new selector name, no other changes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest webapp/static/js/dashboard/card.test.js`
Expected: PASS (all tests in the file, including the 8 new ones)

- [ ] **Step 5: Commit**

```bash
git add webapp/static/js/dashboard/card-view-model.js webapp/static/js/dashboard/card.js webapp/static/style.css webapp/static/js/dashboard/card.test.js
git commit -m "feat: add relevance/magnitude advisory badge to dashboard card"
```

---

### Task 5: Full verification + feature-inventory update

**Files:**
- Modify: `docs/feature-inventory-2026-09-11.md`
- No new source files

**Interfaces:**
- Consumes: everything from Tasks 1-4
- Produces: nothing new — a verification + documentation task

- [ ] **Step 1: Run the full Python test suite**

Run: `pytest tests/ -v`
Expected: PASS, 0 failed. Compare the total passed count against the count recorded in `.superpowers/sdd/2026-09-16-event-symbol-magnitude-grid/progress.md`'s history (701 passed as of Phase 2's completion) — this run should show 701 plus every test added in Tasks 1-4 of this plan (5 + 7 + 5 + 8 = 25 new, so expect 726, though the exact new count depends on how many tests Task 3's integration tests actually end up as once adapted to the real fixture helper — record whatever the real total is, don't force it to match this estimate).

- [ ] **Step 2: Run the full JS test suite**

Run: `npx jest`
Expected: PASS, 0 failed.

- [ ] **Step 3: Live-verify in the Browser pane**

Start the webapp dev server (check `.claude/launch.json` for its configured name; if none exists for this project, run the app's normal local-start command directly and open the Browser pane at its URL). Navigate to the Dashboard tab.

Because a real live event matching one of the 14 mapped titles with a real `NOT_RELEVANT` or `LOW`-magnitude pair may not be firing today, construct one directly the same way prior phases live-verified `tier1_confidence_downgrade`: write a real tier1 prediction row (via the project's existing tier1-prediction DB-write helper, `Certain` confidence, `actual=None`) for a tracked symbol against a real `LOW`-magnitude pair from the shipped table — e.g. `("Retail Sales m/m", "USDJPY")` — for today's date, then reload the dashboard.

Confirm via `read_page` (not just a screenshot) that:
- USDJPY's Retail Sales m/m card shows a downgraded confidence (`Likely`, down from `Certain`) in the existing downgrade badge.
- The card additionally shows the new advisory badge reading "Low expected impact."
- A different tracked symbol/event pair that is `RELEVANT`+`MEDIUM`/`HIGH` (e.g. XAUUSD's CPI m/m) shows neither the downgrade badge nor the new advisory badge (assuming no real exogenous shock is separately live today for XAUUSD — if one is, note it and pick a different neutral comparison pair instead).

Take a screenshot as visual proof after `read_page` confirms the text.

- [ ] **Step 4: Update the feature-inventory doc**

Read `docs/feature-inventory-2026-09-11.md` in full first. Following its own established per-entry format (the same format used for the Phase 1 relevance-grid and Phase 2 magnitude-grid entries already in that file), add a new entry immediately after Phase 2's own entry, describing:
- What shipped: live wiring of both reference tables into `tier1_confidence_downgrade` (second trigger, sharing the existing one-tier ceiling) plus a new, separate advisory badge on the dashboard.
- The title-to-methodology mapping layer (`data_layer/event_title_mapping.py`) this phase added to bridge the two tables' 9 methodology labels to the live system's 14 exact calendar titles.
- The explicit UNVERIFIED/unkeyed-pair-as-neutral rule carried forward from both prior phases.
- Non-goals: no change to either reference table's own content; not a continuously-recomputed score; `predicted_direction` untouched.
- This closes the three-phase event-symbol relevance/magnitude project (Phase 1 relevance → Phase 2 magnitude → Phase 3 live wiring), all three phases now shipped.

- [ ] **Step 5: Commit**

```bash
git add docs/feature-inventory-2026-09-11.md
git commit -m "docs: mark event-symbol relevance/magnitude live wiring shipped in feature inventory"
```
