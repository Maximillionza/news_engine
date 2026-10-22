"""
Tests for data_layer/news_feed.py's B6 same-URL dedup (AS-01) -- pure functions, no network.
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.news_feed import NewsArticle, normalize_url, dedupe_same_url

T0 = dt.datetime(2026, 8, 19, 18, 0, tzinfo=UTC_TZ)


def _art(title, hours_before, url, source_type="test"):
    return NewsArticle(
        title=title, summary="", source="Wire", source_type=source_type,
        published_utc=T0 - dt.timedelta(hours=hours_before), url=url,
    )


def test_same_url_keeps_earliest():
    print("=== news_feed: B6 -- same URL keeps the earliest-published copy ===")
    url = "https://www.cnbc.com/a/b"
    late = _art("CNBC: Fed officials split, dollar slips", 1.0, url)
    early = _art("CNBC: Fed officials split", 3.0, url)
    kept, dropped = dedupe_same_url([late, early])
    assert kept == [early]
    assert dropped == [late]
    print("PASS\n")


def test_same_url_tie_keeps_higher_trust():
    print("=== news_feed: B6 -- equal publish times: the higher-trust copy is kept ===")
    url = "https://example.test/x"
    low = _art("Same story", 2.0, url, source_type="unknown_low")
    high = _art("Same story", 2.0, url, source_type="alpha_vantage_news")
    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
        "data_layer.news_feed.SOURCE_TRUST_WEIGHTS", {"unknown_low": 0.1, "alpha_vantage_news": 0.9}
    ):
        kept, dropped = dedupe_same_url([low, high])
    assert kept == [high] and dropped == [low]
    print("PASS\n")


def test_normalize_url_variants():
    print("=== news_feed: B6 -- URL normalisation ===")
    a = normalize_url("https://WWW.CNBC.com/a/b/#live")
    b = normalize_url("https://www.cnbc.com/a/b")
    c = normalize_url("https://www.cnbc.com/a/b?utm_source=rss")
    assert a == b == c
    assert normalize_url("https://www.cnbc.com/a/b") != normalize_url("https://www.cnbc.com/a/c")
    assert normalize_url("https://x.test/a?id=1") != normalize_url("https://x.test/a?id=2")
    assert normalize_url("") == ""
    assert normalize_url("   ") == ""
    print("PASS\n")


def test_blank_urls_never_merge():
    print("=== news_feed: B6 -- blank URLs are never merged ===")
    a = _art("One", 3.0, "")
    b = _art("Two", 1.0, "")
    kept, dropped = dedupe_same_url([a, b])
    assert kept == [a, b] and dropped == []
    print("PASS\n")


def test_input_order_kept():
    print("=== news_feed: B6 -- kept articles keep input order ===")
    x = _art("X", 1.0, "https://a.test/1")
    y = _art("Y", 2.0, "https://a.test/2")
    y_dup = _art("Y later", 0.5, "https://a.test/2")
    kept, dropped = dedupe_same_url([x, y_dup, y])
    assert kept == [x, y]
    assert dropped == [y_dup]
    print("PASS\n")


if __name__ == "__main__":
    test_same_url_keeps_earliest()
    test_same_url_tie_keeps_higher_trust()
    test_normalize_url_variants()
    test_blank_urls_never_merge()
    test_input_order_kept()
    print("All news_feed same-URL tests passed.")
