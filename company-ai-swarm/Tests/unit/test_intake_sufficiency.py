"""orchestrator/intake.py's assess_sufficiency() round logic (Documentation/plans/
2026-07-19-dynamic-department-routing-design.md Section 3.2), against a fake ModelGateway -
no real API calls."""

from __future__ import annotations

import json

import pytest

from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from orchestrator.intake import FALLBACK_CLARIFYING_QUESTION, assess_sufficiency
from shared.model_gateway import ModelGateway


class _FakeProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response_text


def _registry() -> DepartmentRegistry:
    registry = DepartmentRegistry(".")
    registry._departments["research"] = DepartmentDefinition(
        id="research", name="Research Department", purpose="Information acquisition.",
        mission="Acquire information.", capabilities=["research"], agents=["research_agent_001"],
    )
    return registry


def test_round_1_sufficient() -> None:
    provider = _FakeProvider(json.dumps({"sufficient": True, "clarifying_question": None, "reasoning": "Clear enough."}))
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "Research current market trends.", [], _registry(), round_number=1)

    assert result.sufficient is True
    assert result.clarifying_question is None


def test_round_1_insufficient_asks_the_models_question() -> None:
    provider = _FakeProvider(
        json.dumps({"sufficient": False, "clarifying_question": "Which market segment?", "reasoning": "Too vague."})
    )
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "Do some research", [], _registry(), round_number=1)

    assert result.sufficient is False
    assert result.clarifying_question == "Which market segment?"


def test_round_2_prompt_asks_for_choice_framing() -> None:
    """Round 2's prompt must instruct the model to phrase an insufficient verdict as an
    explicit choice, not another open question - the test can't control what a real model
    outputs, but it can assert the instruction was actually sent."""

    provider = _FakeProvider(
        json.dumps({"sufficient": False, "clarifying_question": "Proceed as-is or provide detail?", "reasoning": "Still vague."})
    )
    gateway = ModelGateway(provider)

    assess_sufficiency(gateway, "Do some research", [("user", "Do some research")], _registry(), round_number=2)

    assert "explicit choice" in provider.prompts[0]
    assert "proceed" in provider.prompts[0].lower()


def test_round_3_never_calls_the_model() -> None:
    provider = _FakeProvider("should never be read")
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "obj", [], _registry(), round_number=3)

    assert result.sufficient is True
    assert provider.prompts == []


def test_round_4_and_beyond_also_never_calls_the_model() -> None:
    provider = _FakeProvider("should never be read")
    result = assess_sufficiency(ModelGateway(provider), "obj", [], _registry(), round_number=5)

    assert result.sufficient is True
    assert provider.prompts == []


def test_unparseable_json_fails_toward_insufficient_with_fallback() -> None:
    provider = _FakeProvider("this is not json")
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "obj", [], _registry(), round_number=1)

    assert result.sufficient is False
    assert result.clarifying_question == FALLBACK_CLARIFYING_QUESTION


def test_missing_expected_keys_fails_toward_insufficient() -> None:
    provider = _FakeProvider(json.dumps({"unexpected": "shape"}))
    gateway = ModelGateway(provider)

    result = assess_sufficiency(gateway, "obj", [], _registry(), round_number=1)

    assert result.sufficient is False
    assert result.clarifying_question == FALLBACK_CLARIFYING_QUESTION


def test_generate_failure_propagates_not_swallowed() -> None:
    """A network/timeout/provider failure is an infrastructure problem, not a 'the model
    said no' verdict - it must raise, not be silently converted into a fabricated
    clarifying question (Documentation/plans/2026-07-19-dynamic-department-routing-design.md
    Section 4's error table)."""

    class _FailingProvider:
        def generate(self, prompt: str) -> str:
            raise RuntimeError("connection reset")

    gateway = ModelGateway(_FailingProvider())

    with pytest.raises(RuntimeError, match="connection reset"):
        assess_sufficiency(gateway, "obj", [], _registry(), round_number=1)
