### Task 5: API layer wiring

**Files:**
- Modify: `apps/api_gateway/main.py`
- Modify: `apps/api_gateway/dashboard_api.py`
- Modify: `Tests/integration/test_api_gateway_objectives.py`
- Modify: `Tests/integration/test_api_gateway_dashboard.py`

**Interfaces:**
- Consumes: `orchestrator.head.create_head_from_env` (Task 1); `orchestrator.controller.
  DepartmentRejectedError` (Task 3).
- Produces: every entry point (`POST /chat`, `POST /chat/sync`, `POST /objectives`) gated by
  the same `head=create_head_from_env()`-configured triage, since all three call the single
  module-level `_coo.receive_objective()`.

- [ ] **Step 1: Write the failing tests**

Append to `Tests/integration/test_api_gateway_objectives.py`:

```python
def test_submit_objective_with_department_rejection_returns_400() -> None:
    from orchestrator.head import HeadVerdict

    class _AlwaysRejectHead:
        def evaluate(self, department, objective, **_):
            return HeadVerdict(accepted=False, reasoning="Rejected for test.", suggested_department_id=None)

    from main import _coo

    original_head = _coo._head
    _coo._head = _AlwaysRejectHead()
    try:
        response = client.post(
            "/objectives",
            headers=HEADERS,
            json={"objective": "Create a market intelligence report", "required_output": "A structured summary"},
        )
        assert response.status_code == 400
    finally:
        _coo._head = original_head
```

Append to `Tests/integration/test_api_gateway_dashboard.py`:

```python
def test_chat_sync_department_rejection_is_a_normal_reply_not_an_error() -> None:
    from orchestrator.head import HeadVerdict

    class _AlwaysRejectHead:
        def evaluate(self, department, objective, **_):
            return HeadVerdict(accepted=False, reasoning="Rejected for test.", suggested_department_id=None)

    original_head = gateway_main._coo._head
    gateway_main._coo._head = _AlwaysRejectHead()
    try:
        response = _client().post(
            "/chat/sync", headers=HEADERS, json={"message": "Research current market trends."}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["decision_id"] is None
        assert "rejected" in body["reply"].lower()
    finally:
        gateway_main._coo._head = original_head
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest Tests/integration/test_api_gateway_objectives.py Tests/integration/test_api_gateway_dashboard.py -v -k department_rejection`
Expected: FAIL - `POST /objectives` returns 500 (unhandled `DepartmentRejectedError`), and
`/chat/sync` also 500s

- [ ] **Step 3: Wire `head` and `DepartmentRejectedError` into `apps/api_gateway/main.py`**

Replace the import line:

```python
from orchestrator.controller import COOOrchestrator, NoMatchingDepartmentError, WorkflowObjectiveOutcome
```

with:

```python
from orchestrator.controller import (
    COOOrchestrator,
    DepartmentRejectedError,
    NoMatchingDepartmentError,
    WorkflowObjectiveOutcome,
)
from orchestrator.head import create_head_from_env
```

Replace the `_coo` construction:

```python
_coo = COOOrchestrator(
    coo_id="coo",
    department_registry=_department_registry,
    agent_registry=_agent_registry,
    model_gateway=_model_gateway,
    telemetry=_telemetry,
    # DEPARTMENT_CLASSIFIER env var selects keyword (default, no credentials) / llm (real
    # Claude-backed routing) - see orchestrator/classification.py and Documentation/plans/
    # 2026-07-19-dynamic-department-routing-design.md Section 3.3.
    classifier=create_classifier_from_env(_model_gateway),
)
```

with:

```python
_coo = COOOrchestrator(
    coo_id="coo",
    department_registry=_department_registry,
    agent_registry=_agent_registry,
    model_gateway=_model_gateway,
    telemetry=_telemetry,
    # DEPARTMENT_CLASSIFIER env var selects keyword (default, no credentials) / llm (real
    # Claude-backed routing) - see orchestrator/classification.py and Documentation/plans/
    # 2026-07-19-dynamic-department-routing-design.md Section 3.3.
    classifier=create_classifier_from_env(_model_gateway),
    # DEPARTMENT_HEAD_TRIAGE env var selects auto_accept (default, no credentials) / llm
    # (real Claude-backed triage) - see orchestrator/head.py and Documentation/plans/
    # 2026-07-19-department-head-triage-design.md Section 3.2.
    head=create_head_from_env(),
)
```

In `submit_objective`, replace:

```python
    try:
        outcome = _coo.receive_objective(session, objective, required_output=required_output)
    except NoMatchingDepartmentError as exc:
        raise HTTPException(status_code=400, detail=f"No department matched this objective: {exc}") from exc
```

with:

```python
    try:
        outcome = _coo.receive_objective(session, objective, required_output=required_output)
    except NoMatchingDepartmentError as exc:
        raise HTTPException(status_code=400, detail=f"No department matched this objective: {exc}") from exc
    except DepartmentRejectedError as exc:
        raise HTTPException(status_code=400, detail=f"Every department rejected this objective: {exc}") from exc
```

Note: since the new head agent identities (`research_head_001`, etc.) are loaded into
`_agent_registry` by the unmodified `AgentRegistry.load_all()` call already present in this
file, `_bootstrap_identities()`'s existing `for agent in _agent_registry.all(): ...` loop
already grants them `agent_execution:<id> execute` and `memory:department read/write` with no
further code change - it iterates every registered agent generically.

- [ ] **Step 4: Wire `DepartmentRejectedError` into `apps/api_gateway/dashboard_api.py`**

Replace the import line:

```python
from orchestrator.controller import NoMatchingDepartmentError
```

with:

```python
from orchestrator.controller import DepartmentRejectedError, NoMatchingDepartmentError
```

In `_run_objective_and_format_reply`, replace:

```python
    except NoMatchingDepartmentError as exc:
        # Not a failure - a legitimate outcome the pre-Phase-B synchronous /chat already
        # treated as a normal (non-error) reply. Preserved here so the async path completes
        # the objective_queue row rather than failing it for the same case.
        return {"reply": f"No department matched that objective: {exc}", "decision_id": None}
```

with:

```python
    except NoMatchingDepartmentError as exc:
        # Not a failure - a legitimate outcome the pre-Phase-B synchronous /chat already
        # treated as a normal (non-error) reply. Preserved here so the async path completes
        # the objective_queue row rather than failing it for the same case.
        return {"reply": f"No department matched that objective: {exc}", "decision_id": None}
    except DepartmentRejectedError as exc:
        # Same treatment as NoMatchingDepartmentError above - a Department Head reject
        # (Documentation/plans/2026-07-19-department-head-triage-design.md) is a legitimate
        # outcome, not a technical failure.
        return {"reply": f"Every department rejected that objective: {exc}", "decision_id": None}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest Tests/integration/test_api_gateway_objectives.py Tests/integration/test_api_gateway_dashboard.py -v`
Expected: all tests PASS

- [ ] **Step 6: Run the full existing suite to confirm zero regressions**

Run: `python -m pytest Tests/ -q`
Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add apps/api_gateway/main.py apps/api_gateway/dashboard_api.py \
  Tests/integration/test_api_gateway_objectives.py Tests/integration/test_api_gateway_dashboard.py
git commit -m "feat: wire Department Head triage through every API Gateway entry point"
```

---

