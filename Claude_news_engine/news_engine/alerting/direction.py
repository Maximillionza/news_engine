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
into a lean. That table lives in alerting/transmission.py (shared with
symbol_relevance.py's channels), with its [Layer2] / [convention] provenance.

Two story-level facts can override a cell, both from the classifier:
- us_link == "none" (no direct US or global-supply link): every lean is
  "mixed" -- a regional story has no reliable direction for USD-priced
  instruments.
- country: "us_only" cells (Fed-driven FX) state a direction only when the
  story is about the US; for any other or unknown country they are "mixed".
None for either means unknown and keeps the table's lean.
"""
from __future__ import annotations

from typing import Iterable, Optional

# Lean lives in transmission.py now; re-exported so `from alerting.direction
# import Lean` keeps working.
from alerting.transmission import TRANSMISSION, Lean

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


NO_US_LINK_WHY = "no direct US or global-supply link"

_MIXED_UNKNOWN = Lean("mixed", "no established direction for this combination")
_MIXED_UNCLEAR = Lean("mixed", "the direction of the news itself is unclear")


def lean_for(
    category: str, polarity: str, symbol_class: str,
    country: Optional[str] = None, us_link: Optional[str] = None,
) -> Lean:
    """
    Order matters: a story with no US link is "mixed" whatever its polarity;
    an unclear polarity is "mixed" whatever the cell; a Fed-only cell needs
    country == "US" before it states a direction.
    """
    if us_link == "none":
        return Lean("mixed", NO_US_LINK_WHY)
    if polarity == "unclear":
        return _MIXED_UNCLEAR
    transmission = TRANSMISSION.get((category, symbol_class))
    if transmission is None:
        return _MIXED_UNKNOWN
    if transmission.us_only and country != "US":
        return Lean("mixed", transmission.not_us_why)
    return transmission.leans.get(polarity, _MIXED_UNKNOWN)


def describe_impacts(
    impacts, category: str, polarity: str,
    country: Optional[str] = None, us_link: Optional[str] = None,
) -> list[dict]:
    """
    SymbolImpact list (alerting/symbol_relevance.py) -> the dicts stored in
    shock_alerts.affected_symbols_json and rendered by Telegram / the Shock
    Alerts tab. Old stored rows simply lack the lean keys; renderers cope.
    """
    out = []
    for impact in impacts:
        lean = lean_for(category, polarity, impact.symbol_class, country=country, us_link=us_link)
        out.append({
            "symbol": impact.symbol, "channel": impact.channel,
            "lean": lean.lean, "lean_why": lean.why,
        })
    return out
