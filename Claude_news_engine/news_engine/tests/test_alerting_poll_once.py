# tests/test_alerting_poll_once.py
from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

from alerting import store
from alerting.llm_classify import ClassificationResult
from alerting.poll_once import run_poll_cycle
from alerting.triage import TriageResult
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


# --- LLM provider chain, push policy and cycle ordering (2026-10) ---

_ALL_TIME = dt.datetime(2020, 1, 1, tzinfo=UTC)


def _triage_result(category="energy", rule_tier_hit=False):
    return TriageResult(
        matched=True, category=category, rule_tier_hit=rule_tier_hit,
        matched_keywords=[], near_miss_score=None,
    )


def _run_cycle_with(articles, triage_by_title, classify=None, send=None):
    """One poll cycle over a single fake feed, triage and classification stubbed per headline."""
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")
    send = send or MagicMock(return_value=True)
    with patch("alerting.poll_once.FREE_PREVIEW_FEEDS", {"feed_a": "https://example.com/feed"}), \
         patch("alerting.poll_once.RSSNewsSource") as source_cls, \
         patch("alerting.poll_once.triage_article", side_effect=lambda a: triage_by_title[a.title]), \
         patch("alerting.poll_once.llm_classify.classify_candidate", classify or MagicMock()), \
         patch("alerting.poll_once.notify_telegram.send_alert", send):
        source_cls.return_value.fetch.return_value = articles
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)
    return conn, send


def test_medium_alert_from_ollama_is_pushed_and_recorded_with_ollama_method():
    classify = MagicMock(return_value=ClassificationResult(
        category="energy", severity="Medium", rationale="routine", provider="ollama"))
    conn, send = _run_cycle_with(
        [_article("Oil prices tick higher on OPEC+ chatter")],
        {"Oil prices tick higher on OPEC+ chatter": _triage_result()}, classify=classify)

    alert = store.list_recent_alerts(conn, _ALL_TIME)[0]
    assert alert.severity == "Medium"
    assert alert.classification_method == "llm_ollama"
    assert alert.delivery_status == "sent"
    assert send.call_count == 1
    assert send.call_args.args[2] == "Medium"
    assert send.call_args.kwargs["classification_failed"] is False


def test_low_alert_is_pushed_under_the_default_threshold():
    classify = MagicMock(return_value=ClassificationResult(
        category="energy", severity="Low", rationale="priced in", provider="claude"))
    conn, send = _run_cycle_with(
        [_article("Oil drifts on OPEC+ remarks")],
        {"Oil drifts on OPEC+ remarks": _triage_result()}, classify=classify)

    assert store.list_recent_alerts(conn, _ALL_TIME)[0].classification_method == "llm"
    assert send.call_count == 1
    assert send.call_args.args[2] == "Low"


def test_threshold_blocks_a_medium_alert_but_never_an_unclassified_one():
    ok = MagicMock(return_value=ClassificationResult(
        category="energy", severity="Medium", rationale="r", provider="claude"))
    failed = MagicMock(return_value=ClassificationResult(
        category="energy", severity="Medium", rationale="all providers down", classification_failed=True))

    with patch("alerting.poll_once.TELEGRAM_MIN_SEVERITY", "High"):
        _, send_ok = _run_cycle_with([_article("Story A")], {"Story A": _triage_result()}, classify=ok)
        conn, send_failed = _run_cycle_with([_article("Story B")], {"Story B": _triage_result()}, classify=failed)

    send_ok.assert_not_called()
    assert send_failed.call_count == 1
    assert send_failed.call_args.kwargs["classification_failed"] is True
    assert store.list_recent_alerts(conn, _ALL_TIME)[0].classification_method == "llm_failed_fallback"


def test_hard_rule_alert_is_pushed_before_any_ambiguous_candidate_is_classified():
    """An ambiguous headline sitting FIRST in the feed must not delay a clear-cut High behind its LLM call."""
    order = []

    def classify(article, triage, conn=None):
        order.append(f"classify:{article.title}")
        return ClassificationResult(category="energy", severity="Medium", rationale="r", provider="ollama")

    def send(headline, *args, **kwargs):
        order.append(f"send:{headline}")
        return True

    _run_cycle_with(
        [_article("Ambiguous oil story"), _article("Strait of Hormuz closed")],
        {"Ambiguous oil story": _triage_result("energy"),
         "Strait of Hormuz closed": _triage_result("geopolitical_conflict", rule_tier_hit=True)},
        classify=MagicMock(side_effect=classify), send=MagicMock(side_effect=send))

    assert order == [
        "send:Strait of Hormuz closed",
        "classify:Ambiguous oil story",
        "send:Ambiguous oil story",
    ]


def test_spent_llm_budget_sends_remaining_candidates_unclassified_without_calling_the_llm():
    classify = MagicMock()
    with patch("alerting.poll_once.LLM_CYCLE_BUDGET_SECONDS", 0):
        conn, send = _run_cycle_with(
            [_article("Story A"), _article("Story B")],
            {"Story A": _triage_result("energy"), "Story B": _triage_result("central_bank")},
            classify=classify)

    classify.assert_not_called()
    alerts = store.list_recent_alerts(conn, _ALL_TIME)
    assert len(alerts) == 2
    assert all(a.classification_method == "llm_failed_fallback" for a in alerts)
    assert send.call_count == 2
    assert all(call.kwargs["classification_failed"] is True for call in send.call_args_list)


def test_provider_chain_receives_the_alerts_connection_for_cooldown_state():
    classify = MagicMock(return_value=ClassificationResult(
        category="energy", severity="Low", rationale="r", provider="claude"))
    conn, _ = _run_cycle_with([_article("Story A")], {"Story A": _triage_result()}, classify=classify)
    assert classify.call_args.kwargs["conn"] is conn


def _run_dedup_match_cycle(existing_id, conn, classification, send):
    webapp_conn = webapp_store.get_connection(":memory:")
    with patch("alerting.poll_once.FREE_PREVIEW_FEEDS", {"feed_a": "u"}), \
         patch("alerting.poll_once.RSSNewsSource") as source_cls, \
         patch("alerting.poll_once.triage_article", return_value=_triage_result()), \
         patch("alerting.poll_once.llm_classify.classify_candidate", MagicMock(return_value=classification)), \
         patch("alerting.poll_once.dedup.find_existing_alert", return_value=existing_id), \
         patch("alerting.poll_once.notify_telegram.send_alert", send):
        source_cls.return_value.fetch.return_value = [_article("Oil drifts on OPEC+ remarks again")]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)


def _existing_low_alert(conn):
    return store.record_alert(
        conn, headline="Oil drifts on OPEC+ remarks", source="cnbc_top_news", url="https://a",
        published_utc=dt.datetime.now(UTC), detected_at_utc=dt.datetime.now(UTC),
        category="energy", severity="Low", classification_method="llm", rationale=None, affected_symbols=[],
    )


def test_escalation_from_low_to_medium_is_pushed_as_an_escalation():
    conn = store.get_connection(":memory:")
    existing_id = _existing_low_alert(conn)
    send = MagicMock(return_value=True)
    _run_dedup_match_cycle(existing_id, conn, ClassificationResult(
        category="energy", severity="Medium", rationale="r", provider="claude"), send)

    assert store.get_alert(conn, existing_id).severity == "Medium"
    assert send.call_args.args[2] == "Medium"
    assert send.call_args.kwargs["is_escalation"] is True


def test_failed_classification_never_escalates_an_existing_alert():
    conn = store.get_connection(":memory:")
    existing_id = _existing_low_alert(conn)
    send = MagicMock()
    _run_dedup_match_cycle(existing_id, conn, ClassificationResult(
        category="energy", severity="Medium", rationale="providers down", classification_failed=True), send)

    assert store.get_alert(conn, existing_id).severity == "Low"
    send.assert_not_called()
