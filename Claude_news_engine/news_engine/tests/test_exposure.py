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
