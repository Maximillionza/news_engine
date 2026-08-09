"""
Tests for webapp.symbols — synthetic, no network needed. Same style as
tests/test_scoring_smoke.py: plain functions with asserts, run via
__main__, no pytest dependency.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.symbols import classify_symbol, UnrecognizedSymbolError


def test_metal_classifies_inverse():
    print("=== metal ticker classifies as inverse ===")
    result = classify_symbol("XAUUSD")
    assert result.symbol_class == "metal"
    assert result.usd_relationship == "inverse"
    print("PASS\n")


def test_index_classifies_risk_sentiment():
    print("=== index ticker classifies as risk_sentiment ===")
    result = classify_symbol("US30")
    assert result.symbol_class == "index_risk"
    assert result.usd_relationship == "risk_sentiment"
    print("PASS\n")


def test_usd_base_classifies_direct():
    print("=== USDxxx classifies as fx_usd_base/direct ===")
    result = classify_symbol("USDJPY")
    assert result.symbol_class == "fx_usd_base"
    assert result.usd_relationship == "direct"
    print("PASS\n")


def test_usd_quote_classifies_inverse():
    print("=== xxxUSD classifies as fx_usd_quote/inverse ===")
    result = classify_symbol("EURUSD")
    assert result.symbol_class == "fx_usd_quote"
    assert result.usd_relationship == "inverse"
    print("PASS\n")


def test_fx_cross_has_no_usd_relationship():
    print("=== cross pair (no USD leg) has usd_relationship=None ===")
    result = classify_symbol("GBPAUD")
    assert result.symbol_class == "fx_cross"
    assert result.usd_relationship is None
    print("PASS\n")


def test_lowercase_input_normalized():
    print("=== lowercase ticker input is normalized to uppercase ===")
    result = classify_symbol("eurusd")
    assert result.symbol == "EURUSD"
    print("PASS\n")


def test_unrecognized_ticker_raises():
    print("=== malformed ticker raises UnrecognizedSymbolError ===")
    try:
        classify_symbol("NOTASYMBOL123")
        assert False, "expected UnrecognizedSymbolError"
    except UnrecognizedSymbolError:
        pass
    print("PASS\n")


if __name__ == "__main__":
    test_metal_classifies_inverse()
    test_index_classifies_risk_sentiment()
    test_usd_base_classifies_direct()
    test_usd_quote_classifies_inverse()
    test_fx_cross_has_no_usd_relationship()
    test_lowercase_input_normalized()
    test_unrecognized_ticker_raises()
    print("All symbol classification tests passed.")
