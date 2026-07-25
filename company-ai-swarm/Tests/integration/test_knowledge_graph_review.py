"""Phase 7 exit-criteria test: MVS Test Categories 003 (Department Operation) and 006
(Knowledge Graph), together.

Source: IMPLEMENTATION_PLAN.md Phase 7 test spec:
    1. Submit an objective exercising all four departments: Research -> Engineering ->
       Compliance -> Review.
    2. Confirm Review Agent produces a pass/fail validation with documented reasoning.
    3. Query the Knowledge Graph for the relationship `Agent USES Capability APPLIES_TO
       Workflow` created by this run and confirm it resolves correctly.

Exit criteria: a full four-department workflow completes with a review gate, and the
resulting relationships are queryable in the Knowledge Graph. This is EIB's MVP Build Order
Version 0.3.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from identity_service.models import EntityType
from identity_service.repository import create_identity
from knowledge_service.repository import get_entity, get_relationships_for_entity
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, WorkflowObjectiveOutcome
from orchestrator.decisions import get_decision
from orchestrator.department_registry import DepartmentRegistry
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]

FOUR_DEPARTMENT_OBJECTIVE = (
    "Research requirements, assess risk, and build software while monitoring quality."
)
FOUR_DEPARTMENT_AGENTS = [
    ("research_agent_001", "research"),
    ("engineering_agent_001", "engineering"),
    ("compliance_agent_001", "compliance"),
    ("review_agent_001", "operations"),
]


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

    for agent_id, department in FOUR_DEPARTMENT_AGENTS:
        create_identity(
            session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department
        )
        grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
        grant_permission(session, subject=agent_id, resource="memory:department", action="read")

    telemetry = TelemetrySink()
    gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)

    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=gateway,
        telemetry=telemetry,
    )


class TestFourDepartmentWorkflowMVS003:
    def test_objective_matches_all_four_departments_in_canonical_order(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation"
        )

        assert isinstance(outcome, WorkflowObjectiveOutcome)
        assert [d.id for d in outcome.matched_departments] == [
            "research",
            "engineering",
            "compliance",
            "operations",
        ]

    def test_workflow_executes_all_four_agents_in_sequence_and_succeeds(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation"
        )

        assert outcome.objective_achieved is True
        assert [t.agent_id for t in outcome.workflow.tasks] == [
            "research_agent_001",
            "engineering_agent_001",
            "compliance_agent_001",
            "review_agent_001",
        ]


class TestReviewAgentProducesPassFailWithReasoningMVS003:
    def test_review_agent_runs_last_with_a_pass_fail_validation_and_reasoning(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation"
        )

        review_task = outcome.workflow.tasks[-1]
        assert review_task.department.id == "operations"
        assert review_task.agent_id == "review_agent_001"

        # Pass/fail:
        assert review_task.validation.objective_achieved is True
        # Documented reasoning - the Review Agent's own produced output, not a separate
        # judgement mechanism (see workflow_engine/review.py's docstring).
        assert review_task.execution_result.output != ""

    def test_review_tier_is_risk_proportional_per_tdl_17(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation"
        )

        # Phase 20 (IMPLEMENTATION_PLAN.md, 2026-07-25): workflow_engine/complexity.py now
        # really computes this - FOUR_DEPARTMENT_OBJECTIVE matches 3 substantive departments
        # (research/engineering/compliance) plus the review step, which assess_complexity()
        # classifies as "Level 3 Advanced" -> "department_review" per review.py's table.
        # Previously asserted "peer_review", back when complexity_level was a fixed
        # "Level 2 Standard" with no real producer (see that module's docstring, pre-Phase-20).
        assert outcome.workflow.review_tier == "department_review"

    def test_decision_record_captures_review_tier_and_outcome(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation"
        )

        record = get_decision(session, outcome.decision_id)

        assert record is not None
        assert record.agents_selected == [
            "research_agent_001",
            "engineering_agent_001",
            "compliance_agent_001",
            "review_agent_001",
        ]
        # Phase 20: see test_review_tier_is_risk_proportional_per_tdl_17 above for why this
        # is "department_review", not the old fixed "peer_review".
        assert "review_tier=department_review" in record.outcome
        assert "objective_achieved=True" in record.outcome


class TestKnowledgeGraphRelationshipsMVS006:
    def test_agent_uses_capability_applies_to_workflow_resolves(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        outcome = coo.receive_objective(
            session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation"
        )
        workflow_id = outcome.workflow.workflow_id

        # Research's task -> Agent --USES--> Capability --APPLIES_TO--> Workflow.
        capability_id = "capability:research:research"
        relationships = get_relationships_for_entity(session, capability_id)

        uses = next(
            r
            for r in relationships
            if r.relationship_type == "USES" and r.target_entity_id == capability_id
        )
        applies_to = next(
            r
            for r in relationships
            if r.relationship_type == "APPLIES_TO" and r.source_entity_id == capability_id
        )

        assert uses.source_entity_id == "agent:research_agent_001"
        assert get_entity(session, uses.source_entity_id).object_type == "Agent"

        assert get_entity(session, capability_id).object_type == "Capability"

        assert applies_to.target_entity_id == f"workflow:{workflow_id}"
        assert get_entity(session, applies_to.target_entity_id).object_type == "Workflow"

    def test_review_agent_is_also_recorded_in_the_knowledge_graph(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        coo.receive_objective(
            session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation"
        )

        capability_id = "capability:operations:validation"
        relationships = get_relationships_for_entity(session, capability_id)
        uses = next(
            r
            for r in relationships
            if r.relationship_type == "USES" and r.target_entity_id == capability_id
        )

        assert uses.source_entity_id == "agent:review_agent_001"

    def test_capability_entity_accumulates_relationships_across_separate_workflow_runs(
        self, session: Session, coo: COOOrchestrator
    ) -> None:
        """A knowledge graph entity is reused, not recreated, across separate runs -
        get_or_create_entity()'s whole purpose (knowledge_service/repository.py)."""

        first = coo.receive_objective(
            session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation"
        )
        second = coo.receive_objective(
            session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation"
        )
        assert first.workflow.workflow_id != second.workflow.workflow_id

        capability_id = "capability:research:research"
        relationships = get_relationships_for_entity(session, capability_id)
        applies_to_workflows = {
            r.target_entity_id for r in relationships if r.relationship_type == "APPLIES_TO"
        }

        assert f"workflow:{first.workflow.workflow_id}" in applies_to_workflows
        assert f"workflow:{second.workflow.workflow_id}" in applies_to_workflows
