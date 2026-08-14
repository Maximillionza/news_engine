"""
Synthetic smoke test — no network required. Validates the scoring pipeline
logic itself (weighting, mapping, contradiction detection, flip tracking)
using hand-built articles rather than live feeds, since this sandbox can't
reach the real APIs. Run this after any change to the scoring engine to
catch obvious regressions before touching real data.
"""
import datetime as dt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent, find_precursor_events
from data_layer.event_context import EventNewsBundle
from data_layer.news_feed import NewsArticle, deduplicate_articles
import scoring.probability_engine as probability_engine
from scoring.probability_engine import score_bundle, Direction
from scoring.history import EventScoreTracker
from scoring.sentiment import score_article_text

# This file's whole contract (see module docstring) is "no network
# required," testing pipeline AGGREGATION logic (weighting, mapping,
# contradiction detection) with hand-built, deterministic lexicon scores.
# R2 (docs/fundamental-analysis-swot-2026-08-14.md) made FinBERT the
# default contextual-sentiment tier, which loads a local model (and
# contacts the HF Hub on first load) the first time scoring runs in a
# process — forcing it off here keeps this file testing what it always
# tested; tests/test_contextual_sentiment.py is where FinBERT's own
# scoring behavior gets validated. A plain reassignment, not
# unittest.mock.patch, is enough — this file's own process never needs
# the original value restored.
probability_engine.ENABLE_FINBERT_SENTIMENT = False
probability_engine.ENABLE_LLM_SENTIMENT = False


def make_article(title, summary, hours_before_event, source_type="alpha_vantage_news", native_sentiment=None):
    published = EVENT_TIME - dt.timedelta(hours=hours_before_event)
    return NewsArticle(
        title=title,
        summary=summary,
        source=source_type,
        source_type=source_type,
        published_utc=published,
        url="https://example.com/article",
        native_sentiment=native_sentiment,
    )


EVENT_TIME = dt.datetime(2026, 8, 7, 12, 30, tzinfo=UTC_TZ)  # a Friday NFP-style release


def test_sentiment_lexicon():
    print("=== Sentiment lexicon test ===")
    bullish = score_article_text("Fed signals hawkish stance as inflation surges", "Officials hint at rate hike")
    bearish = score_article_text("Fed turns dovish, hints at rate cut", "Markets price in easing")
    neutral = score_article_text("Markets await Friday's jobs report", "Traders position ahead of data")
    negated = score_article_text("Fed is not raising rates despite pressure", "")

    print(f"bullish text -> {bullish.usd_score:.2f} (terms: {bullish.matched_terms})")
    print(f"bearish text -> {bearish.usd_score:.2f} (terms: {bearish.matched_terms})")
    print(f"neutral text -> {neutral.usd_score:.2f} (terms: {neutral.matched_terms})")
    print(f"negated text -> {negated.usd_score:.2f} (terms: {negated.matched_terms})")

    assert bullish.usd_score > 0, "hawkish/rate hike language should score USD-bullish"
    assert bearish.usd_score < 0, "dovish/rate cut language should score USD-bearish"
    assert neutral.usd_score == 0.0, "no lexicon matches should score exactly neutral"
    assert negated.usd_score < 0, "negated 'raising rates' should flip to USD-bearish"
    print("PASS\n")


def test_scoring_consistent_bullish_usd():
    print("=== Consistent USD-bullish coverage -> gold should read bearish ===")
    event = EconomicEvent(
        title="Non-Farm Payrolls", country="USD", impact="High", event_time_utc=EVENT_TIME
    )
    articles = [
        make_article("Fed hints at hawkish rate hike", "Strong jobs growth expected", hours_before_event=40),
        make_article("Dollar strength continues on hawkish bets", "Beats expectations widely forecast", hours_before_event=20),
        make_article("Strong jobs report seen boosting dollar", "Economy resilient ahead of NFP", hours_before_event=2),
    ]
    bundle = EventNewsBundle(event=event, articles=articles, as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD")
    print(result.summary())
    print(f"  aggregate_usd_sentiment={result.aggregate_usd_sentiment:.2f} instrument_score={result.instrument_score:.2f}")

    assert result.direction == Direction.BEARISH, "USD-bullish news should map to bearish gold (inverse relationship)"
    assert result.confidence > 0.5, "consistent articles should produce reasonably high agreement/confidence"
    print("PASS\n")


def test_contradiction_detection():
    print("=== Older bullish-USD coverage, recent dovish reversal -> should flag contradiction ===")
    event = EconomicEvent(
        title="Non-Farm Payrolls", country="USD", impact="High", event_time_utc=EVENT_TIME
    )
    articles = [
        # Older window: strongly hawkish
        make_article("Fed hawkish, rate hike expected", "Strong dollar seen ahead of NFP", hours_before_event=44),
        make_article("Dollar strength on hawkish Fed bets", "Tightening expected to continue", hours_before_event=30),
        # Recent window: sudden dovish reversal
        make_article("Fed turns dovish ahead of data, rate cut talk grows", "Dollar weakness spreading", hours_before_event=2),
        make_article("Markets price in dovish pivot, easing bets rise", "Weak dollar expected", hours_before_event=1),
    ]
    bundle = EventNewsBundle(event=event, articles=articles, as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD")
    print(result.summary())
    if result.contradiction_note:
        print(f"  note: {result.contradiction_note}")

    assert result.contradiction_flag is True, "sharp recent reversal vs older sentiment should be flagged"
    print("PASS\n")


def test_flip_tracking():
    print("=== EventScoreTracker flip detection across successive runs ===")
    event = EconomicEvent(title="CPI", country="USD", impact="High", event_time_utc=EVENT_TIME)
    tracker = EventScoreTracker(instrument="XAUUSD", event_label="CPI Aug 2026")

    # Run 1: bullish USD news -> bearish gold call
    bundle1 = EventNewsBundle(
        event=event,
        articles=[make_article("Hawkish Fed, rate hike bets rise", "Dollar strength continues", hours_before_event=40)],
        as_of_utc=EVENT_TIME - dt.timedelta(hours=40),
    )
    result1 = score_bundle(bundle1, "XAUUSD")
    flip1 = tracker.record(result1)
    print(f"Run 1: {result1.summary()} | flip={flip1}")

    # Run 2: dovish reversal -> bullish gold call
    bundle2 = EventNewsBundle(
        event=event,
        articles=[make_article("Fed turns dovish, rate cut expected", "Dollar weakness spreading", hours_before_event=2)],
        as_of_utc=EVENT_TIME - dt.timedelta(hours=2),
    )
    result2 = score_bundle(bundle2, "XAUUSD")
    flip2 = tracker.record(result2)
    print(f"Run 2: {result2.summary()} | flip={flip2.describe() if flip2 else None}")

    assert flip2 is not None, "direction should flip from run 1 to run 2"
    print("PASS\n")
    print(tracker.history_summary())


def test_deduplicate_syndicated_articles():
    print("=== Dedup: syndicated near-duplicates collapse to highest-trust copy ===")
    now = EVENT_TIME - dt.timedelta(hours=10)
    articles = [
        make_article("Fed holds rates steady, signals caution", "", hours_before_event=10, source_type="rss_cnbc_top_news"),
        make_article("Fed Holds Rates Steady, Signals Caution", "", hours_before_event=10, source_type="rss_investing_com_forex"),  # exact dup, lower trust
        make_article("Fed holds rates steady and signals caution ahead", "", hours_before_event=10, source_type="rss_reuters_business"),  # near-dup, highest trust
        make_article("Gold prices jump on soft jobs data", "", hours_before_event=10, source_type="rss_cnbc_economy"),  # genuinely distinct story
    ]
    deduped = deduplicate_articles(articles)
    print(f"  {len(articles)} in -> {len(deduped)} out: {[a.title for a in deduped]}")

    assert len(deduped) == 2, "3 syndicated Fed copies should collapse to 1, distinct gold story survives"
    fed_survivor = next(a for a in deduped if "Fed" in a.title)
    assert fed_survivor.source_type == "rss_reuters_business", "highest-trust copy should be kept, not first-seen"
    print("PASS\n")


def test_confidence_reflects_coverage_not_just_agreement():
    print("=== Confidence: a single signal-bearing article among silent ones should NOT read as high-confidence ===")
    event = EconomicEvent(title="NFP", country="USD", impact="High", event_time_utc=EVENT_TIME)
    bundle = EventNewsBundle(
        event=event,
        articles=[
            # Only this one carries any lexicon signal — 5 more with none.
            make_article("Dovish tone expected from Fed speakers", "", hours_before_event=45),
            make_article("Traders await Friday's jobs report", "", hours_before_event=30),
            make_article("Markets quiet ahead of key data", "", hours_before_event=20),
            make_article("Analysts split on payroll outlook", "", hours_before_event=10),
            make_article("Futures little changed overnight", "", hours_before_event=5),
            make_article("Currency desks brace for volatility", "", hours_before_event=1),
        ],
        as_of_utc=EVENT_TIME,
    )
    result = score_bundle(bundle, "XAUUSD")
    print(f"  {result.summary()}")

    assert result.confidence < 0.5, (
        f"1 signal article out of 6 should NOT report high confidence, got {result.confidence:.0%}"
    )
    print("PASS\n")


def test_precursor_leading_indicator():
    print("=== Precursor: ADP miss before NFP should score as a real structured signal ===")
    nfp = EconomicEvent(
        title="Non-Farm Employment Change", country="USD", impact="High",
        event_time_utc=EVENT_TIME,
    )
    # Real numbers from the 2026-08-07 NFP backtest case earlier this
    # session: ADP came in at 44K vs 75K forecast, a soft miss.
    adp = EconomicEvent(
        title="ADP Nonfarm Employment Change", country="USD", impact="Medium",
        event_time_utc=EVENT_TIME - dt.timedelta(hours=47, minutes=30),
        forecast="75K", actual="44K",
    )

    surprise = adp.usd_surprise_score()
    assert surprise is not None and surprise < 0, "a miss on a higher_bullish indicator should be USD-bearish"

    precursors = find_precursor_events(nfp, [nfp, adp])
    assert len(precursors) == 1 and precursors[0].title == adp.title, "ADP should be found as NFP's precursor"

    empty_bundle = EventNewsBundle(event=nfp, articles=[], as_of_utc=EVENT_TIME)
    result = score_bundle(empty_bundle, "XAUUSD", precursor_events=precursors)
    print(f"  {result.summary()}")

    assert result.direction == Direction.BULLISH, "USD-bearish ADP miss should map to bullish gold via inverse relationship"
    assert len(result.precursor_contributions) == 1
    print("PASS\n")


if __name__ == "__main__":
    test_sentiment_lexicon()
    test_scoring_consistent_bullish_usd()
    test_contradiction_detection()
    test_flip_tracking()
    test_deduplicate_syndicated_articles()
    test_confidence_reflects_coverage_not_just_agreement()
    test_precursor_leading_indicator()
    print("\nAll smoke tests passed.")
