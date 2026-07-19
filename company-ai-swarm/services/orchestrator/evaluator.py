"""Outcome Validation Engine.

Source: Specifications/1 - enterprise-architecture/The Company COO Orchestrator
Specification (COOS).md sec.20:

    Objective Achieved? Quality Acceptable? Compliance Satisfied? Risk Controlled?

Phase 5 scope: only "Objective Achieved?" is checked (did the Agent Runtime complete its
full execution cycle and produce output). "Quality Acceptable?" would need the evaluation
criteria from ADLS sec.16, which exist per-agent but have no scoring mechanism attached yet.
"Compliance Satisfied?" needs the Compliance Agent, which isn't wired in until Phase 6.
"Risk Controlled?" needs COOS sec.10's Risk Assessment Engine, not built. All three are
named explicitly below as not-yet-evaluated, not silently skipped.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_runtime.runtime import ExecutionResult

EXPECTED_EXECUTION_STEPS = [
    "receive_task",
    "load_context",
    "retrieve_knowledge",
    "check_policies",
    "plan_approach",
    "execute",
    "validate",
    "produce_artifact",
    "report_outcome",
    "release_context",
]


@dataclass
class OutcomeValidation:
    objective_achieved: bool
    reasoning: str
    quality_evaluated: bool = False
    compliance_evaluated: bool = False
    risk_evaluated: bool = False


def validate_outcome(result: ExecutionResult) -> OutcomeValidation:
    all_steps_completed = result.steps_completed == EXPECTED_EXECUTION_STEPS
    has_output = bool(result.output and result.output.strip())
    objective_achieved = all_steps_completed and has_output

    if objective_achieved:
        reasoning = "Agent completed the full execution cycle and produced non-empty output."
    elif not all_steps_completed:
        reasoning = (
            f"Execution cycle incomplete: expected {EXPECTED_EXECUTION_STEPS}, got "
            f"{result.steps_completed}."
        )
    else:
        reasoning = "Execution cycle completed but output was empty."

    return OutcomeValidation(objective_achieved=objective_achieved, reasoning=reasoning)
