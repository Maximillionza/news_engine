"""Phase 11 exit-criteria test: MVS Test Category 011 (Evolution Validation).

Source: IMPLEMENTATION_PLAN.md Phase 11 test spec:
    1. Introduce a deliberately inefficient workflow.
    2. Confirm the Evolution Engine detects the inefficiency, requests a simulation, and
       produces an improvement proposal.
    3. Confirm the proposal requires explicit approval before being applied - the Evolution
       Engine cannot self-approve changes.

Exit criteria: the full loop (Observation -> Evolution Engine -> Simulation ->
Recommendation -> Approval -> Implementation) completes for at least one real inefficiency,
with human approval enforced as a hard gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from evolution_service.models import ProposalStatus
from evolution_service.pipeline import EvolutionApprovalError, EvolutionEngine
from identity_service.models import EntityType
from identity_service.repository import create_identity
from memory_service.models import MemoryObject, MemoryTier
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, WorkflowObjectiveOutcome
from orchestrator.department_registry import DepartmentRegistry
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]

# The same "operations only" objective used since Phase 8 to exercise the Gate Integrity
# Check - a real, reproducible inefficiency (a review with nothing to review), not one
# invented for this phase.
INEFFICIENT_OBJECTIVE = "Monitor workflow quality and evaluate the outcome."


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


@pytest.fixture()
def department_registry() -> DepartmentRegistry:
    registry = DepartmentRegistry(REPO_ROOT / "departments")
    registry.load_all()
    return registry


@pytest.fixture()
def agent_registry() -> AgentRegistry:
    registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    registry.load_all()
    return registry


def _make_coo(session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry) -> COOOrchestrator:
    create_identity(session, id="review_agent_001", entity_type=EntityType.AGENT, name="Review Agent")
    grant_permission(session, subject="review_agent_001", resource="agent_execution:review_agent_001", action="execute")
    grant_permission(session, subject="review_agent_001", resource="memory:department", action="read")

    telemetry = TelemetrySink()
    gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
    return COOOrchestrator(
        coo_id="coo", department_registry=department_registry, agent_registry=agent_registry,
        model_gateway=gateway, telemetry=telemetry,
    )


class TestEvolutionValidationMVS011:
    def test_step1_the_inefficient_workflow_is_reproducible(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        coo = _make_coo(session, department_registry, agent_registry)

        outcome = coo.receive_objective(session, INEFFICIENT_OBJECTIVE, required_output="A quality assessment")

        assert isinstance(outcome, WorkflowObjectiveOutcome)
        assert outcome.workflow.gate_superficial is True  # the observed inefficiency

    def test_step2_evolution_engine_detects_simulates_and_proposes(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        coo = _make_coo(session, department_registry, agent_registry)
        outcome = coo.receive_objective(session, INEFFICIENT_OBJECTIVE, required_output="A quality assessment")

        operations = department_registry.get("operations")
        engine = EvolutionEngine()

        proposal = engine.detect_and_propose(
            session,
            decision_id=outcome.decision_id,
            objective=INEFFICIENT_OBJECTIVE,
            required_output="A quality assessment",
            baseline_departments=[operations],
            proposed_departments=[],
            agent_registry=agent_registry,
        )

        assert proposal is not None
        assert proposal.approval_status == ProposalStatus.PENDING  # step 3's own precondition
        assert proposal.simulation_run_id is not None  # a simulation was actually requested
        assert "review" in proposal.reason.lower()

    def test_no_proposal_when_no_inefficiency_was_observed(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        """The engine does not fabricate an opportunity to have something to propose."""

        create_identity(session, id="research_agent_001", entity_type=EntityType.AGENT, name="Research Agent")
        grant_permission(session, subject="research_agent_001", resource="agent_execution:research_agent_001", action="execute")
        grant_permission(session, subject="research_agent_001", resource="memory:department", action="read")

        telemetry = TelemetrySink()
        gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
        coo = COOOrchestrator(
            coo_id="coo", department_registry=department_registry, agent_registry=agent_registry,
            model_gateway=gateway, telemetry=telemetry,
        )
        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        engine = EvolutionEngine()
        proposal = engine.detect_and_propose(
            session, decision_id=outcome.decision_id, objective="Create a market intelligence report",
            required_output="A structured summary", baseline_departments=[], proposed_departments=[],
            agent_registry=agent_registry,
        )

        assert proposal is None

    def test_step3_and_exit_criteria_full_loop_with_approval_as_a_hard_gate(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        # Observation:
        coo = _make_coo(session, department_registry, agent_registry)
        outcome = coo.receive_objective(session, INEFFICIENT_OBJECTIVE, required_output="A quality assessment")

        # Evolution Engine -> Simulation -> Recommendation:
        operations = department_registry.get("operations")
        engine = EvolutionEngine()
        proposal = engine.detect_and_propose(
            session, decision_id=outcome.decision_id, objective=INEFFICIENT_OBJECTIVE,
            required_output="A quality assessment", baseline_departments=[operations],
            proposed_departments=[], agent_registry=agent_registry,
        )
        assert proposal is not None

        # The Evolution Engine cannot self-approve changes (EESIS sec.10, ESTAS sec.21) -
        # its own identity was never granted the approval permission by anything in this
        # codebase, so authorize() denies it structurally, not by a special-cased check.
        with pytest.raises(EvolutionApprovalError):
            engine.approve_change(session, proposal.id, approver_identity_id=engine.engine_identity_id)

        # Implementation cannot skip approval either:
        with pytest.raises(EvolutionApprovalError):
            engine.implement_change(session, proposal.id, implementer_identity_id="director_001")

        assert proposal.approval_status == ProposalStatus.PENDING  # unchanged by both attempts

        # Approval (a human, explicitly granted the permission the engine itself never has):
        create_identity(session, id="director_001", entity_type=EntityType.HUMAN, name="Director")
        grant_permission(session, subject="director_001", resource="evolution:change_proposal", action="approve")
        # Also needed for implement_change()'s Evolution Memory write, below - the no-bypass
        # rule applies to that write too (memory_service/repository.py, since Phase 2).
        grant_permission(session, subject="director_001", resource="memory:historical", action="write")

        approved = engine.approve_change(session, proposal.id, approver_identity_id="director_001")
        assert approved.approval_status == ProposalStatus.APPROVED
        assert approved.resolved_by == "director_001"

        # Implementation:
        memory = engine.implement_change(session, proposal.id, implementer_identity_id="director_001")

        assert isinstance(memory, MemoryObject)
        assert memory.tier == MemoryTier.HISTORICAL
        assert "approved and implemented" in memory.content

        refreshed = session.get(type(proposal), proposal.id)
        assert refreshed.approval_status == ProposalStatus.IMPLEMENTED

    def test_rejected_proposal_never_produces_evolution_memory(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        coo = _make_coo(session, department_registry, agent_registry)
        outcome = coo.receive_objective(session, INEFFICIENT_OBJECTIVE, required_output="A quality assessment")

        operations = department_registry.get("operations")
        engine = EvolutionEngine()
        proposal = engine.detect_and_propose(
            session, decision_id=outcome.decision_id, objective=INEFFICIENT_OBJECTIVE,
            required_output="A quality assessment", baseline_departments=[operations],
            proposed_departments=[], agent_registry=agent_registry,
        )

        create_identity(session, id="director_001", entity_type=EntityType.HUMAN, name="Director")
        grant_permission(session, subject="director_001", resource="evolution:change_proposal", action="approve")

        rejected = engine.reject_change(session, proposal.id, approver_identity_id="director_001", note="Too risky.")
        assert rejected.approval_status == ProposalStatus.REJECTED

        with pytest.raises(EvolutionApprovalError):
            engine.implement_change(session, proposal.id, implementer_identity_id="director_001")

        historical = session.query(MemoryObject).filter(MemoryObject.tier == MemoryTier.HISTORICAL).all()
        assert historical == []
