"""Tests for scripts/export_tier1_methodology.py (B3 T3): the workbook's POC sheets exported to
docs/tier1-methodology.md, which the research task reads instead of the .xlsx.

Reads the committed workbook (read-only); writes only to pytest's tmp_path.
"""
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from data_layer.tier1_events import TIER1_EVENTS  # noqa: E402
from scripts import export_tier1_methodology as export  # noqa: E402

APP = Path(__file__).resolve().parent.parent
WORKBOOK = APP / "docs" / "News_Engine_Causation_Matrix_v2.xlsx"
DOC = APP / "docs" / "tier1-methodology.md"


def _sections(text: str) -> dict[str, str]:
    """Rendered markdown -> {sheet name: that sheet's section text}."""
    out: dict[str, str] = {}
    for chunk in text.split("\n## ")[1:]:
        name, _, body = chunk.partition("\n")
        out[name.strip()] = body
    return out


def test_every_poc_sheet_has_a_section_and_every_tier1_title_is_covered_once() -> None:
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    try:
        poc_sheets = {name for name in wb.sheetnames if name.startswith("POC_")}
    finally:
        wb.close()
    assert poc_sheets == set(export.SECTIONS)
    assert export.SECTIONS["POC_Sub_Event_Consolidation"]["titles"] == []
    for title in TIER1_EVENTS:
        owners = [sheet for sheet, spec in export.SECTIONS.items() if title in spec["titles"]]
        assert len(owners) == 1, (title, owners)
    listed = [title for spec in export.SECTIONS.values() for title in spec["titles"]]
    assert sorted(listed) == sorted(TIER1_EVENTS)   # no title outside the registry
    for spec in export.SECTIONS.values():
        assert set(spec) == {"titles", "rule", "rejected", "confidence"}


def test_render_is_deterministic_and_the_committed_doc_is_current() -> None:
    first = export.render(WORKBOOK)
    assert first == export.render(WORKBOOK)
    assert DOC.read_text(encoding="utf-8") == first


def test_render_has_one_section_per_sheet_with_its_titles_rule_and_every_data_row() -> None:
    text = export.render(WORKBOOK)
    sections = _sections(text)
    assert set(sections) == set(export.SECTIONS)
    assert "`CPI m/m` (formula)" in sections["POC_CPI_Leading_Indicators"]
    assert "`PPI m/m` (judgment)" in sections["POC_PPI_Leading_Indicators"]
    assert "No event titles" in sections["POC_Sub_Event_Consolidation"]
    for body in sections.values():
        for label in ("**Rule:**", "**Rejected or not verified:**", "**Confidence rules:**"):
            assert label in body
    # Every data row of the workbook is in the export, verbatim.
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    try:
        for sheet in export.SECTIONS:
            rows = list(wb[sheet].iter_rows(values_only=True))
            for row in rows[1:]:
                for cell in row:
                    if cell is not None:
                        assert str(cell).strip() in sections[sheet], (sheet, str(cell)[:60])
    finally:
        wb.close()
    # 5-column sheet has no Lag field; 6-column sheets do.
    assert "(Lag: " not in sections["POC_Sub_Event_Consolidation"]
    assert "(Lag: " in sections["POC_NFP_Leading_Indicators"]


def test_intro_states_the_source_regeneration_and_the_formula_rule() -> None:
    intro = export.render(WORKBOOK).split("\n## ")[0]
    assert "News_Engine_Causation_Matrix_v2.xlsx" in intro
    assert "python scripts/export_tier1_methodology.py" in intro
    assert '"Likely"' in intro
    assert "Cleveland Fed nowcast (formula)" in intro
    assert "one rounding step" in intro


def test_rejected_indicators_are_named() -> None:
    sections = _sections(export.render(WORKBOOK))
    nfp = sections["POC_NFP_Leading_Indicators"]
    retail = sections["POC_Retail_Sales"]
    pce = sections["POC_Core_PCE"]
    rejected_nfp = nfp.split("**Rejected or not verified:**")[1].split("**Confidence rules:**")[0]
    rejected_retail = retail.split("**Rejected or not verified:**")[1].split("**Confidence rules:**")[0]
    rejected_pce = pce.split("**Rejected or not verified:**")[1].split("**Confidence rules:**")[0]
    assert "ADP" in rejected_nfp
    assert "consumer confidence" in rejected_retail.lower()
    assert "same-month CPI" in rejected_pce and "unadjusted" in rejected_pce


def test_check_exits_1_for_a_stale_doc_and_0_for_a_current_one(tmp_path: Path) -> None:
    out = tmp_path / "tier1-methodology.md"
    out.write_text("stale\n", encoding="utf-8")
    assert export.main(["--check", "--workbook", str(WORKBOOK), "--out", str(out)]) == 1
    assert out.read_text(encoding="utf-8") == "stale\n"   # --check never writes
    assert export.main(["--workbook", str(WORKBOOK), "--out", str(out)]) == 0
    assert export.main(["--check", "--workbook", str(WORKBOOK), "--out", str(out)]) == 0
