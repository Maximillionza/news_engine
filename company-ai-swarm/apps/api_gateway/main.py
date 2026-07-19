"""API Gateway.

Per Specifications/2 - construction-framework/The Company Repository Blueprint Specification
(CRBS).md, this is the external entry point (apps/api_gateway/). Phase 0 proved only that the
dev environment runs (`/health`). Phase 10 (IMPLEMENTATION_PLAN.md, post-MVP Expansion
Layer) wires this to the already-built COOOrchestrator (Phases 5-9), per
Specifications/4 - future-expansion/Enterprise API Architecture Specification (EAAS).md
sec.18's MVP API Requirements: Objective submission, Task tracking, Workflow status, Agent
visibility, Result retrieval, Authentication, Audit logging. No new orchestration logic - this
is the external HTTP surface over what already exists.

Dev/test: a SQLite file next to this module (shared.db.make_engine()), same
dev/test-vs-production substitution pattern as every other service - see
Documentation/operations/technology_decisions.md. Production: the already-provisioned
Postgres instance (docker-compose.yml).

Authentication (EAAS sec.8): a single static API key checked via the `X-API-Key` header, not
OAuth/JWT/session-based auth - EAAS sec.18 requires "Authentication" exist at MVP level, it
does not mandate a scheme. This is explicitly a placeholder, not production-grade; swap when
a real identity provider is wired in. Audit logging (EAAS's own MVP requirement) reuses
security_service's existing audit trail - no second audit mechanism.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Generator

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from identity_service.models import EntityType
from identity_service.repository import create_identity, get_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.classification import create_classifier_from_env
from orchestrator.controller import (
    COOOrchestrator,
    DepartmentRejectedError,
    NoMatchingDepartmentError,
    WorkflowObjectiveOutcome,
)
from orchestrator.decisions import get_decision
from orchestrator.head import create_head_from_env
from orchestrator.department_registry import DepartmentRegistry
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway
from shared.providers import create_provider_from_env

app = FastAPI(title="The Company - API Gateway", version="0.2.0")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEV_DB_PATH = Path(__file__).resolve().parent / "api_gateway_dev.sqlite3"
_API_KEY = os.environ.get("THE_COMPANY_API_KEY", "dev-only-api-key")

_engine = make_engine(f"sqlite:///{_DEV_DB_PATH}")
Base.metadata.create_all(_engine)
_SessionFactory = make_session_factory(_engine)

_telemetry = TelemetrySink()
# MODEL_PROVIDER env var selects stub (default, no credentials) / anthropic (API-key
# billing) / agent_sdk (subscription-capable) - see shared/providers/__init__.py and
# Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.1.
_model_gateway = ModelGateway(create_provider_from_env(), telemetry=_telemetry)
_department_registry = DepartmentRegistry(_REPO_ROOT / "departments")
_department_registry.load_all()
_agent_registry = AgentRegistry(_REPO_ROOT / "agents" / "active")
_agent_registry.load_all()
_coo = COOOrchestrator(
    coo_id="coo",
    department_registry=_department_registry,
    agent_registry=_agent_registry,
    model_gateway=_model_gateway,
    telemetry=_telemetry,
    # DEPARTMENT_CLASSIFIER env var selects keyword (default, no credentials) / llm (real
    # Claude-backed routing) - see orchestrator/classification.py and Documentation/plans/
    # 2026-07-19-dynamic-department-routing-design.md Section 3.3.
    classifier=create_classifier_from_env(_model_gateway),
    # DEPARTMENT_HEAD_TRIAGE env var selects auto_accept (default, no credentials) / llm
    # (real Claude-backed triage) - see orchestrator/head.py and Documentation/plans/
    # 2026-07-19-department-head-triage-design.md Section 3.2.
    head=create_head_from_env(),
)


def _bootstrap_identities(session: Session) -> None:
    """Grants every already-scaffolded agent (and the COO) the permissions their normal
    operation needs, so a fresh deployment works out of the box - the same grants every
    Phase 5-9 test fixture sets up by hand."""

    if get_identity(session, "coo") is None:
        create_identity(session, id="coo", entity_type=EntityType.SERVICE, name="COO")
        grant_permission(session, subject="coo", resource="memory:historical", action="write")
        grant_permission(session, subject="coo", resource="memory:project", action="write")

    # The dashboard's human operator (EESIS sec.10 / ESTAS sec.21): the identity the
    # dashboard's proposal approve/reject/implement buttons act as. A HUMAN identity with the
    # explicit `evolution:change_proposal approve` grant the Evolution Engine itself is never
    # given - the dashboard exercises the hard gate, it does not bypass it.
    if get_identity(session, "dashboard_director") is None:
        create_identity(
            session, id="dashboard_director", entity_type=EntityType.HUMAN, name="Dashboard Director"
        )
        grant_permission(
            session, subject="dashboard_director", resource="evolution:change_proposal", action="approve"
        )
        grant_permission(
            session, subject="dashboard_director", resource="memory:historical", action="write"
        )

    for agent in _agent_registry.all():
        agent_id = agent.identity.id
        if get_identity(session, agent_id) is None:
            create_identity(session, id=agent_id, entity_type=EntityType.AGENT, name=agent.identity.name)
        grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
        grant_permission(session, subject=agent_id, resource="memory:department", action="read")
        grant_permission(session, subject=agent_id, resource="memory:department", action="write")


with _SessionFactory() as _bootstrap_session:
    _bootstrap_identities(_bootstrap_session)


def get_session() -> Generator[Session, None, None]:
    session = _SessionFactory()
    try:
        yield session
    finally:
        session.close()


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "api_gateway"}


def _serialize_outcome(outcome: Any) -> dict[str, Any]:
    """Task tracking / Workflow status / Result retrieval, generalized across the two
    receive_objective() return shapes (orchestrator/controller.py) - a single department
    (ObjectiveOutcome) or a workflow (WorkflowObjectiveOutcome)."""

    if isinstance(outcome, WorkflowObjectiveOutcome):
        return {
            "decision_id": outcome.decision_id,
            "objective_achieved": outcome.objective_achieved,
            "departments": [d.id for d in outcome.matched_departments],
            "tasks": [
                {
                    "department": t.department.id,
                    "agent_id": t.agent_id,
                    "output": t.execution_result.output,
                    "objective_achieved": t.validation.objective_achieved,
                }
                for t in outcome.workflow.tasks
            ],
        }

    return {
        "decision_id": outcome.decision_id,
        "objective_achieved": outcome.validation.objective_achieved,
        "departments": [outcome.task_profile.matched_department.id],
        "tasks": [
            {
                "department": outcome.task_profile.matched_department.id,
                # AgentRuntime's Produce Artifact step (Phase 4) always includes agent_id.
                "agent_id": outcome.execution_result.artifact.get("agent_id"),
                "output": outcome.execution_result.output,
                "objective_achieved": outcome.validation.objective_achieved,
            }
        ],
    }


@app.post("/objectives")
def submit_objective(
    body: dict[str, str],
    session: Session = Depends(get_session),
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    """EAAS sec.18: Objective submission."""

    objective = body.get("objective")
    required_output = body.get("required_output")
    if not objective or not required_output:
        raise HTTPException(status_code=422, detail="Both 'objective' and 'required_output' are required.")

    try:
        outcome = _coo.receive_objective(session, objective, required_output=required_output)
    except NoMatchingDepartmentError as exc:
        raise HTTPException(status_code=400, detail=f"No department matched this objective: {exc}") from exc
    except DepartmentRejectedError as exc:
        raise HTTPException(status_code=400, detail=f"Every department rejected this objective: {exc}") from exc

    return _serialize_outcome(outcome)


@app.get("/objectives/{decision_id}")
def get_objective_status(
    decision_id: str,
    session: Session = Depends(get_session),
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    """EAAS sec.18: Task tracking / Workflow status / Result retrieval, by Decision Record
    (COOS sec.22), the same record orchestrator/controller.py already writes for every
    objective."""

    record = get_decision(session, decision_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown decision_id: {decision_id}")

    return {
        "decision_id": record.id,
        "objective": record.objective,
        "reasoning": record.reasoning,
        "chosen_action": record.chosen_action,
        "agents_selected": record.agents_selected,
        "outcome": record.outcome,
    }


@app.get("/agents")
def list_agents(_: None = Depends(require_api_key)) -> list[dict[str, Any]]:
    """EAAS sec.18: Agent visibility."""

    return [
        {
            "id": agent.identity.id,
            "name": agent.identity.name,
            "department": agent.department.name,
            "capabilities": agent.capabilities,
        }
        for agent in _agent_registry.all()
    ]


# --- Dashboard (apps/web_interface) -------------------------------------------------------
# The dashboard's aggregation/command endpoints live in dashboard_api.py; its chat table is
# registered on shared.db.Base by that import, so create_all runs again (idempotent) after.
# apps/ is not a package (tests sys.path-insert this directory and `import main`), so
# dashboard_api is imported the same sibling-module way. objective_queue and queue_worker
# (Phase A/B, Documentation/plans/SDK_MIGRATION_PLAN.md) are sibling modules too.

import sys  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dashboard_api  # noqa: E402
from objective_queue import get_objective  # noqa: E402
from queue_worker import QueueWorker, WorkerCycleResult  # noqa: E402

Base.metadata.create_all(_engine)
app.include_router(
    dashboard_api.build_router(
        coo=_coo,
        department_registry=_department_registry,
        agent_registry=_agent_registry,
        telemetry=_telemetry,
        serialize_outcome=_serialize_outcome,
        get_session=get_session,
        require_api_key=require_api_key,
        uploads_dir=_REPO_ROOT / "uploads" / "inbox",
    )
)


@app.get("/objectives/{objective_id}/result")
def get_objective_result(
    objective_id: str,
    session: Session = Depends(get_session),
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    """Phase B (SDK_MIGRATION_PLAN.md Section 4.2 item 4): polling target for anything
    submitted via `POST /chat`'s fire-and-forget response. Distinct from
    `GET /objectives/{decision_id}` above - that looks up a Decision Record (COOS sec.22) by
    `decision_id`, which does not exist until a worker actually runs `receive_objective()`;
    this looks up the `objective_queue` row by `objective_id`, which exists from the moment
    `POST /chat` returns. No ETA field - nothing in this codebase estimates remaining
    execution time."""

    record = get_objective(session, objective_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown objective_id: {objective_id}")

    return {
        "objective_id": record.id,
        "status": record.status,
        "objective": record.objective,
        "required_output": record.required_output,
        "result": record.result,
        "error": record.error,
        "submitted_by": record.submitted_by,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
    }


# The queue worker itself does NOT run here - Section 4.2 item 3 calls for it to run "as a
# background worker (separate from FastAPI process)", not an in-process thread inside this
# module. See Scripts/run_queue_worker.py, which imports `_queue_handler` and
# `_SessionFactory` from this module and calls queue_worker.run_forever() in its own OS
# process. Kept out of this module's import-time side effects deliberately: main.py is
# imported repeatedly across Tests/integration/*.py against the same on-disk dev sqlite
# file, and a live background thread racing test assertions would be a flakiness source for
# no benefit - tests call `drain_queue_once()` below to force one deterministic cycle
# instead of waiting on a poll interval.
_queue_handler = dashboard_api.build_queue_handler(coo=_coo, serialize_outcome=_serialize_outcome)
_queue_worker = QueueWorker(handler=_queue_handler)


def drain_queue_once() -> WorkerCycleResult:
    """Forces one queue-worker cycle synchronously - the deterministic alternative to
    waiting on Scripts/run_queue_worker.py's poll interval. Used by tests
    (Tests/integration/test_api_gateway_async.py) and available for manual/ops use."""

    with _SessionFactory() as session:
        return _queue_worker.run_once(session)


_UI_DIST = Path(__file__).resolve().parents[1] / "web_interface" / "dist"
if _UI_DIST.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/ui", StaticFiles(directory=_UI_DIST, html=True), name="dashboard")
