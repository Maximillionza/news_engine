"""Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.1's
single-department path: up to 2 attempts total, then DepartmentRejectedError. Uses a
scripted test double implementing orchestrator.head.DepartmentHead, not a real dispatch() -
Task 1's test_department_head.py already covers LLMDepartmentHead's own JSON parsing in
isolation; this file covers COOOrchestrator's retry/validation logic around whatever verdict
a DepartmentHead returns.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, DepartmentRejectedError, ObjectiveOutcome
from orchestrator.department_registry import DepartmentRegistry
from orchestrator.escalation import EscalationCondition
from orchestrator.escalations import list_pending_escalations
from orchestrator.head import HeadVerdict
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]

OBJECTIVE = "Create a market intelligence report"


class _ScriptedHead:
    """Returns one scripted verdict per call, in order. Raises if called more times than
    scripted - a test bug, not swallowed."""

    def __init__(self, verdicts: list[HeadVerdict]) -> None:
        self._verdicts = list(verdicts)
        self.calls: list[str] = []

    def evaluate(self, department, objective, **_):
        self.calls.append(department.id)
        return self._verdicts.pop(0)


class _RaisingHead:
    def evaluate(self, department, objective, **_):
        raise RuntimeError("head service unavailable")


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


def _make_coo(session: Session, *, head) -> COOOrchestrator:
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()
    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    _grant(session, "research_agent_001", "research")
    _grant(session, "engineering_agent_001", "engineering")

    telemetry = TelemetrySink()
    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=ModelGateway(StubModelProvider(), telemetry=telemetry),
        telemetry=telemetry,
        head=head,
    )


def test_accept_on_first_attempt_proceeds_normally(session: Session) -> None:
    head = _ScriptedHead([HeadVerdict(accepted=True, reasoning="Fits research.")])
    coo = _make_coo(session, head=head)

    outcome = coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert isinstance(outcome, ObjectiveOutcome)
    assert outcome.task_profile.matched_department.id == "research"
    assert head.calls == ["research"]


def test_reject_then_accept_at_suggested_department_succeeds_on_second_attempt(session: Session) -> None:
    head = _ScriptedHead(
        [
            HeadVerdict(accepted=False, reasoning="Not research.", suggested_department_id="engineering"),
            HeadVerdict(accepted=True, reasoning="Fits engineering."),
        ]
    )
    coo = _make_coo(session, head=head)

    outcome = coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert isinstance(outcome, ObjectiveOutcome)
    assert outcome.task_profile.matched_department.id == "engineering"
    assert head.calls == ["research", "engineering"]


def test_reject_reject_exhausts_the_cap_and_raises(session: Session) -> None:
    head = _ScriptedHead(
        [
            HeadVerdict(accepted=False, reasoning="Not research.", suggested_department_id="engineering"),
            HeadVerdict(accepted=False, reasoning="Not engineering either.", suggested_department_id=None),
        ]
    )
    coo = _make_coo(session, head=head)

    with pytest.raises(DepartmentRejectedError, match="Not engineering either"):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert head.calls == ["research", "engineering"]
    pending = list_pending_escalations(session)
    assert len(pending) == 1
    assert pending[0].condition == EscalationCondition.DEPARTMENT_REJECTED.value


def test_reject_with_no_suggestion_raises_immediately_without_a_second_attempt(session: Session) -> None:
    head = _ScriptedHead([HeadVerdict(accepted=False, reasoning="Not worth it.", suggested_department_id=None)])
    coo = _make_coo(session, head=head)

    with pytest.raises(DepartmentRejectedError, match="Not worth it"):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert head.calls == ["research"]


def test_reject_with_hallucinated_suggestion_is_treated_as_no_suggestion(session: Session) -> None:
    head = _ScriptedHead(
        [HeadVerdict(accepted=False, reasoning="Not research.", suggested_department_id="made_up_department")]
    )
    coo = _make_coo(session, head=head)

    with pytest.raises(DepartmentRejectedError):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert head.calls == ["research"]


def test_reject_with_already_attempted_suggestion_is_treated_as_no_suggestion(session: Session) -> None:
    head = _ScriptedHead(
        [HeadVerdict(accepted=False, reasoning="Circular suggestion.", suggested_department_id="research")]
    )
    coo = _make_coo(session, head=head)

    with pytest.raises(DepartmentRejectedError):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert head.calls == ["research"]


def test_head_call_failure_writes_technical_failure_escalation_then_reraises(session: Session) -> None:
    coo = _make_coo(session, head=_RaisingHead())

    with pytest.raises(RuntimeError, match="head service unavailable"):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    pending = list_pending_escalations(session)
    assert len(pending) == 1
    assert pending[0].condition == EscalationCondition.TECHNICAL_FAILURE.value
    assert pending[0].is_technical_failure is True
