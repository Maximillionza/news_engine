"""
Tests for the Alpha Vantage wiring added to data_layer/news_feed.py and
data_layer/rss_sources.py — synthetic, no live network needed (requests
is patched). Same plain-assert/__main__ style as tests/test_scoring_smoke.py.
"""
import sys
import os
import datetime as dt
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_layer.news_feed as news_feed
import data_layer.rss_sources as rss_sources
from data_layer.news_feed import AlphaVantageNewsSource


def _fake_response(articles):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "feed": [
            {
                "title": a["title"],
                "summary": "",
                "source": "test",
                "time_published": a["time_published"],
                "url": "https://example.com",
                "overall_sentiment_score": a.get("sentiment"),
            }
            for a in articles
        ]
    }
    return resp


def test_no_key_raises_value_error():
    print("=== AlphaVantageNewsSource: no api_key raises ValueError, never silently no-ops ===")
    try:
        AlphaVantageNewsSource(api_key="")
        assert False, "expected ValueError"
    except ValueError:
        pass
    print("PASS\n")


def test_empty_query_maps_to_default_topics_not_sent_literally_empty():
    print("=== AlphaVantageNewsSource: query='' maps to DEFAULT_TOPICS, not a literal empty topics param ===")
    source = AlphaVantageNewsSource(api_key="fake-key-for-test")
    since = dt.datetime(2026, 8, 9, tzinfo=dt.timezone.utc)

    with patch.object(news_feed, "requests") as mock_requests:
        mock_requests.get.return_value = _fake_response([])
        source.fetch(query="", since_utc=since)

        call_kwargs = mock_requests.get.call_args.kwargs
        assert call_kwargs["params"]["topics"] == AlphaVantageNewsSource.DEFAULT_TOPICS, (
            f"expected DEFAULT_TOPICS ({AlphaVantageNewsSource.DEFAULT_TOPICS!r}) when query='', "
            f"got {call_kwargs['params']['topics']!r} — an empty string sent literally isn't "
            "the same as 'no filter' for Alpha Vantage's topics param"
        )
    print("PASS\n")


def test_explicit_query_passed_through_unchanged():
    print("=== AlphaVantageNewsSource: a real query string is passed through as-is, not overridden ===")
    source = AlphaVantageNewsSource(api_key="fake-key-for-test")
    since = dt.datetime(2026, 8, 9, tzinfo=dt.timezone.utc)

    with patch.object(news_feed, "requests") as mock_requests:
        mock_requests.get.return_value = _fake_response([])
        source.fetch(query="earnings,technology", since_utc=since)

        call_kwargs = mock_requests.get.call_args.kwargs
        assert call_kwargs["params"]["topics"] == "earnings,technology"
    print("PASS\n")


def test_native_sentiment_and_published_date_parsed_correctly():
    print("=== AlphaVantageNewsSource: response parses into NewsArticle with native_sentiment set ===")
    source = AlphaVantageNewsSource(api_key="fake-key-for-test")
    since = dt.datetime(2026, 8, 9, tzinfo=dt.timezone.utc)

    with patch.object(news_feed, "requests") as mock_requests:
        mock_requests.get.return_value = _fake_response([
            {"title": "Fed signals hawkish tilt", "time_published": "20260809T143000", "sentiment": 0.42},
        ])
        articles = source.fetch(query="", since_utc=since)

        assert len(articles) == 1
        assert articles[0].native_sentiment == 0.42
        assert articles[0].source_type == "alpha_vantage_news"
        assert articles[0].published_utc == dt.datetime(2026, 8, 9, 14, 30, tzinfo=dt.timezone.utc)
    print("PASS\n")


def test_combined_builder_includes_alpha_vantage_when_key_present():
    print("=== build_all_preview_sources: includes Alpha Vantage when ALPHA_VANTAGE_API_KEY is set ===")
    with patch.object(rss_sources, "ALPHA_VANTAGE_API_KEY", "fake-key-for-test"):
        sources = rss_sources.build_all_preview_sources()
        names = [s.name for s in sources]
        assert "alpha_vantage_news" in names
        # RSS sources must still all be present too — additive, not a replacement.
        for rss_name in rss_sources.FREE_PREVIEW_FEEDS:
            assert rss_name in names
    print("PASS\n")


def test_combined_builder_excludes_alpha_vantage_when_key_absent():
    print("=== build_all_preview_sources: RSS-only when ALPHA_VANTAGE_API_KEY is not set ===")
    with patch.object(rss_sources, "ALPHA_VANTAGE_API_KEY", ""):
        sources = rss_sources.build_all_preview_sources()
        names = [s.name for s in sources]
        assert "alpha_vantage_news" not in names
        assert len(sources) == len(rss_sources.FREE_PREVIEW_FEEDS)
    print("PASS\n")


if __name__ == "__main__":
    test_no_key_raises_value_error()
    test_empty_query_maps_to_default_topics_not_sent_literally_empty()
    test_explicit_query_passed_through_unchanged()
    test_native_sentiment_and_published_date_parsed_correctly()
    test_combined_builder_includes_alpha_vantage_when_key_present()
    test_combined_builder_excludes_alpha_vantage_when_key_absent()
    print("All news_sources tests passed.")
