"""
One-off historical backfill: writes real researched event facts, and —
only where genuinely retrievable — real article-based predictions and
real price outcomes. Never reconstructs, never approximates. See
docs/superpowers/specs/2026-08-13-historical-backfill-and-ui-redesign-design.md.

Run: python scripts/seed_historical_data.py [--dry-run]

Idempotent: safe to re-run (e.g. across multiple days, respecting Alpha
Vantage's 25-req/day free-tier cap) — a seeded predictions/outcomes row
is only written once per (event_title, instrument, event_time_utc).
"""
from __future__ import annotations

import sys
import os
import datetime as dt
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import INSTRUMENTS, UTC_TZ, EVENT_SURPRISE_DIRECTION
from data_layer.calendar_feed import EconomicEvent, classify_surprise
from data_layer.historical_events import HISTORICAL_EVENTS, HistoricalEventFact
from data_layer.event_context import build_event_news_bundle, EventNewsBundle
from data_layer.news_feed import AlphaVantageNewsSource, NewsArticle
import webapp.store as dash_store
import scoring.backtest_store as bt_store
from scoring.probability_engine import score_bundle
from scoring.print_direction import score_print_direction


@dataclass
class SeedReport:
    calendar_writes: int = 0
    predictions_written: int = 0
    predictions_skipped: int = 0
    print_predictions_written: int = 0
    print_predictions_skipped: int = 0
    outcomes_written: int = 0
    outcomes_skipped: int = 0
    skip_reasons: list[str] = field(default_factory=list)


def _fetch_real_articles(event: EconomicEvent) -> list[NewsArticle]:
    """
    Attempts a genuine historical article pull via Alpha Vantage's
    NEWS_SENTIMENT endpoint (the only source in this codebase whose
    since_utc/time_from param genuinely queries the past — RSS sources
    are real-time-only, no archive). Returns [] — never fabricated — on
    any failure (API error, empty result, retention window exceeded).
    Reuses the EXACT same bundle-construction path the live accumulator
    uses (mode='backtest', cutoff at the event's own time — no future
    leak), just with AlphaVantageNewsSource as the only source.
    """
    try:
        bundle = build_event_news_bundle(
            event, sources=[AlphaVantageNewsSource()], query="",
            mode="backtest", backtest_cutoff_utc=event.event_time_utc,
        )
        return bundle.articles
    except Exception as exc:  # noqa: BLE001 — any fetch/config failure degrades to "no real articles", never a fabricated fallback
        print(f"[seed_historical_data] No real articles for {event.title} at {event.event_time_utc.isoformat()}: {exc}")
        return []


def _attempt_article_prediction(bundle: EventNewsBundle | None, instrument: str):
    """
    Runs the ACTUAL score_bundle() against a bundle built from genuinely-
    retrieved articles — never a hand-typed reconstruction. Returns None
    if there was no bundle (no real articles, nothing to score) or if
    score_bundle() itself found nothing scoreable (e.g. all articles too
    far from the event to carry weight). Takes the bundle directly (built
    once per fact by run_seed(), not per instrument) rather than raw
    articles, so it never reconstructs its own EventNewsBundle.
    """
    if bundle is None:
        return None
    result = score_bundle(bundle, instrument)
    if not result.contributions and not result.precursor_contributions:
        return None
    return result


def _classify_outcome(instrument: str, event_time_utc: dt.datetime):
    """
    Runs the ACTUAL outcome_classifier.classify() against genuine
    historical Dukascopy prices. Lazy import — same reasoning as
    scripts/confirm_backtest_outcomes.py: the optional Dukascopy
    dependency must not be required for a --dry-run or any caller that
    doesn't need it.
    """
    from scoring.outcome_classifier import classify
    return classify(instrument, event_time_utc)


def _attempt_outcome_confirmation(instrument: str, event_time_utc: dt.datetime):
    try:
        return _classify_outcome(instrument, event_time_utc)
    except Exception as exc:  # noqa: BLE001 — any fetch failure degrades to "no real outcome", never fabricated
        print(f"[seed_historical_data] No real outcome for {instrument} at {event_time_utc.isoformat()}: {exc}")
        return None


def run_seed(
    facts: list[HistoricalEventFact],
    dashboard_conn,
    backtest_conn,
    instruments: list[str],
    now: dt.datetime | None = None,
) -> SeedReport:
    # Title-validation gate: a typo'd HistoricalEventFact.title would
    # otherwise silently fail to classify (classify_surprise() returns
    # None for any title not in EVENT_SURPRISE_DIRECTION, with no error)
    # — catch that here, before any write, so a direct (non-dry-run)
    # invocation can't silently write bad-title data. Duplicated by the
    # --dry-run path below on purpose, so --dry-run still reports this
    # without needing DB connections.
    unrecognized = sorted({
        fact.title for fact in facts
        if fact.title not in EVENT_SURPRISE_DIRECTION
    })
    if unrecognized:
        raise ValueError(
            f"[seed_historical_data] {len(unrecognized)} HistoricalEventFact title(s) "
            f"do not match any config.settings.EVENT_SURPRISE_DIRECTION key: {unrecognized}"
        )

    report = SeedReport()
    now = now or dt.datetime.now(UTC_TZ)

    for fact in facts:
        event = EconomicEvent(fact.title, "USD", "High", fact.event_time_utc)
        event.forecast = fact.forecast
        event.previous = fact.previous
        event.actual = fact.actual

        # classify_surprise() takes only the event — it looks up
        # EVENT_SURPRISE_DIRECTION[event.title] internally (as an
        # is-this-title-tracked gate, not for its higher_bullish/
        # higher_bearish values). The brief's draft called this with a
        # second positional arg (EVENT_SURPRISE_DIRECTION.get(fact.title))
        # which does not match the real signature in
        # data_layer/calendar_feed.py — corrected here.
        surprise_direction = classify_surprise(event)
        dash_store.upsert_event_history(dashboard_conn, event, surprise_direction, now, source="seeded")
        report.calendar_writes += 1

        # Per-instrument idempotency checks for `predictions` (independent
        # of the per-fact `print_predictions` check below — see the outer
        # comment on the outcomes gate for why each table is checked on its
        # own terms) — computed up front so we know whether any instrument
        # still needs a scored prediction, and whether the per-fact
        # print-direction call still needs to run, BEFORE deciding whether
        # to spend an Alpha Vantage request at all.
        instruments_needing_prediction = [
            instrument for instrument in instruments
            if not backtest_conn.execute(
                "SELECT 1 FROM predictions WHERE event_title = ? AND instrument = ? AND event_time_utc = ? AND source = 'seeded'",
                (fact.title, instrument, fact.event_time_utc.isoformat()),
            ).fetchone()
        ]
        already_print_predicted = backtest_conn.execute(
            "SELECT 1 FROM print_predictions WHERE event_title = ? AND event_time_utc = ? AND source = 'seeded'",
            (fact.title, fact.event_time_utc.isoformat()),
        ).fetchone()

        # Fetch real articles (and build the ONE bundle used by every
        # downstream scorer) at most once per FACT, not once per
        # instrument — score_bundle() is the only thing that varies by
        # instrument; the underlying articles and event context do not.
        # With INSTRUMENTS = {XAUUSD, US30} this halves Alpha Vantage
        # request usage against its 25-req/day free-tier budget versus
        # fetching inside the instrument loop. Also skipped entirely once
        # every consumer of it (both the per-instrument predictions and
        # the per-fact print_predictions call) is already idempotently
        # satisfied for this occurrence.
        bundle: EventNewsBundle | None = None
        if instruments_needing_prediction or not already_print_predicted:
            articles = _fetch_real_articles(event)
            if articles:
                bundle = EventNewsBundle(event=event, articles=articles, as_of_utc=event.event_time_utc)

        # Print-direction prediction ("will THIS release beat/miss
        # forecast") is scored once PER EVENT/FACT, not per instrument —
        # score_print_direction() reasons about the release itself, not
        # about any particular instrument's reaction to it. Gated
        # idempotently the same way `predictions` is: a pre-insert
        # existence check for source='seeded' on this exact occurrence
        # (already_print_predicted, computed above). This is a DIFFERENT
        # idempotency concern than record_print_prediction_if_changed()'s
        # own diff-aware "only write if direction changed" behavior — that
        # governs whether an already-attempted seed write is redundant;
        # this governs whether the seed script has already ATTEMPTED this
        # occurrence at all, so a rerun with different (mocked/live)
        # article data doesn't re-attempt and potentially re-diff.
        if not already_print_predicted:
            print_call = score_print_direction(bundle) if bundle is not None else None
            if print_call is None:
                report.print_predictions_skipped += 1
                report.skip_reasons.append(f"{fact.title}@{fact.event_time_utc.isoformat()}: no real print-direction call")
            else:
                bt_store.record_print_prediction_if_changed(
                    backtest_conn, fact.title, fact.event_time_utc, print_call,
                    now=now, source="seeded",
                )
                report.print_predictions_written += 1

        for instrument in instruments:
            # Idempotency: predictions and outcomes are gated INDEPENDENTLY,
            # each against its own table — not one combined check. A prior
            # run may have written an outcome but no prediction (no real
            # articles that time, but a clear Dukascopy classification), or
            # vice versa; a single shared gate would either re-attempt (and
            # crash on outcomes' UNIQUE(event_title, instrument,
            # event_time_utc) constraint — no ON CONFLICT clause on that
            # insert) or wrongly skip a layer that never actually ran yet.
            if instrument in instruments_needing_prediction:
                result = _attempt_article_prediction(bundle, instrument)
                if result is None:
                    report.predictions_skipped += 1
                    report.skip_reasons.append(f"{fact.title}/{instrument}@{fact.event_time_utc.isoformat()}: no real article-based prediction")
                else:
                    bt_store.record_prediction(
                        backtest_conn, fact.title, instrument, fact.event_time_utc,
                        result.probability, result.direction.value, result.confidence,
                        result.article_count, result.contradiction_flag,
                        # A seeded row's timestamp is the event's own time,
                        # not "now" (the time the seed script happened to
                        # run) — so a seeded historical row never
                        # out-ranks a genuine live row's actual scoring
                        # time in latest-lookup functions like
                        # get_latest_prediction() (MAX(scored_at_utc)).
                        scored_at_utc=fact.event_time_utc, source="seeded",
                    )
                    report.predictions_written += 1

            # Outcome confirmation is attempted independently of whether a
            # prediction was written — the price-outcome layer (#3 in the
            # design doc) is its own genuine-retrieval-or-absent question,
            # not gated behind the article-prediction layer (#2) having
            # succeeded. The brief's draft nested this inside the
            # "prediction written" branch, which would silently skip outcome
            # confirmation for every occurrence with no real articles even
            # when Dukascopy prices ARE genuinely available for it —
            # corrected here. Gated on `outcomes` itself (not on `source`,
            # since a real live-confirmed outcome for this exact occurrence
            # must block a seeded insert too — record_outcome() has no
            # ON CONFLICT and would raise on the table's UNIQUE constraint).
            already_outcomed = backtest_conn.execute(
                "SELECT 1 FROM outcomes WHERE event_title = ? AND instrument = ? AND event_time_utc = ?",
                (fact.title, instrument, fact.event_time_utc.isoformat()),
            ).fetchone()
            if already_outcomed:
                continue
            classification = _attempt_outcome_confirmation(instrument, fact.event_time_utc)
            if classification is None or classification.direction is None:
                report.outcomes_skipped += 1
                note = classification.note if classification is not None else "no real outcome data"
                report.skip_reasons.append(f"{fact.title}/{instrument}@{fact.event_time_utc.isoformat()}: ambiguous/absent outcome ({note})")
                continue
            bt_store.record_outcome(
                backtest_conn, fact.title, instrument, fact.event_time_utc,
                classification.direction.value, classification.note,
                confirmed_at_utc=now, source="seeded",
            )
            report.outcomes_written += 1

    return report


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    dashboard_conn = dash_store.get_connection()
    backtest_conn = bt_store.get_connection()
    if dry_run:
        # Title-validation gate: a typo'd HistoricalEventFact.title would
        # otherwise silently fail to classify (classify_surprise() returns
        # None for any title not in EVENT_SURPRISE_DIRECTION, with no
        # error) — catch that here, before any write, rather than let it
        # pass through unnoticed.
        unrecognized = sorted({
            fact.title for fact in HISTORICAL_EVENTS
            if fact.title not in EVENT_SURPRISE_DIRECTION
        })
        if unrecognized:
            raise ValueError(
                f"[seed_historical_data] {len(unrecognized)} HistoricalEventFact title(s) "
                f"do not match any config.settings.EVENT_SURPRISE_DIRECTION key: {unrecognized}"
            )
        print(f"[seed_historical_data] DRY RUN — would process {len(HISTORICAL_EVENTS)} event facts, "
              f"all titles validated against EVENT_SURPRISE_DIRECTION, no writes.")
    else:
        report = run_seed(HISTORICAL_EVENTS, dashboard_conn, backtest_conn, list(INSTRUMENTS.keys()))
        print(f"[seed_historical_data] calendar_writes={report.calendar_writes} "
              f"predictions_written={report.predictions_written} predictions_skipped={report.predictions_skipped} "
              f"print_predictions_written={report.print_predictions_written} print_predictions_skipped={report.print_predictions_skipped} "
              f"outcomes_written={report.outcomes_written} outcomes_skipped={report.outcomes_skipped}")
        for reason in report.skip_reasons:
            print(f"[seed_historical_data] skipped: {reason}")
    dashboard_conn.close()
    backtest_conn.close()
