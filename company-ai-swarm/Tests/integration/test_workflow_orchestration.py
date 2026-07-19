"""Phase 6 exit-criteria test: MVS Test Category 004 (COO Orchestration), using a
two-department objective.

Source: IMPLEMENTATION_PLAN.md Phase 6 test spec:
    1. Submit an objective requiring both research and engineering capability.
    2. Confirm the COO decomposes it into a workflow spanning Research -> Engineering.
    3. Confirm both agents' outputs are captured and sequenced correctly per their
       dependency.

Exit criteria: a workflow crossing two departments completes correctly, in the right order,
without manual intervention. This is EIB's MVP Build Order Version 0.2.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, NoMatchingDepartmentError, WorkflowObjectiveOutcome
from orchestrator.decisions import get_decision
from orchestrator.department_registry import DepartmentRegistry
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]

TWO_DEPARTMENT_OBJECTIVE = "Research market analysis and build working software"


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


@pytest.fixture()
def coo(session: Session) -> COOOrchestrator:
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()

    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    for agent_id, department in [
        ("research_agent_001", "research"),
        ("engineering_agent_001", "engineering"),
    ]:
        create_identity(
            session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department
        )
        grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
        grant_permission(session, subject=agent_id, resource="memory:department", action="read")

    telemetry = TelemetrySink()
    gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)

    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=gateway,
        telemetry=telemetry,
    )


class TestWorkflowOrchestrationMVS004:
    def test_objective_matches_both_departments_in_canonical_order(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session, TWO_DEPARTMENT_OBJECTIVE, required_output="working code with a supporting summary"
        )

        assert isinstance(outcome, WorkflowObjectiveOutcome)
        assert [d.id for d in outcome.matched_departments] == ["research", "engineering"]

    def test_workflow_executes_both_agents_in_sequence_and_succeeds(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session, TWO_DEPARTMENT_OBJECTIVE, required_output="working code with a supporting summary"
        )

        assert outcome.objective_achieved is True
        assert [t.department.id for t in outcome.workflow.tasks] == ["research", "engineering"]
        assert [t.agent_id for t in outcome.workflow.tasks] == [
            "research_agent_001",
            "engineering_agent_001",
        ]
        for task in outcome.workflow.tasks:
            assert task.execution_result.output != ""
            assert task.validation.objective_achieved is True

    def test_decision_record_captures_both_agents_and_outcome(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session, TWO_DEPARTMENT_OBJECTIVE, required_output="working code with a supporting summary"
        )

        record = get_decision(session, outcome.decision_id)

        assert record is not None
        assert record.agents_selected == ["research_agent_001", "engineering_agent_001"]
        assert "research" in record.chosen_action and "engineering" in record.chosen_action
        assert record.outcome is not None
        assert "objective_achieved=True" in record.outcome
        assert "tasks_completed=2/2" in record.outcome

    def test_single_department_objective_still_uses_phase5_path(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        """Phase 6 must not regress Phase 5: an objective matching only one department
        still returns the original ObjectiveOutcome shape, not a workflow."""
        from orchestrator.controller import ObjectiveOutcome

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary with sources"
        )

        assert isinstance(outcome, ObjectiveOutcome)
        assert outcome.task_profile.matched_department.id == "research"

    def test_objective_with_no_matching_department_is_still_rejected(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        with pytest.raises(NoMatchingDepartmentError):
            coo.receive_objective(session, "xyz qqq zzz", required_output="anything")
