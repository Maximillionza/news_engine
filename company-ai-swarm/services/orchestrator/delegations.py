"""Department Delegation Record persistence.

See orchestrator/models.py's DepartmentDelegationRecord for the schema and its rationale.
Mirrors spawns.py's shape - written once per inter-department delegation
(orchestrator/head.py's resolve_verdict_execution()), read later for audit and for future
gap-detection heuristics (Phase 21, IMPLEMENTATION_PLAN.md, 2026-07-25).
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from orchestrator.models import DepartmentDelegationRecord


def write_delegation(
    session: Session,
    *,
    decision_id: str,
    requesting_department_id: str,
    target_department_id: str,
    reasoning: str,
    chain_depth: int,
) -> DepartmentDelegationRecord:
    record = DepartmentDelegationRecord(
        id=f"DELEG-{uuid4().hex[:8]}",
        decision_id=decision_id,
        requesting_department_id=requesting_department_id,
        target_department_id=target_department_id,
        reasoning=reasoning,
        chain_depth=chain_depth,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def list_delegations_for_department(
    session: Session, department_id: str
) -> list[DepartmentDelegationRecord]:
    return (
        session.query(DepartmentDelegationRecord)
        .filter(DepartmentDelegationRecord.requesting_department_id == department_id)
        .order_by(DepartmentDelegationRecord.created_at)
        .all()
    )
