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


def test_cpi_mm_has_all_12_symbol_entries_with_real_shape():
    print("=== CPI m/m: all 12 symbols present, each with a valid status and a non-empty citation ===")
    for symbol in esr.SYMBOLS:
        judgment = esr.get_relevance("CPI m/m", symbol)
        assert isinstance(judgment.status, esr.RelevanceStatus)
        assert judgment.citation.strip() != "", f"CPI m/m x {symbol} has an empty citation"
    print("PASS\n")


if __name__ == "__main__":
    test_get_relevance_raises_keyerror_for_a_pair_outside_the_108_scope()
    test_treat_as_relevant_relevant_is_true()
    test_treat_as_relevant_not_relevant_is_false()
    test_treat_as_relevant_unverified_defaults_true()
    test_event_types_and_symbols_match_the_spec_exactly()
    test_cpi_mm_has_all_12_symbol_entries_with_real_shape()
    print("All event_symbol_relevance scaffolding tests passed.")
