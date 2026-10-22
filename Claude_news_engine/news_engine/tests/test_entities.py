"""
Tests for data_layer/entities.py -- the B7 (2026-10-22) incident gazetteer.

Pure functions, no network, no DB. Headlines come verbatim from the live
shock_alerts.db (tests/fixtures/b7_live_alert_pairs.json, copied read-only).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_layer.entities import incident_entities

_MODULE_PATH = Path(__file__).resolve().parent.parent / "data_layer" / "entities.py"
_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "b7_live_alert_pairs.json"


def _live() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_entities_of_live_headlines():
    live = _live()
    expected = {
        "12": {"iran", "hormuz"},
        "13": {"iran", "hormuz"},
        "33": {"ukraine", "russia"},
        "39": {"ukraine", "russia", "zelensky"},
        "54": {"saudi arabia"},
        "55": {"saudi arabia"},
        "71": {"russia"},
        "72": {"russia", "zelensky"},
        "41": {"houthi", "saudi arabia"},
        "43": {"iea"},
        "46": set(),
        "52": {"mexico"},
    }
    for alert_no, entities in expected.items():
        assert incident_entities(live[alert_no]["headline"]) == frozenset(entities), alert_no


def test_generic_actors_are_not_entities():
    assert incident_entities("Trump says Fed must cut as US dollar slides; White House weighs response") == frozenset()


def test_word_boundaries():
    assert "oman" not in incident_entities("Omaha refinery")
    assert incident_entities("Iranian drones hit tanker") == frozenset({"iran"})
    assert incident_entities("Kremlin’s warning") == frozenset({"russia"})
    assert incident_entities("Zelenskyy") == frozenset({"zelensky"})
    assert incident_entities("Zelenskiy") == frozenset({"zelensky"})
    assert incident_entities("OPEC+ agrees to cut") == frozenset({"opec"})


def test_source_has_no_backspace_bytes():
    assert b"\x08" not in _MODULE_PATH.read_bytes()
