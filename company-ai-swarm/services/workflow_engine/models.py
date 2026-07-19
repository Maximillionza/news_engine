"""Workflow/Task run records.

Source: Specifications/1 - enterprise-architecture/Enterprise Workflow Orchestration
Specification (EWOS).md sec.5 (Workflow Object) and sec.11 (Task Definition).

Phase 6 scope: these model only the fields Phase 6 actually populates. EWOS sec.5's
`Trigger`, `Policies`, `Completion Criteria`, `Metrics`, and `Lifecycle State`, and sec.11's
`Complexity`, `Risk`, and `Required Model Tier`, have no producer in this codebase yet -
COOS sec.9's complexity scoring and RDL's reasoning-tier routing remain undefined (see
orchestrator/planner.py and shared/model_gateway.py). Not modeling them here is the same
honesty discipline as those modules, not an oversight.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_runtime.runtime import ExecutionResult
from orchestrator.department_registry import DepartmentDefinition
from orchestrator.evaluator import OutcomeValidation


@dataclass
class TaskRun:
    task_id: str
    department: DepartmentDefinition
    agent_id: str
    execution_result: ExecutionResult
    validation: OutcomeValidation


@dataclass
class WorkflowRun:
    workflow_id: str
    objective: str
    tasks: list[TaskRun] = field(default_factory=list)
    succeeded: bool = False
    # Phase 7: set when the workflow included a review step (TDL sec.17), via
    # workflow_engine/review.py's tier mapping. None means no review-capable department
    # (operations) was matched, so no review ran - not that review was skipped/failed.
    review_tier: str | None = None
    # Phase 8: the review step's TDL sec.14 evidence and workflow_engine/gate_integrity.py's
    # verdict on it. Both None when no review ran, same reasoning as review_tier above.
    review_evidence: dict | None = None
    gate_superficial: bool | None = None
    # Phase 8: set (non-None) when a matched department had no registered agent
    # (orchestrator/allocator.py's ValueError) - escalation condition 4
    # (orchestrator/escalation.py), not an unhandled exception. `succeeded` is False
    # whenever this is set.
    blocked_reason: str | None = None
