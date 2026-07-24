"""Specialist Spawn Record persistence.

See orchestrator/models.py's SpecialistSpawnRecord for the schema and its rationale. Mirrors
escalations.py's shape - written once per specialist spawn (orchestrator/head.py's
resolve_verdict_execution()), read later by evolution_service/detection.py's Phase 17
promotion heuristic to decide whether a department has needed a specialist repeatedly enough
to justify a dedicated agent.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from orchestrator.models import SpecialistSpawnRecord


def write_spawn(
    session: Session,
    *,
    decision_id: str,
    department_id: str,
    head_agent_id: str,
    reasoning: str,
) -> SpecialistSpawnRecord:
    record = SpecialistSpawnRecord(
        id=f"SPAWN-{uuid4().hex[:8]}",
        decision_id=decision_id,
        department_id=department_id,
        head_agent_id=head_agent_id,
        reasoning=reasoning,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def list_spawns_for_department(session: Session, department_id: str) -> list[SpecialistSpawnRecord]:
    return (
        session.query(SpecialistSpawnRecord)
        .filter(SpecialistSpawnRecord.department_id == department_id)
        .order_by(SpecialistSpawnRecord.created_at)
        .all()
    )
