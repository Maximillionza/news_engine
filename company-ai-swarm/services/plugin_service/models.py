"""Plugin ORM models.

Source: Specifications/4 - future-expansion/Enterprise Plugin Architecture Specification
(EPAS).md sec.5 (four Plugin Types), sec.7 (Registration schema: id, name, version, type,
owner, purpose, dependencies, permissions, security_level, status).
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class PluginType(str, enum.Enum):
    """EPAS sec.5.1-5.4."""

    TOOL = "tool"
    CAPABILITY = "capability"
    MODEL = "model"
    INTEGRATION = "integration"


class PluginStatus(str, enum.Enum):
    """EPAS sec.6 Plugin Lifecycle: Design -> Register -> Validate -> Test -> Approve ->
    Deploy -> Monitor -> Update/Remove. Test (EPAS sec.8's Capability Test + Integration
    Test) has no status of its own here - see registry.py's module docstring for why those
    two gates aren't implemented."""

    REGISTERED = "registered"
    VALIDATED = "validated"
    APPROVED = "approved"
    ACTIVE = "active"
    DISABLED = "disabled"
    REJECTED = "rejected"


class Plugin(Base):
    __tablename__ = "plugins"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False, default="1.0")
    type: Mapped[PluginType] = mapped_column(Enum(PluginType), nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ESTAS sec.13 Classification levels, reused rather than inventing a second security
    # vocabulary - see shared/contracts.py's Classification enum.
    security_level: Mapped[str] = mapped_column(String, nullable=False, default="internal")
    status: Mapped[PluginStatus] = mapped_column(
        Enum(PluginStatus), nullable=False, default=PluginStatus.REGISTERED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class PluginAccessGrant(Base):
    """EPAS sec.10: agents do not automatically receive plugin access."""

    __tablename__ = "plugin_access_grants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plugin_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
