"""
Subject rules: which fetched articles may vote on which US event.

B6 (2026-10-22), audit AUD-P0-1 / AS-04. The keyword filter in
data_layer/event_context.py only asks "does this article mention the
event's topic?". It cannot tell WHOSE rates or inflation the article is
about, so foreign central-bank coverage was scored as US-dollar news for
FOMC and CPI events. Live examples from scoring/backtest_log.db's
top_contributions_json:

    "Interest rates must rise further on inflation risks, ECB's Schnabel tells Bloomberg - Reuters"
    "BoE's Pill says a rate hike need not be start of long series - Reuters"
    "'Godzilla El Niño' is wreaking havoc with Philippine central bank's inflation forecasts"
    "Gold edges up as October rate hike bets ease, stronger dollar cap gains"   (voted on FOMC)

A hawkish foreign central bank is USD-NEGATIVE, but the lexicon and FinBERT
read "rates must rise" as hawkish and therefore USD-positive: the sign is
inverted, not just noisy.

Three rules, applied in this order by b6_exclusion_reason():

1. foreign_cb (every event title): a foreign central bank or one of its
   officials is named in the title; or in the summary when the title names
   neither the US nor the Fed.
2. no_fed_coterm (FOMC family): the generic FOMC keywords ('rate hike',
   'monetary policy', 'central bank', ...) also fire on any other central
   bank, so the title or summary must also name the Fed (fed, fomc, federal
   reserve, a Fed official, ...).
3. off_subject (FOMC and CPI families, owner decision 8: a title filter,
   not the LLM tier): the TITLE must name the dollar, the Fed, US rates /
   Treasury yields, or (CPI family) US inflation / CPI / the BLS.

Limits, stated plainly: the subject rule reads the title only, so a US
article with a vague headline is dropped and a foreign article with a
US-sounding headline passes. FinBERT and the lexicon still read tone, not
subject: an article that passes these rules but is really about another
economy is still scored as US news. The structural fix is the parked
central-bank stance model; these rules only remove the cases a name list
can see.

Pure functions, no I/O, so later batches (B7 same-incident discount,
K-series, shock-alert country tagging) can reuse the same lists.
"""
from __future__ import annotations

import re

from config.settings import FED_OFFICIAL_SURNAMES, RELEVANCE_FAMILY_BY_TITLE

# Families the Fed co-term and title subject rules apply to. Every other
# family (jobs, ppi, ism, retail_sales, gdp, other) only gets foreign_cb.
SUBJECT_RULE_FAMILIES: tuple[str, ...] = ("fomc", "cpi")

# Foreign central banks and their officials. Bare "Bailey" / "Pill" are NOT
# listed: "poison pill" and "weight-loss pill" would drop real articles, and
# the live offenders say "BoE" / "Bank of England" anyway.
_FOREIGN_CB_NAMES: tuple[str, ...] = (
    "ecb", "european central bank", "lagarde", "schnabel", "villeroy", "nagel",
    "boe", "bank of england", "andrew bailey", "huw pill", "breeden",
    "boj", "bank of japan", "ueda", "himino",
    "rba", "reserve bank of australia", "bullock",
    "snb", "swiss national bank", "schlegel",
    "boc", "bank of canada", "macklem",
    "rbnz", "pboc", "people's bank of china", "pan gongsheng",
    "riksbank", "norges bank", "rbi", "bank of korea", "banxico", "bank of mexico",
    "bundesbank", "banque de france", "bank of italy",
)

# Named foreign banks, plus any "Reserve Bank of <X>" that is not the
# "Federal Reserve Bank of New York / St. Louis / ..." (a US Fed bank).
_FOREIGN_CB_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(name) for name in _FOREIGN_CB_NAMES) + r")\b"
    r"|(?<!federal )\breserve bank of \w+",
    re.IGNORECASE,
)

# A generic "central bank" counts as foreign only next to a foreign place
# name in the same text ("Philippine central bank", "China's ... central
# bank governor says"). Without a place it is left to the Fed co-term rule.
_CENTRAL_BANK_PATTERN = re.compile(r"\bcentral bank(?:s|ers?|'s)?\b", re.IGNORECASE)

_FOREIGN_PLACES: tuple[str, ...] = (
    "china", "chinese", "japan", "japanese", "euro zone", "eurozone", "euro area",
    "europe", "european", "eu", "uk", "u.k.", "britain", "british", "england",
    "germany", "german", "france", "french", "italy", "italian", "spain", "spanish",
    "swiss", "switzerland", "canada", "canadian", "australia", "australian",
    "new zealand", "india", "indian", "brazil", "brazilian", "mexico", "mexican",
    "turkey", "turkish", "russia", "russian", "korea", "korean",
    "philippine", "philippines", "filipino", "indonesia", "indonesian",
    "south africa", "south african", "sweden", "swedish", "norway", "norwegian",
    "poland", "polish", "thailand", "thai", "singapore", "hong kong", "taiwan",
    "israel", "saudi", "nigeria",
)
# Letter lookarounds instead of word boundaries so "u.k." (ends in a dot)
# matches and "indian" does not match inside "indiana".
_FOREIGN_PLACE_PATTERN = re.compile(
    r"(?<![a-z])(?:"
    + "|".join(re.escape(place) for place in sorted(_FOREIGN_PLACES, key=len, reverse=True))
    + r")(?![a-z])",
    re.IGNORECASE,
)

# Fed co-terms. "economic projections" is an FOMC keyword but NOT a co-term:
# the ECB publishes "macroeconomic projections" too.
_FED_PATTERN = re.compile(
    r"\b(?:fed|fomc|federal reserve|federal funds|fed funds|dot plot|"
    + "|".join(re.escape(name) for name in FED_OFFICIAL_SURNAMES)
    + r")\b",
    re.IGNORECASE,
)

# US marker. "US" / "U.S." / "USA" are case-SENSITIVE so the pronoun "us"
# never counts; the letter lookarounds keep "USD", "BUS", "USTR" out.
_US_MARKER = (
    r"(?:(?<![A-Za-z])U\.?S\.?(?![A-Za-z])"
    r"|\bUSA\b"
    r"|(?i:\bamerica(?:ns?)?\b|\bunited states\b))"
)
_US_MARKER_PATTERN = re.compile(_US_MARKER)

# US rates: Treasuries anywhere in the title, or a US marker followed within
# 0-2 words by rates / yields / borrowing costs ("US 10-year yields").
_US_RATES_PATTERN = re.compile(
    r"(?i:\b(?:treasury|treasuries|t-bills?|t-notes?)\b)"
    r"|" + _US_MARKER
    + r"(?i:(?:\s+\S+){0,2}?\s+(?:interest\s+rates?|rates?|yields?|borrowing\s+costs)\b)"
)

# The dollar, once other countries' dollars are removed from the title.
_FOREIGN_DOLLAR_PATTERN = re.compile(
    r"\b(?:australian|aussie|canadian|new zealand|kiwi|hong kong|singapore|taiwan)\s+dollars?\b",
    re.IGNORECASE,
)
_DOLLAR_PATTERN = re.compile(r"\b(?:dollar|usd|greenback|dxy)\b", re.IGNORECASE)

# A title that LEADS with another asset is about that asset, even when it
# mentions the dollar later ("Gold edges up as ..., stronger dollar cap
# gains"). Only applied to the dollar path: a title that names the Fed is
# kept whatever it leads with ("Gold miners rally as Fed signals rate cut").
_OTHER_ASSET_LEAD_PATTERN = re.compile(
    r"^\W*(?:gold|silver|platinum|oil|crude|brent|wti|copper|bitcoin|crypto\w*|"
    r"stocks?|equities|shares|wall st(?:reet)?|s&p(?: 500)?|nasdaq|dow|yen|euro|"
    r"sterling|pound|yuan|asian|european|global)\b",
    re.IGNORECASE,
)

# CPI family extras: US inflation (US marker, optional 's, then within 0-2
# words inflation / CPI / consumer prices), the BLS, or a bare CPI mention
# when no foreign place is named. Bare "inflation" alone does not qualify.
_US_INFLATION_PATTERN = re.compile(
    _US_MARKER
    + r"(?:'s)?(?i:(?:\s+\S+){0,2}?\s+(?:inflation|cpi|consumer\s+prices?|consumer\s+price\s+index)\b)"
)
_BLS_PATTERN = re.compile(r"\b(?:bls|bureau of labor statistics)\b", re.IGNORECASE)
_BARE_CPI_PATTERN = re.compile(r"\b(?:cpi|consumer price index)\b", re.IGNORECASE)

# Bare-CPI guard only: foreign headlines often lead with a currency nickname
# or a city instead of a country ("Aussie dollar eyes ... on hot CPI", live;
# "Tokyo CPI accelerates"). Kept out of _FOREIGN_PLACES so foreign_cb_match's
# "<place> central bank" rule is unchanged. Ambiguous English words ("pound",
# "won", "rand", bare "euro") are left out.
_FOREIGN_CPI_MARKERS: tuple[str, ...] = (
    "aussie", "kiwi", "loonie", "swissie", "sterling", "yen", "yuan", "renminbi",
    "rupee", "rupiah", "ringgit", "peso", "lira", "zloty", "forint", "krona", "krone",
    "tokyo", "beijing", "shanghai", "london", "ottawa", "sydney", "wellington",
    "mumbai", "seoul", "berlin", "paris", "frankfurt",
)
_FOREIGN_CPI_GUARD_PATTERN = re.compile(
    r"(?<![a-z])(?:"
    + "|".join(
        re.escape(marker)
        for marker in sorted(_FOREIGN_PLACES + _FOREIGN_CPI_MARKERS, key=len, reverse=True)
    )
    + r")(?![a-z])",
    re.IGNORECASE,
)


def _normalise(text: str) -> str:
    # Curly apostrophes ("ECB’s") would otherwise dodge the "'s" handling.
    return (text or "").replace("\u2019", "'")


def title_family(event_title: str) -> str:
    """The relevance family of an event title ("fomc", "cpi", "jobs", ...); "other" when unmapped."""
    return RELEVANCE_FAMILY_BY_TITLE.get(event_title, "other")


def foreign_cb_match(text: str) -> str | None:
    """The foreign central bank named in text, lower-case; None when there is none."""
    text = _normalise(text)
    named = _FOREIGN_CB_PATTERN.search(text)
    if named:
        return named.group(0).lower()
    if _CENTRAL_BANK_PATTERN.search(text):
        place = _FOREIGN_PLACE_PATTERN.search(text)
        if place:
            return f"{place.group(0).lower()} central bank"
    return None


def names_fed(text: str) -> bool:
    """True when text names the Fed, the FOMC, fed funds, the dot plot or a Fed official."""
    return bool(_FED_PATTERN.search(_normalise(text)))


def names_us_marker(text: str) -> bool:
    """True for US / U.S. / USA (case-sensitive), American(s) or United States."""
    return bool(_US_MARKER_PATTERN.search(_normalise(text)))


def _fomc_subject(title: str) -> bool:
    if names_fed(title) or _US_RATES_PATTERN.search(title):
        return True
    without_foreign_dollars = _FOREIGN_DOLLAR_PATTERN.sub(" ", title)
    return bool(_DOLLAR_PATTERN.search(without_foreign_dollars)) and not _OTHER_ASSET_LEAD_PATTERN.search(title)


def _cpi_subject(title: str) -> bool:
    if _fomc_subject(title) or _US_INFLATION_PATTERN.search(title) or _BLS_PATTERN.search(title):
        return True
    return bool(_BARE_CPI_PATTERN.search(title)) and not _FOREIGN_CPI_GUARD_PATTERN.search(title)


def passes_subject_rule(title: str, family: str) -> bool:
    """Title-only subject rule for the FOMC and CPI families; True for every other family."""
    if family not in SUBJECT_RULE_FAMILIES:
        return True
    title = _normalise(title)
    if family == "fomc":
        return _fomc_subject(title)
    return _cpi_subject(title)


def b6_exclusion_reason(title: str, summary: str, event_title: str) -> str | None:
    """
    Why an article that matched an event's keywords must not vote on it:
    "foreign_cb" -> "no_fed_coterm" (FOMC family) -> "off_subject" (FOMC
    and CPI families). None = the article is kept.
    """
    family = title_family(event_title)
    title = _normalise(title)
    summary = _normalise(summary)

    # A foreign CB in the title always excludes, even when the title leads
    # with the dollar: the sign can't be pinned to the US side.
    if foreign_cb_match(title) is not None:
        return "foreign_cb"
    if not (names_us_marker(title) or names_fed(title)) and foreign_cb_match(summary) is not None:
        return "foreign_cb"

    if family == "fomc" and not names_fed(f"{title} {summary}"):
        return "no_fed_coterm"

    if not passes_subject_rule(title, family):
        return "off_subject"
    return None
