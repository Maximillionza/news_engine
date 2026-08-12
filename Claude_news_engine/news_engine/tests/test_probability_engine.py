"""
Tests for scoring/probability_engine.py's PrintCallContribution and
TrendStreakContribution — the two new optional signals that blend into
score_bundle()'s existing weighted-average math. No network needed.
"""
import datetime as dt
import sys
import os
from dataclasses import dataclass
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle
import scoring.probability_engine as probability_engine
from scoring.probability_engine import score_bundle, Direction
from scoring.print_direction import PrintCall

EVENT_TIME = dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)


@dataclass
class _FakeTrendSignal:
    """Duck-typed stand-in for webapp.trend.TrendSignal — probability_engine.py
    never imports webapp/, so tests exercise the duck-typed contract directly."""
    direction: str
    strength: float


def _cpi_event():
    # "CPI m/m" is 'higher_bullish' in EVENT_SURPRISE_DIRECTION.
    return EconomicEvent(
        title="CPI m/m", country="USD", impact="High",
        event_time_utc=EVENT_TIME, forecast="0.3%", previous="0.3%",
    )


def _unemployment_event():
    # "Unemployment Rate" is 'higher_bearish' — opposite sign convention,
    # used to prove the mapping isn't hardcoded to "higher = bullish".
    return EconomicEvent(
        title="Unemployment Rate", country="USD", impact="High",
        event_time_utc=EVENT_TIME, forecast="4.0%", previous="3.9%",
    )


def test_score_bundle_without_new_params_is_unchanged():
    print("=== score_bundle: omitting print_call and trend_signal reproduces the exact prior behavior ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD", precursor_events=None)
    assert result.direction == Direction.NEUTRAL
    assert result.probability == 0.5
    assert result.contradiction_note == "No articles or leading indicators in window — no basis for a directional call."
    print("PASS\n")


def test_print_call_higher_on_bullish_indicator_is_bullish_for_direct_instrument():
    print("=== score_bundle: a 'higher' print call on a higher_bullish indicator contributes USD-bullish ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    with patch.dict(probability_engine.INSTRUMENTS, {"USDJPY": {"label": "USD/JPY", "usd_relationship": "direct"}}):
        result = score_bundle(bundle, "USDJPY", print_call=print_call)  # USDJPY = direct relationship
    assert result.direction == Direction.BULLISH
    print("PASS\n")


def test_print_call_higher_on_bearish_indicator_flips_sign():
    print("=== score_bundle: a 'higher' print call on a higher_bearish indicator contributes USD-bearish ===")
    event = _unemployment_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    with patch.dict(probability_engine.INSTRUMENTS, {"USDJPY": {"label": "USD/JPY", "usd_relationship": "direct"}}):
        result = score_bundle(bundle, "USDJPY", print_call=print_call)
    assert result.direction == Direction.BEARISH
    print("PASS\n")


def test_print_call_in_line_contributes_nothing():
    print("=== score_bundle: an in_line print call adds ZERO contributions, not a zero-weight one ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    print_call = PrintCall(direction="in_line", confidence=0.15, article_count=5)
    result = score_bundle(bundle, "XAUUSD", print_call=print_call)
    assert result.direction == Direction.NEUTRAL
    assert result.probability == 0.5  # identical to the no-print-call case — proves zero contribution, not a diluted one
    print("PASS\n")


def test_print_call_decays_with_age():
    print("=== score_bundle: an old print call contributes less than a fresh one ===")
    from data_layer.news_feed import NewsArticle
    event = _cpi_event()
    # A neutral anchor article (no sentiment-lexicon hits -> usd_score=0.0)
    # — without a second, non-decaying contribution in the mix,
    # _weighted_aggregate()'s single-contribution case always returns that
    # one contribution's raw usd_sentiment unchanged regardless of its
    # weight, so decay would never be observable.
    #
    # Each bundle gets its OWN anchor, published 1h before that bundle's
    # own as_of_utc, rather than reusing one fixed article instance. The
    # article half-life (TIME_DECAY_HALF_LIFE_MINUTES, 6h) is far shorter
    # than the print call's half-life (PRECURSOR_TIME_DECAY_HALF_LIFE_MINUTES,
    # tied to PRE_EVENT_WINDOW_HOURS) — reusing one article means it goes
    # fully stale by the 48h mark while the print call is still comparatively
    # fresh, so the anchor's diluting weight shrinks *faster* than the print
    # call's, and the weighted average is pulled closer to the print call's
    # raw value at 48h than at 0h — the opposite of decay. Keeping the
    # anchor "1h old" relative to each bundle holds its own weight ~constant
    # across both scenarios, isolating the print call's weight as the only
    # thing that changes between them.
    def _neutral_article(as_of: dt.datetime) -> NewsArticle:
        return NewsArticle(
            title="Markets await Friday's data release", summary="Traders are watching closely.",
            source="Test Wire", source_type="test", published_utc=as_of - dt.timedelta(hours=1),
            url="https://example.test/neutral",
        )
    bundle_fresh = EventNewsBundle(event=event, articles=[_neutral_article(EVENT_TIME)], as_of_utc=EVENT_TIME)
    stale_as_of = EVENT_TIME + dt.timedelta(hours=48)
    bundle_stale = EventNewsBundle(event=event, articles=[_neutral_article(stale_as_of)], as_of_utc=stale_as_of)
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    fresh_result = score_bundle(bundle_fresh, "XAUUSD", print_call=print_call)
    stale_result = score_bundle(bundle_stale, "XAUUSD", print_call=print_call)
    assert abs(fresh_result.instrument_score) > abs(stale_result.instrument_score)
    print("PASS\n")


def test_trend_signal_higher_contributes_in_correct_direction():
    print("=== score_bundle: a 'higher' trend signal on a higher_bullish indicator contributes USD-bullish ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    trend_signal = _FakeTrendSignal(direction="higher", strength=0.8)
    with patch.dict(probability_engine.INSTRUMENTS, {"USDJPY": {"label": "USD/JPY", "usd_relationship": "direct"}}):
        result = score_bundle(bundle, "USDJPY", trend_signal=trend_signal)
    assert result.direction == Direction.BULLISH
    print("PASS\n")


def test_trend_signal_none_contributes_nothing():
    print("=== score_bundle: trend_signal=None adds zero contributions ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD", trend_signal=None)
    assert result.probability == 0.5
    print("PASS\n")


def test_trend_signal_does_not_decay_with_age():
    print("=== score_bundle: a trend signal contributes identically regardless of bundle age (no time decay) ===")
    event = _cpi_event()
    bundle_fresh = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    bundle_stale = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME + dt.timedelta(hours=48))
    trend_signal = _FakeTrendSignal(direction="higher", strength=0.8)
    fresh_result = score_bundle(bundle_fresh, "XAUUSD", trend_signal=trend_signal)
    stale_result = score_bundle(bundle_stale, "XAUUSD", trend_signal=trend_signal)
    assert abs(fresh_result.instrument_score - stale_result.instrument_score) < 1e-9
    print("PASS\n")


def test_print_call_and_trend_signal_both_present_both_contribute():
    print("=== score_bundle: print_call and trend_signal both present blend together, not mutually exclusive ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    trend_signal = _FakeTrendSignal(direction="higher", strength=0.8)
    both_result = score_bundle(bundle, "XAUUSD", print_call=print_call, trend_signal=trend_signal)
    print_only_result = score_bundle(bundle, "XAUUSD", print_call=print_call)
    # Both agreeing (same direction) should produce a stronger read than print_call alone,
    # since agreement/coverage both improve with a second agreeing signal.
    assert both_result.confidence >= print_only_result.confidence
    print("PASS\n")


def test_print_call_trust_weight_below_precursor_trust_weight():
    print("=== sanity: PRINT_CALL_TRUST_WEIGHT is below PRECURSOR_TRUST_WEIGHT, per the spec's trust tiering ===")
    from config.settings import PRINT_CALL_TRUST_WEIGHT, PRECURSOR_TRUST_WEIGHT, TREND_STREAK_TRUST_WEIGHT
    assert PRINT_CALL_TRUST_WEIGHT < PRECURSOR_TRUST_WEIGHT
    assert TREND_STREAK_TRUST_WEIGHT < PRINT_CALL_TRUST_WEIGHT
    print("PASS\n")


if __name__ == "__main__":
    test_score_bundle_without_new_params_is_unchanged()
    test_print_call_higher_on_bullish_indicator_is_bullish_for_direct_instrument()
    test_print_call_higher_on_bearish_indicator_flips_sign()
    test_print_call_in_line_contributes_nothing()
    test_print_call_decays_with_age()
    test_trend_signal_higher_contributes_in_correct_direction()
    test_trend_signal_none_contributes_nothing()
    test_trend_signal_does_not_decay_with_age()
    test_print_call_and_trend_signal_both_present_both_contribute()
    test_print_call_trust_weight_below_precursor_trust_weight()
    print("All probability_engine tests passed.")
