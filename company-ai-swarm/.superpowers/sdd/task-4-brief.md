### Task 4: Multi-department triage wiring in `workflow_engine/engine.py`

**Files:**
- Modify: `services/workflow_engine/engine.py`
- Modify: `services/orchestrator/controller.py`
- Test: `Tests/integration/test_department_head_triage_workflow.py`

**Interfaces:**
- Consumes: `orchestrator.head.DepartmentHead`/`HeadVerdict`/`AutoAcceptDepartmentHead` (Task
  1); `EscalationCondition.DEPARTMENT_REJECTED` (Task 3).
- Produces: `execute_workflow(..., head: DepartmentHead = AutoAcceptDepartmentHead())`;
  `WorkflowRun.blocked_reason` prefixed `"department_rejected: "` on a mid-workflow reject;
  `COOOrchestrator._receive_multi_department_objective` maps that prefix to
  `EscalationCondition.DEPARTMENT_REJECTED` instead of `UNRESOLVABLE_DEPENDENCY_GAP`.

- [ ] **Step 1: Write the failing tests**

Create `Tests/integration/test_department_head_triage_workflow.py`:

```python
"""Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.5's
multi-department path: each substantive department's Head evaluates immediately before that
department's select_agent()+dispatch(). A reject halts forward progress the same way a failed
validation already does - no rollback, no reassignment.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, WorkflowObjectiveOutcome
from orchestrator.department_registry import DepartmentRegistry
from orchestrator.escalation import EscalationCondition
from orchestrator.escalations import list_pending_escalations
from orchestrator.head import HeadVerdict
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider
from workflow_engine.engine import execute_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]

TWO_DEPARTMENT_OBJECTIVE = "Research market analysis and build working software"


class _RejectSecondDepartmentHead:
    """Accepts the first department it's asked about, rejects every one after that - proves
    the halt happens mid-sequence, not before the first task runs."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def evaluate(self, department, objective, **_):
        self.calls.append(department.id)
        if len(self.calls) == 1:
            return HeadVerdict(accepted=True, reasoning="First department is fine.")
        return HeadVerdict(accepted=False, reasoning="Second department rejected.", suggested_department_id=None)


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def _grant(session: Session, agent_id: str, department: str) -> None:
    create_identity(session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id, department=department)
    grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
    grant_permission(session, subject=agent_id, resource="memory:department", action="read")


def _registries() -> tuple[DepartmentRegistry, AgentRegistry]:
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()
    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()
    return department_registry, agent_registry


def test_execute_workflow_halts_when_a_substantive_departments_head_rejects(session: Session) -> None:
    department_registry, agent_registry = _registries()
    _grant(session, "research_agent_001", "research")
    _grant(session, "engineering_agent_001", "engineering")
    head = _RejectSecondDepartmentHead()

    run = execute_workflow(
        session,
        coo_id="coo",
        objective=TWO_DEPARTMENT_OBJECTIVE,
        required_output="working code with a supporting summary",
        departments=[department_registry.get("research"), department_registry.get("engineering")],
        agent_registry=agent_registry,
        model_gateway=ModelGateway(StubModelProvider()),
        head=head,
    )

    assert run.succeeded is False
    assert run.blocked_reason is not None
    assert run.blocked_reason.startswith("department_rejected:")
    assert "Second department rejected" in run.blocked_reason
    # Earlier task is present and untouched - no rollback.
    assert len(run.tasks) == 1
    assert run.tasks[0].department.id == "research"
    assert head.calls == ["research", "engineering"]


def test_receive_objective_maps_the_reject_to_department_rejected_not_dependency_gap(session: Session) -> None:
    department_registry, agent_registry = _registries()
    _grant(session, "research_agent_001", "research")
    _grant(session, "engineering_agent_001", "engineering")
    telemetry = TelemetrySink()

    coo = COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=ModelGateway(StubModelProvider(), telemetry=telemetry),
        telemetry=telemetry,
        head=_RejectSecondDepartmentHead(),
    )

    outcome = coo.receive_objective(
        session, TWO_DEPARTMENT_OBJECTIVE, required_output="working code with a supporting summary"
    )

    assert isinstance(outcome, WorkflowObjectiveOutcome)
    assert outcome.workflow.succeeded is False

    pending = list_pending_escalations(session)
    conditions = [p.condition for p in pending]
    assert EscalationCondition.DEPARTMENT_REJECTED.value in conditions
    assert EscalationCondition.UNRESOLVABLE_DEPENDENCY_GAP.value not in conditions
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest Tests/integration/test_department_head_triage_workflow.py -v`
Expected: FAIL - `execute_workflow()` has no `head` parameter yet

- [ ] **Step 3: Wire triage into `workflow_engine/engine.py`**

Add to the imports (after `from orchestrator.evaluator import validate_outcome`):

```python
from orchestrator.head import AutoAcceptDepartmentHead, DepartmentHead
```

Replace the `execute_workflow` signature:

```python
def execute_workflow(
    session: Session,
    *,
    coo_id: str,
    objective: str,
    required_output: str,
    departments: list[DepartmentDefinition],
    agent_registry: AgentRegistry,
    model_gateway: ModelGateway,
    telemetry: TelemetrySink | None = None,
    complexity_level: str = "Level 2 Standard",
) -> WorkflowRun:
```

with:

```python
def execute_workflow(
    session: Session,
    *,
    coo_id: str,
    objective: str,
    required_output: str,
    departments: list[DepartmentDefinition],
    agent_registry: AgentRegistry,
    model_gateway: ModelGateway,
    telemetry: TelemetrySink | None = None,
    complexity_level: str = "Level 2 Standard",
    head: DepartmentHead = AutoAcceptDepartmentHead(),
) -> WorkflowRun:
```

Replace the substantive-departments loop:

```python
    for department in substantive_departments:
        try:
            allocation = select_agent(department, agent_registry)
        except ValueError as exc:
            run.succeeded = False
            run.blocked_reason = f"unresolvable_dependency_gap: {exc}"
            return run
```

with:

```python
    for department in substantive_departments:
        verdict = head.evaluate(
            department,
            objective,
            agent_registry=agent_registry,
            model_gateway=model_gateway,
            session=session,
            coo_id=coo_id,
            telemetry=telemetry,
        )
        if not verdict.accepted:
            run.succeeded = False
            run.blocked_reason = f"department_rejected: {verdict.reasoning}"
            return run

        try:
            allocation = select_agent(department, agent_registry)
        except ValueError as exc:
            run.succeeded = False
            run.blocked_reason = f"unresolvable_dependency_gap: {exc}"
            return run
```

Also update the module docstring's Phase 8 paragraph - after the existing paragraph ending
"...this module reports facts, the governance layer above decides what to do with them.",
add a new paragraph:

```
Department Head Triage addition (Documentation/plans/
2026-07-19-department-head-triage-design.md): each substantive department's Head
(orchestrator/head.py) evaluates the objective immediately before that department's
select_agent()+dispatch() - a reject halts forward progress the same way the missing-agent
case above already does (blocked_reason set, no rollback, no reassignment attempted
mid-workflow), distinguished by a "department_rejected:" prefix instead of
"unresolvable_dependency_gap:" so the caller can classify it correctly. The review step is
not triaged - Section 2 of the design doc scopes triage to substantive departments only.
```

- [ ] **Step 4: Wire `head` through `orchestrator/controller.py`'s multi-department path**

In `_receive_multi_department_objective`, replace:

```python
        try:
            workflow = execute_workflow(
                session,
                coo_id=self.coo_id,
                objective=objective,
                required_output=required_output,
                departments=matched_departments,
                agent_registry=self._agents,
                model_gateway=self._model_gateway,
                telemetry=self._telemetry,
            )
        except Exception as exc:
```

with:

```python
        try:
            workflow = execute_workflow(
                session,
                coo_id=self.coo_id,
                objective=objective,
                required_output=required_output,
                departments=matched_departments,
                agent_registry=self._agents,
                model_gateway=self._model_gateway,
                telemetry=self._telemetry,
                head=self._head,
            )
        except Exception as exc:
```

Replace the `blocked_reason` handling:

```python
        if workflow.blocked_reason is not None:
            escalations.write_escalation(
                session,
                condition=EscalationCondition.UNRESOLVABLE_DEPENDENCY_GAP,
                reasoning=workflow.blocked_reason,
                decision_id=decision_id,
            )
        elif not workflow.succeeded:
```

with:

```python
        if workflow.blocked_reason is not None:
            condition = (
                EscalationCondition.DEPARTMENT_REJECTED
                if workflow.blocked_reason.startswith("department_rejected:")
                else EscalationCondition.UNRESOLVABLE_DEPENDENCY_GAP
            )
            escalations.write_escalation(
                session,
                condition=condition,
                reasoning=workflow.blocked_reason,
                decision_id=decision_id,
            )
        elif not workflow.succeeded:
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest Tests/integration/test_department_head_triage_workflow.py -v`
Expected: all tests PASS

- [ ] **Step 6: Run the full existing suite to confirm zero regressions**

Run: `python -m pytest Tests/ -q`
Expected: all tests PASS, including `Tests/integration/test_escalation_policy.py`'s
`TestCondition4UnresolvableDependencyGap` (still reachable - a missing agent, not a Head
reject, is unaffected) and `TestCondition3GateIntegritySuperficial` (the review step is not
triaged)

- [ ] **Step 7: Commit**

```bash
git add services/workflow_engine/engine.py services/orchestrator/controller.py \
  Tests/integration/test_department_head_triage_workflow.py
git commit -m "feat: wire Department Head triage into the multi-department workflow path"
```

---

