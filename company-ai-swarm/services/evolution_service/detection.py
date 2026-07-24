"""Improvement Detection.

Source: Specifications/1 - enterprise-architecture/Enterprise Evolution & Self-Improvement
Specification (EESIS).md sec.5 (Evolution Engine Responsibilities: "Monitor performance,
Detect inefficiencies...") and sec.6 (Improvement Sources - this reuses "Performance Data").

Phase 11 scope (IMPLEMENTATION_PLAN.md, post-MVP Intelligence Systems): reuses
orchestrator/escalation.py's GATE_INTEGRITY_SUPERFICIAL condition (Phase 8) as the one real,
already-detected inefficiency this codebase produces - a review step that ran with nothing
to review. This is not a synthetic inefficiency invented for this phase; it is the exact
signal Phase 8 already writes to the Escalation Record for governance reasons, reused here
as an Evolution input rather than duplicating detection logic. At the time, no other
inefficiency source (Agent Evaluation, Memory Analysis, Knowledge Analysis, Simulation
Results) was implemented - each needed data this corpus didn't track at a granularity fine
enough to detect from.

Phase 17 (IMPLEMENTATION_PLAN.md, 2026-07-23) implements Agent Evaluation:
detect_specialist_pattern() below reuses orchestrator/spawns.py's SpecialistSpawnRecord
ledger (written by Phase 16's Department Head specialist spawning) as that fine-grained
per-agent signal - a real, already-recorded fact (a specific department needed a specialist,
N times), not synthesized for this phase either. Memory Analysis, Knowledge Analysis, and
Simulation Results remain unimplemented for the same reason as before: no data tracked at a
fine enough granularity yet.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from evolution_service.models import ImprovementOpportunity
from orchestrator.escalation import EscalationCondition
from orchestrator.escalations import list_escalations_for_decision
from orchestrator.spawns import list_spawns_for_department


def detect_specialist_pattern(
    session: Session, *, department_id: str, threshold: int = 3
) -> ImprovementOpportunity | None:
    """Phase 17 (IMPLEMENTATION_PLAN.md, 2026-07-23): reuses orchestrator/spawns.py's
    SpecialistSpawnRecord ledger (Phase 16's "Agent Evaluation" source - this module's own
    docstring above named it as one of the not-yet-implemented sources, for lack of
    fine-grained enough data; the spawn ledger is that data) as the input, same discipline as
    detect_inefficiencies() reusing an existing signal rather than inventing new tracking.

    Unlike detect_inefficiencies() (scoped to one decision_id), this reads across every spawn
    ever recorded for one department - there is no per-decision boundary for "has this kept
    happening." Scoped to a single department per call (not "scan every department") because
    the caller (pipeline.py's propose_specialist_agent()) already knows which department it's
    evaluating - deciding *which* departments to check, and *when*, is a policy question left
    to whatever eventually calls this, not decided here.

    Returns None below `threshold` - same "the engine does not fabricate an opportunity to
    have something to propose" discipline detect_and_propose() already documents."""

    spawns = list_spawns_for_department(session, department_id)
    if len(spawns) < threshold:
        return None

    opportunity = ImprovementOpportunity(
        id=f"OPP-{uuid4().hex[:8]}",
        source="agent_evaluation",
        problem=f"The {department_id} department has needed a specialist {len(spawns)} times.",
        impact="Each spawn is a full extra reasoning cycle a dedicated agent could skip.",
        evidence={
            "department_id": department_id,
            "spawn_ids": [s.id for s in spawns],
            "reasonings": [s.reasoning for s in spawns],
        },
        recommended_change=(
            f"Create a dedicated agent for the {department_id} department specializing in "
            f"this recurring need."
        ),
        expected_benefit="Fewer ad hoc specialist dispatches for objectives matching this recurring pattern.",
        risk="low",
        priority="medium",
    )
    session.add(opportunity)
    session.commit()
    session.refresh(opportunity)
    return opportunity


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
