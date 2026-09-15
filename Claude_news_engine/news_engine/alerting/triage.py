"""Pure, no-I/O rule-based first pass over each fetched article."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from data_layer.news_feed import NewsArticle
from alerting.taxonomy import CATEGORY_SIGNAL_KEYWORDS, HARD_RULE_PATTERNS, NEAR_MISS_LOG_THRESHOLD


@dataclass
class TriageResult:
    matched: bool
    category: Optional[str]
    rule_tier_hit: bool
    matched_keywords: list[str]
    near_miss_score: Optional[float]
    near_miss_category: Optional[str] = None


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


def triage_article(article: NewsArticle) -> TriageResult:
    """
    HARD_RULE_PATTERNS checked first (unambiguous -> rule_tier_hit=True,
    severity decided as High by the caller, no LLM call needed); then
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
            return TriageResult(matched=True, category=category, rule_tier_hit=True, matched_keywords=hits, near_miss_score=None)

    best_category: Optional[str] = None
    best_hits: list[str] = []
    for category, keywords in CATEGORY_SIGNAL_KEYWORDS.items():
        hits = [k for k in keywords if k in text]
        if len(hits) > len(best_hits):
            best_category, best_hits = category, hits

    if best_hits:
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
