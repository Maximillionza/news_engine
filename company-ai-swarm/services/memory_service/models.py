"""Memory Object ORM model.

Source: Specifications/1 - enterprise-architecture/Enterprise Memory Architecture
Specification (EMAS).md sec.5-6, and memory/schemas/memory_object_template.yaml.

Reconciliation note: the template this model implements had an internal naming collision -
"domain" was used both for the memory tier (Working/Project/Department/Enterprise/
Historical) and for the context's subject-matter domain (e.g. "security"). Fixed here:
`tier` is the EMAS tier; `context_domain` is the subject-matter field. Same drift-correction
discipline applied throughout the Specifications/ reconciliation.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class MemoryTier(str, enum.Enum):
    """EMAS sec.5 canonical five-tier hierarchy."""

    WORKING = "working"
    PROJECT = "project"
    DEPARTMENT = "department"
    ENTERPRISE = "enterprise"
    HISTORICAL = "historical"


class MemoryType(str, enum.Enum):
    """EMAS sec.7 Memory Types (epistemic classification, orthogonal to tier)."""

    FACT = "fact"
    OBSERVATION = "observation"
    FINDING = "finding"
    LESSON = "lesson"
    PATTERN = "pattern"
    PRINCIPLE = "principle"


class ValidationStatus(str, enum.Enum):
    UNVALIDATED = "unvalidated"
    REVIEWED = "reviewed"
    VALIDATED = "validated"
    DEPRECATED = "deprecated"


class Classification(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class MemoryObject(Base):
    __tablename__ = "memory_objects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[MemoryType] = mapped_column(Enum(MemoryType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    creator: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    tier: Mapped[MemoryTier] = mapped_column(Enum(MemoryTier), nullable=False, index=True)

    # Tier-scoping fields. Populated according to `tier`: project_id for PROJECT-tier
    # memories, department_id for DEPARTMENT-tier. Both null for WORKING/ENTERPRISE/HISTORICAL.
    project_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    department_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    context_domain: Mapped[str | None] = mapped_column(String, nullable=True)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus), nullable=False, default=ValidationStatus.UNVALIDATED
    )

    applicable_situations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    non_applicable_situations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    known_limitations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    expiration: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    relationships: Mapped[list | None] = mapped_column(JSON, nullable=True)

    classification: Mapped[Classification] = mapped_column(
        Enum(Classification), nullable=False, default=Classification.INTERNAL
    )
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
