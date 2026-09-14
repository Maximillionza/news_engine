from __future__ import annotations

from alerting import taxonomy


def test_every_hard_rule_category_is_a_known_shock_category():
    for category in taxonomy.HARD_RULE_PATTERNS:
        assert category in taxonomy.SHOCK_CATEGORIES


def test_every_signal_keyword_category_is_a_known_shock_category():
    for category in taxonomy.CATEGORY_SIGNAL_KEYWORDS:
        assert category in taxonomy.SHOCK_CATEGORIES


def test_all_patterns_are_lowercase():
    for patterns in list(taxonomy.HARD_RULE_PATTERNS.values()) + list(taxonomy.CATEGORY_SIGNAL_KEYWORDS.values()):
        for phrase in patterns:
            assert phrase == phrase.lower(), f"{phrase!r} must be lowercase (triage.py matches case-insensitively)"


def test_hard_rule_patterns_nonempty_for_energy_and_geopolitical():
    assert len(taxonomy.HARD_RULE_PATTERNS["energy"]) > 0
    assert len(taxonomy.HARD_RULE_PATTERNS["geopolitical_conflict"]) > 0
