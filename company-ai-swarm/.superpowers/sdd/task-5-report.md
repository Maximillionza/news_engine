# Task 5 Report: API layer wiring for Department Head Triage

## What I implemented

Applied the brief's Steps 3-4 verbatim to `apps/api_gateway/main.py` and `apps/api_gateway/dashboard_api.py`, and added the brief's Step 1 test cases (appended, not rewritten) to `Tests/integration/test_api_gateway_objectives.py` and `Tests/integration/test_api_gateway_dashboard.py`.

### apps/api_gateway/main.py
- Import line for `orchestrator.controller` expanded to a multi-line import adding `DepartmentRejectedError`; added `from orchestrator.head import create_head_from_env`.
- `_coo = COOOrchestrator(...)` construction now passes `head=create_head_from_env()` (with the brief's exact comment referencing `DEPARTMENT_HEAD_TRIAGE` env var and the design doc).
- `submit_objective()`'s try/except now also catches `DepartmentRejectedError` and raises `HTTPException(400, "Every department rejected this objective: ...")`, mirroring the existing `NoMatchingDepartmentError` handling.
- Verified `COOOrchestrator.__init__` (services/orchestrator/controller.py:110-120) accepts a keyword-only `head: DepartmentHead = AutoAcceptDepartmentHead()` parameter, so the wiring is a straightforward substitution of the default with the env-configured head.
- No bootstrap code added for head agents. Confirmed `_bootstrap_identities()`'s existing `for agent in _agent_registry.all(): ...` loop (main.py, unchanged) already grants every registered agent - including the 4 head agents from Task 2, since they're loaded by the pre-existing `_agent_registry.load_all()` call - the `agent_execution:<id> execute` and `memory:department read/write` grants they need. Zero further code required there, as the brief noted.

### apps/api_gateway/dashboard_api.py
- Import line expanded: `from orchestrator.controller import DepartmentRejectedError, NoMatchingDepartmentError`.
- `_run_objective_and_format_reply()`'s except chain now also catches `DepartmentRejectedError`, returning `{"reply": f"Every department rejected that objective: {exc}", "decision_id": None}` - the same normal-reply treatment given to `NoMatchingDepartmentError`, so both the async queue-worker path (`build_queue_handler`) and the synchronous `/chat/sync` path complete the objective rather than erroring.

### Tests
- Appended `test_submit_objective_with_department_rejection_returns_400` to `Tests/integration/test_api_gateway_objectives.py` - swaps `main._coo._head` for an always-reject stub head, hits `POST /objectives`, asserts 400.
- Appended `test_chat_sync_department_rejection_is_a_normal_reply_not_an_error` to `Tests/integration/test_api_gateway_dashboard.py` - same stub-head swap, hits `POST /chat/sync`, asserts 200 with `decision_id is None` and "rejected" in the reply text.

Both test additions use exactly the code given in the brief's Step 1, appended after the last existing test in each file (no rewrite of existing content).

## Test commands and output

Focused run:
```
python -m pytest Tests/integration/test_api_gateway_objectives.py Tests/integration/test_api_gateway_dashboard.py -v
```
Result: **15 passed** (13 pre-existing + 2 new), 1 unrelated deprecation warning (httpx/starlette TestClient), 2.49s.

Full suite:
```
python -m pytest Tests/ -q
```
Result: **265 passed, 4 skipped**, 19.23s. The 4 skips are pre-existing and unrelated to this change (not investigated further, out of scope for Task 5).

## Files changed

- `C:\Users\Masoodt\Documents\Claude\Projects\company-ai-swarm\apps\api_gateway\main.py`
- `C:\Users\Masoodt\Documents\Claude\Projects\company-ai-swarm\apps\api_gateway\dashboard_api.py`
- `C:\Users\Masoodt\Documents\Claude\Projects\company-ai-swarm\Tests\integration\test_api_gateway_objectives.py`
- `C:\Users\Masoodt\Documents\Claude\Projects\company-ai-swarm\Tests\integration\test_api_gateway_dashboard.py`

Commit: `4ac0c8e` "feat: wire Department Head triage through every API Gateway entry point" - `git show --stat` confirms only these 4 files changed (62 insertions, 2 deletions), nothing else staged despite numerous unrelated pre-existing modified/untracked files in the working tree (CHANGELOG.md, IMPLEMENTATION_PLAN.md, ruvector.db, sdk/*, services/compliance_service/*, services/observability_service/alerting.py, services/workflow_engine/*, .claude/worktrees/, .superpowers/, a new Documentation/plans/ file) - all correctly left unstaged.

## Self-review findings

- **Completeness**: `head=create_head_from_env()` wired into `_coo` construction (main.py); `DepartmentRejectedError` imported and caught as HTTPException 400 in `POST /objectives` (main.py); `DepartmentRejectedError` imported and caught in `dashboard_api._run_objective_and_format_reply` returning a normal reply with `decision_id: None` (dashboard_api.py). All confirmed present via `git show HEAD` diff review.
- **Quality**: No redundant permission-bootstrap code added for head agents - `_bootstrap_identities()` left untouched, verified its generic `for agent in _agent_registry.all(): ...` loop already covers them since `AgentRegistry.load_all()` (unmodified, pre-existing) loads all agents including the 4 head agents from Task 2.
- **Discipline**: Diff scope verified via `git diff --stat` against exactly the 4 named files before staging; nothing beyond the brief's before/after blocks was touched. Import ordering follows the brief literally (head import placed between `orchestrator.decisions` and `orchestrator.department_registry` imports, as the brief's snippet shows) rather than alphabetized - a cosmetic isort deviation already present in the brief itself, not introduced by me.
- **Testing**: Both new tests pass individually and as part of the full suite; full suite shows zero regressions (265 passed, 4 pre-existing skips, same skip count as before this change per the task history's established baseline).

## Concerns

None. Every before/after block in the brief matched the real file content exactly on first read - no guessing was required. `HeadVerdict`, `create_head_from_env`, `DepartmentRejectedError`, and `COOOrchestrator`'s `head` keyword argument were all verified present in `services/orchestrator/head.py` and `services/orchestrator/controller.py` before editing.
