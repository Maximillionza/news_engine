"""Memory CRUD, wired through security_service.authorize() per ESTAS sec.16 ("Memory SHALL
enforce: Access controls... Agents SHALL NOT: Browse unrestricted enterprise memory...").

This is why IMPLEMENTATION_PLAN.md Phase 2 depends on Phase 1: every memory read/write here
requires an identity that has been explicitly granted permission on that memory tier -
there is no memory access path that bypasses Phase 1's identity/permission/audit chain.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from memory_service.models import (
    Classification,
    MemoryObject,
    MemoryTier,
    MemoryType,
    ValidationStatus,
)
from security_service.permissions import authorize


def _resource_name(tier: MemoryTier) -> str:
    return f"memory:{tier.value}"


def write_memory(
    session: Session,
    *,
    identity_id: str,
    id: str,
    type: MemoryType,
    content: str,
    creator: str,
    tier: MemoryTier,
    source: str | None = None,
    project_id: str | None = None,
    department_id: str | None = None,
    context_domain: str | None = None,
    confidence: float | None = None,
    validation_status: ValidationStatus = ValidationStatus.UNVALIDATED,
    applicable_situations: list | None = None,
    non_applicable_situations: list | None = None,
    known_limitations: list | None = None,
    expiration: datetime | None = None,
    classification: Classification = Classification.INTERNAL,
    owner: str | None = None,
) -> MemoryObject:
    result = authorize(
        session, identity_id=identity_id, resource=_resource_name(tier), action="write"
    )
    if not result.allowed:
        raise PermissionError(
            f"{identity_id} may not write to {_resource_name(tier)}: {result.reason}"
        )

    if tier == MemoryTier.PROJECT and project_id is None:
        raise ValueError("project_id is required for PROJECT-tier memory")
    if tier == MemoryTier.DEPARTMENT and department_id is None:
        raise ValueError("department_id is required for DEPARTMENT-tier memory")

    memory = MemoryObject(
        id=id,
        type=type,
        content=content,
        source=source,
        creator=creator,
        tier=tier,
        project_id=project_id,
        department_id=department_id,
        context_domain=context_domain,
        confidence=confidence,
        validation_status=validation_status,
        applicable_situations=applicable_situations,
        non_applicable_situations=non_applicable_situations,
        known_limitations=known_limitations,
        expiration=expiration,
        classification=classification,
        owner=owner,
    )
    session.add(memory)
    session.commit()
    session.refresh(memory)
    return memory


def get_memory(session: Session, *, identity_id: str, id: str) -> MemoryObject | None:
    memory = session.get(MemoryObject, id)
    if memory is None:
        return None

    result = authorize(
        session, identity_id=identity_id, resource=_resource_name(memory.tier), action="read"
    )
    if not result.allowed:
        raise PermissionError(
            f"{identity_id} may not read from {_resource_name(memory.tier)}: {result.reason}"
        )
    return memory


def query_memory(
    session: Session,
    *,
    identity_id: str,
    tier: MemoryTier,
    project_id: str | None = None,
    department_id: str | None = None,
) -> list[MemoryObject]:
    """Query memory within a tier, scoped by project/department where applicable.

    This is the operation EMAS sec.13 "Context Filtering" and sec.14 "Memory Contamination
    Prevention" describe: a query for Project A's context must never return Project B's
    memory, even though both are PROJECT-tier.
    """

    result = authorize(
        session, identity_id=identity_id, resource=_resource_name(tier), action="read"
    )
    if not result.allowed:
        raise PermissionError(
            f"{identity_id} may not read from {_resource_name(tier)}: {result.reason}"
        )

    query = session.query(MemoryObject).filter(MemoryObject.tier == tier)
    if tier == MemoryTier.PROJECT:
        query = query.filter(MemoryObject.project_id == project_id)
    elif tier == MemoryTier.DEPARTMENT:
        query = query.filter(MemoryObject.department_id == department_id)
    return query.all()
