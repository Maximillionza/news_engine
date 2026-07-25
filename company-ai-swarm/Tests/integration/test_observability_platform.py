"""Phase 8 exit-criteria test (part 2 of 3): the Observability Platform.

Source: IMPLEMENTATION_PLAN.md Phase 8 test spec item 2 / MVS Test Category 009:
    Execute a workflow and confirm logs, metrics, traces, and performance data are all
    recorded.

Also covers EOCCS sec.22-24's role-scoped views and sec.25's Alerting Model.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from agent_runtime.runtime import AgentRuntime
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.alerting import AlertSeverity, generate_alerts
from observability_service.telemetry import TelemetryResult, TelemetrySink
from observability_service.views import coo_view, department_view, director_view
from orchestrator.controller import COOOrchestrator
from orchestrator.department_registry import DepartmentRegistry
from security_service.permissions import grant_permission
from shared.contracts import AgentMessageContract
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]


class FailingModelProvider:
    """Deterministic failure, for exercising the technical-failure alerting path - not
    connected to any real model. Duplicated from test_escalation_policy.py rather than
    imported across test modules, since Tests/ isn't a package."""

    def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
        raise RuntimeError("simulated model provider failure")

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


def _grant_all(session: Session) -> None:
    for agent_id, department in FOUR_DEPARTMENT_AGENTS:
        create_identity(
            session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department
        )
        grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
        grant_permission(session, subject=agent_id, resource="memory:department", action="read")


def _run_four_department_workflow(session: Session) -> tuple[TelemetrySink, ModelGateway]:
    _grant_all(session)

    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()
    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    telemetry = TelemetrySink()
    gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
    coo = COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=gateway,
        telemetry=telemetry,
    )
    coo.receive_objective(session, FOUR_DEPARTMENT_OBJECTIVE, required_output="A validated implementation")
    return telemetry, gateway


class TestObservabilityMVS009:
    def test_logs_metrics_traces_performance_data_all_recorded(self, session: Session) -> None:
        telemetry, _ = _run_four_department_workflow(session)

        records = telemetry.query()
        assert len(records) > 0

        for record in records:
            assert record.component != ""  # traces: which component acted
            assert record.action != ""  # logs: what it did
            assert record.duration_ms >= 0  # performance data
            assert record.result in (
                TelemetryResult.SUCCESS,
                TelemetryResult.FAILURE,
                TelemetryResult.DENIED,
            )  # metrics: outcome signal

        # Every agent in the workflow left a trace under its own component name.
        components = {r.component for r in records}
        for agent_id, _ in FOUR_DEPARTMENT_AGENTS:
            assert f"agent_runtime:{agent_id}" in components


class TestCommandCentreViewsEOCCS22to24:
    def test_director_view_reports_health_and_major_decisions(self, session: Session) -> None:
        telemetry, _ = _run_four_department_workflow(session)

        view = director_view(telemetry, session)

        assert view.enterprise_health == "healthy"
        assert FOUR_DEPARTMENT_OBJECTIVE in view.major_decisions

    def test_coo_view_reports_workflow_performance(self, session: Session) -> None:
        telemetry, _ = _run_four_department_workflow(session)

        view = coo_view(telemetry, session)

        assert view.operational_status == "healthy"
        assert view.workflow_performance["total_actions"] > 0
        assert view.workflow_performance["failures"] == 0
        assert view.escalations == []

    def test_department_view_reports_agent_health(self, session: Session) -> None:
        telemetry, _ = _run_four_department_workflow(session)

        view = department_view(
            telemetry, department_id="engineering", agent_ids=["engineering_agent_001"]
        )

        assert view.department_id == "engineering"
        assert view.agent_health == "healthy"
        assert view.quality_metrics["actions_recorded"] > 0


class TestAlertingModelEOCCS25:
    def test_clean_run_produces_only_an_information_alert(self, session: Session) -> None:
        telemetry, _ = _run_four_department_workflow(session)

        alerts = generate_alerts(telemetry, session)

        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.INFORMATION

    def test_denied_permission_produces_a_warning_alert(self, session: Session) -> None:
        from agent_runtime.registry import AgentRegistry as _AR

        agent_registry = _AR(REPO_ROOT / "agents" / "active")
        agent_registry.load_all()
        agent = agent_registry.get("research_agent_001")
        # No permission granted for this identity - Check Policies (Phase 4) SHALL deny.
        create_identity(session, id="research_agent_001", entity_type=EntityType.AGENT, name="Research Agent")

        telemetry = TelemetrySink()
        gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
        runtime = AgentRuntime(agent, model_gateway=gateway, telemetry=telemetry)
        message = AgentMessageContract(
            sender_agent="coo", receiver_agent="research_agent_001", task="x", required_output="y"
        )

        with pytest.raises(PermissionError):
            runtime.execute_task(session, message)

        alerts = generate_alerts(telemetry, session)
        assert any(a.severity == AlertSeverity.WARNING for a in alerts)

    def test_technical_failure_escalation_produces_a_critical_alert(self, session: Session) -> None:
        _grant_all(session)
        department_registry = DepartmentRegistry(REPO_ROOT / "departments")
        department_registry.load_all()
        agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
        agent_registry.load_all()

        telemetry = TelemetrySink()
        gateway = ModelGateway(FailingModelProvider(), telemetry=telemetry)
        coo = COOOrchestrator(
            coo_id="coo",
            department_registry=department_registry,
            agent_registry=agent_registry,
            model_gateway=gateway,
            telemetry=telemetry,
        )

        with pytest.raises(RuntimeError):
            coo.receive_objective(session, "Create a market intelligence report", required_output="x")

        alerts = generate_alerts(telemetry, session)
        assert any(a.severity == AlertSeverity.CRITICAL for a in alerts)
