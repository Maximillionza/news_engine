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


# --- direction: leans attached to stored and pushed alerts ---

def _run_tracking_xau_us30(article_title, triage, classification=None):
    conn = store.get_connection(":memory:")
    webapp_conn = webapp_store.get_connection(":memory:")
    for symbol in ("XAUUSD", "US30"):
        webapp_conn.execute("INSERT INTO tracked_symbols (symbol) VALUES (?)", (symbol,))
    webapp_conn.commit()
    send = MagicMock(return_value=True)
    with patch("alerting.poll_once.FREE_PREVIEW_FEEDS", {"feed_a": "u"}), \
         patch("alerting.poll_once.RSSNewsSource") as source_cls, \
         patch("alerting.poll_once.triage_article", return_value=triage), \
         patch("alerting.poll_once.llm_classify.classify_candidate", MagicMock(return_value=classification)), \
         patch("alerting.poll_once.notify_telegram.send_alert", send):
        source_cls.return_value.fetch.return_value = [_article(article_title)]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)
    stored = store.list_recent_alerts(conn, _ALL_TIME)[0].affected_symbols
    return {s["symbol"]: s for s in stored}, send


def test_hard_rule_alert_carries_its_patterns_polarity_into_leans():
    triage = _triage_result("energy", rule_tier_hit=True)
    triage.matched_keywords = ["strait of hormuz closed"]
    stored, send = _run_tracking_xau_us30("Strait of Hormuz closed after naval clash", triage)

    assert stored["XAUUSD"]["lean"] == "buy" and stored["US30"]["lean"] == "sell"
    pushed = send.call_args.args[4]  # affected_symbols handed to Telegram carries the same leans
    assert {s["symbol"]: s["lean"] for s in pushed} == {"XAUUSD": "buy", "US30": "sell"}


def test_llm_relief_polarity_flips_the_lean_for_the_same_category():
    classification = ClassificationResult(
        category="energy", severity="Medium", rationale="reopening", provider="ollama", polarity="relief")
    stored, _ = _run_tracking_xau_us30("Iran agrees to reopen Strait of Hormuz", _triage_result("energy"), classification)
    assert stored["US30"]["lean"] == "buy"
    assert stored["XAUUSD"]["lean"] == "mixed"


def test_unclear_polarity_reads_no_clear_lean_rather_than_a_guess():
    classification = ClassificationResult(
        category="energy", severity="Low", rationale="commentary", provider="ollama", polarity="unclear")
    stored, _ = _run_tracking_xau_us30("Analysts debate oil outlook", _triage_result("energy"), classification)
    assert {s["lean"] for s in stored.values()} == {"mixed"}


def test_failed_classification_gets_no_clear_lean():
    failed = ClassificationResult(
        category="energy", severity="Medium", rationale="providers down", classification_failed=True)
    stored, send = _run_tracking_xau_us30("Some oil story", _triage_result("energy"), failed)
    assert {s["lean"] for s in stored.values()} == {"mixed"}
    assert send.call_args.kwargs["classification_failed"] is True


def test_unscheduled_rate_cut_is_dovish_so_gold_and_equities_stay_no_clear_lean():
    triage = _triage_result("central_bank", rule_tier_hit=True)
    triage.matched_keywords = ["unscheduled rate cut"]
    stored, _ = _run_tracking_xau_us30("Central bank announces unscheduled rate cut", triage)
    assert {s["lean"] for s in stored.values()} == {"mixed"}


# --- B2: no-US-link cap, new fields, escalation path, classifier-down notice ---

import pytest  # noqa: E402

from alerting.direction import NO_US_LINK_WHY  # noqa: E402
from alerting.us_link import cap_note  # noqa: E402

_NO_LINK_HEADLINES = [
    ("Russia's Yandex says data centre in Vladimir area shut down after drone attack", "geopolitical_conflict", "RU"),
    ("Russia builds major new drone attack base", "geopolitical_conflict", "RU"),
    ("Houthi attack on Yemeni government military camp", "energy", "YE"),
    ("Unrest spreads across France as protesters clash with police", "geopolitical_conflict", "FR"),
]


def _classification(category, severity="High", polarity="escalation", country=None, us_link=None, **kw):
    return ClassificationResult(
        category=category, severity=severity, rationale="why", provider="ollama",
        polarity=polarity, country=country, us_link=us_link, **kw)


def _tracked_webapp(symbols=("XAUUSD", "US30")):
    webapp_conn = webapp_store.get_connection(":memory:")
    for symbol in symbols:
        webapp_conn.execute("INSERT INTO tracked_symbols (symbol) VALUES (?)", (symbol,))
    webapp_conn.commit()
    return webapp_conn


def _cycle(conn, webapp_conn, title, triage, classification, send=None, notice=None, existing_id=None):
    """One poll cycle, one article; Telegram alert and notice sends are both mocked."""
    send = send if send is not None else MagicMock(return_value=True)
    notice = notice if notice is not None else MagicMock(return_value=True)
    dedup_patch = patch("alerting.poll_once.dedup.find_existing_alert", return_value=existing_id)
    with patch("alerting.poll_once.FREE_PREVIEW_FEEDS", {"feed_a": "u"}), \
         patch("alerting.poll_once.RSSNewsSource") as source_cls, \
         patch("alerting.poll_once.triage_article", return_value=triage), \
         patch("alerting.poll_once.llm_classify.classify_candidate", MagicMock(return_value=classification)), \
         patch("alerting.poll_once.notify_telegram.send_notice", notice), \
         patch("alerting.poll_once.notify_telegram.send_alert", send), dedup_patch:
        source_cls.return_value.fetch.return_value = [_article(title)]
        run_poll_cycle(conn=conn, webapp_conn=webapp_conn)
    return send, notice


def _run_full(title, triage, classification, symbols=("XAUUSD", "US30")):
    """Returns (stored alert row, send mock) for one fresh alert."""
    conn = store.get_connection(":memory:")
    send, _ = _cycle(conn, _tracked_webapp(symbols), title, triage, classification)
    return store.list_recent_alerts(conn, _ALL_TIME)[0], send


@pytest.mark.parametrize("headline,category,country", _NO_LINK_HEADLINES)
def test_no_us_link_events_are_not_high_and_carry_no_lean(headline, category, country):
    classification = _classification(category, country=country, us_link="none")
    alert, send = _run_full(headline, _triage_result(category), classification)

    assert alert.severity == "Medium"
    assert alert.original_severity == "High"
    assert alert.capped_no_us_link is True
    assert alert.us_link == "none" and alert.country == country
    assert alert.affected_symbols  # channels still shown, only the lean is withheld
    assert all(s["lean"] == "mixed" and s["lean_why"] == NO_US_LINK_WHY for s in alert.affected_symbols)
    assert send.call_args.args[2] == "Medium"
    assert NO_US_LINK_WHY in send.call_args.kwargs["cap_note"]
    assert not any(s["lean"] in ("buy", "sell") for s in send.call_args.args[4])


def test_unknown_us_link_keeps_todays_high_and_leans():
    classification = _classification("geopolitical_conflict", country="RU", us_link=None)
    alert, send = _run_full(
        "Russia's Yandex says data centre in Vladimir area shut down after drone attack",
        _triage_result("geopolitical_conflict"), classification)
    stored = {s["symbol"]: s["lean"] for s in alert.affected_symbols}
    assert alert.severity == "High" and alert.capped_no_us_link is False
    assert stored == {"XAUUSD": "buy", "US30": "sell"}
    assert send.call_args.kwargs["cap_note"] is None


def test_global_supply_high_keeps_its_leans():
    classification = _classification("energy", country="XX", us_link="global_supply")
    alert, _ = _run_full("Tanker struck in Gulf as Iran escalates attacks", _triage_result("energy"), classification)
    assert alert.severity == "High" and alert.capped_no_us_link is False
    assert {s["symbol"]: s["lean"] for s in alert.affected_symbols} == {"XAUUSD": "buy", "US30": "sell"}


def test_rule_tier_hit_stores_its_mapped_country_and_us_link():
    triage = _triage_result("energy", rule_tier_hit=True)
    triage.matched_keywords = ["strait of hormuz closed"]
    alert, _ = _run_full("Strait of Hormuz closed after naval clash", triage, None)
    assert (alert.country, alert.us_link, alert.polarity) == ("XX", "global_supply", "escalation")
    assert alert.severity == "High" and alert.capped_no_us_link is False


def test_gold_bar_tariff_alert_reaches_xauusd_with_a_mixed_lean():
    classification = _classification("trade_policy", country="US", us_link="direct")
    alert, _ = _run_full("US slaps tariffs on imported gold bars", _triage_result("trade_policy"), classification)
    stored = {s["symbol"]: s for s in alert.affected_symbols}
    assert stored["XAUUSD"]["channel"] == "tariff_bullion" and stored["XAUUSD"]["lean"] == "mixed"
    assert stored["US30"]["lean"] == "sell"


def test_diesel_export_ban_alert_reaches_us30_only():
    classification = _classification("trade_policy", country="RU", us_link=None)
    alert, _ = _run_full("Russia extends diesel export ban to year-end", _triage_result("trade_policy"), classification)
    assert [s["symbol"] for s in alert.affected_symbols] == ["US30"]


def _capped_ru_alert(conn):
    return store.record_alert(
        conn, headline="Russia builds major new drone attack base", source="cnbc_top_news", url="https://a",
        published_utc=dt.datetime.now(UTC), detected_at_utc=dt.datetime.now(UTC),
        category="geopolitical_conflict", severity="Medium", classification_method="llm_ollama", rationale="r",
        affected_symbols=[{"symbol": "XAUUSD", "channel": "safe_haven", "lean": "mixed", "lean_why": NO_US_LINK_WHY}],
        polarity="escalation", country="RU", us_link="none", capped_no_us_link=True, original_severity="High",
    )


def test_capped_alert_is_not_escalated_past_medium_by_an_article_with_unknown_us_link():
    conn = store.get_connection(":memory:")
    alert_id = _capped_ru_alert(conn)
    triage = _triage_result("geopolitical_conflict", rule_tier_hit=True)
    triage.matched_keywords = ["declares war"]  # rule tier: High, link unknown
    send, _ = _cycle(conn, _tracked_webapp(), "Russia declares war on neighbour again", triage, None,
                     existing_id=alert_id)

    row = store.get_alert(conn, alert_id)
    assert row.severity == "Medium" and row.capped_no_us_link is True
    send.assert_not_called()


def test_global_supply_corroboration_lifts_the_cap_and_restores_leans():
    conn = store.get_connection(":memory:")
    alert_id = _capped_ru_alert(conn)
    classification = _classification("geopolitical_conflict", country="XX", us_link="global_supply")
    send, _ = _cycle(conn, _tracked_webapp(), "Russia drone base threatens Black Sea grain and oil exports",
                     _triage_result("geopolitical_conflict"), classification, existing_id=alert_id)

    row = store.get_alert(conn, alert_id)
    assert row.severity == "High" and row.capped_no_us_link is False and row.us_link == "global_supply"
    assert {s["symbol"]: s["lean"] for s in row.affected_symbols} == {"XAUUSD": "buy", "US30": "sell"}
    assert send.call_args.kwargs["is_escalation"] is True
    assert {s["symbol"]: s["lean"] for s in send.call_args.args[4]} == {"XAUUSD": "buy", "US30": "sell"}


def test_no_us_link_corroboration_caps_an_unknown_link_alert_and_strips_its_leans():
    # Stored at Low with an unknown link (e.g. the model omitted it), so it still carries a real lean.
    conn = store.get_connection(":memory:")
    alert_id = store.record_alert(
        conn, headline="Russia builds major new drone attack base", source="cnbc_top_news", url="https://a",
        published_utc=dt.datetime.now(UTC), detected_at_utc=dt.datetime.now(UTC),
        category="geopolitical_conflict", severity="Low", classification_method="llm_ollama", rationale="r",
        affected_symbols=[{"symbol": "XAUUSD", "channel": "safe_haven", "lean": "buy", "lean_why": "w"}],
        polarity="escalation", country=None, us_link=None, capped_no_us_link=False, original_severity="Low",
    )
    classification = _classification("geopolitical_conflict", country="RU", us_link="none")
    send, _ = _cycle(conn, _tracked_webapp(), "Russia's new drone base is a domestic build-up, analysts say",
                     _triage_result("geopolitical_conflict"), classification, existing_id=alert_id)

    row = store.get_alert(conn, alert_id)
    assert row.severity == "Medium" and row.capped_no_us_link is True
    assert row.us_link == "none" and row.country == "RU" and row.original_severity == "High"
    assert row.affected_symbols
    assert all(s["lean"] == "mixed" and s["lean_why"] == NO_US_LINK_WHY for s in row.affected_symbols)
    assert send.call_args.args[2] == "Medium" and send.call_args.kwargs["is_escalation"] is True
    assert all(s["lean"] == "mixed" for s in send.call_args.args[4])
    assert send.call_args.kwargs["cap_note"] == cap_note("High", True)


def test_capped_low_alert_escalated_to_medium_records_the_raw_high_behind_the_cap():
    conn = store.get_connection(":memory:")
    alert_id = store.record_alert(
        conn, headline="Russia builds major new drone attack base", source="cnbc_top_news", url="https://a",
        published_utc=dt.datetime.now(UTC), detected_at_utc=dt.datetime.now(UTC),
        category="geopolitical_conflict", severity="Low", classification_method="llm_ollama", rationale="r",
        affected_symbols=[{"symbol": "XAUUSD", "channel": "safe_haven", "lean": "mixed", "lean_why": NO_US_LINK_WHY}],
        polarity="escalation", country="RU", us_link="none", capped_no_us_link=True, original_severity="Low",
    )
    triage = _triage_result("geopolitical_conflict", rule_tier_hit=True)
    triage.matched_keywords = ["declares war"]  # rule tier: High, link unknown -> inherits the stored "none"
    send, _ = _cycle(conn, _tracked_webapp(), "Russia declares war on neighbour", triage, None,
                     existing_id=alert_id)

    row = store.get_alert(conn, alert_id)
    assert row.severity == "Medium" and row.capped_no_us_link is True and row.original_severity == "High"
    assert all(s["lean"] == "mixed" for s in row.affected_symbols)
    assert all(s["lean"] == "mixed" for s in send.call_args.args[4])
    assert send.call_args.kwargs["cap_note"] == cap_note("High", True)


_FAILED = ClassificationResult(
    category="energy", severity="Medium", rationale="all providers down: connection refused",
    classification_failed=True, all_providers_failed=True)


def test_outage_notice_sent_once_per_utc_day():
    conn = store.get_connection(":memory:")
    webapp_conn = _tracked_webapp()
    notice = MagicMock(return_value=True)
    day1 = dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC)
    with patch("alerting.poll_once._utcnow", return_value=day1):
        _cycle(conn, webapp_conn, "Oil story alpha", _triage_result("energy"), _FAILED, notice=notice)
        _cycle(conn, webapp_conn, "Quarterly bakery wheat harvest bravo", _triage_result("energy"), _FAILED, notice=notice)
    assert notice.call_count == 1
    assert "Shock classifier down" in notice.call_args.args[0]
    assert conn.execute("SELECT COUNT(*) FROM classifier_outage_notices").fetchone()[0] == 1

    with patch("alerting.poll_once._utcnow", return_value=day1 + dt.timedelta(days=1)):
        _cycle(conn, webapp_conn, "Gas pipeline charlie story", _triage_result("energy"), _FAILED, notice=notice)
    assert notice.call_count == 2


def test_failed_notice_send_is_retried_and_success_is_once_per_utc_day():
    conn = store.get_connection(":memory:")
    webapp_conn = _tracked_webapp()
    notice = MagicMock(side_effect=[False, True, True])
    day = dt.datetime(2026, 10, 21, 8, 0, tzinfo=UTC)
    with patch("alerting.poll_once._utcnow", return_value=day):
        for title in ("Oil story alpha", "Wheat harvest bravo", "Pipeline charlie story"):
            _cycle(conn, webapp_conn, title, _triage_result("energy"), _FAILED, notice=notice)
    assert notice.call_count == 2  # failed once, retried and succeeded, then done for the day


def test_budget_spent_fallback_never_sends_an_outage_notice():
    conn = store.get_connection(":memory:")
    notice = MagicMock(return_value=True)
    with patch("alerting.poll_once.LLM_CYCLE_BUDGET_SECONDS", 0):
        _cycle(conn, _tracked_webapp(), "Oil story alpha", _triage_result("energy"), MagicMock(), notice=notice)
    assert len(store.list_recent_alerts(conn, _ALL_TIME)) == 1
    notice.assert_not_called()


def _freshness_run(published_minutes_ago, now):
    conn = store.get_connection(":memory:")
    article = NewsArticle(
        title="Strait of Hormuz closed", summary="", source="reuters_business", source_type="rss_reuters_business",
        published_utc=now - dt.timedelta(minutes=published_minutes_ago), url="https://example.com/h")
    send = MagicMock(return_value=True)
    with patch("alerting.poll_once._utcnow", return_value=now), \
         patch("alerting.poll_once.FREE_PREVIEW_FEEDS", {"feed_a": "u"}), \
         patch("alerting.poll_once.RSSNewsSource") as source_cls, \
         patch("alerting.poll_once.triage_article", return_value=_triage_result(rule_tier_hit=True)), \
         patch("alerting.poll_once.notify_telegram.send_alert", send):
        source_cls.return_value.fetch.return_value = [article]
        run_poll_cycle(conn=conn, webapp_conn=_tracked_webapp())
    return conn, send


def test_pushed_alert_carries_its_freshness_line():
    now = dt.datetime(2026, 10, 21, 12, 42, tzinfo=UTC)
    _, send = _freshness_run(3, now)
    assert send.call_args.kwargs["freshness_line"].endswith("+3 min · Fresh")


def test_very_stale_story_is_still_pushed_with_its_band():
    now = dt.datetime(2026, 10, 21, 12, 42, tzinfo=UTC)
    _, send = _freshness_run(465, now)
    send.assert_called_once()
    assert send.call_args.kwargs["freshness_line"].endswith("Very stale")


def test_escalation_push_shows_the_original_story_age():
    conn = store.get_connection(":memory:")
    published = dt.datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    alert_id = store.record_alert(
        conn, headline="Hormuz tension", source="cnbc_top_news", url="https://a",
        published_utc=published, detected_at_utc=published + dt.timedelta(minutes=4),
        category="energy", severity="Low", classification_method="llm_ollama", rationale="r",
        affected_symbols=[])
    triage = _triage_result("energy", rule_tier_hit=True)
    triage.matched_keywords = ["strait of hormuz"]
    # The corroborating article is detected much later; the line must still describe the ORIGINAL story.
    with patch("alerting.poll_once._utcnow", return_value=published + dt.timedelta(hours=3)):
        send, _ = _cycle(conn, _tracked_webapp(), "Strait of Hormuz closed", triage, None, existing_id=alert_id)
    assert send.call_args.kwargs["is_escalation"] is True
    assert send.call_args.kwargs["freshness_line"] == "Published 14:00 SAST · +4 min · Fresh"
