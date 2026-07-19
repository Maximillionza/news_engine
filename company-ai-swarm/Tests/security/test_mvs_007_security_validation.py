"""Phase 1 exit-criteria test: MVS Test Category 007 (Security Validation), run in isolation
against identity_service + security_service alone. No agents exist yet.

Source: Specifications/3 - execution-framework/MVP Validation Specification (MVS).md sec.11:

    Attempt: Unauthorised access. Permission escalation. Restricted data access.
    Pass Criteria: Access denied correctly. Actions logged. Security events generated.

IMPLEMENTATION_PLAN.md Phase 1 exit criteria restate this as three concrete cases:
    1. No identity -> denied, logged.
    2. Insufficient permission -> denied, logged.
    3. Correct permission -> allowed, logged.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from identity_service.models import EntityType, TrustLevel
from identity_service.repository import create_identity
from security_service.audit import get_audit_trail
from security_service.permissions import authorize, grant_permission
from shared.db import Base, make_engine, make_session_factory


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def test_case_1_no_identity_is_denied_and_logged(session: Session) -> None:
    result = authorize(
        session, identity_id="AGT-DOES-NOT-EXIST", resource="research_data", action="read"
    )

    assert result.allowed is False
    assert result.reason == "identity not found"

    trail = get_audit_trail(session, "AGT-DOES-NOT-EXIST")
    assert len(trail) == 1
    assert trail[0].decision == "denied"
    assert trail[0].actor == "AGT-DOES-NOT-EXIST"


def test_case_2_insufficient_permission_is_denied_and_logged(session: Session) -> None:
    create_identity(
        session,
        id="AGT-000001",
        entity_type=EntityType.AGENT,
        name="Research Agent",
        department="research",
        role="research_agent",
        trust_level=TrustLevel.OPERATIONAL,
    )
    # Identity exists, but no permission has been granted for this resource/action.

    result = authorize(
        session, identity_id="AGT-000001", resource="production_customer_data", action="write"
    )

    assert result.allowed is False
    assert result.reason == "no matching permission"

    trail = get_audit_trail(session, "AGT-000001")
    assert len(trail) == 1
    assert trail[0].decision == "denied"
    assert trail[0].resource == "production_customer_data"


def test_case_3_correct_permission_is_allowed_and_logged(session: Session) -> None:
    create_identity(
        session,
        id="AGT-000001",
        entity_type=EntityType.AGENT,
        name="Research Agent",
        department="research",
        role="research_agent",
        trust_level=TrustLevel.OPERATIONAL,
    )
    grant_permission(
        session, subject="AGT-000001", resource="research_data", action="read"
    )

    result = authorize(session, identity_id="AGT-000001", resource="research_data", action="read")

    assert result.allowed is True
    assert result.reason == "permission matched"

    trail = get_audit_trail(session, "AGT-000001")
    assert len(trail) == 1
    assert trail[0].decision == "allowed"


def test_permission_requiring_approval_is_denied_until_granted(session: Session) -> None:
    """ESTAS sec.9: permissions may carry `approval_required`. Escalation of an
    approval-gated permission must still be denied even though a Permission row exists -
    this is the "permission escalation" attempt named in MVS sec.11."""

    create_identity(
        session,
        id="AGT-000002",
        entity_type=EntityType.AGENT,
        name="Engineering Agent",
        department="engineering",
        role="engineering_agent",
    )
    grant_permission(
        session,
        subject="AGT-000002",
        resource="production_deployment",
        action="execute",
        approval_required=True,
    )

    result = authorize(
        session, identity_id="AGT-000002", resource="production_deployment", action="execute"
    )

    assert result.allowed is False
    assert result.reason == "approval required and not granted"

    trail = get_audit_trail(session, "AGT-000002")
    assert trail[-1].decision == "denied"


def test_every_attempt_regardless_of_outcome_produces_exactly_one_audit_record(
    session: Session,
) -> None:
    """MVS sec.11 pass criteria: 'Actions logged' - for every attempt, not just denials."""

    create_identity(
        session, id="AGT-000003", entity_type=EntityType.AGENT, name="Compliance Agent"
    )
    grant_permission(session, subject="AGT-000003", resource="policy_repository", action="read")

    authorize(session, identity_id="AGT-000003", resource="policy_repository", action="read")
    authorize(session, identity_id="AGT-000003", resource="policy_repository", action="write")
    authorize(session, identity_id="AGT-999999", resource="policy_repository", action="read")

    trail = get_audit_trail(session, "AGT-000003")
    assert len(trail) == 2
    assert [r.decision for r in trail] == ["allowed", "denied"]
