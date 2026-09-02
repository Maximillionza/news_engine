"""
Tests for scoring/backtest_accumulator.py — no live network, calendar/
article fetching and scoring are all mocked.
"""
import sys
import os
import tempfile
import datetime as dt
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import UTC_TZ, PRE_EVENT_WINDOW_HOURS, ACCUMULATOR_MEDIUM_ALLOWLIST
from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle
from data_layer.cot_positioning import CotPositioningRead
from scoring.probability_engine import Direction, ProbabilityResult, ArticleContribution
from data_layer.news_feed import NewsArticle
import scoring.backtest_accumulator as accumulator
import scoring.backtest_store as store
import scoring.print_direction as accumulator_print_direction
import data_layer.kalshi_feed as accumulator_kalshi_feed
import webapp.store as webapp_store

# This whole file exercises the accumulator's OWN logic (calendar
# filtering, precursor lookup, Kalshi resolution, material-change
# gating, etc.) — none of it tests the R5 macro-backdrop cross-check
# itself (that's covered directly in tests/test_macro_backdrop.py and
# tests/test_probability_engine.py). Patched module-wide, unscoped, so
# every one of this file's ~30 run_accumulator_cycle() call sites never
# makes a real live FRED call, regardless of whether FRED_API_KEY
# happens to be set in the environment this suite runs in. Deliberately
# not stopped — this file runs standalone (its own process, `python
# tests/test_backtest_accumulator.py`), never inside a shared pytest
# session where a leaked patch could bleed into another file's tests.
patch.object(accumulator, "get_macro_backdrop_read", return_value=None).start()


def _fake_event(hours_from_now, now, title="Test Event", impact="High"):
    return EconomicEvent(
        title=title, country="USD", impact=impact,
        event_time_utc=now + dt.timedelta(hours=hours_from_now),
        forecast="1.0%", actual=None,
    )


def _bundle(event, articles, now=None):
    now = now or dt.datetime.now(UTC_TZ)
    return EventNewsBundle(event=event, articles=articles, as_of_utc=now)


def _fake_result(probability=0.7, direction=Direction.BULLISH):
    return ProbabilityResult(
        instrument="XAUUSD", as_of_utc=dt.datetime.now(UTC_TZ),
        aggregate_usd_sentiment=0.3, instrument_score=-0.3,
        probability=probability, direction=direction, confidence=0.5,
        article_count=5, contradiction_flag=False, contradiction_note=None,
    )


def test_interval_far_when_nothing_active():
    print("=== accumulator interval: FAR (12h) when no events, or nothing within the pre-event window ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    assert accumulator.compute_accumulator_interval_seconds(None, now=now) == accumulator.FAR_INTERVAL_SECONDS
    assert accumulator.compute_accumulator_interval_seconds([], now=now) == accumulator.FAR_INTERVAL_SECONDS
    far_event = _fake_event(hours_from_now=PRE_EVENT_WINDOW_HOURS + 10, now=now)
    assert accumulator.compute_accumulator_interval_seconds([far_event], now=now) == accumulator.FAR_INTERVAL_SECONDS
    print("PASS\n")


def test_interval_hourly_once_within_pre_event_window():
    print("=== accumulator interval: HOURLY baseline once an event is within its pre-event window, still outside 24h ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    event = _fake_event(hours_from_now=PRE_EVENT_WINDOW_HOURS - 5, now=now)  # inside the pre-event window, outside 24h
    assert accumulator.compute_accumulator_interval_seconds([event], now=now) == accumulator.HOURLY_INTERVAL_SECONDS
    print("PASS\n")


def test_interval_tighter_day_of_event():
    print("=== accumulator interval: tighter (15min) once an event is within 24h, outside the final hour ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    event = _fake_event(hours_from_now=10, now=now)
    assert accumulator.compute_accumulator_interval_seconds([event], now=now) == accumulator.DAY_OF_EVENT_INTERVAL_SECONDS
    print("PASS\n")


def test_interval_final_within_1h_or_grace():
    print("=== accumulator interval: FINAL (5min) within the final hour, and briefly after a scheduled release ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    soon = _fake_event(hours_from_now=0.5, now=now)
    assert accumulator.compute_accumulator_interval_seconds([soon], now=now) == accumulator.FINAL_INTERVAL_SECONDS
    just_passed = _fake_event(hours_from_now=-0.25, now=now)
    assert accumulator.compute_accumulator_interval_seconds([just_passed], now=now) == accumulator.FINAL_INTERVAL_SECONDS
    print("PASS\n")


def test_interval_budget_fallback_applies_to_hourly_and_day_of_event_only():
    print("=== accumulator interval: budget fallback (3h) kicks in once the rolling check count hits the threshold ===")
    now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
    over_budget = accumulator.DAILY_CHECK_BUDGET_THRESHOLD

    hourly_event = _fake_event(hours_from_now=PRE_EVENT_WINDOW_HOURS - 5, now=now)
    interval = accumulator.compute_accumulator_interval_seconds([hourly_event], now=now, recent_check_count=over_budget)
    assert interval == accumulator.BUDGET_FALLBACK_INTERVAL_SECONDS, "hourly tier must back off once over budget"

    day_of_event = _fake_event(hours_from_now=10, now=now)
    interval = accumulator.compute_accumulator_interval_seconds([day_of_event], now=now, recent_check_count=over_budget)
    assert interval == accumulator.BUDGET_FALLBACK_INTERVAL_SECONDS, "day-of-event tier must also back off once over budget"

    # The FINAL tier is always exempt — missing the check right before an
    # actual release is worse than a little extra article-fetch spend.
    final_event = _fake_event(hours_from_now=0.5, now=now)
    interval = accumulator.compute_accumulator_interval_seconds([final_event], now=now, recent_check_count=over_budget)
    assert interval == accumulator.FINAL_INTERVAL_SECONDS, "the final-hour tier must NEVER be throttled by the check budget"

    # Under budget — no throttling, normal tiers apply.
    interval = accumulator.compute_accumulator_interval_seconds([hourly_event], now=now, recent_check_count=0)
    assert interval == accumulator.HOURLY_INTERVAL_SECONDS
    print("PASS\n")


def test_checks_every_cycle_regardless_of_how_far_out_the_event_is():
    print("=== accumulator: checks (fetches+scores) every cycle the event is active — no per-pair check budget or timing gate ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=60, now=now)  # far out (60h), well outside the old final-window gate

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()) as mock_score, \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            # Three cycles, all still far from the event — every one of
            # them must fetch+score. Real regression test: the old design
            # would only check once here (window entry) and go silent for
            # the rest of the pre-event window — exactly the gap observed
            # live (a full 24h with an identical scored_at_utc).
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now + dt.timedelta(hours=1))
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now + dt.timedelta(hours=2))

            assert mock_score.call_count == 3, f"expected a check on every cycle, got {mock_score.call_count}"
    print("PASS\n")


def test_no_cap_on_recorded_snapshots_multiple_material_changes_all_recorded():
    print("=== accumulator: no fixed cap on recorded snapshots — every material change gets written, however many there are ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=60, now=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", side_effect=[
                 _fake_result(probability=0.55, direction=Direction.BULLISH),   # cycle 1: first ever, always recorded
                 _fake_result(probability=0.70, direction=Direction.BULLISH),   # cycle 2: +15pp, material -> recorded
                 _fake_result(probability=0.30, direction=Direction.BEARISH),   # cycle 3: flip -> recorded
             ]), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            for i in range(3):
                accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now + dt.timedelta(hours=i))

            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 3, \
                "the old design capped at 2 RECORDED snapshots total - three genuine material changes must all be recorded now"
            latest = store.get_latest_prediction(conn, "Test Event", "XAUUSD")
            assert latest.direction == "bearish" and abs(latest.probability - 0.30) < 1e-9
            conn.close()
    print("PASS\n")


def test_run_accumulator_cycle_logs_a_check_on_successful_fetch():
    print("=== accumulator: run_accumulator_cycle logs a check (record_check) on every successful article fetch ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            conn = store.get_connection(db_path)
            assert store.count_recent_checks(conn, since=now - dt.timedelta(hours=24)) == 0

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            assert store.count_recent_checks(conn, since=now - dt.timedelta(hours=24)) == 1
            conn.close()
    print("PASS\n")


def test_run_accumulator_cycle_does_not_log_a_check_on_failed_fetch():
    print("=== accumulator: a FAILED article fetch does not log a check — only successful fetches count against the budget ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", side_effect=Exception("article fetch blew up")):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)
            assert store.count_recent_checks(conn, since=now - dt.timedelta(hours=24)) == 0
            conn.close()
    print("PASS\n")


def test_unchanged_score_is_checked_but_not_recorded():
    print("=== accumulator: a re-check within the final window that finds NO material change is not recorded, but still checked ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", side_effect=[
                 _fake_result(probability=0.70, direction=Direction.BULLISH),  # cycle 1
                 _fake_result(probability=0.74, direction=Direction.BULLISH),  # cycle 2 — same direction, only +4pp, below threshold
             ]) as mock_score, \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1

            near_now = event.event_time_utc - dt.timedelta(minutes=20)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert mock_score.call_count == 2, "the second cycle must still fetch+score — supporting articles are checked, not skipped"
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1, \
                "a sub-threshold same-direction move is supporting, not material — must not be recorded"

            latest = store.get_latest_prediction(conn, "Test Event", "XAUUSD")
            assert latest.probability == 0.70, "the stored prediction must remain the ORIGINAL, unreplaced by the unrecorded check"
            conn.close()
    print("PASS\n")


def test_direction_flip_is_always_recorded_regardless_of_magnitude():
    print("=== accumulator: a direction flip is always material, even with a tiny probability change ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", side_effect=[
                 _fake_result(probability=0.55, direction=Direction.BULLISH),  # cycle 1
                 _fake_result(probability=0.56, direction=Direction.BEARISH),  # cycle 2 — tiny probability move, but direction FLIPPED
             ]), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)

            near_now = event.event_time_utc - dt.timedelta(minutes=20)
            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=near_now)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 2, \
                "a direction flip must always be recorded, regardless of how small the probability move is"
            latest = store.get_latest_prediction(conn, "Test Event", "XAUUSD")
            assert latest.direction == "bearish"
            conn.close()
    print("PASS\n")


def _fake_article_contribution(title, combined_weight, usd_sentiment=0.5, published_utc=None, source="Reuters"):
    article = NewsArticle(
        title=title, summary="summary", source=source, source_type="rss_reuters_business",
        published_utc=published_utc or dt.datetime(2026, 8, 17, 12, 0, tzinfo=UTC_TZ),
        url=f"https://example.test/{title.replace(' ', '-')}",
    )
    return ArticleContribution(
        article=article, usd_sentiment=usd_sentiment, trust_weight=0.85, time_weight=1.0,
        combined_weight=combined_weight, matched_terms=["hawkish"],
    )


def test_build_top_contributions_ranks_by_weight_and_caps_at_limit():
    print("=== accumulator: _build_top_contributions ranks by combined_weight descending, capped at TOP_CONTRIBUTIONS_LIMIT (3) ===")
    contributions = [
        _fake_article_contribution("Low weight story", 0.1),
        _fake_article_contribution("Highest weight story", 0.9),
        _fake_article_contribution("Second weight story", 0.6),
        _fake_article_contribution("Third weight story", 0.4),
        _fake_article_contribution("Fifth, excluded story", 0.05),
    ]
    result = accumulator._build_top_contributions(contributions)
    assert len(result) == 3
    assert [r["title"] for r in result] == ["Highest weight story", "Second weight story", "Third weight story"]
    total = sum(c.combined_weight for c in contributions)
    assert abs(result[0]["weight_pct"] - (0.9 / total * 100)) < 0.05
    print("PASS\n")


def test_build_top_contributions_includes_usd_sentiment_and_url():
    print("=== accumulator: _build_top_contributions includes usd_sentiment and a real article url, not just title ===")
    contributions = [_fake_article_contribution("Only story", 0.7, usd_sentiment=-0.6)]
    result = accumulator._build_top_contributions(contributions)
    assert len(result) == 1
    assert result[0]["usd_sentiment"] == -0.6
    assert result[0]["url"] == "https://example.test/Only-story"
    assert result[0]["weight_pct"] == 100.0
    print("PASS\n")


def test_build_top_contributions_returns_empty_list_for_no_contributions():
    print("=== accumulator: _build_top_contributions returns [] (not fabricated) for an empty contribution list ===")
    assert accumulator._build_top_contributions([]) == []
    print("PASS\n")


def test_build_top_contributions_returns_empty_list_when_total_weight_is_zero():
    print("=== accumulator: _build_top_contributions returns [] when total weight is zero (e.g. every combined_weight is 0) ===")
    contributions = [_fake_article_contribution("Zero weight story", 0.0)]
    assert accumulator._build_top_contributions(contributions) == []
    print("PASS\n")


def test_is_material_change_threshold_boundary():
    print("=== accumulator: _is_material_change — same-direction moves at/above 10pp are material, below are not ===")
    # Article counts held equal and well above THIN_SAMPLE_SIGNAL_THRESHOLD
    # on both sides throughout this test — isolates the probability-boundary
    # behavior from the separate thin-crossing behavior (its own test below).
    # Exactly at the threshold — material (>= , not strictly >).
    assert accumulator._is_material_change("bullish", 0.75, 10, "bullish", 0.65, 10) is True
    # Just under the threshold — not material.
    assert accumulator._is_material_change("bullish", 0.7499, 10, "bullish", 0.65, 10) is False
    # A direction flip is material regardless of magnitude, even a near-zero move.
    assert accumulator._is_material_change("bearish", 0.6501, 10, "bullish", 0.65, 10) is True
    # Identical direction and probability — not material.
    assert accumulator._is_material_change("bullish", 0.65, 10, "bullish", 0.65, 10) is False
    print("PASS\n")


def test_is_material_change_crossing_thin_sample_threshold_is_material():
    print("=== accumulator: _is_material_change — crossing THIN_SAMPLE_SIGNAL_THRESHOLD in article_count is material even with direction/probability unchanged ===")
    from config.settings import THIN_SAMPLE_SIGNAL_THRESHOLD
    # Real, live-observed case (2026-08-17): FOMC Meeting Minutes read
    # NEUTRAL 50% on 0 articles, then NEUTRAL 51% (a sub-threshold
    # probability move) on 130 articles — same call, went from no real
    # evidentiary basis to genuinely covered. That crossing must be
    # material on its own.
    assert accumulator._is_material_change(
        "neutral", 0.51, 130,
        "neutral", 0.50, 0,
    ) is True
    # The reverse direction (article coverage DROPS below the thin
    # threshold) is material too — the call's basis got weaker, not just stronger.
    assert accumulator._is_material_change(
        "neutral", 0.50, 1,
        "neutral", 0.51, 130,
    ) is True
    # Moving WITHIN the thin tier (both below threshold) is NOT material on
    # article-count grounds alone — still gated by the normal probability rule.
    assert accumulator._is_material_change(
        "neutral", 0.50, 1,
        "neutral", 0.50, 0,
    ) is False
    # Moving WITHIN the non-thin tier (both comfortably above threshold) is
    # NOT material on article-count grounds alone, regardless of how much
    # the count itself grew — still gated by the normal probability rule.
    assert accumulator._is_material_change(
        "neutral", 0.50, 500,
        "neutral", 0.50, THIN_SAMPLE_SIGNAL_THRESHOLD,
    ) is False
    print("PASS\n")


def test_precursor_events_found_and_passed_to_score_bundle():
    print("=== accumulator: an already-released precursor event (e.g. PPI before CPI) is found and blended into scoring ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        # "CPI m/m" is a real key in config.settings.PRECURSOR_EVENTS,
        # mapped to ["PPI m/m", "Core PPI m/m", "Import Prices m/m"] —
        # using a real title so find_precursor_events()'s real config
        # lookup actually matches, not a mocked stand-in.
        target = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=20), forecast="0.2%", actual=None,
        )
        precursor = EconomicEvent(
            title="Core PPI m/m", country="USD", impact="Medium",
            event_time_utc=now - dt.timedelta(hours=5), forecast="0.2%", actual="0.4%",  # already released
        )
        unrelated = EconomicEvent(
            title="Some Unrelated Report", country="USD", impact="Low",
            event_time_utc=now - dt.timedelta(hours=3), forecast="1.0%", actual="1.0%",
        )

        with patch.object(accumulator, "fetch_calendar", return_value=[target, precursor, unrelated]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: [e for e in events if e.impact == "High"]), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=target, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()) as mock_score, \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            mock_score.assert_called_once()
            _, kwargs = mock_score.call_args
            assert "precursor_events" in kwargs, "score_bundle must be called with precursor_events, not left at its None default"
            precursors_passed = kwargs["precursor_events"]
            assert len(precursors_passed) == 1, f"expected exactly the PPI precursor (Medium impact, real actual, before target), got {precursors_passed}"
            assert precursors_passed[0].title == "Core PPI m/m"
    print("PASS\n")


def test_print_direction_call_recorded_once_per_event():
    print("=== accumulator: score_print_direction is called once per event and recorded via record_print_prediction_if_changed ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=20),
            forecast="0.3%", actual=None,
        )
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)
        fake_call = accumulator_print_direction.PrintCall(direction="higher", confidence=0.6, article_count=2)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "score_print_direction", return_value=fake_call), \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            conn = store.get_connection(db_path)
            latest = store.get_latest_print_prediction(conn, "CPI m/m", event.event_time_utc)
            assert latest is not None
            assert latest.predicted_vs_forecast == "higher"
            assert latest.article_count == 2
            conn.close()
    print("PASS\n")


def test_print_direction_none_call_writes_nothing():
    print("=== accumulator: score_print_direction returning None (no lexicon coverage) writes no print_predictions row ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            conn = store.get_connection(db_path)
            assert store.get_latest_print_prediction(conn, event.title, event.event_time_utc) is None
            conn.close()
    print("PASS\n")


def test_trend_signal_passed_to_score_bundle_when_gate_met():
    print("=== accumulator: a trend_signal is computed and passed to score_bundle() when >=3 confirmed occurrences exist ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"  # must be in EVENT_SURPRISE_DIRECTION for the gate to matter downstream
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        # Seed 3 confirmed occurrences in the dashboard's event_history table.
        dash_conn = webapp_store.get_connection(dashboard_db_path)
        for month in (5, 6, 7):
            hist_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                forecast="0.3%", previous="0.3%", actual="0.5%",
            )
            webapp_store.upsert_event_history(dash_conn, hist_event, "higher", now=hist_event.event_time_utc)
        dash_conn.close()

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["trend_signal"] = trend_signal
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert captured_kwargs["trend_signal"] is not None
        assert captured_kwargs["trend_signal"].direction == "higher"
    print("PASS\n")


def test_trend_signal_is_none_when_gate_not_met():
    print("=== accumulator: trend_signal is None when fewer than MIN_OCCURRENCES_FOR_TREND_PRIOR confirmed occurrences exist ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        # Seed only 2 confirmed occurrences — below MIN_OCCURRENCES_FOR_TREND_PRIOR=3.
        dash_conn = webapp_store.get_connection(dashboard_db_path)
        for month in (6, 7):
            hist_event = EconomicEvent(
                title="CPI m/m", country="USD", impact="High",
                event_time_utc=dt.datetime(2026, month, 12, 12, 30, tzinfo=UTC_TZ),
                forecast="0.3%", previous="0.3%", actual="0.5%",
            )
            webapp_store.upsert_event_history(dash_conn, hist_event, "higher", now=hist_event.event_time_utc)
        dash_conn.close()

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["trend_signal"] = trend_signal
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert captured_kwargs["trend_signal"] is None
    print("PASS\n")


def test_trend_signal_is_none_when_dashboard_db_unreachable():
    print("=== accumulator: a failed dashboard-DB read fails OPEN to trend_signal=None, does not crash the cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["trend_signal"] = trend_signal
            return _fake_result()

        # Nonexistent path in a directory that doesn't exist — get_connection's
        # executescript() will raise (sqlite3.OperationalError: unable to open database file).
        unreachable_dashboard_db = Path(tmp) / "nonexistent_subdir" / "dashboard.db"

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", unreachable_dashboard_db):

            events_result = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert events_result is not None  # cycle completed, did not crash/return None
        assert captured_kwargs["trend_signal"] is None
    print("PASS\n")


def test_trend_signal_is_none_when_read_itself_fails():
    print("=== accumulator: a failure during the event_history READ (not just connect) also fails open to trend_signal=None ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        # A real, reachable dashboard DB (so get_dashboard_connection succeeds) —
        # the failure is injected into the READ call specifically.
        webapp_store.get_connection(dashboard_db_path).close()

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["trend_signal"] = trend_signal
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path), \
             patch.object(accumulator, "get_event_history", side_effect=Exception("simulated read failure")):

            events_result = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert events_result is not None  # cycle completed, did not crash/abort
        assert captured_kwargs["trend_signal"] is None
    print("PASS\n")


def test_print_call_passed_to_score_bundle():
    print("=== accumulator: the already-computed print_call is passed through to score_bundle() ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)
        fake_call = accumulator_print_direction.PrintCall(direction="higher", confidence=0.6, article_count=2)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["print_call"] = print_call
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=fake_call), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert captured_kwargs["print_call"] is fake_call
    print("PASS\n")


def test_precursor_events_uses_unfiltered_calendar_not_high_impact_only():
    print("=== accumulator: precursor lookup uses the FULL unfiltered calendar, not the High-impact-only filtered list ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        target = EconomicEvent(
            title="CPI m/m", country="USD", impact="High",
            event_time_utc=now + dt.timedelta(hours=20), forecast="0.2%", actual=None,
        )
        # Medium impact — filter_relevant_events() (High-only) would drop
        # this from the SCORING candidate list, but it must still be found
        # as a precursor, since find_precursor_events() is explicitly
        # supposed to search the full calendar (precursors are typically
        # Medium impact, per the module's own established convention).
        precursor = EconomicEvent(
            title="PPI m/m", country="USD", impact="Medium",
            event_time_utc=now - dt.timedelta(hours=5), forecast="0.2%", actual="0.5%",
        )

        with patch.object(accumulator, "fetch_calendar", return_value=[target, precursor]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: [e for e in events if e.impact == "High"]), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=target, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()) as mock_score, \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            _, kwargs = mock_score.call_args
            titles_passed = [e.title for e in kwargs["precursor_events"]]
            assert "PPI m/m" in titles_passed, "Medium-impact precursor must still be found via the full unfiltered calendar"
    print("PASS\n")


def test_high_impact_only_no_medium_widening():
    print("=== accumulator: uses filter_relevant_events with default (High-only) min_impact, not Medium widening like the dashboard — only the curated allowlist extra_titles kwarg is passed ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)

        with patch.object(accumulator, "fetch_calendar", return_value=[]) as mock_fetch, \
             patch.object(accumulator, "filter_relevant_events", return_value=[]) as mock_filter, \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)
            mock_filter.assert_called_once_with(mock_fetch.return_value, extra_titles=ACCUMULATOR_MEDIUM_ALLOWLIST)
            # No min_impact kwarg — confirms this does NOT widen the THRESHOLD to Medium
            # like webapp/scheduler.py does; only the curated allowlist is admitted.
            assert set(mock_filter.call_args.kwargs.keys()) == {"extra_titles"}
    print("PASS\n")


def test_accumulator_includes_allowlisted_medium_events():
    print("=== accumulator: run_accumulator_cycle() includes a Medium-impact event on the curated allowlist ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        high_event = _fake_event(hours_from_now=20, now=now, title="CPI m/m", impact="High")
        allowlisted_medium = _fake_event(
            hours_from_now=20, now=now, title="Retail Sales m/m", impact="Medium",
        )

        def _fake_bundle(event, sources, query="", mode="live"):
            return EventNewsBundle(event=event, articles=[], as_of_utc=now)

        # filter_relevant_events is NOT patched here — this exercises the
        # real function (with the real ACCUMULATOR_MEDIUM_ALLOWLIST wired
        # in at the call site) rather than bypassing it like most of this
        # file's other tests do.
        with patch.object(accumulator, "fetch_calendar", return_value=[high_event, allowlisted_medium]), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", side_effect=_fake_bundle), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            events = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            titles = {e.title for e in events}
            assert titles == {"CPI m/m", "Retail Sales m/m"}, f"expected both events, got {titles}"

            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Retail Sales m/m", "XAUUSD", allowlisted_medium.event_time_utc) == 1, (
                "the allowlisted Medium event must actually get processed and recorded, not just pass the filter"
            )
            conn.close()
    print("PASS\n")


def test_accumulator_excludes_non_allowlisted_medium_events():
    print("=== accumulator: a Medium event NOT on the allowlist is still excluded ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        high_event = _fake_event(hours_from_now=20, now=now, title="CPI m/m", impact="High")
        other_medium = _fake_event(
            hours_from_now=20, now=now, title="Building Permits", impact="Medium",
        )

        def _fake_bundle(event, sources, query="", mode="live"):
            return EventNewsBundle(event=event, articles=[], as_of_utc=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[high_event, other_medium]), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", side_effect=_fake_bundle), \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            events = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

            titles = {e.title for e in events}
            assert titles == {"CPI m/m"}, f"Building Permits (non-allowlisted Medium) must be excluded, got {titles}"

            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Building Permits", "XAUUSD", other_medium.event_time_utc) == 0
            conn.close()
    print("PASS\n")


def test_failed_scoring_for_one_pair_does_not_stop_others():
    print("=== accumulator: a scoring failure for one instrument doesn't stop the other instrument's snapshot ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)

        def flaky_score_bundle(bundle, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            if instrument == "XAUUSD":
                raise Exception("scoring blew up")
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=EventNewsBundle(event=event, articles=[], as_of_utc=now)), \
             patch.object(accumulator, "score_bundle", side_effect=flaky_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            accumulator.run_accumulator_cycle(["XAUUSD", "US30"], db_path=db_path, now=now)
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 0, "the failing instrument should not get a row"
            assert store.count_predictions(conn, "Test Event", "US30", event.event_time_utc) == 1, "the other instrument should still succeed"
            conn.close()
    print("PASS\n")


def test_article_bundle_fetched_once_per_event_not_per_instrument():
    print("=== accumulator: build_event_news_bundle is called ONCE per event, reused across all instruments needing a snapshot ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle) as mock_bundle, \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", Path(tmp) / "dashboard.db"):

            accumulator.run_accumulator_cycle(["XAUUSD", "US30"], db_path=db_path, now=now)

            assert mock_bundle.call_count == 1, (
                f"expected build_event_news_bundle to be called exactly once per event "
                f"(reused across instruments), got {mock_bundle.call_count} calls"
            )
            conn = store.get_connection(db_path)
            assert store.count_predictions(conn, "Test Event", "XAUUSD", event.event_time_utc) == 1
            assert store.count_predictions(conn, "Test Event", "US30", event.event_time_utc) == 1
            conn.close()
    print("PASS\n")


def test_failed_calendar_fetch_returns_none_without_crashing():
    print("=== accumulator: a failed calendar fetch returns None and does not crash ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        with patch.object(accumulator, "fetch_calendar", side_effect=Exception("network down")):
            result = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path)
            assert result is None
    print("PASS\n")


def test_shift_back_one_month_normal_case():
    print("=== accumulator: _shift_back_one_month shifts a normal month back by one, day pinned to 1 ===")
    assert accumulator._shift_back_one_month(dt.date(2026, 8, 15)) == dt.date(2026, 7, 1)
    print("PASS\n")


def test_shift_back_one_month_year_rollover():
    print("=== accumulator: _shift_back_one_month handles January -> prior December year rollover ===")
    assert accumulator._shift_back_one_month(dt.date(2026, 1, 20)) == dt.date(2025, 12, 1)
    print("PASS\n")


def test_kalshi_read_passed_to_score_bundle_for_numeric_event():
    print("=== accumulator: a Kalshi read is fetched, recorded, and passed to score_bundle() for a numeric-forecast event ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        event.forecast = "0.1%"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)
        fake_read = accumulator_kalshi_feed.KalshiRead(strike=0.1, implied_direction="higher", implied_probability=0.65, open_interest=100.0)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["kalshi_read"] = kalshi_read
            captured_kwargs["kalshi_direction_override"] = kalshi_direction_override
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read", return_value=fake_read) as mock_kalshi, \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert captured_kwargs["kalshi_read"] is fake_read
        assert captured_kwargs["kalshi_direction_override"] == "higher_bullish", \
            "CPI m/m's EVENT_SURPRISE_DIRECTION entry must be resolved and passed through as the override"
        mock_kalshi.assert_called_once()
        args, kwargs = mock_kalshi.call_args
        assert args[0] == "KXCPI"  # series ticker resolved from KALSHI_SERIES_BY_EVENT_TITLE["CPI m/m"]
        # event.event_time_utc is now + 20h = 2026-08-11 (release date) — Kalshi
        # tickets the DATA month, one month BEHIND the release, so the second
        # positional arg must be the SHIFTED month (2026-07-01), not the raw
        # release date's month (2026-08-11). See _shift_back_one_month().
        assert args[1] == dt.date(2026, 7, 1), \
            f"expected the release date shifted back one month, got {args[1]}"

        conn = store.get_connection(db_path)
        latest = store.get_latest_kalshi_read(conn, "CPI m/m", event.event_time_utc)
        assert latest is not None
        assert latest.implied_direction == "higher"
        conn.close()
    print("PASS\n")


def test_kalshi_lookup_skipped_for_event_with_no_series_mapping():
    print("=== accumulator: an event title with no Kalshi series mapping never triggers get_market_read() ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)  # "Test Event" — not in any Kalshi mapping
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read") as mock_kalshi, \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        mock_kalshi.assert_not_called()
    print("PASS\n")


def test_kalshi_lookup_skipped_for_unparseable_forecast():
    print("=== accumulator: an event with an unparseable/missing forecast skips the Kalshi lookup entirely ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        event.forecast = None  # unparseable/missing
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read") as mock_kalshi, \
             patch.object(accumulator, "score_bundle", return_value=_fake_result()), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        mock_kalshi.assert_not_called()
    print("PASS\n")


def test_kalshi_fetch_failure_fails_open_without_crashing_cycle():
    print("=== accumulator: get_market_read() raising or returning None fails open, does not crash the cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        event.forecast = "0.1%"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["kalshi_read"] = kalshi_read
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read", side_effect=Exception("network down")), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            events_result = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert events_result is not None  # cycle completed, did not crash
        assert captured_kwargs["kalshi_read"] is None
    print("PASS\n")


def test_kalshi_fetch_returning_none_fails_open_without_crashing_cycle():
    print("=== accumulator: get_market_read() returning None (not raising) fails open, does not crash the cycle ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "CPI m/m"
        event.forecast = "0.1%"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["kalshi_read"] = kalshi_read
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read", return_value=None), \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            events_result = accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        assert events_result is not None  # cycle completed, did not crash
        assert captured_kwargs["kalshi_read"] is None
    print("PASS\n")


def test_read_kalshi_signal_resolves_fomc_via_month_ticker():
    print("=== R4: accumulator: 'Federal Funds Rate' resolves via the MONTH-ticketed path — KXFED was misclassified as date-ticketed, now fixed ===")
    # Live-verified 2026-08-14 against Kalshi's real /events?series_ticker=KXFED
    # response: real tickers are month-only (e.g. "KXFED-26SEP"), the same
    # shape get_market_read()/_resolve_event_ticker() already handle — see
    # KALSHI_RATE_DECISION_SERIES's comment in config.settings. This
    # replaces the old test that locked in the (wrong) empty-mapping
    # behavior.
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "Federal Funds Rate"
        event.forecast = "4.25%"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)
        fake_read = accumulator_kalshi_feed.KalshiRead(strike=4.25, implied_direction="in_line", implied_probability=0.5, open_interest=100.0)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["kalshi_read"] = kalshi_read
            captured_kwargs["kalshi_direction_override"] = kalshi_direction_override
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read", return_value=fake_read) as mock_kalshi, \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        mock_kalshi.assert_called_once()
        args, kwargs = mock_kalshi.call_args
        assert args[0] == "KXFED"
        # No month-shift for FOMC (unlike CPI/NFP/etc.) — KXFED tickets its
        # OWN meeting month, not the data-reference month one month back.
        assert args[1] == event.event_time_utc.date(), \
            f"expected the meeting's own release date, unshifted, got {args[1]}"
        assert captured_kwargs["kalshi_read"] is fake_read
        assert captured_kwargs["kalshi_direction_override"] == "higher_bullish"
    print("PASS\n")


def test_read_kalshi_signal_resolves_date_ticketed_event():
    print("=== R4: accumulator: a date-ticketed event (e.g. Retail Sales m/m) resolves via get_market_read_by_date ===")
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        dashboard_db_path = Path(tmp) / "dashboard.db"
        now = dt.datetime(2026, 8, 10, 12, 0, tzinfo=UTC_TZ)
        event = _fake_event(hours_from_now=20, now=now)
        event.title = "Retail Sales m/m"
        event.forecast = "0.3%"
        bundle = EventNewsBundle(event=event, articles=[], as_of_utc=now)
        fake_read = accumulator_kalshi_feed.KalshiRead(strike=0.3, implied_direction="higher", implied_probability=0.6, open_interest=100.0)

        captured_kwargs = {}
        def _capture_score_bundle(bundle_arg, instrument, precursor_events=None, print_call=None, trend_signal=None, kalshi_read=None, kalshi_direction_override=None, macro_backdrop=None, cot_positioning=None, current_direction=None):
            captured_kwargs["kalshi_read"] = kalshi_read
            captured_kwargs["kalshi_direction_override"] = kalshi_direction_override
            return _fake_result()

        with patch.object(accumulator, "fetch_calendar", return_value=[event]), \
             patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
             patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
             patch.object(accumulator, "build_event_news_bundle", return_value=bundle), \
             patch.object(accumulator, "score_print_direction", return_value=None), \
             patch.object(accumulator, "get_market_read_by_date", return_value=fake_read) as mock_kalshi_by_date, \
             patch.object(accumulator, "get_market_read") as mock_kalshi_by_month, \
             patch.object(accumulator, "score_bundle", side_effect=_capture_score_bundle), \
             patch.object(accumulator, "DASHBOARD_DB_PATH", dashboard_db_path):

            accumulator.run_accumulator_cycle(["XAUUSD"], db_path=db_path, now=now)

        mock_kalshi_by_month.assert_not_called()
        mock_kalshi_by_date.assert_called_once()
        args, kwargs = mock_kalshi_by_date.call_args
        assert args[0] == "KXUSRETAIL"
        assert args[1] == event.event_time_utc.date()  # no month-lag for date-ticketed series
        assert captured_kwargs["kalshi_read"] is fake_read
        assert captured_kwargs["kalshi_direction_override"] == "higher_bullish"
    print("PASS\n")


def test_run_accumulator_cycle_fetches_cot_once_per_cycle_not_per_event():
    print("=== run_accumulator_cycle: cot_positioning is fetched ONCE per cycle, reused across every active event, same as macro_backdrop ===")
    event_a = EconomicEvent(title="CPI m/m", country="USD", impact="High", event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ), forecast="0.3%", previous="0.3%")
    event_b = EconomicEvent(title="PPI m/m", country="USD", impact="High", event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ), forecast="0.2%", previous="0.2%")
    with patch.object(accumulator, "fetch_calendar", return_value=[event_a, event_b]), \
         patch.object(accumulator, "filter_relevant_events", side_effect=lambda events, **kwargs: events), \
         patch.object(accumulator, "events_in_pre_window", return_value=[event_a, event_b]), \
         patch.object(accumulator, "build_all_preview_sources", return_value=[]), \
         patch.object(accumulator, "get_macro_backdrop_read", return_value=None), \
         patch.object(accumulator, "get_cot_positioning_read", return_value=None) as mock_cot, \
         patch.object(accumulator, "score_and_record_event") as mock_score, \
         patch.object(accumulator, "get_connection"):
        accumulator.run_accumulator_cycle(["XAUUSD"])

    assert mock_cot.call_count == 1  # fetched once, not once per event
    # Both calls to score_and_record_event received the SAME cot_positioning value (None here, but the point is it's the one shared fetch, not a fresh one per event)
    assert mock_score.call_count == 2
    print("PASS\n")


def test_score_and_record_event_passes_cot_positioning_through_to_score_bundle():
    print("=== score_and_record_event: cot_positioning is threaded through to score_bundle() unchanged ===")
    event = EconomicEvent(title="CPI m/m", country="USD", impact="High", event_time_utc=dt.datetime(2026, 9, 2, 12, 30, tzinfo=UTC_TZ), forecast="0.3%", previous="0.3%")
    sentinel_cot = CotPositioningRead(net_leveraged_funds_position=100, percentile_in_trailing_window=50.0, report_date=dt.date(2026, 8, 29), lookback_weeks=52)
    with patch.object(accumulator, "build_event_news_bundle", return_value=_bundle(event, [])), \
         patch.object(accumulator, "record_check"), \
         patch.object(accumulator, "find_precursor_events", return_value=[]), \
         patch.object(accumulator, "score_print_direction", return_value=None), \
         patch.object(accumulator, "_read_trend_signal", return_value=None), \
         patch.object(accumulator, "_read_kalshi_signal", return_value=(None, None)), \
         patch.object(accumulator, "get_latest_prediction", return_value=None), \
         patch.object(accumulator, "score_bundle") as mock_score_bundle, \
         patch.object(accumulator, "_is_material_change", return_value=False):
        accumulator.score_and_record_event(
            conn=MagicMock(), event=event, all_events=[event], instruments=["XAUUSD"],
            sources=[], cot_positioning=sentinel_cot,
        )

    assert mock_score_bundle.call_args.kwargs["cot_positioning"] is sentinel_cot
    print("PASS\n")


if __name__ == "__main__":
    test_interval_far_when_nothing_active()
    test_interval_hourly_once_within_pre_event_window()
    test_interval_tighter_day_of_event()
    test_interval_final_within_1h_or_grace()
    test_interval_budget_fallback_applies_to_hourly_and_day_of_event_only()
    test_run_accumulator_cycle_logs_a_check_on_successful_fetch()
    test_run_accumulator_cycle_does_not_log_a_check_on_failed_fetch()
    test_checks_every_cycle_regardless_of_how_far_out_the_event_is()
    test_no_cap_on_recorded_snapshots_multiple_material_changes_all_recorded()
    test_unchanged_score_is_checked_but_not_recorded()
    test_direction_flip_is_always_recorded_regardless_of_magnitude()
    test_build_top_contributions_ranks_by_weight_and_caps_at_limit()
    test_build_top_contributions_includes_usd_sentiment_and_url()
    test_build_top_contributions_returns_empty_list_for_no_contributions()
    test_build_top_contributions_returns_empty_list_when_total_weight_is_zero()
    test_is_material_change_threshold_boundary()
    test_is_material_change_crossing_thin_sample_threshold_is_material()
    test_precursor_events_found_and_passed_to_score_bundle()
    test_print_direction_call_recorded_once_per_event()
    test_print_direction_none_call_writes_nothing()
    test_trend_signal_passed_to_score_bundle_when_gate_met()
    test_trend_signal_is_none_when_gate_not_met()
    test_trend_signal_is_none_when_dashboard_db_unreachable()
    test_trend_signal_is_none_when_read_itself_fails()
    test_print_call_passed_to_score_bundle()
    test_precursor_events_uses_unfiltered_calendar_not_high_impact_only()
    test_high_impact_only_no_medium_widening()
    test_accumulator_includes_allowlisted_medium_events()
    test_run_accumulator_cycle_fetches_cot_once_per_cycle_not_per_event()
    test_score_and_record_event_passes_cot_positioning_through_to_score_bundle()
    test_accumulator_excludes_non_allowlisted_medium_events()
    test_failed_scoring_for_one_pair_does_not_stop_others()
    test_article_bundle_fetched_once_per_event_not_per_instrument()
    test_failed_calendar_fetch_returns_none_without_crashing()
    test_shift_back_one_month_normal_case()
    test_shift_back_one_month_year_rollover()
    test_kalshi_read_passed_to_score_bundle_for_numeric_event()
    test_kalshi_lookup_skipped_for_event_with_no_series_mapping()
    test_kalshi_lookup_skipped_for_unparseable_forecast()
    test_kalshi_fetch_failure_fails_open_without_crashing_cycle()
    test_kalshi_fetch_returning_none_fails_open_without_crashing_cycle()
    test_read_kalshi_signal_resolves_fomc_via_month_ticker()
    test_read_kalshi_signal_resolves_date_ticketed_event()
    print("All backtest_accumulator tests passed.")
