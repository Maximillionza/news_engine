"""Alerting Model.

Source: Specifications/1 - enterprise-architecture/Enterprise Observability & Control Plane
Specification (EOCCS).md sec.25:

    Information -> Warning -> High Risk -> Critical

Rule-based classification over real telemetry (Phase 3) and Escalation Records (Phase 8) -
not a new monitoring system. Thresholds/mappings below are illustrative defaults, not tuned
from real operational data - same honesty as every other fixed-default decision in this
corpus (orchestrator/planner.py's complexity level, workflow_engine/review.py's tier
mapping). The mechanism is real; the specific cutoffs are not claimed to be validated.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from sqlalchemy.orm import Session

from observability_service.telemetry import TelemetryResult, TelemetrySink
from orchestrator.escalations import list_pending_escalations


class AlertSeverity(str, enum.Enum):
    INFORMATION = "information"
    WARNING = "warning"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"


@dataclass
class Alert:
    severity: AlertSeverity
    message: str


def generate_alerts(sink: TelemetrySink, session: Session) -> list[Alert]:
    alerts: list[Alert] = []
    records = sink.query()

    denied = [r for r in records if r.result == TelemetryResult.DENIED]
    if denied:
        alerts.append(Alert(AlertSeverity.WARNING, f"{len(denied)} denied action(s) recorded."))

    failures = [r for r in records if r.result == TelemetryResult.FAILURE]
    if failures:
        alerts.append(Alert(AlertSeverity.HIGH_RISK, f"{len(failures)} failed action(s) recorded."))

    for escalation in list_pending_escalations(session):
        if escalation.is_technical_failure:
            alerts.append(
                Alert(
                    AlertSeverity.CRITICAL,
                    f"Unresolved technical failure: {escalation.reasoning}",
                )
            )
        else:
            alerts.append(
                Alert(
                    AlertSeverity.HIGH_RISK,
                    f"Unresolved escalation ({escalation.condition}): {escalation.reasoning}",
                )
            )

    if not alerts:
        alerts.append(Alert(AlertSeverity.INFORMATION, "No issues detected."))

    return alerts
