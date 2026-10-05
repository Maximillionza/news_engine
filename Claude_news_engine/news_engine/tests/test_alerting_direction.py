from __future__ import annotations

import pytest

from alerting import direction
from alerting.direction import (
    POLARITIES, describe_impacts, lean_for, normalize_polarity, rule_polarity,
)
from alerting.symbol_relevance import _CATEGORY_SYMBOL_CLASS_CHANNELS, affected_symbols
from alerting.taxonomy import HARD_RULE_PATTERNS


def test_every_hard_rule_pattern_has_a_deliberate_polarity():
    """These alerts skip the LLM, so a new taxonomy pattern without a direction decision must fail loudly."""
    all_patterns = {p for patterns in HARD_RULE_PATTERNS.values() for p in patterns}
    assert all_patterns == set(direction._RULE_POLARITY)
    assert set(direction._RULE_POLARITY.values()) <= set(POLARITIES)


@pytest.mark.parametrize("keywords,expected", [
    (["strait of hormuz closed"], "escalation"),
    (["opec+ agrees to increase"], "relief"),       # more supply is not an escalation
    (["opec+ agrees to cut"], "escalation"),
    (["unscheduled rate cut"], "dovish"),
    (["unscheduled rate hike"], "hawkish"),
    (["emergency rate decision"], "unclear"),       # direction not fixed by the phrase
    (["fed chair fired"], "unclear"),
    (["not a known pattern", "declares war"], "escalation"),  # first KNOWN pattern wins
    ([], "unclear"),
    (["something unmapped"], "unclear"),
])
def test_rule_polarity(keywords, expected):
    assert rule_polarity(keywords) == expected


@pytest.mark.parametrize("raw,expected", [
    ("escalation", "escalation"), ("Escalation", "escalation"), ("de-escalation", "relief"),
    ("de escalation", "relief"), ("easing", "relief"), ("worsening", "escalation"),
    ("HAWKISH", "hawkish"), ("dovish", "dovish"), ("unclear", "unclear"),
    ("bullish", "unclear"), ("", "unclear"), (None, "unclear"), (42, "unclear"),
])
def test_normalize_polarity(raw, expected):
    assert normalize_polarity(raw) == expected


def test_every_reported_category_and_class_has_a_deliberate_lean_for_each_relevant_polarity():
    """A missing cell would silently read 'no established direction' -- fine as a default, wrong as an oversight."""
    missing = []
    for category, classes in _CATEGORY_SYMBOL_CLASS_CHANNELS.items():
        polarities = ("hawkish", "dovish") if category == "central_bank" else ("escalation", "relief")
        # Classes where the category genuinely has no direction (which central bank? which currency?) are
        # allowed to fall through to 'mixed' on purpose.
        for symbol_class in list(classes) + (["oil_linked_fx"] if category == "energy" else []):
            if symbol_class in ("fx_usd_base", "fx_usd_quote"):
                continue
            for polarity in polarities:
                if (category, polarity, symbol_class) not in direction._LEAN_TABLE:
                    missing.append((category, polarity, symbol_class))
    assert missing == []


def test_lean_values_are_only_buy_sell_or_mixed_and_always_carry_a_reason():
    for lean in direction._LEAN_TABLE.values():
        assert lean.lean in ("buy", "sell", "mixed")
        assert lean.why.strip()


@pytest.mark.parametrize("category,polarity,symbol_class,expected", [
    ("energy", "escalation", "metal", "buy"),
    ("energy", "escalation", "index_risk", "sell"),
    ("energy", "escalation", "oil_linked_fx", "sell"),    # CAD strengthens as oil rises -> USDCAD falls
    ("energy", "relief", "oil_linked_fx", "buy"),
    ("energy", "relief", "index_risk", "buy"),
    ("energy", "relief", "metal", "mixed"),
    ("geopolitical_conflict", "escalation", "metal", "buy"),
    ("geopolitical_conflict", "escalation", "index_risk", "sell"),
    ("central_bank", "hawkish", "metal", "mixed"),        # Layer2: gold/rates link unreliable since 2024
    ("central_bank", "hawkish", "index_risk", "sell"),
    ("central_bank", "dovish", "index_risk", "mixed"),    # Layer2: soft landing vs recession fear
    ("central_bank", "hawkish", "fx_usd_quote", "mixed"), # which central bank is unknown
    ("trade_policy", "escalation", "index_risk", "sell"),
    ("trade_policy", "relief", "index_risk", "buy"),
])
def test_lean_for_known_cells(category, polarity, symbol_class, expected):
    assert lean_for(category, polarity, symbol_class).lean == expected


def test_unclear_polarity_is_always_mixed_never_a_guess():
    for (category, _polarity, symbol_class) in direction._LEAN_TABLE:
        lean = lean_for(category, "unclear", symbol_class)
        assert lean.lean == "mixed"
        assert "unclear" in lean.why


def test_unknown_combination_is_mixed_not_an_error():
    assert lean_for("not_a_category", "escalation", "metal").lean == "mixed"


def test_describe_impacts_attaches_lean_and_reason_to_each_tracked_symbol():
    impacts = affected_symbols("energy", ["XAUUSD", "US30", "USDCAD"])
    described = {d["symbol"]: d for d in describe_impacts(impacts, "energy", "escalation")}
    assert described["XAUUSD"]["lean"] == "buy"
    assert described["US30"]["lean"] == "sell"
    assert described["USDCAD"]["lean"] == "sell"
    assert described["XAUUSD"]["channel"] == "safe_haven"
    assert all(d["lean_why"] for d in described.values())

    relief = {d["symbol"]: d["lean"] for d in describe_impacts(impacts, "energy", "relief")}
    assert relief == {"XAUUSD": "mixed", "US30": "buy", "USDCAD": "buy"}


def test_describe_impacts_with_no_tracked_relevance_is_empty():
    assert describe_impacts([], "energy", "escalation") == []
