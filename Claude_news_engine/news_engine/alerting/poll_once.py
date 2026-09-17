# alerting/poll_once.py
"""
Task Scheduler entry point — one poll cycle across all free RSS sources,
then exits. Deliberately stateless between invocations (all state lives
in alerting/store.py's standalone DB) so the OS scheduler is the only
supervisor this needs: a crash or reboot just means the next scheduled
tick runs normally. See docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md.
"""
from __future__ import annotations

import datetime as dt

from alerting import dedup, llm_classify, notify_telegram, store
from alerting.symbol_relevance import affected_symbols
from alerting.triage import triage_article
from alerting.taxonomy import NEAR_MISS_LOG_THRESHOLD
from data_layer.news_feed import NewsArticle
from data_layer.rss_sources import FREE_PREVIEW_FEEDS, RSSNewsSource
from webapp.store import get_connection as get_webapp_connection, list_tracked_symbols

_DEFAULT_LOOKBACK = dt.timedelta(minutes=10)  # first-ever run for a source, or a missing cursor


def run_poll_cycle(conn=None, webapp_conn=None) -> None:
    conn = conn if conn is not None else store.get_connection()
    webapp_conn = webapp_conn if webapp_conn is not None else get_webapp_connection()
    now = dt.datetime.now(dt.timezone.utc)
    for name, url in FREE_PREVIEW_FEEDS.items():
        _poll_source(conn, webapp_conn, name, url, now)


def _poll_source(conn, webapp_conn, name: str, url: str, now: dt.datetime) -> None:
    since = store.get_cursor(conn, name) or (now - _DEFAULT_LOOKBACK)
    try:
        articles = RSSNewsSource(name, url).fetch(query="", since_utc=since, limit=50)
    except Exception as exc:  # noqa: BLE001 -- one broken feed must never block the others
        print(f"[poll_once] WARNING: fetch failed for source {name!r}: {exc}")
        return
    for article in articles:
        _process_article(conn, webapp_conn, article)
    # Advance the cursor to the newest published_utc actually seen this
    # cycle, not to wall-clock `now` -- RSSNewsSource.fetch() filters on
    # published < since_utc, so anchoring to `now` can silently drop an
    # article that only appears in the feed a few minutes after its own
    # published_utc (it falls into the gap between two poll cycles and is
    # never seen). An empty poll falls back to the existing `since` value
    # so the cursor never resets backward or gets stuck incorrectly.
    #
    # +1 microsecond past the newest article's own timestamp, not exactly
    # equal to it -- found live 2026-09-17 (real production run): since
    # RSSNewsSource's filter is `published < since_utc` (inclusive of an
    # exact match), setting the cursor to exactly newest_seen guarantees
    # that same article satisfies the filter again next cycle and gets
    # fully reprocessed -- confirmed live as 46 duplicate append_source()
    # calls on one real alert over 2.5 hours. No functional harm (dedup
    # already prevents a second alert/Telegram push), but pure noise in
    # sources_json. This one-microsecond nudge closes the exact-equality
    # gap without touching data_layer/rss_sources.py's shared filter,
    # which other, non-alerting consumers also rely on.
    newest_seen = max((a.published_utc for a in articles), default=None)
    if newest_seen is not None:
        store.set_cursor(conn, name, newest_seen + dt.timedelta(microseconds=1))
    else:
        store.set_cursor(conn, name, since)


def _process_article(conn, webapp_conn, article: NewsArticle) -> None:
    result = triage_article(article)
    if not result.matched:
        if result.near_miss_score is not None and result.near_miss_score >= NEAR_MISS_LOG_THRESHOLD:
            store.record_near_miss(conn, article.title, result.near_miss_category, result.near_miss_score)
        return

    if result.rule_tier_hit:
        category, severity, method, rationale = result.category, "High", "rule_tier", None
    else:
        classification = llm_classify.classify_candidate(article, result)
        category = classification.category
        severity = classification.severity
        method = "llm_failed_fallback" if classification.classification_failed else "llm"
        rationale = classification.rationale

    existing_id = dedup.find_existing_alert(article.title, category, conn)
    if existing_id is not None:
        store.append_source(conn, existing_id, article.source, article.url, article.published_utc)
        return

    tracked_symbols = list_tracked_symbols(webapp_conn)
    impacts = affected_symbols(category, tracked_symbols)
    affected_dicts = [{"symbol": i.symbol, "channel": i.channel} for i in impacts]

    alert_id = store.record_alert(
        conn, headline=article.title, source=article.source, url=article.url,
        published_utc=article.published_utc, detected_at_utc=dt.datetime.now(dt.timezone.utc),
        category=category, severity=severity, classification_method=method,
        rationale=rationale, affected_symbols=affected_dicts,
    )

    if severity == "High":
        sent = notify_telegram.send_alert(
            article.title, category, severity, rationale, affected_dicts,
            [{"source": article.source, "url": article.url}],
        )
        store.set_delivery_status(conn, alert_id, "sent" if sent else "failed")


if __name__ == "__main__":
    run_poll_cycle()
