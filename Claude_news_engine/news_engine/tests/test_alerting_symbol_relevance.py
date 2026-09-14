from __future__ import annotations

from alerting.symbol_relevance import affected_symbols


def test_energy_shock_affects_gold_via_safe_haven():
    result = affected_symbols("energy", ["XAUUSD", "US30"])
    symbols = {r.symbol: r.channel for r in result}
    assert symbols["XAUUSD"] == "safe_haven"


def test_energy_shock_affects_us30_via_risk_sentiment():
    result = affected_symbols("energy", ["XAUUSD", "US30"])
    symbols = {r.symbol: r.channel for r in result}
    assert symbols["US30"] == "risk_sentiment"


def test_energy_shock_affects_oil_linked_usdcad_directly():
    result = affected_symbols("energy", ["USDCAD"])
    symbols = {r.symbol: r.channel for r in result}
    assert symbols["USDCAD"] == "oil_linkage"


def test_no_tracked_symbols_returns_empty_list():
    assert affected_symbols("energy", []) == []


def test_unrecognized_tracked_symbol_is_skipped_not_crashed():
    result = affected_symbols("energy", ["XAUUSD", "NOT_A_REAL_TICKER_9"])
    symbols = {r.symbol for r in result}
    assert "XAUUSD" in symbols
    assert "NOT_A_REAL_TICKER_9" not in symbols


def test_category_with_no_real_relevance_for_a_symbol_omits_it():
    # trade_policy has no established transmission logic for a plain FX cross
    result = affected_symbols("trade_policy", ["GBPAUD"])
    assert result == []
