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
