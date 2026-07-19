"""Knowledge entity and relationship ORM models.

Source: Specifications/1 - enterprise-architecture/Enterprise Knowledge Graph Specification
(EKGS).md sec.5 (Object Model), and Universal Ontology (UOL) sec.6 (relationship types).

Per IMPLEMENTATION_PLAN.md Phase 2 scope: this is storage only, not wired to a graph query
engine yet (that's Phase 7, "Knowledge Graph + Full Roster"). Relationships are stored as
explicit rows so a future graph engine can be layered on top without a schema migration.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class KnowledgeEntity(Base):
    __tablename__ = "knowledge_entities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    object_type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_status: Mapped[str] = mapped_column(String, nullable=False, default="unvalidated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class KnowledgeRelationship(Base):
    """Directional typed edge. `relationship_type` should be one of UOL sec.6's canonical
    types (OWNS, CONTAINS, REPORTS_TO, DEPENDS_ON, USES, GENERATES, IMPLEMENTS, GOVERNS,
    VALIDATES, APPROVES, EXECUTES, CREATES, REQUIRES, PROVIDES, LEARNS_FROM, SUPERSEDES,
    REFERENCES) but is not DB-enforced to that list yet, since UOL sec.6 explicitly leaves
    it extensible ("Supported relationship types include...")."""

    __tablename__ = "knowledge_relationships"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_entity_id: Mapped[str] = mapped_column(
        String, ForeignKey("knowledge_entities.id"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String, nullable=False)
    target_entity_id: Mapped[str] = mapped_column(
        String, ForeignKey("knowledge_entities.id"), nullable=False, index=True
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
