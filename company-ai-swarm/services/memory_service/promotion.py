"""Lesson Promotion Workflow: the tiered Learn step (COOS sec.6, Phase 9).

Source: IMPLEMENTATION_PLAN.md Phase 9, adopted from an external swarm review (see
Documentation/operations/technology_decisions.md's Phase 8 entry) and reusing Phase 8's
four-condition escalation policy as the sole criticality signal, rather than inventing a
second risk classification.

- **Minor lessons** (a workflow that tripped none of Phase 8's four escalation conditions):
  the COO self-approves and writes directly to the Historical tier as a new, self-contained
  MemoryObject (memory_service.repository.write_memory() with tier=HISTORICAL) - no code in
  this module is involved, there is nothing to hold pending.
- **Critical lessons** (a workflow that tripped an escalation condition): written to
  Project-tier memory (not Historical) and held here as a `LessonPromotion` with status
  PENDING - a promotion-workflow concept kept deliberately separate from
  `MemoryObject.validation_status`, which is EMAS's epistemic-confidence field, not an
  approval-state field (conflating the two would repeat the tier/domain naming collision
  fixed in Phase 2). Approval never mutates the pending memory object's tier in place -
  approve_promotion() writes a brand-new Historical-tier MemoryObject, so "never merged into
  or amending an existing one" holds for promoted lessons too, not just auto-approved ones.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from memory_service.models import MemoryObject, MemoryTier
from memory_service.repository import write_memory
from shared.db import Base


class PromotionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LessonPromotion(Base):
    __tablename__ = "lesson_promotions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    memory_object_id: Mapped[str] = mapped_column(
        String, ForeignKey("memory_objects.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default=PromotionStatus.PENDING.value)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)


def request_promotion(
    session: Session, *, memory_object_id: str, reason: str
) -> LessonPromotion:
    record = LessonPromotion(
        id=f"PROMO-{uuid4().hex[:8]}", memory_object_id=memory_object_id, reason=reason
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_promotion(session: Session, promotion_id: str) -> LessonPromotion | None:
    return session.get(LessonPromotion, promotion_id)


def list_pending_promotions(session: Session) -> list[LessonPromotion]:
    return (
        session.query(LessonPromotion)
        .filter(LessonPromotion.status == PromotionStatus.PENDING.value)
        .order_by(LessonPromotion.created_at)
        .all()
    )


def approve_promotion(
    session: Session, promotion_id: str, *, approver_identity_id: str, note: str | None = None
) -> MemoryObject:
    promotion = session.get(LessonPromotion, promotion_id)
    if promotion is None:
        raise ValueError(f"Unknown promotion request: {promotion_id}")
    if promotion.status != PromotionStatus.PENDING.value:
        raise ValueError(f"Promotion {promotion_id} is not pending (status={promotion.status})")

    pending_memory = session.get(MemoryObject, promotion.memory_object_id)
    if pending_memory is None:
        raise ValueError(f"Memory object {promotion.memory_object_id} not found")

    historical_memory = write_memory(
        session,
        identity_id=approver_identity_id,
        id=f"{pending_memory.id}-HIST",
        type=pending_memory.type,
        content=pending_memory.content,
        creator=pending_memory.creator,
        tier=MemoryTier.HISTORICAL,
        source=f"promoted from {pending_memory.id} by {approver_identity_id}",
    )

    promotion.status = PromotionStatus.APPROVED.value
    promotion.resolved_at = datetime.now(timezone.utc)
    promotion.resolved_by = approver_identity_id
    promotion.resolution_note = note
    session.commit()
    session.refresh(promotion)
    return historical_memory


def reject_promotion(
    session: Session, promotion_id: str, *, approver_identity_id: str, note: str | None = None
) -> LessonPromotion:
    promotion = session.get(LessonPromotion, promotion_id)
    if promotion is None:
        raise ValueError(f"Unknown promotion request: {promotion_id}")
    if promotion.status != PromotionStatus.PENDING.value:
        raise ValueError(f"Promotion {promotion_id} is not pending (status={promotion.status})")

    promotion.status = PromotionStatus.REJECTED.value
    promotion.resolved_at = datetime.now(timezone.utc)
    promotion.resolved_by = approver_identity_id
    promotion.resolution_note = note
    session.commit()
    session.refresh(promotion)
    return promotion
