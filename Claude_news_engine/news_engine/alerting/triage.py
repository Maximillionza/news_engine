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
    r"\b(?:den(?:y|ies|ied|ying)|rul(?:e|es|ed) out|no plans? to|not|false reports?|unconfirmed|rumou?r(?:s|ed)?)\b"
    r"|\b\w+n't\b"
)

_PRICE_REPORT_RE = re.compile(
    r"\b(?:prices?|oil|crude|brent|wti|gold|stocks?|shares)\b.{0,30}?"
    r"\b(?:rises?|rose|falls?|fell|jump(?:s|ed)?|slides?|slid|climb(?:s|ed)?|drop(?:s|ped)?|dip(?:s|ped)?"
    r"|sinks?|sank|surge[sd]?|tumble[sd]?|gain(?:s|ed)?)\b"
    r"|\bfutures\b"
    r"|\bsettle[sd]?\b"
    r"|\d+(?:\.\d+)?\s*%\s+(?:higher|lower)\b"
    r"|\bhits? \d+-(?:day|week|month|year) (?:high|low)s?\b"
)

# "may" the month is stripped first, so only the modal reads as speculation.
_MONTH_MAY_RE = re.compile(r"\b(?:in|by|of|on|since|from|until|early|late|mid|next|last|this)[\s-]+may\b|\bmay\s+(?=\d)")

_COMMENTARY_RE = re.compile(
    r"\banalysts?\s+(?:says?|said|warns?|sees?|expects?)\b"
    r"|\b(?:could|might|may)\b"
    r"|\bwarns?\s+(?:that|of)\b"
    r"|\bfears?\b"
)


def rule_guard_reason(title: str, hits: list[str]) -> Optional[str]:
    """
    The first GUARD_REASONS entry that stops a hard-rule hit firing on its
    own; None = a clean rule hit. Reads the title only: a phrase found just
    in the summary (live alert 7) is "summary_only", and a denial or price
    word in a summary says nothing about the headline the owner reads.
    "unknown_us_link" comes last: the phrase does not name a path into US
    prices, so the classifier must judge it (alerting/us_link.py).
    """
    text = title.lower().replace("\u2019", "'").replace("\u2018", "'")
    if not any(hit in text for hit in hits):
        return "summary_only"
    if _DENIAL_RE.search(text):
        return "denial"
    if _PRICE_REPORT_RE.search(text):
        return "price_report"
    if _COMMENTARY_RE.search(_MONTH_MAY_RE.sub(" ", text)):
        return "commentary"
    if rule_country_us_link(hits)[1] is None:
        return "unknown_us_link"
    return None


def triage_article(article: NewsArticle) -> TriageResult:
    """
    HARD_RULE_PATTERNS checked first. A clean hit -> rule_tier_hit=True,
    severity decided as High by the caller, no LLM call needed. A hit
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
                matched=True, category=category, rule_tier_hit=reason is None, matched_keywords=hits,
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
