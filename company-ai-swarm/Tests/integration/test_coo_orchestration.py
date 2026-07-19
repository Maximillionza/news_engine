"""Phase 5 exit-criteria test: MVS Test Category 001 (Objective Execution), constrained to
Research only.

Source: IMPLEMENTATION_PLAN.md Phase 5 test spec:
    1. Submit "Create a market intelligence report" (per CCBP's Definition of Done example).
    2. Confirm COO analyzes the objective, creates a task, assigns Research Agent,
       executes, and returns output.
    3. Confirm a COO Decision Record was written with reasoning, chosen action, and
       outcome.

Exit criteria: end-to-end objective -> COO -> single agent -> output succeeds
reproducibly. This is EIB's MVP Build Order Version 0.1.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, NoMatchingDepartmentError
from orchestrator.decisions import get_decision
from orchestrator.department_registry import DepartmentRegistry
from agent_runtime.registry import AgentRegistry
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]


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

    # Grant the Research Agent the permissions it needs to execute (Phase 4's Check
    # Policies gate) and to read department memory (Phase 4's Retrieve Knowledge step).
    create_identity(
        session, id="research_agent_001", entity_type=EntityType.AGENT, name="Research Agent", department="research"
    )
    grant_permission(session, subject="research_agent_001", resource="agent_execution:research_agent_001", action="execute")
    grant_permission(session, subject="research_agent_001", resource="memory:department", action="read")

    telemetry = TelemetrySink()
    gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)

    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=gateway,
        telemetry=telemetry,
    )


class TestObjectiveExecutionMVS001:
    def test_objective_routes_to_research_department(self, session: Session, coo: COOOrchestrator) -> None:
        outcome = coo.receive_objective(
            session,
            "Create a market intelligence report",
            required_output="A structured summary with sources",
        )

        assert outcome.task_profile.matched_department is not None
        assert outcome.task_profile.matched_department.id == "research"

    def test_research_agent_is_assigned_and_executes(self, session: Session, coo: COOOrchestrator) -> None:
        outcome = coo.receive_objective(
            session,
            "Create a market intelligence report",
            required_output="A structured summary with sources",
        )

        assert outcome.execution_result.output != ""
        assert outcome.validation.objective_achieved is True

    def test_decision_record_has_reasoning_chosen_action_and_outcome(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session,
            "Create a market intelligence report",
            required_output="A structured summary with sources",
        )

        record = get_decision(session, outcome.decision_id)

        assert record is not None
        assert record.objective == "Create a market intelligence report"
        assert record.reasoning != ""
        assert "research_agent_001" in record.chosen_action
        assert record.agents_selected == ["research_agent_001"]
        assert record.outcome is not None
        assert "objective_achieved=True" in record.outcome

    def test_end_to_end_flow_succeeds_reproducibly(self, session: Session, coo: COOOrchestrator) -> None:
        """Exit criterion: 'succeeds reproducibly' - not a one-off fluke."""

        for _ in range(3):
            outcome = coo.receive_objective(
                session,
                "Create a market intelligence report",
                required_output="A structured summary with sources",
            )
            assert outcome.validation.objective_achieved is True
            assert outcome.task_profile.matched_department.id == "research"

    def test_objective_with_no_matching_department_is_rejected_but_recorded(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        with pytest.raises(NoMatchingDepartmentError):
            coo.receive_objective(session, "xyz qqq zzz", required_output="anything")

        # Even a rejected objective produces a governance record (COOS sec.22) - the COO
        # does not fail silently.
        from orchestrator.models import COODecisionRecord

        all_records = session.query(COODecisionRecord).all()
        rejected = [r for r in all_records if r.chosen_action.startswith("reject")]
        assert len(rejected) == 1
        assert rejected[0].objective == "xyz qqq zzz"
