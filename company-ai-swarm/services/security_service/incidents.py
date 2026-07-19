"""Security Incident Response + Incident Workflow.

Source: Specifications/1 - enterprise-architecture/Enterprise Security & Trust Architecture
Specification (ESTAS).md sec.27 (Detection, Containment, Analysis, Recovery, Learning) and
sec.28:

    Detection -> Classification -> Containment -> Investigation -> Remediation -> Review ->
    Knowledge Update

Implemented as an explicit state machine over a persisted SecurityIncident row, advancing one
canonical stage at a time. Phase 8 scope: forward-only, no skip, no loop back - a deliberate
simplification; real incident handling sometimes needs to revisit an earlier stage, not
modeled here.

Incidents are opened explicitly (open_incident()) by whatever detects a security-relevant
event - this module is not wired into orchestrator/escalation.py's four-condition policy.
That policy concerns workflow/task governance verdicts (no matching department, a review
that didn't pass); this concerns security events (unauthorized access, policy violations).
ESTAS itself treats these as separate concerns (sec.26's own note distinguishing Trust from
Authority from Autonomy draws the same kind of line).
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db import Base


class IncidentStatus(str, enum.Enum):
    DETECTION = "detection"
    CLASSIFICATION = "classification"
    CONTAINMENT = "containment"
    INVESTIGATION = "investigation"
    REMEDIATION = "remediation"
    REVIEW = "review"
    KNOWLEDGE_UPDATE = "knowledge_update"


_STAGE_ORDER = [
    IncidentStatus.DETECTION,
    IncidentStatus.CLASSIFICATION,
    IncidentStatus.CONTAINMENT,
    IncidentStatus.INVESTIGATION,
    IncidentStatus.REMEDIATION,
    IncidentStatus.REVIEW,
    IncidentStatus.KNOWLEDGE_UPDATE,
]


class InvalidStageTransition(Exception):
    pass


class SecurityIncident(Base):
    __tablename__ = "security_incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=IncidentStatus.DETECTION.value)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


def open_incident(
    session: Session, *, description: str, actor: str | None = None, evidence: dict | None = None
) -> SecurityIncident:
    incident = SecurityIncident(
        id=f"INC-{uuid4().hex[:8]}",
        description=description,
        actor=actor,
        status=IncidentStatus.DETECTION.value,
        evidence=evidence or {},
        notes=[],
    )
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


def advance_incident(
    session: Session, incident_id: str, *, note: str | None = None
) -> SecurityIncident:
    """Advances to the single next stage in sec.28's canonical order - see module docstring
    for why this is forward-only, one step at a time."""

    incident = session.get(SecurityIncident, incident_id)
    if incident is None:
        raise ValueError(f"Unknown incident: {incident_id}")

    current = IncidentStatus(incident.status)
    current_index = _STAGE_ORDER.index(current)
    if current_index == len(_STAGE_ORDER) - 1:
        raise InvalidStageTransition(
            f"Incident {incident_id} is already at the final stage ({current.value})."
        )

    next_stage = _STAGE_ORDER[current_index + 1]
    incident.status = next_stage.value
    if note:
        incident.notes = [*(incident.notes or []), f"{next_stage.value}: {note}"]
    session.commit()
    session.refresh(incident)
    return incident


def get_incident(session: Session, incident_id: str) -> SecurityIncident | None:
    return session.get(SecurityIncident, incident_id)
