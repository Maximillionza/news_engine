"""
Backtest module.

Two ways to run a backtest case:

1. fetch-based (run_backtest_case): pulls real pre-event articles from your
   configured news sources via event_context.build_event_news_bundle() in
   'backtest' mode, which enforces the no-lookahead cutoff. This is the
   real, production path — use this once you have API keys and are running
   outside a network-restricted sandbox.

2. manual (run_backtest_case_manual): takes a pre-built list of NewsArticle
   objects instead of fetching. Useful for reconstructing a historical case
   from research (e.g. real reported pre-event sentiment pulled via web
   search) when live source access isn't available, or for unit-testing the
   backtest harness itself without network calls.

Either way, the case is scored through the exact same scoring.probability_engine
pipeline used live — no separate "backtest scoring logic" to keep in sync.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle, build_event_news_bundle
from data_layer.news_feed import NewsArticle, NewsSource
from scoring.probability_engine import Direction, ProbabilityResult, score_bundle


@dataclass
class BacktestCase:
    event: EconomicEvent
    instrument: str
    actual_direction: Direction        # what gold/US30 actually did after the release
    actual_move_note: str = ""         # optional human-readable context, e.g. "+1.2% in 30min"
    result: ProbabilityResult | None = None
    predicted_correct: bool | None = None

    def evaluate(self) -> None:
        if self.result is None:
            raise RuntimeError("evaluate() called before the case was scored")
        if self.result.direction == Direction.NEUTRAL:
            self.predicted_correct = None  # no call made — doesn't count as right or wrong
        else:
            self.predicted_correct = self.result.direction == self.actual_direction

    def describe(self) -> str:
        pred = self.result.direction.value.upper() if self.result else "N/A"
        actual = self.actual_direction.value.upper()
        verdict = {True: "✅ CORRECT", False: "❌ WRONG", None: "— NO CALL"}[self.predicted_correct]
        prob = f"{self.result.probability:.0%}" if self.result else "n/a"
        conf = f"{self.result.confidence:.0%}" if self.result else "n/a"
        flag = " ⚠ contradiction flagged" if (self.result and self.result.contradiction_flag) else ""
        return (
            f"{self.event.title} ({self.event.event_time_local.strftime('%Y-%m-%d')}) "
            f"[{self.instrument}]: predicted={pred} ({prob} prob, {conf} conf) "
            f"actual={actual} {self.actual_move_note} -> {verdict}{flag}"
        )


def run_backtest_case(
    event: EconomicEvent,
    sources: list[NewsSource],
    query: str,
    instrument: str,
    actual_direction: Direction,
    actual_move_note: str = "",
    precursor_events: list[EconomicEvent] | None = None,
) -> BacktestCase:
    """
    Production path — fetches real pre-event articles from live sources.

    precursor_events: optional leading-indicator events already released
    ahead of `event` (build with data_layer.calendar_feed.find_precursor_events()
    against the full, unfiltered calendar — the high-impact-only filter
    used for the target event would exclude these, since precursors like
    ADP are typically Medium impact).
    """
    bundle = build_event_news_bundle(event, sources, query, mode="backtest")
    case = BacktestCase(
        event=event, instrument=instrument,
        actual_direction=actual_direction, actual_move_note=actual_move_note,
    )
    case.result = score_bundle(bundle, instrument, precursor_events=precursor_events)
    case.evaluate()
    return case


def run_backtest_case_manual(
    event: EconomicEvent,
    articles: list[NewsArticle],
    instrument: str,
    actual_direction: Direction,
    actual_move_note: str = "",
) -> BacktestCase:
    """
    Manual path — scores a pre-built article list instead of fetching.
    Still enforces the no-lookahead rule: any article published after the
    event time is dropped before scoring, same guarantee the fetch-based
    path gets from build_event_news_bundle().
    """
    pre_event_only = [a for a in articles if a.published_utc <= event.event_time_utc]
    dropped = len(articles) - len(pre_event_only)
    if dropped:
        print(f"[backtest] WARNING: dropped {dropped} article(s) published after event time — lookahead leak prevented")

    bundle = EventNewsBundle(event=event, articles=pre_event_only, as_of_utc=event.event_time_utc)
    case = BacktestCase(
        event=event, instrument=instrument,
        actual_direction=actual_direction, actual_move_note=actual_move_note,
    )
    case.result = score_bundle(bundle, instrument)
    case.evaluate()
    return case


@dataclass
class BacktestReport:
    cases: list[BacktestCase] = field(default_factory=list)

    def add(self, case: BacktestCase) -> None:
        self.cases.append(case)

    def accuracy(self) -> float | None:
        """Accuracy over cases where the engine actually made a directional call (excludes NEUTRAL no-calls)."""
        scored = [c for c in self.cases if c.predicted_correct is not None]
        if not scored:
            return None
        correct = sum(1 for c in scored if c.predicted_correct)
        return correct / len(scored)

    def call_rate(self) -> float:
        """Fraction of cases where the engine made a directional call at all, vs staying neutral."""
        if not self.cases:
            return 0.0
        called = sum(1 for c in self.cases if c.predicted_correct is not None)
        return called / len(self.cases)

    def contradiction_rate(self) -> float:
        flagged = sum(1 for c in self.cases if c.result and c.result.contradiction_flag)
        return flagged / len(self.cases) if self.cases else 0.0

    def print_report(self) -> None:
        print(f"{'=' * 70}\nBACKTEST REPORT — {len(self.cases)} events\n{'=' * 70}")
        for case in self.cases:
            print(case.describe())

        acc = self.accuracy()
        print(f"\n{'-' * 70}")
        print(f"Directional calls made: {self.call_rate():.0%} of events")
        print(f"Accuracy on calls made: {acc:.0%}" if acc is not None else "Accuracy: n/a (no directional calls made)")
        print(f"Contradiction flagged:  {self.contradiction_rate():.0%} of events")
        print(f"{'-' * 70}")


def build_real_backtest_report(db_path: Optional[Path] = None) -> BacktestReport:
    """
    Builds a BacktestReport from the article-based accumulator's real,
    confirmed (prediction, outcome) pairs — scoring/backtest_store.py's
    running log. Same report shape as the reconstructed backtest
    (tests/run_historical_backtest.py), so real and reconstructed
    results are directly comparable via the same print_report() output.
    """
    from scoring.backtest_store import get_all_confirmed_cases, get_connection

    conn = get_connection(db_path)
    confirmed = get_all_confirmed_cases(conn)
    conn.close()

    report = BacktestReport()
    for prediction, outcome in confirmed:
        event = EconomicEvent(
            title=prediction.event_title, country="USD", impact="High",
            event_time_utc=dt.datetime.fromisoformat(prediction.event_time_utc),
        )
        case = BacktestCase(
            event=event, instrument=prediction.instrument,
            actual_direction=Direction(outcome.actual_direction),
            actual_move_note=outcome.actual_move_note,
        )
        case.result = ProbabilityResult(
            instrument=prediction.instrument,
            as_of_utc=dt.datetime.fromisoformat(prediction.scored_at_utc),
            aggregate_usd_sentiment=0.0, instrument_score=0.0,
            probability=prediction.probability, direction=Direction(prediction.direction),
            confidence=prediction.confidence, article_count=prediction.article_count,
            contradiction_flag=prediction.contradiction_flag, contradiction_note=None,
        )
        case.evaluate()
        report.add(case)
    return report
