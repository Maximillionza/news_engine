"""Objective Queue: persisted job records for async objective execution.

Source: Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.2. Phase A scope only - the
table, ORM model, and CRUD functions exist and are tested (Tests/integration/
test_async_objective_queue.py), but nothing in apps/api_gateway/main.py or dashboard_api.py
writes to this table yet. `POST /chat` still calls `COOOrchestrator.receive_objective()`
directly and blocks, exactly as it did before this file existed - wiring `POST /chat` to
enqueue here instead, and having a background worker drain the queue, is Phase B ("Gateway
endpoint refactor" / "Queue worker core loop").

Status values (`ObjectiveStatus`) and columns follow the plan's Section 4.2 schema
one-for-one: id, status, objective, required_output, result (JSON), error, created_at,
started_at, completed_at, submitted_by.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db import Base


class ObjectiveStatus(str, Enum):
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class ObjectiveQueueRecord(Base):
    __tablename__ = "objective_queue"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=ObjectiveStatus.QUEUED.value)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    required_output: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue_objective(
    session: Session,
    *,
    objective: str,
    required_output: str,
    submitted_by: str | None = None,
) -> ObjectiveQueueRecord:
    """Creates a `queued` row and commits it. Returns the record so the caller (eventually
    `POST /chat`, in Phase B) can hand `record.id` straight back to the client as
    `objective_id` without a second query."""

    record = ObjectiveQueueRecord(
        id=f"OBJ-{uuid4().hex[:8]}",
        status=ObjectiveStatus.QUEUED.value,
        objective=objective,
        required_output=required_output,
        submitted_by=submitted_by,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_objective(session: Session, objective_id: str) -> ObjectiveQueueRecord | None:
    return session.get(ObjectiveQueueRecord, objective_id)


def list_queued_objectives(session: Session, *, limit: int = 50) -> list[ObjectiveQueueRecord]:
    """Oldest-first, so a worker polling this processes objectives in submission order."""

    return (
        session.query(ObjectiveQueueRecord)
        .filter(ObjectiveQueueRecord.status == ObjectiveStatus.QUEUED.value)
        .order_by(ObjectiveQueueRecord.created_at)
        .limit(limit)
        .all()
    )


def mark_executing(session: Session, objective_id: str) -> ObjectiveQueueRecord:
    record = _require(session, objective_id)
    record.status = ObjectiveStatus.EXECUTING.value
    record.started_at = _now()
    session.commit()
    session.refresh(record)
    return record


def mark_completed(session: Session, objective_id: str, result: dict[str, Any]) -> ObjectiveQueueRecord:
    record = _require(session, objective_id)
    record.status = ObjectiveStatus.COMPLETED.value
    record.result = result
    record.completed_at = _now()
    session.commit()
    session.refresh(record)
    return record


def mark_failed(session: Session, objective_id: str, error: str) -> ObjectiveQueueRecord:
    record = _require(session, objective_id)
    record.status = ObjectiveStatus.FAILED.value
    record.error = error
    record.completed_at = _now()
    session.commit()
    session.refresh(record)
    return record


def _require(session: Session, objective_id: str) -> ObjectiveQueueRecord:
    record = get_objective(session, objective_id)
    if record is None:
        raise ValueError(f"Unknown objective_id: {objective_id}")
    return record
