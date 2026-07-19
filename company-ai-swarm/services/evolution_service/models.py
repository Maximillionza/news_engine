"""Evolution Engine persistence: Improvement Opportunity + Change Proposal.

Source: Specifications/1 - enterprise-architecture/Enterprise Evolution & Self-Improvement
Specification (EESIS).md sec.7 (Improvement Opportunity Schema) and sec.8 (Change Proposal
Model), both modeled literally.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base
from simulation_service.models import SimulationRun  # noqa: F401 - registers the FK target table


class ProposalStatus(str, enum.Enum):
    """EESIS sec.8's `approval_status` field, plus IMPLEMENTED - the Evolution Engine's own
    terminal state. EESIS sec.13's Evolution Testing flow ends at Approval; sec.17's
    Evolution Feedback Loop's "Improve" step is what IMPLEMENTED represents (see
    pipeline.py's module docstring for exactly what "implemented" means here)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


class ImprovementOpportunity(Base):
    __tablename__ = "improvement_opportunities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommended_change: Mapped[str] = mapped_column(Text, nullable=False)
    expected_benefit: Mapped[str] = mapped_column(Text, nullable=False)
    risk: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ChangeProposal(Base):
    __tablename__ = "change_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(
        String, ForeignKey("improvement_opportunities.id"), nullable=False
    )
    target: Mapped[str] = mapped_column(String, nullable=False)
    current_state: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_state: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list] = mapped_column(JSON, nullable=False)
    risk: Mapped[str] = mapped_column(String, nullable=False)
    simulation_run_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("simulation_runs.id"), nullable=True
    )
    approval_status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus), nullable=False, default=ProposalStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)
