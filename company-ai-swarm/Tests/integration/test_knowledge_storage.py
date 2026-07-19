"""Phase 2: knowledge entity/relationship storage (EKGS Object Model, UOL relationship
types). Not wired to a graph query engine yet - that's Phase 7 - this only proves the
storage layer round-trips correctly.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from knowledge_service.repository import (
    create_entity,
    create_relationship,
    get_entity,
    get_relationships_for_entity,
)
from shared.db import Base, make_engine, make_session_factory


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def test_create_and_retrieve_entity(session: Session) -> None:
    create_entity(
        session,
        id="AGT-000001",
        object_type="Agent",
        name="Research Agent",
        description="Performs research tasks.",
        source="agents/active/research_agent/agent.yaml",
        confidence=1.0,
    )

    entity = get_entity(session, "AGT-000001")

    assert entity is not None
    assert entity.name == "Research Agent"
    assert entity.object_type == "Agent"


def test_relationship_between_two_entities(session: Session) -> None:
    create_entity(session, id="AGT-000001", object_type="Agent", name="Research Agent")
    create_entity(session, id="CAP-market_research", object_type="Capability", name="Market Research")

    create_relationship(
        session,
        source_entity_id="AGT-000001",
        relationship_type="USES",
        target_entity_id="CAP-market_research",
        confidence=1.0,
        evidence={"source": "agent.yaml capabilities list"},
    )

    relationships = get_relationships_for_entity(session, "AGT-000001")

    assert len(relationships) == 1
    assert relationships[0].relationship_type == "USES"
    assert relationships[0].target_entity_id == "CAP-market_research"


def test_relationship_requires_known_entities(session: Session) -> None:
    create_entity(session, id="AGT-000001", object_type="Agent", name="Research Agent")

    with pytest.raises(ValueError, match="Unknown target entity"):
        create_relationship(
            session,
            source_entity_id="AGT-000001",
            relationship_type="USES",
            target_entity_id="CAP-does-not-exist",
        )


def test_relationships_queryable_from_either_side(session: Session) -> None:
    create_entity(session, id="AGT-000001", object_type="Agent", name="Research Agent")
    create_entity(session, id="DEP-research", object_type="Department", name="Research Department")

    create_relationship(
        session,
        source_entity_id="AGT-000001",
        relationship_type="REPORTS_TO",
        target_entity_id="DEP-research",
    )

    from_source = get_relationships_for_entity(session, "AGT-000001")
    from_target = get_relationships_for_entity(session, "DEP-research")

    assert len(from_source) == 1
    assert len(from_target) == 1
    assert from_source[0].id == from_target[0].id
