"""Digital Twin snapshot persistence.

Source: Specifications/1 - enterprise-architecture/Enterprise Simulation & Digital Twin
Specification (ESDTS).md sec.6 (Digital Twin Object Model), sec.31 (MVP Requirements:
Enterprise state model, Agent representation, Workflow representation, Event
synchronisation).

Phase 11 scope (IMPLEMENTATION_PLAN.md, post-MVP Intelligence Systems): a snapshot is a
point-in-time capture of real state already tracked elsewhere in this codebase (the Agent
Registry, Department Registry, and recent COO Decision Records) - not a live-updating
mirror. "Event synchronisation" (sec.31) is satisfied by capturing a fresh snapshot on
demand, not by a continuous change-feed subscription - no such feed exists anywhere in this
corpus (event_service's InMemoryEventBus is in-process pub/sub, not a durable change log).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class DigitalTwinSnapshot(Base):
    __tablename__ = "digital_twin_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # ESTAS sec.5-style entity representations, not the live ORM rows themselves - a
    # snapshot must remain valid after the underlying registries change.
    agents: Mapped[list] = mapped_column(JSON, nullable=False)
    departments: Mapped[list] = mapped_column(JSON, nullable=False)
    recent_decisions: Mapped[list] = mapped_column(JSON, nullable=False)
