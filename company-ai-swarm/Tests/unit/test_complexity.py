"""workflow_engine.complexity.assess_complexity() - the first real producer for
Complexity/Risk/Required Model Tier (Phase 20, IMPLEMENTATION_PLAN.md, 2026-07-25). Pure
function, no session/model_gateway needed - only DepartmentDefinition objects."""

from __future__ import annotations

from orchestrator.department_registry import DepartmentDefinition
from workflow_engine.complexity import (
    MODEL_BY_TIER,
    MODEL_TIER_LEAN,
    MODEL_TIER_STANDARD,
    assess_complexity,
)


def _dept(dept_id: str) -> DepartmentDefinition:
    return DepartmentDefinition(
        id=dept_id,
        name=dept_id.title(),
        purpose="",
        mission="",
        leader=f"{dept_id}_head_001",
        capabilities=[],
        agents=[f"{dept_id}_agent_001"],
    )


def test_single_department_is_routine_and_lean() -> None:
    result = assess_complexity([_dept("research")])

    assert result.complexity_level == "Level 1 Routine"
    assert result.risk_level == "low"
    assert result.required_model_tier == MODEL_TIER_LEAN


def test_two_departments_is_standard_and_needs_standard_tier() -> None:
    result = assess_complexity([_dept("research"), _dept("engineering")])

    assert result.complexity_level == "Level 2 Standard"
    assert result.required_model_tier == MODEL_TIER_STANDARD


def test_three_departments_is_advanced() -> None:
    result = assess_complexity([_dept("research"), _dept("engineering"), _dept("compliance")])

    assert result.complexity_level == "Level 3 Advanced"


def test_four_or_more_departments_is_expert() -> None:
    result = assess_complexity(
        [_dept("research"), _dept("engineering"), _dept("compliance"), _dept("strategy")]
    )

    assert result.complexity_level == "Level 4 Expert"


def test_review_department_excluded_from_substantive_count() -> None:
    """operations (Review) never counts toward complexity - execute_workflow()'s own
    convention passes the full matched list including it."""

    result = assess_complexity([_dept("research"), _dept("engineering"), _dept("operations")])

    assert result.complexity_level == "Level 2 Standard"


def test_compliance_alone_raises_risk_to_medium_and_needs_standard_tier() -> None:
    """Unlike department *count*, compliance involvement alone is enough to require the
    standard tier even for a single department - governance/regulatory work is treated as
    higher-stakes than a same-size task without it, regardless of headcount."""

    result = assess_complexity([_dept("compliance")])

    assert result.risk_level == "medium"
    assert result.required_model_tier == MODEL_TIER_STANDARD


def test_compliance_with_three_departments_is_high_risk() -> None:
    result = assess_complexity([_dept("research"), _dept("engineering"), _dept("compliance")])

    assert result.risk_level == "high"


def test_no_departments_is_routine_and_low_risk() -> None:
    result = assess_complexity([])

    assert result.complexity_level == "Level 1 Routine"
    assert result.risk_level == "low"
    assert result.required_model_tier == MODEL_TIER_LEAN


def test_reasoning_mentions_department_count_and_compliance_involvement() -> None:
    result = assess_complexity([_dept("research"), _dept("compliance")])

    assert "2 substantive department(s)" in result.reasoning
    assert "compliance involved: True" in result.reasoning


def test_model_by_tier_maps_to_real_model_ids() -> None:
    assert MODEL_BY_TIER[MODEL_TIER_LEAN] == "claude-haiku-4-5-20251001"
    assert MODEL_BY_TIER[MODEL_TIER_STANDARD] == "claude-sonnet-5"
