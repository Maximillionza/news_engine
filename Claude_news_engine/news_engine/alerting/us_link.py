"""
Country and US link of a shock alert (B2 K2/K3, 2026-10-21).

The instruments this tool watches (XAUUSD, US30, USD pairs) are priced off
the US. A story with no path into US prices -- unrest in France, a drone hit
on a Russian data centre -- was alerting High with firm buy/sell leans
(audit SA-01/02/03). Each alert therefore carries:

- country: ISO 3166-1 alpha-2 of where it happens or the main actor, "XX"
  for global / several countries, None = unknown.
- us_link, one of US_LINKS (None = unknown):
  - "direct": it happens in the US or a US actor does it (the Fed, the US
    government or Treasury, US companies or markets).
  - "global_supply": it happens elsewhere but changes a supply the whole
    world prices -- oil or gas output and exports, OPEC+ decisions, a
    shipping chokepoint (Hormuz, Bab el-Mandeb, Suez) -- so it reaches US
    prices and gold anyway.
  - "none": a local event outside the US with neither link (domestic
    unrest, a strike on a local site, a local company's outage).

An LLM-classified alert gets both fields from the classifier, best-effort
(alerting/llm_classify.py). A hard-rule hit never sees the LLM, so its
fields come from the fixed _RULE_COUNTRY_US_LINK map below. "none" caps the
alert at Medium with no buy/sell lean (cap_severity / cap_note); unknown
(None) keeps today's behaviour.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from alerting.direction import NO_US_LINK_WHY
from config.settings import SHOCK_GLOBAL_SUPPLY_TERMS

US_LINKS = ("direct", "global_supply", "none")

_SEVERITY_RANK = {"Low": 0, "Medium": 1, "High": 2}
_CAP_SEVERITY = "Medium"

_COUNTRY_SYNONYMS = {
    "USA": "US", "U.S.": "US", "U.S": "US", "UNITED STATES": "US",
    "GLOBAL": "XX", "MULTIPLE": "XX",
}
_ISO2 = re.compile(r"^[A-Z]{2}$")

_GLOBAL_SUPPLY = ("XX", "global_supply")
_US_DIRECT = ("US", "direct")
_UNKNOWN: tuple[Optional[str], Optional[str]] = (None, None)

# One deliberate entry per taxonomy.HARD_RULE_PATTERNS phrase (a test pins the
# key set). (None, None) where the phrase does not name the actor: a tanker or
# pipeline attack, a war, a default or a downgrade can be anywhere.
# Deliberate deviation from the B2 brief's example: unscheduled rate cut/hike
# is NOT mapped to ("US", "direct") -- the phrase does not name the Fed, and
# US/direct would give USD pairs a firm buy/sell lean on, say, a Turkish
# emergency hike. Change that one line if the owner wants it.
_RULE_COUNTRY_US_LINK: dict[str, tuple[Optional[str], Optional[str]]] = {
    # energy
    "strait of hormuz closed": _GLOBAL_SUPPLY,
    "strait of hormuz blocked": _GLOBAL_SUPPLY,
    "strait of hormuz shut": _GLOBAL_SUPPLY,
    "bab el-mandeb closed": _GLOBAL_SUPPLY,
    "opec+ agrees to cut": _GLOBAL_SUPPLY,
    "opec+ agrees to increase": _GLOBAL_SUPPLY,
    "opec+ output cut confirmed": _GLOBAL_SUPPLY,
    "oil export ban": (None, "global_supply"),  # whoever bans, it is oil leaving the world market
    "tanker attacked": _UNKNOWN,
    "pipeline attack": _UNKNOWN,
    # geopolitical_conflict
    "declares war": _UNKNOWN,
    "declaration of war": _UNKNOWN,
    "military invasion": _UNKNOWN,
    "state of war declared": _UNKNOWN,
    # central_bank
    "emergency rate decision": _UNKNOWN,
    "unscheduled rate cut": _UNKNOWN,
    "unscheduled rate hike": _UNKNOWN,
    "fed chair fired": _US_DIRECT,
    "fed chair resigns": _US_DIRECT,
    # sovereign_fiscal
    "sovereign default": _UNKNOWN,
    "credit rating downgraded": _UNKNOWN,
    # trade_policy
    "retaliatory tariffs announced": _UNKNOWN,
    # natural_disaster_supply_chain
    "suez canal blocked": _GLOBAL_SUPPLY,
}


def normalize_country(raw: object) -> Optional[str]:
    """ISO-2 (or "XX") from a model's free text; anything else -> None (unknown), never a guess."""
    if not isinstance(raw, str):
        return None
    value = raw.strip().upper()
    value = _COUNTRY_SYNONYMS.get(value, value)
    return value if _ISO2.match(value) else None


def normalize_us_link(raw: object) -> Optional[str]:
    """Surface form only ("Global supply", "global-supply", "None"); anything outside US_LINKS -> None."""
    if not isinstance(raw, str):
        return None
    value = re.sub(r"[\s\-]+", "_", raw.strip().lower())
    return value if value in US_LINKS else None


def reconcile(country: Optional[str], us_link: Optional[str]) -> Optional[str]:
    """
    A US event is "direct" by definition, so a model's "none" (or omission)
    for country "US" is overridden. Otherwise the model's answer stands.
    """
    if country == "US":
        return "direct"
    return us_link


GLOBAL_SUPPLY_REJECTED_NOTE = "us_link global_supply rejected: not a supply story"

# Whole-word match of any term; spaces in a term match any run of whitespace, and a
# trailing "s"/"es" also matches (ports, tankers, pipelines). "port" never matches
# inside "report" or "export".
_SUPPLY_TERM_RE = re.compile(
    r"\b(?:" + "|".join(
        r"\s+".join(re.escape(word) for word in term.split())
        for term in sorted(SHOCK_GLOBAL_SUPPLY_TERMS, key=len, reverse=True)
    ) + r")(?:e?s)?\b",
    re.IGNORECASE,
)


def check_global_supply(us_link: Optional[str], category: Optional[str], text: str) -> tuple[Optional[str], bool]:
    """
    (us_link, rejected). A classifier's "global_supply" stands only for an
    energy-category story or one whose text names a supply term
    (SHOCK_GLOBAL_SUPPLY_TERMS); otherwise it is downgraded to "none" and
    rejected=True, so the no-US-link cap applies. A small model was seen
    calling Russia drone stories "global_supply" (smoke test 2026-10-21).
    "direct", "none" and unknown pass through unchanged.
    """
    if us_link != "global_supply":
        return us_link, False
    if category == "energy" or _SUPPLY_TERM_RE.search(text or ""):
        return us_link, False
    return "none", True


def rule_country_us_link(matched_keywords: Iterable[str]) -> tuple[Optional[str], Optional[str]]:
    """(country, us_link) for a hard-rule hit: the first known pattern wins; (None, None) if none is known."""
    for keyword in matched_keywords:
        entry = _RULE_COUNTRY_US_LINK.get(str(keyword).strip().lower())
        if entry is not None:
            return entry
    return _UNKNOWN


def cap_severity(severity: str, us_link: Optional[str]) -> tuple[str, bool]:
    """
    (severity, capped). us_link "none" caps at Medium (a Low stays Low) and
    reports capped=True even when nothing was lowered, because the alert
    still loses its buy/sell lean. Unknown or linked -> unchanged.
    """
    if us_link != "none":
        return severity, False
    if _SEVERITY_RANK.get(severity, -1) > _SEVERITY_RANK[_CAP_SEVERITY]:
        return _CAP_SEVERITY, True
    return severity, True


def cap_note(original_severity: Optional[str], capped: Optional[bool]) -> Optional[str]:
    """The one line the owner sees on a capped alert (Telegram, tab); None when not capped."""
    if not capped:
        return None
    if original_severity == "High":
        return f"Capped High -> Medium: {NO_US_LINK_WHY}"
    return f"No buy/sell lean: {NO_US_LINK_WHY}"
