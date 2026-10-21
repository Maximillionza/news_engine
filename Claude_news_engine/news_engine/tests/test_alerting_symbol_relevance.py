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


def test_usdcad_is_oil_linked_under_energy_and_usd_base_under_central_bank():
    (energy,) = affected_symbols("energy", ["USDCAD"])
    assert (energy.channel, energy.symbol_class) == ("oil_linkage", "oil_linked_fx")

    (central_bank,) = affected_symbols("central_bank", ["USDCAD"])
    assert (central_bank.channel, central_bank.symbol_class) == ("usd_relationship", "fx_usd_base")


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


def test_gold_bar_tariff_headline_reaches_xauusd_via_tariff_bullion():
    result = affected_symbols("trade_policy", ["XAUUSD", "US30"], headline="US slaps tariffs on imported gold bars")
    assert {i.symbol: i.channel for i in result} == {"XAUUSD": "tariff_bullion", "US30": "risk_sentiment"}


def test_diesel_export_ban_reaches_us30_only():
    result = affected_symbols(
        "trade_policy", ["XAUUSD", "US30"], headline="Russia extends diesel export ban to year-end")
    assert [i.symbol for i in result] == ["US30"]


def test_bullion_gate_is_a_word_match():
    def reaches_gold(headline: str) -> bool:
        return "XAUUSD" in [i.symbol for i in affected_symbols("trade_policy", ["XAUUSD"], headline=headline)]
    assert not reaches_gold("Goldman Sachs warns on tariffs")
    assert reaches_gold("Tariffs on Precious Metals widen")
    assert reaches_gold("BULLION tariff talk")


def test_no_headline_means_no_bullion_channel():
    result = affected_symbols("trade_policy", ["XAUUSD", "US30"])
    assert [i.symbol for i in result] == ["US30"]
