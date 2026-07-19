"""Phase 2 exit-criteria test: all five EMAS memory tiers support write/read with all
required fields persisted, and Project-tier queries demonstrate no cross-project leakage.

Source: IMPLEMENTATION_PLAN.md Phase 2 test spec, built on EMAS sec.5 (five-tier hierarchy),
sec.6 (Memory Object Model), and sec.13 (Context Filtering / "no cross-project leakage").

Memory access here also exercises Phase 1's identity/permission/audit chain (ESTAS sec.16)
- every write/read below requires a granted permission, proving the phases are actually
wired together, not just sequentially built.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from identity_service.models import EntityType
from identity_service.repository import create_identity
from memory_service.models import Classification, MemoryTier, MemoryType, ValidationStatus
from memory_service.repository import get_memory, query_memory, write_memory
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


@pytest.fixture()
def research_agent(session: Session) -> str:
    """An identity with write+read permission on every memory tier, so tier-mechanics
    tests aren't also permission tests (that's Tests/security/test_mvs_007...)."""

    identity_id = "AGT-000001"
    create_identity(session, id=identity_id, entity_type=EntityType.AGENT, name="Research Agent")
    for tier in MemoryTier:
        grant_permission(session, subject=identity_id, resource=f"memory:{tier.value}", action="write")
        grant_permission(session, subject=identity_id, resource=f"memory:{tier.value}", action="read")
    return identity_id


ALL_TIER_KWARGS = {
    MemoryTier.WORKING: {},
    MemoryTier.PROJECT: {"project_id": "PRJ-A"},
    MemoryTier.DEPARTMENT: {"department_id": "DEP-research"},
    MemoryTier.ENTERPRISE: {},
    MemoryTier.HISTORICAL: {},
}


@pytest.mark.parametrize("tier", list(MemoryTier))
def test_write_and_read_at_each_tier(session: Session, research_agent: str, tier: MemoryTier) -> None:
    memory_id = f"MEM-{tier.value}-001"
    write_memory(
        session,
        identity_id=research_agent,
        id=memory_id,
        type=MemoryType.OBSERVATION,
        content=f"A test observation stored at the {tier.value} tier.",
        creator=research_agent,
        tier=tier,
        source="unit-test",
        context_domain="testing",
        confidence=0.75,
        validation_status=ValidationStatus.UNVALIDATED,
        applicable_situations=["automated test runs"],
        non_applicable_situations=["production data"],
        known_limitations=["synthetic content"],
        classification=Classification.INTERNAL,
        owner=research_agent,
        **ALL_TIER_KWARGS[tier],
    )

    retrieved = get_memory(session, identity_id=research_agent, id=memory_id)

    assert retrieved is not None
    assert retrieved.tier == tier
    # EMAS-required fields (sec.6 Memory Object Model) must all persist, not just content.
    assert retrieved.content == f"A test observation stored at the {tier.value} tier."
    assert retrieved.source == "unit-test"
    assert retrieved.creator == research_agent
    assert retrieved.context_domain == "testing"
    assert retrieved.confidence == 0.75
    assert retrieved.validation_status == ValidationStatus.UNVALIDATED
    assert retrieved.applicable_situations == ["automated test runs"]
    assert retrieved.non_applicable_situations == ["production data"]
    assert retrieved.known_limitations == ["synthetic content"]
    assert retrieved.classification == Classification.INTERNAL
    assert retrieved.owner == research_agent


def test_project_tier_requires_project_id(session: Session, research_agent: str) -> None:
    with pytest.raises(ValueError, match="project_id is required"):
        write_memory(
            session,
            identity_id=research_agent,
            id="MEM-bad-001",
            type=MemoryType.FACT,
            content="x",
            creator=research_agent,
            tier=MemoryTier.PROJECT,
        )


def test_project_tier_isolation_no_cross_project_leakage(
    session: Session, research_agent: str
) -> None:
    """EMAS sec.13/14: a memory written under Project A must never be returned when
    querying Project B's context, even though both are PROJECT-tier."""

    write_memory(
        session,
        identity_id=research_agent,
        id="MEM-project-a-001",
        type=MemoryType.LESSON,
        content="Project A learned that early stakeholder review reduces rework.",
        creator=research_agent,
        tier=MemoryTier.PROJECT,
        project_id="PRJ-A",
    )
    write_memory(
        session,
        identity_id=research_agent,
        id="MEM-project-b-001",
        type=MemoryType.LESSON,
        content="Project B learned that the vendor API rate-limits aggressively.",
        creator=research_agent,
        tier=MemoryTier.PROJECT,
        project_id="PRJ-B",
    )

    project_a_memories = query_memory(
        session, identity_id=research_agent, tier=MemoryTier.PROJECT, project_id="PRJ-A"
    )
    project_b_memories = query_memory(
        session, identity_id=research_agent, tier=MemoryTier.PROJECT, project_id="PRJ-B"
    )

    assert [m.id for m in project_a_memories] == ["MEM-project-a-001"]
    assert [m.id for m in project_b_memories] == ["MEM-project-b-001"]
    # The critical assertion: Project A's query result contains nothing from Project B.
    assert "MEM-project-b-001" not in [m.id for m in project_a_memories]
    assert "MEM-project-a-001" not in [m.id for m in project_b_memories]


def test_department_tier_isolation(session: Session, research_agent: str) -> None:
    write_memory(
        session,
        identity_id=research_agent,
        id="MEM-dept-research-001",
        type=MemoryType.PATTERN,
        content="Research department pattern.",
        creator=research_agent,
        tier=MemoryTier.DEPARTMENT,
        department_id="DEP-research",
    )
    write_memory(
        session,
        identity_id=research_agent,
        id="MEM-dept-engineering-001",
        type=MemoryType.PATTERN,
        content="Engineering department pattern.",
        creator=research_agent,
        tier=MemoryTier.DEPARTMENT,
        department_id="DEP-engineering",
    )

    research_memories = query_memory(
        session, identity_id=research_agent, tier=MemoryTier.DEPARTMENT, department_id="DEP-research"
    )

    assert [m.id for m in research_memories] == ["MEM-dept-research-001"]


def test_memory_access_without_permission_is_denied(session: Session) -> None:
    """Reuses Phase 1's authorize() - an identity with no granted memory permission must
    be denied, consistent with MVS-007 (Tests/security/test_mvs_007...)."""

    create_identity(session, id="AGT-000002", entity_type=EntityType.AGENT, name="Unpermitted Agent")

    with pytest.raises(PermissionError):
        write_memory(
            session,
            identity_id="AGT-000002",
            id="MEM-denied-001",
            type=MemoryType.FACT,
            content="Should never be written.",
            creator="AGT-000002",
            tier=MemoryTier.ENTERPRISE,
        )
