# Final Whole-Branch Review Fixes — Department Head Triage

Branch: `feature/department-head-triage`
Working dir: `C:\Users\Masoodt\Documents\Claude\Projects\company-ai-swarm`

## Finding 1 (Important) — Fixed

**Problem:** `_triage_single_department()`'s `suggestion_valid` check allowed a Head-suggested
`"operations"` (the Review Department, `workflow_engine.engine.REVIEW_DEPARTMENT_ID`) to be
retried via the single-department dispatch path. Since `operations` is registered and has an
agent (`review_agent_001`), the retry would succeed and `select_agent("operations")` would
dispatch the raw objective to `review_agent_001` as primary work — reintroducing the exact
anti-pattern the Phase 8 `routes_through_workflow_engine` fix in `receive_objective()` was
built to prevent (a lone `"operations"` match must go through the multi-department workflow
engine, not straight to the Review Agent, per `review_agent/agent.yaml`'s mission: "Does not
perform the original work it reviews").

**Confirmed before fixing:**
- `REVIEW_DEPARTMENT_ID` is already imported in `controller.py` line 58:
  `from workflow_engine.engine import REVIEW_DEPARTMENT_ID, execute_workflow`
- It's already used at line 188 in `receive_objective()`'s `routes_through_workflow_engine` check.
- `departments/operations/definition.yaml` confirms `operations` is registered with
  `agents: [review_agent_001]` — i.e. without the fix, `suggestion_valid` would evaluate `True`
  for a suggested `"operations"`, making this a real, exploitable gap.

**Fix applied** in `services/orchestrator/controller.py`, `_triage_single_department`
(added one condition to `suggestion_valid`, plus an accompanying docstring note):

```python
suggestion_valid = (
    suggested is not None
    and bool(suggested.agents)
    and suggested.id not in attempted_ids
    and suggested.id != REVIEW_DEPARTMENT_ID
)
```

Docstring was also updated to document the new exclusion condition (see diff below).

**Test added** in `Tests/integration/test_department_head_triage_single.py`:
`test_reject_with_review_department_suggestion_is_treated_as_no_suggestion` — reuses the
existing `_ScriptedHead` double and `_make_coo` helper. Scripts a single verdict: reject with
`suggested_department_id="operations"`. Asserts `DepartmentRejectedError` is raised and
`head.calls == ["research"]` (only the original department was called — no second attempt at
`operations`).

## Finding 2 (Minor) — Fixed

**Problem:** CHANGELOG.md's Department Head Triage entry claimed `DepartmentRejectedError` gets
"the same normal-reply-not-HTTP-error treatment `apps/api_gateway/main.py`/`dashboard_api.py`
already give `NoMatchingDepartmentError`."

**Verified by reading both files:**
- `apps/api_gateway/main.py` lines 196-199: both `NoMatchingDepartmentError` and
  `DepartmentRejectedError` are caught and re-raised as `HTTPException(status_code=400, ...)`
  — an HTTP error response, not a normal reply.
- `apps/api_gateway/dashboard_api.py` lines 124-133: both exceptions are caught and returned as
  a normal `{"reply": ..., "decision_id": None}` dict — a non-error chat reply. The existing
  code comment even says "Same treatment as NoMatchingDepartmentError above ... a legitimate
  outcome, not a technical failure."

So the CHANGELOG's claim was wrong for `main.py` (it's an HTTP 400 error, not a normal reply) and
right only for `dashboard_api.py`.

**Fix applied** — reworded the clause in place, kept the rest of the bullet untouched:

Before:
> ... then raises `DepartmentRejectedError` - the same normal-reply-not-HTTP-error treatment
> `apps/api_gateway/main.py`/`dashboard_api.py` already give `NoMatchingDepartmentError`.

After:
> ... then raises `DepartmentRejectedError` - the same treatment `apps/api_gateway/main.py`
> (HTTP 400) and `dashboard_api.py` (a normal chat reply) already give `NoMatchingDepartmentError`.

## Test Commands and Output

### Covering tests
```
python -m pytest Tests/integration/test_department_head_triage_single.py -v
```
```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\Masoodt\Documents\Claude\Projects\company-ai-swarm
configfile: pyproject.toml
plugins: anyio-4.14.1
collecting ... collected 8 items

Tests/integration/test_department_head_triage_single.py::test_accept_on_first_attempt_proceeds_normally PASSED [ 12%]
Tests/integration/test_department_head_triage_single.py::test_reject_then_accept_at_suggested_department_succeeds_on_second_attempt PASSED [ 25%]
Tests/integration/test_department_head_triage_single.py::test_reject_reject_exhausts_the_cap_and_raises PASSED [ 37%]
Tests/integration/test_department_head_triage_single.py::test_reject_with_no_suggestion_raises_immediately_without_a_second_attempt PASSED [ 50%]
Tests/integration/test_department_head_triage_single.py::test_reject_with_hallucinated_suggestion_is_treated_as_no_suggestion PASSED [ 62%]
Tests/integration/test_department_head_triage_single.py::test_reject_with_already_attempted_suggestion_is_treated_as_no_suggestion PASSED [ 75%]
Tests/integration/test_department_head_triage_single.py::test_reject_with_review_department_suggestion_is_treated_as_no_suggestion PASSED [ 87%]
Tests/integration/test_department_head_triage_single.py::test_head_call_failure_writes_technical_failure_escalation_then_reraises PASSED [100%]

============================== 8 passed in 2.26s ==============================
```

### Full suite (regression check)
```
python -m pytest Tests/ -q
```
```
...........................s.......s.................................... [ 26%]
.................................s...................................... [ 53%]
..............s......................................................... [ 80%]
......................................................                   [100%]
266 passed, 4 skipped, 1 warning in 12.25s
```
(4 skips are pre-existing, unrelated to this change.)

## Files Changed

- `services/orchestrator/controller.py` — added the `REVIEW_DEPARTMENT_ID` exclusion condition
  to `suggestion_valid` in `_triage_single_department`; updated the method's docstring.
- `Tests/integration/test_department_head_triage_single.py` — added
  `test_reject_with_review_department_suggestion_is_treated_as_no_suggestion`.
- `CHANGELOG.md` — corrected the `main.py`/`dashboard_api.py` error-handling description in the
  Department Head Triage entry.

## Concerns

None. Both findings were verified against the actual source before editing (import present,
constant used elsewhere, `operations` department genuinely registered with an agent so the test
is meaningful; both gateway files read directly to confirm the accurate wording). Scope was kept
to exactly the three files specified; no restructuring beyond the one added condition.
