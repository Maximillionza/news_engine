from __future__ import annotations

import pytest

from alerting import us_link
from alerting.taxonomy import HARD_RULE_PATTERNS
from alerting.us_link import (
    US_LINKS, cap_note, cap_severity, normalize_country, normalize_us_link, reconcile, rule_country_us_link,
)


# --- rule-tier map: a hard-rule hit skips the LLM, so its country / US link come from here ---

def test_every_hard_rule_pattern_has_a_deliberate_country_and_us_link():
    every_pattern = {p for patterns in HARD_RULE_PATTERNS.values() for p in patterns}
    assert set(us_link._RULE_COUNTRY_US_LINK) == every_pattern
    for country, link in us_link._RULE_COUNTRY_US_LINK.values():
        assert link in US_LINKS + (None,)
        assert country is None or country == "XX" or (len(country) == 2 and country.isupper())


@pytest.mark.parametrize("keywords,expected", [
    (["strait of hormuz closed"], ("XX", "global_supply")),
    (["opec+ agrees to cut"], ("XX", "global_supply")),
    (["fed chair fired"], ("US", "direct")),
    (["declares war"], (None, None)),
    (["oil export ban"], (None, "global_supply")),
    (["unscheduled rate hike"], (None, None)),  # the phrase does not name the Fed -- see the module docstring
    ([], (None, None)),
    (["not a hard-rule phrase", "suez canal blocked"], ("XX", "global_supply")),  # first KNOWN pattern wins
])
def test_rule_map_examples(keywords, expected):
    assert rule_country_us_link(keywords) == expected


# --- normalization of the model's free-text answers ---

@pytest.mark.parametrize("raw,expected", [
    ("ru", "RU"), (" US ", "US"), ("USA", "US"), ("U.S.", "US"), ("united states", "US"),
    ("global", "XX"), ("Multiple", "XX"), ("xx", "XX"),
    ("Russia", None), ("", None), (None, None), (7, None), ("R1", None),
])
def test_normalize_country(raw, expected):
    assert normalize_country(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("direct", "direct"), ("Global supply", "global_supply"), ("global-supply", "global_supply"),
    ("None", "none"), (" NONE ", "none"), ("indirect", None), (None, None), ("", None), (3, None),
])
def test_normalize_us_link(raw, expected):
    assert normalize_us_link(raw) == expected


@pytest.mark.parametrize("country,link,expected", [
    ("US", "none", "direct"),   # a US event is direct by definition, whatever the model said
    ("US", None, "direct"),
    ("US", "global_supply", "direct"),
    ("RU", "none", "none"),
    ("XX", "global_supply", "global_supply"),
    (None, None, None),
    (None, "direct", "direct"),
])
def test_reconcile(country, link, expected):
    assert reconcile(country, link) == expected


# --- the cap: no US link -> at most Medium, no buy/sell lean ---

@pytest.mark.parametrize("severity,link,expected", [
    ("High", "none", ("Medium", True)),
    ("Medium", "none", ("Medium", True)),
    ("Low", "none", ("Low", True)),
    ("High", None, ("High", False)),
    ("High", "direct", ("High", False)),
    ("High", "global_supply", ("High", False)),
])
def test_cap_severity(severity, link, expected):
    assert cap_severity(severity, link) == expected


def test_cap_note_wording():
    assert cap_note("High", True) == "Capped High -> Medium: no direct US or global-supply link"
    assert cap_note("Medium", True) == "No buy/sell lean: no direct US or global-supply link"
    assert cap_note("Low", True) == "No buy/sell lean: no direct US or global-supply link"
    assert cap_note("High", False) is None
    assert cap_note("High", None) is None
    assert cap_note(None, None) is None
