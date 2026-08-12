# Task 4 Report: Multi-department triage wiring in `workflow_engine/engine.py`

## What I implemented

Followed the brief (`.superpowers/sdd/task-4-brief.md`) verbatim.

1. **`services/workflow_engine/engine.py`**
   - Added import: `from orchestrator.head import AutoAcceptDepartmentHead, DepartmentHead`
   - `execute_workflow()` gained `head: DepartmentHead = AutoAcceptDepartmentHead()` as the
     last keyword-only parameter.
   - The `substantive_departments` loop now calls `head.evaluate(department, objective,
     agent_registry=..., model_gateway=..., session=..., coo_id=..., telemetry=...)`
     immediately before `select_agent()`. On `not verdict.accepted`, sets
     `run.succeeded = False`, `run.blocked_reason = f"department_rejected: {verdict.reasoning}"`,
     and returns immediately (no rollback, no reassignment) - identical control-flow shape to
     the existing missing-agent (`unresolvable_dependency_gap:`) halt just below it.
   - The review-step block (dispatch to the "operations" department after the substantive
     loop) was left completely untouched - no Head evaluation added there, per the brief's
     explicit scope note.
   - Added the "Department Head Triage addition" paragraph to the module docstring, after the
     existing Phase 8 paragraph, exactly as given in the brief.

2. **`services/orchestrator/controller.py`**
   - `_receive_multi_department_objective`'s call to `execute_workflow(...)` now passes
     `head=self._head` (the field already existed from Task 3's `COOOrchestrator.__init__`).
   - `blocked_reason` handling now branches: `EscalationCondition.DEPARTMENT_REJECTED` if
     `workflow.blocked_reason.startswith("department_rejected:")`, else
     `EscalationCondition.UNRESOLVABLE_DEPENDENCY_GAP` (unchanged behavior for the
     missing-agent case).

3. **`Tests/integration/test_department_head_triage_workflow.py`** - new file, written
   exactly as given in the brief. Two tests:
   - `test_execute_workflow_halts_when_a_substantive_departments_head_rejects`: a
     `_RejectSecondDepartmentHead` accepts "research" then rejects "engineering"; asserts the
     run halts with `blocked_reason` starting `"department_rejected:"`, containing the
     rejection reasoning, exactly one completed task (research, untouched - no rollback), and
     that the Head was consulted for both departments in order.
   - `test_receive_objective_maps_the_reject_to_department_rejected_not_dependency_gap`: runs
     the same rejecting Head through `COOOrchestrator.receive_objective()` and asserts the
     pending escalation list contains `DEPARTMENT_REJECTED` and not
     `UNRESOLVABLE_DEPENDENCY_GAP`.

Before editing, I read both target files in full and confirmed their current content matched
the brief's "before" code blocks exactly (both the signature/loop text in `engine.py` and the
`_receive_multi_department_objective` blocks in `controller.py`, including the `head`
constructor param and `DepartmentRejectedError`/`EscalationCondition.DEPARTMENT_REJECTED`
already landed by Task 3). No mismatches found, so no escalation was needed.

## Test commands and output

Focused:
```
python -m pytest Tests/integration/test_department_head_triage_workflow.py -v
```
```
Tests/integration/test_department_head_triage_workflow.py::test_execute_workflow_halts_when_a_substantive_departments_head_rejects PASSED [ 50%]
Tests/integration/test_department_head_triage_workflow.py::test_receive_objective_maps_the_reject_to_department_rejected_not_dependency_gap PASSED [100%]
2 passed in 0.76s
```

Full suite:
```
python -m pytest Tests/ -q
```
```
263 passed, 4 skipped, 1 warning in 12.70s
```
Zero regressions. Confirmed by name that `Tests/integration/test_escalation_policy.py`'s
`TestCondition4UnresolvableDependencyGap` and `TestCondition3GateIntegritySuperficial` are
part of that passing run (they're collected under `Tests/integration/`, which is fully
covered by the `Tests/` run above; no failures or new skips appeared).

## Files changed

- `services/workflow_engine/engine.py` (modified)
- `services/orchestrator/controller.py` (modified)
- `Tests/integration/test_department_head_triage_workflow.py` (new)

Note: `services/workflow_engine/engine.py` had pre-existing uncommitted changes in the
working tree before this task started (unrelated doc-reference updates: `orchestrator/planner.py`
-> `orchestrator/classification.py` in two docstring paragraphs, per the session's initial
`git status`). Since the brief's own Step 7 instructs staging the whole file
(`git add services/workflow_engine/engine.py`), those pre-existing edits were included in the
same commit alongside my Task 4 changes - I did not introduce them and did not attempt to
split them out, per the task's explicit instruction to stage only these 3 files (not `git add -A`)
and its note that unrelated pre-existing uncommitted changes exist in this working tree.

## Self-review findings

- Completeness: `execute_workflow()` signature gained `head: DepartmentHead =
  AutoAcceptDepartmentHead()` as specified; the substantive-departments loop evaluates the
  Head before `select_agent()` and halts with the `"department_rejected: "` prefix on
  reject; the review step is untouched (verified by diff - no `head.evaluate` call added to
  that block); `_receive_multi_department_objective` passes `head=self._head` and branches
  correctly on the blocked_reason prefix.
- Quality: no rollback logic added - the reject path is a direct `return run` after setting
  `succeeded`/`blocked_reason`, matching the "no rollback, no reassignment" constraint and
  mirroring the existing missing-agent halt's shape. The module docstring paragraph from the
  brief is included verbatim.
- Discipline: diff for `controller.py` and the new test file contains only the brief-specified
  changes. Diff for `engine.py` additionally contains the pre-existing unrelated doc-reference
  changes described above (not introduced by me).
- Testing: both new tests pass; full suite (263 passed, 4 skipped) has zero regressions
  versus the pre-task baseline.

## Concerns

None. The task proceeded exactly as scripted by the brief with no mismatches between the
brief's before/after blocks and the actual file contents.
