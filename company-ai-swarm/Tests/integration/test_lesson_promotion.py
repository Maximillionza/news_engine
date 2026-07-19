"""Phase 9: the tiered Learn step (COOS sec.6), IMPLEMENTATION_PLAN.md Phase 9's deliverable.

Covers what Tests/acceptance/test_mvs_acceptance.py's MVS-005 test doesn't: the minor/
critical promotion split itself (orchestrator/controller.py._learn, memory_service/
promotion.py), Business-As-Usual continuing while a critical promotion is pending, the
approve/reject workflow, and the best-effort fallback when the COO lacks memory-write
permission.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from identity_service.models import EntityType
from identity_service.repository import create_identity
from memory_service.models import MemoryObject, MemoryTier
from memory_service.promotion import (
    approve_promotion,
    list_pending_promotions,
    reject_promotion,
)
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, WorkflowObjectiveOutcome
from orchestrator.decisions import get_decision
from orchestrator.department_registry import DepartmentRegistry
from security_service.audit import get_audit_trail
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]

OPERATIONS_ONLY_OBJECTIVE = "Monitor workflow quality and evaluate the outcome."


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def _grant_agent(session: Session, agent_id: str, department: str, *, memory_write: bool = True) -> None:
    create_identity(
        session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department
    )
    grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
    grant_permission(session, subject=agent_id, resource="memory:department", action="read")
    if memory_write:
        grant_permission(session, subject=agent_id, resource="memory:department", action="write")


def _grant_coo(session: Session, coo_id: str = "coo") -> None:
    create_identity(session, id=coo_id, entity_type=EntityType.SERVICE, name="COO")
    grant_permission(session, subject=coo_id, resource="memory:historical", action="write")
    grant_permission(session, subject=coo_id, resource="memory:project", action="write")


def _make_coo(session: Session, *, grant_coo_memory: bool = True) -> COOOrchestrator:
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()
    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    telemetry = TelemetrySink()
    gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)

    if grant_coo_memory:
        _grant_coo(session)
    else:
        create_identity(session, id="coo", entity_type=EntityType.SERVICE, name="COO")

    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=gateway,
        telemetry=telemetry,
    )


class TestMinorLessonAutoApproved:
    def test_clean_run_writes_a_historical_lesson_and_no_pending_promotion(self, session: Session) -> None:
        _grant_agent(session, "research_agent_001", "research")
        coo = _make_coo(session)

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        lessons = (
            session.query(MemoryObject)
            .filter(MemoryObject.tier == MemoryTier.HISTORICAL)
            .all()
        )
        assert len(lessons) == 1
        assert outcome.execution_result.output in lessons[0].content or lessons[0].content != ""

        record = get_decision(session, outcome.decision_id)
        assert "promotion=auto-approved" in record.outcome
        assert list_pending_promotions(session) == []


class TestCriticalLessonHeldPendingApproval:
    def test_escalating_run_writes_a_project_tier_lesson_pending_approval(
        self, session: Session
    ) -> None:
        _grant_agent(session, "review_agent_001", "operations")
        coo = _make_coo(session)

        outcome = coo.receive_objective(
            session, OPERATIONS_ONLY_OBJECTIVE, required_output="A quality assessment"
        )
        assert isinstance(outcome, WorkflowObjectiveOutcome)
        assert outcome.workflow.gate_superficial is True  # this is what makes it "critical"

        pending = list_pending_promotions(session)
        assert len(pending) == 1
        promotion = pending[0]

        memory = session.get(MemoryObject, promotion.memory_object_id)
        assert memory.tier == MemoryTier.PROJECT
        assert memory.project_id == outcome.decision_id

        record = get_decision(session, outcome.decision_id)
        assert "promotion=pending_approval" in record.outcome

        # Not promoted to Historical yet:
        historical = session.query(MemoryObject).filter(MemoryObject.tier == MemoryTier.HISTORICAL).all()
        assert historical == []

    def test_business_as_usual_continues_while_a_promotion_is_pending(self, session: Session) -> None:
        _grant_agent(session, "review_agent_001", "operations")
        _grant_agent(session, "research_agent_001", "research")
        coo = _make_coo(session)

        coo.receive_objective(session, OPERATIONS_ONLY_OBJECTIVE, required_output="A quality assessment")
        assert len(list_pending_promotions(session)) == 1

        # A second, unrelated objective is unaffected - approval is asynchronous, never
        # blocks the orchestrator.
        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )
        assert outcome.validation.objective_achieved is True


class TestApproveAndRejectPromotion:
    def test_approving_writes_a_new_historical_memory_without_mutating_the_pending_one(
        self, session: Session
    ) -> None:
        _grant_agent(session, "review_agent_001", "operations")
        coo = _make_coo(session)
        coo.receive_objective(session, OPERATIONS_ONLY_OBJECTIVE, required_output="A quality assessment")
        promotion = list_pending_promotions(session)[0]
        pending_memory_id = promotion.memory_object_id

        create_identity(session, id="director_001", entity_type=EntityType.HUMAN, name="Director")
        grant_permission(session, subject="director_001", resource="memory:historical", action="write")

        historical_memory = approve_promotion(
            session, promotion.id, approver_identity_id="director_001", note="Aligned with framework."
        )

        assert historical_memory.tier == MemoryTier.HISTORICAL
        assert historical_memory.id == f"{pending_memory_id}-HIST"

        still_pending_memory = session.get(MemoryObject, pending_memory_id)
        assert still_pending_memory.tier == MemoryTier.PROJECT  # never mutated in place

        assert list_pending_promotions(session) == []

    def test_rejecting_leaves_no_historical_memory(self, session: Session) -> None:
        _grant_agent(session, "review_agent_001", "operations")
        coo = _make_coo(session)
        coo.receive_objective(session, OPERATIONS_ONLY_OBJECTIVE, required_output="A quality assessment")
        promotion = list_pending_promotions(session)[0]

        create_identity(session, id="director_001", entity_type=EntityType.HUMAN, name="Director")

        rejected = reject_promotion(
            session, promotion.id, approver_identity_id="director_001", note="Too case-specific."
        )

        assert rejected.status == "rejected"
        assert rejected.resolved_by == "director_001"
        historical = session.query(MemoryObject).filter(MemoryObject.tier == MemoryTier.HISTORICAL).all()
        assert historical == []

    def test_approving_an_already_resolved_promotion_raises(self, session: Session) -> None:
        _grant_agent(session, "review_agent_001", "operations")
        coo = _make_coo(session)
        coo.receive_objective(session, OPERATIONS_ONLY_OBJECTIVE, required_output="A quality assessment")
        promotion = list_pending_promotions(session)[0]
        create_identity(session, id="director_001", entity_type=EntityType.HUMAN, name="Director")
        reject_promotion(session, promotion.id, approver_identity_id="director_001")

        with pytest.raises(ValueError):
            approve_promotion(session, promotion.id, approver_identity_id="director_001")


class TestLearnIsBestEffort:
    def test_missing_coo_memory_permission_is_audited_not_raised(self, session: Session) -> None:
        _grant_agent(session, "research_agent_001", "research")
        coo = _make_coo(session, grant_coo_memory=False)  # coo identity exists, no memory grants

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        assert outcome.validation.objective_achieved is True  # the objective itself still succeeded

        trail = get_audit_trail(session, "coo")
        assert any(r.action.startswith("learn:") and r.decision == "denied" for r in trail)

        record = get_decision(session, outcome.decision_id)
        assert "promotion=skipped" in record.outcome
