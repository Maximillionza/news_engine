"""Dashboard API: the endpoints the web dashboard (apps/web_interface) polls and posts to.

Phase 12 (dashboard, post-Phase-11 addition): a thin aggregation-and-command surface over
what already exists - no new orchestration logic, same rule as the rest of this gateway.

- GET  /activity   - one aggregated poll target (agents, departments, decisions, escalations,
                     proposals, metrics, in_flight_objectives) so the UI's configurable
                     refresh hits one endpoint.
- GET  /chat, POST /chat - the COO chat. Phase B (Documentation/plans/
                     SDK_MIGRATION_PLAN.md Section 4.2): `POST /chat` is now fire-and-forget
                     - it enqueues the objective and returns {objective_id, status}
                     immediately, instead of blocking on COOOrchestrator. The "coo" reply
                     this used to write synchronously is now written by
                     `build_queue_handler()`'s handler once the queue worker (a separate
                     process - see Scripts/run_queue_worker.py) actually processes the
                     objective. `GET /chat` is unchanged - it still returns the 10 most
                     recent transcript lines.
- POST /chat/sync  - preserves the pre-Phase-B blocking behavior exactly (Section 6: "keep
                     /chat/sync for testing... /chat for production"). Not used by the
                     dashboard UI.
- POST /files      - saves an uploaded file (base64 JSON, avoiding a python-multipart
                     dependency) into uploads/inbox/ - the pickup location the swarm can
                     consume, referenced in the next chat message.
- POST /proposals/{id}/approve|reject|implement - the Evolution hard gate, exercised by a
                     human through the dashboard. Acts as the `dashboard_director` HUMAN
                     identity, which holds the explicit `evolution:change_proposal approve`
                     grant (EESIS sec.10, ESTAS sec.21) - the same no-bypass
                     security_service.authorize() path as everywhere else.

Agent "working" status is still the same honest approximation Phase 12 shipped: an agent
shows as working if it was selected by a decision created within the last
ACTIVE_WINDOW_SECONDS; otherwise idle. SDK_MIGRATION_PLAN.md Section 4.3 describes a third
"waiting" state ("waiting for user input, e.g. during chat turn") - deliberately not
implemented here. Nothing in this codebase's agent execution model pauses mid-task waiting
for user input (AgentRuntime.execute_task, services/agent_runtime/runtime.py, runs straight
through Receive Task -> ... -> Release Context with no such pause point), so a third state
would have no real signal to derive it from; inventing one would be a guess dressed up as a
feature. `in_flight_objectives` (below) is the concrete, well-specified piece of Section 4.3
this phase actually implements.
"""

from __future__ import annotations

import base64
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from evolution_service.models import ChangeProposal, ProposalStatus
from evolution_service.pipeline import EvolutionApprovalError, EvolutionEngine
from orchestrator.controller import NoMatchingDepartmentError
from orchestrator.decisions import list_decisions
from orchestrator.escalations import list_pending_escalations
from shared.db import Base

# apps/ is not a package (see apps/api_gateway/main.py's note on this same import there) -
# same-directory sibling import, valid once apps/api_gateway is on sys.path.
from objective_queue import ObjectiveQueueRecord, enqueue_objective, list_in_flight_objectives

ACTIVE_WINDOW_SECONDS = 120

# objective_queue.submitted_by marker for objectives that came from the dashboard chat, as
# opposed to (in the future) the EAAS /objectives endpoint or a voice interface - lets
# build_queue_handler() decide whether to write a DashboardChatMessage reply for a given
# completed objective.
DASHBOARD_CHAT_SUBMITTER = "dashboard_chat"


class DashboardChatMessage(Base):
    __tablename__ = "dashboard_chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    decision_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite round-trips timezone-aware datetimes back as naive; re-anchor to UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _run_objective_and_format_reply(
    session: Session,
    *,
    coo,
    objective: str,
    required_output: str,
    serialize_outcome: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    """Shared by `chat_send_sync` (blocking, in `build_router` below) and
    `build_queue_handler` (async, via the queue worker) - both call
    `COOOrchestrator.receive_objective()` and shape the result into the same
    `{reply, decision_id}` dashboard-chat reply; they differ only in *when* this runs and
    what happens to the result afterwards."""

    try:
        outcome = coo.receive_objective(session, objective, required_output=required_output)
        serialized = serialize_outcome(outcome)
        departments = ", ".join(serialized["departments"])
        achieved = serialized["objective_achieved"]
        reply = (
            f"Objective routed to {departments}. "
            f"{'Delivered' if achieved else 'Completed with issues'} "
            f"({len(serialized['tasks'])} task(s), decision {serialized['decision_id']})."
        )
        return {"reply": reply, "decision_id": serialized["decision_id"], "outcome": serialized}
    except NoMatchingDepartmentError as exc:
        # Not a failure - a legitimate outcome the pre-Phase-B synchronous /chat already
        # treated as a normal (non-error) reply. Preserved here so the async path completes
        # the objective_queue row rather than failing it for the same case.
        return {"reply": f"No department matched that objective: {exc}", "decision_id": None}


def build_queue_handler(
    *, coo, serialize_outcome: Callable[[Any], dict[str, Any]]
) -> Callable[[Session, ObjectiveQueueRecord], dict[str, Any]]:
    """The real `queue_worker.Handler` for objectives submitted via `POST /chat`
    (Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.2/5 Phase B) - the counterpart to
    Phase A's trivial stub handlers. Runs in the worker's own session, not the original HTTP
    request's (which has already returned by the time this fires). If the objective came
    from the dashboard chat, also writes the "coo" reply into the same DashboardChatMessage
    transcript `chat_history()` reads, so the dashboard's chat still shows a reply once the
    worker finishes - exactly what the old synchronous `chat_send` did inline. Any exception
    other than `NoMatchingDepartmentError` (which `_run_objective_and_format_reply` already
    turns into a normal reply) propagates out of this function; `queue_worker.QueueWorker`
    catches it and marks the objective `failed`."""

    def handler(session: Session, record: ObjectiveQueueRecord) -> dict[str, Any]:
        result = _run_objective_and_format_reply(
            session,
            coo=coo,
            objective=record.objective,
            required_output=record.required_output,
            serialize_outcome=serialize_outcome,
        )

        if record.submitted_by == DASHBOARD_CHAT_SUBMITTER:
            session.add(
                DashboardChatMessage(
                    role="coo", content=result["reply"], decision_id=result.get("decision_id")
                )
            )
            session.commit()

        return result

    return handler


def build_router(
    *,
    coo,
    department_registry,
    agent_registry,
    telemetry,
    serialize_outcome: Callable[[Any], dict[str, Any]],
    get_session,
    require_api_key,
    uploads_dir: Path,
) -> APIRouter:
    router = APIRouter()
    evolution_engine = EvolutionEngine()

    def _recent_decisions(session: Session, limit: int = 50) -> list[Any]:
        return list_decisions(session)[-limit:]

    @router.get("/activity")
    def activity(
        session: Session = Depends(get_session), _: None = Depends(require_api_key)
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        decisions = _recent_decisions(session)
        active_agents: set[str] = set()
        active_departments: set[str] = set()
        for record in decisions:
            created = _aware(record.created_at)
            if created is not None and now - created <= timedelta(seconds=ACTIVE_WINDOW_SECONDS):
                active_agents.update(record.agents_selected or [])

        agents = []
        for agent in agent_registry.all():
            working = agent.identity.id in active_agents
            if working:
                active_departments.add(agent.department.name.lower())
            agents.append(
                {
                    "id": agent.identity.id,
                    "name": agent.identity.name,
                    "department": agent.department.name,
                    "capabilities": agent.capabilities,
                    "status": "working" if working else "idle",
                }
            )

        escalations = [
            {
                "id": esc.id,
                "decision_id": esc.decision_id,
                "condition": esc.condition,
                "reasoning": esc.reasoning,
                "created_at": (_aware(esc.created_at) or now).isoformat(),
            }
            for esc in list_pending_escalations(session)
        ]

        proposals = [
            {
                "id": prop.id,
                "target": prop.target,
                "proposed_state": prop.proposed_state,
                "reason": prop.reason,
                "risk": prop.risk,
                "status": prop.approval_status.value,
                "resolved_by": prop.resolved_by,
                "created_at": (_aware(prop.created_at) or now).isoformat(),
            }
            for prop in session.query(ChangeProposal).order_by(ChangeProposal.created_at).all()
        ]

        decision_items = [
            {
                "decision_id": record.id,
                "objective": record.objective,
                "chosen_action": record.chosen_action,
                "agents_selected": record.agents_selected,
                "outcome": record.outcome,
                "created_at": (_aware(record.created_at) or now).isoformat(),
            }
            for record in reversed(decisions)
        ]

        achieved = sum(1 for d in decisions if "objective_achieved=True" in (d.outcome or ""))
        completed = sum(1 for d in decisions if d.outcome)

        # Phase B (SDK_MIGRATION_PLAN.md Section 4.3): objectives queued or executing right
        # now - the concrete piece of "in-flight" visibility this phase implements (see this
        # module's docstring for the three-state agent status this deliberately skips).
        # ETA is not included: nothing in this codebase estimates remaining execution time,
        # and fabricating one would be a guess dressed up as data.
        in_flight = [
            {
                "id": r.id,
                "status": r.status,
                "objective": r.objective,
                "required_output": r.required_output,
                "submitted_by": r.submitted_by,
                "submitted_at": (_aware(r.created_at) or now).isoformat(),
                "started_at": (_aware(r.started_at).isoformat() if r.started_at else None),
            }
            for r in list_in_flight_objectives(session)
        ]

        return {
            "time": now.isoformat(),
            "departments": [
                {
                    "id": dept.id,
                    "name": dept.name,
                    "mission": dept.mission,
                    "agents": dept.agents,
                    "active": dept.id in active_departments or dept.name.lower() in active_departments,
                }
                for dept in department_registry.all()
            ],
            "agents": agents,
            "decisions": decision_items,
            "escalations": escalations,
            "proposals": proposals,
            "in_flight_objectives": in_flight,
            "metrics": {
                "objectives_total": len(decisions),
                "objectives_completed": completed,
                "objectives_achieved": achieved,
                "objectives_in_flight": len(in_flight),
                "agents_total": len(agents),
                "agents_working": sum(1 for a in agents if a["status"] == "working"),
                "telemetry_records": len(telemetry),
                "pending_escalations": len(escalations),
                "pending_proposals": sum(1 for p in proposals if p["status"] == "pending"),
            },
        }

    @router.get("/chat")
    def chat_history(
        session: Session = Depends(get_session), _: None = Depends(require_api_key)
    ) -> dict[str, Any]:
        total = session.query(DashboardChatMessage).count()
        recent = (
            session.query(DashboardChatMessage)
            .order_by(DashboardChatMessage.id.desc())
            .limit(10)
            .all()
        )
        return {
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "decision_id": m.decision_id,
                    "created_at": (_aware(m.created_at) or datetime.now(timezone.utc)).isoformat(),
                }
                for m in reversed(recent)
            ],
            "archived": max(0, total - 10),
        }

    def _build_objective_from_chat_body(body: dict[str, Any]) -> tuple[str, str]:
        """Shared by chat_send and chat_send_sync: validates the request body and returns
        (objective_text, required_output). Also writes the user's DashboardChatMessage row -
        both endpoints do this identically, immediately, regardless of whether the objective
        itself runs synchronously or gets queued."""

        message = (body.get("message") or "").strip()
        file_path = body.get("file_path")
        if not message and not file_path:
            raise HTTPException(status_code=422, detail="'message' is required.")

        objective = message or "Process the attached file."
        if file_path:
            objective = f"{objective}\nInput file saved at: {file_path}"

        return objective, (body.get("required_output") or "response")

    @router.post("/chat")
    def chat_send(
        body: dict[str, Any],
        session: Session = Depends(get_session),
        _: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        """Phase B (SDK_MIGRATION_PLAN.md Section 4.2): fire-and-forget. Enqueues the
        objective and returns immediately - contrast with the pre-Phase-B behavior, still
        available at POST /chat/sync below. The "coo" reply is written later, by
        build_queue_handler()'s handler, once a queue worker process picks this row up."""

        objective, required_output = _build_objective_from_chat_body(body)

        user_msg = DashboardChatMessage(role="user", content=objective)
        session.add(user_msg)
        session.commit()

        record = enqueue_objective(
            session,
            objective=objective,
            required_output=required_output,
            submitted_by=DASHBOARD_CHAT_SUBMITTER,
        )

        return {"objective_id": record.id, "status": record.status}

    @router.post("/chat/sync")
    def chat_send_sync(
        body: dict[str, Any],
        session: Session = Depends(get_session),
        _: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        """Preserves the pre-Phase-B blocking behavior exactly (SDK_MIGRATION_PLAN.md
        Section 6: "keep /chat/sync for testing... /chat for production"). Not used by the
        dashboard UI; kept for callers that need a synchronous, deterministic reply without
        a queue worker process running."""

        objective, required_output = _build_objective_from_chat_body(body)

        user_msg = DashboardChatMessage(role="user", content=objective)
        session.add(user_msg)
        session.commit()

        result = _run_objective_and_format_reply(
            session,
            coo=coo,
            objective=objective,
            required_output=required_output,
            serialize_outcome=serialize_outcome,
        )

        coo_msg = DashboardChatMessage(
            role="coo", content=result["reply"], decision_id=result.get("decision_id")
        )
        session.add(coo_msg)
        session.commit()

        return {"reply": result["reply"], "decision_id": result.get("decision_id")}

    @router.post("/files")
    def upload_file(
        body: dict[str, Any],
        _: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        filename = body.get("filename") or ""
        content_b64 = body.get("content_base64") or ""
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)
        if not safe_name or not content_b64:
            raise HTTPException(status_code=422, detail="'filename' and 'content_base64' are required.")

        try:
            content = base64.b64decode(content_b64, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid base64 content: {exc}") from exc

        uploads_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        target = uploads_dir / f"{stamp}_{safe_name}"
        try:
            target.write_bytes(content)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Could not save file: {exc}") from exc

        return {"path": str(target)}

    def _proposal_action(session: Session, proposal_id: str, action: str) -> dict[str, Any]:
        try:
            if action == "approve":
                prop = evolution_engine.approve_change(
                    session, proposal_id, approver_identity_id="dashboard_director"
                )
            elif action == "reject":
                prop = evolution_engine.reject_change(
                    session, proposal_id, approver_identity_id="dashboard_director"
                )
            else:
                evolution_engine.implement_change(
                    session, proposal_id, implementer_identity_id="dashboard_director"
                )
                prop = session.get(ChangeProposal, proposal_id)
        except EvolutionApprovalError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"id": prop.id, "status": prop.approval_status.value}

    @router.post("/proposals/{proposal_id}/approve")
    def approve_proposal(
        proposal_id: str,
        session: Session = Depends(get_session),
        _: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        return _proposal_action(session, proposal_id, "approve")

    @router.post("/proposals/{proposal_id}/reject")
    def reject_proposal(
        proposal_id: str,
        session: Session = Depends(get_session),
        _: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        return _proposal_action(session, proposal_id, "reject")

    @router.post("/proposals/{proposal_id}/implement")
    def implement_proposal(
        proposal_id: str,
        session: Session = Depends(get_session),
        _: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        return _proposal_action(session, proposal_id, "implement")

    return router
