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
import re
from dataclasses import dataclass, field, replace
from enum import Enum

from config.settings import (
    CONTEXTUAL_CONFIDENCE_THRESHOLD,
    CONTRADICTION_MIN_MAGNITUDE,
    COT_CROWDING_CONFIDENCE_MULTIPLIER,
    DIRECTION_FLIP_HYSTERESIS_MARGIN,
    DIRECTION_NEUTRAL_BAND,
    ENABLE_FINBERT_SENTIMENT,
    ENABLE_LLM_SENTIMENT,
    EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER,
    EVENT_INFLUENCE_LINKS,
    EVENT_SURPRISE_DIRECTION,
    INSTRUMENTS,
    KALSHI_TRUST_WEIGHT,
    MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER,
    OIL_SHOCK_CONFIDENCE_MULTIPLIER,
    PRECURSOR_CHAIN_CONFLICT_CONFIDENCE_MULTIPLIER,
    PRE_EVENT_WINDOW_HOURS,
    PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES,
    PRECURSOR_TRUST_WEIGHT,
    PRINT_CALL_TRUST_WEIGHT,
    RECENT_WINDOW_HOURS,
    REDUNDANCY_DISCOUNT_MULTIPLIER,
    REDUNDANCY_TERM_OVERLAP_THRESHOLD,
    REDUNDANCY_TIME_PROXIMITY_MINUTES,
    RISK_SENTIMENT_DAMPENING,
    SOURCE_TRUST_WEIGHTS,
    THIN_SAMPLE_PROBABILITY_CAP,
    THIN_SAMPLE_SIGNAL_THRESHOLD,
    TIME_DECAY_HALF_LIFE_MINUTES,
    TREND_STREAK_TRUST_WEIGHT,
    UTC_TZ,
)
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle
from data_layer.macro_backdrop import EQUITY_INDEX_LEAN_THRESHOLD_PCT, OIL_SHOCK_DAILY_THRESHOLD_PCT
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
class PrintCallContribution:
    """
    Audit trail for this occurrence's print-direction call
    (scoring/print_direction.py's PrintCall), mapped onto the USD axis via
    EVENT_SURPRISE_DIRECTION. Duck-typed like PrecursorContribution — same
    usd_sentiment/combined_weight fields — so it flows through the
    existing weighted-average, agreement, and coverage math unchanged.
    """
    event_title: str
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float


@dataclass
class TrendStreakContribution:
    """
    Audit trail for the event's historical beat/miss streak
    (webapp/trend.py's TrendSignal), mapped onto the USD axis via
    EVENT_SURPRISE_DIRECTION. Duck-typed like PrecursorContribution.
    """
    event_title: str
    usd_sentiment: float
    trust_weight: float
    time_weight: float
    combined_weight: float


@dataclass
class KalshiMarketContribution:
    """
    Audit trail for a Kalshi prediction-market read (data_layer.kalshi_feed's
    KalshiRead), mapped onto the USD axis via EVENT_SURPRISE_DIRECTION (for
    numeric events) or RATE_DECISION_DIRECTION (for FOMC/Federal Funds
    Rate). Duck-typed like the other three contribution types — same
    usd_sentiment/combined_weight fields — so it flows through the
    existing weighted-average, agreement, and coverage math unchanged.
    """
    event_title: str
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
    thin_sample: bool = False           # True if probability was pulled toward 50% by THIN_SAMPLE_PROBABILITY_CAP (see R3)
    macro_backdrop_agrees: bool | None = None   # None = no macro backdrop data available; True/False = did the dollar/rates backdrop agree with this read? (see R5)
    macro_backdrop_note: str | None = None
    cot_crowding_flag: bool | None = None       # None = no COT data or not extreme; True = crowded and aligned with this read (see R-fundamental-signals-batch)
    cot_crowding_note: str | None = None
    equity_risk_agrees: bool | None = None       # None = not a risk_sentiment instrument, or no equity data; True/False = did the equity backdrop agree?
    equity_risk_note: str | None = None
    oil_shock_flag: bool = False                 # True = a sharp single-session oil move was detected
    oil_shock_note: str | None = None
    chain_conflict_flag: bool = False             # True = 2+ linked, confirmed precursors disagreed in direction
    chain_conflict_note: str | None = None
    redundant_contributions_discounted: int = 0   # how many article contributions were discounted as likely-redundant with an earlier one (see _apply_redundancy_discounts)
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
        if self.macro_backdrop_agrees is False:
            base += f" — ⚠ {self.macro_backdrop_note}"
        if self.chain_conflict_flag:
            base += f" — ⚠ {self.chain_conflict_note}"
        return base


def _get_article_sentiment(article: NewsArticle) -> tuple[float, list[str]]:
    """
    Returns (usd_sentiment, matched_terms). Tiered fallback, cheapest and
    most-deterministic first — see the block comment above
    CONTEXTUAL_CONFIDENCE_THRESHOLD in config.settings for the full
    rationale:

      1. native_sentiment on the article, if a vendor already supplied one
         (Alpha Vantage / APITube) — unchanged, always wins if present.
      2. FinBERT (local, free) — only if ENABLE_FINBERT_SENTIMENT=1, and
         used only when its own top-class confidence is at or above
         CONTEXTUAL_CONFIDENCE_THRESHOLD.
      3. Claude API — only if ENABLE_LLM_SENTIMENT=1, and only when
         FinBERT was unavailable/disabled or itself unsure (confidence
         below threshold); this is the tier that actually understands
         hedged/conditional language ("rate hike risk IF data surprises")
         instead of matching it as declarative.
      4. The keyword lexicon (sentiment.py) — final fallback, zero
         dependencies, zero cost, unchanged behavior from before this
         tiering existed. This is what runs with both flags at their
         default (off) — installing torch/transformers/anthropic alone
         does NOT change scoring behavior, only the env vars do.
    """
    if article.native_sentiment is not None:
        clamped = max(-1.0, min(1.0, article.native_sentiment))
        return clamped, ["<native_sentiment>"]

    finbert_result = score_article_finbert(article.title, article.summary) if ENABLE_FINBERT_SENTIMENT else None
    if finbert_result is not None and finbert_result.confidence >= CONTEXTUAL_CONFIDENCE_THRESHOLD:
        return finbert_result.usd_score, [f"<finbert:{finbert_result.label}:{finbert_result.confidence:.2f}>"]

    llm_result = score_article_llm(article.title, article.summary) if ENABLE_LLM_SENTIMENT else None
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


_REDUNDANCY_STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "for", "to", "and", "or", "is", "are",
    "as", "at", "by", "with", "from", "its", "it's", "that", "this", "after",
    "before", "amid", "over", "says", "said", "will", "has", "have", "had",
    "be", "been", "was", "were", "than", "into", "but", "not", "no",
}


def _significant_words(text: str) -> set[str]:
    """Lowercased, stopword- and short-word-filtered word set — the shared basis _is_likely_redundant() compares two articles' actual text on."""
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if w not in _REDUNDANCY_STOPWORDS and len(w) > 2}


def _is_likely_redundant(a: ArticleContribution, b: ArticleContribution) -> bool:
    """
    True if `b` looks like the same underlying story as `a` — close in
    time AND its title+summary text substantially overlaps `a`'s. Both
    conditions are required (see REDUNDANCY_TIME_PROXIMITY_MINUTES /
    REDUNDANCY_TERM_OVERLAP_THRESHOLD's comments in config.settings for
    why one alone isn't enough).

    Compares the articles' own TEXT (title+summary), not `matched_terms` —
    deliberately, so this works regardless of which sentiment tier scored
    the article. `matched_terms` only holds real lexicon phrases for the
    lexicon fallback tier; native_sentiment/FinBERT/LLM-scored articles
    (the common case now that ENABLE_FINBERT_SENTIMENT defaults on, R2)
    carry a tag like "<finbert:positive:0.78>" instead, which isn't a
    phrase list at all — comparing THAT would make this check silently
    inert for most real articles. Text-based comparison has no such gap.
    """
    time_gap_minutes = abs((a.article.published_utc - b.article.published_utc).total_seconds()) / 60.0
    if time_gap_minutes > REDUNDANCY_TIME_PROXIMITY_MINUTES:
        return False

    words_a = _significant_words(f"{a.article.title} {a.article.summary}")
    words_b = _significant_words(f"{b.article.title} {b.article.summary}")
    if not words_a or not words_b:
        return False  # nothing meaningful to compare — never guess redundancy from an empty/trivial text

    overlap = len(words_a & words_b) / len(words_a | words_b)
    return overlap >= REDUNDANCY_TERM_OVERLAP_THRESHOLD


def _apply_redundancy_discounts(contributions: list[ArticleContribution]) -> tuple[list[ArticleContribution], int]:
    """
    Returns (adjusted_contributions, discounted_count). Processes
    contributions earliest-published first; any contribution found
    likely-redundant (_is_likely_redundant()) with an EARLIER,
    already-processed contribution has its combined_weight discounted by
    REDUNDANCY_DISCOUNT_MULTIPLIER — a later syndicated repeat of the
    same story is still weak corroborating evidence, not zero evidence,
    so it's discounted rather than dropped entirely.

    Comparing only against earlier contributions (not all pairs) means a
    chain of 3+ near-identical articles doesn't let the 2nd and 3rd each
    independently "not count" the 1st while still fully counting each
    other — every one after the first genuine telling gets discounted.
    """
    ordered = sorted(contributions, key=lambda c: c.article.published_utc)
    kept: list[ArticleContribution] = []
    discounted_count = 0
    for c in ordered:
        if any(_is_likely_redundant(earlier, c) for earlier in kept):
            kept.append(replace(c, combined_weight=c.combined_weight * REDUNDANCY_DISCOUNT_MULTIPLIER))
            discounted_count += 1
        else:
            kept.append(c)
    return kept, discounted_count


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


def get_precursor_events_for(
    target_title: str,
    target_event_time_utc: dt.datetime,
    conn,
) -> list[EconomicEvent]:
    """
    Graph-driven replacement for the old in-memory-calendar precursor
    lookup (removed from data_layer/calendar_feed.py). Looks up
    EVENT_INFLUENCE_LINKS[target_title] (empty list if no configured
    links). For each linked precursor title, fetches that title's most
    recent RESOLVED (actual IS NOT NULL) event_history row — kept only if
    it falls inside target's own PRE_EVENT_WINDOW_HOURS pre-event window,
    the same bound the old lookup used, so a resolved row from a PRIOR
    cycle (e.g. last month's ADP print) is never mistaken for this
    cycle's precursor. Also requires country == "USD" strictly (2026-09-03
    fix) — a resolved row with country NULL or any other value is skipped,
    never treated as USD by default; see the inline comment below for why.
    Skips any precursor title with no resolved row in that window at all
    — never fabricates.

    `conn` is a webapp.store-shaped sqlite3.Connection (duck-typed — this
    module never imports webapp/ at module level, to avoid a cycle with
    webapp/ importing scoring/).
    """
    from webapp.store import get_event_history  # local import: avoid a module-level cycle with webapp/

    linked = EVENT_INFLUENCE_LINKS.get(target_title, [])
    if not linked:
        return []
    window_start = target_event_time_utc - dt.timedelta(hours=PRE_EVENT_WINDOW_HOURS)

    precursors: list[EconomicEvent] = []
    for precursor_title, _weight in linked:
        rows = get_event_history(conn, precursor_title, limit=6)
        # country == "USD" strictly (2026-09-03 root-cause fix) — never
        # NULL/unknown either. Many precursor titles are generic strings
        # ("CPI m/m", "Retail Sales m/m", "Unemployment Rate") that other
        # countries also use on Forex Factory; confirmed live that foreign
        # prints under these exact titles have landed in event_history
        # before country was tracked. This path is fully automated with no
        # human review, unlike webapp.store.get_events_with_stale_missing_
        # actual()'s manual-research list — a legacy row with country
        # still NULL is excluded here until it self-heals or gets
        # backfilled, never treated as USD by default.
        resolved = [r for r in rows if r.actual is not None and r.country == "USD"]
        if not resolved:
            continue
        most_recent = resolved[0]  # get_event_history orders DESC by event_time_utc
        event_time = dt.datetime.fromisoformat(most_recent.event_time_utc)
        if not (window_start <= event_time < target_event_time_utc):
            continue
        precursors.append(
            EconomicEvent(
                title=most_recent.event_title,
                country="USD",
                impact=most_recent.impact or "Medium",
                event_time_utc=event_time,
                forecast=most_recent.forecast,
                previous=most_recent.previous,
                actual=most_recent.actual,
            )
        )
    return precursors


def _build_print_call_contribution(
    print_call,  # PrintCall | None — duck-typed, no import from scoring.print_direction needed
    event: EconomicEvent,
    as_of: dt.datetime,
):
    """
    Returns None (no contribution) if print_call is None, its direction is
    'in_line' (no lean either way), or the event's title has no
    EVENT_SURPRISE_DIRECTION entry (defensive — PRINT_SURPRISE_LEXICON is
    a subset of that dict, so this should never actually miss).
    """
    if print_call is None or print_call.direction == "in_line":
        return None
    surprise_map = EVENT_SURPRISE_DIRECTION.get(event.title)
    if surprise_map is None:
        return None

    raw = print_call.confidence if print_call.direction == "higher" else -print_call.confidence
    usd_sentiment = raw if surprise_map == "higher_bullish" else -raw

    age_minutes = max(0.0, (as_of - event.event_time_utc).total_seconds() / 60.0)
    time_w = 0.5 ** (age_minutes / PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES)
    return PrintCallContribution(
        event_title=event.title,
        usd_sentiment=usd_sentiment,
        trust_weight=PRINT_CALL_TRUST_WEIGHT,
        time_weight=time_w,
        combined_weight=PRINT_CALL_TRUST_WEIGHT * time_w,
    )


def _build_trend_streak_contribution(
    trend_signal,  # TrendSignal | None — duck-typed (.direction, .strength), no import from webapp.trend
    event: EconomicEvent,
):
    """
    Returns None if trend_signal is None (either the accumulator's
    MIN_OCCURRENCES_FOR_TREND_PRIOR gate wasn't met, or
    compute_trend_signal() itself found no clean majority) or the event's
    title has no EVENT_SURPRISE_DIRECTION entry. No time decay — a
    historical streak isn't tied to a specific timestamp.
    """
    if trend_signal is None:
        return None
    surprise_map = EVENT_SURPRISE_DIRECTION.get(event.title)
    if surprise_map is None:
        return None

    raw = trend_signal.strength if trend_signal.direction == "higher" else -trend_signal.strength
    usd_sentiment = raw if surprise_map == "higher_bullish" else -raw

    return TrendStreakContribution(
        event_title=event.title,
        usd_sentiment=usd_sentiment,
        trust_weight=TREND_STREAK_TRUST_WEIGHT,
        time_weight=1.0,
        combined_weight=TREND_STREAK_TRUST_WEIGHT,
    )


def _build_kalshi_contribution(
    kalshi_read,  # KalshiRead | None — duck-typed, no import from data_layer.kalshi_feed needed
    event: EconomicEvent,
    as_of: dt.datetime,
    surprise_direction_value: str | None = None,
):
    """
    Returns None (no contribution) if kalshi_read is None, its direction
    is 'in_line' (no lean either way), or no direction-mapping value was
    resolved for this event title. surprise_direction_value is the
    ALREADY-RESOLVED direction-mapping string ('higher_bullish' /
    'higher_bearish' from EVENT_SURPRISE_DIRECTION, or 'bullish' /
    'bearish' / 'neutral' straight from RATE_DECISION_DIRECTION for a
    discrete FOMC decision) — the caller (scoring/backtest_accumulator.py)
    already knows which of the two mapping dicts matched this event's
    title from its own lookup, so this function doesn't re-derive it.
    """
    if kalshi_read is None or kalshi_read.implied_direction == "in_line":
        return None
    if surprise_direction_value is None:
        return None

    raw = kalshi_read.implied_probability if kalshi_read.implied_direction == "higher" else -kalshi_read.implied_probability
    if surprise_direction_value == "higher_bullish":
        usd_sentiment = raw
    elif surprise_direction_value == "higher_bearish":
        usd_sentiment = -raw
    elif surprise_direction_value == "bullish":
        usd_sentiment = abs(raw)
    elif surprise_direction_value == "bearish":
        usd_sentiment = -abs(raw)
    else:  # 'neutral', or any unrecognized value — no lean, no contribution
        return None

    age_minutes = max(0.0, (as_of - event.event_time_utc).total_seconds() / 60.0)
    time_w = 0.5 ** (age_minutes / PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES)
    return KalshiMarketContribution(
        event_title=event.title,
        usd_sentiment=usd_sentiment,
        trust_weight=KALSHI_TRUST_WEIGHT,
        time_weight=time_w,
        combined_weight=KALSHI_TRUST_WEIGHT * time_w,
    )


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


def _signal_bearing_count(contributions: list[ArticleContribution]) -> int:
    """
    How many contributions (articles + structured precursor/print/trend/
    Kalshi signals combined) actually carried a real directional
    opinion — same epsilon and "silent contribution" concept
    _agreement_and_coverage() already uses, just counted rather than
    weighted. Feeds _apply_thin_sample_cap() below (R3): a small count
    here means the probability read is riding on very little evidence,
    regardless of how strongly that little evidence agrees.
    """
    return sum(1 for c in contributions if abs(c.usd_sentiment) >= 1e-6)


def _apply_thin_sample_cap(probability: float, signal_count: int) -> tuple[float, bool]:
    """
    Returns (possibly-capped probability, whether it was actually thin).
    Below THIN_SAMPLE_SIGNAL_THRESHOLD signal-bearing contributions, caps
    probability's distance from 50% at THIN_SAMPLE_PROBABILITY_CAP - 0.5 —
    see the constants' comments in config.settings for the BACKTEST_REPORT
    finding this targets (near-certain probabilities from 2-3 articles).
    Deliberately independent of the agreement x coverage confidence
    discount already applied upstream: a thin sample that unanimously
    agrees still passes THAT discount untouched (agreement=1.0), so
    without this cap it can still reach 99% probability from 2 articles.
    """
    if signal_count >= THIN_SAMPLE_SIGNAL_THRESHOLD:
        return probability, False
    max_distance = THIN_SAMPLE_PROBABILITY_CAP - 0.5
    distance = probability - 0.5
    clamped_distance = max(-max_distance, min(max_distance, distance))
    return 0.5 + clamped_distance, True


def _check_macro_backdrop(
    aggregate_usd: float,
    macro_backdrop,  # MacroBackdropRead | None — duck-typed (.lean, .dollar_index_trend_pct, .real_yield_trend_bps), no data_layer.macro_backdrop import needed
) -> tuple[bool | None, str | None]:
    """
    Compares this bundle's aggregate USD-directional read against the
    independent dollar/rates backdrop (R5). Returns (agrees, note):

    - (None, None) if no macro backdrop data is available at all, or the
      backdrop itself has no clear lean (too small a move on both
      measures to call) — "no data"/"no lean" is never treated as
      agreement OR disagreement, same "absent, not fabricated" contract
      every other optional signal in this pipeline uses.
    - (True, None) if the backdrop's lean matches the aggregate's sign.
    - (False, a human-readable note) if they clearly disagree — this
      never flips direction or probability, only feeds into a confidence
      discount (see score_bundle()) — a real signal shouldn't be able to
      silently overrule the rest of the pipeline on the strength of two
      macro series alone.
    """
    if macro_backdrop is None:
        return None, None
    lean = macro_backdrop.lean
    if lean is None:
        return None, None

    usd_sign = 1 if aggregate_usd >= 0 else -1
    if lean == usd_sign:
        return True, None

    backdrop_dir = "USD-bullish" if lean > 0 else "USD-bearish"
    read_dir = "USD-bullish" if usd_sign > 0 else "USD-bearish"
    note = (
        f"Macro backdrop (dollar index/real yields/oil) leans {backdrop_dir}, "
        f"but this read is {read_dir} — treat with extra caution until they align."
    )
    return False, note


def _check_cot_crowding(
    aggregate_usd: float,
    cot_positioning,  # CotPositioningRead | None — duck-typed (.is_crowded), no data_layer.cot_positioning import needed
) -> tuple[bool | None, str | None]:
    """
    Confidence-only crowding dampener (spec: never a directional lean).
    Opposite polarity from _check_macro_backdrop: this fires on
    AGREEMENT with an extreme reading, not disagreement — a crowded
    trade in the SAME direction as this read is the caution signal, not
    a crowded trade in the opposite direction (which this check ignores
    entirely, hence no (False, ...) case here at all).

    Returns (None, None) if no COT data, or positioning isn't extreme.
    Returns (True, note) if positioning IS extreme AND aligned with
    aggregate_usd's sign.
    """
    if cot_positioning is None:
        return None, None
    crowded_direction = cot_positioning.is_crowded
    if crowded_direction is None:
        return None, None

    usd_sign = 1 if aggregate_usd >= 0 else -1
    if crowded_direction != usd_sign:
        return None, None

    direction_label = "long" if crowded_direction > 0 else "short"
    note = (
        f"COT positioning shows crowded {direction_label} USD Index speculative positioning "
        f"(percentile {cot_positioning.percentile_in_trailing_window:.0f}) aligned with this read — "
        f"may already be priced in, treat with extra caution."
    )
    return True, note


def _check_equity_risk_sentiment(
    instrument_score: float,
    instrument: str,
    macro_backdrop,  # MacroBackdropRead | None — duck-typed (.equity_index_trend_pct), reuses the same object _check_macro_backdrop reads
) -> tuple[bool | None, str | None]:
    """
    Only ever active for risk_sentiment-mapped instruments (today: US30)
    — returns (None, None) immediately for anything else, regardless of
    equity data availability. Compares equity_index_trend_pct's sign
    (positive = risk-on) against instrument_score's sign for THIS
    instrument (not aggregate_usd) — an equity index has no USD sign of
    its own.
    """
    if INSTRUMENTS.get(instrument, {}).get("usd_relationship") != "risk_sentiment":
        return None, None
    if macro_backdrop is None:
        return None, None
    equity_trend = macro_backdrop.equity_index_trend_pct
    if equity_trend is None or abs(equity_trend) < EQUITY_INDEX_LEAN_THRESHOLD_PCT:
        return None, None

    equity_sign = 1 if equity_trend > 0 else -1
    instrument_sign = 1 if instrument_score >= 0 else -1
    if equity_sign == instrument_sign:
        return True, None

    equity_dir = "risk-on (equities up)" if equity_sign > 0 else "risk-off (equities down)"
    read_dir = "bullish" if instrument_sign > 0 else "bearish"
    note = (
        f"Equity risk-sentiment backdrop leans {equity_dir}, but this {instrument} read is {read_dir} "
        f"— treat with extra caution until they align."
    )
    return False, note


def _check_oil_shock(macro_backdrop) -> tuple[bool, str | None]:
    """
    Fires on a sharp single-session oil move, regardless of direction or
    of this bundle's own USD read — "something sharp just happened
    outside the tracked calendar," not an agree/disagree comparison.
    Always returns a bool (never None) for the flag itself, matching
    ProbabilityResult.oil_shock_flag's bool (not Optional[bool]) type —
    there's no meaningful "unknown" state distinct from "no shock."
    """
    if macro_backdrop is None:
        return False, None
    daily_change = macro_backdrop.oil_daily_change_pct
    if daily_change is None or abs(daily_change) < OIL_SHOCK_DAILY_THRESHOLD_PCT:
        return False, None

    direction = "spiked" if daily_change > 0 else "dropped"
    note = (
        f"Oil {direction} {abs(daily_change):.1f}% in the most recent session — "
        f"a possible exogenous shock outside the tracked calendar, treat this call with extra caution."
    )
    return True, note


def _check_precursor_chain_conflict(
    precursor_contributions: list[PrecursorContribution],
) -> tuple[bool, str | None]:
    """
    (True, note) if 2+ precursor contributions disagree in sign (one
    USD-bullish, one USD-bearish) — a genuine conflict within THIS target
    event's own linked-precursor chain (config.settings.EVENT_INFLUENCE_LINKS).
    Distinct from _detect_contradiction() (article-only, recent-vs-older
    narrative shift) and from _check_macro_backdrop() (compares against
    an external dollar/rates read, not against other precursors).

    (False, None) if fewer than 2 precursor contributions, or all agree.
    Never touches direction or probability — confidence-only, same
    discipline as every other _check_* function here.
    """
    if len(precursor_contributions) < 2:
        return False, None

    bullish = [c for c in precursor_contributions if c.usd_sentiment > 0]
    bearish = [c for c in precursor_contributions if c.usd_sentiment < 0]
    if not bullish or not bearish:
        return False, None

    bullish_titles = ", ".join(c.event.title for c in bullish)
    bearish_titles = ", ".join(c.event.title for c in bearish)
    note = (
        f"Linked precursor chain conflict: {bullish_titles} read USD-bullish while "
        f"{bearish_titles} read USD-bearish — not silently averaged, treat this call with extra caution."
    )
    return True, note


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
        return -usd_sentiment * RISK_SENTIMENT_DAMPENING  # dampened relative to gold's cleaner inverse relationship
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


def _direction_for_score(instrument_score: float, current_direction: str | None) -> Direction:
    """
    Maps instrument_score to BULLISH/BEARISH/NEUTRAL, applying hysteresis
    when current_direction is known — see DIRECTION_FLIP_HYSTERESIS_MARGIN's
    comment in config/settings.py for the real bug this fixes (21 direction
    flips within 72h on pure time-decay noise, no hysteresis to hold the
    read steady).

    current_direction=None (no known prior state, e.g. this event's
    first-ever score): plain DIRECTION_NEUTRAL_BAND threshold, no
    hysteresis — there's nothing to be "sticky" relative to yet.

    current_direction known: if the plain (non-hysteresis) read already
    matches current_direction, nothing changed — return it as-is,
    hysteresis is a no-op. If the plain read DIFFERS from
    current_direction, only accept that different read if instrument_score
    clears the WIDER band (DIRECTION_NEUTRAL_BAND + DIRECTION_FLIP_HYSTERESIS_MARGIN);
    otherwise current_direction is "sticky" and is returned unchanged —
    this uniformly covers every transition (bullish->neutral, neutral->
    bearish, a direct bullish->bearish jump, etc.) with one rule.
    """
    if instrument_score > DIRECTION_NEUTRAL_BAND:
        plain = Direction.BULLISH
    elif instrument_score < -DIRECTION_NEUTRAL_BAND:
        plain = Direction.BEARISH
    else:
        plain = Direction.NEUTRAL

    if current_direction is None or plain.value == current_direction:
        return plain

    wide = DIRECTION_NEUTRAL_BAND + DIRECTION_FLIP_HYSTERESIS_MARGIN
    if instrument_score > wide:
        return Direction.BULLISH
    if instrument_score < -wide:
        return Direction.BEARISH
    return Direction(current_direction)  # move is real but hasn't cleared the wider band — stay put


def score_bundle(
    bundle: EventNewsBundle,
    instrument: str,
    precursor_events: list[EconomicEvent] | None = None,
    print_call=None,   # PrintCall | None — duck-typed
    trend_signal=None,  # TrendSignal | None — duck-typed
    kalshi_read=None,   # KalshiRead | None — duck-typed
    kalshi_direction_override=None,  # str | None — 'higher_bullish'/'higher_bearish', see below
    macro_backdrop=None,  # MacroBackdropRead | None — duck-typed, see _check_macro_backdrop(), _check_equity_risk_sentiment(), _check_oil_shock()
    cot_positioning=None,  # CotPositioningRead | None — duck-typed, see _check_cot_crowding()
    current_direction: str | None = None,  # 'bullish'/'bearish'/'neutral' | None — see _direction_for_score()
) -> ProbabilityResult:
    """
    Main entry point: score an EventNewsBundle for a given instrument
    (must be a key in config.settings.INSTRUMENTS, e.g. 'XAUUSD').

    precursor_events: optional leading-indicator events (already-released
    minor/medium USD releases that predict this event — ADP before NFP,
    PPI before CPI, etc; see get_precursor_events_for() above for how to
    build this list). Their forecast-vs-actual surprise is
    blended in as a structured, high-trust contribution alongside article
    sentiment — same USD-directional axis, same weighted-average math,
    just a different (and more reliable) source of signal.

    print_call: optional — this occurrence's print-direction call
    (scoring/print_direction.py's PrintCall). Blended in as a structured
    contribution the same way a precursor is, but at a lower trust weight
    (config.settings.PRINT_CALL_TRUST_WEIGHT) since it's inference about a
    number that hasn't printed yet. An 'in_line' call contributes nothing.

    trend_signal: optional — the event's historical beat/miss streak
    (webapp/trend.py's TrendSignal, gated by the caller at
    MIN_OCCURRENCES_FOR_TREND_PRIOR before being passed in here). Blended
    in at TREND_STREAK_TRUST_WEIGHT, with no time decay. None contributes
    nothing.

    kalshi_read: optional — a Kalshi prediction-market read
    (data_layer/kalshi_feed.py's KalshiRead) for this occurrence. Blended
    in at config.settings.KALSHI_TRUST_WEIGHT (the highest tier — real
    money priced directly on the exact event being scored), with the same
    decay a precursor uses. An 'in_line' read contributes nothing.

    kalshi_direction_override: optional — a 'higher_bullish'/'higher_bearish'
    string to use INSTEAD of looking up EVENT_SURPRISE_DIRECTION[bundle.event.title]
    when resolving kalshi_read's USD-sentiment sign. Needed for events like
    FOMC/Federal Funds Rate that aren't in EVENT_SURPRISE_DIRECTION at all
    (a discrete rate decision, not a continuous forecast-vs-actual number)
    — the caller (scoring/backtest_accumulator.py's _read_kalshi_signal())
    already knows which of its two Kalshi-series dicts matched this
    event's title and resolves the correct direction value itself, so
    score_bundle() stays free of any FOMC-specific special-casing or a
    dependency on config.settings.KALSHI_RATE_DECISION_SERIES. Ignored
    when kalshi_read is None.

    macro_backdrop: optional — an independent dollar-index/real-yield
    read (data_layer.macro_backdrop.MacroBackdropRead), R5's
    macro-backdrop cross-check. NEVER blended into aggregate_usd_sentiment
    as a weighted vote (no real backtested trust weight exists for it) —
    it can only discount CONFIDENCE via
    MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER when it clearly
    disagrees with this bundle's own read, same "pull toward uncertain,
    never invent a wrong-direction call" discipline agreement/coverage
    and the thin-sample cap already follow. See _check_macro_backdrop().
    None contributes nothing (confidence unchanged, macro_backdrop_agrees
    stays None).

    cot_positioning: optional — an independent CFTC COT positioning read
    (data_layer.cot_positioning.CotPositioningRead), the fundamental
    signals batch's crowding dampener. NEVER blended into
    aggregate_usd_sentiment (same "no real backtested trust weight yet"
    discipline as macro_backdrop) — it can only discount CONFIDENCE, and
    only when positioning is BOTH extreme AND aligned with this read's
    own direction (opposite polarity from macro_backdrop's disagreement-
    based discount). See _check_cot_crowding().

    current_direction: optional — the currently-recorded direction for
    this (event, instrument) pair ('bullish'/'bearish'/'neutral'), if
    known. Enables hysteresis on direction flips — see
    _direction_for_score(). None (the default) reproduces the old,
    non-hysteresis, "first-ever score" behavior exactly.
    """
    if instrument not in INSTRUMENTS:
        raise ValueError(f"Unknown instrument {instrument!r} — add it to config.settings.INSTRUMENTS first")

    as_of = bundle.as_of_utc
    article_contributions = _build_contributions(bundle.articles, as_of, TIME_DECAY_HALF_LIFE_MINUTES)
    # Correlation/redundancy discount (2026-08-16 follow-up to R5): applied
    # here, before article_contributions feeds into aggregation, agreement,
    # contradiction detection, or the thin-sample count — every one of
    # those benefits from not treating a syndicated repeat of the same
    # story as independent confirmation. See _apply_redundancy_discounts()'s
    # docstring.
    article_contributions, redundant_contributions_discounted = _apply_redundancy_discounts(article_contributions)
    precursor_contributions = _build_precursor_contributions(precursor_events or [], as_of)
    print_call_contribution = _build_print_call_contribution(print_call, bundle.event, as_of)
    trend_streak_contribution = _build_trend_streak_contribution(trend_signal, bundle.event)
    kalshi_surprise_value = kalshi_direction_override if kalshi_direction_override is not None else EVENT_SURPRISE_DIRECTION.get(bundle.event.title)
    kalshi_contribution = _build_kalshi_contribution(
        kalshi_read, bundle.event, as_of,
        surprise_direction_value=kalshi_surprise_value,
    )
    extra_contributions = precursor_contributions + (
        [print_call_contribution] if print_call_contribution is not None else []
    ) + (
        [trend_streak_contribution] if trend_streak_contribution is not None else []
    ) + (
        [kalshi_contribution] if kalshi_contribution is not None else []
    )
    all_contributions = article_contributions + extra_contributions

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

    # R3: separately, cap how far a THIN sample can push probability from
    # 50% regardless of how well that thin sample agrees with itself — see
    # _apply_thin_sample_cap()'s docstring for why this is independent of
    # the agreement-based discount just above.
    signal_count = _signal_bearing_count(all_contributions)
    adjusted_probability, thin_sample = _apply_thin_sample_cap(adjusted_probability, signal_count)

    # Confidence must reflect BOTH agreement (do the sources that spoke
    # agree?) AND coverage (did enough of the bundle actually speak?).
    # agreement alone lets a single signal-bearing article among a dozen
    # silent ones report 100% confidence — it trivially agrees with itself.
    confidence = agreement * coverage

    # R5: independent dollar/rates backdrop check — measured on aggregate_usd
    # (the raw USD-directional axis), same reasoning as agreement/coverage
    # above. A clear disagreement discounts confidence; it never touches
    # probability or direction.
    macro_backdrop_agrees, macro_backdrop_note = _check_macro_backdrop(aggregate_usd, macro_backdrop)
    if macro_backdrop_agrees is False:
        confidence *= MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER

    cot_crowding_flag, cot_crowding_note = _check_cot_crowding(aggregate_usd, cot_positioning)
    if cot_crowding_flag:
        confidence *= COT_CROWDING_CONFIDENCE_MULTIPLIER

    equity_risk_agrees, equity_risk_note = _check_equity_risk_sentiment(instrument_score, instrument, macro_backdrop)
    if equity_risk_agrees is False:
        confidence *= EQUITY_RISK_DISAGREEMENT_CONFIDENCE_MULTIPLIER

    oil_shock_flag, oil_shock_note = _check_oil_shock(macro_backdrop)
    if oil_shock_flag:
        confidence *= OIL_SHOCK_CONFIDENCE_MULTIPLIER

    chain_conflict_flag, chain_conflict_note = _check_precursor_chain_conflict(precursor_contributions)
    if chain_conflict_flag:
        confidence *= PRECURSOR_CHAIN_CONFLICT_CONFIDENCE_MULTIPLIER

    direction = _direction_for_score(instrument_score, current_direction)

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
        thin_sample=thin_sample,
        macro_backdrop_agrees=macro_backdrop_agrees,
        macro_backdrop_note=macro_backdrop_note,
        cot_crowding_flag=cot_crowding_flag,
        cot_crowding_note=cot_crowding_note,
        equity_risk_agrees=equity_risk_agrees,
        equity_risk_note=equity_risk_note,
        oil_shock_flag=oil_shock_flag,
        oil_shock_note=oil_shock_note,
        chain_conflict_flag=chain_conflict_flag,
        chain_conflict_note=chain_conflict_note,
        redundant_contributions_discounted=redundant_contributions_discounted,
        contributions=article_contributions,
        precursor_contributions=precursor_contributions,
    )
