"""Complexity/Risk/Required-Model-Tier estimation.

Source: Specifications/1 - enterprise-architecture/Enterprise Workflow Orchestration
Specification (EWOS).md sec.11 (Task Definition's Complexity, Risk, Required Model Tier
fields) and Task Definition Language (TDL).md sec.7's 5-level Task Complexity Model (Routine/
Standard/Advanced/Expert/Enterprise Critical) - already consumed by workflow_engine/review.py's
REVIEW_TIER_BY_COMPLEXITY table, which previously only ever received a fixed
"Level 2 Standard" from orchestrator/controller.py, so the "peer_review" row was the only one
Phase 7 could ever actually produce (see that module's docstring). This is the first real
producer for any of these fields.

Phase 20 (IMPLEMENTATION_PLAN.md, 2026-07-25) honesty note, same shape as review.py's own:
no numeric Task Complexity or Task Risk scoring algorithm exists anywhere in the source corpus
(TDL sec.7-8 define the scales, not how to compute a score), so this is a deliberately simple,
explicitly-stated heuristic, not a claim to replicate an undefined spec algorithm. It uses the
one signal reliably available before any department starts working - which/how many
departments the classifier matched - and is expected to get more precise as Phase 14's real
usage reveals whether department-count alone is a good enough proxy.

Risk uses its own three-level scale (low/medium/high) - no canonical Risk scale exists
anywhere in this corpus to match against (unlike Complexity's TDL sec.7 table), so this is a
new scale, not an implementation of something already defined.
"""

from __future__ import annotations

from dataclasses import dataclass

from orchestrator.department_registry import DepartmentDefinition

REVIEW_DEPARTMENT_ID = "operations"

COMPLEXITY_LEVELS = (
    "Level 1 Routine",
    "Level 2 Standard",
    "Level 3 Advanced",
    "Level 4 Expert",
    "Level 5 Enterprise Critical",
)

RISK_LEVELS = ("low", "medium", "high")

# Real model IDs (see this session's environment context for the current Claude line-up),
# not placeholders. "lean" is a genuinely cheaper/faster model than "standard" - there is no
# tier above "standard" wired yet: this codebase has no evidence any task it actually
# performs needs a bigger model's ceiling, and picking one without a real case to justify it
# would repeat the "capability nobody asked for" pattern this project has otherwise avoided.
# Add a "heavy" tier -> a specific department/agent that demonstrably needs it, not before.
MODEL_TIER_LEAN = "lean"
MODEL_TIER_STANDARD = "standard"
MODEL_TIERS = (MODEL_TIER_LEAN, MODEL_TIER_STANDARD)

MODEL_BY_TIER: dict[str, str] = {
    MODEL_TIER_LEAN: "claude-haiku-4-5-20251001",
    MODEL_TIER_STANDARD: "claude-sonnet-5",
}


@dataclass
class ComplexityAssessment:
    complexity_level: str
    risk_level: str
    required_model_tier: str
    reasoning: str


def assess_complexity(departments: list[DepartmentDefinition]) -> ComplexityAssessment:
    """`departments` is the classifier's full matched list (review department included, same
    convention execute_workflow() itself uses) - substantive count drives complexity; whether
    Compliance is among them drives risk, since governance/regulatory work is inherently
    higher-stakes than a same-size task without it."""

    substantive = [d for d in departments if d.id != REVIEW_DEPARTMENT_ID]
    count = len(substantive)
    has_compliance = any(d.id == "compliance" for d in substantive)

    if count <= 1:
        complexity_level = COMPLEXITY_LEVELS[0]
    elif count == 2:
        complexity_level = COMPLEXITY_LEVELS[1]
    elif count == 3:
        complexity_level = COMPLEXITY_LEVELS[2]
    else:
        complexity_level = COMPLEXITY_LEVELS[3]

    if has_compliance and count >= 3:
        risk_level = "high"
    elif has_compliance or count >= 3:
        risk_level = "medium"
    else:
        risk_level = "low"

    required_model_tier = (
        MODEL_TIER_STANDARD if (has_compliance or count >= 2) else MODEL_TIER_LEAN
    )

    reasoning = (
        f"{count} substantive department(s) matched "
        f"({[d.id for d in substantive]}); compliance involved: {has_compliance}."
    )

    return ComplexityAssessment(
        complexity_level=complexity_level,
        risk_level=risk_level,
        required_model_tier=required_model_tier,
        reasoning=reasoning,
    )
