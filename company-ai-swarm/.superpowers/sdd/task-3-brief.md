### Task 3: Single-department triage wiring in `orchestrator/controller.py`

**Files:**
- Modify: `services/orchestrator/escalation.py`
- Modify: `services/orchestrator/controller.py`
- Test: `Tests/integration/test_department_head_triage_single.py`

**Interfaces:**
- Consumes: `orchestrator.head.DepartmentHead`/`HeadVerdict`/`AutoAcceptDepartmentHead` (Task 1).
- Produces: `EscalationCondition.DEPARTMENT_REJECTED`; `orchestrator.controller.
  DepartmentRejectedError`; `COOOrchestrator.__init__`'s new `head: DepartmentHead =
  AutoAcceptDepartmentHead()` kwarg (stored as `self._head`); `COOOrchestrator.
  _triage_single_department(...)`. Task 4/5 reuse `EscalationCondition.DEPARTMENT_REJECTED`
  and `DepartmentRejectedError`.

- [ ] **Step 1: Write the failing tests**

Create `Tests/integration/test_department_head_triage_single.py`:

```python
"""Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.1's
single-department path: up to 2 attempts total, then DepartmentRejectedError. Uses a
scripted test double implementing orchestrator.head.DepartmentHead, not a real dispatch() -
Task 1's test_department_head.py already covers LLMDepartmentHead's own JSON parsing in
isolation; this file covers COOOrchestrator's retry/validation logic around whatever verdict
a DepartmentHead returns.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetrySink
from orchestrator.controller import COOOrchestrator, DepartmentRejectedError, ObjectiveOutcome
from orchestrator.department_registry import DepartmentRegistry
from orchestrator.escalation import EscalationCondition
from orchestrator.escalations import list_pending_escalations
from orchestrator.head import HeadVerdict
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]

OBJECTIVE = "Create a market intelligence report"


class _ScriptedHead:
    """Returns one scripted verdict per call, in order. Raises if called more times than
    scripted - a test bug, not swallowed."""

    def __init__(self, verdicts: list[HeadVerdict]) -> None:
        self._verdicts = list(verdicts)
        self.calls: list[str] = []

    def evaluate(self, department, objective, **_):
        self.calls.append(department.id)
        return self._verdicts.pop(0)


class _RaisingHead:
    def evaluate(self, department, objective, **_):
        raise RuntimeError("head service unavailable")


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


def _make_coo(session: Session, *, head) -> COOOrchestrator:
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()
    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    _grant(session, "research_agent_001", "research")
    _grant(session, "engineering_agent_001", "engineering")

    telemetry = TelemetrySink()
    return COOOrchestrator(
        coo_id="coo",
        department_registry=department_registry,
        agent_registry=agent_registry,
        model_gateway=ModelGateway(StubModelProvider(), telemetry=telemetry),
        telemetry=telemetry,
        head=head,
    )


def test_accept_on_first_attempt_proceeds_normally(session: Session) -> None:
    head = _ScriptedHead([HeadVerdict(accepted=True, reasoning="Fits research.")])
    coo = _make_coo(session, head=head)

    outcome = coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert isinstance(outcome, ObjectiveOutcome)
    assert outcome.task_profile.matched_department.id == "research"
    assert head.calls == ["research"]


def test_reject_then_accept_at_suggested_department_succeeds_on_second_attempt(session: Session) -> None:
    head = _ScriptedHead(
        [
            HeadVerdict(accepted=False, reasoning="Not research.", suggested_department_id="engineering"),
            HeadVerdict(accepted=True, reasoning="Fits engineering."),
        ]
    )
    coo = _make_coo(session, head=head)

    outcome = coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert isinstance(outcome, ObjectiveOutcome)
    assert outcome.task_profile.matched_department.id == "engineering"
    assert head.calls == ["research", "engineering"]


def test_reject_reject_exhausts_the_cap_and_raises(session: Session) -> None:
    head = _ScriptedHead(
        [
            HeadVerdict(accepted=False, reasoning="Not research.", suggested_department_id="engineering"),
            HeadVerdict(accepted=False, reasoning="Not engineering either.", suggested_department_id=None),
        ]
    )
    coo = _make_coo(session, head=head)

    with pytest.raises(DepartmentRejectedError, match="Not engineering either"):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert head.calls == ["research", "engineering"]
    pending = list_pending_escalations(session)
    assert len(pending) == 1
    assert pending[0].condition == EscalationCondition.DEPARTMENT_REJECTED.value


def test_reject_with_no_suggestion_raises_immediately_without_a_second_attempt(session: Session) -> None:
    head = _ScriptedHead([HeadVerdict(accepted=False, reasoning="Not worth it.", suggested_department_id=None)])
    coo = _make_coo(session, head=head)

    with pytest.raises(DepartmentRejectedError, match="Not worth it"):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert head.calls == ["research"]


def test_reject_with_hallucinated_suggestion_is_treated_as_no_suggestion(session: Session) -> None:
    head = _ScriptedHead(
        [HeadVerdict(accepted=False, reasoning="Not research.", suggested_department_id="made_up_department")]
    )
    coo = _make_coo(session, head=head)

    with pytest.raises(DepartmentRejectedError):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert head.calls == ["research"]


def test_reject_with_already_attempted_suggestion_is_treated_as_no_suggestion(session: Session) -> None:
    head = _ScriptedHead(
        [HeadVerdict(accepted=False, reasoning="Circular suggestion.", suggested_department_id="research")]
    )
    coo = _make_coo(session, head=head)

    with pytest.raises(DepartmentRejectedError):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    assert head.calls == ["research"]


def test_head_call_failure_writes_technical_failure_escalation_then_reraises(session: Session) -> None:
    coo = _make_coo(session, head=_RaisingHead())

    with pytest.raises(RuntimeError, match="head service unavailable"):
        coo.receive_objective(session, OBJECTIVE, required_output="A structured summary")

    pending = list_pending_escalations(session)
    assert len(pending) == 1
    assert pending[0].condition == EscalationCondition.TECHNICAL_FAILURE.value
    assert pending[0].is_technical_failure is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest Tests/integration/test_department_head_triage_single.py -v`
Expected: FAIL - `COOOrchestrator.__init__()` has no `head` parameter yet

- [ ] **Step 3: Add `DEPARTMENT_REJECTED` to `orchestrator/escalation.py`**

Replace the whole file's contents with:

```python
"""Five-condition escalation policy (ESTAS sec.10 Risk Assessment substitute).

Source: IMPLEMENTATION_PLAN.md Phase 8, adopted (by explicit user decision, see
Documentation/operations/technology_decisions.md) from an external swarm review in place of
inventing a numeric risk/complexity score for COOS sec.9 - no such algorithm exists anywhere
in the source corpus (orchestrator/planner.py's docstring made this point originally; the
same fixed-default honesty note now lives in orchestrator/controller.py, see also
Documentation/operations/technology_decisions.md). The COO escalates to a human
- and only a human - when one of exactly five named conditions fires; everything else it
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
  5. DEPARTMENT_REJECTED - a Department Head (Documentation/plans/
     2026-07-19-department-head-triage-design.md, DOMS sec.8-9) rejected the objective and no
     valid alternative department remained to try - either the single-department retry cap
     (2 attempts) was reached in orchestrator.controller.COOOrchestrator._triage_single_department,
     or a Head rejected mid-workflow in workflow_engine/engine.py's execute_workflow().

A technical failure (an unhandled exception during dispatch - agent runtime error, Model
Gateway failure, or anything else not one of the five cases above) always escalates too, but
is logged as TECHNICAL_FAILURE, distinct from the five framework verdicts - never conflated
with them in the Escalation Record.
"""

from __future__ import annotations

import enum


class EscalationCondition(str, enum.Enum):
    NO_MATCHING_DEPARTMENT = "no_matching_department"
    OUTCOME_NOT_ACHIEVED = "outcome_not_achieved"
    GATE_INTEGRITY_SUPERFICIAL = "gate_integrity_superficial"
    UNRESOLVABLE_DEPENDENCY_GAP = "unresolvable_dependency_gap"
    DEPARTMENT_REJECTED = "department_rejected"
    TECHNICAL_FAILURE = "technical_failure"


FRAMEWORK_CONDITIONS = (
    EscalationCondition.NO_MATCHING_DEPARTMENT,
    EscalationCondition.OUTCOME_NOT_ACHIEVED,
    EscalationCondition.GATE_INTEGRITY_SUPERFICIAL,
    EscalationCondition.UNRESOLVABLE_DEPENDENCY_GAP,
    EscalationCondition.DEPARTMENT_REJECTED,
)
```

- [ ] **Step 4: Wire triage into `orchestrator/controller.py`**

Add to the imports (after `from orchestrator.evaluator import OutcomeValidation, validate_outcome`):

```python
from orchestrator.head import AutoAcceptDepartmentHead, DepartmentHead
```

Add `DepartmentRejectedError` right after `NoMatchingDepartmentError`'s definition:

```python
class NoMatchingDepartmentError(Exception):
    pass


class DepartmentRejectedError(Exception):
    pass
```

In `COOOrchestrator.__init__`, replace:

```python
    def __init__(
        self,
        *,
        coo_id: str,
        department_registry: DepartmentRegistry,
        agent_registry: AgentRegistry,
        model_gateway: ModelGateway,
        telemetry: TelemetrySink | None = None,
        classifier: DepartmentClassifier = KeywordDepartmentClassifier(),
    ) -> None:
        self.coo_id = coo_id
        self._departments = department_registry
        self._agents = agent_registry
        self._model_gateway = model_gateway
        self._telemetry = telemetry
        self._classifier = classifier
```

with:

```python
    def __init__(
        self,
        *,
        coo_id: str,
        department_registry: DepartmentRegistry,
        agent_registry: AgentRegistry,
        model_gateway: ModelGateway,
        telemetry: TelemetrySink | None = None,
        classifier: DepartmentClassifier = KeywordDepartmentClassifier(),
        head: DepartmentHead = AutoAcceptDepartmentHead(),
    ) -> None:
        self.coo_id = coo_id
        self._departments = department_registry
        self._agents = agent_registry
        self._model_gateway = model_gateway
        self._telemetry = telemetry
        self._classifier = classifier
        self._head = head
```

In `receive_objective()`, replace:

```python
        task_profile = TaskProfile(
            task_id=f"TSK-{uuid4().hex[:8]}",
            objective=objective,
            # Fixed default - real complexity scoring is deferred (design doc Section 2);
            # unchanged from orchestrator/planner.py's original placeholder.
            complexity_level="Level 2 Standard",
            matched_department=matched_departments[0],
            reasoning=classification.reasoning,
        )

        # Select Agents
        allocation = select_agent(task_profile.matched_department, self._agents)
```

with:

```python
        department = self._triage_single_department(
            session, objective, decision_id=decision_id, initial_department=matched_departments[0]
        )

        task_profile = TaskProfile(
            task_id=f"TSK-{uuid4().hex[:8]}",
            objective=objective,
            # Fixed default - real complexity scoring is deferred (design doc Section 2);
            # unchanged from orchestrator/planner.py's original placeholder.
            complexity_level="Level 2 Standard",
            matched_department=department,
            reasoning=classification.reasoning,
        )

        # Select Agents
        allocation = select_agent(task_profile.matched_department, self._agents)
```

Add a new method, immediately after `receive_objective()` and before `_receive_multi_department_objective()`:

```python
    def _triage_single_department(
        self,
        session: Session,
        objective: str,
        *,
        decision_id: str,
        initial_department: DepartmentDefinition,
    ) -> DepartmentDefinition:
        """Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.1's
        single-department path: up to 2 attempts total - the classifier's original match,
        then (if rejected with a valid suggested department) one retry at that department. A
        suggested department is valid only if it is registered and has at least one
        dispatchable agent (mirrors KeywordDepartmentClassifier's own exclusion of agentless
        departments) and has not already been attempted in this call. Mirrors
        NoMatchingDepartmentError's pattern on terminal reject: a Decision Record and a
        DEPARTMENT_REJECTED Escalation Record before raising."""

        attempted_ids: set[str] = set()
        department = initial_department

        for attempt in (1, 2):
            attempted_ids.add(department.id)
            try:
                verdict = self._head.evaluate(
                    department,
                    objective,
                    agent_registry=self._agents,
                    model_gateway=self._model_gateway,
                    session=session,
                    coo_id=self.coo_id,
                    telemetry=self._telemetry,
                )
            except Exception as exc:
                # Same audit trail any other technical failure gets - mirrors the classifier
                # failure handling above in receive_objective().
                decisions.write_decision(
                    session,
                    id=decision_id,
                    objective=objective,
                    reasoning=f"Department Head triage failed: {type(exc).__name__}: {exc}",
                    chosen_action="reject: triage failed",
                )
                escalations.write_escalation(
                    session,
                    condition=EscalationCondition.TECHNICAL_FAILURE,
                    reasoning=f"{type(exc).__name__}: {exc}",
                    decision_id=decision_id,
                    is_technical_failure=True,
                )
                raise

            if verdict.accepted:
                return department

            suggested = (
                self._departments.get(verdict.suggested_department_id)
                if verdict.suggested_department_id
                else None
            )
            suggestion_valid = (
                suggested is not None
                and bool(suggested.agents)
                and suggested.id not in attempted_ids
            )

            if attempt == 2 or not suggestion_valid:
                decisions.write_decision(
                    session,
                    id=decision_id,
                    objective=objective,
                    reasoning=verdict.reasoning,
                    chosen_action=f"reject: department head rejected ({department.id})",
                )
                escalations.write_escalation(
                    session,
                    condition=EscalationCondition.DEPARTMENT_REJECTED,
                    reasoning=verdict.reasoning,
                    decision_id=decision_id,
                )
                raise DepartmentRejectedError(verdict.reasoning)

            department = suggested

        raise AssertionError("unreachable: loop must return or raise within 2 attempts")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest Tests/integration/test_department_head_triage_single.py -v`
Expected: all tests PASS

- [ ] **Step 6: Run the full existing suite to confirm zero regressions**

Run: `python -m pytest Tests/ -q`
Expected: all tests PASS, including `Tests/integration/test_coo_orchestration.py`,
`Tests/integration/test_workflow_orchestration.py`, `Tests/integration/
test_classifier_failure_escalation.py`, and `Tests/integration/test_escalation_policy.py`
unmodified (`AutoAcceptDepartmentHead` is the default and always accepts on the first
attempt)

- [ ] **Step 7: Commit**

```bash
git add services/orchestrator/escalation.py services/orchestrator/controller.py \
  Tests/integration/test_department_head_triage_single.py
git commit -m "feat: wire Department Head triage into the single-department objective path"
```

---

