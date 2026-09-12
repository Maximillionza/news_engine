# Layer1/Layer2 Instrument-Selective Exposure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Batch 6's exogenous-shock confidence downgrade instrument-selective — using real, cited evidence from the `Layer1_Event_to_USD`/`Layer2_Asset_Transmission` workbook sheets — instead of downgrading every tracked instrument's Tier 1 confidence uniformly regardless of what caused the shock.

**Architecture:** A new, small `data_layer/exposure.py` module holds a hand-curated, cited exposure table and a pure `is_exposed()` lookup. `webapp/predictions_service.py`'s downgrade computation switches from "first shock found today" to "all of today's real shocks, checked per instrument" so a non-exposing shock never shadows a real exposing one.

**Tech Stack:** Python, existing `scoring/backtest_store.py`/`webapp/symbols.py` infrastructure — no new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-12-layer1-layer2-exposure-design.md`

## Global Constraints

- `predicted_direction` is never touched by this plan, in any code path — confidence-only, exactly like Batch 6.
- The exposure table is a static, hand-reviewed Python constant — no new database table, no live-fetch dependency.
- Every entry in `_NOT_EXPOSED` must cite the real Layer1/Layer2 workbook row(s) it's built from, directly in a comment above it.
- Only `Certain`/`Likely`-confidence entries are ever honored by `is_exposed()` at runtime; a `Guessing`-confidence entry stays documented but inert.
- The exposure table's keys are `symbol_class` string values from `webapp/symbols.py::classify_symbol()` (`"metal"`, `"index_risk"`, `"fx_usd_base"`, `"fx_usd_quote"`, `"fx_cross"`), never a hardcoded ticker.
- The one-tier floor and never-compounds-past-one-tier rules from Batch 6 are unchanged, just applied per-instrument.

---

### Task 1: `data_layer/exposure.py` — the exposure table and lookup

**Files:**
- Create: `data_layer/exposure.py`
- Test: `tests/test_exposure.py`

**Interfaces:**
- Consumes: nothing new (no imports from other project modules — this file is a pure, standalone lookup).
- Produces: `ExposureJudgment` dataclass (`exposed: bool`, `confidence: str`, `citation: str`), `is_exposed(taxonomy_category: Optional[str], symbol_class: str) -> bool` — Task 2 imports and calls `is_exposed` by exact name.

The real, curated table content below is the result of a full read of all 16 real `Layer1_Event_to_USD` rows and all 14 real `Layer2_Asset_Transmission` rows in `docs/News_Engine_Causation_Matrix_v2.xlsx`, done during this feature's own brainstorming session. Exactly one category has cited evidence of non-exposure for a tracked instrument class — every other `(category, symbol_class)` pair is correctly absent, defaulting to exposed. Read `docs/News_Engine_Causation_Matrix_v2.xlsx`'s `Layer1_Event_to_USD` and `Layer2_Asset_Transmission` sheets yourself (e.g. via `python -c "import openpyxl; wb = openpyxl.load_workbook('docs/News_Engine_Causation_Matrix_v2.xlsx', data_only=True); ...`") to independently confirm the two citations below before committing — this is real evidence a reviewer will re-check against the actual workbook, not a rubber-stamped table.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_exposure.py
"""
Tests for data_layer/exposure.py — pure logic, no DB, no network.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.exposure import ExposureJudgment, is_exposed, _NOT_EXPOSED


def test_none_category_always_exposed():
    print("=== exposure: a None taxonomy_category (unclassified shock) always returns True — zero curated basis to narrow anything ===")
    assert is_exposed(None, "metal") is True
    assert is_exposed(None, "index_risk") is True
    assert is_exposed(None, "fx_usd_base") is True
    print("PASS\n")


def test_unlisted_pair_defaults_exposed():
    print("=== exposure: a (category, symbol_class) pair with no table entry defaults to True — absence of evidence is not evidence of non-exposure ===")
    assert is_exposed("Treasury buyback size/schedule change", "metal") is True
    assert is_exposed("Fed-independence shock", "index_risk") is True
    assert is_exposed("Geopolitical war-driven oil supply shock", "fx_cross") is True
    print("PASS\n")


def test_guessing_confidence_entry_never_honored_at_runtime():
    print("=== exposure: a Guessing-confidence entry is documented but never suppresses exposure — same discipline as POC_Sub_Event_Consolidation staying out of live calc until real evidence exists ===")
    # A synthetic Guessing-confidence entry, constructed ONLY for this test —
    # never added to the real _NOT_EXPOSED table, which contains only
    # Certain/Likely entries per this plan's Global Constraints.
    fake_table = {
        ("Fed Chair transition", "metal"): ExposureJudgment(
            exposed=False, confidence="Guessing", citation="test fixture only, not real evidence",
        ),
    }
    assert is_exposed("Fed Chair transition", "metal", table=fake_table) is True, \
        "a Guessing-confidence entry must be inert at runtime, not suppress exposure"
    print("PASS\n")


def test_real_opec_supply_decision_not_exposed_for_metal_and_index_risk():
    print("=== exposure: the one real, cited entry — OPEC+ supply decisions don't meaningfully touch gold or index confidence — verified via the real _NOT_EXPOSED table, not a fixture ===")
    assert is_exposed("OPEC+ supply decision", "metal") is False
    assert is_exposed("OPEC+ supply decision", "index_risk") is False
    print("PASS\n")


def test_opec_supply_decision_still_exposed_for_fx_classes_no_cited_evidence_there():
    print("=== exposure: OPEC+ supply decisions have NO cited non-exposure evidence for generic FX classes (only USDCAD specifically, which isn't a tracked symbol_class) — must default exposed ===")
    assert is_exposed("OPEC+ supply decision", "fx_usd_base") is True
    assert is_exposed("OPEC+ supply decision", "fx_usd_quote") is True
    print("PASS\n")


def test_real_table_entries_are_all_certain_or_likely():
    print("=== exposure: every entry in the REAL _NOT_EXPOSED table is Certain or Likely confidence — Guessing entries would be silently inert, so none should exist there ===")
    for key, judgment in _NOT_EXPOSED.items():
        assert judgment.confidence in ("Certain", "Likely"), (
            f"{key} has confidence={judgment.confidence!r} — a Guessing entry in the real table "
            f"would be silently inert at runtime; either upgrade it with real evidence or remove it"
        )
    print("PASS\n")


def test_real_table_entries_all_have_a_citation():
    print("=== exposure: every real entry cites its source — no entry without a citation, per this plan's Global Constraints ===")
    for key, judgment in _NOT_EXPOSED.items():
        assert judgment.citation and len(judgment.citation) > 20, f"{key} has no real citation"
    print("PASS\n")


if __name__ == "__main__":
    test_none_category_always_exposed()
    test_unlisted_pair_defaults_exposed()
    test_guessing_confidence_entry_never_honored_at_runtime()
    test_real_opec_supply_decision_not_exposed_for_metal_and_index_risk()
    test_opec_supply_decision_still_exposed_for_fx_classes_no_cited_evidence_there()
    test_real_table_entries_are_all_certain_or_likely()
    test_real_table_entries_all_have_a_citation()
    print("All exposure tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_exposure.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_layer.exposure'`

- [ ] **Step 3: Write the implementation**

```python
# data_layer/exposure.py
"""
Instrument-selective exposure judgments for Tier 2/3 exogenous shocks
(docs/superpowers/specs/2026-09-12-layer1-layer2-exposure-design.md).
Answers: does a detected shock's real, classified category actually
touch a given instrument class's confidence, per the real, dated,
sourced evidence in docs/News_Engine_Causation_Matrix_v2.xlsx's
Layer1_Event_to_USD and Layer2_Asset_Transmission sheets?

This is a strict NARROWING of Batch 6's blanket-downgrade-every-
instrument behavior, never a widening — the default is always
"exposed" (today's safe behavior), and only a real, cited,
Certain-or-Likely-confidence entry below can turn that off for one
specific (category, symbol_class) pair.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExposureJudgment:
    exposed: bool
    confidence: str   # "Certain" | "Likely" | "Guessing" — same 3-tier language as Tier1Prediction elsewhere in this project
    citation: str      # the real Layer1/Layer2 workbook row(s) this judgment is built from


# Keyed by (taxonomy_category, symbol_class). taxonomy_category values
# are exactly scoring/backtest_store.py's _VALID_TAXONOMY_CATEGORIES's 8
# strings (or None, for an unclassified real shock). symbol_class values
# are whatever webapp/symbols.py's classify_symbol() can produce today
# ("metal", "index_risk", "fx_usd_base", "fx_usd_quote", "fx_cross") or
# adds for a future tracked symbol.
#
# Absence of a pair here means exposed=True (the safe default) — a pair
# only belongs here when real, dated evidence says this category's
# documented transmission mechanism does NOT meaningfully touch this
# instrument class. This table intentionally starts small: most
# categories have real evidence of what they DO affect, not sourced
# evidence of what they DON'T — and "no evidence found" is never treated
# as "evidence of no effect."
_NOT_EXPOSED: dict[tuple[str, str], ExposureJudgment] = {
    # Layer1_Event_to_USD, "OPEC+ production increase (Nov 2025 supply)"
    # row: "+137,000 b/d increase ... Brent fell from ~$70 to $65/bbl on
    # the day ... direct USD/DXY reaction not quantified in sourcing
    # found, flagged rather than assumed" — i.e. no real evidence this
    # specific OPEC+ supply-increase event moved broad USD/gold/equities
    # the way Treasury-buyback, Fed-independence, or shutdown shocks
    # demonstrably do elsewhere in the same sheet.
    #
    # Layer2_Asset_Transmission, "Oil (WTI/Brent)" row makes this
    # explicit and general, not just a one-off absence of sourcing: "In
    # practice this channel is usually secondary to supply/demand
    # headlines — the Oct 5 2025 OPEC+ decision moved Brent on a pure
    # supply signal, not a USD move." That row's own confidence tag:
    # "Certain on the OPEC+ instance; Likely (not separately sourced)
    # that the USD-mechanical channel is secondary in general" — hence
    # Likely here, not Certain, since it generalizes one real instance
    # into a category-wide judgment.
    ("OPEC+ supply decision", "metal"): ExposureJudgment(
        exposed=False, confidence="Likely",
        citation=(
            "Layer1_Event_to_USD 'OPEC+ production increase (Nov 2025 supply)': "
            "'direct USD/DXY reaction not quantified in sourcing found, flagged rather than assumed'. "
            "Layer2_Asset_Transmission 'Oil (WTI/Brent)': 'In practice this channel is usually secondary "
            "to supply/demand headlines - the Oct 5 2025 OPEC+ decision moved Brent on a pure supply "
            "signal, not a USD move.' Confidence: 'Certain on the OPEC+ instance; Likely (not separately "
            "sourced) that the USD-mechanical channel is secondary in general.'"
        ),
    ),
    ("OPEC+ supply decision", "index_risk"): ExposureJudgment(
        exposed=False, confidence="Likely",
        citation=(
            "Same evidence as ('OPEC+ supply decision', 'metal') above — a supply-side oil move with no "
            "demonstrated direct USD/DXY channel has no sourced equity-index channel either in this "
            "workbook; the only real equity-index-moving mechanism documented (Layer2's 'S&P 500 / "
            "Nasdaq / Dow (US30)' row) is about rate-cut framing (soft-landing vs recession-fear), not "
            "oil-supply headlines."
        ),
    ),
    # NOTE: no entry for fx_usd_base/fx_usd_quote/fx_cross under this
    # category. Layer1/Layer2 DO document a real OPEC+-supply channel for
    # USDCAD specifically (CAD is oil-linked) — but USDCAD is a single
    # pair, not the generic fx_usd_base/fx_usd_quote/fx_cross classes
    # classify_symbol() produces for ANY USD pair, and no tracked symbol
    # in this project is USDCAD. Marking the whole fx_usd_quote class
    # "not exposed" here would misapply CAD-specific evidence to every
    # USD pair — stays at the safe default (exposed) instead.
}


def is_exposed(
    taxonomy_category: Optional[str], symbol_class: str,
    table: Optional[dict[tuple[str, str], ExposureJudgment]] = None,
) -> bool:
    """
    True unless a real, cited, Certain-or-Likely-confidence entry in the
    exposure table says otherwise. `table` defaults to the real
    _NOT_EXPOSED table above — the parameter exists only so tests can
    inject a synthetic fixture without touching real, cited data.

    Returns True (exposed, the safe default — same blanket behavior
    Batch 6 already has) when:
    - taxonomy_category is None (an unclassified real shock — zero
      curated basis to narrow anything).
    - the (taxonomy_category, symbol_class) pair has no entry at all
      (absence of evidence is not evidence of non-exposure).
    - the pair HAS an entry, but its confidence is "Guessing" (documented
      for the record, never acted on at runtime — same discipline this
      project already applies to POC_Sub_Event_Consolidation).

    Only returns False when a real entry exists with confidence
    "Certain" or "Likely".
    """
    if table is None:
        table = _NOT_EXPOSED
    if taxonomy_category is None:
        return True
    judgment = table.get((taxonomy_category, symbol_class))
    if judgment is None:
        return True
    if judgment.confidence not in ("Certain", "Likely"):
        return True
    return judgment.exposed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_exposure.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add data_layer/exposure.py tests/test_exposure.py
git commit -m "feat: add instrument-selective exposure lookup for exogenous shocks"
```

---

### Task 2: Wire per-instrument exposure into `webapp/predictions_service.py`

**Files:**
- Modify: `webapp/predictions_service.py`
- Test: `tests/test_webapp_app.py`

**Interfaces:**
- Consumes: `data_layer.exposure.is_exposed` (Task 1). Already-imported `classify_symbol` (`webapp.symbols`), `get_exogenous_shock_for_date` (`scoring.backtest_store`), `DETECTOR_SERIES` (`data_layer.discovery_detector`) — all present in this file already, no new imports needed for those.
- Produces: `_get_todays_exogenous_shocks(backtest_conn) -> list[ExogenousShockRow]` (replaces the old singular `_get_todays_exogenous_shock`), `_first_exposing_shock(shocks, symbol_class) -> Optional[ExogenousShockRow]` — no other task depends on these, but Task 3's live-verify exercises them indirectly through `/api/predictions`.

Read the current `webapp/predictions_service.py` yourself first — the exact line numbers below are current as of this plan's writing but may have shifted by the time you implement; find each piece by name (`_get_todays_exogenous_shock`, `todays_shock`, the `tier1_confidence_downgrade` block) rather than trusting the literal line numbers.

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/test_webapp_app.py, before the `if __name__` block.
# These extend the existing downgrade tests (test_predictions_downgrades_tier1_confidence_when_a_real_shock_is_logged_today/_yesterday,
# test_predictions_no_tier1_confidence_downgrade_without_a_real_shock,
# test_predictions_no_tier1_confidence_downgrade_for_an_already_resolved_event)
# with instrument-selectivity cases. Read those existing tests first for
# the exact _seed_calendar/store/backtest_store fixture pattern this file
# already uses — the tests below follow it exactly.

def test_predictions_no_downgrade_when_the_only_shock_is_a_category_this_instrument_is_not_exposed_to():
    print("=== app: /api/predictions does NOT downgrade XAUUSD's Tier 1 confidence when today's only real shock is an OPEC+ supply decision (real, cited non-exposure for the 'metal' symbol_class) ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            ppi_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ)
            _seed_calendar(db_path, [
                EconomicEvent(title="PPI m/m", country="USD", impact="High",
                               event_time_utc=ppi_time, forecast="0.2%", previous="0.0%", actual=None),
            ])
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            conn.close()

            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time, 0.60, "bearish", 0.5, 100, False,
            )
            backtest_store.record_tier1_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time,
                value="Some call", confidence="Certain", source="BLS/ISM", predicted_direction="bearish",
            )
            today = dt.datetime.now(dt.timezone.utc).date()
            backtest_store.record_exogenous_shock(
                bconn, "DXY", today, move_pct=3.0, stdev_move=2.5,
                taxonomy_category="OPEC+ supply decision",
                headline_cause="Real OPEC+ supply-increase headline", source="Reuters",
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = {e["event_title"]: e for e in resp.get_json()["predictions"][0]["events"]}
            assert events["PPI m/m"]["tier1_confidence_downgrade"] is None, \
                "XAUUSD (symbol_class='metal') is not exposed to an OPEC+ supply decision per the real exposure table — no downgrade expected"
    print("PASS\n")


def test_predictions_downgrades_when_a_default_exposed_category_shock_exists_alongside_a_non_exposing_one():
    print("=== app: two real shocks exist today — one non-exposing category (OPEC+), one default-exposed category (Treasury buyback, no exposure-table entry) — XAUUSD must still be downgraded via the SECOND shock, not silently shadowed by the first ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        backtest_db_path = Path(tmp) / "backtest_log.db"
        with patch.object(store, "DB_PATH", db_path), \
             patch.object(backtest_store, "DB_PATH", backtest_db_path):
            ppi_time = dt.datetime(2026, 9, 10, 12, 30, tzinfo=UTC_TZ)
            _seed_calendar(db_path, [
                EconomicEvent(title="PPI m/m", country="USD", impact="High",
                               event_time_utc=ppi_time, forecast="0.2%", previous="0.0%", actual=None),
            ])
            conn = store.get_connection(db_path)
            store.add_tracked_symbol(conn, "XAUUSD")
            conn.close()

            bconn = backtest_store.get_connection(backtest_db_path)
            backtest_store.record_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time, 0.60, "bearish", 0.5, 100, False,
            )
            backtest_store.record_tier1_prediction(
                bconn, "PPI m/m", "XAUUSD", ppi_time,
                value="Some call", confidence="Certain", source="BLS/ISM", predicted_direction="bearish",
            )
            today = dt.datetime.now(dt.timezone.utc).date()
            # DETECTOR_SERIES order is ["DXY", "UST_BOND", "XAUUSD", "US30"] --
            # DXY's shock (non-exposing OPEC+ category) is checked before
            # UST_BOND's (default-exposed Treasury buyback category), so
            # this exercises the exact "first shock found" shadowing bug
            # the plan's data-flow fix exists to prevent.
            backtest_store.record_exogenous_shock(
                bconn, "DXY", today, move_pct=3.0, stdev_move=2.5,
                taxonomy_category="OPEC+ supply decision",
                headline_cause="Real OPEC+ supply-increase headline", source="Reuters",
            )
            backtest_store.record_exogenous_shock(
                bconn, "UST_BOND", today, move_pct=1.2, stdev_move=2.8,
                taxonomy_category="Treasury buyback size/schedule change",
                headline_cause="Real Treasury buyback cap change headline", source="Bloomberg",
            )
            bconn.close()

            client = webapp_app.app.test_client()
            resp = client.get("/api/predictions")
            events = {e["event_title"]: e for e in resp.get_json()["predictions"][0]["events"]}
            downgrade = events["PPI m/m"]["tier1_confidence_downgrade"]
            assert downgrade is not None, \
                "the Treasury-buyback shock (default exposed, no exposure-table entry) must still downgrade XAUUSD, even though the OPEC+ shock (checked first, per DETECTOR_SERIES order) does not expose it"
            assert downgrade["series"] == "UST_BOND", \
                "the downgrade's shown reason/series must come from the EXPOSING shock (UST_BOND/Treasury buyback), not the non-exposing one (DXY/OPEC+) that happened to be found first"
    print("PASS\n")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_webapp_app.py -v -k "no_downgrade_when_the_only_shock_is_a_category or downgrades_when_a_default_exposed"`
Expected: FAIL — the first test fails because `_get_todays_exogenous_shock()` (singular, current) has no exposure check at all, so it downgrades unconditionally whenever ANY shock exists; the second test's assertion on `downgrade["series"] == "UST_BOND"` fails because the current code always shows whichever shock was found FIRST (`DXY`), not whichever one actually exposes the instrument.

- [ ] **Step 3: Write the implementation**

In `webapp/predictions_service.py`, add the import:

```python
from data_layer.exposure import is_exposed
```

Replace the entire `_get_todays_exogenous_shock` function with:

```python
def _get_todays_exogenous_shocks(backtest_conn: sqlite3.Connection) -> list:
    """
    Every real unresolved shock found for today OR yesterday across
    DETECTOR_SERIES — not just the first (that was Batch 6's behavior;
    see docs/superpowers/specs/2026-09-12-layer1-layer2-exposure-design.md's
    Architecture section for why "first found" became a real bug once
    exposure is instrument-selective: a non-exposing shock checked first
    could otherwise shadow a real exposing one checked later). Fail-open
    (same pattern as build_predictions_payload()'s existing
    get_latest_tier1_predictions_bulk() try/except) -- a broken lookup
    must never take down /api/predictions.

    Both today's AND yesterday's date are checked (today's results
    first, in list order) for the same reason as Batch 6's original
    function: the scheduled research task persists a shock under
    YESTERDAY's date (detect_anomaly() runs against yesterday's
    completed session), so checking only today would silently regress
    that already-fixed write/read mismatch.
    """
    today = dt.datetime.now(dt.timezone.utc).date()
    yesterday = today - dt.timedelta(days=1)
    shocks = []
    try:
        for shock_date in (today, yesterday):
            for series in DETECTOR_SERIES:
                shock = get_exogenous_shock_for_date(backtest_conn, series, shock_date)
                if shock is not None:
                    shocks.append(shock)
    except Exception:
        logger.warning("exogenous shock lookup failed for this cycle", exc_info=True)
    return shocks


def _first_exposing_shock(shocks: list, symbol_class: str):
    """
    The first shock in `shocks` this symbol_class is actually exposed to
    (per data_layer.exposure.is_exposed()), or None if today's real
    shocks exist but none of them expose this instrument class. "First"
    is a display-stability choice only -- the one-tier-never-compounds
    rule means which specific exposing shock gets shown (its series/
    headline_cause) is not load-bearing when multiple would qualify.
    """
    for shock in shocks:
        if is_exposed(shock.taxonomy_category, symbol_class):
            return shock
    return None
```

Change the single call site (currently `todays_shock = _get_todays_exogenous_shock(backtest_conn)`, near the top of `build_predictions_payload()`, alongside the other bulk fetches) to:

```python
    # Same single-shot-per-request, fail-open shape as tier1_by_occurrence
    # above -- computed once here, reused for every symbol/event pair below.
    todays_shocks = _get_todays_exogenous_shocks(backtest_conn)
```

Inside the per-event loop, change the downgrade computation from:

```python
            tier1_confidence_downgrade = None
            if tier1_prediction is not None and todays_shock is not None and event["actual"] is None:
                tier1_confidence_downgrade = {
                    "original_confidence": tier1_prediction["confidence"],
                    "displayed_confidence": _downgrade_one_tier(tier1_prediction["confidence"]),
                    "reason": todays_shock.headline_cause,
                    "series": todays_shock.series,
                }
```

to:

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

`symbol_class` here is the same `SymbolClass` object already computed once per ticker at the top of the outer `for ticker in symbols:` loop (`symbol_class = classify_symbol(ticker)`) — `symbol_class.symbol_class` is its string field (`"metal"`, `"index_risk"`, etc.), already used a few lines above for `_trend_instrument_lean()`. No new per-event computation needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_webapp_app.py -v -k "no_downgrade_when_the_only_shock_is_a_category or downgrades_when_a_default_exposed or tier1_confidence_downgrade"`
Expected: PASS (all downgrade-related tests, old and new)

- [ ] **Step 5: Run the full Python suite to confirm no regressions**

Run: `python -m pytest -q`
Expected: all pass, count unchanged apart from this task's new tests

- [ ] **Step 6: Commit**

```bash
git add webapp/predictions_service.py tests/test_webapp_app.py
git commit -m "feat: make exogenous-shock confidence downgrade instrument-selective"
```

---

### Task 3: Full verification pass + feature-inventory doc update

**Files:**
- Modify: `docs/feature-inventory-2026-09-11.md`

**Interfaces:**
- Consumes: nothing new — this task verifies and documents Tasks 1-2's already-complete work.
- Produces: nothing new.

- [ ] **Step 1: Run the complete automated suite**

```bash
python -m pytest -q
```

Expected: all pass. Confirm the count matches Task 2's Step 5 plus nothing else changed — this feature touches zero JS files, so `npm test`'s count (from the frontend rendering refactor) is unaffected; run it too for completeness:

```bash
npm test
```

Expected: unchanged from before this plan (this plan touches no JS).

- [ ] **Step 2: Live-verify the instrument-selective behavior**

Using the Browser pane tooling: ensure the dashboard is running (`preview_start` with the `news-engine-webapp` launch config, or reload if already running — check for a stray orphaned process first per this project's own history). If no real OPEC+-category shock exists live today (the common case — real anomalies are rare), construct one directly through the real, already-tested `record_exogenous_shock()` function rather than fabricating dashboard state by hand:

```bash
python -c "
import datetime as dt
from scoring import backtest_store as bstore
conn = bstore.get_connection(bstore.DB_PATH)
today = dt.datetime.now(dt.timezone.utc).date()
bstore.record_exogenous_shock(
    conn, 'DXY', today, move_pct=3.0, stdev_move=2.5,
    taxonomy_category='OPEC+ supply decision',
    headline_cause='Live-verification test shock — safe to delete after this check',
    source='manual live-verify',
)
print('inserted for', today)
"
```

Reload the dashboard, find a tracked XAUUSD event with a logged Tier 1 prediction — confirm its card shows NO confidence-downgrade badge (the real OPEC+ exposure-table entry means `metal` is not exposed). Then insert a second shock under a default-exposed category to confirm the mechanism still fires when it should:

```bash
python -c "
import datetime as dt
from scoring import backtest_store as bstore
conn = bstore.get_connection(bstore.DB_PATH)
today = dt.datetime.now(dt.timezone.utc).date()
bstore.record_exogenous_shock(
    conn, 'UST_BOND', today, move_pct=1.2, stdev_move=2.8,
    taxonomy_category='Treasury buyback size/schedule change',
    headline_cause='Live-verification test shock — safe to delete after this check',
    source='manual live-verify',
)
print('inserted for', today)
"
```

Reload again — confirm the SAME card now shows the downgrade badge, with `series: UST_BOND` (the exposing shock), not `DXY` (the non-exposing one). Screenshot both states for the record.

Clean up the two test rows afterward so they don't linger as fake production data:

```bash
python -c "
import datetime as dt
from scoring import backtest_store as bstore
conn = bstore.get_connection(bstore.DB_PATH)
today = dt.datetime.now(dt.timezone.utc).date()
conn.execute(\"DELETE FROM exogenous_shocks WHERE headline_cause LIKE 'Live-verification test shock%'\")
conn.commit()
print('cleaned up')
"
```

- [ ] **Step 3: Update `docs/feature-inventory-2026-09-11.md`**

In §1 (the three-layer overview), find the paragraph ending "...Batch 6 closes that gap for the confidence dimension... it does not close it for the causal-chain/transmission-nuance dimension, which stays future work." Add, directly after it:

```markdown
**Update (2026-09-12):** the confidence-dimension gap itself had an
imprecision Batch 6 left unaddressed — a downgrade applied to EVERY
tracked instrument uniformly, regardless of whether the shock's actual
category has any documented transmission channel to that instrument.
Closed: `data_layer/exposure.py`'s hand-curated, cited exposure table
(built from a full read of `Layer1_Event_to_USD`'s 16 real rows and
`Layer2_Asset_Transmission`'s 14 real rows) now makes the downgrade
instrument-selective — e.g. an OPEC+ supply decision, which this
project's own sourced evidence shows has no demonstrated direct
USD/gold/equity channel, no longer downgrades XAUUSD or US30's Tier 1
confidence. This closes the *confidence* dimension's remaining
imprecision fully; the *causal-chain/transmission-nuance* dimension
(Layer2's other 12 documented instrument classes never wired to
anything live, and Layer2's per-instrument DIRECTIONAL nuance —
`predicted_direction` stays manual-only) remains future work, per the
2026-09-12 design spec's own explicit Non-goals.
```

In §2c's `Discovery_Detector_Spec`/`Mechanism connecting Tier 2/3 context to a Tier 1 verdict's confidence` row area, add a new row directly after the "Mechanism connecting..." row:

```markdown
| Instrument-selective exposure (which categories actually touch which instrument classes) | **Shipped** (2026-09-12) | `data_layer/exposure.py` — `is_exposed()`, hand-curated `_NOT_EXPOSED` table (one real, cited entry as of ship: OPEC+ supply decisions don't meaningfully touch `metal`/`index_risk` confidence, per `Layer2_Asset_Transmission`'s own Oil row). `webapp/predictions_service.py`'s `_get_todays_exogenous_shocks()`/`_first_exposing_shock()` replace Batch 6's single-shock "first found" lookup so a non-exposing shock can never shadow a real exposing one checked later. Default is always exposed — this can only narrow Batch 6's blanket downgrade, never widen it. `Layer1_Event_to_USD`/`Layer2_Asset_Transmission`'s other documented instrument classes (FX majors, silver, Bitcoin, oil, the 2s10s curve) and Layer2's per-instrument DIRECTIONAL nuance remain unwired — out of scope, see the design spec's Non-goals |
```

- [ ] **Step 4: Commit**

```bash
git add docs/feature-inventory-2026-09-11.md
git commit -m "docs: mark instrument-selective exposure shipped in feature inventory"
```

---

## Self-Review Notes (writing-plans skill's own checklist, run before handoff)

**Spec coverage:** All 3 of the spec's Architecture sections have a task — the exposure lookup (Task 1), the data-flow change from first-found to all-shocks-per-instrument (Task 2), and testing/documentation (Task 3, plus tests embedded in Tasks 1-2 per the spec's own Testing section). The spec's Non-goals (no direction change, no new DB table, no live-fetch, no detection/persistence change, no wiring of Layer2's other 12 instrument classes) are respected — nothing in this plan touches any of them.

**Placeholder scan:** No TBD/TODO. The `_NOT_EXPOSED` table's real content is fully written in Task 1's Step 3, not deferred — the only thing left to the implementer is independently re-verifying the two citations against the real workbook (an explicit, real verification step, not a placeholder).

**Type consistency:** `ExposureJudgment`'s field names (`exposed`, `confidence`, `citation`) are used identically in Task 1's implementation and its tests. `is_exposed(taxonomy_category, symbol_class, table=None)`'s signature matches every call site across Tasks 1-2. `_get_todays_exogenous_shocks`/`_first_exposing_shock`'s names and return shapes in Task 2 match what Task 3's live-verify exercises through the real `/api/predictions` route, not a separate/renamed variant.
