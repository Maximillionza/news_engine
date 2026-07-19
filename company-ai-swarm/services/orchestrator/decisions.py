"""COO Decision Record persistence (COOS sec.22)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from orchestrator.models import COODecisionRecord


def write_decision(
    session: Session,
    *,
    id: str,
    objective: str,
    reasoning: str,
    chosen_action: str,
    options_considered: list[str] | None = None,
    agents_selected: list[str] | None = None,
    models_used: list[str] | None = None,
    outcome: str | None = None,
    review_date: datetime | None = None,
) -> COODecisionRecord:
    record = COODecisionRecord(
        id=id,
        objective=objective,
        reasoning=reasoning,
        options_considered=options_considered or [],
        chosen_action=chosen_action,
        agents_selected=agents_selected or [],
        models_used=models_used or [],
        outcome=outcome,
        review_date=review_date,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def update_outcome(session: Session, *, decision_id: str, outcome: str) -> COODecisionRecord | None:
    record = session.get(COODecisionRecord, decision_id)
    if record is not None:
        record.outcome = outcome
        session.commit()
        session.refresh(record)
    return record


def get_decision(session: Session, decision_id: str) -> COODecisionRecord | None:
    return session.get(COODecisionRecord, decision_id)


def list_decisions(session: Session) -> list[COODecisionRecord]:
    """Phase 8 addition: observability_service/views.py's Director/COO views (EOCCS
    sec.22-23) need "Major decisions"/recent activity, not just single-record lookup."""

    return session.query(COODecisionRecord).order_by(COODecisionRecord.created_at).all()
