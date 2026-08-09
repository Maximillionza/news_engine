"""
Core probability scoring engine.

Pipeline for a single scoring run:
  1. Every article gets a USD-directional sentiment score (native if the
     source provides one, otherwise the lexicon fallback in sentiment.py).
  2. Each article's contribution is weighted by (source trust) x (time decay).
  3. Weighted average -> a single aggregate USD sentiment score.
  4. That score is mapped to an instrument-specific score using the
     instrument's usd_relationship (inverse for gold, etc.)
  5. Instrument score -> probability via a bounded sigmoid transform.
  6. Agreement across articles (not just their average) further adjusts
     confidence — ten articles that barely agree should not produce the
     same confidence as ten articles all pointing the same way.
  7. Separately, recent articles vs. older articles are compared — if they
     point in meaningfully different directions, that's flagged explicitly
     rather than just averaged away, per the requirement that a late
     contradiction should be surfaced, not hidden inside an average.

This module scores a single point in time. Tracking how the score changes
across repeated calls (to catch indecision through the event window) is
handled separately in history.py.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from enum import Enum

from config.settings import (
    CONTEXTUAL_CONFIDENCE_THRESHOLD,
    CONTRADICTION_MIN_MAGNITUDE,
    INSTRUMENTS,
    PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES,
    PRECURSOR_TRUST_WEIGHT,
    RECENT_WINDOW_HOURS,
    SOURCE_TRUST_WEIGHTS,
    TIME_DECAY_HALF_LIFE_MINUTES,
    UTC_TZ,
)
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle
from data_layer.news_feed import NewsArticle
from scoring.finbert_sentiment import score_article_finbert
from scoring.llm_sentiment import score_article_llm
from scoring.sentiment import score_article_text


class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class ArticleContribution:
    """Per-article audit trail — why the score came out the way it did."""
    article: NewsArticle
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float
    matched_terms: list[str] = field(default_factory=list)


@dataclass
class PrecursorContribution:
    """
    Audit trail for a leading-indicator precursor event's contribution —
    structured forecast-vs-actual surprise, not lexicon-scored text.
    Deliberately mirrors ArticleContribution's usd_sentiment/combined_weight
    fields (duck-typed) so it can flow through the same weighted-average,
    agreement, and coverage math without those functions needing to
    special-case it.
    """
    event: EconomicEvent
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float


@dataclass
class ProbabilityResult:
    instrument: str
    as_of_utc: dt.datetime
    aggregate_usd_sentiment: float      # -1.0 to +1.0, raw USD-directional read
    instrument_score: float             # aggregate_usd_sentiment after instrument mapping
    probability: float                  # 0.0 to 1.0 — probability of `direction`
    direction: Direction
    confidence: float                   # 0.0 to 1.0 — agreement x coverage; separate from probability.
                                         # Low if sources disagree OR if too few sources had an opinion.
    article_count: int
    contradiction_flag: bool
    contradiction_note: str | None
    contributions: list[ArticleContribution] = field(default_factory=list, repr=False)
    precursor_contributions: list[PrecursorContribution] = field(default_factory=list, repr=False)

    def summary(self) -> str:
        base = (
            f"{self.instrument}: {self.direction.value.upper()} "
            f"({self.probability:.0%} probability, {self.confidence:.0%} confidence, "
            f"{self.article_count} articles"
        )
        if self.precursor_contributions:
            base += f", {len(self.precursor_contributions)} leading indicators"
        base += ")"
        if self.contradiction_flag:
            base += f" — ⚠ {self.contradiction_note}"
        return base


def _get_article_sentiment(article: NewsArticle) -> tuple[float, list[str]]:
    """
    Returns (usd_sentiment, matched_terms). Tiered fallback, cheapest and
    most-deterministic first — see the block comment above
    CONTEXTUAL_CONFIDENCE_THRESHOLD in config.settings for the full
    rationale:

      1. native_sentiment on the article, if a vendor already supplied one
         (Alpha Vantage / APITube) — unchanged, always wins if present.
      2. FinBERT (local, free) — used if its own top-class confidence is
         at or above CONTEXTUAL_CONFIDENCE_THRESHOLD.
      3. Claude API — only when FinBERT is unavailable or was itself
         unsure (confidence below threshold); this is the tier that
         actually understands hedged/conditional language ("rate hike
         risk IF data surprises") instead of matching it as declarative.
      4. The keyword lexicon (sentiment.py) — final fallback, zero
         dependencies, zero cost, unchanged behavior from before this
         tiering existed.
    """
    if article.native_sentiment is not None:
        clamped = max(-1.0, min(1.0, article.native_sentiment))
        return clamped, ["<native_sentiment>"]

    finbert_result = score_article_finbert(article.title, article.summary)
    if finbert_result is not None and finbert_result.confidence >= CONTEXTUAL_CONFIDENCE_THRESHOLD:
        return finbert_result.usd_score, [f"<finbert:{finbert_result.label}:{finbert_result.confidence:.2f}>"]

    llm_result = score_article_llm(article.title, article.summary)
    if llm_result is not None:
        return llm_result.usd_score, [f"<llm:{llm_result.usd_score:+.2f}:{llm_result.reasoning}>"]

    if finbert_result is not None:
        # FinBERT ran but was below the confidence threshold, and the LLM
        # tier wasn't available to arbitrate — use FinBERT's read anyway
        # rather than fall all the way back to the lexicon, which has no
        # contextual understanding at all. A low-confidence contextual
        # read still beats a keyword-triggered one.
        return finbert_result.usd_score, [f"<finbert:{finbert_result.label}:{finbert_result.confidence:.2f}:low_confidence>"]

    result = score_article_text(article.title, article.summary)
    return result.usd_score, result.matched_terms


def _time_decay_weight(article: NewsArticle, as_of: dt.datetime, half_life_minutes: float) -> float:
    age_minutes = max(0.0, article.age_minutes(as_of))
    return 0.5 ** (age_minutes / half_life_minutes)


def _trust_weight(article: NewsArticle) -> float:
    return SOURCE_TRUST_WEIGHTS.get(article.source_type, 0.5)  # unknown sources get a conservative default


def _build_contributions(
    articles: list[NewsArticle],
    as_of: dt.datetime,
    half_life_minutes: float,
) -> list[ArticleContribution]:
    contributions = []
    for article in articles:
        usd_sentiment, matched = _get_article_sentiment(article)
        trust_w = _trust_weight(article)
        time_w = _time_decay_weight(article, as_of, half_life_minutes)
        contributions.append(
            ArticleContribution(
                article=article,
                usd_sentiment=usd_sentiment,
                trust_weight=trust_w,
                time_weight=time_w,
                combined_weight=trust_w * time_w,
                matched_terms=matched,
            )
        )
    return contributions


def _build_precursor_contributions(
    precursor_events: list[EconomicEvent],
    as_of: dt.datetime,
) -> list[PrecursorContribution]:
    """
    Age-decayed like article contributions, but using
    PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES rather than the article
    half-life — a structured forecast-vs-actual print doesn't go stale at
    the same rate ephemeral news text does (see that constant's comment
    in config.settings for why). Events with no computable surprise
    (missing data, unmapped indicator) are silently skipped — see
    EconomicEvent.usd_surprise_score()'s docstring for why that returns
    None instead of a fabricated 0.0.
    """
    contributions = []
    for event in precursor_events:
        usd_surprise = event.usd_surprise_score()
        if usd_surprise is None:
            continue
        age_minutes = max(0.0, (as_of - event.event_time_utc).total_seconds() / 60.0)
        time_w = 0.5 ** (age_minutes / PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES)
        contributions.append(
            PrecursorContribution(
                event=event,
                usd_sentiment=usd_surprise,
                trust_weight=PRECURSOR_TRUST_WEIGHT,
                time_weight=time_w,
                combined_weight=PRECURSOR_TRUST_WEIGHT * time_w,
            )
        )
    return contributions


def _weighted_aggregate(contributions: list[ArticleContribution]) -> float:
    total_weight = sum(c.combined_weight for c in contributions)
    if total_weight <= 0:
        return 0.0
    weighted_sum = sum(c.usd_sentiment * c.combined_weight for c in contributions)
    return weighted_sum / total_weight


def _agreement_and_coverage(
    contributions: list[ArticleContribution], aggregate_sign: int
) -> tuple[float, float]:
    """
    Returns (agreement, coverage) — two separate questions that
    _agreement_ratio used to conflate into one number:

    agreement: of the articles that actually carried a directional signal,
    what fraction (by weight) agree with the aggregate's sign? 1.0 = every
    signal-bearing article points the same way. 0.5 = a coin flip. Articles
    with ~zero sentiment (no signal) are excluded from this — same as before.

    coverage: what fraction of the bundle's *total* weight came from
    signal-bearing articles at all? 1.0 = every article had an opinion.
    Near 0.0 = almost the whole bundle was silent and one lone article is
    doing all the talking. This exists because "agreement" alone can't
    distinguish 10/10 articles agreeing from 1/10 trivially agreeing with
    itself — both used to report 100%. Confidence needs both: agreement
    without coverage is a false-certainty bug (see the 2026-08-07 NFP
    backtest case: 1 signal article out of 6 produced 100% "confidence").
    """
    total_weight = sum(c.combined_weight for c in contributions)
    if total_weight <= 0:
        return 0.0, 0.0

    agreeing_weight = 0.0
    signal_weight = 0.0
    for c in contributions:
        if abs(c.usd_sentiment) < 1e-6:
            continue
        signal_weight += c.combined_weight
        if (c.usd_sentiment > 0) == (aggregate_sign > 0):
            agreeing_weight += c.combined_weight

    if signal_weight <= 0:
        return 0.0, 0.0

    agreement = agreeing_weight / signal_weight
    coverage = signal_weight / total_weight
    return agreement, coverage


def _map_to_instrument_score(usd_sentiment: float, instrument: str) -> float:
    relationship = INSTRUMENTS[instrument]["usd_relationship"]
    if relationship == "inverse":
        return -usd_sentiment
    if relationship == "direct":
        return usd_sentiment
    if relationship == "risk_sentiment":
        # Simplification for v1: treat USD-bearish (dovish/easing) as broadly
        # risk-on/supportive for equities, USD-bullish (hawkish/tightening)
        # as broadly risk-off/negative for equities. This is a real
        # simplification — hawkish-because-strong-economy can also be
        # equity-positive — flagged here so it's the first thing to
        # re-examine if US30 backtest accuracy comes out weak.
        return -usd_sentiment * 0.7  # dampened relative to gold's cleaner inverse relationship
    raise ValueError(f"Unknown usd_relationship for instrument {instrument!r}: {relationship}")


def _score_to_probability(instrument_score: float, k: float = 2.5) -> float:
    """
    Bounded sigmoid transform: instrument_score of 0 -> 50% probability,
    approaches 0%/100% at the extremes. k controls how quickly probability
    saturates — higher k means the engine commits to strong probabilities
    from smaller sentiment scores. Needs tuning against backtest results.
    """
    return 0.5 + 0.5 * math.tanh(k * instrument_score)


def _detect_contradiction(
    contributions: list[ArticleContribution],
    as_of: dt.datetime,
    instrument: str,
) -> tuple[bool, str | None]:
    """
    Splits contributions into 'recent' (last RECENT_WINDOW_HOURS) and
    'older', computes each window's instrument-mapped sentiment, and flags
    a contradiction if both windows show a real directional lean but in
    opposite directions.
    """
    recent_cutoff = as_of - dt.timedelta(hours=RECENT_WINDOW_HOURS)
    recent = [c for c in contributions if c.article.published_utc >= recent_cutoff]
    older = [c for c in contributions if c.article.published_utc < recent_cutoff]

    if not recent or not older:
        return False, None  # need both windows populated to compare

    recent_usd = _weighted_aggregate(recent)
    older_usd = _weighted_aggregate(older)

    recent_instrument = _map_to_instrument_score(recent_usd, instrument)
    older_instrument = _map_to_instrument_score(older_usd, instrument)

    both_meaningful = (
        abs(recent_instrument) >= CONTRADICTION_MIN_MAGNITUDE
        and abs(older_instrument) >= CONTRADICTION_MIN_MAGNITUDE
    )
    opposite_signs = (recent_instrument > 0) != (older_instrument > 0)

    if both_meaningful and opposite_signs:
        recent_dir = "bullish" if recent_instrument > 0 else "bearish"
        older_dir = "bullish" if older_instrument > 0 else "bearish"
        note = (
            f"Sentiment fluctuating: last {RECENT_WINDOW_HOURS}h leans {recent_dir}, "
            f"but earlier coverage leaned {older_dir} — treat as indecisive until this settles."
        )
        return True, note

    return False, None


def score_bundle(
    bundle: EventNewsBundle,
    instrument: str,
    precursor_events: list[EconomicEvent] | None = None,
) -> ProbabilityResult:
    """
    Main entry point: score an EventNewsBundle for a given instrument
    (must be a key in config.settings.INSTRUMENTS, e.g. 'XAUUSD').

    precursor_events: optional leading-indicator events (already-released
    minor/medium USD releases that predict this event — ADP before NFP,
    PPI before CPI, etc; see data_layer.calendar_feed.find_precursor_events()
    for how to build this list). Their forecast-vs-actual surprise is
    blended in as a structured, high-trust contribution alongside article
    sentiment — same USD-directional axis, same weighted-average math,
    just a different (and more reliable) source of signal.
    """
    if instrument not in INSTRUMENTS:
        raise ValueError(f"Unknown instrument {instrument!r} — add it to config.settings.INSTRUMENTS first")

    as_of = bundle.as_of_utc
    article_contributions = _build_contributions(bundle.articles, as_of, TIME_DECAY_HALF_LIFE_MINUTES)
    precursor_contributions = _build_precursor_contributions(precursor_events or [], as_of)
    all_contributions = article_contributions + precursor_contributions

    if not all_contributions:
        return ProbabilityResult(
            instrument=instrument,
            as_of_utc=as_of,
            aggregate_usd_sentiment=0.0,
            instrument_score=0.0,
            probability=0.5,
            direction=Direction.NEUTRAL,
            confidence=0.0,
            article_count=0,
            contradiction_flag=False,
            contradiction_note="No articles or leading indicators in window — no basis for a directional call.",
        )

    aggregate_usd = _weighted_aggregate(all_contributions)
    instrument_score = _map_to_instrument_score(aggregate_usd, instrument)
    raw_probability = _score_to_probability(instrument_score)

    # Agreement must be measured on the same axis the contributions live in
    # (raw USD sentiment), not the instrument-mapped axis — otherwise an
    # inverse-mapped instrument like gold would have its sign flipped
    # relative to the per-article scores and every article would spuriously
    # register as "disagreeing" with the aggregate.
    usd_sign = 1 if aggregate_usd >= 0 else -1
    agreement, coverage = _agreement_and_coverage(all_contributions, usd_sign)

    # Pull probability back toward 50% when agreement is weak — a strong
    # average built from disagreeing sources shouldn't read as high-confidence.
    adjusted_probability = 0.5 + (raw_probability - 0.5) * agreement

    # Confidence must reflect BOTH agreement (do the sources that spoke
    # agree?) AND coverage (did enough of the bundle actually speak?).
    # agreement alone lets a single signal-bearing article among a dozen
    # silent ones report 100% confidence — it trivially agrees with itself.
    confidence = agreement * coverage

    if instrument_score > 0.02:
        direction = Direction.BULLISH
    elif instrument_score < -0.02:
        direction = Direction.BEARISH
    else:
        direction = Direction.NEUTRAL

    # Contradiction detection stays article-only — it's designed to catch
    # a narrative shifting over time (recent vs older text), which isn't
    # the right frame for a precursor's one-shot structured surprise.
    contradiction_flag, contradiction_note = _detect_contradiction(article_contributions, as_of, instrument)

    return ProbabilityResult(
        instrument=instrument,
        as_of_utc=as_of,
        aggregate_usd_sentiment=aggregate_usd,
        instrument_score=instrument_score,
        probability=adjusted_probability,
        direction=direction,
        confidence=confidence,
        article_count=len(article_contributions),
        contradiction_flag=contradiction_flag,
        contradiction_note=contradiction_note,
        contributions=article_contributions,
        precursor_contributions=precursor_contributions,
    )
