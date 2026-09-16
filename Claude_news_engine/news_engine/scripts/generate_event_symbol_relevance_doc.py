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
