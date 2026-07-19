"""Policy Impact Analysis.

Source: Specifications/3 - execution-framework/MVP Validation Specification (MVS).md sec.12
(Test Category 008): Policy Added -> Impact Analysis -> Workflow Review -> Control
Recommendation.

Honest scope: "Impact Analysis" is keyword-overlap matching between the policy's description
and each department's name/purpose/mission/capabilities - the same weak-but-real mechanism
already used for objective-to-department routing (orchestrator/planner.py's
select_all_matching_departments), reused rather than inventing a second matcher. "Workflow
Review" is the resulting list of affected departments. "Control Recommendation" is a
templated string naming the policy and affected departments, not an AI-generated
recommendation - no real model is wired anywhere in this corpus yet (shared/model_gateway.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm import Session

from compliance_service.models import PolicyImpactAssessment
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry

_WORD_RE = re.compile(r"[a-zA-Z_]+")


@dataclass
class PolicyRequirement:
    name: str
    description: str


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text) if len(w) > 3}


def _department_corpus(department: DepartmentDefinition) -> set[str]:
    text = " ".join([department.name, department.purpose, department.mission, *department.capabilities])
    return _tokenize(text)


def analyze_policy_impact(
    session: Session, *, policy: PolicyRequirement, department_registry: DepartmentRegistry
) -> PolicyImpactAssessment:
    policy_tokens = _tokenize(policy.description)
    affected = [
        d.id
        for d in department_registry.all()
        if d.agents and (policy_tokens & _department_corpus(d))
    ]

    if affected:
        control_recommendation = (
            f"Review and update controls in {affected} to address '{policy.name}': "
            f"{policy.description}"
        )
    else:
        control_recommendation = (
            f"No department's capabilities overlapped '{policy.name}' by keyword - escalate "
            f"to a human for manual impact assessment rather than assuming no impact."
        )

    evidence = {
        "policy_name": policy.name,
        "policy_description": policy.description,
        "affected_departments": affected,
        "matching_method": "keyword_overlap",
    }

    record = PolicyImpactAssessment(
        id=f"PIA-{uuid4().hex[:8]}",
        policy_name=policy.name,
        policy_description=policy.description,
        affected_departments=affected,
        control_recommendation=control_recommendation,
        evidence=evidence,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
