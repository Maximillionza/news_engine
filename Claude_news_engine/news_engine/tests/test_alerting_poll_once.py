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


def test_cursor_advances_past_newest_article_not_exactly_to_it():
    """
    Regression test for a real production bug (2026-09-17): a cursor set
    to exactly the newest article's own published_utc would still satisfy
    RSSNewsSource's `published < since_utc` filter next cycle (equality
    doesn't fail that check), so the same article gets refetched and
    reprocessed for as long as it stays in the feed's window -- confirmed
    live as 46 duplicate append_source() calls on one real alert over
    2.5 hours. The cursor must land strictly after the article's own
    timestamp, not exactly on it.
    """
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")
    published = dt.datetime(2026, 9, 17, 12, 44, 10, tzinfo=UTC)

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.notify_telegram.send_alert", return_value=True):
        mock_source_cls.return_value.fetch.return_value = [
            NewsArticle(
                title="Strait of Hormuz closed after pipeline attack", summary="",
                source="reuters_business", source_type="rss_reuters_business",
                published_utc=published, url="https://example.com/a",
            )
        ]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    cursor = store.get_cursor(conn, "reuters_business")
    assert cursor > published


def test_dedup_match_escalates_severity_and_notifies_on_upgrade():
    """
    Regression test for a real gap found 2026-09-17: a dedup match used
    to silently discard the new article's own severity, so a story that
    started Medium (LLM-judged) and later escalated to an unambiguous
    hard-rule High event never got upgraded or re-notified -- it was
    just appended as routine corroboration. Now it must upgrade the
    stored severity and fire an escalation push.
    """
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")

    existing_id = store.record_alert(
        conn, headline="Oil prices tick up on OPEC+ chatter", source="cnbc_top_news", url="https://a",
        published_utc=dt.datetime.now(UTC), detected_at_utc=dt.datetime.now(UTC),
        category="energy", severity="Medium", classification_method="llm", rationale=None, affected_symbols=[],
    )

    escalating_article = _article("Oil prices tick up as Strait of Hormuz closed after naval clash")

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.dedup.find_existing_alert", return_value=existing_id), \
         patch("alerting.poll_once.notify_telegram.send_alert", return_value=True) as mock_send:
        mock_source_cls.return_value.fetch.return_value = [escalating_article]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    row = store.get_alert(conn, existing_id)
    assert row.severity == "High"
    assert mock_send.called
    assert mock_send.call_args.kwargs.get("is_escalation") is True
    assert row.delivery_status == "sent"


def test_dedup_match_does_not_downgrade_or_renotify_on_equal_or_lower_severity():
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")

    existing_id = store.record_alert(
        conn, headline="Strait of Hormuz closed after naval clash", source="cnbc_top_news", url="https://a",
        published_utc=dt.datetime.now(UTC), detected_at_utc=dt.datetime.now(UTC),
        category="energy", severity="High", classification_method="rule_tier", rationale=None, affected_symbols=[],
    )

    same_story_article = _article("Strait of Hormuz remains closed following naval clash")

    with patch("alerting.poll_once.RSSNewsSource") as mock_source_cls, \
         patch("alerting.poll_once.dedup.find_existing_alert", return_value=existing_id), \
         patch("alerting.poll_once.notify_telegram.send_alert") as mock_send:
        mock_source_cls.return_value.fetch.return_value = [same_story_article]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)

    row = store.get_alert(conn, existing_id)
    assert row.severity == "High"
    mock_send.assert_not_called()


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
