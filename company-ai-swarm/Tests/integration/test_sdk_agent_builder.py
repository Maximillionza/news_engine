"""Phase 10 exit-criteria test: use the SDK to define a new agent (not one of the original
four) without editing core runtime code; confirm it registers in the Agent Registry and
executes a task successfully through the existing COO/workflow path from Phases 5-7.

Source: IMPLEMENTATION_PLAN.md Phase 10 test spec.

Interpretation note: "the existing COO/workflow path" is exercised here via
`orchestrator.router.dispatch()` directly - the single dispatch function both
`orchestrator/controller.py`'s single-department path and `workflow_engine/engine.py`'s
per-task loop call for every task in this codebase since Phase 5, unmodified. A full
`COOOrchestrator.receive_objective()` run would require the new agent to also be added to a
department's `agents:` list (departments/*/definition.yaml) for the keyword matcher to ever
select it over the department's existing agent - that's a data-file edit, not a runtime-code
edit, but it isn't required to prove the exit criterion ("executes a task successfully
through the existing COO/workflow path"), so this test does not do it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from sqlalchemy.orm import Session

from agent_builder.builder import AgentDraft, build_agent
from agent_runtime.registry import AgentRegistry, load_agent_definition
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.department_registry import DepartmentRegistry
from orchestrator.router import dispatch
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider
from validation.pipeline import ComponentValidationError

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
    """Loaded from the real agents/active/ directory - proves the new agent coexists with
    the original four, not a synthetic empty registry."""

    registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    registry.load_all()
    return registry


class TestSDKAgentBuilderMVPPhase10:
    def test_new_agent_registers_and_executes_via_the_existing_dispatch_path(
        self, tmp_path: Path, session: Session, department_registry: DepartmentRegistry,
        agent_registry: AgentRegistry,
    ) -> None:
        assert agent_registry.get("data_science_agent_001") is None  # genuinely new

        telemetry = TelemetrySink()
        gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)

        draft = AgentDraft(
            identity_id="data_science_agent_001",
            name="Data Science Agent",
            department="research",
            mission="Apply statistical analysis to research findings.",
            capabilities=["research", "analysis"],
        )

        new_agent = build_agent(
            draft,
            session=session,
            department_registry=department_registry,
            agent_registry=agent_registry,
            model_gateway=gateway,
            agents_root=tmp_path,
        )

        # Registers in the Agent Registry:
        assert agent_registry.get("data_science_agent_001") is new_agent
        assert len(agent_registry) == 5  # original four + this one

        # Written to disk without touching any existing file (agents_root=tmp_path, not the
        # real agents/active/), and round-trips through the unmodified loader:
        written_path = tmp_path / "data_science_agent_001" / "agent.yaml"
        assert written_path.exists()
        reloaded = load_agent_definition(written_path)
        assert reloaded.identity.id == "data_science_agent_001"
        assert reloaded.capabilities == ["research", "analysis"]

        # Executes a task successfully through the existing COO/workflow dispatch path
        # (orchestrator/router.py's dispatch(), unmodified since Phase 5):
        result = dispatch(
            session,
            coo_id="coo",
            agent=new_agent,
            objective="Analyse the statistical significance of a research finding.",
            required_output="A confidence assessment",
            model_gateway=gateway,
            telemetry=telemetry,
        )

        assert result.output != ""
        assert len(result.steps_completed) == 10

    def test_unknown_department_fails_security_review_and_is_not_registered(
        self, tmp_path: Path, session: Session, department_registry: DepartmentRegistry,
        agent_registry: AgentRegistry,
    ) -> None:
        gateway = ModelGateway(StubModelProvider(), telemetry=TelemetrySink())
        draft = AgentDraft(
            identity_id="ghost_agent_001",
            name="Ghost Agent",
            department="does_not_exist",
            mission="x",
            capabilities=["x"],
        )

        with pytest.raises(ComponentValidationError, match="Unknown department"):
            build_agent(
                draft, session=session, department_registry=department_registry,
                agent_registry=agent_registry, model_gateway=gateway, agents_root=tmp_path,
            )

        assert agent_registry.get("ghost_agent_001") is None
        assert not (tmp_path / "ghost_agent_001").exists()

    def test_duplicate_agent_id_fails_architecture_check(
        self, tmp_path: Path, session: Session, department_registry: DepartmentRegistry,
        agent_registry: AgentRegistry,
    ) -> None:
        gateway = ModelGateway(StubModelProvider(), telemetry=TelemetrySink())
        draft = AgentDraft(
            identity_id="research_agent_001",  # already exists in agent_registry
            name="Duplicate Research Agent",
            department="research",
            mission="x",
            capabilities=["research"],
        )

        with pytest.raises(ComponentValidationError, match="already registered"):
            build_agent(
                draft, session=session, department_registry=department_registry,
                agent_registry=agent_registry, model_gateway=gateway, agents_root=tmp_path,
            )
