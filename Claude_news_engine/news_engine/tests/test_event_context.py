"""
Tests for data_layer/event_context.py's relevance filter — no live network,
a stub NewsSource returns a fixed article list.

Background: the article pipeline has no topic filtering at the fetch layer
(every source is called with query="", "return everything in the window" —
see news_feed.py/rss_sources.py docstrings). That's fine for events where
the general macro news cycle IS the relevant news cycle, but it means an
event like FOMC Meeting Minutes gets scored against whatever else was
published in the window too — confirmed live 2026-08-19: unrelated Apple/
Nvidia headlines showed up in FOMC's top-3 contributing articles for
XAUUSD. This filter is a second, event-title-keyed pass over the merged
article set: relevant if title+summary contains any of that event's
configured keywords, case-insensitive. An event title with no configured
keywords is NOT filtered at all (fail-open, same "absent, not fabricated"
contract as the rest of this pipeline) — silently guessing keywords for an
event nobody's curated would risk dropping genuinely relevant coverage.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ, PRE_EVENT_WINDOW_HOURS
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import build_event_news_bundle
from data_layer.news_feed import NewsArticle

EVENT_TIME = dt.datetime(2026, 8, 19, 18, 0, tzinfo=UTC_TZ)


def _event(title="FOMC Meeting Minutes"):
    return EconomicEvent(title=title, country="USD", impact="High", event_time_utc=EVENT_TIME, forecast=None, actual=None)


def _article(title, summary="", hours_before_event=1.0):
    return NewsArticle(
        title=title, summary=summary, source="Test Wire", source_type="test",
        published_utc=EVENT_TIME - dt.timedelta(hours=hours_before_event),
        url=f"https://example.test/{title[:10]}",
    )


class _StubSource:
    name = "stub"

    def __init__(self, articles):
        self._articles = articles

    def fetch(self, query, since_utc, limit=50):
        return list(self._articles)


def _build(event, source, mode_kwargs=None):
    # backtest mode with an explicit cutoff at the event time — deterministic
    # regardless of wall-clock "now", unlike mode="live" which would make
    # this test's pass/fail depend on when it happens to run.
    return build_event_news_bundle(
        event, [source], query="", mode="backtest", backtest_cutoff_utc=EVENT_TIME
    )


def test_off_topic_article_is_dropped_for_an_event_with_configured_keywords():
    print("=== event_context: an article with no FOMC-relevant keyword is dropped from an FOMC bundle ===")
    on_topic = _article("Fed signals hawkish tilt in FOMC minutes", "Federal Reserve officials debated rate hikes")
    off_topic = _article("Apple to change app data consent rules, German regulator says")
    source = _StubSource([on_topic, off_topic])
    bundle = _build(_event("FOMC Meeting Minutes"), source)
    titles = [a.title for a in bundle.articles]
    assert on_topic.title in titles
    assert off_topic.title not in titles
    print("PASS\n")


def test_relevance_keyword_match_is_case_insensitive_and_checks_summary_too():
    print("=== event_context: relevance match is case-insensitive and checks the summary, not just the title ===")
    matches_via_summary = _article("Markets steady ahead of release", "Traders await the FOMC statement for rate guidance")
    source = _StubSource([matches_via_summary])
    bundle = _build(_event("FOMC Meeting Minutes"), source)
    assert len(bundle.articles) == 1
    print("PASS\n")


def test_event_with_no_configured_keywords_is_not_filtered_at_all():
    print("=== event_context: an event title with no keyword mapping gets NO filtering (fail-open, not a guessed filter) ===")
    unrelated_looking = _article("Apple to change app data consent rules, German regulator says")
    source = _StubSource([unrelated_looking])
    bundle = _build(_event("Some Untracked Event Title"), source)
    assert len(bundle.articles) == 1  # kept — no keyword list exists for this title, so nothing is dropped
    print("PASS\n")


def test_relevance_filter_runs_before_dedup_but_does_not_break_it():
    print("=== event_context: relevance filtering and dedup compose — an off-topic near-duplicate pair both get dropped ===")
    on_topic = _article("Fed holds rates steady, FOMC minutes show", "Federal Reserve policy")
    off_topic_dupe_a = _article("Apple to change app data consent rules, regulator says")
    off_topic_dupe_b = _article("Apple to change app data consent rules, regulator says")  # exact dupe title
    source = _StubSource([on_topic, off_topic_dupe_a, off_topic_dupe_b])
    bundle = _build(_event("FOMC Meeting Minutes"), source)
    assert [a.title for a in bundle.articles] == [on_topic.title]
    print("PASS\n")


if __name__ == "__main__":
    test_off_topic_article_is_dropped_for_an_event_with_configured_keywords()
    test_relevance_keyword_match_is_case_insensitive_and_checks_summary_too()
    test_event_with_no_configured_keywords_is_not_filtered_at_all()
    test_relevance_filter_runs_before_dedup_but_does_not_break_it()
    print("All event_context tests passed.")
