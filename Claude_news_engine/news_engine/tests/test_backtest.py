"""
Tests for scoring/backtest.py — the Causation-Matrix Option A extension
(docs/News_Engine_Causation_Matrix_v1.xlsx, 2026-09-06): a Tier 1
comparison prediction carried alongside sentiment's own ProbabilityResult
on BacktestCase, plus BacktestReport's new tier1_accuracy()/
tier1_call_rate()/agreement_rate() metrics. No network needed — all
cases are built directly via BacktestCase/Tier1Prediction, not through
run_backtest_case's live-fetch path.

Every test here also asserts sentiment's own existing fields/behavior are
completely untouched by tier1's presence — this is a comparison
capability, not a replacement (per the design brief), and that must hold
whether or not a case carries a tier1 prediction.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime as dt

from config.settings import UTC_TZ
from data_layer.calendar_feed import EconomicEvent
from scoring.backtest import BacktestCase, BacktestReport, Tier1Prediction
from scoring.probability_engine import Direction, ProbabilityResult


def _event(title="CPI m/m"):
    return EconomicEvent(
        title=title, country="USD", impact="High",
        event_time_utc=dt.datetime(2026, 9, 11, 12, 30, tzinfo=UTC_TZ),
    )


def _sentiment_result(direction: Direction, probability: float = 0.6, confidence: float = 0.5) -> ProbabilityResult:
    return ProbabilityResult(
        instrument="XAUUSD", as_of_utc=dt.datetime(2026, 9, 11, 6, 0, tzinfo=UTC_TZ),
        aggregate_usd_sentiment=0.0, instrument_score=0.0,
        probability=probability, direction=direction, confidence=confidence,
        article_count=10, contradiction_flag=False, contradiction_note=None,
    )


def test_backtest_case_without_tier1_behaves_exactly_as_before():
    print("=== BacktestCase: no tier1 supplied -> tier1 fields stay None, evaluate()/describe() unaffected ===")
    case = BacktestCase(
        event=_event(), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.BULLISH),
    )
    case.evaluate()
    assert case.tier1 is None
    assert case.tier1_predicted_correct is None
    assert case.predicted_correct is True
    assert "Tier 1" not in case.describe()
    print("PASS\n")


def test_tier1_prediction_carries_value_confidence_and_source_distinctly():
    print("=== Tier1Prediction: value/confidence/source are three distinct fields, never collapsed into one number ===")
    t1 = Tier1Prediction(
        value="Headline m/m +0.36%, core m/m +0.20%; headline y/y 3.38%, core y/y 2.38%",
        confidence="Certain",
        source="Cleveland Fed live nowcast (clevelandfed.org/inflation-nowcasting)",
        predicted_direction=Direction.BULLISH,
    )
    assert isinstance(t1.value, str)
    assert t1.confidence == "Certain"
    assert t1.confidence in ("Certain", "Likely", "Guessing")
    assert t1.source.startswith("Cleveland Fed")
    assert t1.predicted_direction == Direction.BULLISH
    print("PASS\n")


def test_tier1_correct_call_evaluated_against_actual():
    print("=== BacktestCase.evaluate(): tier1_predicted_correct compares tier1's own direction against actual, independent of sentiment ===")
    t1 = Tier1Prediction(
        value="muted-to-modest, not sharply reaccelerating", confidence="Certain",
        source="BLS July 2026 PPI release + ISM Manufacturing Prices Paid (Aug 2026, 71.1)",
        predicted_direction=Direction.BEARISH,
    )
    # Sentiment calls bullish, Tier 1 calls bearish, actual is bearish —
    # sentiment should be WRONG while Tier 1 is CORRECT, proving the two
    # are evaluated completely independently.
    case = BacktestCase(
        event=_event("PPI m/m"), instrument="XAUUSD", actual_direction=Direction.BEARISH,
        result=_sentiment_result(Direction.BULLISH), tier1=t1,
    )
    case.evaluate()
    assert case.predicted_correct is False
    assert case.tier1_predicted_correct is True
    print("PASS\n")


def test_tier1_neutral_direction_is_no_call_not_wrong():
    print("=== BacktestCase.evaluate(): a NEUTRAL tier1.predicted_direction is a no-call (None), never scored right or wrong — same convention as sentiment's own NEUTRAL handling ===")
    t1 = Tier1Prediction(
        value="no clear signal", confidence="Guessing",
        source="placeholder", predicted_direction=Direction.NEUTRAL,
    )
    case = BacktestCase(
        event=_event(), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.NEUTRAL), tier1=t1,
    )
    case.evaluate()
    assert case.predicted_correct is None
    assert case.tier1_predicted_correct is None
    print("PASS\n")


def test_describe_includes_tier1_line_when_present():
    print("=== BacktestCase.describe(): includes a Tier 1 line (confidence, source, value, verdict) only when tier1 is set ===")
    t1 = Tier1Prediction(
        value="Headline m/m +0.36%", confidence="Certain",
        source="Cleveland Fed live nowcast", predicted_direction=Direction.BULLISH,
    )
    case = BacktestCase(
        event=_event(), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.BULLISH), tier1=t1,
    )
    case.evaluate()
    description = case.describe()
    assert "Tier 1" in description
    assert "Certain" in description
    assert "Cleveland Fed live nowcast" in description
    assert "Headline m/m +0.36%" in description
    print("PASS\n")


def test_report_tier1_metrics_are_none_or_zero_with_no_tier1_cases():
    print("=== BacktestReport: tier1_accuracy/agreement_rate return None, tier1_call_rate returns 0.0, when no case carries a tier1 prediction — sentiment-only reports unaffected ===")
    report = BacktestReport()
    case = BacktestCase(
        event=_event(), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.BULLISH),
    )
    case.evaluate()
    report.add(case)

    assert report.tier1_accuracy() is None
    assert report.tier1_call_rate() == 0.0
    assert report.agreement_rate() is None
    # Sentiment's own existing metrics still work exactly as before.
    assert report.accuracy() == 1.0
    print("PASS\n")


def test_report_agreement_rate_counts_only_comparable_cases():
    print("=== BacktestReport.agreement_rate(): scoped to cases where BOTH sentiment and tier1 made a real (non-neutral) call; measures agreement with each other, independent of correctness ===")
    report = BacktestReport()

    # Case 1: both bullish -> agree (both happen to be wrong against actual, irrelevant to agreement).
    t1_agree = Tier1Prediction(value="v1", confidence="Certain", source="s1", predicted_direction=Direction.BULLISH)
    case1 = BacktestCase(
        event=_event("CPI m/m"), instrument="XAUUSD", actual_direction=Direction.BEARISH,
        result=_sentiment_result(Direction.BULLISH), tier1=t1_agree,
    )
    case1.evaluate()
    report.add(case1)

    # Case 2: sentiment bullish, tier1 bearish -> disagree.
    t1_disagree = Tier1Prediction(value="v2", confidence="Certain", source="s2", predicted_direction=Direction.BEARISH)
    case2 = BacktestCase(
        event=_event("PPI m/m"), instrument="XAUUSD", actual_direction=Direction.BEARISH,
        result=_sentiment_result(Direction.BULLISH), tier1=t1_disagree,
    )
    case2.evaluate()
    report.add(case2)

    # Case 3: sentiment stays neutral -> not comparable, must not count either way.
    t1_neutral_partner = Tier1Prediction(value="v3", confidence="Likely", source="s3", predicted_direction=Direction.BULLISH)
    case3 = BacktestCase(
        event=_event("CPI m/m"), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.NEUTRAL), tier1=t1_neutral_partner,
    )
    case3.evaluate()
    report.add(case3)

    # Case 4: no tier1 at all -> must not count either way.
    case4 = BacktestCase(
        event=_event("PPI m/m"), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.BULLISH),
    )
    case4.evaluate()
    report.add(case4)

    # Only cases 1 and 2 are comparable: 1 agreement out of 2 -> 50%.
    assert report.agreement_rate() == 0.5
    print("PASS\n")


def test_report_tier1_accuracy_and_call_rate():
    print("=== BacktestReport.tier1_accuracy()/tier1_call_rate(): computed the same way sentiment's own accuracy()/call_rate() are, scoped to tier1-carrying cases ===")
    report = BacktestReport()

    correct = Tier1Prediction(value="v", confidence="Certain", source="s", predicted_direction=Direction.BULLISH)
    case1 = BacktestCase(
        event=_event("CPI m/m"), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.BULLISH), tier1=correct,
    )
    case1.evaluate()
    report.add(case1)

    wrong = Tier1Prediction(value="v", confidence="Likely", source="s", predicted_direction=Direction.BEARISH)
    case2 = BacktestCase(
        event=_event("PPI m/m"), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.BULLISH), tier1=wrong,
    )
    case2.evaluate()
    report.add(case2)

    neutral = Tier1Prediction(value="v", confidence="Guessing", source="s", predicted_direction=Direction.NEUTRAL)
    case3 = BacktestCase(
        event=_event("CPI m/m"), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.BULLISH), tier1=neutral,
    )
    case3.evaluate()
    report.add(case3)

    # call_rate: 2 of 3 tier1-carrying cases made a real call (case3 stayed neutral).
    assert report.tier1_call_rate() == 2 / 3
    # accuracy: 1 correct of 2 calls made.
    assert report.tier1_accuracy() == 0.5
    print("PASS\n")


def test_print_report_omits_tier1_section_when_no_case_has_it(capsys):
    print("=== BacktestReport.print_report(): output is unchanged from before this extension when no case carries a tier1 prediction ===")
    report = BacktestReport()
    case = BacktestCase(
        event=_event(), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.BULLISH),
    )
    case.evaluate()
    report.add(case)
    report.print_report()
    output = capsys.readouterr().out
    assert "Tier 1" not in output
    print("PASS\n")


def test_print_report_includes_tier1_section_when_present(capsys):
    print("=== BacktestReport.print_report(): prints the Tier 1 comparison block when at least one case carries a tier1 prediction ===")
    report = BacktestReport()
    t1 = Tier1Prediction(value="v", confidence="Certain", source="s", predicted_direction=Direction.BULLISH)
    case = BacktestCase(
        event=_event(), instrument="XAUUSD", actual_direction=Direction.BULLISH,
        result=_sentiment_result(Direction.BULLISH), tier1=t1,
    )
    case.evaluate()
    report.add(case)
    report.print_report()
    output = capsys.readouterr().out
    assert "Tier 1 accuracy" in output
    assert "Sentiment/Tier 1 agreement" in output
    print("PASS\n")


if __name__ == "__main__":
    test_backtest_case_without_tier1_behaves_exactly_as_before()
    test_tier1_prediction_carries_value_confidence_and_source_distinctly()
    test_tier1_correct_call_evaluated_against_actual()
    test_tier1_neutral_direction_is_no_call_not_wrong()
    test_describe_includes_tier1_line_when_present()
    test_report_tier1_metrics_are_none_or_zero_with_no_tier1_cases()
    test_report_agreement_rate_counts_only_comparable_cases()
    test_report_tier1_accuracy_and_call_rate()
    print("All non-capsys tests passed! (Run via pytest for the capsys-based print_report tests.)")
