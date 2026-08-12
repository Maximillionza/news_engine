# Task 3 Report: Single-department triage wiring in `orchestrator/controller.py`

## What was implemented

Followed the brief verbatim (`.superpowers/sdd/task-3-brief.md`) with no deviations.

1. **`services/orchestrator/escalation.py`** - replaced whole file: `EscalationCondition` gained
   `DEPARTMENT_REJECTED = "department_rejected"`, added to `FRAMEWORK_CONDITIONS`, and the module
   docstring updated from "Four-condition" to "Five-condition" policy with a new item 5 describing
   the Department Head rejection condition.

2. **`services/orchestrator/controller.py`**:
   - Added `from orchestrator.head import AutoAcceptDepartmentHead, DepartmentHead` (between the
     `orchestrator.evaluator` and `orchestrator.router` imports).
   - Added `class DepartmentRejectedError(Exception): pass` immediately after
     `NoMatchingDepartmentError`.
   - `COOOrchestrator.__init__` gained a `head: DepartmentHead = AutoAcceptDepartmentHead()` kwarg,
     stored as `self._head`.
   - `receive_objective()`'s single-department branch now calls
     `self._triage_single_department(...)` to resolve the actual department (instead of using
     `matched_departments[0]` directly), and uses its return value as `TaskProfile.matched_department`.
   - Added `_triage_single_department()` (new method, placed between `receive_objective()` and
     `_receive_multi_department_objective()`): bounded 2-attempt loop. Attempt 1 evaluates the
     classifier's original match; on reject with a *valid* suggested department (registered via
     `self._departments.get()`, has at least one agent, not already attempted in this call),
     attempt 2 retries at that department. Any other reject condition (no suggestion, invalid
     suggestion, or reject on attempt 2) writes a Decision Record + a `DEPARTMENT_REJECTED`
     Escalation Record and raises `DepartmentRejectedError(verdict.reasoning)`. An exception raised
     by `self._head.evaluate(...)` itself is caught, written as a Decision Record +
     `TECHNICAL_FAILURE` escalation (`is_technical_failure=True`), and re-raised - mirroring the
     existing classifier-failure handling earlier in `receive_objective()`.

3. **`Tests/integration/test_department_head_triage_single.py`** - created exactly as given in the
   brief: 7 test cases covering accept-on-first-attempt, reject-then-accept-on-retry,
   reject-reject-exhausts-cap, reject-with-no-suggestion, reject-with-hallucinated-suggestion,
   reject-with-already-attempted-suggestion, and head-call-failure-writes-technical-failure.

Before editing, I read the current contents of both target files and confirmed they matched the
brief's "before" blocks exactly (no drift), so all edits were applied precisely as specified with
no adaptation needed.

## Test commands run and output

**Step 2 (pre-change, expected failure):**
```
python -m pytest Tests/integration/test_department_head_triage_single.py -v
```
Result: collection error - `ImportError: cannot import name 'DepartmentRejectedError' from
'orchestrator.controller'` - confirms the test file fails for the expected reason before any
implementation changes.

**Step 5 (post-change, focused suite):**
```
python -m pytest Tests/integration/test_department_head_triage_single.py -v
```
Result: **7 passed** in 0.95s - all of
`test_accept_on_first_attempt_proceeds_normally`,
`test_reject_then_accept_at_suggested_department_succeeds_on_second_attempt`,
`test_reject_reject_exhausts_the_cap_and_raises`,
`test_reject_with_no_suggestion_raises_immediately_without_a_second_attempt`,
`test_reject_with_hallucinated_suggestion_is_treated_as_no_suggestion`,
`test_reject_with_already_attempted_suggestion_is_treated_as_no_suggestion`,
`test_head_call_failure_writes_technical_failure_escalation_then_reraises`.

**Step 6 (full suite):**
```
python -m pytest Tests/ -q
```
Result: **261 passed, 4 skipped** in 12.62s. Zero failures. The 4 skips are pre-existing and
unrelated to this change. Confirmed by name that
`Tests/integration/test_coo_orchestration.py`, `Tests/integration/test_workflow_orchestration.py`,
`Tests/integration/test_classifier_failure_escalation.py`, and
`Tests/integration/test_escalation_policy.py` all ran and passed unmodified, since
`AutoAcceptDepartmentHead` (the default) always accepts on the first attempt and adds zero calls.

## Files changed

- `services/orchestrator/escalation.py` (modified)
- `services/orchestrator/controller.py` (modified)
- `Tests/integration/test_department_head_triage_single.py` (new)

Diff stats: 3 files changed, 286 insertions(+), 6 deletions(-).

Commit: `647fa2e` - "feat: wire Department Head triage into the single-department objective path"
on branch `feature/department-head-triage`. Only the 3 files above were staged (`git add
services/orchestrator/escalation.py services/orchestrator/controller.py
Tests/integration/test_department_head_triage_single.py`); the pre-existing unrelated uncommitted
changes in the working tree (`CHANGELOG.md`, `IMPLEMENTATION_PLAN.md`, `ruvector.db`, `sdk/*`,
`services/compliance_service/*`, `services/observability_service/alerting.py`,
`services/workflow_engine/*`) were left untouched and unstaged, as instructed.

## Self-review findings

Checked against the brief's checklist:

- **Completeness**: `DepartmentRejectedError` added; `head` kwarg added with correct default
  (`AutoAcceptDepartmentHead()`); `_triage_single_department()` implements the full 2-attempt
  retry with correct validation of the suggested department (must be `self._departments.get(...)
  is not None`, must have `bool(suggested.agents)`, must not be in `attempted_ids`);
  `DEPARTMENT_REJECTED` added to both `EscalationCondition` and `FRAMEWORK_CONDITIONS`.
- **Quality**: the head-call try/except block mirrors the existing classifier-failure pattern
  already in `receive_objective()` - same Decision Record + `TECHNICAL_FAILURE` escalation +
  re-raise shape.
- **Discipline**: diffed the final files against the brief's exact before/after blocks - no
  deviation, nothing added beyond what the brief specified. `services/workflow_engine/engine.py`
  was not touched (confirmed via `git status` - it shows as pre-existing unstaged modification
  from other work, untouched by this task).
- **Testing**: all 7 new test cases pass; full suite has zero regressions (261 passed / 4 skipped,
  same skip count as baseline behavior would predict since `AutoAcceptDepartmentHead` changes
  nothing for existing callers).

No findings requiring changes. No issues or concerns.
