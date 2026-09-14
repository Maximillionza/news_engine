# tests/test_alerting_poll_once.py
from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

from alerting import store
from alerting.poll_once import run_poll_cycle
from data_layer.news_feed import NewsArticle
from webapp import store as webapp_store

UTC = dt.timezone.utc


def _article(title: str) -> NewsArticle:
    return NewsArticle(
        title=title, summary="", source="reuters_business", source_type="rss_reuters_business",
        published_utc=dt.datetime.now(UTC), url="https://example.com/a",
    )


def test_rule_tier_hit_persists_and_pushes_high_alert():
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")
    webapp_conn.execute("INSERT INTO tracked_symbols (symbol) VALUES ('XAUUSD')")
    webapp_conn.commit()

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.notify_telegram.send_alert", return_value=True) as mock_send:
        mock_source_cls.return_value.fetch.return_value = [_article("Strait of Hormuz closed after naval clash")]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    alerts = store.list_recent_alerts(conn, dt.datetime(2020, 1, 1, tzinfo=UTC))
    assert len(alerts) == 1
    assert alerts[0].severity == "High"
    assert alerts[0].classification_method == "rule_tier"
    assert mock_send.called


def test_no_match_never_persists_or_pushes():
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.notify_telegram.send_alert") as mock_send:
        mock_source_cls.return_value.fetch.return_value = [_article("Local bakery wins regional award")]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    assert store.list_recent_alerts(conn, dt.datetime(2020, 1, 1, tzinfo=UTC)) == []
    mock_send.assert_not_called()


def test_duplicate_article_appends_source_not_new_alert():
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")

    def _make_source(headline):
        def _factory(name, url):
            source = MagicMock()
            source.fetch.return_value = [_article(headline)] if name == "reuters_business" else []
            return source
        return _factory

    with patch("alerting.poll_once.RSSNewsSource", side_effect=_make_source("Strait of Hormuz closed after naval clash")), \
         patch("alerting.poll_once.notify_telegram.send_alert", return_value=True):
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    with patch("alerting.poll_once.RSSNewsSource", side_effect=_make_source("Strait of Hormuz closed following naval clash")), \
         patch("alerting.poll_once.notify_telegram.send_alert", return_value=True):
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    alerts = store.list_recent_alerts(conn, dt.datetime(2020, 1, 1, tzinfo=UTC))
    assert len(alerts) == 1
    assert len(alerts[0].sources) == 2


def test_one_source_fetch_failure_does_not_block_others():
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")

    call_count = {"n": 0}

    def fetch_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("feed down")
        return [_article("Strait of Hormuz closed after naval clash")]

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.notify_telegram.send_alert", return_value=True):
        mock_source_cls.return_value.fetch.side_effect = fetch_side_effect
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    alerts = store.list_recent_alerts(conn, dt.datetime(2020, 1, 1, tzinfo=UTC))
    assert len(alerts) >= 1  # at least one of the (mocked) multiple sources succeeded
