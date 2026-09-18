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
configured keywords, case-insensitive.

2026-09-17 fix: an event title with no configured keywords now FAILS
CLOSED (zero articles, loudly logged) — was previously fail-open (return
everything unfiltered). The fail-open default was found, via a real
2026-09-17 audit of scoring/backtest_log.db's top_contributions_json, to
be silently letting genuinely off-topic articles (a Chipotle restaurant
opening, a TSMC earnings report, a regional bank's CEO succession) score
real, non-trivial weight into events that had no curated keyword list at
all — 13+ of this project's tracked event titles, not just the couple this
suite originally covered. Fail-closed makes an uncurated event's missing
coverage loud and visible (an empty score) instead of silently plausible
(a garbage-fed one).
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


def test_event_with_no_configured_keywords_fails_closed_to_zero_articles():
    print("=== event_context: an event title with no keyword mapping now FAILS CLOSED to zero articles (2026-09-17 fix — was fail-open) ===")
    unrelated_looking = _article("Apple to change app data consent rules, German regulator says")
    even_a_real_looking_one = _article("Big Uncurated Event beats forecast, markets react")
    source = _StubSource([unrelated_looking, even_a_real_looking_one])
    bundle = _build(_event("Some Untracked Event Title"), source)
    assert bundle.articles == []  # dropped — no keyword list exists for this title, so nothing is scored unfiltered
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


def test_cpi_off_topic_article_is_dropped_reproducing_the_diagnosed_dilution():
    print("=== event_context: P0 #3 fix (fundamental-analysis-review-2026-09-11.md) — CPI m/m now filters off-topic noise, same class of bug already fixed for FOMC ===")
    on_topic = _article("US CPI cools to 3.3% y/y, core inflation steady", "Consumer price index data shows disinflation continuing")
    # Reproduces the exact noise found in the live Aug-12 2026 diagnosis —
    # real headlines that scored zero USD sentiment because they have
    # nothing to do with CPI/inflation at all.
    off_topic_a = _article("UAE to invest $40 billion in Germany amid slew of business deals")
    off_topic_b = _article("OpenAI launches ChatGPT for financial services industry")
    source = _StubSource([on_topic, off_topic_a, off_topic_b])
    bundle = _build(_event("CPI m/m"), source)
    titles = [a.title for a in bundle.articles]
    assert on_topic.title in titles
    assert off_topic_a.title not in titles
    assert off_topic_b.title not in titles
    print("PASS\n")


def test_cpi_keyword_list_shared_across_all_four_title_variants():
    print("=== event_context: CPI m/m, CPI y/y, Core CPI m/m, Core CPI y/y all get the same relevance filter — framing variants of the same BLS release ===")
    on_topic = _article("Inflation data due Wednesday, CPI expected to ease")
    off_topic = _article("Nubank launches US high-yield savings account, credit cards")
    for title in ("CPI m/m", "CPI y/y", "Core CPI m/m", "Core CPI y/y"):
        source = _StubSource([on_topic, off_topic])
        bundle = _build(_event(title), source)
        result_titles = [a.title for a in bundle.articles]
        assert on_topic.title in result_titles, f"{title}: on-topic article was wrongly dropped"
        assert off_topic.title not in result_titles, f"{title}: off-topic article was wrongly kept"
    print("PASS\n")


# --- 2026-09-17 audit: real off-topic articles pulled from
# scoring/backtest_log.db's top_contributions_json, each one a real,
# non-trivial-weight contribution to a real scored prediction for the
# named event before this fix. Reproduces the exact live evidence, same
# discipline as test_cpi_off_topic_article_is_dropped_reproducing_the_diagnosed_dilution
# above. ---

def test_nfp_drops_the_real_chipotle_article_that_previously_contributed_weight():
    print("=== event_context: Non-Farm Employment Change drops the real off-topic Chipotle article (2026-09-04 live evidence, 2.3% weight, +0.84 USD sentiment before this fix) ===")
    on_topic = _article("US adds 180,000 jobs in August, unemployment rate steady", "Non-farm payrolls beat expectations")
    off_topic = _article("Chipotle enters Asian market with first restaurant in Seoul")
    source = _StubSource([on_topic, off_topic])
    bundle = _build(_event("Non-Farm Employment Change"), source)
    titles = [a.title for a in bundle.articles]
    assert on_topic.title in titles
    assert off_topic.title not in titles
    print("PASS\n")


def test_ppi_drops_the_real_tsmc_article_that_previously_contributed_weight():
    print("=== event_context: PPI m/m drops the real off-topic TSMC revenue article (2026-09-10 live evidence, 1.9% weight, +0.95 USD sentiment before this fix) ===")
    on_topic = _article("US producer prices rise 0.3% in August, above forecast", "PPI data shows wholesale inflation ticking up")
    off_topic = _article("World's largest contract chipmaker TSMC sees August revenue surge over 53% to record high")
    source = _StubSource([on_topic, off_topic])
    bundle = _build(_event("PPI m/m"), source)
    titles = [a.title for a in bundle.articles]
    assert on_topic.title in titles
    assert off_topic.title not in titles
    print("PASS\n")


def test_ism_manufacturing_drops_the_real_venezuela_oil_article_that_previously_contributed_weight():
    print("=== event_context: ISM Manufacturing PMI drops the real off-topic Venezuela oil-deal article (2026-09-01 live evidence, 3.5% weight before this fix) ===")
    on_topic = _article("ISM Manufacturing PMI expands to 52.1, factory activity picks up", "Purchasing managers index beats forecast")
    off_topic = _article("Firms including Chevron, ONGC, GE Vernova on track to sign final pacts in Venezuela, sources say")
    source = _StubSource([on_topic, off_topic])
    bundle = _build(_event("ISM Manufacturing PMI"), source)
    titles = [a.title for a in bundle.articles]
    assert on_topic.title in titles
    assert off_topic.title not in titles
    print("PASS\n")


def test_retail_sales_drops_the_real_huntington_bank_article_that_previously_contributed_weight():
    print("=== event_context: Retail Sales m/m drops the real off-topic Huntington Bank CEO-succession article (2026-09-16 live evidence, 1.5% weight before this fix) ===")
    on_topic = _article("US retail sales rise 0.6% in August, consumer spending strong", "Retail sales data beats forecast")
    off_topic = _article("Huntington Bank promotes executive likely to become its next CEO")
    source = _StubSource([on_topic, off_topic])
    bundle = _build(_event("Retail Sales m/m"), source)
    titles = [a.title for a in bundle.articles]
    assert on_topic.title in titles
    assert off_topic.title not in titles
    print("PASS\n")


def test_unemployment_claims_drops_the_real_intel_sk_hynix_article_that_previously_contributed_weight():
    print("=== event_context: Unemployment Claims drops the real off-topic Intel/SK Hynix chip-manufacturing article (2026-09-17 live evidence, 3.1% weight before this fix) ===")
    on_topic = _article("Weekly jobless claims fall to 215,000, labor market resilient", "Unemployment claims data shows continued strength")
    off_topic = _article("Intel, SK Hynix shares jump on report they're discussing U.S. memory chip manufacturing")
    source = _StubSource([on_topic, off_topic])
    bundle = _build(_event("Unemployment Claims"), source)
    titles = [a.title for a in bundle.articles]
    assert on_topic.title in titles
    assert off_topic.title not in titles
    print("PASS\n")


def test_fomc_relevance_keywords_still_match_the_current_fed_chair_warsh():
    print("=== event_context: FOMC relevance keywords match 'Warsh' too, not just the stale 'Powell' (Kevin Warsh confirmed Fed Chair 2026-05-13) ===")
    on_topic = _article("Fed Chair Warsh signals data-dependent approach to rate decisions")
    source = _StubSource([on_topic])
    bundle = _build(_event("FOMC Statement"), source)
    assert len(bundle.articles) == 1
    print("PASS\n")


if __name__ == "__main__":
    test_off_topic_article_is_dropped_for_an_event_with_configured_keywords()
    test_relevance_keyword_match_is_case_insensitive_and_checks_summary_too()
    test_event_with_no_configured_keywords_fails_closed_to_zero_articles()
    test_relevance_filter_runs_before_dedup_but_does_not_break_it()
    test_cpi_off_topic_article_is_dropped_reproducing_the_diagnosed_dilution()
    test_cpi_keyword_list_shared_across_all_four_title_variants()
    print("All event_context tests passed.")
