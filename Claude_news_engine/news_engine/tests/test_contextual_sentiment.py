"""
Tests the contextual sentiment tiers (FinBERT + Claude API fallback) added
to fix the lexicon's known failure mode: hedged/conditional language
scored as declarative (the June-NFP case in tests/run_historical_backtest.py
— "rate hike risk IF data surprises to upside" matched "rate hike" and
"hawkish" as if they'd already happened).

Deliberately NOT part of test_scoring_smoke.py — that file's whole point
is running with zero network access and zero extra dependencies. This
file needs `transformers`+`torch` installed (see
requirements-contextual.txt) and, for the LLM-tier tests, ANTHROPIC_API_KEY
set. Each test skips itself with a clear message rather than failing if
its tier isn't available — same graceful-degradation contract the
pipeline itself follows.

R2 (docs/fundamental-analysis-swot-2026-08-14.md): ENABLE_FINBERT_SENTIMENT
now defaults ON (config/settings.py) specifically so this tier's fix for
the hedged-language failure below is live by default, not opt-in — this
file's FinBERT test is the validation exercise R2 called for.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.finbert_sentiment import score_article_finbert, is_available as finbert_available
from scoring.llm_sentiment import score_article_llm, is_available as llm_available
from scoring.sentiment import score_article_text


def test_finbert_handles_hedged_language():
    print("=== FinBERT: hedged/conditional language should NOT score as declarative ===")
    if not finbert_available():
        print("SKIP — transformers/torch not installed (pip install -r requirements-contextual.txt)\n")
        return

    # The exact failure mode from the June-NFP backtest case (BACKTEST_REPORT.md
    # case #2): conditional framing ("risk IF... surprises"), not a statement
    # that a hike is coming. The lexicon scores this a flat +1.0 declarative
    # hawkish/USD-bullish read by matching "rate hike" verbatim — the one
    # documented wrong call in this project's only backtest.
    title = "Rate hike risk if jobs data surprises to upside"
    summary = "Equity and gold markets react primarily to shifting rate differentials from employment report"

    lexicon_result = score_article_text(title, summary)
    print(f"  lexicon: usd_score={lexicon_result.usd_score:+.2f} matched={lexicon_result.matched_terms}")
    assert lexicon_result.usd_score == 1.0, (
        "sanity check on the test text itself — if the lexicon no longer scores this "
        f"as a flat +1.0, the test text needs updating to still reproduce the known failure (got {lexicon_result.usd_score:+.2f})"
    )

    result = score_article_finbert(title, summary)
    print(f"  finbert: label={result.label} confidence={result.confidence:.2f} usd_score={result.usd_score:+.2f}")
    assert result is not None
    assert -1.0 <= result.usd_score <= 1.0
    # R2's actual bar: FinBERT must NOT reproduce the lexicon's blind
    # declarative +1.0 on hedged/conditional text — it doesn't need to land
    # on any specific value (its pos/neg axis is a documented simplification,
    # see config.settings), it just needs to visibly differ from "treat
    # 'rate hike risk IF...' as if the hike already happened."
    assert result.usd_score < 0.9, (
        f"FinBERT reproduced the lexicon's near-maximal declarative read ({result.usd_score:+.2f}) "
        "on hedged/conditional text — the hedged-language fix isn't actually landing"
    )
    print("PASS — FinBERT's read differs from the lexicon's blind declarative +1.0 on hedged text\n")


def test_llm_handles_hedged_language():
    print("=== Claude API: hedged/conditional language should score near-neutral, not declarative ===")
    if not llm_available():
        print("SKIP — ANTHROPIC_API_KEY not set or anthropic package missing\n")
        return

    result = score_article_llm(
        "Rate hike risk if jobs data surprises to upside",
        "Equity and gold markets react primarily to shifting rate differentials from employment report",
    )
    print(f"  usd_score={result.usd_score:+.2f} reasoning={result.reasoning!r}")
    assert result is not None
    # This IS the case the LLM tier was specifically built to get right —
    # a conditional "risk if X" is not the same as "X is happening", so
    # it should land closer to neutral than the lexicon's declarative +1.0.
    assert abs(result.usd_score) < 0.6, (
        f"hedged/conditional language should score closer to neutral, got {result.usd_score:+.2f}"
    )
    print("PASS\n")


def test_llm_handles_negation():
    print("=== Claude API: negation should flip the read, not just cancel to zero ===")
    if not llm_available():
        print("SKIP — ANTHROPIC_API_KEY not set or anthropic package missing\n")
        return

    result = score_article_llm(
        "Fed officials say they are not raising rates despite inflation pressure",
        "",
    )
    print(f"  usd_score={result.usd_score:+.2f} reasoning={result.reasoning!r}")
    assert result is not None
    assert result.usd_score < 0, "explicit 'not raising rates' should read as dovish/USD-bearish, not bullish"
    print("PASS\n")


if __name__ == "__main__":
    test_finbert_handles_hedged_language()
    test_llm_handles_hedged_language()
    test_llm_handles_negation()
    print("All contextual sentiment tests completed (see above for any SKIPs).")
