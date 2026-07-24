"""Phase 9 exit-criteria test: the full MVS acceptance suite, Test Categories 001-010,
executed end to end.

Source: Specifications/3 - execution-framework/MVP Validation Specification (MVS).md, and
IMPLEMENTATION_PLAN.md Phase 9's test spec, which names all ten categories explicitly.

This file is the formal, phase-boundary re-confirmation of each category's pass criteria in
MVS's own vocabulary - it is not the only place these mechanisms are tested. Categories
001, 006, 007, 008, and 009 already have thorough dedicated coverage from earlier phases
(Tests/integration/test_coo_orchestration.py, test_knowledge_graph_review.py,
Tests/security/test_mvs_007_security_validation.py, test_compliance_intelligence.py,
test_observability_platform.py) - this file re-asserts their pass criteria briefly rather
than duplicating that depth. Categories 002, 005, and 010 needed new or extended mechanisms
this phase (agent-lifecycle-from-scratch, memory-improves-on-repeat, and failure recovery
respectively) and are tested more thoroughly here, where those mechanisms were actually
built. Test Category 011 (Evolution) is explicitly out of scope - it requires Phase 11.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import (
    AgentDefinition,
    AgentDepartment,
    AgentIdentity,
    AgentMission,
    AgentRegistry,
)
from agent_runtime.runtime import AgentRuntime
from compliance_service.applicability import ApplicabilityFactors, assess_applicability
from compliance_service.policy_impact import PolicyRequirement, analyze_policy_impact
from identity_service.models import EntityType
from identity_service.repository import create_identity
from knowledge_service.repository import get_entity, get_relationships_for_entity
from memory_service.models import MemoryTier
from memory_service.repository import query_memory
from observability_service.alerting import AlertSeverity, generate_alerts
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, WorkflowObjectiveOutcome
from orchestrator.decisions import get_decision
from orchestrator.department_registry import DepartmentRegistry
from orchestrator.escalation import EscalationCondition
from orchestrator.escalations import list_pending_escalations, resolve_escalation
from security_service.audit import get_audit_trail
from security_service.permissions import authorize, grant_permission
from shared.contracts import AgentMessageContract
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]

ALL_AGENTS = [
    ("research_agent_001", "research"),
    ("engineering_agent_001", "engineering"),
    ("compliance_agent_001", "compliance"),
    ("review_agent_001", "operations"),
]


class FailingModelProvider:
    """Deterministic failure, for exercising MVS-010 (Failure Recovery). Not connected to
    any real model, same dev/test-only status as StubModelProvider."""

    def generate(self, prompt: str, *, allowed_tools=None) -> str:
        raise RuntimeError("simulated model provider failure")


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def _grant_full_agent(session: Session, agent_id: str, department: str) -> None:
    """Full Phase 9 grant set - includes memory:department WRITE, which most earlier
    phases' fixtures deliberately did not grant (nothing wrote before Phase 9 - see
    Documentation/operations/technology_decisions.md)."""

    create_identity(
        session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department
    )
    grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
    grant_permission(session, subject=agent_id, resource="memory:department", action="read")
    grant_permission(session, subject=agent_id, resource="memory:department", action="write")


def _grant_coo(session: Session, coo_id: str = "coo") -> None:
    create_identity(session, id=coo_id, entity_type=EntityType.SERVICE, name="COO")
    grant_permission(session, subject=coo_id, resource="memory:historical", action="write")
    grant_permission(session, subject=coo_id, resource="memory:project", action="write")


def _make_coo(session: Session, *, provider=None, telemetry: TelemetrySink | None = None) -> COOOrchestrator:
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()

    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    # `telemetry or TelemetrySink()` would be wrong here - TelemetrySink defines __len__, so
    # a freshly-passed-in *empty* sink is falsy and would be silently replaced (the exact bug
    # fixed in Phase 3's service_bus.py/event_service - see technology_decisions.md).
    telemetry = telemetry if telemetry is not None else TelemetrySink()
    gateway = ModelGateway(provider if provider is not None else StubModelProvider(), telemetry=telemetry)

    _grant_coo(session)

    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=gateway,
        telemetry=telemetry,
    )


class TestMVS001ObjectiveExecution:
    """Full dedicated coverage: Tests/integration/test_coo_orchestration.py."""

    def test_objective_produces_output_and_a_decision_record(self, session: Session) -> None:
        _grant_full_agent(session, "research_agent_001", "research")
        coo = _make_coo(session)

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        assert outcome.execution_result.output != ""
        assert outcome.validation.objective_achieved is True
        record = get_decision(session, outcome.decision_id)
        assert record is not None and record.reasoning != ""


class TestMVS002AgentLifecycle:
    """Source: MVS sec.6. Test: Create 'New Research Specialist Agent'. Expected Flow:
    Agent Definition -> Validation -> Permission Assignment -> Testing -> Deployment.
    Pass Criteria: Agent registered, Permissions enforced, Agent executes correctly.

    No dedicated Phase built this as a standalone flow before now - Phase 4/5 tests load
    already-scaffolded agent.yaml files, they don't demonstrate defining, registering, and
    permissioning a brand-new agent from nothing. Built here rather than a throwaway YAML
    fixture file, since the mechanism (AgentDefinition + AgentRegistry + authorize()) is
    what's under test, not the file format.
    """

    def test_new_agent_is_defined_validated_registered_permissioned_and_executes(
        self, session: Session
    ) -> None:
        # Agent Definition (+ Validation: AgentDefinition is a Pydantic model - an invalid
        # shape would raise here, not silently pass).
        new_agent = AgentDefinition(
            identity=AgentIdentity(id="research_specialist_agent_001", name="New Research Specialist Agent"),
            mission=AgentMission(objective="Deep-dive research on a single named topic."),
            department=AgentDepartment(name="research"),
            capabilities=["research"],
        )

        # Agent registered:
        registry = AgentRegistry(REPO_ROOT / "agents" / "active")
        registry.load_all()
        registry._agents[new_agent.identity.id] = new_agent  # same registration path load_all() uses
        assert registry.get("research_specialist_agent_001") is new_agent

        # Permission Assignment:
        create_identity(
            session, id=new_agent.identity.id, entity_type=EntityType.AGENT, name=new_agent.identity.name
        )
        grant_permission(
            session,
            subject=new_agent.identity.id,
            resource=f"agent_execution:{new_agent.identity.id}",
            action="execute",
        )

        # Permissions enforced: an unrelated action was never granted.
        denied = authorize(
            session, identity_id=new_agent.identity.id, resource="production_deployment", action="execute"
        )
        assert denied.allowed is False

        # Testing / Deployment / "Agent executes correctly":
        telemetry = TelemetrySink()
        gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
        runtime = AgentRuntime(new_agent, model_gateway=gateway, telemetry=telemetry)
        message = AgentMessageContract(
            sender_agent="coo",
            receiver_agent=new_agent.identity.id,
            task="Research the adoption rate of a named technology.",
            required_output="A short findings summary",
        )
        result = runtime.execute_task(session, message)

        assert result.output != ""
        assert len(result.steps_completed) == 10


class TestMVS003DepartmentOperation:
    """Source: MVS sec.7. Pass Criteria: Department operates independently, Agents
    collaborate, Results are measurable."""

    def test_department_operates_independently(self, session: Session) -> None:
        _grant_full_agent(session, "research_agent_001", "research")
        coo = _make_coo(session)

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        assert outcome.task_profile.matched_department.id == "research"

    def test_agents_collaborate_across_departments(self, session: Session) -> None:
        _grant_full_agent(session, "research_agent_001", "research")
        _grant_full_agent(session, "engineering_agent_001", "engineering")
        coo = _make_coo(session)

        outcome = coo.receive_objective(
            session,
            "Research market analysis and build working software",
            required_output="working code with a supporting summary",
        )

        assert isinstance(outcome, WorkflowObjectiveOutcome)
        assert [t.agent_id for t in outcome.workflow.tasks] == [
            "research_agent_001",
            "engineering_agent_001",
        ]

    def test_results_are_measurable(self, session: Session) -> None:
        """A Decision Record with reasoning/outcome is the measurable result."""

        _grant_full_agent(session, "research_agent_001", "research")
        coo = _make_coo(session)

        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )
        record = get_decision(session, outcome.decision_id)

        assert record.outcome is not None and "objective_achieved=True" in record.outcome


class TestMVS004COOOrchestration:
    """Source: MVS sec.8. Test: 'Develop a new software product concept.' Expected Flow: COO
    -> Task Breakdown -> Department Allocation -> Agent Assignment -> Workflow Execution ->
    Review. Pass Criteria: Correct decomposition, Appropriate agents selected, Execution
    completed."""

    def test_complex_objective_decomposes_allocates_assigns_executes_and_reviews(
        self, session: Session
    ) -> None:
        for agent_id, department in ALL_AGENTS:
            _grant_full_agent(session, agent_id, department)
        coo = _make_coo(session)

        outcome = coo.receive_objective(
            session,
            "Research requirements, assess risk, and build software while monitoring quality.",
            required_output="A validated implementation",
        )

        # Correct decomposition + Appropriate agents selected:
        assert [d.id for d in outcome.matched_departments] == [
            "research", "engineering", "compliance", "operations",
        ]
        assert [t.agent_id for t in outcome.workflow.tasks] == [
            "research_agent_001", "engineering_agent_001", "compliance_agent_001", "review_agent_001",
        ]
        # Execution completed (Workflow Execution -> Review):
        assert outcome.objective_achieved is True
        assert outcome.workflow.tasks[-1].department.id == "operations"


class TestMVS005MemoryValidation:
    """Source: MVS sec.9. Test: Complete task twice. Expected: second execution improves
    through Stored knowledge / Previous workflows / Learned patterns. Pass Criteria: Memory
    stored, Memory retrieved, Performance improves.

    Honest definition of "Performance improves" used here: this codebase has no real model
    (StubModelProvider is deterministic and content-blind) and no quality-scoring mechanism
    anywhere in the corpus - so "improves" cannot mean "better output quality." What Phase 9
    actually built (orchestrator/router.py's department-observation write) makes a real,
    structural claim true instead: the pool of Department-tier memory available to
    agent_runtime/runtime.py's Retrieve Relevant Knowledge step (Step 3) grows after each
    completed task, so the second run has strictly more to draw on than the first. That
    growth is what's asserted below - not a fabricated quality delta.
    """

    def test_memory_stored_and_retrieved_and_grows_across_repeated_runs(
        self, session: Session
    ) -> None:
        _grant_full_agent(session, "research_agent_001", "research")
        coo = _make_coo(session)

        before = query_memory(
            session, identity_id="research_agent_001", tier=MemoryTier.DEPARTMENT, department_id="research"
        )
        assert before == []

        coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        # Memory stored:
        after_first_run = query_memory(
            session, identity_id="research_agent_001", tier=MemoryTier.DEPARTMENT, department_id="research"
        )
        assert len(after_first_run) == 1

        coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        # Memory retrieved (the second run's own Retrieve Relevant Knowledge step used this
        # exact query - see agent_runtime/runtime.py Step 3) + Performance improves (grows):
        after_second_run = query_memory(
            session, identity_id="research_agent_001", tier=MemoryTier.DEPARTMENT, department_id="research"
        )
        assert len(after_second_run) == 2
        assert len(after_second_run) > len(after_first_run)


class TestMVS006KnowledgeGraphValidation:
    """Full dedicated coverage: Tests/integration/test_knowledge_graph_review.py."""

    def test_agent_uses_capability_applies_to_workflow_entities_and_relationships(
        self, session: Session
    ) -> None:
        for agent_id, department in ALL_AGENTS:
            _grant_full_agent(session, agent_id, department)
        coo = _make_coo(session)

        outcome = coo.receive_objective(
            session,
            "Research requirements, assess risk, and build software while monitoring quality.",
            required_output="A validated implementation",
        )

        capability_id = "capability:research:research"
        relationships = get_relationships_for_entity(session, capability_id)
        assert any(r.relationship_type == "USES" for r in relationships)
        assert any(
            r.relationship_type == "APPLIES_TO" and r.target_entity_id == f"workflow:{outcome.workflow.workflow_id}"
            for r in relationships
        )
        assert get_entity(session, capability_id).object_type == "Capability"


class TestMVS007SecurityValidation:
    """Full dedicated coverage: Tests/security/test_mvs_007_security_validation.py."""

    def test_unauthorised_access_denied_and_logged(self, session: Session) -> None:
        result = authorize(session, identity_id="does-not-exist", resource="x", action="read")
        assert result.allowed is False
        assert get_audit_trail(session, "does-not-exist")[-1].decision == "denied"

    def test_correct_permission_allowed_and_logged(self, session: Session) -> None:
        create_identity(session, id="agent_x", entity_type=EntityType.AGENT, name="Agent X")
        grant_permission(session, subject="agent_x", resource="research_data", action="read")

        result = authorize(session, identity_id="agent_x", resource="research_data", action="read")
        assert result.allowed is True
        assert get_audit_trail(session, "agent_x")[-1].decision == "allowed"


class TestMVS008ComplianceValidation:
    """Full dedicated coverage: Tests/integration/test_compliance_intelligence.py."""

    def test_policy_added_impact_analysis_and_evidence(self, session: Session) -> None:
        department_registry = DepartmentRegistry(REPO_ROOT / "departments")
        department_registry.load_all()

        assessment = analyze_policy_impact(
            session,
            policy=PolicyRequirement(
                name="Secure Coding Standard",
                description="All new software must pass security testing before release.",
            ),
            department_registry=department_registry,
        )

        assert "engineering" in assessment.affected_departments
        assert assessment.evidence["matching_method"] == "keyword_overlap"

        applicability = assess_applicability(
            session,
            regulation="POPIA",
            factors=ApplicabilityFactors(
                business_activity="x", location="south_africa", data_type="personal_information",
                industry="x", entity_type="x", risk_profile="x",
            ),
        )
        assert applicability.applicable is True


class TestMVS009ObservabilityValidation:
    """Full dedicated coverage: Tests/integration/test_observability_platform.py."""

    def test_logs_metrics_traces_performance_data_recorded(self, session: Session) -> None:
        _grant_full_agent(session, "research_agent_001", "research")
        telemetry = TelemetrySink()
        coo = _make_coo(session, telemetry=telemetry)

        coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        records = telemetry.query()
        assert len(records) > 0
        for record in records:
            assert record.component != "" and record.action != "" and record.duration_ms >= 0


class TestMVS010FailureRecovery:
    """Source: MVS sec.14. Test: Disable a component. Expected: Failure Detected -> Alert
    Generated -> Recovery Triggered -> System Restored. Pass Criteria: Failure detected,
    Recovery executed, Operations resumed.

    "Disable a component" = the Model Gateway's provider fails (FailingModelProvider).
    "Recovery Triggered" = ModelGateway.replace_provider() (Phase 9 addition), a manual
    hot-swap - not an automated detect-and-recover daemon (EOCCS sec.20's full Automated
    Intervention loop is not built; see the module docstring on that method).
    """

    def test_failure_detected_alerted_recovered_and_operations_resumed(self, session: Session) -> None:
        _grant_full_agent(session, "research_agent_001", "research")

        telemetry = TelemetrySink()
        gateway = ModelGateway(FailingModelProvider(), telemetry=telemetry)
        _grant_coo(session)
        department_registry = DepartmentRegistry(REPO_ROOT / "departments")
        department_registry.load_all()
        agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
        agent_registry.load_all()
        coo = COOOrchestrator(
            coo_id="coo", department_registry=department_registry, agent_registry=agent_registry,
            model_gateway=gateway, telemetry=telemetry,
        )

        # Failure Detected:
        with pytest.raises(RuntimeError, match="simulated model provider failure"):
            coo.receive_objective(
                session, "Create a market intelligence report", required_output="A structured summary"
            )

        pending = list_pending_escalations(session)
        assert len(pending) == 1
        assert pending[0].condition == EscalationCondition.TECHNICAL_FAILURE.value
        failure_escalation = pending[0]

        # Alert Generated:
        alerts = generate_alerts(telemetry, session)
        assert any(a.severity == AlertSeverity.CRITICAL for a in alerts)

        # Recovery Triggered:
        gateway.replace_provider(StubModelProvider())
        resolve_escalation(
            session, failure_escalation.id, resolution="Model provider replaced; operations resumed."
        )

        # System Restored / Operations resumed:
        outcome = coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )
        assert outcome.validation.objective_achieved is True

        assert list_pending_escalations(session) == []
