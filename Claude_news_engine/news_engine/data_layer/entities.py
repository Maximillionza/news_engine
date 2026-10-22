"""
Named places and actors that identify one news incident.

B7 (2026-10-22), audit SA-04 / AS-01. Follow-up coverage of one event comes
back under a new headline ("Loud blast at Riyadh airport ..." then "Multiple
people wounded in blast at Riyadh airport ..."), so the similarity ratio
misses it. Two headlines of the same family that name the same place or
actor within a short window are the same incident (alerting/incident.py);
two articles of one event bundle naming the same set are one re-coverage
(scoring/probability_engine.py). Live pairs this was built from: #54/#55
(Riyadh), #71/#72 (Russia), #33/#39 (Ukraine/Russia), #12/#13 (Iran/Hormuz).

Owner decision: a small hand-written gazetteer, deterministic and testable.
It works on hard-rule hits and on alerts whose classification failed (42 of
75 live alerts at audit time), needs no LLM key and adds no classifier field.

Left out on purpose:
- generic actors that appear in most alerts of their family and so identify
  no incident: the US (US / U.S. / American / Washington), Trump, the White
  House, the Fed (Fed / Federal Reserve / FOMC);
- ambiguous names: Chad, Georgia, Jordan, Niger (people, a US state, a river).

Limits, stated plainly: headline (or title + summary) text only; an incident
named only by an unlisted place or actor yields no entity and simply is not
linked (today's behaviour); there is no capitalised-token fallback.
"""
from __future__ import annotations

import re

# canonical -> lower-case aliases (demonyms, capitals used as metonyms, spelling variants).
# The canonical name is what incident rules and labels show ("entity:saudi arabia").
INCIDENT_GAZETTEER: dict[str, tuple[str, ...]] = {
    # countries and their demonyms / metonym capitals
    "iran": ("iran", "iranian", "tehran"),
    "iraq": ("iraq", "iraqi"),
    "israel": ("israel", "israeli"),
    "saudi arabia": ("saudi arabia", "saudi", "saudis", "riyadh"),
    "uae": ("uae", "united arab emirates", "emirati", "abu dhabi", "dubai"),
    "qatar": ("qatar", "qatari"),
    "kuwait": ("kuwait",),
    "oman": ("oman", "omani"),
    "yemen": ("yemen", "yemeni"),
    "lebanon": ("lebanon", "lebanese", "beirut"),
    "syria": ("syria", "syrian", "damascus"),
    "egypt": ("egypt", "egyptian"),
    "libya": ("libya", "libyan"),
    "turkey": ("turkey", "turkish", "türkiye"),
    "russia": ("russia", "russian", "russians", "moscow", "kremlin"),
    "ukraine": ("ukraine", "ukrainian", "kyiv", "kiev"),
    "belarus": ("belarus",),
    "china": ("china", "chinese", "beijing"),
    "taiwan": ("taiwan", "taiwanese"),
    "japan": ("japan", "japanese"),
    "north korea": ("north korea", "north korean", "pyongyang"),
    "south korea": ("south korea", "south korean", "seoul"),
    "india": ("india", "indian"),
    "pakistan": ("pakistan", "pakistani"),
    "venezuela": ("venezuela", "venezuelan"),
    "mexico": ("mexico", "mexican"),
    "canada": ("canada", "canadian"),
    "brazil": ("brazil", "brazilian"),
    "nigeria": ("nigeria", "nigerian"),
    "eu": ("eu", "european union"),
    "uk": ("uk", "britain", "british"),
    # places
    "hormuz": ("hormuz", "strait of hormuz"),
    "red sea": ("red sea",),
    "bab el-mandeb": ("bab el-mandeb",),
    "suez": ("suez", "suez canal"),
    "black sea": ("black sea",),
    "panama canal": ("panama canal",),
    "taiwan strait": ("taiwan strait",),
    "gaza": ("gaza",),
    "west bank": ("west bank",),
    "crimea": ("crimea",),
    "kharkiv": ("kharkiv",),
    "odesa": ("odesa", "odessa"),
    "abqaiq": ("abqaiq",),
    "ras tanura": ("ras tanura",),
    "basra": ("basra",),
    "kharg": ("kharg",),
    # actors
    "houthi": ("houthi", "houthis"),
    "hezbollah": ("hezbollah",),
    "hamas": ("hamas",),
    "opec": ("opec", "opec+"),
    "iea": ("iea",),
    "nato": ("nato",),
    "iaea": ("iaea",),
    "aramco": ("aramco",),
    "putin": ("putin",),
    "zelensky": ("zelensky", "zelenskiy", "zelenskyy"),
    "netanyahu": ("netanyahu",),
    "khamenei": ("khamenei",),
    "xi jinping": ("xi jinping",),
    "erdogan": ("erdogan",),
    "maduro": ("maduro",),
    "kim jong un": ("kim jong un",),
    "mbs": ("mbs", "mohammed bin salman"),
}

_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical for canonical, aliases in INCIDENT_GAZETTEER.items() for alias in aliases
}

# Longest alias first, so "taiwan strait" is one match rather than "taiwan" + leftovers.
# Lookarounds instead of word boundaries: a word boundary after "opec+" would need a word
# character next, and "Omaha" must not match "oman".
_ALIAS_PATTERN = re.compile(
    r"(?<!\w)(?:"
    + "|".join(re.escape(alias) for alias in sorted(_ALIAS_TO_CANONICAL, key=len, reverse=True))
    + r")(?!\w)"
)


def _normalize(text: str) -> str:
    """Lower-case, curly apostrophes made straight, runs of whitespace collapsed."""
    text = (text or "").lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text)


def incident_entities(text: str) -> frozenset[str]:
    """Canonical gazetteer names found in `text` (a headline, or title + summary); empty when none."""
    return frozenset(_ALIAS_TO_CANONICAL[m.group(0)] for m in _ALIAS_PATTERN.finditer(_normalize(text)))
