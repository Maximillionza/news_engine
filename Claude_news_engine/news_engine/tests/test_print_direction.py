"""
Tests for scoring/print_direction.py — the print-surprise lexicon
classifier ("will this release come in higher/lower than forecast,"
distinct from scoring/sentiment.py's general USD-directional lexicon).
"""
import sys
import os
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle
from data_layer.news_feed import NewsArticle
from scoring.print_direction import score_print_direction, PrintCall


def _article(title, summary="", published_hours_ago=2, now=None):
    now = now or dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
    return NewsArticle(
        title=title, summary=summary, source="Test Wire", source_type="test",
        published_utc=now - dt.timedelta(hours=published_hours_ago),
        url="https://example.test/a",
    )


def _bundle(event_title, articles, now=None):
    now = now or dt.datetime(2026, 8, 12, 12, 30, tzinfo=UTC_TZ)
    event = EconomicEvent(
        title=event_title, country="USD", impact="High",
        event_time_utc=now, forecast="0.3%", previous="0.3%",
    )
    return EventNewsBundle(event=event, articles=articles, as_of_utc=now)


def test_no_lexicon_entry_returns_none():
    print("=== score_print_direction: an event title with no PRINT_SURPRISE_LEXICON entry returns None ===")
    bundle = _bundle("Some Untracked Indicator", [_article("Hotter than expected inflation data")])
    assert score_print_direction(bundle) is None
    print("PASS\n")


def test_unanimous_higher_hits_high_confidence():
    print("=== score_print_direction: all articles hitting 'higher' phrases returns HIGHER with high confidence ===")
    bundle = _bundle("CPI m/m", [
        _article("Economists warn of sticky inflation ahead of CPI"),
        _article("Analysts see upside surprise risk for CPI print"),
    ])
    call = score_print_direction(bundle)
    assert call is not None
    assert call.direction == "higher"
    assert call.confidence > 0.5
    assert call.article_count == 2
    print("PASS\n")


def test_unanimous_lower_hits():
    print("=== score_print_direction: all articles hitting 'lower' phrases returns LOWER ===")
    bundle = _bundle("CPI m/m", [
        _article("Signs of cooling inflation build ahead of report"),
        _article("Disinflation trend expected to continue"),
    ])
    call = score_print_direction(bundle)
    assert call.direction == "lower"
    print("PASS\n")


def test_ppi_lexicon_coverage_higher_and_lower():
    print("=== score_print_direction: PPI m/m and Core PPI m/m have real lexicon coverage (added ahead of the 2026-08-13 release) ===")
    higher_bundle = _bundle("PPI m/m", [
        _article("Producer prices surge past estimates, wholesale prices rise sharply"),
    ])
    higher_call = score_print_direction(higher_bundle)
    assert higher_call is not None
    assert higher_call.direction == "higher"

    lower_bundle = _bundle("Core PPI m/m", [
        _article("Producer prices cool more than expected, downside surprise for wholesale costs"),
    ])
    lower_call = score_print_direction(lower_bundle)
    assert lower_call is not None
    assert lower_call.direction == "lower"
    print("PASS\n")


def test_mixed_hits_lower_confidence_correct_majority():
    print("=== score_print_direction: mixed higher/lower hits picks the majority side with lower confidence than unanimous ===")
    bundle = _bundle("CPI m/m", [
        _article("Sticky inflation could push CPI higher"),
        _article("Sticky inflation remains a concern"),
        _article("Some see a downside surprise possible"),
    ])
    call = score_print_direction(bundle)
    assert call.direction == "higher"  # 2 higher-hit articles vs 1 lower-hit article

    unanimous_bundle = _bundle("CPI m/m", [
        _article("Sticky inflation could push CPI higher"),
        _article("Sticky inflation remains a concern"),
    ])
    unanimous_call = score_print_direction(unanimous_bundle)
    assert call.confidence < unanimous_call.confidence
    print("PASS\n")


def test_zero_hits_returns_in_line_low_confidence():
    print("=== score_print_direction: no phrase hits at all returns IN_LINE with low confidence, not a fabricated lean ===")
    bundle = _bundle("CPI m/m", [_article("Markets await Friday's jobs report")])
    call = score_print_direction(bundle)
    assert call is not None
    assert call.direction == "in_line"
    assert call.confidence < 0.3
    print("PASS\n")


def test_no_articles_returns_none():
    print("=== score_print_direction: an empty article bundle returns None, nothing to reason from ===")
    bundle = _bundle("CPI m/m", [])
    assert score_print_direction(bundle) is None
    print("PASS\n")


if __name__ == "__main__":
    test_no_lexicon_entry_returns_none()
    test_unanimous_higher_hits_high_confidence()
    test_unanimous_lower_hits()
    test_ppi_lexicon_coverage_higher_and_lower()
    test_mixed_hits_lower_confidence_correct_majority()
    test_zero_hits_returns_in_line_low_confidence()
    test_no_articles_returns_none()
    print("All print_direction tests passed.")
