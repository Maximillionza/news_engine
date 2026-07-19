"""Permission evaluation engine.

Implements a Phase 1 subset of ESTAS sec.10 Agent Action Validation:

    Agent Request -> Identity Check -> Permission Check -> Approve/Reject -> (audit always)

Risk Assessment (the fourth step in ESTAS sec.10) is a COO-level concern (COOS sec.10) and
is deliberately out of scope until the COO exists (IMPLEMENTATION_PLAN.md Phase 5) - Phase 1
proves identity + permission + audit work correctly in isolation, per the plan's own
"independently testable" requirement.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from identity_service.repository import get_identity
from security_service.audit import write_audit_record
from security_service.models import Permission


@dataclass(frozen=True)
class AuthorizationResult:
    allowed: bool
    reason: str


def grant_permission(
    session: Session,
    *,
    subject: str,
    resource: str,
    action: str,
    scope: str | None = None,
    approval_required: bool = False,
) -> Permission:
    permission = Permission(
        subject=subject,
        resource=resource,
        action=action,
        scope=scope,
        approval_required=approval_required,
    )
    session.add(permission)
    session.commit()
    session.refresh(permission)
    return permission


def _find_matching_permission(
    session: Session, *, subject: str, resource: str, action: str
) -> Permission | None:
    return (
        session.query(Permission)
        .filter(
            Permission.subject == subject,
            Permission.resource == resource,
            Permission.action == action,
        )
        .first()
    )


def authorize(
    session: Session, *, identity_id: str, resource: str, action: str
) -> AuthorizationResult:
    """Evaluate whether `identity_id` may perform `action` on `resource`.

    Every call - regardless of outcome - writes an audit record (ESTAS sec.19: "Every
    important action records...").
    """

    # Step 1: Identity Check
    identity = get_identity(session, identity_id)
    if identity is None:
        write_audit_record(
            session,
            actor=identity_id,
            action=f"{action}:{resource}",
            decision="denied",
            resource=resource,
            reason="identity not found",
        )
        return AuthorizationResult(allowed=False, reason="identity not found")

    # Step 2: Permission Check
    permission = _find_matching_permission(
        session, subject=identity_id, resource=resource, action=action
    )
    if permission is None:
        write_audit_record(
            session,
            actor=identity_id,
            action=f"{action}:{resource}",
            decision="denied",
            resource=resource,
            reason="no matching permission",
        )
        return AuthorizationResult(allowed=False, reason="no matching permission")

    if permission.approval_required:
        write_audit_record(
            session,
            actor=identity_id,
            action=f"{action}:{resource}",
            decision="denied",
            resource=resource,
            reason="approval required and not granted",
        )
        return AuthorizationResult(allowed=False, reason="approval required and not granted")

    # Step 3: Allow
    write_audit_record(
        session,
        actor=identity_id,
        action=f"{action}:{resource}",
        decision="allowed",
        resource=resource,
        reason="permission matched",
    )
    return AuthorizationResult(allowed=True, reason="permission matched")
