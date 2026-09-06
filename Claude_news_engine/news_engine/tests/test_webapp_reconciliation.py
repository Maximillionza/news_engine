"""
Tests for webapp/reconciliation.py's reconcile_group() — a pure function
over already-fetched Prediction rows, no DB, no network. See
docs/superpowers/specs/2026-09-04-co-released-event-reconciliation-design.md
for the algorithm this implements.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.backtest_store import Prediction
from webapp.reconciliation import reconcile_group, ReconciledCall


def _pred(title, direction, probability, confidence, instrument="US30", article_count=100):
    return Prediction(
        id=1, event_title=title, instrument=instrument, event_time_utc="2026-09-04T12:30:00+00:00",
        scored_at_utc="2026-09-04T06:00:00+00:00", probability=probability, direction=direction,
        confidence=confidence, article_count=article_count, contradiction_flag=False, source="live",
    )


def test_single_real_call_returns_none():
    print("=== reconcile_group: only one non-neutral title in the group -> nothing to reconcile, caller falls through ===")
    result = reconcile_group({
        "Non-Farm Employment Change": _pred("Non-Farm Employment Change", "bullish", 0.60, 0.30),
        "Unemployment Rate": _pred("Unemployment Rate", "neutral", 0.50, 0.0),
    })
    assert result is None
    print("PASS\n")


def test_all_neutral_returns_none():
    print("=== reconcile_group: every co-released title is neutral -> nothing to reconcile (falls through to plain neutral display) ===")
    result = reconcile_group({
        "Non-Farm Employment Change": _pred("Non-Farm Employment Change", "neutral", 0.50, 0.0),
        "Unemployment Rate": _pred("Unemployment Rate", "neutral", 0.50, 0.0),
    })
    assert result is None
    print("PASS\n")


def test_unanimous_agreement_returns_highest_confidence_titles_own_prediction():
    print("=== reconcile_group: every non-neutral title agrees on direction -> no conflict, the highest-confidence title's own prediction is returned untouched ===")
    dominant = _pred("Non-Farm Employment Change", "bullish", 0.70, 0.55, article_count=136)
    weaker_agree = _pred("Average Hourly Earnings m/m", "bullish", 0.55, 0.20)
    result = reconcile_group({
        "Non-Farm Employment Change": dominant,
        "Average Hourly Earnings m/m": weaker_agree,
    })
    assert result is not None
    assert result.conflict is False
    assert result.prediction is dominant  # exact same object -- never a synthetic blend
    assert result.prediction.article_count == 136
    print("PASS\n")


def test_real_2026_09_04_case_is_a_conflict():
    print("=== reconcile_group: the real 2026-09-04 occurrence (US30 bullish/bullish/bearish across NFP/AHE/Unemployment Rate) resolves as a genuine conflict ===")
    # Real confidence/probability values recorded live for this exact
    # occurrence (US30, 2026-09-04T12:30 UTC) -- see this plan's Task 2
    # for the matching /api/predictions-level regression test. Note:
    # NFP+AHE's COMBINED confidence (0.53+0.54) exceeds Unemployment
    # Rate's alone (0.37) -- an earlier, confidence-weighted design for
    # this function let that combined weight silently outvote the
    # dissenting title and call this "no conflict". The real subsequent
    # price move (XAUUSD -1.73%, bearish) agreed with the OUTVOTED
    # minority title, not the higher-combined-confidence pair -- which is
    # exactly why this function uses strict unanimity instead of a
    # confidence contest (see the design spec's 2026-09-05 revision).
    nfp = _pred("Non-Farm Employment Change", "bullish", 0.4697793269246527, 0.5314798614615047)
    ahe = _pred("Average Hourly Earnings m/m", "bullish", 0.46705663115758544, 0.536405991676083)
    unemployment_rate = _pred("Unemployment Rate", "bearish", 0.4495123783660442, 0.3705108141070306)
    result = reconcile_group({
        "Non-Farm Employment Change": nfp,
        "Average Hourly Earnings m/m": ahe,
        "Unemployment Rate": unemployment_rate,
    })
    assert result is not None
    assert result.conflict is True
    assert set(result.conflicting_titles) == {
        "Non-Farm Employment Change", "Average Hourly Earnings m/m", "Unemployment Rate",
    }
    print("PASS\n")


def test_a_single_dissenting_title_is_still_a_conflict_regardless_of_confidence_gap():
    print("=== reconcile_group: one low-confidence dissenting title is STILL a conflict, even against two much-higher-confidence agreeing titles -- no confidence contest overrules a real disagreement ===")
    strong_bullish_1 = _pred("Title A", "bullish", 0.75, 0.60)
    strong_bullish_2 = _pred("Title B", "bullish", 0.72, 0.58)
    weak_bearish = _pred("Title C", "bearish", 0.48, 0.05)
    result = reconcile_group({
        "Title A": strong_bullish_1, "Title B": strong_bullish_2, "Title C": weak_bearish,
    })
    assert result is not None
    assert result.conflict is True
    assert set(result.conflicting_titles) == {"Title A", "Title B", "Title C"}
    print("PASS\n")


def test_neutral_titles_never_block_agreement_among_the_real_calls():
    print("=== reconcile_group: neutral titles in the group are irrelevant to agreement -- two agreeing non-neutral titles plus a neutral one is still no conflict ===")
    dominant = _pred("Title A", "bullish", 0.65, 0.50)
    agrees = _pred("Title B", "bullish", 0.55, 0.20)
    neutral = _pred("Title C", "neutral", 0.50, 0.0)
    result = reconcile_group({"Title A": dominant, "Title B": agrees, "Title C": neutral})
    assert result is not None
    assert result.conflict is False
    assert result.prediction is dominant
    print("PASS\n")


def test_empty_input_returns_none():
    print("=== reconcile_group: an empty group (e.g. every title excluded upstream for a malformed row) is handled the same as 'nothing to reconcile' ===")
    result = reconcile_group({})
    assert result is None
    print("PASS\n")


if __name__ == "__main__":
    test_single_real_call_returns_none()
    test_all_neutral_returns_none()
    test_unanimous_agreement_returns_highest_confidence_titles_own_prediction()
    test_real_2026_09_04_case_is_a_conflict()
    test_a_single_dissenting_title_is_still_a_conflict_regardless_of_confidence_gap()
    test_neutral_titles_never_block_agreement_among_the_real_calls()
    test_empty_input_returns_none()
    print("All tests passed!")
