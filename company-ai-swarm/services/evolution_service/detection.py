"""Improvement Detection.

Source: Specifications/1 - enterprise-architecture/Enterprise Evolution & Self-Improvement
Specification (EESIS).md sec.5 (Evolution Engine Responsibilities: "Monitor performance,
Detect inefficiencies...") and sec.6 (Improvement Sources - this reuses "Performance Data").

Phase 11 scope (IMPLEMENTATION_PLAN.md, post-MVP Intelligence Systems): reuses
orchestrator/escalation.py's GATE_INTEGRITY_SUPERFICIAL condition (Phase 8) as the one real,
already-detected inefficiency this codebase produces - a review step that ran with nothing
to review. This is not a synthetic inefficiency invented for this phase; it is the exact
signal Phase 8 already writes to the Escalation Record for governance reasons, reused here
as an Evolution input rather than duplicating detection logic. No other inefficiency source
(Agent Evaluation, Memory Analysis, Knowledge Analysis, Simulation Results) is implemented -
each needs data this corpus doesn't track at a granularity fine enough to detect from
(per-agent failure-rate trends, knowledge staleness, etc.).
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from evolution_service.models import ImprovementOpportunity
from orchestrator.escalation import EscalationCondition
from orchestrator.escalations import list_escalations_for_decision


def detect_inefficiencies(session: Session, *, decision_id: str) -> list[ImprovementOpportunity]:
    escalations = list_escalations_for_decision(session, decision_id)
    gate_escalations = [
        e for e in escalations if e.condition == EscalationCondition.GATE_INTEGRITY_SUPERFICIAL.value
    ]

    opportunities: list[ImprovementOpportunity] = []
    for escalation in gate_escalations:
        opportunity = ImprovementOpportunity(
            id=f"OPP-{uuid4().hex[:8]}",
            source="performance_data",
            problem="A review step ran with nothing to review (Gate Integrity Check flagged it superficial).",
            impact="Wasted a task dispatch, a Model Gateway call, and telemetry for zero informational value.",
            evidence={
                "escalation_id": escalation.id,
                "decision_id": decision_id,
                "reasoning": escalation.reasoning,
            },
            recommended_change="Skip the review step when the workflow has no substantive tasks to review.",
            expected_benefit="Fewer wasted task dispatches for objectives that match only the review department.",
            risk="low",
            priority="medium",
        )
        session.add(opportunity)
        opportunities.append(opportunity)

    session.commit()
    for opportunity in opportunities:
        session.refresh(opportunity)
    return opportunities
