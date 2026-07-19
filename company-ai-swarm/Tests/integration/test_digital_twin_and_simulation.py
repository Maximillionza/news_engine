"""Phase 11: Digital Twin state synchronization (ESDTS sec.4/6/31) and the Workflow
Simulation Engine (ESDTS sec.9/11/12.5/14).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from digital_twin_service.snapshot import capture_snapshot
from identity_service.models import EntityType
from identity_service.repository import create_identity
from orchestrator.controller import COOOrchestrator
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from observability_service.telemetry import TelemetrySink
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider
from simulation_service.workflow_simulation import simulate_workflow_change

# Import so their tables are registered on Base.metadata before create_all() below.
import evolution_service.models  # noqa: F401
import simulation_service.models  # noqa: F401
import digital_twin_service.models  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _grant_agent(session: Session, agent_id: str, department: str) -> None:
    create_identity(session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department)
    grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
    grant_permission(session, subject=agent_id, resource="memory:department", action="read")


class TestDigitalTwinSnapshotESDTS:
    def test_snapshot_captures_real_agents_departments_and_recent_decisions(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        _grant_agent(session, "research_agent_001", "research")
        create_identity(session, id="coo", entity_type=EntityType.SERVICE, name="COO")

        telemetry = TelemetrySink()
        gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
        coo = COOOrchestrator(
            coo_id="coo", department_registry=department_registry, agent_registry=agent_registry,
            model_gateway=gateway, telemetry=telemetry,
        )
        coo.receive_objective(
            session, "Create a market intelligence report", required_output="A structured summary"
        )

        snapshot = capture_snapshot(session, agent_registry=agent_registry, department_registry=department_registry)

        agent_ids = {a["id"] for a in snapshot.agents}
        assert "research_agent_001" in agent_ids
        department_ids = {d["id"] for d in snapshot.departments}
        assert "research" in department_ids
        assert any(d["objective"] == "Create a market intelligence report" for d in snapshot.recent_decisions)


class TestWorkflowSimulationESDTS:
    def test_simulation_runs_both_variants_and_compares_real_metrics(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        operations = department_registry.get("operations")
        assert operations is not None

        simulation = simulate_workflow_change(
            session,
            objective="Monitor workflow quality and evaluate the outcome.",
            required_output="A quality assessment",
            baseline_departments=[operations],
            proposed_departments=[],
            agent_registry=agent_registry,
            scenario="Skip empty review",
        )

        assert simulation.predicted_results["baseline"]["task_count"] == 1
        assert simulation.predicted_results["proposed"]["task_count"] == 0
        assert simulation.predicted_results["proposed"]["succeeded"] is True
        assert simulation.advantages != []
        assert simulation.recommendation == "Adopt the proposed change."
        assert 0.0 <= simulation.confidence <= 1.0

        # Environment separation (ESDTS sec.9): the simulation must not have touched the
        # caller's real session/production data - only the SimulationRun record itself was
        # written here, no COO Decision Record or Escalation Record from the dry runs leaked
        # into this session.
        from orchestrator.decisions import list_decisions

        assert list_decisions(session) == []

    def test_simulation_with_unmatched_department_still_reports_a_baseline(
        self, session: Session, department_registry: DepartmentRegistry, agent_registry: AgentRegistry
    ) -> None:
        research = department_registry.get("research")
        fabricated_empty = DepartmentDefinition(
            id="operations", name="Operations Department", capabilities=[], agents=["review_agent_001"]
        )

        simulation = simulate_workflow_change(
            session,
            objective="Create a market intelligence report",
            required_output="A structured summary",
            baseline_departments=[research],
            proposed_departments=[research, fabricated_empty],
            agent_registry=agent_registry,
            scenario="Compare research-only vs research+review",
        )

        assert simulation.predicted_results["baseline"]["task_count"] == 1
        assert simulation.predicted_results["proposed"]["task_count"] == 2
