"""Scope confirmation: when an objective matches more than one department, ask the user to
confirm narrow-vs-broad before committing, rather than silently executing across every
matched department.

Source: 2026-07-25 vision-comparison session - the founder's original example: a user
providing supporting artefacts and requesting an app/feature built should get a chance to
confirm "Engineering only, to start the build" vs "the full review, including Compliance
requirements" - not have that decided for them silently. Distinct from orchestrator/intake.py's
sufficiency check, which only judges whether there is enough DETAIL to act at all - this judges
how many departments should be involved once there is already enough detail to know that.

Phase 22 (IMPLEMENTATION_PLAN.md, 2026-07-26) scope note: this deliberately does not attempt
real artifact-content analysis - no document-parsing tool exists anywhere in this codebase yet
(Phase 12 only gave Research a web-search tool). The trigger is purely "did the classifier
match more than one department" - the confirmation question lets the user's own free-text
reply carry any nuance ("just the build, skip compliance") into the consolidated objective
text that then flows through the existing classifier, which is already capable of reading
that nuance semantically (especially with DEPARTMENT_CLASSIFIER=llm) - no separate routing
override mechanism was built or is needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from orchestrator.department_registry import DepartmentDefinition
from shared.llm_json import strip_code_fence
from shared.model_gateway import ModelGateway

FALLBACK_SCOPE_QUESTION = (
    "This could be handled narrowly or broadly - would you like just {primary} to start, "
    "or the full review across {all_depts} as well?"
)


@dataclass
class ScopeConfirmationAssessment:
    needs_confirmation: bool
    clarifying_question: str | None
    reasoning: str


def assess_scope_confirmation(
    model_gateway: ModelGateway,
    objective: str,
    matched_departments: list[DepartmentDefinition],
    *,
    already_asked: bool,
) -> ScopeConfirmationAssessment:
    """`already_asked` is True when the immediately preceding coo message in this conversation
    was itself a scope-confirmation question (apps/api_gateway/dashboard_api.py tracks this via
    DashboardChatMessage.is_scope_confirmation) - in that case this always returns
    needs_confirmation=False without a model call, since the user's current message is the
    answer, not a new request to re-litigate. Combined with the single boolean gate (no
    round-counter of its own - it reuses intake.py's existing clarifying-round cap purely by
    also writing is_clarifying_question=True), this guarantees the gate can fire at most once
    per objective, never loop.

    A model-call failure is NOT caught here - same discipline as intake.assess_sufficiency(),
    it propagates so the caller can surface a distinct infrastructure error. An unparseable
    *response* fails toward needs_confirmation=False (proceed broad, i.e. every matched
    department) rather than asking again - unlike sufficiency's missing-detail case, a broad
    default here doesn't skip anything the user might have wanted, it's the same outcome as
    if this gate didn't exist at all."""

    if already_asked or len(matched_departments) <= 1:
        return ScopeConfirmationAssessment(
            needs_confirmation=False,
            clarifying_question=None,
            reasoning="Already confirmed, or only one department matched - nothing to confirm.",
        )

    primary = matched_departments[0]
    departments_text = "\n".join(f"- {d.id}: {d.name}. {d.purpose}" for d in matched_departments)

    prompt = (
        "You are the Chief Operating Officer of an AI company. A user's request has matched "
        "more than one department, and it may or may not be genuinely ambiguous whether they "
        "want the narrow scope (just the primary department, to move fast) or the broad scope "
        "(all matched departments, for a fuller review) - not every multi-department match "
        "needs asking, only ones where the request's own wording doesn't already make the "
        "intended scope clear.\n\n"
        f"Primary department: {primary.id}\n"
        f"All matched departments:\n{departments_text}\n\n"
        f"Request:\n{objective}\n\n"
        "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
        '{"needs_confirmation": true|false, "clarifying_question": "<string, or null>", '
        '"reasoning": "<one sentence>"}\n'
        "needs_confirmation=false if the request's own wording already makes the intended "
        'scope clear (e.g. it explicitly says "just build it" or explicitly asks for '
        "compliance/review too) - only ask when it is genuinely unclear."
    )

    # Deliberately not caught here - see this function's docstring.
    raw = model_gateway.generate(requester="coo:scope_confirmation", prompt=prompt)

    try:
        data = json.loads(strip_code_fence(raw))
        needs_confirmation = bool(data["needs_confirmation"])
        clarifying_question = data.get("clarifying_question")
        reasoning = data["reasoning"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return ScopeConfirmationAssessment(
            needs_confirmation=False,
            clarifying_question=None,
            reasoning=f"Could not parse the scope-confirmation response ({exc}); proceeding broad.",
        )

    if not needs_confirmation:
        return ScopeConfirmationAssessment(
            needs_confirmation=False, clarifying_question=None, reasoning=reasoning
        )

    all_ids = ", ".join(d.id for d in matched_departments)
    question = clarifying_question or FALLBACK_SCOPE_QUESTION.format(
        primary=primary.id, all_depts=all_ids
    )
    return ScopeConfirmationAssessment(
        needs_confirmation=True, clarifying_question=question, reasoning=reasoning
    )
