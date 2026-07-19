"""Permission and audit ORM models.

Source: Specifications/1 - enterprise-architecture/Enterprise Security & Trust Architecture
Specification (ESTAS).md sec.9 (Permission Schema) and sec.24 (Audit Architecture).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class Permission(Base):
    """ESTAS sec.9 Permission Schema: subject + resource + action + scope + conditions."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String, nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    scope: Mapped[str | None] = mapped_column(String, nullable=True)
    conditions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AuditRecord(Base):
    """ESTAS sec.24 Audit Architecture schema."""

    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resource: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)  # "allowed" | "denied"
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
