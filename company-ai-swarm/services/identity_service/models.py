"""Identity ORM model.

Source: Specifications/1 - enterprise-architecture/Enterprise Security & Trust Architecture
Specification (ESTAS).md sec.5-7 (Identity Object).

Note: ESTAS sec.6 lists "Audit History" as an Identity Object field. It is intentionally not
stored here as a column - audit records live in security_service.models.AuditRecord, keyed
by actor, so history is queried rather than duplicated inline (single source of truth).
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class EntityType(str, enum.Enum):
    """ESTAS sec.5 Identity subjects."""

    HUMAN = "human"
    AGENT = "agent"
    SERVICE = "service"
    APPLICATION = "application"


class TrustLevel(str, enum.Enum):
    """ESTAS sec.7 Trust Levels."""

    RESTRICTED = "restricted"
    OPERATIONAL = "operational"
    TRUSTED = "trusted"
    ENTERPRISE_AUTHORITY = "enterprise_authority"


class LifecycleState(str, enum.Enum):
    """AOSS sec.19 Agent Lifecycle, generalized to any identity."""

    CREATED = "created"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class Identity(Base):
    __tablename__ = "identities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
    department: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    trust_level: Mapped[TrustLevel] = mapped_column(
        Enum(TrustLevel), nullable=False, default=TrustLevel.RESTRICTED
    )
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        Enum(LifecycleState), nullable=False, default=LifecycleState.CREATED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
