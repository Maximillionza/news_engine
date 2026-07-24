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


def test_assess_sufficiency_delegates_to_intake_with_configured_departments(coo: COOOrchestrator) -> None:
    """COOOrchestrator.assess_sufficiency() is a thin wrapper - this proves it actually
    reaches a real model_gateway call and returns a SufficiencyAssessment, using the same
    StubModelProvider-backed COO every other test in this file builds. StubModelProvider's
    fixed text isn't parseable JSON, so this exercises the 'fails toward insufficient with
    fallback question' path - a real assertion, not a placeholder."""

    from orchestrator.intake import FALLBACK_CLARIFYING_QUESTION, SufficiencyAssessment

    result = coo.assess_sufficiency("Do something", [], round_number=1)

    assert isinstance(result, SufficiencyAssessment)
    assert result.sufficient is False
    assert result.clarifying_question == FALLBACK_CLARIFYING_QUESTION


def _coo_with_head(session: Session, head) -> COOOrchestrator:
    """Phase 16 (IMPLEMENTATION_PLAN.md, 2026-07-23): same registries/permissions as the
    `coo` fixture above, but with a caller-supplied DepartmentHead so tests can exercise
    orchestrator/head.py's resolve_verdict_execution() paths directly, without needing a real
    LLMDepartmentHead call (that's covered separately once Increment 3 wires its prompt to
    this same HeadVerdict shape)."""

    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()

    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    create_identity(
        session, id="research_agent_001", entity_type=EntityType.AGENT, name="Research Agent", department="research"
    )
    grant_permission(session, subject="research_agent_001", resource="agent_execution:research_agent_001", action="execute")
    grant_permission(session, subject="research_agent_001", resource="memory:department", action="read")

    # The Head's own identity (research_head_001, loaded from agents/active/research_head/
    # agent.yaml) needs the same execute grant - resolve_verdict_execution()'s specialist
    # path (orchestrator/head.py) reuses this identity to dispatch, per Phase 16's design:
    # a spawned specialist is the Head adopting a specialized role, not a new identity.
    create_identity(
        session, id="research_head_001", entity_type=EntityType.AGENT, name="Research Head", department="research"
    )
    grant_permission(session, subject="research_head_001", resource="agent_execution:research_head_001", action="execute")
    grant_permission(session, subject="research_head_001", resource="memory:department", action="read")

    telemetry = TelemetrySink()
    gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)

    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=gateway,
        telemetry=telemetry,
        head=head,
    )


class TestPhase16DepartmentHeadDirectExecution:
    """IMPLEMENTATION_PLAN.md Phase 16: the Department Head executes objectives directly when
    it can, and spawns a specialist (its own identity, a specialized role) only when the
    objective genuinely exceeds one agent's capacity - not just because a HeadVerdict was
    accepted, which is all AutoAcceptDepartmentHead and this file's other tests exercise."""

    def test_head_resolves_directly_no_agent_dispatch(self, session: Session) -> None:
        from orchestrator.head import HeadVerdict

        class _ResolvesDirectlyHead:
            def evaluate(self, department, objective, **_):
                return HeadVerdict(
                    accepted=True,
                    reasoning="Simple enough to answer directly.",
                    resolved_output="EUR/USD is currently trading sideways.",
                )

        coo = _coo_with_head(session, _ResolvesDirectlyHead())

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A short answer"
        )

        assert outcome.execution_result.output == "EUR/USD is currently trading sideways."
        assert outcome.validation.objective_achieved is True

        record = get_decision(session, outcome.decision_id)
        assert record.agents_selected == ["research_head_001"]
        assert "resolved directly by department head" in record.reasoning

    def test_head_spawns_specialist_when_it_needs_more_than_one_agent(self, session: Session) -> None:
        from orchestrator.head import HeadVerdict

        class _NeedsSpecialistHead:
            def evaluate(self, department, objective, **_):
                return HeadVerdict(
                    accepted=True,
                    reasoning="Requires deep statistical modeling beyond my own depth.",
                    needs_specialist=True,
                )

        coo = _coo_with_head(session, _NeedsSpecialistHead())

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A model"
        )

        assert outcome.validation.objective_achieved is True

        record = get_decision(session, outcome.decision_id)
        assert record.agents_selected == ["research_head_001"]
        assert "spawned a specialist" in record.reasoning
        assert "deep statistical modeling" in record.reasoning

        # Phase 17 (IMPLEMENTATION_PLAN.md, 2026-07-23): every successful specialist spawn
        # writes a SpecialistSpawnRecord, feeding the Evolution Engine's promotion heuristic.
        from orchestrator.spawns import list_spawns_for_department

        spawns = list_spawns_for_department(session, "research")
        assert len(spawns) == 1
        assert spawns[0].decision_id == outcome.decision_id
        assert spawns[0].head_agent_id == "research_head_001"
        assert "deep statistical modeling" in spawns[0].reasoning

    def test_head_direct_resolution_does_not_write_a_spawn_record(self, session: Session) -> None:
        """Only an actual specialist spawn counts toward the pattern Phase 17 detects - the
        Head resolving something itself is the opposite case (one agent was enough)."""
        from orchestrator.head import HeadVerdict
        from orchestrator.spawns import list_spawns_for_department

        class _ResolvesDirectlyHead:
            def evaluate(self, department, objective, **_):
                return HeadVerdict(accepted=True, reasoning="Simple.", resolved_output="Done.")

        coo = _coo_with_head(session, _ResolvesDirectlyHead())
        coo.receive_objective(session, "Create a market intelligence report", required_output="A short answer")

        assert list_spawns_for_department(session, "research") == []

    def test_auto_accept_head_still_uses_the_normal_agent_selection_path(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        """Backward-compatibility check: the default AutoAcceptDepartmentHead never sets
        resolved_output/needs_specialist, so this must still dispatch to research_agent_001
        via the unchanged select_agent() path, not the Head's own identity."""

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        record = get_decision(session, outcome.decision_id)
        assert record.agents_selected == ["research_agent_001"]
