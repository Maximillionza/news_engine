"""
Tests for webapp.symbols.usd_sign and its 5 call sites (B11 C3).

The equivalence rows pin the pre-refactor outputs with exact == (float
identity), so the helper cannot drift from the old per-site branching.
"""
import os
import re
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import config.settings
from scoring.probability_engine import _map_to_instrument_score
from webapp.history import _implied_surprise_direction
from webapp.predictions_service import _trend_instrument_lean
from webapp.scoring_service import score_event_for_symbol
from webapp.stats_methods import market_lean
from webapp.symbols import SymbolClass, classify_symbol, usd_sign

CASES = [("direct", "USDJPY"), ("inverse", "XAUUSD"), ("risk_sentiment", "US30"), (None, "GBPAUD")]
D = config.settings.RISK_SENTIMENT_DAMPENING

_SITE_FILES = [
    "scoring/probability_engine.py",
    "webapp/scoring_service.py",
    "webapp/stats_methods.py",
    "webapp/history.py",
    "webapp/predictions_service.py",
]
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("rel,expected", [("direct", 1), ("inverse", -1), ("risk_sentiment", -1), (None, None)])
def test_usd_sign(rel, expected):
    assert usd_sign(rel) == expected


def test_usd_sign_rejects_unknown_relationship():
    with pytest.raises(ValueError):
        usd_sign("bogus")


def test_map_to_instrument_score_equivalence():
    assert _map_to_instrument_score(0.37, "USDJPY") == 0.37
    assert _map_to_instrument_score(0.37, "XAUUSD") == -0.37
    assert _map_to_instrument_score(0.37, "US30") == -0.37 * D
    with pytest.raises(ValueError):
        _map_to_instrument_score(0.37, "GBPAUD")


def test_score_event_for_symbol_equivalence():
    event = SimpleNamespace(title="CPI m/m", usd_surprise_score=lambda: 0.37)
    expected = {"USDJPY": 0.37, "XAUUSD": -0.37, "US30": -0.37 * D}
    for rel, sym in CASES:
        sc = SymbolClass(symbol=sym, symbol_class=classify_symbol(sym).symbol_class, usd_relationship=rel)
        result = score_event_for_symbol(event, sc)
        if rel is None:
            assert result.applicable is False
        else:
            assert result.raw_score == expected[sym]


def test_market_lean_equivalence():
    got = [market_lean("CPI m/m", 1, sym) for _, sym in CASES]
    assert got == ["buy", "sell", "sell", "mixed"]


def test_implied_surprise_direction_equivalence():
    got = [_implied_surprise_direction("CPI m/m", sym, "bullish") for _, sym in CASES]
    assert got == ["higher", "lower", "lower", None]


def test_trend_instrument_lean_equivalence():
    got = [_trend_instrument_lean("CPI m/m", "higher", rel) for rel, _ in CASES]
    assert got == ["bullish", "bearish", "bearish", None]


def test_one_usd_sign_rule():
    pattern = re.compile(r'==\s*"(inverse|direct)"')
    for rel_path in _SITE_FILES:
        with open(os.path.join(_APP_DIR, rel_path), encoding="utf-8") as fh:
            src = fh.read()
        assert not pattern.search(src), f"{rel_path} still branches on inverse/direct"
        assert "usd_sign(" in src, f"{rel_path} does not use usd_sign"
