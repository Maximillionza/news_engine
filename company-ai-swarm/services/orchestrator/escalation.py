"""Four-condition escalation policy (ESTAS sec.10 Risk Assessment substitute).

Source: IMPLEMENTATION_PLAN.md Phase 8, adopted (by explicit user decision, see
Documentation/operations/technology_decisions.md) from an external swarm review in place of
inventing a numeric risk/complexity score for COOS sec.9 - no such algorithm exists anywhere
in the source corpus (see orchestrator/planner.py's docstring). The COO escalates to a human
- and only a human - when one of exactly four named conditions fires; everything else it
resolves itself:

  1. NO_MATCHING_DEPARTMENT - Objective Understanding / Department Selection (COOS sec.7-9)
     found no viable department (orchestrator.controller.NoMatchingDepartmentError).
  2. OUTCOME_NOT_ACHIEVED - Outcome Validation (COOS sec.20) returned "objective not
     achieved" for a substantive (non-review) task, or the workflow as a whole.
  3. GATE_INTEGRITY_SUPERFICIAL - a review nominally passed (evaluator.validate_outcome())
     but its TDL sec.14 evidence is incomplete - see workflow_engine/gate_integrity.py.
  4. UNRESOLVABLE_DEPENDENCY_GAP - a matched department has no registered agent to carry out
     its task (orchestrator/allocator.py's ValueError case), so the workflow cannot proceed
     without a human resolving the gap.

A technical failure (an unhandled exception during dispatch - agent runtime error, Model
Gateway failure, or anything else not one of the four cases above) always escalates too, but
is logged as TECHNICAL_FAILURE, distinct from the four framework verdicts - never conflated
with them in the Escalation Record.
"""

from __future__ import annotations

import enum


class EscalationCondition(str, enum.Enum):
    NO_MATCHING_DEPARTMENT = "no_matching_department"
    OUTCOME_NOT_ACHIEVED = "outcome_not_achieved"
    GATE_INTEGRITY_SUPERFICIAL = "gate_integrity_superficial"
    UNRESOLVABLE_DEPENDENCY_GAP = "unresolvable_dependency_gap"
    TECHNICAL_FAILURE = "technical_failure"


FRAMEWORK_CONDITIONS = (
    EscalationCondition.NO_MATCHING_DEPARTMENT,
    EscalationCondition.OUTCOME_NOT_ACHIEVED,
    EscalationCondition.GATE_INTEGRITY_SUPERFICIAL,
    EscalationCondition.UNRESOLVABLE_DEPENDENCY_GAP,
)
