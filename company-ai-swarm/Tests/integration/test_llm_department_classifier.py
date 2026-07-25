"""LLMDepartmentClassifier makes one real Claude call per objective, using a fake
ModelGateway so no real API call or credentials are required to run these in CI - same
pattern as Tests/integration/test_anthropic_provider.py's fake client_factory. A separate,
gated test at the bottom makes one real call.
"""

from __future__ import annotations

import json
import os

import pytest

from orchestrator.classification import (
    DepartmentClassificationError,
    LLMDepartmentClassifier,
    create_classifier_from_env,
)
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from shared.model_gateway import ModelGateway


class _FakeProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.prompts: list[str] = []

    def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
        self.prompts.append(prompt)
        return self.response_text


def _registry(*departments: DepartmentDefinition) -> DepartmentRegistry:
    registry = DepartmentRegistry(".")
    for department in departments:
        registry._departments[department.id] = department
    return registry


def _forex_registry() -> DepartmentRegistry:
    return _registry(
        DepartmentDefinition(
            id="research", name="Research Department", purpose="Information acquisition.",
            mission="Acquire information.", capabilities=["research"], agents=["research_agent_001"],
        ),
        DepartmentDefinition(
            id="engineering", name="Engineering Department", purpose="Build systems.",
            mission="Build.", capabilities=["engineering"], agents=["engineering_agent_001"],
        ),
    )


def test_classify_returns_matched_departments_from_model_json() -> None:
    provider = _FakeProvider(json.dumps({"departments": ["research"], "reasoning": "Needs deep research."}))
    gateway = ModelGateway(provider)
    classifier = LLMDepartmentClassifier(gateway)

    result = classifier.classify("Design a Forex trading strategy", _forex_registry())

    assert [d.id for d in result.matched_departments] == ["research"]
    assert result.reasoning == "Needs deep research."
    assert "Forex" in provider.prompts[0]
    assert "research" in provider.prompts[0]  # department descriptions were included


def test_classify_strips_markdown_code_fence() -> None:
    payload = json.dumps({"departments": ["engineering"], "reasoning": "Build work."})
    provider = _FakeProvider(f"```json\n{payload}\n```")
    classifier = LLMDepartmentClassifier(ModelGateway(provider))

    result = classifier.classify("Build the thing", _forex_registry())

    assert [d.id for d in result.matched_departments] == ["engineering"]


def test_classify_drops_hallucinated_department_ids() -> None:
    provider = _FakeProvider(
        json.dumps({"departments": ["research", "made_up_department"], "reasoning": "..."})
    )
    classifier = LLMDepartmentClassifier(ModelGateway(provider))

    result = classifier.classify("obj", _forex_registry())

    assert [d.id for d in result.matched_departments] == ["research"]


def test_classify_empty_departments_list_is_a_valid_no_match() -> None:
    provider = _FakeProvider(json.dumps({"departments": [], "reasoning": "Out of scope."}))
    classifier = LLMDepartmentClassifier(ModelGateway(provider))

    result = classifier.classify("What's the weather?", _forex_registry())

    assert result.matched_departments == []
    assert result.reasoning == "Out of scope."


def test_classify_raises_on_unparseable_response() -> None:
    provider = _FakeProvider("this is not json at all")
    classifier = LLMDepartmentClassifier(ModelGateway(provider))

    with pytest.raises(DepartmentClassificationError):
        classifier.classify("obj", _forex_registry())


def test_classify_raises_on_generate_failure() -> None:
    class _FailingProvider:
        def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
            raise RuntimeError("rate limited")

    classifier = LLMDepartmentClassifier(ModelGateway(_FailingProvider()))

    with pytest.raises(DepartmentClassificationError, match="rate limited"):
        classifier.classify("obj", _forex_registry())


def test_create_classifier_from_env_selects_keyword_by_default() -> None:
    from orchestrator.classification import KeywordDepartmentClassifier

    classifier = create_classifier_from_env(ModelGateway(_FakeProvider("{}")), env={})
    assert isinstance(classifier, KeywordDepartmentClassifier)


def test_create_classifier_from_env_selects_llm() -> None:
    classifier = create_classifier_from_env(
        ModelGateway(_FakeProvider("{}")), env={"DEPARTMENT_CLASSIFIER": "llm"}
    )
    assert isinstance(classifier, LLMDepartmentClassifier)


def test_create_classifier_from_env_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="Unknown DEPARTMENT_CLASSIFIER"):
        create_classifier_from_env(ModelGateway(_FakeProvider("{}")), env={"DEPARTMENT_CLASSIFIER": "made_up"})


@pytest.mark.skipif(
    not (os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("RUN_REAL_ANTHROPIC_SMOKE_TEST") == "1"),
    reason="Real Claude API smoke test - set ANTHROPIC_API_KEY and RUN_REAL_ANTHROPIC_SMOKE_TEST=1 to run",
)
def test_real_llm_classification_smoke_test() -> None:
    from shared.providers.anthropic_provider import AnthropicModelProvider

    gateway = ModelGateway(AnthropicModelProvider())
    classifier = LLMDepartmentClassifier(gateway)

    result = classifier.classify("Research current renewable energy storage trends", _forex_registry())

    assert [d.id for d in result.matched_departments] == ["research"]
