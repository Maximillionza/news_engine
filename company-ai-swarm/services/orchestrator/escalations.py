"""Escalation Record persistence (ESTAS sec.10 Risk Assessment output).

See orchestrator/escalation.py for the four-condition policy and orchestrator/models.py's
EscalationRecord for the schema. Mirrors decisions.py's shape.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from orchestrator.escalation import EscalationCondition
from orchestrator.models import EscalationRecord


def write_escalation(
    session: Session,
    *,
    condition: EscalationCondition,
    reasoning: str,
    decision_id: str | None = None,
    is_technical_failure: bool = False,
) -> EscalationRecord:
    record = EscalationRecord(
        id=f"ESC-{uuid4().hex[:8]}",
        decision_id=decision_id,
        condition=condition.value,
        reasoning=reasoning,
        is_technical_failure=is_technical_failure,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_escalation(session: Session, escalation_id: str) -> EscalationRecord | None:
    return session.get(EscalationRecord, escalation_id)


def list_escalations_for_decision(session: Session, decision_id: str) -> list[EscalationRecord]:
    """Phase 9 addition: orchestrator/controller.py's Learn step uses this as the sole
    criticality signal - a workflow is "critical" iff it produced at least one Escalation
    Record, reusing Phase 8's policy rather than a second risk classification."""

    return (
        session.query(EscalationRecord)
        .filter(EscalationRecord.decision_id == decision_id)
        .all()
    )


def list_pending_escalations(session: Session) -> list[EscalationRecord]:
    return (
        session.query(EscalationRecord)
        .filter(EscalationRecord.resolved.is_(False))
        .order_by(EscalationRecord.created_at)
        .all()
    )


def resolve_escalation(
    session: Session, escalation_id: str, *, resolution: str
) -> EscalationRecord | None:
    record = session.get(EscalationRecord, escalation_id)
    if record is not None:
        record.resolved = True
        record.resolution = resolution
        session.commit()
        session.refresh(record)
    return record
