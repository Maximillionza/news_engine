"""Compliance Intelligence Engine data structures.

Source: Specifications/1 - enterprise-architecture/Enterprise Compliance & Regulatory
Intelligence Specification (ECRIS).md sec.8 (Applicability Assessment), and
Specifications/3 - execution-framework/MVP Validation Specification (MVS).md sec.12
(Test Category 008: Policy Added -> Impact Analysis -> Workflow Review -> Control
Recommendation).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class ApplicabilityAssessment(Base):
    """ECRIS sec.8: Business Activity + Location + Data Type + Industry + Entity Type +
    Risk Profile -> Regulatory Applicability. `applicable` is nullable, not just
    True/False - see applicability.py's module docstring for why an unrecognized regulation
    must record UNKNOWN rather than silently defaulting to not-applicable."""

    __tablename__ = "compliance_applicability_assessments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    regulation: Mapped[str] = mapped_column(String, nullable=False, index=True)
    business_activity: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    data_type: Mapped[str] = mapped_column(String, nullable=False)
    industry: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    risk_profile: Mapped[str] = mapped_column(String, nullable=False)
    applicable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class PolicyImpactAssessment(Base):
    """MVS sec.12 Test Category 008's flow, persisted: Policy Added -> Impact Analysis ->
    Workflow Review -> Control Recommendation. `affected_departments` is the Workflow Review
    result; `evidence` satisfies MVS-008's "Evidence generated" pass criterion."""

    __tablename__ = "compliance_policy_impact_assessments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    policy_name: Mapped[str] = mapped_column(String, nullable=False)
    policy_description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_departments: Mapped[list] = mapped_column(JSON, nullable=False)
    control_recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
