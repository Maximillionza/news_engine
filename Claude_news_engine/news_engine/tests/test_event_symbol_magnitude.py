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


def test_cpi_mm_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== CPI m/m: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("CPI m/m", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"CPI m/m x {symbol} has an empty citation"
    print("PASS\n")


def test_ppi_mm_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== PPI m/m: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("PPI m/m", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"PPI m/m x {symbol} has an empty citation"
    print("PASS\n")


def test_nfp_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== Non-Farm Employment Change: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("Non-Farm Employment Change", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"NFP x {symbol} has an empty citation"
    print("PASS\n")


def test_fomc_rate_decision_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== FOMC Rate Decision: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("FOMC Rate Decision", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"FOMC Rate Decision x {symbol} has an empty citation"
    print("PASS\n")


def test_gdp_qq_has_all_10_relevant_magnitude_entries_with_real_shape():
    print("=== GDP q/q: all 10 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("GDP q/q", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"GDP q/q x {symbol} has an empty citation"
    print("PASS\n")


def test_core_pce_has_all_12_relevant_magnitude_entries_with_real_shape():
    print("=== Core PCE Price Index m/m: all 12 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "US500", "NAS100", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("Core PCE Price Index m/m", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"Core PCE x {symbol} has an empty citation"
    print("PASS\n")


def test_ism_manufacturing_has_all_10_relevant_magnitude_entries_with_real_shape():
    print("=== ISM Manufacturing PMI: all 10 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "XAGUSD", "US30", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD"]
    for symbol in symbols:
        judgment = esm.get_magnitude("ISM Manufacturing PMI", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"ISM Manufacturing PMI x {symbol} has an empty citation"
    print("PASS\n")


def test_ism_services_has_all_4_relevant_magnitude_entries_with_real_shape():
    print("=== ISM Services PMI: all 4 RELEVANT symbols have a magnitude entry, each with a valid tier and a non-empty citation ===")
    symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
    for symbol in symbols:
        judgment = esm.get_magnitude("ISM Services PMI", symbol)
        assert isinstance(judgment.tier, esm.MagnitudeTier)
        assert judgment.citation.strip() != "", f"ISM Services PMI x {symbol} has an empty citation"
    print("PASS\n")


if __name__ == "__main__":
    test_get_magnitude_raises_keyerror_for_a_pair_outside_the_94_scope()
    test_magnitude_tier_has_exactly_four_members()
    test_cpi_mm_has_all_12_relevant_magnitude_entries_with_real_shape()
    test_ppi_mm_has_all_12_relevant_magnitude_entries_with_real_shape()
    test_nfp_has_all_12_relevant_magnitude_entries_with_real_shape()
    test_fomc_rate_decision_has_all_12_relevant_magnitude_entries_with_real_shape()
    test_gdp_qq_has_all_10_relevant_magnitude_entries_with_real_shape()
    test_core_pce_has_all_12_relevant_magnitude_entries_with_real_shape()
    test_ism_manufacturing_has_all_10_relevant_magnitude_entries_with_real_shape()
    test_ism_services_has_all_4_relevant_magnitude_entries_with_real_shape()
    print("All event_symbol_magnitude scaffolding tests passed.")
