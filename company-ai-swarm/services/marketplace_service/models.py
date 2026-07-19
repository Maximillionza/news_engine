"""Marketplace Asset ORM model.

Source: Specifications/4 - future-expansion/Enterprise Marketplace Architecture
Specification (EMAS).md sec.5 (four asset types: Agent/Workflow/Plugin/Capability
Packages), sec.6 (Asset Schema: id, name, type, version, description, owner, capabilities,
requirements, permissions, dependencies, evaluation, status).
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class AssetType(str, enum.Enum):
    AGENT_PACKAGE = "agent_package"
    WORKFLOW_PACKAGE = "workflow_package"
    PLUGIN_PACKAGE = "plugin_package"
    CAPABILITY_PACKAGE = "capability_package"


class AssetStatus(str, enum.Enum):
    """EMAS sec.7 Marketplace Lifecycle: Created -> Submitted -> Validated -> Published ->
    Used -> Evaluated -> Updated. "Used"/"Evaluated" are not distinct statuses here - they
    describe ongoing activity on a Published asset, tracked via evaluation_count/
    evaluation_score below rather than a status transition (an asset stays PUBLISHED while
    being used and evaluated; see registry.py's record_evaluation())."""

    CREATED = "created"
    SUBMITTED = "submitted"
    VALIDATED = "validated"
    PUBLISHED = "published"
    REJECTED = "rejected"
    RETIRED = "retired"


class MarketplaceAsset(Base):
    __tablename__ = "marketplace_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String, nullable=False, default="1.0")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner: Mapped[str] = mapped_column(String, nullable=False)
    capabilities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    requirements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    permissions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    dependencies: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus), nullable=False, default=AssetStatus.CREATED
    )
    evaluation_count: Mapped[int] = mapped_column(default=0)
    evaluation_score_total: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
