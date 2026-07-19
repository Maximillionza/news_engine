"""Enterprise Command Centre views.

Source: Specifications/1 - enterprise-architecture/Enterprise Observability & Control Plane
Specification (EOCCS).md sec.21 (Enterprise Command Centre), sec.22 (Director View), sec.23
(COO View), sec.24 (Department View).

Read-only aggregations over Phase 3's TelemetrySink and Phase 5/8's orchestrator records (COO
Decision Records, Escalation Records) - real data already being recorded, not new
instrumentation. EOCCS sec.21's Command Centre (Enterprise Health, Active Work, Intelligence
Utilization, Risk Overview, Improvement Opportunities) is a UI concept; what's implemented
here is the query layer beneath it, scoped to what sec.22-24 actually require each role to
receive. No dashboard/frontend exists - these are dataclasses a future one would query.

Fields sec.22-24 name that are deliberately NOT populated here (documented, not silently
dropped): "Long-term trends" (Director) needs historical time-series data this codebase
doesn't retain; "Resource utilization" and "Agent availability" (COO) need concurrent-task/
capacity tracking - the same gap orchestrator/allocator.py already documents for Agent
Allocation; "Demand" and "Knowledge growth" (Department) need historical trend data not
tracked anywhere yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from observability_service.telemetry import TelemetryResult, TelemetrySink
from orchestrator.decisions import list_decisions
from orchestrator.escalations import list_pending_escalations


@dataclass
class DirectorView:
    enterprise_health: str
    major_risks: list[str] = field(default_factory=list)
    major_decisions: list[str] = field(default_factory=list)


@dataclass
class COOView:
    operational_status: str
    workflow_performance: dict = field(default_factory=dict)
    escalations: list[str] = field(default_factory=list)


@dataclass
class DepartmentView:
    department_id: str
    agent_health: str
    quality_metrics: dict = field(default_factory=dict)


def _health_from_sink(sink: TelemetrySink) -> str:
    records = sink.query()
    if not records:
        return "unknown"
    if any(r.result == TelemetryResult.FAILURE for r in records):
        return "degraded"
    if any(r.result == TelemetryResult.DENIED for r in records):
        return "attention_needed"
    return "healthy"


def director_view(sink: TelemetrySink, session: Session) -> DirectorView:
    escalations = list_pending_escalations(session)
    decisions = list_decisions(session)
    return DirectorView(
        enterprise_health=_health_from_sink(sink),
        major_risks=[f"{e.condition}: {e.reasoning}" for e in escalations],
        major_decisions=[d.objective for d in decisions],
    )


def coo_view(sink: TelemetrySink, session: Session) -> COOView:
    records = sink.query()
    escalations = list_pending_escalations(session)
    return COOView(
        operational_status=_health_from_sink(sink),
        workflow_performance={
            "total_actions": len(records),
            "failures": len([r for r in records if r.result == TelemetryResult.FAILURE]),
        },
        escalations=[e.condition for e in escalations],
    )


def department_view(sink: TelemetrySink, *, department_id: str, agent_ids: list[str]) -> DepartmentView:
    components = {f"agent_runtime:{agent_id}" for agent_id in agent_ids}
    records = [r for r in sink.query() if r.component in components]
    failures = [r for r in records if r.result == TelemetryResult.FAILURE]

    if not records:
        health = "unknown"
    elif failures:
        health = "degraded"
    else:
        health = "healthy"

    return DepartmentView(
        department_id=department_id,
        agent_health=health,
        quality_metrics={"actions_recorded": len(records), "failures": len(failures)},
    )
