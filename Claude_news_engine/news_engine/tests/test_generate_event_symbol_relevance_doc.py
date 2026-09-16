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
        esr.RelevanceStatus.RELEVANT: "✓",      # checkmark
        esr.RelevanceStatus.NOT_RELEVANT: "✕",  # cross
        esr.RelevanceStatus.UNVERIFIED: "?",
    }[judgment.status]
    assert status_symbol in output, f"expected the {judgment.status} status symbol {status_symbol!r} to appear"
    assert judgment.citation in output, "expected the real citation text to appear verbatim, not summarized or dropped"
    print("PASS\n")


if __name__ == "__main__":
    test_render_markdown_table_includes_every_event_type_as_a_heading()
    test_render_markdown_table_includes_a_real_cells_status_and_citation()
    print("All generator tests passed.")
