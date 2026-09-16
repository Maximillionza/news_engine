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
