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
from typing import Literal, Optional

from data_layer.calendar_feed import EconomicEvent
from data_layer.event_context import EventNewsBundle, build_event_news_bundle
from data_layer.news_feed import NewsArticle, NewsSource
from scoring.probability_engine import Direction, ProbabilityResult, score_bundle

# Causation-Matrix Option A (docs/News_Engine_Causation_Matrix_v1.xlsx,
# 2026-09-06): a Tier 1 causation-matrix reading, kept as a COMPARISON
# prediction alongside sentiment's own ProbabilityResult — never a
# replacement. Sentiment's existing path (result/predicted_correct) is
# completely unchanged by this; tier1/tier1_predicted_correct below are
# purely additive and both default to None.
#
# Confidence is a tag, not a number: Certain/Likely/Guessing, exactly as
# the workbook rates each Tier 1 source (e.g. CPI's Cleveland Fed nowcast
# is Certain; PPI's ISM Manufacturing Prices Paid is Certain specifically
# for PPI, per the Cleveland Fed study that found it does NOT predict
# CPI). Collapsing this to a numeric score in place of the tag would be
# the exact "reduces this to a single float" spec violation flagged
# during design — this dataclass exists specifically so that never
# happens by construction.
Tier1Confidence = Literal["Certain", "Likely", "Guessing"]


@dataclass(frozen=True)
class Tier1Prediction:
    """
    A single Tier 1 causation-matrix reading for one historical event
    occurrence, exactly as its source stated it — never coerced into a
    shape a given methodology doesn't actually produce. CPI's Tier 1
    (Cleveland Fed nowcast) yields four numbers (headline/core m/m and
    y/y); PPI's Tier 1 (BLS's own release + ISM Manufacturing Prices
    Paid, per the POC sheet's Tier 1 rows — NOT the Tier 1.5/Likely
    regional Fed survey) currently yields a directional judgment with no
    number at all. `value` is a free-text field precisely so both are
    representable honestly, with nothing invented to fill a numeric slot
    the underlying methodology doesn't have.
    """
    value: str          # the raw reading, verbatim as the source stated it
    confidence: Tier1Confidence
    source: str          # citation — which real source produced this reading

    # predicted_direction is MANUALLY SUPPLIED and is NOT the output of
    # a validated methodology. A real consolidation methodology for
    # combining multi-part event readings (e.g. CPI's headline vs core,
    # which have genuinely diverged before — see the July 2025 CPI row
    # in Layer1_Event_to_USD, where headline missed/dovish and core
    # beat/hawkish at the same release) into one series-level direction
    # does not exist yet and is a separate, queued build item. Treat any
    # value in this field as a placeholder judgment call, not a
    # validated signal. Nothing in this module derives this value from
    # `value` above — that derivation is deliberately out of scope here.
    predicted_direction: Direction


@dataclass
class BacktestCase:
    event: EconomicEvent
    instrument: str
    actual_direction: Direction        # what gold/US30 actually did after the release
    actual_move_note: str = ""         # optional human-readable context, e.g. "+1.2% in 30min"
    result: ProbabilityResult | None = None
    predicted_correct: bool | None = None

    # Causation-Matrix Option A comparison prediction — see
    # Tier1Prediction's docstring. Both default to None so every
    # existing sentiment-only caller (run_backtest_case,
    # run_backtest_case_manual, build_real_backtest_report) is
    # completely unaffected.
    tier1: Tier1Prediction | None = None
    tier1_predicted_correct: bool | None = None

    def evaluate(self) -> None:
        if self.result is None:
            raise RuntimeError("evaluate() called before the case was scored")
        if self.result.direction == Direction.NEUTRAL:
            self.predicted_correct = None  # no call made — doesn't count as right or wrong
        else:
            self.predicted_correct = self.result.direction == self.actual_direction

        if self.tier1 is not None:
            if self.tier1.predicted_direction == Direction.NEUTRAL:
                self.tier1_predicted_correct = None  # no call made — same convention as sentiment above
            else:
                self.tier1_predicted_correct = self.tier1.predicted_direction == self.actual_direction

    def describe(self) -> str:
        pred = self.result.direction.value.upper() if self.result else "N/A"
        actual = self.actual_direction.value.upper()
        verdict = {True: "✅ CORRECT", False: "❌ WRONG", None: "— NO CALL"}[self.predicted_correct]
        prob = f"{self.result.probability:.0%}" if self.result else "n/a"
        conf = f"{self.result.confidence:.0%}" if self.result else "n/a"
        flag = " ⚠ contradiction flagged" if (self.result and self.result.contradiction_flag) else ""
        line = (
            f"{self.event.title} ({self.event.event_time_local.strftime('%Y-%m-%d')}) "
            f"[{self.instrument}]: predicted={pred} ({prob} prob, {conf} conf) "
            f"actual={actual} {self.actual_move_note} -> {verdict}{flag}"
        )
        if self.tier1 is not None:
            t1_pred = self.tier1.predicted_direction.value.upper()
            t1_verdict = {True: "✅ CORRECT", False: "❌ WRONG", None: "— NO CALL"}[self.tier1_predicted_correct]
            line += (
                f"\n    Tier 1 ({self.tier1.confidence}, {self.tier1.source}): "
                f"\"{self.tier1.value}\" -> predicted={t1_pred} -> {t1_verdict}"
            )
        return line


def run_backtest_case(
    event: EconomicEvent,
    sources: list[NewsSource],
    query: str,
    instrument: str,
    actual_direction: Direction,
    actual_move_note: str = "",
    precursor_events: list[EconomicEvent] | None = None,
    tier1: Tier1Prediction | None = None,
) -> BacktestCase:
    """
    Production path — fetches real pre-event articles from live sources.

    precursor_events: optional leading-indicator events already released
    ahead of `event` (build with scoring.probability_engine.get_precursor_events_for()
    against the dashboard's persisted event_history — precursors like ADP
    are typically Medium impact, so this is unaffected by any high-impact-only
    filter used for the target event's own candidate list).

    tier1: optional Causation-Matrix Option A comparison prediction (see
    Tier1Prediction) — sentiment's own scoring above is completely
    unaffected whether this is supplied or not.
    """
    bundle = build_event_news_bundle(event, sources, query, mode="backtest")
    case = BacktestCase(
        event=event, instrument=instrument,
        actual_direction=actual_direction, actual_move_note=actual_move_note,
        tier1=tier1,
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
    tier1: Tier1Prediction | None = None,
) -> BacktestCase:
    """
    Manual path — scores a pre-built article list instead of fetching.
    Still enforces the no-lookahead rule: any article published after the
    event time is dropped before scoring, same guarantee the fetch-based
    path gets from build_event_news_bundle().

    tier1: optional Causation-Matrix Option A comparison prediction (see
    Tier1Prediction) — sentiment's own scoring below is completely
    unaffected whether this is supplied or not.
    """
    pre_event_only = [a for a in articles if a.published_utc <= event.event_time_utc]
    dropped = len(articles) - len(pre_event_only)
    if dropped:
        print(f"[backtest] WARNING: dropped {dropped} article(s) published after event time — lookahead leak prevented")

    bundle = EventNewsBundle(event=event, articles=pre_event_only, as_of_utc=event.event_time_utc)
    case = BacktestCase(
        event=event, instrument=instrument,
        actual_direction=actual_direction, actual_move_note=actual_move_note,
        tier1=tier1,
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

    # --- Causation-Matrix Option A: Tier 1 comparison metrics ---
    # All three mirror the sentiment-only metrics above exactly, scoped to
    # cases that actually carry a tier1 prediction. A case with no tier1
    # set contributes to none of these — sentiment-only reports (every
    # existing caller) see these methods return None/0.0 on an empty
    # tier1 population, same "n/a, not fabricated" contract accuracy()
    # already uses.

    def tier1_accuracy(self) -> float | None:
        """Tier 1's own accuracy, over cases where it made a directional call (excludes NEUTRAL no-calls)."""
        scored = [c for c in self.cases if c.tier1_predicted_correct is not None]
        if not scored:
            return None
        correct = sum(1 for c in scored if c.tier1_predicted_correct)
        return correct / len(scored)

    def tier1_call_rate(self) -> float:
        """Fraction of tier1-carrying cases where Tier 1 made a directional call at all, vs staying neutral."""
        with_tier1 = [c for c in self.cases if c.tier1 is not None]
        if not with_tier1:
            return 0.0
        called = sum(1 for c in with_tier1 if c.tier1_predicted_correct is not None)
        return called / len(with_tier1)

    def agreement_rate(self) -> float | None:
        """
        How often sentiment's own call and Tier 1's own call point the
        SAME direction — independent of whether either was actually
        correct. This is the actual point of carrying two predictions
        side by side: it answers "do these two independently-built
        predictors agree," not "which one is right." Scoped to cases
        where BOTH made a real (non-neutral) call; a case where either
        stayed neutral contributes nothing here (no directional claim to
        compare). None (not 0.0) when no such case exists — same "n/a,
        not fabricated" contract as accuracy().
        """
        comparable = [
            c for c in self.cases
            if c.tier1 is not None
            and c.result is not None
            and c.result.direction != Direction.NEUTRAL
            and c.tier1.predicted_direction != Direction.NEUTRAL
        ]
        if not comparable:
            return None
        agreeing = sum(1 for c in comparable if c.result.direction == c.tier1.predicted_direction)
        return agreeing / len(comparable)

    def print_report(self) -> None:
        print(f"{'=' * 70}\nBACKTEST REPORT — {len(self.cases)} events\n{'=' * 70}")
        for case in self.cases:
            print(case.describe())

        acc = self.accuracy()
        print(f"\n{'-' * 70}")
        print(f"Directional calls made: {self.call_rate():.0%} of events")
        print(f"Accuracy on calls made: {acc:.0%}" if acc is not None else "Accuracy: n/a (no directional calls made)")
        print(f"Contradiction flagged:  {self.contradiction_rate():.0%} of events")

        # Causation-Matrix Option A metrics — only printed when at least
        # one case in this report actually carries a tier1 prediction, so
        # a sentiment-only report's output is byte-identical to before
        # this extension existed.
        if any(c.tier1 is not None for c in self.cases):
            t1_acc = self.tier1_accuracy()
            agreement = self.agreement_rate()
            print(f"{'-' * 70}")
            print(f"Tier 1 calls made:      {self.tier1_call_rate():.0%} of tier1-carrying events")
            print(f"Tier 1 accuracy:        {t1_acc:.0%}" if t1_acc is not None else "Tier 1 accuracy: n/a (no directional calls made)")
            print(f"Sentiment/Tier 1 agreement: {agreement:.0%}" if agreement is not None else "Sentiment/Tier 1 agreement: n/a (no comparable calls)")
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
