# alerting/poll_once.py
"""
Task Scheduler entry point — one poll cycle across all free RSS sources,
then exits. Deliberately stateless between invocations (all state lives
in alerting/store.py's standalone DB) so the OS scheduler is the only
supervisor this needs: a crash or reboot just means the next scheduled
tick runs normally. See docs/superpowers/specs/2026-09-14-realtime-news-shock-alerting-design.md.

Notification timeliness (2026-10): articles are triaged across ALL sources
first, then hard-rule hits (no LLM, instantly High) are processed and
pushed BEFORE any ambiguous candidate waits on an LLM, and the LLM gets a
bounded total time budget per cycle. A slow or dead classifier therefore
can never delay a clear-cut alert, and can never push a cycle past the
2-minute scheduler cadence.
"""
from __future__ import annotations

import datetime as dt
import time

from alerting import dedup, direction, llm_classify, notify_telegram, store
from alerting.symbol_relevance import affected_symbols
from alerting.triage import triage_article, TriageResult
from alerting.taxonomy import NEAR_MISS_LOG_THRESHOLD
from config.settings import LLM_CYCLE_BUDGET_SECONDS, TELEGRAM_MIN_SEVERITY
from data_layer.news_feed import NewsArticle
from data_layer.rss_sources import FREE_PREVIEW_FEEDS, RSSNewsSource
from webapp.store import get_connection as get_webapp_connection, list_tracked_symbols

_DEFAULT_LOOKBACK = dt.timedelta(minutes=10)  # first-ever run for a source, or a missing cursor

_SEVERITY_RANK = {"Low": 0, "Medium": 1, "High": 2}

_METHOD_BY_PROVIDER = {"claude": "llm", "ollama": "llm_ollama"}


def _should_push(severity: str, classification_failed: bool) -> bool:
    """
    A classification that failed on every provider has no trustworthy
    severity, so it is always pushed (labelled UNCLASSIFIED) rather than
    risk a silent miss; everything else is pushed at or above
    TELEGRAM_MIN_SEVERITY.
    """
    if classification_failed:
        return True
    return _SEVERITY_RANK.get(severity, -1) >= _SEVERITY_RANK[TELEGRAM_MIN_SEVERITY]


def run_poll_cycle(conn=None, webapp_conn=None) -> None:
    conn = conn if conn is not None else store.get_connection()
    webapp_conn = webapp_conn if webapp_conn is not None else get_webapp_connection()
    now = dt.datetime.now(dt.timezone.utc)

    fetched: list[tuple[str, dt.datetime, list[NewsArticle]]] = []
    for name, url in FREE_PREVIEW_FEEDS.items():
        since = store.get_cursor(conn, name) or (now - _DEFAULT_LOOKBACK)
        try:
            articles = RSSNewsSource(name, url).fetch(query="", since_utc=since, limit=50)
        except Exception as exc:  # noqa: BLE001 -- one broken feed must never block the others
            print(f"[poll_once] WARNING: fetch failed for source {name!r}: {exc}")
            continue
        fetched.append((name, since, articles))

    hard_rule: list[tuple[NewsArticle, TriageResult]] = []
    ambiguous: list[tuple[NewsArticle, TriageResult]] = []
    for _name, _since, articles in fetched:
        for article in articles:
            result = triage_article(article)
            if not result.matched:
                if result.near_miss_score is not None and result.near_miss_score >= NEAR_MISS_LOG_THRESHOLD:
                    store.record_near_miss(conn, article.title, result.near_miss_category, result.near_miss_score)
                continue
            (hard_rule if result.rule_tier_hit else ambiguous).append((article, result))

    for article, result in hard_rule:
        _process_matched(conn, webapp_conn, article, result)

    llm_deadline = time.monotonic() + LLM_CYCLE_BUDGET_SECONDS
    for article, result in ambiguous:
        _process_matched(conn, webapp_conn, article, result, llm_deadline=llm_deadline)

    for name, since, articles in fetched:
        _advance_cursor(conn, name, since, articles)


def _advance_cursor(conn, name: str, since: dt.datetime, articles: list[NewsArticle]) -> None:
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


def _classify(article: NewsArticle, result: TriageResult, conn, llm_deadline) -> llm_classify.ClassificationResult:
    if llm_deadline is not None and time.monotonic() >= llm_deadline:
        print(f"[poll_once] WARNING: LLM time budget for this cycle is spent -- {article.title!r} goes out unclassified")
        return llm_classify.ClassificationResult(
            category=result.category, severity="Medium", classification_failed=True,
            rationale="LLM time budget for this poll cycle was spent -- unclassified, needs manual review.",
        )
    return llm_classify.classify_candidate(article, result, conn=conn)


def _process_matched(conn, webapp_conn, article: NewsArticle, result: TriageResult, llm_deadline=None) -> None:
    classification_failed = False
    if result.rule_tier_hit:
        category, severity, method, rationale = result.category, "High", "rule_tier", None
        polarity = direction.rule_polarity(result.matched_keywords)
    else:
        classification = _classify(article, result, conn, llm_deadline)
        category = classification.category
        severity = classification.severity
        classification_failed = classification.classification_failed
        method = "llm_failed_fallback" if classification_failed else _METHOD_BY_PROVIDER.get(classification.provider, "llm")
        rationale = classification.rationale
        polarity = classification.polarity

    existing_id = dedup.find_existing_alert(article.title, category, conn)
    if existing_id is not None:
        store.append_source(conn, existing_id, article.source, article.url, article.published_utc)
        _maybe_escalate(conn, existing_id, category, severity, rationale, classification_failed)
        return

    tracked_symbols = list_tracked_symbols(webapp_conn)
    impacts = affected_symbols(category, tracked_symbols)
    affected_dicts = direction.describe_impacts(impacts, category, polarity)

    alert_id = store.record_alert(
        conn, headline=article.title, source=article.source, url=article.url,
        published_utc=article.published_utc, detected_at_utc=dt.datetime.now(dt.timezone.utc),
        category=category, severity=severity, classification_method=method,
        rationale=rationale, affected_symbols=affected_dicts,
    )

    if _should_push(severity, classification_failed):
        sent = notify_telegram.send_alert(
            article.title, category, severity, rationale, affected_dicts,
            [{"source": article.source, "url": article.url}],
            classification_failed=classification_failed,
        )
        store.set_delivery_status(conn, alert_id, "sent" if sent else "failed")


def _maybe_escalate(
    conn, alert_id: int, new_category: str, new_severity: str, new_rationale,
    new_classification_failed: bool = False,
) -> None:
    """
    A dedup match means this article is corroborating an ALREADY-KNOWN
    story, already appended as a source by the caller -- but its own
    freshly-computed severity might read more severe than the existing
    alert's stored one (e.g. the story was first caught as Medium via
    LLM judgment, then a later article hits an unambiguous hard-rule
    pattern). If so, upgrade the stored severity and, if that severity
    clears the Telegram threshold, send a fresh push labeled as an
    escalation rather than silently treating a genuine escalation as
    routine corroboration. Never downgrades -- that judgment call stays
    manual. A severity that is only the fallback guess from a failed
    classification is not a real assessment and never escalates anything.
    """
    if new_classification_failed:
        return
    existing = store.get_alert(conn, alert_id)
    if existing is None:
        return  # shouldn't happen (caller just appended to this id), but never crash on it
    if _SEVERITY_RANK.get(new_severity, -1) <= _SEVERITY_RANK.get(existing.severity, -1):
        return

    store.set_severity(conn, alert_id, new_severity)
    if _should_push(new_severity, False):
        sent = notify_telegram.send_alert(
            existing.headline, new_category, new_severity, new_rationale,
            existing.affected_symbols, existing.sources, is_escalation=True,
        )
        store.set_delivery_status(conn, alert_id, "sent" if sent else "failed")


if __name__ == "__main__":
    run_poll_cycle()
