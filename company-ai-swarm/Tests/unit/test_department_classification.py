"""KeywordDepartmentClassifier must reproduce orchestrator/planner.py's exact existing
matching behavior - this is a relocation of that logic behind a swappable interface
(Documentation/plans/2026-07-19-dynamic-department-routing-design.md Section 3.3), not a
rewrite. Uses the same in-memory DepartmentRegistry construction pattern as
Tests/integration/test_coo_orchestration.py.
"""

from __future__ import annotations

from orchestrator.classification import KeywordDepartmentClassifier, ObjectiveClassification
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry


def _registry(*departments: DepartmentDefinition) -> DepartmentRegistry:
    registry = DepartmentRegistry(".")  # path unused - we populate directly
    for department in departments:
        registry._departments[department.id] = department
    return registry


def test_matches_department_by_keyword_overlap() -> None:
    research = DepartmentDefinition(
        id="research",
        name="Research Department",
        purpose="Information acquisition, analysis, and intelligence generation.",
        mission="Acquire and analyse information required by enterprise objectives.",
        capabilities=["research", "analysis", "reporting"],
        agents=["research_agent_001"],
    )
    registry = _registry(research)

    result = KeywordDepartmentClassifier().classify("Research current market trends.", registry)

    assert isinstance(result, ObjectiveClassification)
    assert [d.id for d in result.matched_departments] == ["research"]
    assert "research" in result.reasoning


def test_excludes_departments_with_no_agents() -> None:
    """The empty-roster fix from orchestrator/planner.py: a department with no agents.yaml
    entries must never be considered a viable match, even if its text scores higher."""

    strategy = DepartmentDefinition(
        id="strategy",
        name="Strategy Department",
        purpose="Market intelligence and strategic planning.",
        mission="Provide market intelligence for enterprise strategy.",
        capabilities=[],
        agents=[],  # no agents - must be excluded
    )
    research = DepartmentDefinition(
        id="research",
        name="Research Department",
        purpose="Information acquisition and analysis.",
        mission="Acquire market intelligence and information.",
        capabilities=["research"],
        agents=["research_agent_001"],
    )
    registry = _registry(strategy, research)

    result = KeywordDepartmentClassifier().classify("Create a market intelligence report", registry)

    assert [d.id for d in result.matched_departments] == ["research"]


def test_no_keyword_overlap_returns_empty_with_reasoning() -> None:
    research = DepartmentDefinition(
        id="research", name="Research Department", purpose="Research.", mission="Research.",
        capabilities=["research"], agents=["research_agent_001"],
    )
    registry = _registry(research)

    result = KeywordDepartmentClassifier().classify("xyz qqq zzz", registry)

    assert result.matched_departments == []
    assert "No department" in result.reasoning


def test_multiple_departments_sorted_in_canonical_order() -> None:
    engineering = DepartmentDefinition(
        id="engineering", name="Engineering Department", purpose="Build systems.",
        mission="Engineering build.", capabilities=["engineering", "build"],
        agents=["engineering_agent_001"],
    )
    research = DepartmentDefinition(
        id="research", name="Research Department", purpose="Research analysis.",
        mission="Research analysis.", capabilities=["research", "analysis"],
        agents=["research_agent_001"],
    )
    registry = _registry(engineering, research)  # inserted out of canonical order

    result = KeywordDepartmentClassifier().classify(
        "Research and build an engineering analysis system", registry
    )

    assert [d.id for d in result.matched_departments] == ["research", "engineering"]
