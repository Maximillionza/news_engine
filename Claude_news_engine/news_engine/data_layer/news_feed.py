"""
News article fetchers — pluggable by source so new providers can be added
without touching the scoring engine downstream.

Each source implementation returns a list of NewsArticle objects normalized
to the same shape: title, summary, source, published_utc, url, and a raw
sentiment score if the provider gives one natively (else None, and the
scoring engine will compute its own later).
"""
from __future__ import annotations

import datetime as dt
import difflib
from dataclasses import dataclass, field
from typing import Optional, Protocol

import requests

from config.settings import (
    ALPHA_VANTAGE_API_KEY,
    APITUBE_API_KEY,
    LOCAL_TZ,
    SOURCE_TRUST_WEIGHTS,
    UTC_TZ,
)


@dataclass
class NewsArticle:
    title: str
    summary: str
    source: str                 # publisher name, e.g. "Reuters"
    source_type: str            # which fetcher produced it, e.g. "alpha_vantage_news"
    published_utc: dt.datetime
    url: str
    native_sentiment: Optional[float] = None   # -1.0 (very bearish) to +1.0 (very bullish), if provider supplies it
    tickers: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def published_local(self) -> dt.datetime:
        return self.published_utc.astimezone(LOCAL_TZ)

    def age_minutes(self, now_utc: Optional[dt.datetime] = None) -> float:
        now_utc = now_utc or dt.datetime.now(UTC_TZ)
        return (now_utc - self.published_utc).total_seconds() / 60.0

    def __repr__(self) -> str:
        return f"<NewsArticle {self.title[:60]!r} src={self.source} age={self.age_minutes():.0f}m>"


class NewsSource(Protocol):
    """Interface every news source fetcher must implement."""
    name: str

    def fetch(self, query: str, since_utc: dt.datetime, limit: int = 50) -> list[NewsArticle]:
        ...


class AlphaVantageNewsSource:
    """
    Alpha Vantage NEWS_SENTIMENT endpoint.
    Docs: https://www.alphavantage.co/documentation/#news-sentiment
    Free tier: 25 requests/day as of last check — verify current limits
    before relying on this for continuous polling.
    """
    name = "alpha_vantage_news"
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str = ALPHA_VANTAGE_API_KEY):
        if not api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY not set")
        self.api_key = api_key

    def fetch(self, query: str, since_utc: dt.datetime, limit: int = 50) -> list[NewsArticle]:
        params = {
            "function": "NEWS_SENTIMENT",
            "topics": query,          # e.g. "economy_macro,finance"
            "time_from": since_utc.strftime("%Y%m%dT%H%M"),
            "limit": min(limit, 200),
            "apikey": self.api_key,
        }
        resp = requests.get(self.BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("feed", []):
            try:
                published = dt.datetime.strptime(item["time_published"], "%Y%m%dT%H%M%S").replace(tzinfo=UTC_TZ)
            except (KeyError, ValueError):
                continue

            articles.append(
                NewsArticle(
                    title=item.get("title", ""),
                    summary=item.get("summary", ""),
                    source=item.get("source", "unknown"),
                    source_type=self.name,
                    published_utc=published,
                    url=item.get("url", ""),
                    native_sentiment=item.get("overall_sentiment_score"),
                    tickers=[t.get("ticker") for t in item.get("ticker_sentiment", [])],
                    raw=item,
                )
            )
        return articles


class ApiTubeNewsSource:
    """
    APITube financial news endpoint — good for central bank / macro-event
    specific filtering. Check current API docs for exact param names before
    running, this client targets the general article-search endpoint.
    """
    name = "apitube_news"
    BASE_URL = "https://api.apitube.io/v1/news/everything"

    def __init__(self, api_key: str = APITUBE_API_KEY):
        if not api_key:
            raise ValueError("APITUBE_API_KEY not set")
        self.api_key = api_key

    def fetch(self, query: str, since_utc: dt.datetime, limit: int = 50) -> list[NewsArticle]:
        params = {
            "api_key": self.api_key,
            "q": query,
            "published_at.start": since_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "per_page": min(limit, 100),
            "sort.by": "published_at",
            "sort.order": "desc",
        }
        resp = requests.get(self.BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        articles = []
        for item in data.get("results", []):
            try:
                published = dt.datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue

            articles.append(
                NewsArticle(
                    title=item.get("title", ""),
                    summary=item.get("description", ""),
                    source=item.get("source", {}).get("domain", "unknown"),
                    source_type=self.name,
                    published_utc=published,
                    url=item.get("href", ""),
                    native_sentiment=item.get("sentiment", {}).get("overall") if item.get("sentiment") else None,
                    raw=item,
                )
            )
        return articles


def fetch_from_all_sources(
    sources: list[NewsSource],
    query: str,
    since_utc: dt.datetime,
    limit_per_source: int = 50,
) -> list[NewsArticle]:
    """
    Fan out to every configured source and merge results, sorted newest
    first. A failure in one source (bad key, rate limit, etc.) is logged
    and skipped rather than crashing the whole fetch — partial data beats
    no data for this use case.
    """
    all_articles: list[NewsArticle] = []
    for source in sources:
        try:
            all_articles.extend(source.fetch(query, since_utc, limit_per_source))
        except Exception as exc:
            print(f"[news_feed] WARNING: source '{getattr(source, 'name', source)}' failed: {exc}")

    all_articles.sort(key=lambda a: a.published_utc, reverse=True)
    return all_articles


def _trust_weight_for(article: NewsArticle) -> float:
    return SOURCE_TRUST_WEIGHTS.get(article.source_type, 0.5)  # unknown sources get a conservative default


def deduplicate_articles(articles: list[NewsArticle], title_similarity_threshold: float = 0.85) -> list[NewsArticle]:
    """
    Collapses syndicated near-duplicates — the same underlying story
    reprinted near-verbatim across outlets around a major release — down to
    one representative article. Without this, a single wire story picked
    up by three outlets looks like three independent sources agreeing,
    which inflates both the weighted aggregate sentiment and (since the
    coverage-aware confidence fix in probability_engine.py) confidence
    itself — real corroboration and syndicated republishing must not score
    the same.

    Two passes:
      1. Exact title match (case-insensitive).
      2. Near-duplicate title match via stdlib difflib — catches outlets
         that reword the headline slightly while covering the same story.
         Threshold is deliberately conservative (0.85) — the point is
         catching syndication, not merging genuinely distinct stories
         about the same event (that's corroboration, and should still
         count as separate votes).

    Within each duplicate cluster, keeps the highest-trust copy (ties
    broken by most recent) rather than whichever happened to come first in
    fetch order — no reason to keep a low-trust syndication of a story a
    high-trust wire also carried.
    """
    # Pass 1: exact-title clusters, keep the highest-trust copy per cluster.
    exact_clusters: dict[str, list[NewsArticle]] = {}
    order: list[str] = []
    for a in articles:
        key = a.title.strip().lower()
        if not key:
            continue
        if key not in exact_clusters:
            exact_clusters[key] = []
            order.append(key)
        exact_clusters[key].append(a)

    def _best(cluster: list[NewsArticle]) -> NewsArticle:
        return max(cluster, key=lambda a: (_trust_weight_for(a), a.published_utc))

    stage1 = [_best(exact_clusters[key]) for key in order]

    # Pass 2: near-duplicate titles across what's left after exact dedup.
    deduped: list[NewsArticle] = []
    for a in stage1:
        match_idx = None
        for i, kept in enumerate(deduped):
            ratio = difflib.SequenceMatcher(
                None, a.title.strip().lower(), kept.title.strip().lower()
            ).ratio()
            if ratio >= title_similarity_threshold:
                match_idx = i
                break
        if match_idx is None:
            deduped.append(a)
        elif _trust_weight_for(a) > _trust_weight_for(deduped[match_idx]):
            deduped[match_idx] = a

    return deduped
