from __future__ import annotations

import datetime as dt

from alerting.triage import triage_article
from data_layer.news_feed import NewsArticle

UTC = dt.timezone.utc


def _article(title: str, summary: str = "") -> NewsArticle:
    return NewsArticle(
        title=title, summary=summary, source="test", source_type="rss_test",
        published_utc=dt.datetime(2026, 9, 14, tzinfo=UTC), url="https://example.com",
    )


def test_hard_rule_pattern_gives_rule_tier_hit():
    result = triage_article(_article("Iran says Strait of Hormuz closed after clash"))
    assert result.matched is True
    assert result.rule_tier_hit is True
    assert result.category == "energy"


def test_category_signal_keyword_gives_ambiguous_candidate():
    result = triage_article(_article("Oil prices tick higher on OPEC+ output chatter"))
    assert result.matched is True
    assert result.rule_tier_hit is False
    assert result.category == "energy"


def test_no_match_returns_matched_false():
    # Deliberately picked to have zero incidental substring overlap with
    # any CATEGORY_SIGNAL_KEYWORDS phrase word (see
    # test_partial_keyword_overlap_gets_positive_near_miss_score for why
    # that matters -- ordinary words like "award" or "wins" can
    # coincidentally contain a keyword's substring, e.g. "war" in "award").
    result = triage_article(_article("Cat show draws big crowd today"))
    assert result.matched is False
    assert result.category is None
    assert result.rule_tier_hit is False
    assert result.near_miss_score == 0.0
    assert result.near_miss_category is None


def test_partial_keyword_overlap_gets_positive_near_miss_score():
    # Contains "hormuz" (one of the three words in the "strait of hormuz"
    # CATEGORY_SIGNAL_KEYWORDS phrase) but not "strait" or "of" alongside
    # it, so the full phrase never matches and this falls through to the
    # no-match branch -- but the partial overlap should still register.
    result = triage_article(_article("Tensions near Hormuz keep traders cautious"))
    assert result.matched is False
    assert result.category is None
    assert result.near_miss_score is not None
    assert result.near_miss_score > 0.0
    assert result.near_miss_category is not None


def test_matching_checks_title_and_summary():
    result = triage_article(_article("Markets steady", summary="Reports confirm: Strait of Hormuz closed overnight"))
    assert result.matched is True
    assert result.rule_tier_hit is True
