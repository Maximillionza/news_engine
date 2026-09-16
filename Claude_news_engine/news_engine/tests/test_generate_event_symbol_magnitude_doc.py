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
