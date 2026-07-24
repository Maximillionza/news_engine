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
from evolution_service.detection import detect_specialist_pattern
from evolution_service.models import ProposalStatus
from evolution_service.pipeline import EvolutionApprovalError, EvolutionEngine
from identity_service.models import EntityType
from identity_service.repository import create_identity
from memory_service.models import MemoryObject, MemoryTier
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, WorkflowObjectiveOutcome
from orchestrator.department_registry import DepartmentRegistry
from orchestrator.spawns import write_spawn
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


class TestPhase17SpecialistPromotion:
    """IMPLEMENTATION_PLAN.md Phase 17: the Evolution Engine's second detection source (the
    specialist spawn ledger, orchestrator/spawns.py) and its first proposal type that does
    real work on implementation (create_agent, via sdk.agent_builder.build_agent())."""

    def _seed_spawns(self, session: Session, *, department_id: str, count: int, reasoning: str) -> None:
        for i in range(count):
            write_spawn(
                session,
                decision_id=f"DEC-seed-{i}",
                department_id=department_id,
                head_agent_id=f"{department_id}_head_001",
                reasoning=reasoning,
            )

    def test_detect_specialist_pattern_below_threshold_returns_none(self, session: Session) -> None:
        self._seed_spawns(session, department_id="research", count=2, reasoning="Needs deep modeling.")

        assert detect_specialist_pattern(session, department_id="research", threshold=3) is None

    def test_detect_specialist_pattern_at_threshold_creates_opportunity(self, session: Session) -> None:
        self._seed_spawns(session, department_id="research", count=3, reasoning="Needs deep modeling.")

        opportunity = detect_specialist_pattern(session, department_id="research", threshold=3)

        assert opportunity is not None
        assert opportunity.source == "agent_evaluation"
        assert len(opportunity.evidence["spawn_ids"]) == 3

    def test_propose_specialist_agent_returns_none_below_threshold(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        self._seed_spawns(session, department_id="research", count=2, reasoning="Needs deep modeling.")
        engine = EvolutionEngine()

        proposal = engine.propose_specialist_agent(
            session, department=department_registry.get("research"), agent_registry=agent_registry
        )

        assert proposal is None

    def test_propose_specialist_agent_creates_pending_create_agent_proposal(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        self._seed_spawns(session, department_id="research", count=3, reasoning="Needs deep econometric modeling.")
        engine = EvolutionEngine()

        proposal = engine.propose_specialist_agent(
            session, department=department_registry.get("research"), agent_registry=agent_registry
        )

        assert proposal is not None
        assert proposal.approval_status == ProposalStatus.PENDING
        assert proposal.action_type == "create_agent"
        assert proposal.simulation_run_id is None  # no meaningful dry run for this proposal type
        assert proposal.action_payload["department"] == "research"
        assert "econometric modeling" in proposal.action_payload["mission"]
        assert proposal.action_payload["capabilities"]  # reused from the real research_head_001

    def test_propose_specialist_agent_is_idempotent_while_pending(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        self._seed_spawns(session, department_id="research", count=3, reasoning="Needs deep modeling.")
        engine = EvolutionEngine()
        department = department_registry.get("research")

        first = engine.propose_specialist_agent(session, department=department, agent_registry=agent_registry)
        assert first is not None

        second = engine.propose_specialist_agent(session, department=department, agent_registry=agent_registry)
        assert second is None

    def test_implement_change_for_create_agent_registers_a_working_agent(
        self,
        session: Session,
        department_registry: DepartmentRegistry,
        agent_registry: AgentRegistry,
        tmp_path: Path,
    ) -> None:
        """The end-to-end path: propose -> approve -> implement actually adds a new,
        immediately-usable agent to the live registry - not just a memory record describing
        one, which is all every proposal type before this phase ever did."""

        self._seed_spawns(session, department_id="research", count=3, reasoning="Needs deep econometric modeling.")
        engine = EvolutionEngine()
        proposal = engine.propose_specialist_agent(
            session, department=department_registry.get("research"), agent_registry=agent_registry
        )
        assert proposal is not None

        create_identity(session, id="director_001", entity_type=EntityType.HUMAN, name="Director")
        grant_permission(session, subject="director_001", resource="evolution:change_proposal", action="approve")
        grant_permission(session, subject="director_001", resource="memory:historical", action="write")
        engine.approve_change(session, proposal.id, approver_identity_id="director_001")

        gateway = ModelGateway(StubModelProvider())
        memory = engine.implement_change(
            session,
            proposal.id,
            implementer_identity_id="director_001",
            department_registry=department_registry,
            agent_registry=agent_registry,
            model_gateway=gateway,
            agents_root=tmp_path,
        )

        assert "registered as a new agent" in memory.content

        new_agent_id = proposal.action_payload["identity_id"]
        registered = agent_registry.get(new_agent_id)
        assert registered is not None
        assert registered.department.name == "research"
        assert (tmp_path / new_agent_id / "agent.yaml").exists()  # Activate step wrote to disk too

        refreshed = session.get(type(proposal), proposal.id)
        assert refreshed.approval_status == ProposalStatus.IMPLEMENTED

    def test_implement_change_for_create_agent_without_kwargs_raises(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        self._seed_spawns(session, department_id="research", count=3, reasoning="Needs deep modeling.")
        engine = EvolutionEngine()
        proposal = engine.propose_specialist_agent(
            session, department=department_registry.get("research"), agent_registry=agent_registry
        )

        create_identity(session, id="director_001", entity_type=EntityType.HUMAN, name="Director")
        grant_permission(session, subject="director_001", resource="evolution:change_proposal", action="approve")
        engine.approve_change(session, proposal.id, approver_identity_id="director_001")

        with pytest.raises(EvolutionApprovalError, match="department_registry, agent_registry, model_gateway, agents_root"):
            engine.implement_change(session, proposal.id, implementer_identity_id="director_001")
