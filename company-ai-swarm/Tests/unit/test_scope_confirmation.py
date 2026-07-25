"""orchestrator/scope_confirmation.py's assess_scope_confirmation() (Phase 22,
IMPLEMENTATION_PLAN.md, 2026-07-26), against a fake ModelGateway - no real API calls. Mirrors
Tests/unit/test_intake_sufficiency.py's pattern for the sibling sufficiency gate."""

from __future__ import annotations

import json

import pytest

from orchestrator.department_registry import DepartmentDefinition
from orchestrator.scope_confirmation import FALLBACK_SCOPE_QUESTION, assess_scope_confirmation
from shared.model_gateway import ModelGateway


class _FakeProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.prompts: list[str] = []

    def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
        self.prompts.append(prompt)
        return self.response_text


def _dept(dept_id: str) -> DepartmentDefinition:
    return DepartmentDefinition(
        id=dept_id, name=dept_id.title(), purpose=f"{dept_id} purpose.", mission="",
        capabilities=[], agents=[f"{dept_id}_agent_001"],
    )


def test_single_department_never_asks_without_a_model_call() -> None:
    provider = _FakeProvider("should never be read")
    gateway = ModelGateway(provider)

    result = assess_scope_confirmation(
        gateway, "Research trends", [_dept("research")], already_asked=False
    )

    assert result.needs_confirmation is False
    assert provider.prompts == []


def test_already_asked_never_calls_the_model_again() -> None:
    provider = _FakeProvider("should never be read")
    gateway = ModelGateway(provider)

    result = assess_scope_confirmation(
        gateway,
        "Build a new app and validate compliance",
        [_dept("engineering"), _dept("compliance")],
        already_asked=True,
    )

    assert result.needs_confirmation is False
    assert provider.prompts == []


def test_ambiguous_multi_department_objective_asks_the_models_question() -> None:
    provider = _FakeProvider(
        json.dumps(
            {
                "needs_confirmation": True,
                "clarifying_question": "Just the build, or the full compliance review too?",
                "reasoning": "Genuinely ambiguous scope.",
            }
        )
    )
    gateway = ModelGateway(provider)

    result = assess_scope_confirmation(
        gateway,
        "Build me an app for tracking expenses",
        [_dept("engineering"), _dept("compliance")],
        already_asked=False,
    )

    assert result.needs_confirmation is True
    assert result.clarifying_question == "Just the build, or the full compliance review too?"
    assert len(provider.prompts) == 1


def test_explicit_wording_does_not_need_confirmation() -> None:
    provider = _FakeProvider(
        json.dumps(
            {
                "needs_confirmation": False,
                "clarifying_question": None,
                "reasoning": "The request already says 'just build it, skip compliance'.",
            }
        )
    )
    gateway = ModelGateway(provider)

    result = assess_scope_confirmation(
        gateway,
        "Build me an app for tracking expenses - just build it, skip compliance for now.",
        [_dept("engineering"), _dept("compliance")],
        already_asked=False,
    )

    assert result.needs_confirmation is False
    assert result.clarifying_question is None


def test_missing_clarifying_question_falls_back_to_generated_one() -> None:
    provider = _FakeProvider(
        json.dumps({"needs_confirmation": True, "clarifying_question": None, "reasoning": "Ambiguous."})
    )
    gateway = ModelGateway(provider)

    result = assess_scope_confirmation(
        gateway, "obj", [_dept("engineering"), _dept("compliance")], already_asked=False
    )

    assert result.needs_confirmation is True
    assert result.clarifying_question == FALLBACK_SCOPE_QUESTION.format(
        primary="engineering", all_depts="engineering, compliance"
    )


def test_unparseable_json_fails_toward_not_asking_proceed_broad() -> None:
    """Unlike intake.py's sufficiency gate (which fails toward asking again - missing detail
    is a real block), an unparseable scope-confirmation response fails toward NOT asking -
    proceeding broad (every matched department) is the same outcome as if this gate didn't
    exist at all, so it's a safe default rather than another round of asking."""

    provider = _FakeProvider("this is not json")
    gateway = ModelGateway(provider)

    result = assess_scope_confirmation(
        gateway, "obj", [_dept("engineering"), _dept("compliance")], already_asked=False
    )

    assert result.needs_confirmation is False
    assert result.clarifying_question is None


def test_missing_expected_keys_fails_toward_not_asking() -> None:
    provider = _FakeProvider(json.dumps({"unexpected": "shape"}))
    gateway = ModelGateway(provider)

    result = assess_scope_confirmation(
        gateway, "obj", [_dept("engineering"), _dept("compliance")], already_asked=False
    )

    assert result.needs_confirmation is False


def test_generate_failure_propagates_not_swallowed() -> None:
    class _FailingProvider:
        def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
            raise RuntimeError("connection reset")

    gateway = ModelGateway(_FailingProvider())

    with pytest.raises(RuntimeError, match="connection reset"):
        assess_scope_confirmation(
            gateway, "obj", [_dept("engineering"), _dept("compliance")], already_asked=False
        )


def test_prompt_names_primary_department_and_all_matched() -> None:
    provider = _FakeProvider(
        json.dumps({"needs_confirmation": False, "clarifying_question": None, "reasoning": "clear"})
    )
    gateway = ModelGateway(provider)

    assess_scope_confirmation(
        gateway, "obj", [_dept("engineering"), _dept("compliance")], already_asked=False
    )

    assert "Primary department: engineering" in provider.prompts[0]
    assert "compliance" in provider.prompts[0]
