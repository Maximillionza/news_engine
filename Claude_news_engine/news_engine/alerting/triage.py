"""Pure, no-I/O rule-based first pass over each fetched article."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from data_layer.news_feed import NewsArticle
from alerting.taxonomy import CATEGORY_SIGNAL_KEYWORDS, HARD_RULE_PATTERNS, NEAR_MISS_LOG_THRESHOLD
from alerting.us_link import rule_country_us_link
from config.settings import EARTHQUAKE_MIN_MAGNITUDE

# Why a hard-rule hit may not fire on its own (FIX C1), in checking order.
GUARD_REASONS: tuple[str, ...] = ("summary_only", "denial", "price_report", "commentary", "unknown_us_link")


@dataclass
class TriageResult:
    matched: bool
    category: Optional[str]
    rule_tier_hit: bool
    matched_keywords: list[str]
    near_miss_score: Optional[float]
    near_miss_category: Optional[str] = None
    guard_reason: Optional[str] = None  # GUARD_REASONS entry on a hard-rule hit sent to the classifier


def _searchable_text(article: NewsArticle) -> str:
    return f"{article.title} {article.summary}".lower()


def _partial_match_score(text: str) -> tuple[Optional[str], float]:
    """
    For every phrase across all of CATEGORY_SIGNAL_KEYWORDS's keyword
    lists, splits the phrase into words and computes what fraction of
    those words appear anywhere in `text`. Returns the category and
    fraction for the single highest-scoring phrase found -- a real
    partial-match signal for the shock_near_misses audit log (previously
    hardcoded to 0.0, so nothing could ever clear NEAR_MISS_LOG_THRESHOLD
    and the log never got a row).
    """
    best_category: Optional[str] = None
    best_score = 0.0
    for category, keywords in CATEGORY_SIGNAL_KEYWORDS.items():
        for phrase in keywords:
            words = phrase.split()
            if not words:
                continue
            hits = sum(1 for w in words if w in text)
            score = hits / len(words)
            if score > best_score:
                best_score = score
                best_category = category
    return best_category, best_score


_MAGNITUDE_PATTERNS = (
    re.compile(r"magnitude[\s-]*(\d+(?:\.\d+)?)"),
    re.compile(r"(\d+(?:\.\d+)?)[\s-]*magnitude"),
    re.compile(r"\bm\s?(\d+(?:\.\d+)?)\b"),
)


def _stated_magnitude(text: str) -> Optional[float]:
    for pattern in _MAGNITUDE_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1))
    return None


def _is_minor_earthquake_only(text: str, category: Optional[str], hits: list[str]) -> bool:
    """
    True when the ONLY reason an article matched is the word "earthquake" and it states a
    magnitude under EARTHQUAKE_MIN_MAGNITUDE. No stated magnitude -> never filtered.
    """
    if category != "natural_disaster_supply_chain" or hits != ["earthquake"]:
        return False
    magnitude = _stated_magnitude(text)
    return magnitude is not None and magnitude < EARTHQUAKE_MIN_MAGNITUDE


# "not" also covers has not / have not / will not.
_DENIAL_RE = re.compile(
    r"\b(?:den(?:y|ies|ied|ying)|rul(?:e|es|ed|ing) out|no plans? to|not|false reports?|unconfirmed|rumou?r(?:s|ed)?)\b"
    r"|\b\w+n't\b"
)

_PRICED_ASSET = r"\b(?:prices?|oil|crude|brent|wti|gold|stocks?|shares)\b"
# Reporting words allowed between an asset and a tight move word ("Oil edges up", "Stocks end sharply lower",
# "Gold is 2% down"). A closed list on purpose: any other word there is usually a noun, and then the sentence
# is about that noun ("Oil exports shut down", "Oil tanker attack lifts premiums higher").
_ASSET_TO_MOVE = (
    r"(?:\s+prices?)?"
    r"(?:\s+(?:edg(?:e|es|ed|ing)|inch(?:es|ed|ing)?|tick(?:s|ed|ing)?|drift(?:s|ed|ing)?|trad(?:e|es|ed|ing)"
    r"|end(?:s|ed|ing)?|clos(?:e|es|ed|ing)|finish(?:es|ed|ing)?|open(?:s|ed|ing)?|turn(?:s|ed|ing)?"
    r"|head(?:s|ed|ing)?|mov(?:e|es|ed|ing)|push(?:es|ed|ing)?|stay(?:s|ed|ing)?|hold(?:s|ing)?|held"
    r"|remain(?:s|ed|ing)?|is|are|was|were|sharply|slightly|briefly|again|back|now|still"
    r"|\d+(?:\.\d+)?\s*%)){0,2}"
    r"\s+"
)
_LONG_RANGE = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|multi)[- ](?:day|week|month|year)"
_EXTREME = r"(?:record|all[- ]time|highest|lowest|" + _LONG_RANGE + r")"

# The first shape reads its verbs across a 30-character window, as it always did. The second holds the words
# that also turn up in event headlines ("up", "down", "lower", "top", "pare"), so they count only right after
# the asset, or after _ASSET_TO_MOVE. "top" and "pare" also take the plural-subject form ("Oil prices top $100",
# "Stocks pare losses"); bare "top" needs the dollar figure, since "Oil tanker seized, top general says" is an
# event. "high" and "low" beside a superlative read as a price with or without a named asset ("Dollar hits
# record high"), but "highest level" also means an alert or a rank, so "level" and "highest since" need the
# asset and a verb of arrival right before them.
_PRICE_REPORT_RE = re.compile(
    _PRICED_ASSET + r".{0,30}?"
    r"\b(?:rises?|rose|rising|falls?|fell|falling|jump(?:s|ed|ing)?|slides?|slid|sliding|climb(?:s|ed|ing)?"
    r"|drop(?:s|ped|ping)?|dip(?:s|ped|ping)?|sinks?|sank|sinking|surg(?:e|es|ed|ing)|tumbl(?:e|es|ed|ing)"
    r"|gain(?:s|ed|ing)?|soar(?:s|ed|ing)?|spik(?:e|es|ed|ing)|rall(?:y|ies|ied|ying))\b"
    r"|" + _PRICED_ASSET + _ASSET_TO_MOVE +
    r"(?:(?:up|down|higher|lower|mixed|flat|unchanged|steady|steadie[sd]|top(?:s|ped|ping)|advanc(?:e|es|ed|ing)"
    r"|par(?:e|es|ed|ing)|plung(?:e|es|ed|ing)|slump(?:s|ed|ing)?|slip(?:s|ped|ping)?|rebound(?:s|ed|ing)?"
    r"|retreat(?:s|ed|ing)?|eas(?:e|es|ed|ing)|extend(?:s|ed|ing)?|trim(?:s|med|ming)?|recover(?:s|ed|ing)?)\b"
    r"|(?:top|above|below|over|under)\s+\$\d)"
    r"|\bfutures\b"
    r"|\bsettle[sd]?\b"
    r"|\d+(?:\.\d+)?\s*%\s+(?:higher|lower)\b"
    r"|\b" + _EXTREME + r"[- ](?:high|low)s?\b"
    r"|" + _PRICED_ASSET + r"(?:\s+prices?)?\s+(?:hit(?:s|ting)?|at|near|reach(?:es|ed|ing)?|touch(?:es|ed|ing)?)"
    r"(?:\s+(?:its|their|a|an|the|new|fresh))*\s+"
    r"(?:records?|" + _EXTREME + r"\s+levels?|(?:highest|lowest)\s+(?:since|in))\b"
    r"|\bhit(?:s|ting)? \$\d"
)

# "may" the month is stripped first, so only the modal reads as speculation.
_MONTH_MAY_RE = re.compile(r"\b(?:in|by|of|on|since|from|until|early|late|mid|next|last|this)[\s-]+may\b|\bmay\s+(?=\d)")

_COMMENTARY_RE = re.compile(
    r"\banalysts?\s+(?:says?|said|warn(?:s|ed)?|sees?|saw|expect(?:s|ed)?)\b"
    r"|\b(?:could|might|may|would|if)\b"
    r"|\bwarn(?:s|ed)?\s+(?:that|of)\b"
    r"|\bfear(?:s|ed)?\b"
)


def _guard_text(title: str) -> str:
    return title.lower().replace("\u2019", "'").replace("\u2018", "'")


def _title_hits(title: str, hits: list[str]) -> list[str]:
    text = _guard_text(title)
    return [hit for hit in hits if hit in text]


def rule_guard_reason(title: str, hits: list[str]) -> Optional[str]:
    """
    The first GUARD_REASONS entry that stops a hard-rule hit firing on its
    own; None = a clean rule hit. Reads the title only: a phrase found just
    in the summary (live alert 7) is "summary_only", and a denial or price
    word in a summary says nothing about the headline the owner reads.
    "unknown_us_link" comes last: the title's own phrases do not name a path
    into US prices, so the classifier must judge it (alerting/us_link.py). A
    summary phrase with a known link cannot vouch for them.
    """
    text = _guard_text(title)
    title_hits = _title_hits(title, hits)
    if not title_hits:
        return "summary_only"
    if _DENIAL_RE.search(text):
        return "denial"
    if _PRICE_REPORT_RE.search(text):
        return "price_report"
    if _COMMENTARY_RE.search(_MONTH_MAY_RE.sub(" ", text)):
        return "commentary"
    if rule_country_us_link(title_hits)[1] is None:
        return "unknown_us_link"
    return None


def triage_article(article: NewsArticle) -> TriageResult:
    """
    HARD_RULE_PATTERNS checked first. A clean hit -> rule_tier_hit=True,
    severity decided as High by the caller, no LLM call needed, and
    matched_keywords holds the title's phrases only, because the caller
    reads the link and polarity from them. A hit
    rule_guard_reason() stops -> rule_tier_hit=False with guard_reason set,
    returned here rather than falling through, because phrases such as
    "sovereign default" have no keyword entry and would otherwise vanish;
    the caller classifies it like any ambiguous candidate. Then
    CATEGORY_SIGNAL_KEYWORDS (plausible category, ambiguous severity ->
    caller escalates to llm_classify.py). No match at all -> matched=False,
    with near_miss_score/near_miss_category recording the single
    best-scoring CATEGORY_SIGNAL_KEYWORDS phrase's word-level overlap
    (see _partial_match_score), purely for the non-match audit log
    (alerting/store.py's record_near_miss()) -- never used to alert on
    its own.
    """
    text = _searchable_text(article)

    for category, patterns in HARD_RULE_PATTERNS.items():
        hits = [p for p in patterns if p in text]
        if hits:
            reason = rule_guard_reason(article.title, hits)
            return TriageResult(
                matched=True, category=category, rule_tier_hit=reason is None,
                matched_keywords=_title_hits(article.title, hits) if reason is None else hits,
                near_miss_score=None, guard_reason=reason,
            )

    best_category: Optional[str] = None
    best_hits: list[str] = []
    for category, keywords in CATEGORY_SIGNAL_KEYWORDS.items():
        hits = [k for k in keywords if k in text]
        if len(hits) > len(best_hits):
            best_category, best_hits = category, hits

    if best_hits and not _is_minor_earthquake_only(text, best_category, best_hits):
        return TriageResult(matched=True, category=best_category, rule_tier_hit=False, matched_keywords=best_hits, near_miss_score=None)

    # No match at all -- record a real partial-match score (word-level
    # overlap against every CATEGORY_SIGNAL_KEYWORDS phrase) purely for
    # the near-miss audit log. `category` stays None here -- this is a
    # genuine no-match -- the best-scoring phrase's category is threaded
    # through separately as near_miss_category instead.
    near_miss_category, near_miss_score = _partial_match_score(text)
    return TriageResult(
        matched=False, category=None, rule_tier_hit=False, matched_keywords=[],
        near_miss_score=near_miss_score, near_miss_category=near_miss_category,
    )
