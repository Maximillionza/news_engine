"""Department classification: decides which department(s) an objective belongs to.

Source: Documentation/plans/2026-07-19-dynamic-department-routing-design.md Section 3.3.
Two swappable implementations of one interface - exactly parallel to shared/model_gateway.py's
ModelProvider/StubModelProvider/AnthropicModelProvider pattern:

- KeywordDepartmentClassifier (this task): the exact keyword-overlap logic
  orchestrator/planner.py used to implement directly, relocated here unchanged - not fixed,
  not rewritten. Dev/test default.
- LLMDepartmentClassifier (added in a later task): wraps a ModelGateway to make one real
  classification call per objective. Production, selected via DEPARTMENT_CLASSIFIER=llm.

COOOrchestrator.__init__ defaults to KeywordDepartmentClassifier() - every existing call site
that constructs a COOOrchestrator without specifying a classifier needs zero changes.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Mapping, Protocol

from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from shared.llm_json import strip_code_fence
from shared.model_gateway import ModelGateway

_WORD_RE = re.compile(r"[a-zA-Z_]+")
_CANONICAL_DEPARTMENT_ORDER = ["research", "engineering", "compliance", "operations"]


@dataclass
class ObjectiveClassification:
    matched_departments: list[DepartmentDefinition]
    reasoning: str


class DepartmentClassifier(Protocol):
    def classify(self, objective: str, registry: DepartmentRegistry) -> ObjectiveClassification: ...


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text) if len(w) > 3}


def _department_corpus(dept: DepartmentDefinition) -> set[str]:
    text = " ".join([dept.name, dept.purpose, dept.mission, *dept.capabilities])
    return _tokenize(text)


def _canonical_sort_key(department: DepartmentDefinition) -> int:
    try:
        return _CANONICAL_DEPARTMENT_ORDER.index(department.id)
    except ValueError:
        return len(_CANONICAL_DEPARTMENT_ORDER)


class KeywordDepartmentClassifier:
    """Dev/test default - the exact keyword-overlap matching orchestrator/planner.py
    implemented directly before this module existed (see
    Documentation/operations/technology_decisions.md's "Objective-to-department routing"
    note for its known weakness, preserved verbatim here, not fixed). Departments with no
    assigned agents are excluded from consideration entirely - a department the COO cannot
    dispatch to is not a viable match regardless of text-similarity score."""

    def classify(self, objective: str, registry: DepartmentRegistry) -> ObjectiveClassification:
        objective_tokens = _tokenize(objective)
        matched = [
            department
            for department in registry.all()
            if department.agents and len(objective_tokens & _department_corpus(department)) > 0
        ]
        matched.sort(key=_canonical_sort_key)

        if not matched:
            reasoning = (
                "No department's capabilities, purpose, or mission shared any keyword with "
                "the objective. Cannot route without a human-specified department."
            )
        else:
            reasoning = (
                f"Matched {len(matched)} department(s) via keyword overlap: "
                f"{[d.id for d in matched]}."
            )

        return ObjectiveClassification(matched_departments=matched, reasoning=reasoning)


class DepartmentClassificationError(Exception):
    """Raised when LLMDepartmentClassifier's call fails or its response can't be parsed."""


class LLMDepartmentClassifier:
    """Production: one real Claude call per objective, via the same ModelGateway swarm
    agents already use - no new tiering axis (Documentation/plans/
    2026-07-19-dynamic-department-routing-design.md Section 2 scope note: model tier
    selection is deferred, separate future work). Reuses ModelGateway.generate(prompt) -> str
    (no new provider methods); asks for JSON, parses it, and drops any department ID the
    model names that isn't in the real registry rather than trusting it."""

    def __init__(self, model_gateway: ModelGateway) -> None:
        self._model_gateway = model_gateway

    def classify(self, objective: str, registry: DepartmentRegistry) -> ObjectiveClassification:
        eligible = [d for d in registry.all() if d.agents]
        if not eligible:
            return ObjectiveClassification(
                matched_departments=[],
                reasoning="No department in the registry has any assigned agents.",
            )

        department_descriptions = "\n".join(
            f"- {d.id}: {d.name}. Purpose: {d.purpose}. Mission: {d.mission}. "
            f"Capabilities: {', '.join(d.capabilities) or 'none listed'}."
            for d in eligible
        )
        prompt = (
            "You are classifying a business objective to determine which department(s) of "
            "a company should handle it. Consider what the objective actually requires, not "
            "just literal keyword overlap - for example, a Forex trading strategy request "
            "may require deep research even if the word \"research\" never appears.\n\n"
            f"Objective:\n{objective}\n\n"
            f"Available departments:\n{department_descriptions}\n\n"
            "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
            '{"departments": ["<department_id>", ...], "reasoning": "<one or two '
            'sentences>"}\n'
            'Use an empty list for "departments" if the objective genuinely does not '
            "belong to any of the departments listed above."
        )

        try:
            raw = self._model_gateway.generate(requester="coo:classify", prompt=prompt)
        except Exception as exc:  # noqa: BLE001 - re-raised as a classification error
            raise DepartmentClassificationError(f"Classification call failed: {exc}") from exc

        try:
            data = json.loads(strip_code_fence(raw))
            department_ids = data["departments"]
            reasoning = data["reasoning"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise DepartmentClassificationError(
                f"Classifier response was not valid JSON in the expected shape: {raw!r}"
            ) from exc

        eligible_ids = {d.id for d in eligible}
        matched = [d for d in eligible if d.id in department_ids and d.id in eligible_ids]
        matched.sort(key=_canonical_sort_key)

        return ObjectiveClassification(matched_departments=matched, reasoning=reasoning)


_CLASSIFIERS = ("keyword", "llm")


def create_classifier_from_env(
    model_gateway: ModelGateway, env: Mapping[str, str] | None = None
) -> DepartmentClassifier:
    """DEPARTMENT_CLASSIFIER env var: "keyword" (default) or "llm" - exactly parallel to
    shared.providers.create_provider_from_env()'s MODEL_PROVIDER switch."""

    source = env if env is not None else os.environ
    selected = source.get("DEPARTMENT_CLASSIFIER", "keyword").strip().lower()

    if selected == "keyword":
        return KeywordDepartmentClassifier()
    if selected == "llm":
        return LLMDepartmentClassifier(model_gateway)

    raise ValueError(f"Unknown DEPARTMENT_CLASSIFIER={selected!r}; expected one of {_CLASSIFIERS}.")
