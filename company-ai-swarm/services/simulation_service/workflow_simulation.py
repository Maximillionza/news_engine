"""Workflow Simulation Engine.

Source: ESDTS sec.9 (Simulation Environment Separation: "Changes are tested in simulation
first" - Production -> Digital Twin -> Simulation Environment), sec.11 (Workflow Simulation
Engine: "Test operational processes... Measures: Completion time, Bottlenecks, Failure
probability, Resource usage"), sec.12.5 (Workflow Simulation: "Can this approval step be
automated?" - literally the shape of the one scenario this module is built to answer).

Phase 11 scope (IMPLEMENTATION_PLAN.md, post-MVP Intelligence Systems): this is a real dry
run, not a fabricated prediction. Both the baseline and proposed department lists are
executed through the unmodified Phase 6/7 workflow_engine.execute_workflow(), against a
throwaway in-memory database and a fresh identity/permission set constructed here - never
the caller's real session - so a simulation can never write production state (sec.9's
Environment Separation, taken literally: the simulation runs in its own sandbox, not just a
sandboxed *query* against production data). Metrics (task count, telemetry record count,
success) are measured from real execution, not estimated. There is no behaviour-prediction
model beyond that - no real model exists anywhere in this corpus (shared/model_gateway.py's
StubModelProvider is deterministic and content-blind), so "predicted_results" here means
"observed results of an actual dry run," and `confidence` is set low and explained in
`limitations` rather than invented.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.department_registry import DepartmentDefinition
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider
from simulation_service.models import SimulationRun
from workflow_engine.engine import execute_workflow
from workflow_engine.models import WorkflowRun


def _run_in_sandbox(
    *, objective: str, required_output: str, departments: list[DepartmentDefinition], agent_registry: AgentRegistry
) -> tuple[WorkflowRun, int]:
    """Executes one variant end to end in an isolated, throwaway environment. Returns the
    WorkflowRun and the number of telemetry records it produced (a real Resource Usage
    proxy - ESDTS sec.11)."""

    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    telemetry = TelemetrySink()
    gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)

    with session_factory() as sandbox_session:
        agent_ids = {agent_id for d in departments for agent_id in d.agents}
        for agent_id in agent_ids:
            agent = agent_registry.get(agent_id)
            if agent is None:
                continue
            create_identity(
                sandbox_session, id=agent_id, entity_type=EntityType.AGENT, name=agent.identity.name
            )
            grant_permission(sandbox_session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
            grant_permission(sandbox_session, subject=agent_id, resource="memory:department", action="read")
            grant_permission(sandbox_session, subject=agent_id, resource="memory:department", action="write")

        workflow = execute_workflow(
            sandbox_session,
            coo_id="simulation",
            objective=objective,
            required_output=required_output,
            departments=departments,
            agent_registry=agent_registry,
            model_gateway=gateway,
            # Phase 17 (IMPLEMENTATION_PLAN.md, 2026-07-23): execute_workflow() now records a
            # SpecialistSpawnRecord per spawn, keyed to a decision_id - this sandbox never has
            # a real COO Decision Record (there is no real objective here), so a synthetic id
            # scoped to this throwaway run is enough; the whole database is discarded when
            # this function returns.
            decision_id=f"SIM-{uuid4().hex[:8]}",
            telemetry=telemetry,
        )

    return workflow, len(telemetry.query())


def simulate_workflow_change(
    session: Session,
    *,
    objective: str,
    required_output: str,
    baseline_departments: list[DepartmentDefinition],
    proposed_departments: list[DepartmentDefinition],
    agent_registry: AgentRegistry,
    scenario: str,
) -> SimulationRun:
    baseline_run, baseline_telemetry_count = _run_in_sandbox(
        objective=objective, required_output=required_output,
        departments=baseline_departments, agent_registry=agent_registry,
    )
    proposed_run, proposed_telemetry_count = _run_in_sandbox(
        objective=objective, required_output=required_output,
        departments=proposed_departments, agent_registry=agent_registry,
    )

    predicted_results = {
        "baseline": {
            "task_count": len(baseline_run.tasks),
            "telemetry_record_count": baseline_telemetry_count,
            "succeeded": baseline_run.succeeded,
        },
        "proposed": {
            "task_count": len(proposed_run.tasks),
            "telemetry_record_count": proposed_telemetry_count,
            "succeeded": proposed_run.succeeded,
        },
    }

    advantages = []
    risks = []
    if len(proposed_run.tasks) < len(baseline_run.tasks):
        advantages.append(
            f"Fewer tasks dispatched ({len(proposed_run.tasks)} vs {len(baseline_run.tasks)}) - "
            f"less resource usage per objective (ESDTS sec.11)."
        )
    if not proposed_run.succeeded and baseline_run.succeeded:
        risks.append("The proposed variant did not complete successfully in simulation.")

    recommendation = (
        "Adopt the proposed change." if (proposed_run.succeeded and advantages and not risks)
        else "Do not adopt without further review."
    )

    run = SimulationRun(
        id=f"SIM-{uuid4().hex[:8]}",
        objective=objective,
        starting_state={
            "baseline_departments": [d.id for d in baseline_departments],
            "proposed_departments": [d.id for d in proposed_departments],
        },
        variables={"required_output": required_output},
        constraints={"sandboxed": True, "model_provider": "stub"},
        assumptions=[
            "StubModelProvider output is deterministic and content-blind - this simulation "
            "measures real task/telemetry counts, not output quality or business value.",
        ],
        success_metrics=["task_count", "telemetry_record_count", "succeeded"],
        scenario=scenario,
        predicted_results=predicted_results,
        risks=risks,
        advantages=advantages,
        limitations=[
            "No real model or business-outcome measure exists anywhere in this corpus - "
            "'predicted_results' are observed dry-run metrics, not forecasts of real-world "
            "quality, cost, or duration.",
        ],
        confidence=0.4,  # low, deliberately - see limitations above
        recommendation=recommendation,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
