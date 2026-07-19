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

import re
from dataclasses import dataclass
from typing import Protocol

from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry

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
