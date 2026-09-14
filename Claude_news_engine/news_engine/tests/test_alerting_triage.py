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
    result = triage_article(_article("Local bakery wins regional award"))
    assert result.matched is False
    assert result.category is None
    assert result.rule_tier_hit is False


def test_matching_checks_title_and_summary():
    result = triage_article(_article("Markets steady", summary="Reports confirm: Strait of Hormuz closed overnight"))
    assert result.matched is True
    assert result.rule_tier_hit is True
