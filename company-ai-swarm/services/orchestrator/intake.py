"""Sufficiency check: does the COO have enough detail to act on an objective, or should it
ask the user a clarifying question first?

Source: Documentation/plans/2026-07-19-dynamic-department-routing-design.md Section 3.2.
Chat-specific pre-flight logic - called from apps/api_gateway/dashboard_api.py's POST /chat,
before anything is ever enqueued. POST /chat/sync and POST /objectives (EAAS) do not use
this.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from orchestrator.department_registry import DepartmentRegistry
from shared.llm_json import strip_code_fence
from shared.model_gateway import ModelGateway

FALLBACK_CLARIFYING_QUESTION = (
    "Could you provide a bit more detail about what you'd like the swarm to do?"
)


@dataclass
class SufficiencyAssessment:
    sufficient: bool
    clarifying_question: str | None
    reasoning: str


def assess_sufficiency(
    model_gateway: ModelGateway,
    objective: str,
    recent_messages: list[tuple[str, str]],
    department_registry: DepartmentRegistry,
    round_number: int,
) -> SufficiencyAssessment:
    """`round_number` is 1-indexed, computed by the caller (apps/api_gateway/dashboard_api.py
    counts trailing consecutive is_clarifying_question=True DashboardChatMessage rows + 1).
    Round 3+ never calls the model - forces sufficient=True in code, guaranteeing the
    clarification loop terminates regardless of what the model would have said.

    A model-call failure (network/timeout/provider error) is NOT caught here - it propagates
    to the caller, which must surface a distinct error rather than silently treat it as an
    'insufficient' verdict. An unparseable/malformed *response* (the call succeeded, but
    didn't return the JSON shape asked for) IS caught, and fails toward insufficient with a
    generic fallback question - proceeding into a real task execution on a response we
    couldn't interpret is worse than asking once more."""

    if round_number >= 3:
        return SufficiencyAssessment(
            sufficient=True,
            clarifying_question=None,
            reasoning="Round 3 cap reached - proceeding with the information gathered so far.",
        )

    history_text = "\n".join(f"{role}: {content}" for role, content in recent_messages) or "(none yet)"
    departments_text = "\n".join(
        f"- {d.name}: {d.purpose}" for d in department_registry.all() if d.agents
    )

    if round_number == 1:
        round_instruction = (
            "This is the first time you're assessing this request. If it lacks enough "
            "detail to act on, ask one specific clarifying question about what's missing."
        )
    else:
        round_instruction = (
            "You have already asked one clarifying question about this request and the "
            "user has replied, but it is still not enough to act on confidently. Do NOT ask "
            "another open-ended question. Instead, phrase your reply as an explicit choice: "
            "offer to proceed with what has been shared so far (noting this may affect "
            "delivery quality or detail), or ask specifically for the one piece of "
            "information still missing."
        )

    prompt = (
        "You are the Chief Operating Officer of an AI company, deciding whether a user's "
        "request has enough detail to hand off to a department for execution.\n\n"
        f"Departments available:\n{departments_text}\n\n"
        f"Conversation so far:\n{history_text}\n\n"
        f"Latest request:\n{objective}\n\n"
        f"{round_instruction}\n\n"
        "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
        '{"sufficient": true|false, "clarifying_question": "<string, or null if sufficient>", '
        '"reasoning": "<one sentence>"}'
    )

    # Deliberately not caught here - see this function's docstring.
    raw = model_gateway.generate(requester="coo:sufficiency", prompt=prompt)

    try:
        data = json.loads(strip_code_fence(raw))
        sufficient = bool(data["sufficient"])
        clarifying_question = data.get("clarifying_question")
        reasoning = data["reasoning"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return SufficiencyAssessment(
            sufficient=False,
            clarifying_question=FALLBACK_CLARIFYING_QUESTION,
            reasoning=f"Could not parse the sufficiency check's response ({exc}); asking for more detail.",
        )

    if sufficient:
        return SufficiencyAssessment(sufficient=True, clarifying_question=None, reasoning=reasoning)

    return SufficiencyAssessment(
        sufficient=False,
        clarifying_question=clarifying_question or FALLBACK_CLARIFYING_QUESTION,
        reasoning=reasoning,
    )
