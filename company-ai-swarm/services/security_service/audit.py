"""Audit log sink.

Every identity/permission action - allowed or denied - produces an audit record.
Source: ESTAS sec.19 ("Every important action records..."), sec.24.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from security_service.models import AuditRecord


def write_audit_record(
    session: Session,
    *,
    actor: str,
    action: str,
    decision: str,
    resource: str | None = None,
    reason: str | None = None,
    evidence: dict | None = None,
) -> AuditRecord:
    record = AuditRecord(
        actor=actor,
        action=action,
        decision=decision,
        resource=resource,
        reason=reason,
        evidence=evidence or {},
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_audit_trail(session: Session, actor: str) -> list[AuditRecord]:
    return (
        session.query(AuditRecord)
        .filter(AuditRecord.actor == actor)
        .order_by(AuditRecord.timestamp)
        .all()
    )
