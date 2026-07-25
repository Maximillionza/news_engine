"""Phase 8 exit-criteria test (part 3 of 3): the four-condition escalation policy
(orchestrator/escalation.py) plus the technical-failure path, triggered independently and
confirmed as correctly classified in the Escalation Record.

Source: IMPLEMENTATION_PLAN.md Phase 8 test spec item 3: "Trigger each of the four
escalation conditions independently ... and confirm each produces a human-escalation record,
and that a separate technical-failure case ... is logged as a technical failure rather than
as one of the four."

Reachability note (see also orchestrator/controller.py's OUTCOME_NOT_ACHIEVED comment and
Documentation/operations/technology_decisions.md's Phase 8 entry): conditions 2 and 4 are not
reachable through COOOrchestrator.receive_objective()'s public entry point with this
codebase's stub model provider and real department/agent files - AgentRuntime always either
completes fully (objective_achieved=True) or raises (a technical failure), and every real
departments/*/definition.yaml already resolves to a registered agent. Both are still real,
correct code paths - tested here as direct, targeted exercises of the same functions
receive_objective() calls, not as contrived end-to-end scenarios.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from agent_runtime.runtime import ExecutionResult
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, NoMatchingDepartmentError
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from orchestrator.escalation import EscalationCondition
from orchestrator.escalations import list_pending_escalations, write_escalation
from orchestrator.evaluator import validate_outcome
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]


class FailingModelProvider:
    """Deterministic failure, for exercising the TECHNICAL_FAILURE path - not connected to
    any real model, same dev/test-only status as StubModelProvider."""

    def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
        raise RuntimeError("simulated model provider failure")


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def _grant(session: Session, agent_id: str, department: str) -> None:
    create_identity(
        session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department
    )
    grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
    grant_permission(session, subject=agent_id, resource="memory:department", action="read")


def _make_coo(session: Session, *, provider=None, telemetry: TelemetrySink | None = None) -> COOOrchestrator:
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()

    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    telemetry = telemetry or TelemetrySink()
    gateway = ModelGateway(provider or StubModelProvider(), telemetry=telemetry)

    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=gateway,
        telemetry=telemetry,
    )


class TestCondition1NoMatchingDepartment:
    def test_produces_an_escalation_record(self, session: Session) -> None:
        coo = _make_coo(session)

        with pytest.raises(NoMatchingDepartmentError):
            coo.receive_objective(session, "xyz qqq zzz", required_output="anything")

        pending = list_pending_escalations(session)
        assert len(pending) == 1
        assert pending[0].condition == EscalationCondition.NO_MATCHING_DEPARTMENT.value
        assert pending[0].is_technical_failure is False


class TestCondition2OutcomeNotAchieved:
    def test_validate_outcome_and_escalation_wiring_directly(self, session: Session) -> None:
        """See module docstring: not reachable via receive_objective() with this codebase's
        AgentRuntime, which never returns an incomplete ExecutionResult - it raises first."""

        incomplete_result = ExecutionResult(
            task="test task", output="", artifact={}, steps_completed=["receive_task"]
        )
        validation = validate_outcome(incomplete_result)
        assert validation.objective_achieved is False

        record = write_escalation(
            session,
            condition=EscalationCondition.OUTCOME_NOT_ACHIEVED,
            reasoning=validation.reasoning,
        )
        assert record.condition == EscalationCondition.OUTCOME_NOT_ACHIEVED.value
        assert record.resolved is False


class TestCondition3GateIntegritySuperficial:
    def test_review_with_nothing_to_review_is_flagged_superficial(self, session: Session) -> None:
        """An objective matching only the Review Agent's own department (operations) means
        zero substantive tasks run before the review step - the review still nominally
        passes (stub output, full execution cycle), but has no real evidence behind it."""

        coo = _make_coo(session)
        _grant(session, "review_agent_001", "operations")

        outcome = coo.receive_objective(
            session, "Monitor workflow quality and evaluate the outcome.", required_output="A quality assessment"
        )

        assert outcome.matched_departments == [
            d for d in outcome.matched_departments if d.id == "operations"
        ]
        assert outcome.workflow.gate_superficial is True
        assert outcome.workflow.succeeded is True  # nominally passing - that's the point

        pending = list_pending_escalations(session)
        conditions = [p.condition for p in pending]
        assert EscalationCondition.GATE_INTEGRITY_SUPERFICIAL.value in conditions


class TestCondition4UnresolvableDependencyGap:
    def test_department_with_no_registered_agent_halts_and_escalates(self, session: Session) -> None:
        coo = _make_coo(session)

        broken_department = DepartmentDefinition(
            id="research",
            name="Research Department",
            purpose="test",
            mission="test",
            capabilities=["research"],
            agents=["nonexistent_agent_099"],
        )
        second_department = DepartmentDefinition(
            id="engineering",
            name="Engineering Department",
            purpose="test",
            mission="test",
            capabilities=["coding"],
            agents=["engineering_agent_001"],
        )
        _grant(session, "engineering_agent_001", "engineering")

        outcome = coo._receive_multi_department_objective(
            session,
            "test objective requiring a missing agent",
            required_output="anything",
            decision_id="DEC-test-condition4",
            matched_departments=[broken_department, second_department],
        )

        assert outcome.workflow.succeeded is False
        assert outcome.workflow.blocked_reason is not None
        assert "unresolvable_dependency_gap" in outcome.workflow.blocked_reason

        pending = list_pending_escalations(session)
        conditions = [p.condition for p in pending]
        assert EscalationCondition.UNRESOLVABLE_DEPENDENCY_GAP.value in conditions


class TestTechnicalFailureIsDistinctFromTheFourConditions:
    def test_single_department_technical_failure_is_logged_and_reraised(self, session: Session) -> None:
        coo = _make_coo(session, provider=FailingModelProvider())
        _grant(session, "research_agent_001", "research")

        with pytest.raises(RuntimeError, match="simulated model provider failure"):
            coo.receive_objective(
                session, "Create a market intelligence report", required_output="A structured summary"
            )

        pending = list_pending_escalations(session)
        assert len(pending) == 1
        assert pending[0].condition == EscalationCondition.TECHNICAL_FAILURE.value
        assert pending[0].is_technical_failure is True

    def test_multi_department_technical_failure_is_logged_and_reraised(self, session: Session) -> None:
        coo = _make_coo(session, provider=FailingModelProvider())
        _grant(session, "research_agent_001", "research")
        _grant(session, "engineering_agent_001", "engineering")

        with pytest.raises(RuntimeError, match="simulated model provider failure"):
            coo.receive_objective(
                session,
                "Research market analysis and build working software",
                required_output="working code with a supporting summary",
            )

        pending = list_pending_escalations(session)
        assert len(pending) == 1
        assert pending[0].condition == EscalationCondition.TECHNICAL_FAILURE.value
        assert pending[0].is_technical_failure is True
        # Distinct from the four framework verdicts - never classified as one of them.
        assert pending[0].condition != EscalationCondition.OUTCOME_NOT_ACHIEVED.value

    def test_genuine_mid_workflow_failure_preserves_knowledge_but_not_the_decision_record(
        self, session: Session
    ) -> None:
        """Phase 13 (IMPLEMENTATION_PLAN.md, 2026-07-23): FailingModelProvider above fails on
        the very FIRST call, so the two tests above never actually exercise a failure that
        happens after real work already completed - they can't distinguish "fails
        immediately" from "fails partway through." This uses a provider that succeeds once
        (research) then fails (engineering), and documents what was empirically observed
        (not assumed) to happen to research's completed work:

        - The escalation and technical-failure classification are unaffected - identical to
          the immediate-failure case above.
        - workflow_engine.knowledge.record_task_knowledge() already ran for research before
          engineering's dispatch() raised, so research's Agent/Capability/Workflow entities
          are recorded in the knowledge graph and survive the failure.
        - The COO Decision Record does NOT reflect that research completed real work -
          agents_selected stays empty and outcome stays None, identical to what an
          immediate, zero-progress failure produces. Not a bug introduced by this test - a
          pre-existing gap in orchestrator/controller.py's exception handler (it writes the
          Decision Record with only objective/reasoning/chosen_action, never touching
          agents_selected/outcome on the failure path) made visible for the first time by
          actually testing a failure with real partial progress behind it."""

        class _SucceedsThenFailsProvider:
            def __init__(self, succeed_count: int) -> None:
                self._remaining = succeed_count
                self.calls = 0

            def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
                self.calls += 1
                if self._remaining > 0:
                    self._remaining -= 1
                    return f"[stub output for call {self.calls}]"
                raise RuntimeError("simulated model provider failure")

        provider = _SucceedsThenFailsProvider(succeed_count=1)
        coo = _make_coo(session, provider=provider)
        _grant(session, "research_agent_001", "research")
        _grant(session, "engineering_agent_001", "engineering")

        with pytest.raises(RuntimeError, match="simulated model provider failure"):
            coo.receive_objective(
                session,
                "Research market analysis and build working software",
                required_output="working code with a supporting summary",
            )

        # Confirms this genuinely reached department 2 - not an immediate, zero-progress
        # failure like the test above.
        assert provider.calls == 2

        pending = list_pending_escalations(session)
        assert len(pending) == 1
        assert pending[0].condition == EscalationCondition.TECHNICAL_FAILURE.value
        assert pending[0].is_technical_failure is True

        from knowledge_service.repository import KnowledgeEntity
        from orchestrator.decisions import list_decisions

        entities = session.query(KnowledgeEntity).all()
        assert any(e.id == "agent:research_agent_001" for e in entities)

        records = list_decisions(session)
        assert len(records) == 1
        assert records[0].agents_selected == []  # research's completion isn't reflected here
        assert records[0].outcome is None
