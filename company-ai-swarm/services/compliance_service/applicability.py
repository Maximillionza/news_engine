"""Applicability Assessment (ECRIS sec.8).

    Business Activity + Location + Data Type + Industry + Entity Type + Risk Profile
        = Regulatory Applicability

Implemented as a small, explicit rule registry - ECRIS sec.9's Compliance Knowledge Model
says knowledge SHALL be stored as Rules (among other categories) and explicitly prohibits
storing generalizations like "all projects of this type have this problem." The one rule
seeded here (POPIA) is taken directly from ECRIS sec.8's own worked example
("Personal information processed? Yes. South African entity? Yes. Applicability: Yes.").
Populating a real regulatory rule set is content curation, not a mechanism gap - out of
scope for this codebase. The mechanism (rule registry + evaluation) is real; the content is
deliberately minimal.

Safety-relevant design choice: an unrecognized regulation returns `applicable=None`
(UNKNOWN), never a silent `False`. A compliance engine defaulting an unrecognized regulation
to "not applicable" would be a false negative with real consequences - the honest failure
mode is "we don't know, a human must review," the same escalate-rather-than-guess spirit as
orchestrator/escalation.py's four-condition policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from sqlalchemy.orm import Session

from compliance_service.models import ApplicabilityAssessment


@dataclass
class ApplicabilityFactors:
    business_activity: str
    location: str
    data_type: str
    industry: str
    entity_type: str
    risk_profile: str


@dataclass
class ApplicabilityRule:
    regulation: str
    predicate: Callable[[ApplicabilityFactors], bool]
    reasoning_template: str


def _popia_predicate(factors: ApplicabilityFactors) -> bool:
    return (
        "personal_information" in factors.data_type.lower()
        and "south_africa" in factors.location.lower()
    )


RULES: list[ApplicabilityRule] = [
    ApplicabilityRule(
        regulation="POPIA",
        predicate=_popia_predicate,
        reasoning_template=(
            "POPIA regulates processing of personal information by South African entities "
            "(ECRIS sec.8's own worked example). data_type='{data_type}', "
            "location='{location}'."
        ),
    ),
]


def assess_applicability(
    session: Session, *, regulation: str, factors: ApplicabilityFactors
) -> ApplicabilityAssessment:
    rule = next((r for r in RULES if r.regulation == regulation), None)

    if rule is None:
        applicable = None
        reasoning = (
            f"No rule registered for '{regulation}' - see module docstring: this is a "
            f"small, seeded rule registry, not a full regulatory database. Result is "
            f"UNKNOWN, not 'not applicable' - requires human/legal review before proceeding."
        )
    else:
        applicable = rule.predicate(factors)
        reasoning = rule.reasoning_template.format(
            data_type=factors.data_type, location=factors.location
        )

    record = ApplicabilityAssessment(
        id=f"APL-{uuid4().hex[:8]}",
        regulation=regulation,
        business_activity=factors.business_activity,
        location=factors.location,
        data_type=factors.data_type,
        industry=factors.industry,
        entity_type=factors.entity_type,
        risk_profile=factors.risk_profile,
        applicable=applicable,
        reasoning=reasoning,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
