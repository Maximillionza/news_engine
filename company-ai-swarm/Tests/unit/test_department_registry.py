"""Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3's Department
Head agent registration: `department.leader` promoted from department_registry.py's
catch-all `extra` dict to a first-class field, and the four dispatch-relevant departments
(research, engineering, compliance, operations) each carry a real head agent identity.
Strategy is deliberately excluded - its empty `agents` list already keeps it out of the
classifier's matches before triage would ever run.
"""

from __future__ import annotations

from pathlib import Path

from agent_runtime.registry import AgentRegistry
from orchestrator.department_registry import DepartmentRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]


def _departments() -> DepartmentRegistry:
    registry = DepartmentRegistry(REPO_ROOT / "departments")
    registry.load_all()
    return registry


def _agents() -> AgentRegistry:
    registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    registry.load_all()
    return registry


def test_leader_is_a_first_class_field_not_in_extra() -> None:
    research = _departments().get("research")

    assert research is not None
    assert research.leader == "research_head_001"
    assert "leader" not in research.extra


class TestDispatchRelevantDepartmentsHaveARegisteredHead:
    def test_research_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        research = departments.get("research")

        assert research is not None
        assert agents.get(research.leader) is not None
        assert research.leader not in research.agents

    def test_engineering_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        engineering = departments.get("engineering")

        assert engineering is not None
        assert agents.get(engineering.leader) is not None
        assert engineering.leader not in engineering.agents

    def test_compliance_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        compliance = departments.get("compliance")

        assert compliance is not None
        assert agents.get(compliance.leader) is not None
        assert compliance.leader not in compliance.agents

    def test_operations_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        operations = departments.get("operations")

        assert operations is not None
        assert agents.get(operations.leader) is not None
        assert operations.leader not in operations.agents


def test_strategy_has_no_head_by_design() -> None:
    departments, agents = _departments(), _agents()
    strategy = departments.get("strategy")

    assert strategy is not None
    assert strategy.leader == ""
    assert agents.get("strategy_head_001") is None
