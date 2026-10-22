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

Incidents (B7, 2026-10-22): follow-up coverage of an event already alerted (same URL re-stamped,
or, against an incident's root headline of the last 24 h, the same named place/actor AND the same
event words, see alerting/incident.py) is LINKED and LABELLED, never suppressed: it is stored on
its incident (visible on the Shock Alerts tab) with no new lean, and pushed once as "Update to
incident #N" only when its severity rises above the incident's highest or its direction flips. A
follow-up of equal severity and direction is stored silently. A failed classification is linked
only by URL, never by the entity rule, so it keeps its UNCLASSIFIED push.
"""
from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from typing import Optional

from alerting import dedup, direction, incident, llm_classify, notify_telegram, store
from alerting.source_backoff import FEED_BACKOFF_AFTER_FAILURES, backoff_delay, in_backoff
from alerting.freshness import freshness_line
from alerting.symbol_relevance import affected_symbols
from alerting.us_link import cap_note, cap_severity, rule_country_us_link
from alerting.triage import triage_article, TriageResult
from alerting.taxonomy import NEAR_MISS_LOG_THRESHOLD
from config.settings import LLM_CYCLE_BUDGET_SECONDS, LOCAL_TZ, TELEGRAM_MIN_SEVERITY
from data_layer.news_feed import NewsArticle
from data_layer.rss_sources import FREE_PREVIEW_FEEDS, RSSNewsSource
from webapp.store import get_connection as get_webapp_connection, list_tracked_symbols

_DEFAULT_LOOKBACK = dt.timedelta(minutes=10)  # first-ever run for a source, or a missing cursor

_SEVERITY_RANK = {"Low": 0, "Medium": 1, "High": 2}

_METHOD_BY_PROVIDER = {"claude": "llm", "ollama": "llm_ollama"}

FOLLOW_UP_LEAN_WHY = "follow-up of incident #{n}: no new lean"  # B7: a silent follow-up adds no lean


@dataclass(frozen=True)
class _Assessment:
    """One article's classification outcome, as the new-alert and follow-up paths both store it."""
    category: str
    severity: str       # after the no-US-link cap
    raw_severity: str   # before the cap
    method: str
    rationale: Optional[str]
    polarity: str
    country: Optional[str]
    us_link: Optional[str]
    capped: bool
    classification_failed: bool


def _utcnow() -> dt.datetime:
    """Isolated seam so tests can move the UTC clock (the outage notice is once per UTC day)."""
    return dt.datetime.now(dt.timezone.utc)


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
    now = _utcnow()

    fetched: list[tuple[str, dt.datetime, list[NewsArticle]]] = []
    for name, url in FREE_PREVIEW_FEEDS.items():
        health = store.get_source_health(conn, name)
        if in_backoff(health, now):
            continue  # B4 O5: a feed that keeps failing is skipped silently until its backoff ends
        since = store.get_cursor(conn, name) or (now - _DEFAULT_LOOKBACK)
        try:
            articles = RSSNewsSource(name, url).fetch(
                query="", since_utc=since, limit=50, raise_on_parse_error=True)
        except Exception as exc:  # noqa: BLE001 -- one broken feed must never block the others
            _record_feed_failure(conn, name, health, now, exc)
            continue
        recovered = store.record_source_success(conn, name, now)
        if recovered is not None and recovered.consecutive_failures >= FEED_BACKOFF_AFTER_FAILURES:
            print(
                f"[poll_once] source {name!r} recovered after {recovered.consecutive_failures} "
                f"consecutive failures (failing since {_sast(recovered.failing_since_utc)})"
            )
        fetched.append((name, since, articles))

    hard_rule: list[tuple[NewsArticle, TriageResult]] = []
    ambiguous: list[tuple[NewsArticle, TriageResult]] = []
    for _name, _since, articles in fetched:
        for article in articles:
            result = triage_article(article)
            if not result.matched:
                if result.near_miss_score is not None and result.near_miss_score >= NEAR_MISS_LOG_THRESHOLD:
                    store.record_near_miss(
                        conn, article.title, result.near_miss_category, result.near_miss_score, seen_at_utc=now)
                continue
            (hard_rule if result.rule_tier_hit else ambiguous).append((article, result))

    for article, result in hard_rule:
        _process_matched(conn, webapp_conn, article, result)

    llm_deadline = time.monotonic() + LLM_CYCLE_BUDGET_SECONDS
    for article, result in ambiguous:
        _process_matched(conn, webapp_conn, article, result, llm_deadline=llm_deadline)

    for name, since, articles in fetched:
        _advance_cursor(conn, name, since, articles)

    store.prune_near_misses(conn, now)  # K15: 30-day retention, bounded per cycle
    store.prune_seen_urls(conn, now)  # B7 K9: 72 h URL memory, bounded per cycle


def _sast(when: Optional[dt.datetime]) -> str:
    return when.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M SAST") if when else "unknown"


def _record_feed_failure(
    conn, name: str, health: Optional[store.SourceHealth], now: dt.datetime, exc: Exception,
) -> None:
    """
    Persists the failure and logs it: a plain warning for the first failures, ONE line when the
    feed enters backoff (3rd consecutive failure), nothing further while it stays down.
    """
    failures = (health.consecutive_failures if health else 0) + 1
    delay = backoff_delay(failures)
    until = now + delay if delay is not None else None
    store.record_source_failure(conn, name, now, str(exc), until)
    if failures < FEED_BACKOFF_AFTER_FAILURES:
        print(f"[poll_once] WARNING: fetch failed for source {name!r}: {exc}")
    elif failures == FEED_BACKOFF_AFTER_FAILURES:
        print(
            f"[poll_once] source {name!r} in backoff after {FEED_BACKOFF_AFTER_FAILURES} consecutive failures, "
            f"skipped until {_sast(until)} (last error: {exc})"
        )


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
    all_providers_failed = False
    if result.rule_tier_hit:
        category, raw_severity, method, rationale = result.category, "High", "rule_tier", None
        polarity = direction.rule_polarity(result.matched_keywords)
        # A rule-tier phrase maps to a fixed (country, us_link) -- never "none", so a hard rule is never capped.
        country, us_link = rule_country_us_link(result.matched_keywords)
    else:
        classification = _classify(article, result, conn, llm_deadline)
        category = classification.category
        raw_severity = classification.severity
        classification_failed = classification.classification_failed
        # Only a real every-provider failure is an outage; the budget-spent fallback sets classification_failed alone.
        all_providers_failed = classification.all_providers_failed
        method = "llm_failed_fallback" if classification_failed else _METHOD_BY_PROVIDER.get(classification.provider, "llm")
        rationale = classification.rationale
        polarity = classification.polarity
        country, us_link = classification.country, classification.us_link

    # B2 K3: an event with no direct US or global-supply link is held at Medium and carries no buy/sell lean.
    severity, capped = cap_severity(raw_severity, us_link)

    detected_at = _utcnow()  # one instant for the stored detection time and the freshness line
    existing_id = dedup.find_existing_alert(article.title, category, conn)
    if existing_id is not None:
        store.append_source(conn, existing_id, article.source, article.url, article.published_utc)
        store.remember_url(conn, article.url, existing_id, detected_at, article.published_utc)  # B7 K9
        _maybe_escalate(
            conn, webapp_conn, existing_id, category, raw_severity, rationale, classification_failed,
            polarity=polarity, country=country, us_link=us_link,
        )
        if all_providers_failed:
            _maybe_notify_classifier_down(conn, rationale, _utcnow())
        return

    assessment = _Assessment(
        category=category, severity=severity, raw_severity=raw_severity, method=method, rationale=rationale,
        polarity=polarity, country=country, us_link=us_link, capped=capped,
        classification_failed=classification_failed,
    )
    # B7 (2026-10-22): a re-stamped URL keeps its first publication time, and a follow-up of an
    # already-alerted incident is stored on it instead of alerting again. A failed classification
    # is never linked by the entity rule (it keeps its UNCLASSIFIED push); only the URL rule applies.
    cand = incident.IncidentCandidate(
        headline=article.title, category=category, polarity=polarity, url=article.url,
        published_utc=article.published_utc, detected_at_utc=detected_at,
        classification_failed=classification_failed,
    )
    first_published = incident.effective_first_published(conn, cand)
    link = incident.find_incident(conn, cand)
    if link is not None:
        _record_follow_up(conn, webapp_conn, article, link, assessment, first_published, detected_at)
    else:
        tracked_symbols = list_tracked_symbols(webapp_conn)
        impacts = affected_symbols(category, tracked_symbols, headline=article.title)
        affected_dicts = direction.describe_impacts(impacts, category, polarity, country=country, us_link=us_link)

        alert_id = store.record_alert(
            conn, headline=article.title, source=article.source, url=article.url,
            published_utc=article.published_utc, detected_at_utc=detected_at,
            category=category, severity=severity, classification_method=method,
            rationale=rationale, affected_symbols=affected_dicts,
            polarity=polarity, country=country, us_link=us_link,
            capped_no_us_link=capped, original_severity=raw_severity,
            first_published_utc=first_published,
        )
        store.remember_url(conn, article.url, alert_id, detected_at, first_published)

        if _should_push(severity, classification_failed):
            sent = notify_telegram.send_alert(
                article.title, category, severity, rationale, affected_dicts,
                [{"source": article.source, "url": article.url}],
                classification_failed=classification_failed,
                cap_note=cap_note(raw_severity, capped),
                freshness_line=freshness_line(first_published, detected_at),
            )
            store.set_delivery_status(conn, alert_id, "sent" if sent else "failed")

    if all_providers_failed:
        _maybe_notify_classifier_down(conn, rationale, _utcnow())


def _record_follow_up(
    conn, webapp_conn, article: NewsArticle, link: incident.IncidentLink, a: _Assessment,
    first_published: dt.datetime, detected_at: dt.datetime,
) -> int:
    """
    B7: stores the article as a follow-up row on its incident and returns the new row's id.
    Pushed once as "Update to incident #N" only when update_reason() finds the severity above
    the incident's highest or the direction flipped (never for a failed classification);
    otherwise it is stored silently (delivery_status "follow_up") and every affected symbol
    reads "mixed": a follow-up adds no new lean. An update row keeps its real leans.
    """
    rows = store.list_incident_alerts(conn, link.incident_id)
    reason = incident.update_reason(rows, a.severity, a.polarity, article.title, a.classification_failed)
    role = "update" if reason else "follow_up"

    impacts = affected_symbols(a.category, list_tracked_symbols(webapp_conn), headline=article.title)
    affected_dicts = direction.describe_impacts(impacts, a.category, a.polarity, country=a.country, us_link=a.us_link)
    if not reason:
        affected_dicts = [
            {**d, "lean": "mixed", "lean_why": FOLLOW_UP_LEAN_WHY.format(n=link.incident_id)} for d in affected_dicts
        ]

    alert_id = store.record_alert(
        conn, headline=article.title, source=article.source, url=article.url,
        published_utc=article.published_utc, detected_at_utc=detected_at,
        category=a.category, severity=a.severity, classification_method=a.method,
        rationale=a.rationale, affected_symbols=affected_dicts,
        polarity=a.polarity, country=a.country, us_link=a.us_link,
        capped_no_us_link=a.capped, original_severity=a.raw_severity,
        incident_id=link.incident_id, incident_role=role, incident_rule=link.rule,
        first_published_utc=first_published,
    )
    store.remember_url(conn, article.url, alert_id, detected_at, first_published)

    if reason and _should_push(a.severity, False):
        sent = notify_telegram.send_alert(
            article.title, a.category, a.severity, a.rationale, affected_dicts,
            [{"source": article.source, "url": article.url}],
            cap_note=cap_note(a.raw_severity, a.capped),
            freshness_line=freshness_line(first_published, detected_at),
            update_of_incident=link.incident_id, update_reason=reason,
        )
        store.set_delivery_status(conn, alert_id, "sent" if sent else "failed")
    elif not reason:
        store.set_delivery_status(conn, alert_id, "follow_up")

    outcome = f"update pushed ({reason})" if reason else "stored, no push"
    print(f"[poll_once] incident #{link.incident_id} {role} ({link.rule}): {article.title!r} -- {outcome}")
    return alert_id


def _maybe_notify_classifier_down(conn, detail: str, now: dt.datetime) -> None:
    """
    Every provider failed, so alerts are going out UNCLASSIFIED -- tell the
    owner once per UTC day (B2 K8) rather than once per alert. The day is
    only marked done after Telegram confirmed the send: a failed send must
    not use up the day's notice, so the next outage-affected alert retries.
    """
    if store.outage_notice_sent(conn, now.date()):
        return
    text = (
        f"⚠️ Shock classifier down: every provider failed ({(detail or 'no detail')[:300]}). "
        "Alerts keep going out as UNCLASSIFIED until it recovers. "
        "This notice is sent at most once per UTC day."
    )
    if notify_telegram.send_notice(text):
        store.record_outage_notice(conn, now.date(), now, (detail or "")[:300])


def _maybe_escalate(
    conn, webapp_conn, alert_id: int, new_category: str, raw_new_severity: str, new_rationale,
    new_classification_failed: bool = False, *,
    polarity=None, country=None, us_link=None,
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
    manual. B7 (2026-10-22): "more severe" is measured against the
    incident's HIGHEST stored severity, not the matched row's, so a Medium
    follow-up row can never be "escalated" back to the High its incident
    already pushed. A severity that is only the fallback guess from a failed
    classification is not a real assessment and never escalates anything.

    B2: a corroborating article whose US link is unknown inherits the
    STORED alert's link ("effective"), and the no-US-link cap applies to
    it. Otherwise a hard-rule corroboration (link unknown) would bring back
    a High on a story already judged to have no US or global-supply link,
    with its stale lean-less symbols. The cap is lifted only by an article
    that positively reports a direct / global_supply link: that rewrites
    severity, cap flag and leans together (store.update_alert_assessment).
    The same full rewrite runs whenever the effective link is "none": an
    escalation of an alert stored with an unknown link (and real leans) by
    an article judged no-US-link is capped and stripped of every lean, and
    the push carries the cap note.
    """
    if new_classification_failed:
        return
    existing = store.get_alert(conn, alert_id)
    if existing is None:
        return  # shouldn't happen (caller just appended to this id), but never crash on it
    effective = us_link if us_link is not None else existing.us_link
    new_severity, _ = cap_severity(raw_new_severity, effective)
    incident_high = incident.incident_max_severity(store.list_incident_alerts(conn, existing.incident_id))
    if _SEVERITY_RANK.get(new_severity, -1) <= _SEVERITY_RANK.get(incident_high, -1):
        return

    affected = existing.affected_symbols
    push_cap_note = None
    lifts_cap = existing.capped_no_us_link and effective in ("direct", "global_supply")
    if lifts_cap or effective == "none":
        # Rewrite the whole assessment for the stored headline under the effective link, so the
        # severity, cap flag and leans never disagree. Lifting the cap restores leans; "none"
        # (whether this article first reports it or the alert already carried it) withholds every
        # lean -- an escalation on a no-US-link judgement must never push a buy/sell lean (K3).
        new_polarity = polarity if polarity not in (None, "unclear") else (existing.polarity or "unclear")
        new_country = country if country is not None else existing.country
        impacts = affected_symbols(new_category, list_tracked_symbols(webapp_conn), headline=existing.headline)
        affected = direction.describe_impacts(
            impacts, new_category, new_polarity, country=new_country, us_link=effective)
        capped = effective == "none"
        store.update_alert_assessment(
            conn, alert_id, severity=new_severity, polarity=new_polarity, country=new_country,
            us_link=effective, capped_no_us_link=capped, original_severity=raw_new_severity,
            affected_symbols=affected,
        )
        push_cap_note = cap_note(raw_new_severity, capped)
    else:
        store.set_severity(conn, alert_id, new_severity)
        if existing.capped_no_us_link:
            push_cap_note = cap_note(existing.original_severity, True)

    if _should_push(new_severity, False):
        sent = notify_telegram.send_alert(
            existing.headline, new_category, new_severity, new_rationale,
            affected, existing.sources, is_escalation=True, cap_note=push_cap_note,
            # Age of the ORIGINAL story at its first catch, not of this corroborating article.
            freshness_line=freshness_line(existing.first_published_utc, existing.detected_at_utc),
        )
        store.set_delivery_status(conn, alert_id, "sent" if sent else "failed")


def maybe_send_health_notice() -> bool:
    """Lazy indirection to ops.health (so a broken health module can never stop the poll)."""
    from ops.health import maybe_send_health_notice as _send
    return _send()


def _send_health_notice_fail_open() -> None:
    try:
        maybe_send_health_notice()
    except Exception as exc:  # noqa: BLE001 - the notice must never break the poll
        print(f"[poll_once] WARNING: health notice skipped: {exc}")


def main() -> None:
    """
    One scheduled poll, then the once-per-UTC-day health notice (B4 O6).
    The notice also runs when the cycle raises (the exception still ends
    the run with exit 1); maybe_send_health_notice never raises itself.
    """
    try:
        run_poll_cycle()
    finally:
        _send_health_notice_fail_open()


if __name__ == "__main__":
    main()
