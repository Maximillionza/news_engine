# Workflow Engine

Executes, sequences, and recovers enterprise workflows.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Workflow Orchestration Specification (EWOS).md

**Status:** Implemented through IMPLEMENTATION_PLAN.md Phase 8 (MVP Build Order Version
0.4). Department-level Task Decomposition (EWOS sec.10) + Sequential Execution (EWOS sec.14)
only, with a risk-proportional review step, Knowledge Graph recording, a Gate Integrity
Check, and graceful (non-crashing) handling of an unresolvable agent-allocation gap.

- `models.py` - `TaskRun`/`WorkflowRun`, the EWOS sec.5/sec.11 fields Phase 6/7 actually
  populate (see module docstring for what's not modeled yet). `WorkflowRun.review_tier` is
  the Phase 7 addition.
- `engine.py` - `execute_workflow()`: one task per matched department, executed in a fixed
  canonical order (`orchestrator/classification.py`'s `select_all_matching_departments`,
  originally `orchestrator/planner.py`'s), halting on
  the first task whose outcome is not achieved. Parallel Execution (EWOS sec.13) is not
  implemented - see module docstring. Phase 7: if "operations" (the Review Agent's
  department, `REVIEW_DEPARTMENT_ID`) is among the matched departments, it is not run as a
  substantive task on the original objective - once every other department succeeds, a
  review task is dispatched to it instead (see `review.py`), and every task (substantive and
  review) is recorded to the Knowledge Graph (see `knowledge.py`). Phase 8: if a matched
  department has no registered agent (`orchestrator/allocator.py`'s `ValueError`), the
  workflow halts gracefully with `WorkflowRun.blocked_reason` set, rather than raising -
  escalation condition 4 (`orchestrator/escalation.py`), a framework verdict the caller is
  responsible for turning into an Escalation Record. The review step's TDL sec.14 evidence
  and its Gate Integrity verdict (`gate_integrity.py`, escalation condition 3) are also
  recorded onto the `WorkflowRun` - this module reports facts, `orchestrator/controller.py`
  decides what to do with them.
- `review.py` - Phase 7: TDL sec.17's risk-proportional Task Review tier table
  (`determine_review_tier`). Complexity scoring is still a fixed default everywhere in this
  corpus (`orchestrator/controller.py`, originally set in `orchestrator/planner.py`), so
  "peer_review" is the only tier this phase can ever actually produce - the full table is
  implemented so the other tiers activate without redesign once real complexity scoring
  exists.
- `knowledge.py` - Phase 7: `record_task_knowledge()` records
  `Agent --USES--> Capability --APPLIES_TO--> Workflow` (EKGS sec.5, UOL sec.6) to
  `knowledge_service` for every completed task, substantive or review. One capability per
  task (the department's first-listed one) - see module docstring for why.
- `gate_integrity.py` - Phase 8: `check_gate_integrity()` (TDL sec.13/14), flags a review
  that nominally passed but whose TDL sec.14 evidence is empty - concretely, a review with
  nothing to review (an "operations only" objective). Confidence Assessment is deliberately
  excluded from the check - see module docstring for why requiring it would flag every
  review this codebase can ever produce.

**Tests:** `Tests/integration/test_workflow_orchestration.py` (Phase 6, two-department),
`Tests/integration/test_knowledge_graph_review.py` (Phase 7, four-department + review +
Knowledge Graph), `Tests/integration/test_escalation_policy.py` (Phase 8, conditions 3 and 4).
