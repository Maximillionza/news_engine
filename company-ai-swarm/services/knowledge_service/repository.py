"""Knowledge entity/relationship CRUD (storage only - see models.py docstring)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from knowledge_service.models import KnowledgeEntity, KnowledgeRelationship


def create_entity(
    session: Session,
    *,
    id: str,
    object_type: str,
    name: str,
    description: str | None = None,
    attributes: dict | None = None,
    source: str | None = None,
    confidence: float | None = None,
) -> KnowledgeEntity:
    entity = KnowledgeEntity(
        id=id,
        object_type=object_type,
        name=name,
        description=description,
        attributes=attributes or {},
        source=source,
        confidence=confidence,
    )
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def get_entity(session: Session, entity_id: str) -> KnowledgeEntity | None:
    return session.get(KnowledgeEntity, entity_id)


def get_or_create_entity(
    session: Session,
    *,
    id: str,
    object_type: str,
    name: str,
    description: str | None = None,
    attributes: dict | None = None,
    source: str | None = None,
    confidence: float | None = None,
) -> KnowledgeEntity:
    """Phase 7 addition: workflow execution (workflow_engine/knowledge.py) records the same
    Agent/Capability entity repeatedly across separate workflow runs - a knowledge graph
    accumulating relationships onto a stable entity is the point, not an error, so this is
    get-or-create rather than create_entity()'s create-or-fail."""

    existing = get_entity(session, id)
    if existing is not None:
        return existing
    return create_entity(
        session,
        id=id,
        object_type=object_type,
        name=name,
        description=description,
        attributes=attributes,
        source=source,
        confidence=confidence,
    )


def create_relationship(
    session: Session,
    *,
    source_entity_id: str,
    relationship_type: str,
    target_entity_id: str,
    confidence: float | None = None,
    evidence: dict | None = None,
) -> KnowledgeRelationship:
    if get_entity(session, source_entity_id) is None:
        raise ValueError(f"Unknown source entity: {source_entity_id}")
    if get_entity(session, target_entity_id) is None:
        raise ValueError(f"Unknown target entity: {target_entity_id}")

    relationship = KnowledgeRelationship(
        source_entity_id=source_entity_id,
        relationship_type=relationship_type,
        target_entity_id=target_entity_id,
        confidence=confidence,
        evidence=evidence or {},
    )
    session.add(relationship)
    session.commit()
    session.refresh(relationship)
    return relationship


def get_relationships_for_entity(
    session: Session, entity_id: str
) -> list[KnowledgeRelationship]:
    """Relationships where the entity is either source or target."""

    return (
        session.query(KnowledgeRelationship)
        .filter(
            (KnowledgeRelationship.source_entity_id == entity_id)
            | (KnowledgeRelationship.target_entity_id == entity_id)
        )
        .all()
    )
