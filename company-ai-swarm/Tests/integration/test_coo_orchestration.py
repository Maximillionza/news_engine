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


def _grant_engineering_head(session: Session) -> None:
    """Mirrors _coo_with_head()'s research_head_001 grant - needed for delegation tests since
    a delegated department's own Head is evaluated too (orchestrator/head.py's
    _resolve_department_delegation())."""

    create_identity(
        session, id="engineering_head_001", entity_type=EntityType.AGENT, name="Engineering Head", department="engineering"
    )
    grant_permission(session, subject="engineering_head_001", resource="agent_execution:engineering_head_001", action="execute")
    grant_permission(session, subject="engineering_head_001", resource="memory:department", action="read")


class TestPhase21InterDepartmentDelegation:
    """IMPLEMENTATION_PLAN.md Phase 21: a Department Head can ask one other department for a
    specific piece of help mid-task (needs_department_help), distinct from needs_specialist
    (more of its own kind) and suggested_department_id-on-reject (full handoff, no work
    retained by the original department)."""

    def test_successful_delegation_writes_ledger_and_finalizes_via_original_head(
        self, session: Session
    ) -> None:
        from orchestrator.delegations import list_delegations_for_department
        from orchestrator.head import HeadVerdict

        class _DelegatesToEngineeringHead:
            def evaluate(self, department, objective, **_):
                if department.id == "research":
                    return HeadVerdict(
                        accepted=True,
                        reasoning="Need one build-timeline fact from Engineering.",
                        needs_department_help="engineering",
                    )
                if department.id == "engineering":
                    return HeadVerdict(
                        accepted=True,
                        reasoning="Can answer directly.",
                        resolved_output="The build takes 3 days.",
                    )
                raise AssertionError(f"unexpected department: {department.id}")

        _grant_engineering_head(session)
        coo = _coo_with_head(session, _DelegatesToEngineeringHead())

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A short answer"
        )

        assert outcome.validation.objective_achieved is True
        assert outcome.execution_result.artifact["resolved_by"] == "head_after_delegation"
        assert outcome.execution_result.artifact["delegated_to"] == "engineering"

        delegations = list_delegations_for_department(session, "research")
        assert len(delegations) == 1
        assert delegations[0].decision_id == outcome.decision_id
        assert delegations[0].target_department_id == "engineering"
        assert delegations[0].chain_depth == 1
        assert "build-timeline" in delegations[0].reasoning

    def test_delegation_to_review_department_is_rejected_and_falls_back(self, session: Session) -> None:
        """Operations (the Review department) can never be a delegation target - same reason
        it can never be dispatched raw objectives as primary work (Phase 8)."""

        from orchestrator.delegations import list_delegations_for_department
        from orchestrator.head import HeadVerdict

        class _DelegatesToReviewHead:
            def evaluate(self, department, objective, **_):
                return HeadVerdict(
                    accepted=True,
                    reasoning="Thought Operations could help.",
                    needs_department_help="operations",
                )

        coo = _coo_with_head(session, _DelegatesToReviewHead())

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A short answer"
        )

        assert outcome.execution_result.artifact["resolved_by"] == "head_after_unhonored_delegation"
        assert outcome.execution_result.artifact["requested_department"] == "operations"
        assert list_delegations_for_department(session, "research") == []

    def test_delegation_to_unknown_department_is_rejected_and_falls_back(self, session: Session) -> None:
        from orchestrator.head import HeadVerdict

        class _DelegatesToUnknownHead:
            def evaluate(self, department, objective, **_):
                return HeadVerdict(
                    accepted=True,
                    reasoning="Made up a department.",
                    needs_department_help="marketing",
                )

        coo = _coo_with_head(session, _DelegatesToUnknownHead())

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A short answer"
        )

        assert outcome.execution_result.artifact["resolved_by"] == "head_after_unhonored_delegation"
        assert outcome.execution_result.artifact["requested_department"] == "marketing"

    def test_cyclical_delegation_is_avoided_not_looped(self, session: Session) -> None:
        """Unit-level: exercises resolve_verdict_execution() directly with a delegation_chain
        that already contains the requested target - the chain-membership check is what
        keeps unbounded-depth delegation (this session's design choice) from ever looping,
        without needing a fixed hop cap."""

        from orchestrator.department_registry import DepartmentRegistry
        from orchestrator.head import AutoAcceptDepartmentHead, HeadVerdict, resolve_verdict_execution

        department_registry = DepartmentRegistry(REPO_ROOT / "departments")
        department_registry.load_all()
        agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
        agent_registry.load_all()

        create_identity(session, id="research_head_001", entity_type=EntityType.AGENT, name="Research Head")
        grant_permission(session, subject="research_head_001", resource="agent_execution:research_head_001", action="execute")
        grant_permission(session, subject="research_head_001", resource="memory:department", action="read")

        verdict = HeadVerdict(
            accepted=True,
            reasoning="Need engineering's help again.",
            needs_department_help="engineering",
        )

        result = resolve_verdict_execution(
            verdict,
            department_registry.get("research"),
            objective="Some objective",
            required_output="A short answer",
            agent_registry=agent_registry,
            model_gateway=ModelGateway(StubModelProvider()),
            session=session,
            coo_id="coo",
            decision_id="DEC-test",
            telemetry=None,
            department_registry=department_registry,
            head=AutoAcceptDepartmentHead(),
            delegation_chain=frozenset({"research", "engineering"}),
        )

        assert result.artifact["resolved_by"] == "head_after_unhonored_delegation"
        assert result.artifact["requested_department"] == "engineering"

    def test_direct_resolution_does_not_write_a_delegation_record(self, session: Session) -> None:
        from orchestrator.delegations import list_delegations_for_department
        from orchestrator.head import HeadVerdict

        class _ResolvesDirectlyHead:
            def evaluate(self, department, objective, **_):
                return HeadVerdict(accepted=True, reasoning="Simple.", resolved_output="Done.")

        coo = _coo_with_head(session, _ResolvesDirectlyHead())
        coo.receive_objective(session, "Create a market intelligence report", required_output="A short answer")

        assert list_delegations_for_department(session, "research") == []


class _RecordingProvider:
    """Records the `model=` kwarg each generate() call received - Phase 20's actual exit
    criterion: does the real model string reach the provider, not just get computed and
    ignored."""

    def __init__(self) -> None:
        self.models_seen: list[str | None] = []

    def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
        self.models_seen.append(model)
        return "[recorded output]"


def _coo_with_recording_provider(session: Session, provider: _RecordingProvider, *, execution_mode: str) -> COOOrchestrator:
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()
    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    for agent_id, department in [("research_agent_001", "research"), ("engineering_agent_001", "engineering")]:
        create_identity(session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department)
        grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
        grant_permission(session, subject=agent_id, resource="memory:department", action="read")

    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=ModelGateway(provider),
        execution_mode=execution_mode,
    )


class TestPhase20ComplexityAwareModelSelection:
    """IMPLEMENTATION_PLAN.md Phase 20: workflow_engine/complexity.py's tier assessment
    actually reaches the provider - not just computed and discarded."""

    def test_single_department_objective_uses_lean_tier_by_default(self, session: Session) -> None:
        from workflow_engine.complexity import MODEL_BY_TIER, MODEL_TIER_LEAN

        provider = _RecordingProvider()
        coo = _coo_with_recording_provider(session, provider, execution_mode="lean")

        coo.receive_objective(
            session, "Create a market intelligence report", required_output="A short answer"
        )

        assert provider.models_seen == [MODEL_BY_TIER[MODEL_TIER_LEAN]]

    def test_two_department_objective_uses_standard_tier(self, session: Session) -> None:
        from workflow_engine.complexity import MODEL_BY_TIER, MODEL_TIER_STANDARD

        provider = _RecordingProvider()
        coo = _coo_with_recording_provider(session, provider, execution_mode="lean")

        coo.receive_objective(
            session,
            "Research current trends and build a working prototype based on the findings.",
            required_output="A validated implementation",
        )

        assert len(provider.models_seen) == 2
        assert all(m == MODEL_BY_TIER[MODEL_TIER_STANDARD] for m in provider.models_seen)

    def test_fast_mode_never_downgrades_a_single_department_objective_to_lean(self, session: Session) -> None:
        from workflow_engine.complexity import MODEL_BY_TIER, MODEL_TIER_STANDARD

        provider = _RecordingProvider()
        coo = _coo_with_recording_provider(session, provider, execution_mode="fast")

        coo.receive_objective(
            session, "Create a market intelligence report", required_output="A short answer"
        )

        assert provider.models_seen == [MODEL_BY_TIER[MODEL_TIER_STANDARD]]

    def test_decision_record_models_used_reflects_the_real_model_not_stub(self, session: Session) -> None:
        from workflow_engine.complexity import MODEL_BY_TIER, MODEL_TIER_LEAN

        provider = _RecordingProvider()
        coo = _coo_with_recording_provider(session, provider, execution_mode="lean")

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A short answer"
        )

        record = get_decision(session, outcome.decision_id)
        assert record.models_used == [MODEL_BY_TIER[MODEL_TIER_LEAN]]
