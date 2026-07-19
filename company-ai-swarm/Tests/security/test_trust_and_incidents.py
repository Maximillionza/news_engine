"""Phase 8: Security monitoring completion (ESTAS sec.26 Trust Scoring, sec.28 Incident
Workflow).
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from identity_service.models import EntityType, TrustLevel
from identity_service.repository import create_identity
from security_service.audit import write_audit_record
from security_service.incidents import (
    IncidentStatus,
    InvalidStageTransition,
    advance_incident,
    get_incident,
    open_incident,
)
from security_service.trust import compute_trust_score, update_trust_level
from shared.db import Base, make_engine, make_session_factory


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


class TestTrustScoringESTAS26:
    def test_no_history_defaults_to_restricted_not_a_guess(self, session: Session) -> None:
        result = compute_trust_score(session, "brand_new_agent")

        assert result.score is None
        assert result.level == TrustLevel.RESTRICTED
        assert result.total_actions == 0

    def test_clean_history_reaches_trusted(self, session: Session) -> None:
        for _ in range(10):
            write_audit_record(session, actor="reliable_agent", action="execute", decision="allowed")

        result = compute_trust_score(session, "reliable_agent")

        assert result.score == 1.0
        assert result.level == TrustLevel.TRUSTED

    def test_high_denial_rate_stays_restricted(self, session: Session) -> None:
        for _ in range(3):
            write_audit_record(session, actor="risky_agent", action="execute", decision="allowed")
        for _ in range(7):
            write_audit_record(session, actor="risky_agent", action="execute", decision="denied")

        result = compute_trust_score(session, "risky_agent")

        assert result.score == pytest.approx(0.3)
        assert result.level == TrustLevel.RESTRICTED

    def test_moderate_denial_rate_lands_operational(self, session: Session) -> None:
        for _ in range(7):
            write_audit_record(session, actor="ok_agent", action="execute", decision="allowed")
        for _ in range(3):
            write_audit_record(session, actor="ok_agent", action="execute", decision="denied")

        result = compute_trust_score(session, "ok_agent")

        assert result.score == pytest.approx(0.7)
        assert result.level == TrustLevel.OPERATIONAL

    def test_update_trust_level_persists_onto_identity(self, session: Session) -> None:
        create_identity(session, id="agent_x", entity_type=EntityType.AGENT, name="Agent X")
        for _ in range(10):
            write_audit_record(session, actor="agent_x", action="execute", decision="allowed")

        identity = update_trust_level(session, "agent_x")

        assert identity is not None
        assert identity.trust_level == TrustLevel.TRUSTED

    def test_update_trust_level_for_unknown_identity_returns_none(self, session: Session) -> None:
        assert update_trust_level(session, "does_not_exist") is None


class TestIncidentWorkflowESTAS28:
    def test_incident_opens_at_detection(self, session: Session) -> None:
        incident = open_incident(session, description="Suspicious repeated auth denial", actor="agent_x")

        assert incident.status == IncidentStatus.DETECTION.value

    def test_incident_advances_through_all_seven_stages_in_order(self, session: Session) -> None:
        incident = open_incident(session, description="Prompt injection attempt detected")

        expected_order = [
            IncidentStatus.CLASSIFICATION,
            IncidentStatus.CONTAINMENT,
            IncidentStatus.INVESTIGATION,
            IncidentStatus.REMEDIATION,
            IncidentStatus.REVIEW,
            IncidentStatus.KNOWLEDGE_UPDATE,
        ]
        for expected_stage in expected_order:
            incident = advance_incident(session, incident.id, note=f"moving to {expected_stage.value}")
            assert incident.status == expected_stage.value

        assert incident.status == IncidentStatus.KNOWLEDGE_UPDATE.value
        assert len(incident.notes) == 6

    def test_cannot_advance_past_the_final_stage(self, session: Session) -> None:
        incident = open_incident(session, description="test")
        for _ in range(6):
            incident = advance_incident(session, incident.id)

        with pytest.raises(InvalidStageTransition):
            advance_incident(session, incident.id)

    def test_advancing_unknown_incident_raises(self, session: Session) -> None:
        with pytest.raises(ValueError):
            advance_incident(session, "INC-doesnotexist")

    def test_get_incident_returns_persisted_state(self, session: Session) -> None:
        incident = open_incident(session, description="test", evidence={"source_ip": "10.0.0.1"})
        advance_incident(session, incident.id)

        fetched = get_incident(session, incident.id)

        assert fetched is not None
        assert fetched.status == IncidentStatus.CLASSIFICATION.value
        assert fetched.evidence == {"source_ip": "10.0.0.1"}
