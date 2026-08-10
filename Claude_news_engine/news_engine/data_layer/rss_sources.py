"""
RSS-based sources, deliberately split into two categories that must not be
conflated:

1. PRE-EVENT SENTIMENT SOURCES (RSSNewsSource + FREE_PREVIEW_FEEDS)
   These publish previews, analyst expectations, and positioning commentary
   in the run-up to a scheduled release. This is the only category that
   should ever feed the pre-event probability score.

2. GROUND-TRUTH OUTCOME SOURCES (OFFICIAL_OUTCOME_FEEDS)
   Fed / BLS / Treasury feeds only publish AT release time — they announce
   the number, they don't predict it. They are worthless as scoring input
   (there's nothing there before the event) but essential for the backtest
   module later: they're what "did the prediction turn out right" gets
   checked against.

Mixing these two up would either leak the answer into the "prediction"
(if an official release slips into the pre-event window) or waste cycles
polling a feed that has nothing to say until the event has already
happened. The event_context module's backtest cutoff enforcement is the
other half of this guard — this module just keeps the source lists honest
about what each one is actually good for.
"""
from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from config.settings import ALPHA_VANTAGE_API_KEY, UTC_TZ
from data_layer.news_feed import AlphaVantageNewsSource, NewsArticle, NewsSource


# --- Tier 1: pre-event sentiment sources (previews, analyst commentary, positioning) ---
FREE_PREVIEW_FEEDS = {
    # Reuters killed its public RSS feeds (reutersagency.com/feed/... 404s).
    # Google News RSS scoped to site:reuters.com is the standard free
    # workaround — same RSS 2.0 shape, parses with the existing parser.
    "reuters_business": "https://news.google.com/rss/search?q=site:reuters.com+business+when:1d&hl=en-US&gl=US&ceid=US:en",
    "cnbc_top_news": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "cnbc_economy": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "investing_com_forex": "https://www.investing.com/rss/news_1.rss",
    # GDELT is a query API rather than a fixed RSS feed — kept separate below.
}

# --- Tier 2: ground-truth outcome sources — release-time only, NOT for pre-event scoring ---
OFFICIAL_OUTCOME_FEEDS = {
    "federal_reserve_press": "https://www.federalreserve.gov/feeds/press_all.xml",
    # BLS sits behind Akamai bot-fingerprinting (blocks on TLS/JA3 +
    # request pattern, not just User-Agent) — a browser-like UA is set in
    # RSSNewsSource.fetch() as best effort, but this feed may still 403
    # from a scripted client. It's backtest-only ground truth, not on the
    # live scoring path, so a persistent block here isn't a scoring risk.
    "bls_news_releases": "https://www.bls.gov/feed/news_release.rss",
}


class RSSNewsSource:
    """
    Generic RSS fetcher. One instance per feed. Use FREE_PREVIEW_FEEDS
    entries for pre-event scoring input; use OFFICIAL_OUTCOME_FEEDS entries
    only in the backtest module to fetch the actual outcome, never as
    scoring input.
    """

    def __init__(self, name: str, feed_url: str):
        self.name = name
        self.feed_url = feed_url

    def fetch(self, query: str, since_utc: dt.datetime, limit: int = 50) -> list[NewsArticle]:
        """
        query is applied as a simple case-insensitive substring filter over
        title+summary, since most of these feeds don't support server-side
        search. Pass an empty string to skip filtering and get everything
        in the window.
        """
        resp = requests.get(
            self.feed_url,
            timeout=15,
            headers={
                # A generic UA string gets 403'd by Akamai-fronted feeds
                # (e.g. BLS) — a realistic browser UA is the best-effort
                # fix; some Akamai deployments fingerprint beyond the UA
                # and will still block a scripted client regardless.
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            },
        )
        resp.raise_for_status()

        articles = self._parse_rss(resp.content, since_utc, limit)

        if query:
            q = query.lower()
            articles = [
                a for a in articles
                if q in a.title.lower() or q in a.summary.lower()
            ]
        return articles

    def _parse_rss(self, xml_bytes: bytes, since_utc: dt.datetime, limit: int) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError as exc:
            print(f"[rss_feed] WARNING: failed to parse feed '{self.name}': {exc}")
            return articles

        # Standard RSS 2.0 structure: rss/channel/item
        for item in root.findall(".//item")[: limit * 2]:  # overfetch slightly before date-filtering
            title = (item.findtext("title") or "").strip()
            summary = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date_raw = item.findtext("pubDate")

            published = self._parse_pubdate(pub_date_raw)
            if published is None:
                continue
            if published < since_utc:
                continue

            articles.append(
                NewsArticle(
                    title=title,
                    summary=summary,
                    source=self.name,
                    source_type=f"rss_{self.name}",
                    published_utc=published,
                    url=link,
                    native_sentiment=None,  # RSS feeds don't carry sentiment scores; scoring engine computes this
                )
            )
            if len(articles) >= limit:
                break

        return articles

    # Fallback formats for feeds that don't use RFC 822 pubDate (e.g.
    # investing.com ships bare "YYYY-MM-DD HH:MM:SS", no weekday/tz).
    _FALLBACK_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S",)

    @classmethod
    def _parse_pubdate(cls, raw: str | None) -> dt.datetime | None:
        if not raw:
            return None
        raw = raw.strip()
        parsed = None
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            for fmt in cls._FALLBACK_DATE_FORMATS:
                try:
                    parsed = dt.datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            # No tz on the feed — assume UTC, same as the RFC822 branch
            # does for naive timestamps. Best-effort; feeds don't declare it.
            parsed = parsed.replace(tzinfo=UTC_TZ)
        return parsed.astimezone(UTC_TZ)


def build_preview_sources() -> list[RSSNewsSource]:
    """All Tier 1 (pre-event, scoring-eligible) RSS sources, ready to use."""
    return [RSSNewsSource(name, url) for name, url in FREE_PREVIEW_FEEDS.items()]


def build_all_preview_sources() -> list[NewsSource]:
    """
    All Tier 1 sources this environment can actually use: the free RSS
    feeds (always available, no config needed) plus Alpha Vantage's
    NEWS_SENTIMENT source IF ALPHA_VANTAGE_API_KEY is set — opt-in by key
    presence, same as this project's other optional tiers (FinBERT/LLM
    contextual sentiment gate on an explicit ENABLE_* env var instead,
    since those activate just from a dependency being importable; an API
    key is already a deliberate user action, so its mere presence is a
    legitimate opt-in signal here).

    Alpha Vantage's native_sentiment (if present on a returned article)
    bypasses the lexicon/FinBERT/LLM tiers entirely in
    probability_engine._get_article_sentiment() — it's the vendor's own
    computed score, already the most-trusted tier by design.

    Use this instead of build_preview_sources() directly for anything
    that should pick up Alpha Vantage automatically once configured,
    without every caller re-writing the same "is the key set" check.
    """
    sources: list[NewsSource] = build_preview_sources()
    if ALPHA_VANTAGE_API_KEY:
        sources.append(AlphaVantageNewsSource())
    return sources


def build_outcome_sources() -> list[RSSNewsSource]:
    """
    All Tier 2 (ground-truth, backtest-only) RSS sources.
    Do not pass these into build_event_news_bundle() for scoring — use
    them only to confirm what actually happened after the fact.
    """
    return [RSSNewsSource(name, url) for name, url in OFFICIAL_OUTCOME_FEEDS.items()]
