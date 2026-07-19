"""Digital Twin state synchronization.

Source: ESDTS sec.4 (Digital Twin Architecture), sec.31 (MVP Requirements). See
models.py's docstring for what "synchronization" means at this phase's scope.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from digital_twin_service.models import DigitalTwinSnapshot
from orchestrator.decisions import list_decisions
from orchestrator.department_registry import DepartmentRegistry


def capture_snapshot(
    session: Session,
    *,
    agent_registry: AgentRegistry,
    department_registry: DepartmentRegistry,
    recent_decision_limit: int = 20,
) -> DigitalTwinSnapshot:
    agents = [
        {
            "id": a.identity.id,
            "name": a.identity.name,
            "department": a.department.name,
            "capabilities": a.capabilities,
        }
        for a in agent_registry.all()
    ]
    departments = [
        {"id": d.id, "name": d.name, "capabilities": d.capabilities, "agents": d.agents}
        for d in department_registry.all()
    ]
    decisions = list_decisions(session)[-recent_decision_limit:]
    recent_decisions = [
        {"id": d.id, "objective": d.objective, "chosen_action": d.chosen_action, "outcome": d.outcome}
        for d in decisions
    ]

    snapshot = DigitalTwinSnapshot(
        id=f"TWIN-{uuid4().hex[:8]}",
        agents=agents,
        departments=departments,
        recent_decisions=recent_decisions,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot
