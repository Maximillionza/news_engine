"""Identity CRUD operations (create + read, per IMPLEMENTATION_PLAN.md Phase 1 scope)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from identity_service.models import EntityType, Identity, LifecycleState, TrustLevel


def create_identity(
    session: Session,
    *,
    id: str,
    entity_type: EntityType,
    name: str,
    owner: str | None = None,
    department: str | None = None,
    role: str | None = None,
    trust_level: TrustLevel = TrustLevel.RESTRICTED,
) -> Identity:
    identity = Identity(
        id=id,
        entity_type=entity_type,
        name=name,
        owner=owner,
        department=department,
        role=role,
        trust_level=trust_level,
        lifecycle_state=LifecycleState.ACTIVE,
    )
    session.add(identity)
    session.commit()
    session.refresh(identity)
    return identity


def get_identity(session: Session, identity_id: str) -> Identity | None:
    return session.get(Identity, identity_id)
