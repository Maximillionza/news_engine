from __future__ import annotations

import pytest

from alerting import direction
from alerting.direction import (
    NO_US_LINK_WHY, POLARITIES, Lean, describe_impacts, lean_for, normalize_polarity, rule_polarity,
)
from alerting.symbol_relevance import affected_symbols
from alerting.taxonomy import HARD_RULE_PATTERNS
from alerting.transmission import TRANSMISSION

# Frozen copies of the two tables that alerting/transmission.py replaced
# (symbol_relevance._CATEGORY_SYMBOL_CLASS_CHANNELS and direction._LEAN_TABLE,
# as of 8056a42). The merge must not silently drop or change any of them.
_PRE_MERGE_CHANNELS: dict[str, dict[str, str]] = {
    "energy": {"metal": "safe_haven", "index_risk": "risk_sentiment"},
    "geopolitical_conflict": {"metal": "safe_haven", "index_risk": "risk_sentiment"},
    "central_bank": {
        "metal": "usd_relationship", "index_risk": "risk_sentiment",
        "fx_usd_base": "usd_relationship", "fx_usd_quote": "usd_relationship",
    },
    "sovereign_fiscal": {
        "metal": "usd_relationship", "index_risk": "risk_sentiment",
        "fx_usd_base": "usd_relationship", "fx_usd_quote": "usd_relationship",
    },
    "trade_policy": {"index_risk": "risk_sentiment"},
    "natural_disaster_supply_chain": {"index_risk": "risk_sentiment"},
}

_GOLD_RATES = ("mixed", "gold's link to rate expectations has been unreliable since 2024 [Layer2]")
_RELIEF_GOLD = ("mixed", "safe-haven unwind and lower-inflation support pull gold opposite ways")

_PRE_MERGE_LEANS: dict[tuple[str, str, str], tuple[str, str]] = {
    ("energy", "escalation", "metal"): ("buy", "safe-haven bid and inflation hedge on an oil-supply shock [convention]"),
    ("energy", "escalation", "index_risk"): ("sell", "oil-supply shock weighs on risk appetite [convention]"),
    ("energy", "escalation", "oil_linked_fx"): ("sell", "higher oil strengthens CAD, so USDCAD falls [Layer2]"),
    ("energy", "relief", "metal"): _RELIEF_GOLD,
    ("energy", "relief", "index_risk"): ("buy", "easing supply fears support risk appetite [convention]"),
    ("energy", "relief", "oil_linked_fx"): ("buy", "lower oil weakens CAD, so USDCAD rises [Layer2]"),
    ("geopolitical_conflict", "escalation", "metal"): ("buy", "safe-haven demand [convention]"),
    ("geopolitical_conflict", "escalation", "index_risk"): ("sell", "risk-off [convention]"),
    ("geopolitical_conflict", "relief", "metal"): _RELIEF_GOLD,
    ("geopolitical_conflict", "relief", "index_risk"): ("buy", "relief rally in risk appetite [convention]"),
    ("central_bank", "hawkish", "metal"): _GOLD_RATES,
    ("central_bank", "hawkish", "index_risk"): ("sell", "tighter policy and higher yields weigh on equities [convention]"),
    ("central_bank", "dovish", "metal"): _GOLD_RATES,
    ("central_bank", "dovish", "index_risk"): (
        "mixed", "rate cuts read bullish (soft landing) or bearish (recession fear) depending on framing [Layer2]"),
    ("sovereign_fiscal", "escalation", "metal"): ("buy", "safe-haven bid on sovereign stress [convention]"),
    ("sovereign_fiscal", "escalation", "index_risk"): ("sell", "credit stress is risk-off [convention]"),
    ("sovereign_fiscal", "relief", "metal"): _RELIEF_GOLD,
    ("sovereign_fiscal", "relief", "index_risk"): ("buy", "easing credit stress supports risk appetite [convention]"),
    ("trade_policy", "escalation", "index_risk"): ("sell", "trade escalation weighs on risk appetite [convention]"),
    ("trade_policy", "relief", "index_risk"): ("buy", "trade de-escalation supports risk appetite [convention]"),
    ("natural_disaster_supply_chain", "escalation", "index_risk"): (
        "sell", "supply-chain disruption is risk-off [convention]"),
    ("natural_disaster_supply_chain", "relief", "index_risk"): (
        "buy", "supply chains recovering supports risk appetite [convention]"),
}

# Keys the merged table may hold beyond the pre-merge channel table: the
# oil-linked USDCAD cell (previously a special case in symbol_relevance.py).
_ALLOWED_EXTRA_KEYS = {("energy", "oil_linked_fx"), ("trade_policy", "metal")}


def _relevant_polarities(category: str) -> tuple[str, str]:
    return ("hawkish", "dovish") if category == "central_bank" else ("escalation", "relief")


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


def test_merged_table_keeps_every_pre_merge_channel():
    pre_merge_keys = set()
    for category, classes in _PRE_MERGE_CHANNELS.items():
        for symbol_class, channel in classes.items():
            pre_merge_keys.add((category, symbol_class))
            assert TRANSMISSION[(category, symbol_class)].channel == channel, (category, symbol_class)
    assert set(TRANSMISSION) - pre_merge_keys == _ALLOWED_EXTRA_KEYS
    assert TRANSMISSION[("energy", "oil_linked_fx")].channel == "oil_linkage"


def test_merged_table_keeps_every_pre_merge_lean():
    for (category, polarity, symbol_class), (lean, why) in _PRE_MERGE_LEANS.items():
        got = lean_for(category, polarity, symbol_class, country=None, us_link=None)
        assert (got.lean, got.why) == (lean, why), (category, polarity, symbol_class)


def test_every_transmission_has_a_deliberate_lean_for_each_relevant_polarity():
    """A missing cell would silently read 'no established direction' -- fine as a default, wrong as an oversight."""
    missing = []
    for (category, symbol_class), transmission in TRANSMISSION.items():
        for polarity in _relevant_polarities(category):
            if polarity not in transmission.leans:
                missing.append((category, polarity, symbol_class))
    assert missing == []


def test_lean_values_are_only_buy_sell_or_mixed_and_always_carry_a_reason():
    for transmission in TRANSMISSION.values():
        assert transmission.channel.strip()
        if transmission.us_only:
            assert transmission.not_us_why.strip()
        for lean in transmission.leans.values():
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
    ("trade_policy", "escalation", "index_risk", "sell"),
    ("trade_policy", "relief", "index_risk", "buy"),
])
def test_lean_for_known_cells(category, polarity, symbol_class, expected):
    assert lean_for(category, polarity, symbol_class).lean == expected


def test_lean_for_fx_quote_with_unknown_central_bank_is_mixed():
    # Which central bank is unknown, so there is no USD direction to state.
    assert lean_for("central_bank", "hawkish", "fx_usd_quote", country=None).lean == "mixed"


def test_fed_hawkish_lifts_usd_base_and_drops_usd_quote():
    assert lean_for("central_bank", "hawkish", "fx_usd_base", country="US").lean == "buy"
    assert lean_for("central_bank", "hawkish", "fx_usd_quote", country="US").lean == "sell"
    assert lean_for("central_bank", "dovish", "fx_usd_base", country="US").lean == "sell"
    assert lean_for("central_bank", "dovish", "fx_usd_quote", country="US").lean == "buy"
    assert "[convention]" in lean_for("central_bank", "hawkish", "fx_usd_base", country="US").why


@pytest.mark.parametrize("country", [None, "GB", "XX"])
@pytest.mark.parametrize("polarity", ["hawkish", "dovish"])
@pytest.mark.parametrize("symbol_class", ["fx_usd_base", "fx_usd_quote"])
def test_non_fed_or_unknown_central_bank_fx_is_mixed(country, polarity, symbol_class):
    lean = lean_for("central_bank", polarity, symbol_class, country=country)
    assert lean == Lean("mixed", "which central bank is unknown or not the Fed")


@pytest.mark.parametrize("country", [None, "US", "GB"])
@pytest.mark.parametrize("polarity", ["escalation", "relief"])
@pytest.mark.parametrize("symbol_class", ["fx_usd_base", "fx_usd_quote"])
def test_sovereign_fiscal_fx_is_mixed_even_for_the_us(country, polarity, symbol_class):
    lean = lean_for("sovereign_fiscal", polarity, symbol_class, country=country)
    assert lean.lean == "mixed"
    if country == "US":
        assert "US fiscal stress" in lean.why
    else:
        assert lean.why == "which government is unknown or not the US"


def test_no_us_link_overrides_every_cell():
    assert NO_US_LINK_WHY == "no direct US or global-supply link"
    for (category, symbol_class) in TRANSMISSION:
        for polarity in POLARITIES:
            for country in (None, "US", "RU"):
                lean = lean_for(category, polarity, symbol_class, country=country, us_link="none")
                assert lean == Lean("mixed", "no direct US or global-supply link"), (category, polarity, symbol_class)


@pytest.mark.parametrize("us_link", [None, "direct", "global_supply"])
def test_unknown_or_linked_us_link_keeps_todays_lean(us_link):
    for (category, polarity, symbol_class) in _PRE_MERGE_LEANS:
        assert lean_for(category, polarity, symbol_class, us_link=us_link) == lean_for(category, polarity, symbol_class)


def test_unclear_polarity_is_always_mixed_never_a_guess():
    for (category, symbol_class) in TRANSMISSION:
        for country in (None, "US"):
            lean = lean_for(category, "unclear", symbol_class, country=country)
            assert lean.lean == "mixed"
            assert "unclear" in lean.why


def test_unknown_combination_is_mixed_not_an_error():
    assert lean_for("not_a_category", "escalation", "metal").lean == "mixed"
    assert lean_for("energy", "escalation", "fx_cross", country="US").lean == "mixed"


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


def test_describe_impacts_passes_country_and_us_link_through():
    impacts = affected_symbols("central_bank", ["EURUSD", "USDJPY"])
    fed = {d["symbol"]: d["lean"] for d in describe_impacts(impacts, "central_bank", "hawkish", country="US")}
    assert fed == {"EURUSD": "sell", "USDJPY": "buy"}

    unlinked = describe_impacts(impacts, "central_bank", "hawkish", country="US", us_link="none")
    assert {d["lean"] for d in unlinked} == {"mixed"}
    assert {d["lean_why"] for d in unlinked} == {NO_US_LINK_WHY}
    assert set(unlinked[0]) == {"symbol", "channel", "lean", "lean_why"}


def test_describe_impacts_with_no_tracked_relevance_is_empty():
    assert describe_impacts([], "energy", "escalation") == []


def test_tariffs_on_bullion_lean_is_mixed_citing_comex_for_both_polarities():
    for polarity in ("escalation", "relief"):
        got = lean_for("trade_policy", polarity, "metal")
        assert got.lean == "mixed"
        assert "COMEX" in got.why
