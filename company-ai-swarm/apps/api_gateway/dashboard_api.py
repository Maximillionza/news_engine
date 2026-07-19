"""Dashboard API: the endpoints the web dashboard (apps/web_interface) polls and posts to.

Phase 12 (dashboard, post-Phase-11 addition): a thin aggregation-and-command surface over
what already exists - no new orchestration logic, same rule as the rest of this gateway.

- GET  /activity   - one aggregated poll target (agents, departments, decisions, escalations,
                     proposals, metrics) so the UI's configurable refresh hits one endpoint.
- GET  /chat, POST /chat - the COO chat. Every user message is submitted to the unmodified
                     COOOrchestrator as an objective; the reply summarizes the outcome. The
                     endpoint returns only the 10 most recent lines (the dashboard spec's
                     performance rule); the full history stays archived in the table.
- POST /files      - saves an uploaded file (base64 JSON, avoiding a python-multipart
                     dependency) into uploads/inbox/ - the pickup location the swarm can
                     consume, referenced in the next chat message.
- POST /proposals/{id}/approve|reject|implement - the Evolution hard gate, exercised by a
                     human through the dashboard. Acts as the `dashboard_director` HUMAN
                     identity, which holds the explicit `evolution:change_proposal approve`
                     grant (EESIS sec.10, ESTAS sec.21) - the same no-bypass
                     security_service.authorize() path as everywhere else.

Agent "working" status is an honest approximation: execution is synchronous, so nothing is
ever mid-flight when polled. An agent shows as working if it was selected by a decision
created within the last ACTIVE_WINDOW_SECONDS; otherwise idle.
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

ACTIVE_WINDOW_SECONDS = 120


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
            "metrics": {
                "objectives_total": len(decisions),
                "objectives_completed": completed,
                "objectives_achieved": achieved,
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

    @router.post("/chat")
    def chat_send(
        body: dict[str, Any],
        session: Session = Depends(get_session),
        _: None = Depends(require_api_key),
    ) -> dict[str, Any]:
        message = (body.get("message") or "").strip()
        file_path = body.get("file_path")
        if not message and not file_path:
            raise HTTPException(status_code=422, detail="'message' is required.")

        objective = message or "Process the attached file."
        if file_path:
            objective = f"{objective}\nInput file saved at: {file_path}"

        user_msg = DashboardChatMessage(role="user", content=objective)
        session.add(user_msg)
        session.commit()

        try:
            outcome = coo.receive_objective(
                session, objective, required_output=body.get("required_output") or "response"
            )
            serialized = serialize_outcome(outcome)
            departments = ", ".join(serialized["departments"])
            achieved = serialized["objective_achieved"]
            reply = (
                f"Objective routed to {departments}. "
                f"{'Delivered' if achieved else 'Completed with issues'} "
                f"({len(serialized['tasks'])} task(s), decision {serialized['decision_id']})."
            )
            decision_id = serialized["decision_id"]
        except NoMatchingDepartmentError as exc:
            reply = f"No department matched that objective: {exc}"
            decision_id = None

        coo_msg = DashboardChatMessage(role="coo", content=reply, decision_id=decision_id)
        session.add(coo_msg)
        session.commit()

        return {"reply": reply, "decision_id": decision_id}

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
