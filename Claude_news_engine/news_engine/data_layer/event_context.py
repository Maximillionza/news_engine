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
from dataclasses import dataclass

from config.settings import PRE_EVENT_WINDOW_HOURS, UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.news_feed import NewsArticle, NewsSource, fetch_from_all_sources, deduplicate_articles


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
