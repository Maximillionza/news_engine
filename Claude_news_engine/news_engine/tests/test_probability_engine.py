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

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.cot_positioning import CotPositioningRead
from data_layer.event_context import EventNewsBundle
from data_layer.macro_backdrop import MacroBackdropRead
from data_layer.news_feed import NewsArticle
import scoring.probability_engine as probability_engine
from scoring.probability_engine import (
    score_bundle, Direction,
    _check_cot_crowding, _check_equity_risk_sentiment, _check_oil_shock,
)
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


@dataclass
class _FakeKalshiRead:
    """Duck-typed stand-in for data_layer.kalshi_feed.KalshiRead — probability_engine.py never imports data_layer.kalshi_feed directly, tests exercise the duck-typed contract."""
    strike: float
    implied_direction: str
    implied_probability: float
    open_interest: float


def test_kalshi_read_higher_on_bullish_indicator_is_bullish():
    print("=== score_bundle: a 'higher' Kalshi read on a higher_bullish indicator contributes USD-bullish ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    kalshi_read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.7, open_interest=100.0)
    with patch.dict(probability_engine.INSTRUMENTS, {"USDJPY": {"label": "USD/JPY", "usd_relationship": "direct"}}):
        result = score_bundle(bundle, "USDJPY", kalshi_read=kalshi_read)
    assert result.direction == Direction.BULLISH
    print("PASS\n")


def test_kalshi_read_higher_on_bearish_indicator_flips_sign():
    print("=== score_bundle: a 'higher' Kalshi read on a higher_bearish indicator contributes USD-bearish ===")
    event = _unemployment_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    kalshi_read = _FakeKalshiRead(strike=4.0, implied_direction="higher", implied_probability=0.7, open_interest=100.0)
    with patch.dict(probability_engine.INSTRUMENTS, {"USDJPY": {"label": "USD/JPY", "usd_relationship": "direct"}}):
        result = score_bundle(bundle, "USDJPY", kalshi_read=kalshi_read)
    assert result.direction == Direction.BEARISH
    print("PASS\n")


def test_kalshi_read_in_line_contributes_nothing():
    print("=== score_bundle: an in_line Kalshi read adds ZERO contributions, not a zero-weight one ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    kalshi_read = _FakeKalshiRead(strike=0.3, implied_direction="in_line", implied_probability=0.5, open_interest=100.0)
    result = score_bundle(bundle, "XAUUSD", kalshi_read=kalshi_read)
    assert result.probability == 0.5  # identical to the no-kalshi-read case — proves zero contribution
    print("PASS\n")


def test_kalshi_read_none_contributes_nothing():
    print("=== score_bundle: kalshi_read=None adds zero contributions ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD", kalshi_read=None)
    assert result.probability == 0.5
    print("PASS\n")


def test_kalshi_read_decays_with_age():
    print("=== score_bundle: an old Kalshi read contributes less than a fresh one ===")
    event = _cpi_event()
    kalshi_read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.7, open_interest=100.0)
    # Same comparably-weighted anchor-article approach the existing
    # test_print_call_decays_with_age test already uses — a single
    # contribution's weight cancels algebraically in _weighted_aggregate(),
    # so decay is only observable relative to a second, fixed contribution.
    from data_layer.news_feed import NewsArticle
    anchor_fresh = NewsArticle(
        title="Markets await Friday's data release", summary="Traders are watching closely.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/neutral-fresh",
    )
    anchor_stale = NewsArticle(
        title="Markets await Friday's data release", summary="Traders are watching closely.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME + dt.timedelta(hours=47),
        url="https://example.test/neutral-stale",
    )
    bundle_fresh = EventNewsBundle(event=event, articles=[anchor_fresh], as_of_utc=EVENT_TIME)
    bundle_stale = EventNewsBundle(event=event, articles=[anchor_stale], as_of_utc=EVENT_TIME + dt.timedelta(hours=48))
    fresh_result = score_bundle(bundle_fresh, "XAUUSD", kalshi_read=kalshi_read)
    stale_result = score_bundle(bundle_stale, "XAUUSD", kalshi_read=kalshi_read)
    assert abs(fresh_result.instrument_score) > abs(stale_result.instrument_score)
    print("PASS\n")


def test_kalshi_and_print_call_and_trend_signal_all_present_all_contribute():
    print("=== score_bundle: kalshi_read, print_call, and trend_signal can all be present at once, none excludes another ===")
    from config.settings import KALSHI_TRUST_WEIGHT, PRINT_CALL_TRUST_WEIGHT, TREND_STREAK_TRUST_WEIGHT

    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    kalshi_read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.7, open_interest=100.0)
    print_call = PrintCall(direction="higher", confidence=0.7, article_count=5)
    trend_signal = _FakeTrendSignal(direction="higher", strength=0.8)
    all_result = score_bundle(bundle, "XAUUSD", print_call=print_call, trend_signal=trend_signal, kalshi_read=kalshi_read)
    kalshi_only_result = score_bundle(bundle, "XAUUSD", kalshi_read=kalshi_read)

    # A >= comparison on confidence alone can't fail even if the Kalshi
    # contribution were silently dropped — with all three signals agreeing,
    # confidence saturates at 1.0 (agreement x coverage) whether one
    # contribution is present or three are, so that alone proves nothing.
    # Instead, pin the exact weighted-average USD sentiment that can ONLY
    # come out right if all three contributions (each with their own
    # trust_weight and usd_sentiment) are genuinely blended in — as_of ==
    # event_time_utc for every contribution here, so every time_weight is
    # 1.0 and the combined_weight reduces to the trust_weight alone. This
    # fails if any of the three were dropped, mis-weighted, or mis-signed.
    expected_aggregate_usd = (
        KALSHI_TRUST_WEIGHT * 0.7        # kalshi_read: implied_probability=0.7, 'higher' -> +0.7
        + PRINT_CALL_TRUST_WEIGHT * 0.7  # print_call: confidence=0.7, 'higher' -> +0.7
        + TREND_STREAK_TRUST_WEIGHT * 0.8  # trend_signal: strength=0.8, 'higher' -> +0.8
    ) / (KALSHI_TRUST_WEIGHT + PRINT_CALL_TRUST_WEIGHT + TREND_STREAK_TRUST_WEIGHT)
    assert abs(all_result.aggregate_usd_sentiment - expected_aggregate_usd) < 1e-9
    # And it must differ from the kalshi-only read (0.7 exactly) — proves
    # the other two signals are actually moving the blended output, not
    # just present-but-inert.
    assert all_result.aggregate_usd_sentiment != kalshi_only_result.aggregate_usd_sentiment
    assert all_result.confidence >= kalshi_only_result.confidence
    print("PASS\n")


def test_kalshi_trust_weight_above_precursor_trust_weight():
    print("=== sanity: KALSHI_TRUST_WEIGHT is above PRECURSOR_TRUST_WEIGHT, per the spec's trust tiering ===")
    from config.settings import KALSHI_TRUST_WEIGHT, PRECURSOR_TRUST_WEIGHT
    assert KALSHI_TRUST_WEIGHT > PRECURSOR_TRUST_WEIGHT
    print("PASS\n")


def test_thin_sample_caps_extreme_probability():
    print("=== R3: score_bundle: a thin (2-article) strongly-agreeing sample has probability capped, not near-certain ===")
    from data_layer.news_feed import NewsArticle
    from config.settings import THIN_SAMPLE_PROBABILITY_CAP
    event = _cpi_event()  # "CPI m/m", higher_bullish
    # Two strongly bullish-USD articles, reproducing BACKTEST_REPORT.md's
    # documented failure shape: a thin (2-3 article) sample that agrees
    # unanimously used to reach 98%+/1%- probability with 100% confidence.
    articles = [
        NewsArticle(
            title="Fed seen hawkish, rate hike bets surge", summary="Dollar strength widely expected.",
            source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
            url="https://example.test/thin-1",
        ),
        NewsArticle(
            title="Hawkish tilt firms as data looms", summary="Traders raising rate hike bets.",
            source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
            url="https://example.test/thin-2",
        ),
    ]
    bundle = EventNewsBundle(event=event, articles=articles, as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD")  # inverse mapping — bullish USD -> bearish gold
    assert result.thin_sample is True
    lower_bound = 1.0 - THIN_SAMPLE_PROBABILITY_CAP
    assert lower_bound <= result.probability <= THIN_SAMPLE_PROBABILITY_CAP, (
        f"expected probability capped within [{lower_bound}, {THIN_SAMPLE_PROBABILITY_CAP}], got {result.probability}"
    )
    print("PASS\n")


def test_sufficient_signal_count_is_not_capped():
    print("=== R3: score_bundle: 3+ signal-bearing contributions are NOT capped by the thin-sample ceiling ===")
    from data_layer.news_feed import NewsArticle
    from config.settings import THIN_SAMPLE_PROBABILITY_CAP
    event = _cpi_event()
    articles = [
        NewsArticle(
            title="Fed seen hawkish, rate hike bets surge", summary="Dollar strength widely expected.",
            source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
            url="https://example.test/sufficient-1",
        ),
        NewsArticle(
            title="Hawkish tilt firms as data looms", summary="Traders raising rate hike bets.",
            source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
            url="https://example.test/sufficient-2",
        ),
    ]
    bundle = EventNewsBundle(event=event, articles=articles, as_of_utc=EVENT_TIME)
    # A third, strongly agreeing structured signal (Kalshi) pushes the
    # signal-bearing count to 3, clearing THIN_SAMPLE_SIGNAL_THRESHOLD.
    kalshi_read = _FakeKalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.95, open_interest=100.0)
    result = score_bundle(bundle, "XAUUSD", kalshi_read=kalshi_read)
    assert result.thin_sample is False
    assert result.probability < (1.0 - THIN_SAMPLE_PROBABILITY_CAP), (
        f"expected an uncapped, near-extreme probability, got {result.probability}"
    )
    print("PASS\n")


@dataclass
class _FakeMacroBackdrop:
    """Duck-typed stand-in for data_layer.macro_backdrop.MacroBackdropRead — probability_engine.py never imports that module, tests exercise the duck-typed .lean contract directly."""
    lean: int | None
    equity_index_trend_pct: float | None = None
    oil_daily_change_pct: float | None = None


def test_macro_backdrop_agrees_when_lean_matches_aggregate_sign():
    print("=== R5: score_bundle: macro_backdrop_agrees=True and confidence UNCHANGED when the backdrop's lean matches the read ===")
    from data_layer.news_feed import NewsArticle
    event = _cpi_event()  # higher_bullish
    bullish_article = NewsArticle(
        title="Hawkish tilt firms, rate hike bets rise", summary="Dollar strength widely expected.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/macro-agree",
    )
    bundle = EventNewsBundle(event=event, articles=[bullish_article], as_of_utc=EVENT_TIME)
    no_macro_result = score_bundle(bundle, "XAUUSD")
    macro_backdrop = _FakeMacroBackdrop(lean=1)  # backdrop leans USD-bullish, matching the article's own bullish-USD read
    with_macro_result = score_bundle(bundle, "XAUUSD", macro_backdrop=macro_backdrop)
    assert with_macro_result.macro_backdrop_agrees is True
    assert with_macro_result.macro_backdrop_note is None
    assert abs(with_macro_result.confidence - no_macro_result.confidence) < 1e-9  # unchanged
    print("PASS\n")


def test_macro_backdrop_disagreement_discounts_confidence_not_probability_or_direction():
    print("=== R5: score_bundle: a disagreeing macro backdrop discounts CONFIDENCE only — probability and direction untouched ===")
    from data_layer.news_feed import NewsArticle
    from config.settings import MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER
    event = _cpi_event()
    bullish_article = NewsArticle(
        title="Hawkish tilt firms, rate hike bets rise", summary="Dollar strength widely expected.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/macro-disagree",
    )
    bundle = EventNewsBundle(event=event, articles=[bullish_article], as_of_utc=EVENT_TIME)
    no_macro_result = score_bundle(bundle, "XAUUSD")
    macro_backdrop = _FakeMacroBackdrop(lean=-1)  # backdrop leans USD-bearish — opposite the article's bullish-USD read
    with_macro_result = score_bundle(bundle, "XAUUSD", macro_backdrop=macro_backdrop)
    assert with_macro_result.macro_backdrop_agrees is False
    assert with_macro_result.macro_backdrop_note is not None
    assert abs(with_macro_result.confidence - no_macro_result.confidence * MACRO_BACKDROP_DISAGREEMENT_CONFIDENCE_MULTIPLIER) < 1e-9
    # Never flips direction or probability — same discipline as agreement/coverage and the thin-sample cap.
    assert with_macro_result.direction == no_macro_result.direction
    assert with_macro_result.probability == no_macro_result.probability
    print("PASS\n")


def test_macro_backdrop_none_contributes_nothing():
    print("=== R5: score_bundle: macro_backdrop=None leaves macro_backdrop_agrees=None and confidence unchanged ===")
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD", macro_backdrop=None)
    assert result.macro_backdrop_agrees is None
    assert result.macro_backdrop_note is None
    print("PASS\n")


def test_macro_backdrop_no_lean_is_treated_as_no_data_not_disagreement():
    print("=== R5: score_bundle: a macro backdrop with NO clear lean (.lean=None) doesn't discount confidence ===")
    from data_layer.news_feed import NewsArticle
    event = _cpi_event()
    bullish_article = NewsArticle(
        title="Hawkish tilt firms, rate hike bets rise", summary="Dollar strength widely expected.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/macro-flat",
    )
    bundle = EventNewsBundle(event=event, articles=[bullish_article], as_of_utc=EVENT_TIME)
    no_macro_result = score_bundle(bundle, "XAUUSD")
    flat_backdrop = _FakeMacroBackdrop(lean=None)
    with_macro_result = score_bundle(bundle, "XAUUSD", macro_backdrop=flat_backdrop)
    assert with_macro_result.macro_backdrop_agrees is None
    assert abs(with_macro_result.confidence - no_macro_result.confidence) < 1e-9
    print("PASS\n")


# --- _check_cot_crowding ---

def test_check_cot_crowding_no_data_returns_none_none():
    print("=== _check_cot_crowding: no COT data at all returns (None, None) ===")
    assert _check_cot_crowding(aggregate_usd=0.5, cot_positioning=None) == (None, None)
    print("PASS\n")


def test_check_cot_crowding_not_extreme_returns_none_none():
    print("=== _check_cot_crowding: positioning within the normal range returns (None, None) regardless of the read's direction ===")
    cot = CotPositioningRead(net_leveraged_funds_position=100, percentile_in_trailing_window=50.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    assert _check_cot_crowding(aggregate_usd=0.5, cot_positioning=cot) == (None, None)
    print("PASS\n")


def test_check_cot_crowding_extreme_and_aligned_dampens():
    print("=== _check_cot_crowding: extreme long positioning aligned with a USD-bullish read triggers the dampener ===")
    cot = CotPositioningRead(net_leveraged_funds_position=50000, percentile_in_trailing_window=98.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    crowded, note = _check_cot_crowding(aggregate_usd=0.5, cot_positioning=cot)  # positive = USD-bullish, matches is_crowded=+1
    assert crowded is True
    assert note is not None
    print("PASS\n")


def test_check_cot_crowding_extreme_but_opposite_direction_no_effect():
    print("=== _check_cot_crowding: extreme long positioning does NOT dampen a USD-BEARISH read (crowding must match direction) ===")
    cot = CotPositioningRead(net_leveraged_funds_position=50000, percentile_in_trailing_window=98.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    crowded, note = _check_cot_crowding(aggregate_usd=-0.5, cot_positioning=cot)  # negative = USD-bearish, opposite of is_crowded=+1
    assert crowded is None  # not (False, ...) — this check has no disagreement case, only "crowded+aligned" or "no concern"
    assert note is None
    print("PASS\n")


# --- _check_equity_risk_sentiment ---

def test_check_equity_risk_sentiment_only_applies_to_risk_sentiment_instruments():
    print("=== _check_equity_risk_sentiment: returns (None, None) for XAUUSD regardless of equity data (not risk_sentiment-mapped) ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=5.0, equity_index_latest_date=dt.date(2026, 8, 29),  # strongly risk-on
        oil_daily_change_pct=None, lookback_days=10,
    )
    assert _check_equity_risk_sentiment(instrument_score=-0.5, instrument="XAUUSD", macro_backdrop=macro) == (None, None)
    print("PASS\n")


def test_check_equity_risk_sentiment_agrees_for_us30():
    print("=== _check_equity_risk_sentiment: US30 with equities trending up and a bullish instrument_score agrees ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=5.0, equity_index_latest_date=dt.date(2026, 8, 29),
        oil_daily_change_pct=None, lookback_days=10,
    )
    agrees, note = _check_equity_risk_sentiment(instrument_score=0.3, instrument="US30", macro_backdrop=macro)
    assert agrees is True
    assert note is None
    print("PASS\n")


def test_check_equity_risk_sentiment_disagrees_for_us30():
    print("=== _check_equity_risk_sentiment: US30 with equities trending DOWN (risk-off) but a bullish instrument_score disagrees ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=-5.0, equity_index_latest_date=dt.date(2026, 8, 29),
        oil_daily_change_pct=None, lookback_days=10,
    )
    agrees, note = _check_equity_risk_sentiment(instrument_score=0.3, instrument="US30", macro_backdrop=macro)
    assert agrees is False
    assert note is not None
    print("PASS\n")


def test_check_equity_risk_sentiment_below_threshold_no_effect():
    print("=== _check_equity_risk_sentiment: a tiny equity move below EQUITY_INDEX_LEAN_THRESHOLD_PCT has no effect ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=0.1, equity_index_latest_date=dt.date(2026, 8, 29),  # well below 1.0% threshold
        oil_daily_change_pct=None, lookback_days=10,
    )
    assert _check_equity_risk_sentiment(instrument_score=0.3, instrument="US30", macro_backdrop=macro) == (None, None)
    print("PASS\n")


# --- _check_oil_shock ---

def test_check_oil_shock_no_data_returns_false_none():
    print("=== _check_oil_shock: no macro backdrop data at all returns (False, None) ===")
    assert _check_oil_shock(macro_backdrop=None) == (False, None)
    print("PASS\n")


def test_check_oil_shock_below_threshold_no_effect():
    print("=== _check_oil_shock: a routine day-over-day oil move below OIL_SHOCK_DAILY_THRESHOLD_PCT has no effect ===")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=None, equity_index_latest_date=None,
        oil_daily_change_pct=1.5, lookback_days=10,  # well below 4.0% threshold
    )
    assert _check_oil_shock(macro_backdrop=macro) == (False, None)
    print("PASS\n")


def test_check_oil_shock_above_threshold_triggers_regardless_of_direction():
    print("=== _check_oil_shock: a sharp single-day oil move (either direction) triggers the flag ===")
    for daily_change in (6.0, -6.0):
        macro = MacroBackdropRead(
            dollar_index_trend_pct=None, dollar_index_latest_date=None,
            real_yield_trend_bps=None, real_yield_latest_date=None,
            oil_trend_pct=None, oil_latest_date=None,
            equity_index_trend_pct=None, equity_index_latest_date=None,
            oil_daily_change_pct=daily_change, lookback_days=10,
        )
        shocked, note = _check_oil_shock(macro_backdrop=macro)
        assert shocked is True
        assert note is not None
    print("PASS\n")


# --- score_bundle() integration: the core invariant — none of the three ever touch direction/probability ---

def test_score_bundle_new_signals_default_to_no_effect_when_omitted():
    print("=== score_bundle: omitting cot_positioning entirely reproduces today's exact behavior (backward compatible) ===")
    event = _cpi_event()
    article = NewsArticle(
        title="Sticky inflation could push CPI higher", summary="Analysts see upside risk to the print.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/new-signals-default",
    )
    bundle = EventNewsBundle(event=event, articles=[article], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD")  # no cot_positioning, no macro_backdrop — exactly like every existing call site
    assert result.cot_crowding_flag is None
    assert result.equity_risk_agrees is None
    assert result.oil_shock_flag is False
    print("PASS\n")


def test_score_bundle_cot_crowding_only_touches_confidence():
    print("=== score_bundle: a crowded, aligned COT read discounts confidence but never changes direction or probability ===")
    event = _cpi_event()
    # "Hawkish tilt firms, rate hike bets rise" reliably scores USD-bullish
    # (positive aggregate_usd) — same article used by the macro-backdrop
    # agreement tests above, needed here so it aligns with is_crowded=+1.
    article = NewsArticle(
        title="Hawkish tilt firms, rate hike bets rise", summary="Dollar strength widely expected.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/cot-crowding-only-confidence",
    )
    bundle = EventNewsBundle(event=event, articles=[article], as_of_utc=EVENT_TIME)
    baseline = score_bundle(bundle, "XAUUSD")
    cot = CotPositioningRead(net_leveraged_funds_position=50000, percentile_in_trailing_window=98.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    with_cot = score_bundle(bundle, "XAUUSD", cot_positioning=cot)

    assert with_cot.direction == baseline.direction
    assert with_cot.probability == pytest.approx(baseline.probability)
    assert with_cot.confidence < baseline.confidence  # crowding only ever DAMPENS
    assert with_cot.cot_crowding_flag is True
    print("PASS\n")


def test_score_bundle_oil_shock_only_touches_confidence():
    print("=== score_bundle: an oil shock discounts confidence but never changes direction or probability ===")
    event = _cpi_event()
    # Same proven-non-zero-confidence article as the COT crowding test above
    # (not the brief's literal "Sticky inflation could push CPI higher" —
    # under the full test suite, tests/test_scoring_smoke.py leaks a
    # module-level ENABLE_FINBERT_SENTIMENT=False mutation with no teardown,
    # forcing lexicon-only scoring for the rest of the session; that literal
    # article scores confidence exactly 0.0 under lexicon-only mode, which
    # makes "with_shock.confidence < baseline.confidence" false (0.0 < 0.0).
    # This article scores non-zero confidence under both FinBERT and
    # lexicon-only paths, so the test is robust to that leak either way).
    article = NewsArticle(
        title="Hawkish tilt firms, rate hike bets rise", summary="Dollar strength widely expected.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/oil-shock-only-confidence",
    )
    bundle = EventNewsBundle(event=event, articles=[article], as_of_utc=EVENT_TIME)
    baseline = score_bundle(bundle, "XAUUSD")
    macro = MacroBackdropRead(
        dollar_index_trend_pct=None, dollar_index_latest_date=None,
        real_yield_trend_bps=None, real_yield_latest_date=None,
        oil_trend_pct=None, oil_latest_date=None,
        equity_index_trend_pct=None, equity_index_latest_date=None,
        oil_daily_change_pct=7.0, lookback_days=10,
    )
    with_shock = score_bundle(bundle, "XAUUSD", macro_backdrop=macro)

    assert with_shock.direction == baseline.direction
    assert with_shock.probability == pytest.approx(baseline.probability)
    assert with_shock.confidence < baseline.confidence
    assert with_shock.oil_shock_flag is True
    print("PASS\n")


def test_redundancy_discount_applies_to_near_duplicate_articles():
    print("=== Correlation/redundancy: two near-duplicate articles close in time — the later one is discounted, not double-counted ===")
    from data_layer.news_feed import NewsArticle
    from config.settings import REDUNDANCY_DISCOUNT_MULTIPLIER
    event = _cpi_event()
    earlier = NewsArticle(
        title="Fed seen hawkish as rate hike bets surge", summary="Dollar strength widely expected across markets today.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1, minutes=10),
        url="https://example.test/redundant-earlier",
    )
    later_duplicate = NewsArticle(
        title="Fed hawkish, rate hike bets surge", summary="Dollar strength expected across markets today.",
        source="Test Wire 2", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/redundant-later",
    )
    bundle = EventNewsBundle(event=event, articles=[earlier, later_duplicate], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD")
    assert result.redundant_contributions_discounted == 1

    # Cross-check: the SAME two articles, scored alone (no redundancy
    # partner), should each carry their full, undiscounted weight — proves
    # the discount is real, not an artifact of some other difference.
    solo_bundle = EventNewsBundle(event=event, articles=[later_duplicate], as_of_utc=EVENT_TIME)
    solo_result = score_bundle(bundle=solo_bundle, instrument="XAUUSD")
    assert solo_result.redundant_contributions_discounted == 0
    print("PASS\n")


def test_redundancy_discount_does_not_apply_to_distinct_articles():
    print("=== Correlation/redundancy: two genuinely distinct articles are NOT discounted, even if close in time ===")
    from data_layer.news_feed import NewsArticle
    event = _cpi_event()
    fed_article = NewsArticle(
        title="Fed hawkish, rate hike bets surge", summary="Dollar strength expected across markets today.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/distinct-1",
    )
    unrelated_article = NewsArticle(
        title="Gold miners report record quarterly earnings", summary="Production costs fell as output rose in the quarter.",
        source="Test Wire 2", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1, minutes=5),
        url="https://example.test/distinct-2",
    )
    bundle = EventNewsBundle(event=event, articles=[fed_article, unrelated_article], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD")
    assert result.redundant_contributions_discounted == 0
    print("PASS\n")


def test_redundancy_discount_does_not_apply_when_far_apart_in_time():
    print("=== Correlation/redundancy: near-identical text is NOT discounted when published far apart in time ===")
    from data_layer.news_feed import NewsArticle
    event = _cpi_event()
    earlier = NewsArticle(
        title="Fed hawkish, rate hike bets surge", summary="Dollar strength expected across markets today.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=40),
        url="https://example.test/time-far-1",
    )
    later = NewsArticle(
        title="Fed seen hawkish as rate hike bets surge", summary="Dollar strength widely expected across markets today.",
        source="Test Wire 2", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/time-far-2",
    )
    bundle = EventNewsBundle(event=event, articles=[earlier, later], as_of_utc=EVENT_TIME)
    result = score_bundle(bundle, "XAUUSD")
    assert result.redundant_contributions_discounted == 0
    print("PASS\n")


def test_redundancy_discount_works_across_sentiment_tiers_not_just_lexicon():
    print("=== Correlation/redundancy: detection compares article TEXT, so it still fires when FinBERT (not the lexicon) scored the articles ===")
    from data_layer.news_feed import NewsArticle
    event = _cpi_event()
    earlier = NewsArticle(
        title="Fed seen hawkish as rate hike bets surge", summary="Dollar strength widely expected across markets today.",
        source="Test Wire", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1, minutes=10),
        url="https://example.test/finbert-tier-1",
    )
    later_duplicate = NewsArticle(
        title="Fed hawkish, rate hike bets surge", summary="Dollar strength expected across markets today.",
        source="Test Wire 2", source_type="test", published_utc=EVENT_TIME - dt.timedelta(hours=1),
        url="https://example.test/finbert-tier-2",
    )
    bundle = EventNewsBundle(event=event, articles=[earlier, later_duplicate], as_of_utc=EVENT_TIME)
    # ENABLE_FINBERT_SENTIMENT defaults on (R2) and this environment has
    # torch/transformers installed — score_bundle() is called with no
    # override, exercising the REAL default tiering, not a forced-lexicon
    # path, unlike test_scoring_smoke.py's deliberate no-network contract.
    result = score_bundle(bundle, "XAUUSD")
    assert result.contributions[0].matched_terms[0].startswith("<"), (
        "expected the FinBERT tier to have actually scored these — if this fails, "
        "the test environment lost its torch/transformers install and this test can't prove what it claims"
    )
    assert result.redundant_contributions_discounted == 1
    print("PASS\n")


def _bundle_with_print_call_score(confidence):
    """
    A single print_call contribution, no articles — the only voter, so
    instrument_score is fully controllable via `confidence` with no
    FinBERT/lexicon variability. CPI m/m is 'higher_bullish' and
    direction='higher' gives usd_sentiment=+confidence; XAUUSD is
    'inverse', so instrument_score = -confidence. See
    _build_print_call_contribution()'s math.
    """
    event = _cpi_event()
    bundle = EventNewsBundle(event=event, articles=[], as_of_utc=EVENT_TIME)
    print_call = PrintCall(direction="higher", confidence=confidence, article_count=5)
    return bundle, print_call


def test_direction_hysteresis_not_applied_without_a_current_direction():
    print("=== score_bundle: no current_direction given (first-ever score) -> plain threshold, no hysteresis ===")
    bundle, print_call = _bundle_with_print_call_score(0.03)  # instrument_score -0.03, clears the PLAIN 0.02 band
    result = score_bundle(bundle, "XAUUSD", print_call=print_call, current_direction=None)
    assert result.direction == Direction.BEARISH
    print("PASS\n")


def test_direction_hysteresis_suppresses_a_flip_that_does_not_clear_the_wider_band():
    print("=== score_bundle: a move that clears the PLAIN band but not the WIDER hysteresis band does not flip away from current_direction ===")
    # Real bug this fixes (2026-08-26 live investigation): 21 recorded
    # direction flips within 72h for one event/instrument, oscillating in
    # a narrow band purely from continuous time-decay recomputation, no
    # new evidence required each time.
    bundle, print_call = _bundle_with_print_call_score(0.03)  # instrument_score -0.03: plain=BEARISH, but doesn't clear the wider band
    result = score_bundle(bundle, "XAUUSD", print_call=print_call, current_direction="bullish")
    assert result.direction == Direction.BULLISH, "should stay at the current direction — the move is real but not wide enough to flip"
    print("PASS\n")


def test_direction_hysteresis_allows_a_flip_that_clears_the_wider_band():
    print("=== score_bundle: a move that clears the WIDER hysteresis band DOES flip, even away from current_direction ===")
    bundle, print_call = _bundle_with_print_call_score(0.06)  # instrument_score -0.06: clears the wider 0.05 band
    result = score_bundle(bundle, "XAUUSD", print_call=print_call, current_direction="bullish")
    assert result.direction == Direction.BEARISH
    print("PASS\n")


def test_direction_hysteresis_no_effect_when_new_plain_direction_already_matches_current():
    print("=== score_bundle: hysteresis is a no-op when the plain direction already matches current_direction ===")
    bundle, print_call = _bundle_with_print_call_score(0.03)  # instrument_score -0.03: plain=BEARISH
    result = score_bundle(bundle, "XAUUSD", print_call=print_call, current_direction="bearish")
    assert result.direction == Direction.BEARISH
    print("PASS\n")


def test_direction_hysteresis_keeps_neutral_when_move_out_of_neutral_is_too_small():
    print("=== score_bundle: hysteresis applies leaving NEUTRAL too, not just leaving bullish/bearish ===")
    bundle, print_call = _bundle_with_print_call_score(0.03)  # plain=BEARISH (clears 0.02), but not the wider 0.05 band
    result = score_bundle(bundle, "XAUUSD", print_call=print_call, current_direction="neutral")
    assert result.direction == Direction.NEUTRAL, "should stay neutral — the move isn't wide enough to leave it"
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
    test_kalshi_read_higher_on_bullish_indicator_is_bullish()
    test_kalshi_read_higher_on_bearish_indicator_flips_sign()
    test_kalshi_read_in_line_contributes_nothing()
    test_kalshi_read_none_contributes_nothing()
    test_kalshi_read_decays_with_age()
    test_kalshi_and_print_call_and_trend_signal_all_present_all_contribute()
    test_kalshi_trust_weight_above_precursor_trust_weight()
    test_thin_sample_caps_extreme_probability()
    test_sufficient_signal_count_is_not_capped()
    test_macro_backdrop_agrees_when_lean_matches_aggregate_sign()
    test_macro_backdrop_disagreement_discounts_confidence_not_probability_or_direction()
    test_macro_backdrop_none_contributes_nothing()
    test_macro_backdrop_no_lean_is_treated_as_no_data_not_disagreement()
    test_check_cot_crowding_no_data_returns_none_none()
    test_check_cot_crowding_not_extreme_returns_none_none()
    test_check_cot_crowding_extreme_and_aligned_dampens()
    test_check_cot_crowding_extreme_but_opposite_direction_no_effect()
    test_check_equity_risk_sentiment_only_applies_to_risk_sentiment_instruments()
    test_check_equity_risk_sentiment_agrees_for_us30()
    test_check_equity_risk_sentiment_disagrees_for_us30()
    test_check_equity_risk_sentiment_below_threshold_no_effect()
    test_check_oil_shock_no_data_returns_false_none()
    test_check_oil_shock_below_threshold_no_effect()
    test_check_oil_shock_above_threshold_triggers_regardless_of_direction()
    test_score_bundle_new_signals_default_to_no_effect_when_omitted()
    test_score_bundle_cot_crowding_only_touches_confidence()
    test_score_bundle_oil_shock_only_touches_confidence()
    test_redundancy_discount_applies_to_near_duplicate_articles()
    test_redundancy_discount_does_not_apply_to_distinct_articles()
    test_redundancy_discount_does_not_apply_when_far_apart_in_time()
    test_redundancy_discount_works_across_sentiment_tiers_not_just_lexicon()
    test_direction_hysteresis_not_applied_without_a_current_direction()
    test_direction_hysteresis_suppresses_a_flip_that_does_not_clear_the_wider_band()
    test_direction_hysteresis_allows_a_flip_that_clears_the_wider_band()
    test_direction_hysteresis_no_effect_when_new_plain_direction_already_matches_current()
    test_direction_hysteresis_keeps_neutral_when_move_out_of_neutral_is_too_small()
    print("All probability_engine tests passed.")
