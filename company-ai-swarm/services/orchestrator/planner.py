"""Objective Understanding + Task Classification.

Source: Specifications/1 - enterprise-architecture/The Company COO Orchestrator
Specification (COOS).md sec.7 (Objective Understanding Engine) and sec.8 (Task
Classification Engine).

Honesty note, consistent with shared/model_gateway.py's: COOS sec.9's Complexity Scoring
Model has no numeric weights or thresholds anywhere in the source corpus (confirmed during
the Specifications/ reconciliation and re-confirmed in Phase 4's technology_decisions.md).
This module does not pretend to implement that scoring - `complexity_level` below is a fixed
default for Phase 5's single, well-understood task shape, not a computed value. A real
complexity classifier is future work, not a Phase 5 gap this module papers over.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import uuid4

from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry

_WORD_RE = re.compile(r"[a-zA-Z_]+")


@dataclass
class TaskProfile:
    task_id: str
    objective: str
    complexity_level: str
    matched_department: DepartmentDefinition | None
    match_score: int
    reasoning: str


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text) if len(w) > 3}


def _department_corpus(dept: DepartmentDefinition) -> set[str]:
    text = " ".join([dept.name, dept.purpose, dept.mission, *dept.capabilities])
    return _tokenize(text)


def select_best_matching_department(
    objective: str, registry: DepartmentRegistry
) -> tuple[DepartmentDefinition | None, int]:
    """Simple keyword-overlap classifier between the objective text and each department's
    name/purpose/mission/capabilities. This is a genuine (if weak) matcher, not a stub that
    always returns the same department - see the module docstring for why it stops here.

    Departments with no assigned agents are excluded from consideration entirely, not just
    deprioritized. This was found empirically, not designed up front: CRBS's example
    "Strategy Department" (departments/strategy/, deliberately left with no capabilities or
    agents - out of MVS-canonical scope per its own definition.yaml comment) scored *higher*
    than Research on "Create a market intelligence report" (its mission text happens to
    contain both "market" and "intelligence"). A department the COO cannot actually dispatch
    to is not a viable match regardless of text-similarity score - this filter is a genuine
    correctness fix to the Department Selection Engine, not test-tuning."""

    objective_tokens = _tokenize(objective)
    best_department: DepartmentDefinition | None = None
    best_score = 0
    for department in registry.all():
        if not department.agents:
            continue
        score = len(objective_tokens & _department_corpus(department))
        if score > best_score:
            best_score = score
            best_department = department
    return best_department, best_score


_CANONICAL_DEPARTMENT_ORDER = ["research", "engineering", "compliance", "operations"]


def select_all_matching_departments(
    objective: str, registry: DepartmentRegistry
) -> list[DepartmentDefinition]:
    """Phase 6 extension of select_best_matching_department() to multiple departments, for
    objectives that require more than one department's capability (IMPLEMENTATION_PLAN.md
    Phase 6, EWOS sec.16 Department Routing). Reuses the exact same keyword-overlap scoring -
    it does not fix the weakness already documented in
    Documentation/operations/technology_decisions.md, it only extends the same mechanism from
    picking one winner to collecting every department that scores above zero.

    Ordering is a fixed canonical department sequence, NOT the match score - EWOS sec.14
    (Sequential Execution) requires an execution order, but no dependency-graph mechanism
    exists in this corpus to derive one from EWOS sec.5's `Dependencies` field. The order used
    here mirrors this plan's own documented MVP activation sequence (Research -> Engineering +
    Compliance -> Review/Operations, see IMPLEMENTATION_PLAN.md's "Notes on scope
    discipline"). Departments not in the canonical list sort last, in registry order.

    Honesty note: every MVP department's definition.yaml already lists a capability-aligned
    agent as of Phase 5 (not just Research's) - this function can therefore already route to
    Compliance or Operations if an objective's vocabulary happens to score there, ahead of
    those departments' documented Phase 7/8 test activation. That is not a bug introduced
    here: department eligibility in this codebase has always been "has a capability-aligned
    agent in its definition.yaml," never a phase-gated allowlist. Phase 6's own test objective
    is chosen to exercise Research + Engineering specifically."""

    objective_tokens = _tokenize(objective)
    matched = [
        department
        for department in registry.all()
        if department.agents and len(objective_tokens & _department_corpus(department)) > 0
    ]

    def _sort_key(department: DepartmentDefinition) -> int:
        try:
            return _CANONICAL_DEPARTMENT_ORDER.index(department.id)
        except ValueError:
            return len(_CANONICAL_DEPARTMENT_ORDER)

    matched.sort(key=_sort_key)
    return matched


def analyze_objective(objective: str, registry: DepartmentRegistry) -> TaskProfile:
    department, score = select_best_matching_department(objective, registry)

    if department is None:
        reasoning = (
            f"No department's capabilities, purpose, or mission shared any keyword with "
            f"the objective. Cannot route without a human-specified department."
        )
    else:
        reasoning = (
            f"Matched department '{department.id}' with keyword-overlap score {score} "
            f"against its name/purpose/mission/capabilities."
        )

    return TaskProfile(
        task_id=f"TSK-{uuid4().hex[:8]}",
        objective=objective,
        # Fixed default - see module docstring. Label corrected in Phase 7 from "Level 2
        # Moderate" to "Level 2 Standard": nothing consumed this string before Phase 7 wired
        # it into TDL sec.17's review-tier table (workflow_engine/review.py), whose keys are
        # TDL sec.7's own tier names verbatim - the old label was a paraphrase that would
        # have silently failed to match any tier.
        complexity_level="Level 2 Standard",
        matched_department=department,
        match_score=score,
        reasoning=reasoning,
    )
