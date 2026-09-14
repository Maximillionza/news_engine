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


def _searchable_text(article: NewsArticle) -> str:
    return f"{article.title} {article.summary}".lower()


def triage_article(article: NewsArticle) -> TriageResult:
    """
    HARD_RULE_PATTERNS checked first (unambiguous -> rule_tier_hit=True,
    severity decided as High by the caller, no LLM call needed); then
    CATEGORY_SIGNAL_KEYWORDS (plausible category, ambiguous severity ->
    caller escalates to llm_classify.py). No match at all -> matched=False,
    with near_miss_score recording how many signal keywords (as a
    fraction of the category with the most hits) came close, purely for
    the non-match audit log (alerting/store.py's record_near_miss()) --
    never used to alert on its own.
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

    # No match at all -- record how close the single best keyword hit
    # count came, scaled by the largest keyword list, purely as a rough
    # near-miss signal. 0 hits -> score 0.0 (an honest "not close at all"
    # rather than a fabricated positive number).
    all_keyword_lists = list(CATEGORY_SIGNAL_KEYWORDS.values())
    largest_list_len = max(len(k) for k in all_keyword_lists) if all_keyword_lists else 1
    near_miss_score = 0.0
    return TriageResult(matched=False, category=None, rule_tier_hit=False, matched_keywords=[], near_miss_score=near_miss_score)
