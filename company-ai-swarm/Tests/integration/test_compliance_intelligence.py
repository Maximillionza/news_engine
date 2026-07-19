"""Phase 8 exit-criteria test (part 1 of 3): the Compliance Intelligence Engine.

Source: IMPLEMENTATION_PLAN.md Phase 8 test spec item 1 / MVS Test Category 008:
    Introduce new policy requirement -> Impact Analysis -> Workflow Review -> Control
    Recommendation. Pass criteria: Requirement identified, Impact assessed, Evidence
    generated.

Also covers ECRIS sec.8's Applicability Assessment (Business Activity + Location + Data Type
+ Industry + Entity Type + Risk Profile -> Regulatory Applicability).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from compliance_service.applicability import ApplicabilityFactors, assess_applicability
from compliance_service.policy_impact import PolicyRequirement, analyze_policy_impact
from orchestrator.department_registry import DepartmentRegistry
from shared.db import Base, make_engine, make_session_factory

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


@pytest.fixture()
def department_registry() -> DepartmentRegistry:
    registry = DepartmentRegistry(REPO_ROOT / "departments")
    registry.load_all()
    return registry


class TestApplicabilityAssessmentECRIS8:
    def test_popia_applies_to_south_african_personal_information(self, session: Session) -> None:
        record = assess_applicability(
            session,
            regulation="POPIA",
            factors=ApplicabilityFactors(
                business_activity="Internal employee analytics",
                location="south_africa",
                data_type="personal_information",
                industry="technology",
                entity_type="private_company",
                risk_profile="moderate",
            ),
        )

        assert record.applicable is True
        assert "POPIA" in record.reasoning

    def test_popia_does_not_apply_outside_south_africa(self, session: Session) -> None:
        record = assess_applicability(
            session,
            regulation="POPIA",
            factors=ApplicabilityFactors(
                business_activity="Internal employee analytics",
                location="united_states",
                data_type="personal_information",
                industry="technology",
                entity_type="private_company",
                risk_profile="moderate",
            ),
        )

        assert record.applicable is False

    def test_unrecognized_regulation_is_unknown_not_false(self, session: Session) -> None:
        """A compliance engine must never silently default an unrecognized regulation to
        not-applicable - see applicability.py's module docstring."""

        record = assess_applicability(
            session,
            regulation="GDPR",
            factors=ApplicabilityFactors(
                business_activity="x", location="x", data_type="x", industry="x",
                entity_type="x", risk_profile="x",
            ),
        )

        assert record.applicable is None
        assert "UNKNOWN" in record.reasoning


class TestPolicyImpactMVS008:
    def test_requirement_identified_impact_assessed_evidence_generated(
        self, session: Session, department_registry: DepartmentRegistry
    ) -> None:
        policy = PolicyRequirement(
            name="Secure Coding Standard",
            description="All new software must pass security testing before release.",
        )

        assessment = analyze_policy_impact(
            session, policy=policy, department_registry=department_registry
        )

        # Requirement identified:
        assert assessment.policy_name == "Secure Coding Standard"
        # Impact assessed:
        assert "engineering" in assessment.affected_departments
        assert "Secure Coding Standard" in assessment.control_recommendation
        # Evidence generated:
        assert assessment.evidence["matching_method"] == "keyword_overlap"
        assert assessment.evidence["affected_departments"] == assessment.affected_departments

    def test_no_department_overlap_recommends_human_escalation_not_silence(
        self, session: Session, department_registry: DepartmentRegistry
    ) -> None:
        policy = PolicyRequirement(name="Zzz Policy", description="Qqq xyz flerm blorp.")

        assessment = analyze_policy_impact(
            session, policy=policy, department_registry=department_registry
        )

        assert assessment.affected_departments == []
        assert "escalate to a human" in assessment.control_recommendation
