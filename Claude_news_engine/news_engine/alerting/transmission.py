"""
The one table of how a shock category reaches an instrument class: the
transmission CHANNEL (read by symbol_relevance.py to decide which tracked
symbols an alert affects) and the typical LEAN per news polarity (read by
direction.py to word the alert). Keeping both in one row means a channel can
never exist without a deliberate lean decision, and vice versa.

Channels: built as its own lightweight (category, symbol_class) table --
NOT a reuse of scoring/probability_engine.py's private _check_oil_shock,
which takes a pre-computed MacroBackdropRead object, not a category label
(the wrong shape for this purpose) -- layered on top of
webapp.symbols.classify_symbol()'s public usd_relationship baseline. Only
combinations with a real, documented transmission path are listed; anything
absent means "no established relevance", an honest [] result, not a guess.

Leans: where the evidence is genuinely contested the table says "mixed"
rather than inventing a direction -- cells marked [Layer2] are backed by
docs/News_Engine_Causation_Matrix_v2.xlsx's Layer2_Asset_Transmission sheet;
the rest are conventional market reasoning, marked [convention].

us_only cells state a direction only when the story is about the US (a Fed
decision moves USD; a BoE decision does not move USD-base pairs in a known
direction). For any other or unknown country the lean is "mixed" with
not_us_why as the reason.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class Lean:
    lean: str  # "buy" | "sell" | "mixed"
    why: str


@dataclass(frozen=True)
class Transmission:
    channel: str
    leans: Mapping[str, Lean]  # polarity -> Lean
    us_only: bool = False
    not_us_why: str = ""
    # When set, the channel only applies if the headline matches (e.g. a tariff
    # story reaches gold only when it is about bullion).
    headline_gate: Optional[re.Pattern[str]] = None


# Tariff stories reach gold only when the headline is about bullion itself.
BULLION_HEADLINE = re.compile(r"\b(?:gold|bullion|precious metals?)\b", re.IGNORECASE)

_BULLION_TARIFF_MIXED = Lean(
    "mixed", "tariffs on bullion can move gold either way via the COMEX-London premium [convention]")

# Oil-linked FX pairs (design spec: "USDCAD is oil-linked... independent
# of and sometimes working against the pure USD-weakness direction") get
# their own "oil_linked_fx" class wherever the table has one for the
# category, checked before webapp.symbols' generic class -- a real,
# specific transmission path, not the plain usd_relationship mapping.
OIL_LINKED_SYMBOLS = frozenset({"USDCAD"})

_GOLD_RATES_CONTESTED = Lean(
    "mixed", "gold's link to rate expectations has been unreliable since 2024 [Layer2]")
_RELIEF_GOLD_MIXED = Lean(
    "mixed", "safe-haven unwind and lower-inflation support pull gold opposite ways")

_NOT_THE_FED = "which central bank is unknown or not the Fed"
_NOT_THE_US_GOVERNMENT = "which government is unknown or not the US"
_US_FISCAL_FX_MIXED = Lean(
    "mixed", "US fiscal stress can weaken USD on credit risk or lift it on haven demand [convention]")

# (category, symbol_class) -> Transmission.
TRANSMISSION: dict[tuple[str, str], Transmission] = {
    # --- energy ---
    ("energy", "metal"): Transmission("safe_haven", {
        "escalation": Lean("buy", "safe-haven bid and inflation hedge on an oil-supply shock [convention]"),
        "relief": _RELIEF_GOLD_MIXED,
    }),
    ("energy", "index_risk"): Transmission("risk_sentiment", {
        "escalation": Lean("sell", "oil-supply shock weighs on risk appetite [convention]"),
        "relief": Lean("buy", "easing supply fears support risk appetite [convention]"),
    }),
    ("energy", "oil_linked_fx"): Transmission("oil_linkage", {
        "escalation": Lean("sell", "higher oil strengthens CAD, so USDCAD falls [Layer2]"),
        "relief": Lean("buy", "lower oil weakens CAD, so USDCAD rises [Layer2]"),
    }),
    # --- geopolitical conflict ---
    ("geopolitical_conflict", "metal"): Transmission("safe_haven", {
        "escalation": Lean("buy", "safe-haven demand [convention]"),
        "relief": _RELIEF_GOLD_MIXED,
    }),
    ("geopolitical_conflict", "index_risk"): Transmission("risk_sentiment", {
        "escalation": Lean("sell", "risk-off [convention]"),
        "relief": Lean("buy", "relief rally in risk appetite [convention]"),
    }),
    # --- central bank (FX direction only when it is the Fed; gold stays contested) ---
    ("central_bank", "metal"): Transmission("usd_relationship", {
        "hawkish": _GOLD_RATES_CONTESTED,
        "dovish": _GOLD_RATES_CONTESTED,
    }),
    ("central_bank", "index_risk"): Transmission("risk_sentiment", {
        "hawkish": Lean("sell", "tighter policy and higher yields weigh on equities [convention]"),
        "dovish": Lean(
            "mixed", "rate cuts read bullish (soft landing) or bearish (recession fear) depending on framing [Layer2]"),
    }),
    ("central_bank", "fx_usd_base"): Transmission("usd_relationship", {
        "hawkish": Lean("buy", "a hawkish Fed lifts USD, so USD-base pairs rise [convention]"),
        "dovish": Lean("sell", "a dovish Fed weakens USD, so USD-base pairs fall [convention]"),
    }, us_only=True, not_us_why=_NOT_THE_FED),
    ("central_bank", "fx_usd_quote"): Transmission("usd_relationship", {
        "hawkish": Lean("sell", "a hawkish Fed lifts USD, so USD-quote pairs fall [convention]"),
        "dovish": Lean("buy", "a dovish Fed weakens USD, so USD-quote pairs rise [convention]"),
    }, us_only=True, not_us_why=_NOT_THE_FED),
    # --- sovereign / fiscal stress ---
    ("sovereign_fiscal", "metal"): Transmission("usd_relationship", {
        "escalation": Lean("buy", "safe-haven bid on sovereign stress [convention]"),
        "relief": _RELIEF_GOLD_MIXED,
    }),
    ("sovereign_fiscal", "index_risk"): Transmission("risk_sentiment", {
        "escalation": Lean("sell", "credit stress is risk-off [convention]"),
        "relief": Lean("buy", "easing credit stress supports risk appetite [convention]"),
    }),
    ("sovereign_fiscal", "fx_usd_base"): Transmission("usd_relationship", {
        "escalation": _US_FISCAL_FX_MIXED,
        "relief": _US_FISCAL_FX_MIXED,
    }, us_only=True, not_us_why=_NOT_THE_US_GOVERNMENT),
    ("sovereign_fiscal", "fx_usd_quote"): Transmission("usd_relationship", {
        "escalation": _US_FISCAL_FX_MIXED,
        "relief": _US_FISCAL_FX_MIXED,
    }, us_only=True, not_us_why=_NOT_THE_US_GOVERNMENT),
    # --- trade policy ---
    ("trade_policy", "metal"): Transmission("tariff_bullion", {
        "escalation": _BULLION_TARIFF_MIXED,
        "relief": _BULLION_TARIFF_MIXED,
    }, headline_gate=BULLION_HEADLINE),
    ("trade_policy", "index_risk"): Transmission("risk_sentiment", {
        "escalation": Lean("sell", "trade escalation weighs on risk appetite [convention]"),
        "relief": Lean("buy", "trade de-escalation supports risk appetite [convention]"),
    }),
    # --- natural disaster / supply chain ---
    ("natural_disaster_supply_chain", "index_risk"): Transmission("risk_sentiment", {
        "escalation": Lean("sell", "supply-chain disruption is risk-off [convention]"),
        "relief": Lean("buy", "supply chains recovering supports risk appetite [convention]"),
    }),
}
