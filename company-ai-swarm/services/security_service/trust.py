"""Trust Scoring Model.

Source: Specifications/1 - enterprise-architecture/Enterprise Security & Trust Architecture
Specification (ESTAS).md sec.26:

    Trust MAY consider: Historical reliability, Compliance performance, Error rate, Security
    behaviour, Validation results.
    Trust scores SHALL influence: Permissions, Review requirements, Resource allocation.

Honest scope: only "Error rate" is computed, from the actor's own audit trail
(security_service/audit.py, Phase 1) - denied-decision ratio. "Compliance performance" needs
compliance_service assessments tied to a specific actor (not modeled that way);
"Security behaviour" and "Validation results" need the Prompt Injection Defence / Agent
Behaviour Monitoring machinery (ESTAS sec.22-23, not implemented); "Historical reliability"
beyond error rate needs longer-window trend data this codebase doesn't retain. The score
computed here is real and used to set Identity.trust_level - wiring trust level to actually
*influence* Permissions/Review requirements/Resource allocation (sec.26's last paragraph) is
not done in this pass; that's an enforcement change with a wider blast radius than this
phase's exit criteria calls for, not a silently-dropped requirement.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from identity_service.models import Identity, TrustLevel
from security_service.audit import get_audit_trail

# ESTAS sec.7's four trust levels, in ascending order. ENTERPRISE_AUTHORITY is never derived
# from a score here - ESTAS describes no scoring path to the top tier, only assignment.
_LEVEL_THRESHOLDS: list[tuple[float, TrustLevel]] = [
    (0.9, TrustLevel.TRUSTED),
    (0.5, TrustLevel.OPERATIONAL),
]


@dataclass
class TrustScoreResult:
    identity_id: str
    score: float | None
    level: TrustLevel
    total_actions: int
    denied_actions: int


def compute_trust_score(session: Session, identity_id: str) -> TrustScoreResult:
    records = get_audit_trail(session, identity_id)
    total = len(records)
    denied = len([r for r in records if r.decision == "denied"])

    if total == 0:
        # No history to score - ESTAS sec.7's own default for a new identity, not a guess.
        return TrustScoreResult(
            identity_id=identity_id, score=None, level=TrustLevel.RESTRICTED,
            total_actions=0, denied_actions=0,
        )

    score = 1.0 - (denied / total)
    level = TrustLevel.RESTRICTED
    for threshold, candidate_level in _LEVEL_THRESHOLDS:
        if score >= threshold:
            level = candidate_level
            break

    return TrustScoreResult(
        identity_id=identity_id, score=score, level=level,
        total_actions=total, denied_actions=denied,
    )


def update_trust_level(session: Session, identity_id: str) -> Identity | None:
    result = compute_trust_score(session, identity_id)
    identity = session.get(Identity, identity_id)
    if identity is not None:
        identity.trust_level = result.level
        session.commit()
        session.refresh(identity)
    return identity
