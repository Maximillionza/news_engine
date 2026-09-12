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
