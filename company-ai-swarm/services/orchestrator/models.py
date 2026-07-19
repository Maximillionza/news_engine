"""COO Decision Record.

Source: Specifications/1 - enterprise-architecture/The Company COO Orchestrator
Specification (COOS).md sec.22:

    Decision_ID, Objective, Reasoning, Options Considered, Chosen Action, Agents Selected,
    Models Used, Outcome, Review Date

This mirrors the Decision Ledger in Decision Definition Language sec.17 (COOS sec.22's own
docstring note) - a COO Decision Record is a Decision Ledger entry scoped to operational
decisions. A general-purpose Decision Ledger table does not exist yet (nothing outside the
COO makes governed decisions yet), so this is COO-specific for now.

Phase 8 adds EscalationRecord: ESTAS sec.10 Risk Assessment persistence for
orchestrator/escalation.py's four-condition policy - see that module's docstring.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class COODecisionRecord(Base):
    __tablename__ = "coo_decision_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    options_considered: Mapped[list | None] = mapped_column(JSON, nullable=True)
    chosen_action: Mapped[str] = mapped_column(String, nullable=False)
    agents_selected: Mapped[list | None] = mapped_column(JSON, nullable=True)
    models_used: Mapped[list | None] = mapped_column(JSON, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EscalationRecord(Base):
    """Phase 8: persistence for orchestrator/escalation.py's four-condition policy (plus the
    technical-failure path). Distinct from COODecisionRecord - a decision is made for every
    objective; an escalation is written only when one of the five conditions fires. Linked to
    the decision it arose from, when one exists (NO_MATCHING_DEPARTMENT's rejection still
    writes a decision first, so it's always present)."""

    __tablename__ = "coo_escalation_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    decision_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("coo_decision_records.id"), nullable=True
    )
    condition: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    is_technical_failure: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
