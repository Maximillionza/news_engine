"""
Likely market LEAN (potential buy / potential sell-off / no clear lean) for each
instrument a shock alert affects.

This is alert TEXT only. It is never read by scoring/, never feeds
predicted_direction, and is worded as a typical reaction, not a signal.

Why two steps: the same category points opposite ways depending on the
headline (energy: a strait closing vs. a ceasefire; central_bank: hawkish vs.
dovish), so a static category -> direction table would often be wrong. The
news's POLARITY is read per headline (hard-rule patterns carry theirs below;
everything else comes from the classifier, see llm_classify.py) and a
hand-written, auditable table turns (category, polarity, instrument class)
into a lean. Where the evidence is genuinely contested the table says "mixed"
rather than inventing a direction -- cells marked [Layer2] are backed by
docs/News_Engine_Causation_Matrix_v2.xlsx's Layer2_Asset_Transmission sheet;
the rest are conventional market reasoning, marked [convention].
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

POLARITIES = ("escalation", "relief", "hawkish", "dovish", "unclear")

_POLARITY_SYNONYMS = {
    "escalate": "escalation", "escalating": "escalation", "worsening": "escalation",
    "de-escalation": "relief", "de_escalation": "relief", "deescalation": "relief",
    "easing": "relief", "recovery": "relief",
}


def normalize_polarity(raw) -> str:
    """Maps a model's free-text polarity onto POLARITIES; anything unrecognized is 'unclear'."""
    if raw is None:
        return "unclear"
    value = str(raw).strip().lower().replace(" ", "_")
    value = _POLARITY_SYNONYMS.get(value, value)
    return value if value in POLARITIES else "unclear"


# Explicit polarity for EVERY hard-rule pattern (alerting/taxonomy.py) -- these
# alerts skip the LLM entirely, so their polarity must be known statically.
# A test fails if a pattern is added to taxonomy.py without an entry here.
_RULE_POLARITY: dict[str, str] = {
    "strait of hormuz closed": "escalation", "strait of hormuz blocked": "escalation",
    "strait of hormuz shut": "escalation", "bab el-mandeb closed": "escalation",
    "opec+ agrees to cut": "escalation", "opec+ output cut confirmed": "escalation",
    "opec+ agrees to increase": "relief",
    "oil export ban": "escalation", "tanker attacked": "escalation", "pipeline attack": "escalation",
    "declares war": "escalation", "declaration of war": "escalation",
    "military invasion": "escalation", "state of war declared": "escalation",
    "unscheduled rate cut": "dovish", "unscheduled rate hike": "hawkish",
    # Direction of an emergency decision / Fed-independence shock is not fixed by the phrase.
    "emergency rate decision": "unclear", "fed chair fired": "unclear", "fed chair resigns": "unclear",
    "sovereign default": "escalation", "credit rating downgraded": "escalation",
    "retaliatory tariffs announced": "escalation",
    "suez canal blocked": "escalation",
}


def rule_polarity(matched_keywords: Iterable[str]) -> str:
    for keyword in matched_keywords:
        if keyword in _RULE_POLARITY:
            return _RULE_POLARITY[keyword]
    return "unclear"


@dataclass(frozen=True)
class Lean:
    lean: str  # "buy" | "sell" | "mixed"
    why: str


_MIXED_UNKNOWN = Lean("mixed", "no established direction for this combination")

_GOLD_RATES_CONTESTED = Lean(
    "mixed", "gold's link to rate expectations has been unreliable since 2024 [Layer2]")
_RELIEF_GOLD_MIXED = Lean(
    "mixed", "safe-haven unwind and lower-inflation support pull gold opposite ways")

# (category, polarity, symbol class) -> Lean. Only combinations that
# symbol_relevance.py actually reports can ever be looked up.
_LEAN_TABLE: dict[tuple[str, str, str], Lean] = {
    # --- energy ---
    ("energy", "escalation", "metal"): Lean("buy", "safe-haven bid and inflation hedge on an oil-supply shock [convention]"),
    ("energy", "escalation", "index_risk"): Lean("sell", "oil-supply shock weighs on risk appetite [convention]"),
    ("energy", "escalation", "oil_linked_fx"): Lean("sell", "higher oil strengthens CAD, so USDCAD falls [Layer2]"),
    ("energy", "relief", "metal"): _RELIEF_GOLD_MIXED,
    ("energy", "relief", "index_risk"): Lean("buy", "easing supply fears support risk appetite [convention]"),
    ("energy", "relief", "oil_linked_fx"): Lean("buy", "lower oil weakens CAD, so USDCAD rises [Layer2]"),
    # --- geopolitical conflict ---
    ("geopolitical_conflict", "escalation", "metal"): Lean("buy", "safe-haven demand [convention]"),
    ("geopolitical_conflict", "escalation", "index_risk"): Lean("sell", "risk-off [convention]"),
    ("geopolitical_conflict", "relief", "metal"): _RELIEF_GOLD_MIXED,
    ("geopolitical_conflict", "relief", "index_risk"): Lean("buy", "relief rally in risk appetite [convention]"),
    # --- central bank (which central bank is not known, so FX and gold stay mixed) ---
    ("central_bank", "hawkish", "metal"): _GOLD_RATES_CONTESTED,
    ("central_bank", "hawkish", "index_risk"): Lean("sell", "tighter policy and higher yields weigh on equities [convention]"),
    ("central_bank", "dovish", "metal"): _GOLD_RATES_CONTESTED,
    ("central_bank", "dovish", "index_risk"): Lean(
        "mixed", "rate cuts read bullish (soft landing) or bearish (recession fear) depending on framing [Layer2]"),
    # --- sovereign / fiscal stress ---
    ("sovereign_fiscal", "escalation", "metal"): Lean("buy", "safe-haven bid on sovereign stress [convention]"),
    ("sovereign_fiscal", "escalation", "index_risk"): Lean("sell", "credit stress is risk-off [convention]"),
    ("sovereign_fiscal", "relief", "metal"): _RELIEF_GOLD_MIXED,
    ("sovereign_fiscal", "relief", "index_risk"): Lean("buy", "easing credit stress supports risk appetite [convention]"),
    # --- trade policy ---
    ("trade_policy", "escalation", "index_risk"): Lean("sell", "trade escalation weighs on risk appetite [convention]"),
    ("trade_policy", "relief", "index_risk"): Lean("buy", "trade de-escalation supports risk appetite [convention]"),
    # --- natural disaster / supply chain ---
    ("natural_disaster_supply_chain", "escalation", "index_risk"): Lean("sell", "supply-chain disruption is risk-off [convention]"),
    ("natural_disaster_supply_chain", "relief", "index_risk"): Lean("buy", "supply chains recovering supports risk appetite [convention]"),
}


def lean_for(category: str, polarity: str, symbol_class: str) -> Lean:
    if polarity == "unclear":
        return Lean("mixed", "the direction of the news itself is unclear")
    return _LEAN_TABLE.get((category, polarity, symbol_class), _MIXED_UNKNOWN)


def describe_impacts(impacts, category: str, polarity: str) -> list[dict]:
    """
    SymbolImpact list (alerting/symbol_relevance.py) -> the dicts stored in
    shock_alerts.affected_symbols_json and rendered by Telegram / the Shock
    Alerts tab. Old stored rows simply lack the lean keys; renderers cope.
    """
    out = []
    for impact in impacts:
        lean = lean_for(category, polarity, impact.symbol_class)
        out.append({
            "symbol": impact.symbol, "channel": impact.channel,
            "lean": lean.lean, "lean_why": lean.why,
        })
    return out
