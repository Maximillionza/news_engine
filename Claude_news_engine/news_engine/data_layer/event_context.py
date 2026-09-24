"""
Ties an EconomicEvent to its relevant news window.

This is the hand-off point to the scoring engine (not built yet): for a
given event, gather every article published between
(event_time - PRE_EVENT_WINDOW_HOURS) and "now" (live mode) or the event
time itself (backtest mode), tag each with its age relative to the event,
and hand that bundle off for scoring.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from config.settings import EVENT_RELEVANCE_KEYWORDS_BY_TITLE, PRE_EVENT_WINDOW_HOURS, UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.news_feed import NewsArticle, NewsSource, fetch_from_all_sources, deduplicate_articles

# 2026-09-24 fix: a single-company stock-price blurb ("First Solar stock
# heads into the open after a 4.42 percent drop", "NetApp stock rises 1.8
# percent ahead of the open") routinely appends a boilerplate "US data due
# today" calendar footer naming that day's scheduled macro release --
# genuinely containing a real keyword (e.g. "jobless claims") from
# EVENT_RELEVANCE_KEYWORDS_BY_TITLE, even though the article's actual
# subject is that one company's own price move, unrelated to the named
# event. Live-confirmed 2026-09-24: two real Unemployment Claims scores had
# 76.9% and 52.8% of their total sentiment weight driven by exactly this
# pattern (Dexcom, Synchrony Financial, First Solar, NetApp, Align
# Technology); historical damage included one prediction (Fed Chairman
# Warsh Speaks / Prelim Benchmark Payrolls Revision) where a single
# unrelated "Dick's Sporting Goods stock falls 20%..." earnings-miss
# headline was 100% of that prediction's weight.
#
# A keyword substring match can't tell "this article is ABOUT the event"
# apart from "this article mentions the event in a footer" -- but the
# HEADLINE shape reliably can: a genuine macro article is essentially never
# titled "<Company> stock <verb> X percent" the way a syndicated
# single-stock blurb always is. Checked against the title only (not
# summary/body) -- deliberately narrower than the keyword filter itself,
# so this can't suppress a genuinely on-topic article whose own headline
# happens to name a company reacting to real macro news (e.g. "Gold miners
# rally as Fed signals rate cut" doesn't match: no "<Name> stock <verb>"
# shape).
_SINGLE_STOCK_BLURB_TITLE_PATTERN = re.compile(
    r"\bstock (rises?|falls?|drops?|slips?|gains?|jumps?|climbs?|declines?|"
    r"surges?|plunges?|sinks?|ralli(?:es|ed)|tumbles?|heads into)\b",
    re.IGNORECASE,
)


def _is_single_stock_blurb(article: NewsArticle) -> bool:
    return bool(_SINGLE_STOCK_BLURB_TITLE_PATTERN.search(article.title))


@dataclass
class EventNewsBundle:
    event: EconomicEvent
    articles: list[NewsArticle]
    as_of_utc: dt.datetime   # the "now" this bundle was assembled for (live) or capped at (backtest)

    def articles_sorted_by_recency(self) -> list[NewsArticle]:
        return sorted(self.articles, key=lambda a: a.published_utc, reverse=True)

    def minutes_before_event(self, article: NewsArticle) -> float:
        """Positive = article came before the event. Negative = after (should not happen in a proper pre-event bundle)."""
        return (self.event.event_time_utc - article.published_utc).total_seconds() / 60.0


def _is_relevant(article: NewsArticle, keywords: list[str]) -> bool:
    haystack = f"{article.title} {article.summary}".lower()
    return any(kw in haystack for kw in keywords)


def _filter_relevant(articles: list[NewsArticle], event_title: str) -> list[NewsArticle]:
    """
    Applies EVENT_RELEVANCE_KEYWORDS_BY_TITLE's keyword filter. An event
    title with no entry FAILS CLOSED (returns no articles at all), not
    open (2026-09-17 fix — was previously "return articles unchanged").

    Why fail-closed: fetching itself is event-agnostic (every NewsSource
    is called with query="" — see this module's own build_event_news_bundle()
    and news_feed.py's docstrings), so this filter is the ONLY thing
    standing between "whatever the broad macro-news feed happened to
    return" and this event's sentiment score. The old fail-open behavior
    let that broad, unrelated feed straight through for any event without
    a curated keyword list — live-confirmed via real top_contributions_json
    rows in scoring/backtest_log.db: a Chipotle restaurant-opening article
    contributed 2.3% weight and +0.84 USD sentiment to a real Non-Farm
    Employment Change score; similar real off-topic contributions found for
    PPI m/m, ISM Manufacturing PMI, Retail Sales m/m, and Unemployment
    Claims — none topically related to the event they were scored against.

    A genuinely uncurated event title now gets zero articles (loudly
    logged) rather than a silently-diluted score — the same "never
    fabricate, fail loud" discipline this project applies everywhere else,
    now applied here too. Add a real, curated keyword list to
    config.settings.EVENT_RELEVANCE_KEYWORDS_BY_TITLE before this event
    can get article-based sentiment coverage again.
    """
    keywords = EVENT_RELEVANCE_KEYWORDS_BY_TITLE.get(event_title)
    if not keywords:
        print(
            f"[event_context] WARNING: no relevance keywords configured for "
            f"{event_title!r} — dropping all {len(articles)} fetched article(s) "
            f"rather than scoring them unfiltered. Add an entry to "
            f"config.settings.EVENT_RELEVANCE_KEYWORDS_BY_TITLE to restore "
            f"article-based sentiment coverage for this event."
        )
        return []
    return [a for a in articles if not _is_single_stock_blurb(a) and _is_relevant(a, keywords)]


def build_event_news_bundle(
    event: EconomicEvent,
    sources: list[NewsSource],
    query: str,
    mode: str = "live",
    backtest_cutoff_utc: dt.datetime | None = None,
) -> EventNewsBundle:
    """
    mode='live': window is (event_time - PRE_EVENT_WINDOW_HOURS) -> now
    mode='backtest': window is (event_time - PRE_EVENT_WINDOW_HOURS) -> event_time
                      (or an explicit backtest_cutoff_utc, which must be <= event_time,
                      so the model never sees articles published after the release —
                      that would leak the outcome into the "prediction")
    """
    window_start = event.event_time_utc - dt.timedelta(hours=PRE_EVENT_WINDOW_HOURS)

    if mode == "backtest":
        cutoff = backtest_cutoff_utc or event.event_time_utc
        if cutoff > event.event_time_utc:
            raise ValueError(
                "backtest_cutoff_utc must not be after the event time — "
                "the whole point of the backtest is testing on pre-release info only"
            )
        as_of = cutoff
    elif mode == "live":
        as_of = dt.datetime.now(UTC_TZ)
    else:
        raise ValueError("mode must be 'live' or 'backtest'")

    raw_articles = fetch_from_all_sources(sources, query, since_utc=window_start)

    # Enforce the cutoff strictly — some APIs are sloppy about time_from filtering
    windowed = [a for a in raw_articles if window_start <= a.published_utc <= as_of]
    windowed = _filter_relevant(windowed, event.title)
    windowed = deduplicate_articles(windowed)

    return EventNewsBundle(event=event, articles=windowed, as_of_utc=as_of)


def fetch_outcome_confirmation(
    event: EconomicEvent,
    outcome_sources: list[NewsSource],
    query: str,
    lookahead_hours: float = 6.0,
) -> list[NewsArticle]:
    """
    Backtest-only helper: pulls articles published AFTER the event, from
    official ground-truth sources (Fed press releases, BLS releases), to
    confirm what the actual number/outcome was.

    This is deliberately a separate function from build_event_news_bundle()
    so it can never accidentally be wired into the pre-event scoring path.
    Pass build_outcome_sources() from rss_sources.py here, not the preview
    sources used for scoring.
    """
    window_end = event.event_time_utc + dt.timedelta(hours=lookahead_hours)
    raw_articles = fetch_from_all_sources(outcome_sources, query, since_utc=event.event_time_utc)
    return [a for a in raw_articles if event.event_time_utc <= a.published_utc <= window_end]
