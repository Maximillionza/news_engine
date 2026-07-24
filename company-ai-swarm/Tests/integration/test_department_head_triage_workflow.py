"""Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.5's
multi-department path: each substantive department's Head evaluates immediately before that
department's select_agent()+dispatch(). A reject halts forward progress the same way a failed
validation already does - no rollback, no reassignment.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, WorkflowObjectiveOutcome
from orchestrator.department_registry import DepartmentRegistry
from orchestrator.escalation import EscalationCondition
from orchestrator.escalations import list_pending_escalations
from orchestrator.head import HeadVerdict
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider
from workflow_engine.engine import execute_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]

TWO_DEPARTMENT_OBJECTIVE = "Research market analysis and build working software"


class _RejectSecondDepartmentHead:
    """Accepts the first department it's asked about, rejects every one after that - proves
    the halt happens mid-sequence, not before the first task runs."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def evaluate(self, department, objective, **_):
        self.calls.append(department.id)
        if len(self.calls) == 1:
            return HeadVerdict(accepted=True, reasoning="First department is fine.")
        return HeadVerdict(accepted=False, reasoning="Second department rejected.", suggested_department_id=None)


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def _grant(session: Session, agent_id: str, department: str) -> None:
    create_identity(session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department)
    grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
    grant_permission(session, subject=agent_id, resource="memory:department", action="read")


def _registries() -> tuple[DepartmentRegistry, AgentRegistry]:
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()
    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()
    return department_registry, agent_registry


def test_execute_workflow_halts_when_a_substantive_departments_head_rejects(session: Session) -> None:
    department_registry, agent_registry = _registries()
    _grant(session, "research_agent_001", "research")
    _grant(session, "engineering_agent_001", "engineering")
    head = _RejectSecondDepartmentHead()

    run = execute_workflow(
        session,
        coo_id="coo",
        objective=TWO_DEPARTMENT_OBJECTIVE,
        required_output="working code with a supporting summary",
        departments=[department_registry.get("research"), department_registry.get("engineering")],
        agent_registry=agent_registry,
        model_gateway=ModelGateway(StubModelProvider()),
        head=head,
    )

    assert run.succeeded is False
    assert run.blocked_reason is not None
    assert run.blocked_reason.startswith("department_rejected:")
    assert "Second department rejected" in run.blocked_reason
    # Earlier task is present and untouched - no rollback.
    assert len(run.tasks) == 1
    assert run.tasks[0].department.id == "research"
    assert head.calls == ["research", "engineering"]


def test_receive_objective_maps_the_reject_to_department_rejected_not_dependency_gap(session: Session) -> None:
    department_registry, agent_registry = _registries()
    _grant(session, "research_agent_001", "research")
    _grant(session, "engineering_agent_001", "engineering")
    telemetry = TelemetrySink()

    coo = COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=ModelGateway(StubModelProvider(), telemetry=telemetry),
        telemetry=telemetry,
        head=_RejectSecondDepartmentHead(),
    )

    outcome = coo.receive_objective(
        session, TWO_DEPARTMENT_OBJECTIVE, required_output="working code with a supporting summary"
    )

    assert isinstance(outcome, WorkflowObjectiveOutcome)
    assert outcome.workflow.succeeded is False

    pending = list_pending_escalations(session)
    conditions = [p.condition for p in pending]
    assert EscalationCondition.DEPARTMENT_REJECTED.value in conditions
    assert EscalationCondition.UNRESOLVABLE_DEPENDENCY_GAP.value not in conditions


class _ResolvesFirstDepartmentDirectlyHead:
    """Phase 16 (IMPLEMENTATION_PLAN.md, 2026-07-23): resolves the first department itself,
    accepts the rest normally - proves resolve_verdict_execution() is applied per-department
    in the multi-department loop, not all-or-nothing across the whole workflow."""

    def evaluate(self, department, objective, **_):
        if department.id == "research":
            return HeadVerdict(
                accepted=True,
                reasoning="Simple enough to answer directly.",
                resolved_output="Market analysis: sideways, low volatility.",
            )
        return HeadVerdict(accepted=True, reasoning="Genuinely engineering work.")


class _NeedsSpecialistFirstDepartmentHead:
    def evaluate(self, department, objective, **_):
        if department.id == "research":
            return HeadVerdict(
                accepted=True,
                reasoning="Requires deep statistical modeling beyond my own depth.",
                needs_specialist=True,
            )
        return HeadVerdict(accepted=True, reasoning="Genuinely engineering work.")


def test_execute_workflow_uses_head_direct_resolution_for_one_department(session: Session) -> None:
    department_registry, agent_registry = _registries()
    _grant(session, "research_head_001", "research")
    _grant(session, "engineering_agent_001", "engineering")

    run = execute_workflow(
        session,
        coo_id="coo",
        objective=TWO_DEPARTMENT_OBJECTIVE,
        required_output="working code with a supporting summary",
        departments=[department_registry.get("research"), department_registry.get("engineering")],
        agent_registry=agent_registry,
        model_gateway=ModelGateway(StubModelProvider()),
        head=_ResolvesFirstDepartmentDirectlyHead(),
    )

    assert run.succeeded is True
    research_task = next(t for t in run.tasks if t.department.id == "research")
    assert research_task.agent_id == "research_head_001"
    assert research_task.execution_result.output == "Market analysis: sideways, low volatility."
    # The second department is completely unaffected - normal select_agent()+dispatch().
    engineering_task = next(t for t in run.tasks if t.department.id == "engineering")
    assert engineering_task.agent_id == "engineering_agent_001"


def test_execute_workflow_spawns_specialist_for_one_department(session: Session) -> None:
    department_registry, agent_registry = _registries()
    _grant(session, "research_head_001", "research")
    _grant(session, "engineering_agent_001", "engineering")

    run = execute_workflow(
        session,
        coo_id="coo",
        objective=TWO_DEPARTMENT_OBJECTIVE,
        required_output="working code with a supporting summary",
        departments=[department_registry.get("research"), department_registry.get("engineering")],
        agent_registry=agent_registry,
        model_gateway=ModelGateway(StubModelProvider()),
        head=_NeedsSpecialistFirstDepartmentHead(),
    )

    assert run.succeeded is True
    research_task = next(t for t in run.tasks if t.department.id == "research")
    assert research_task.agent_id == "research_head_001"
    assert research_task.execution_result.artifact["resolved_by"] == "specialist"
