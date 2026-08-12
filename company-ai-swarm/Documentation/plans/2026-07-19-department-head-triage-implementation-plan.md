# Department Head Triage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every dispatch-relevant department a real Head agent (DOMS sec.5/8-9's `leader`
field, currently unread and empty everywhere) that can accept or reject an objective before
`COOOrchestrator.receive_objective()` commits to it, per `Documentation/plans/
2026-07-19-department-head-triage-design.md` (Approved design).

**Architecture:** A new `DepartmentHead` protocol (`services/orchestrator/head.py`), exactly
parallel to `orchestrator/classification.py`'s `DepartmentClassifier` pattern: a zero-call
`AutoAcceptDepartmentHead` dev/test default, and a production `LLMDepartmentHead` that
dispatches to the department's own registered head agent via the existing
`orchestrator/router.py` `dispatch()` -> `AgentRuntime.execute_task()` cycle (not a bespoke
`model_gateway.generate()` call). `orchestrator/controller.py`'s single-department path
triages once with a bounded 2-attempt reassignment retry; `workflow_engine/engine.py`'s
multi-department path triages each substantive department immediately before its dispatch,
halting forward progress on a reject. A terminal reject raises `DepartmentRejectedError`,
treated as a normal completed reply upstream (same as `NoMatchingDepartmentError` today), and
writes a new `DEPARTMENT_REJECTED` escalation condition.

**Tech Stack:** Python, Pydantic, SQLAlchemy, pytest - matches the rest of `services/`.

## Global Constraints

- Every existing test that constructs a `COOOrchestrator` without a `head` kwarg, or calls
  `workflow_engine.execute_workflow()` without a `head` kwarg, must keep passing unmodified -
  both default to `AutoAcceptDepartmentHead()`, which always accepts and makes zero
  model/dispatch calls.
- The Department Head's identity must never appear in `department.agents` -
  `orchestrator/allocator.py`'s `select_agent()` must never be able to pick it for
  substantive work. It is looked up directly via `agent_registry.get(department.leader)`.
- Strategy department gets no head agent - its `agents` list is already empty, so
  `KeywordDepartmentClassifier`/`LLMDepartmentClassifier` already exclude it from
  `matched_departments` before triage would ever run.
- `suggested_department_id` validation (unknown, hallucinated, or already-attempted) happens
  in the caller (`orchestrator/controller.py`, `workflow_engine/engine.py`'s caller chain),
  never inside `orchestrator/head.py` itself - `head.py` has no access to the full
  `DepartmentRegistry` or the set of departments already attempted in this call.
- `DEPARTMENT_HEAD_TRIAGE` env var: `"auto_accept"` (default) or `"llm"` - exactly parallel to
  `DEPARTMENT_CLASSIFIER`.
- Single-department path: exactly 2 attempts total (the classifier's original match, then one
  retry at a Head-suggested department), then `DepartmentRejectedError`.
- Multi-department path: no reassignment retry mid-workflow, no rollback of earlier
  departments' completed work - a reject halts forward progress exactly like a failed
  validation already does (`run.succeeded = False`, `run.blocked_reason` set, return
  immediately).

---

### Task 1: `services/orchestrator/head.py` - the DepartmentHead protocol

**Files:**
- Create: `services/orchestrator/head.py`
- Modify: `services/orchestrator/department_registry.py`
- Test: `Tests/integration/test_department_head.py`

**Interfaces:**
- Produces: `HeadVerdict(accepted: bool, reasoning: str, suggested_department_id: str | None
  = None)`; `DepartmentHead` Protocol with `evaluate(self, department: DepartmentDefinition,
  objective: str, *, agent_registry: AgentRegistry, model_gateway: ModelGateway, session:
  Session, coo_id: str, telemetry: TelemetrySink | None) -> HeadVerdict`;
  `AutoAcceptDepartmentHead`; `LLMDepartmentHead`; `create_head_from_env(env: Mapping[str,
  str] | None = None) -> DepartmentHead`; `DepartmentDefinition.leader: str` (first-class
  field, previously fell into `extra` - promoted here, not in Task 2, because `head.py`'s own
  test fixtures construct `DepartmentDefinition(leader=..., ...)` and Pydantic's default
  `extra="ignore"` behavior silently drops an undeclared kwarg rather than erroring, so
  `department.leader` would raise `AttributeError` without this. Task 2 below builds
  dispatch-relevant departments' real `leader` values and head agent files on top of this
  field rather than promoting it a second time.

- [ ] **Step 1: Write the failing tests**

Create `Tests/integration/test_department_head.py`:

```python
"""Documentation/plans/2026-07-19-department-head-triage-design.md Section 5's
"LLMDepartmentHead - unit tests against a fake dispatch()/AgentRuntime path" - uses a real
dispatch() (orchestrator/router.py) and a real AgentRuntime, with a fake ModelGateway
provider, same pattern Tests/integration/test_llm_department_classifier.py already
established for LLMDepartmentClassifier. AutoAcceptDepartmentHead needs no such
infrastructure - it never calls dispatch().
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import (
    AgentDefinition,
    AgentDepartment,
    AgentIdentity,
    AgentMission,
    AgentRegistry,
)
from identity_service.models import EntityType
from identity_service.repository import create_identity
from orchestrator.department_registry import DepartmentDefinition, DepartmentRegistry
from orchestrator.head import (
    AutoAcceptDepartmentHead,
    HeadVerdict,
    LLMDepartmentHead,
    create_head_from_env,
)
from security_service.permissions import grant_permission
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway

REPO_ROOT = Path(__file__).resolve().parents[2]


class _FakeProvider:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response_text


class _FailingProvider:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("rate limited")


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def _research_department() -> DepartmentDefinition:
    return DepartmentDefinition(
        id="research",
        name="Research Department",
        purpose="Information acquisition.",
        mission="Acquire information.",
        leader="research_head_001",
        capabilities=["research"],
        agents=["research_agent_001"],
    )


def _head_agent_registry() -> AgentRegistry:
    registry = AgentRegistry(".")
    registry._agents["research_head_001"] = AgentDefinition(
        identity=AgentIdentity(id="research_head_001", name="Research Department Head"),
        mission=AgentMission(objective="Evaluate whether an objective belongs to Research."),
        department=AgentDepartment(name="research"),
        capabilities=["triage"],
    )
    return registry


def _grant(session: Session, agent_id: str) -> None:
    create_identity(session, id=agent_id, entity_type=EntityType.AGENT, name=agent_id)
    grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")


class TestAutoAcceptDepartmentHead:
    def test_always_accepts_with_no_suggested_department(self) -> None:
        verdict = AutoAcceptDepartmentHead().evaluate(
            _research_department(),
            "any objective",
            agent_registry=AgentRegistry("."),
            model_gateway=None,
            session=None,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict == HeadVerdict(
            accepted=True, reasoning="Auto-accept (dev/test default).", suggested_department_id=None
        )


class TestLLMDepartmentHead:
    def test_accepts_and_parses_reasoning(self, session: Session) -> None:
        _grant(session, "research_head_001")
        provider = _FakeProvider(
            json.dumps(
                {"accepted": True, "reasoning": "Genuinely a research task.", "suggested_department_id": None}
            )
        )

        verdict = LLMDepartmentHead().evaluate(
            _research_department(),
            "Design a Forex trading strategy",
            agent_registry=_head_agent_registry(),
            model_gateway=ModelGateway(provider),
            session=session,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict.accepted is True
        assert verdict.reasoning == "Genuinely a research task."
        assert verdict.suggested_department_id is None
        assert "Forex trading strategy" in provider.prompts[0]

    def test_rejects_with_suggested_department(self, session: Session) -> None:
        _grant(session, "research_head_001")
        provider = _FakeProvider(
            json.dumps(
                {
                    "accepted": False,
                    "reasoning": "This is engineering work, not research.",
                    "suggested_department_id": "engineering",
                }
            )
        )

        verdict = LLMDepartmentHead().evaluate(
            _research_department(),
            "Build a trading bot",
            agent_registry=_head_agent_registry(),
            model_gateway=ModelGateway(provider),
            session=session,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict.accepted is False
        assert verdict.suggested_department_id == "engineering"

    def test_rejects_with_no_suggestion_when_not_worth_the_swarm(self, session: Session) -> None:
        _grant(session, "research_head_001")
        provider = _FakeProvider(
            json.dumps(
                {
                    "accepted": False,
                    "reasoning": "Not worth dispatching the swarm for.",
                    "suggested_department_id": None,
                }
            )
        )

        verdict = LLMDepartmentHead().evaluate(
            _research_department(),
            "What's the weather?",
            agent_registry=_head_agent_registry(),
            model_gateway=ModelGateway(provider),
            session=session,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict.accepted is False
        assert verdict.suggested_department_id is None

    def test_strips_markdown_code_fence(self, session: Session) -> None:
        _grant(session, "research_head_001")
        payload = json.dumps({"accepted": True, "reasoning": "ok", "suggested_department_id": None})
        provider = _FakeProvider(f"```json\n{payload}\n```")

        verdict = LLMDepartmentHead().evaluate(
            _research_department(),
            "obj",
            agent_registry=_head_agent_registry(),
            model_gateway=ModelGateway(provider),
            session=session,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict.accepted is True

    def test_drops_non_string_suggested_department_id(self, session: Session) -> None:
        """A suggested_department_id that isn't even a string (the model returning a number,
        a list, etc.) is dropped here - full registry-membership/already-attempted validation
        happens downstream in orchestrator/controller.py, but a type that could never be a
        real department id is never passed through."""
        _grant(session, "research_head_001")
        provider = _FakeProvider(
            json.dumps({"accepted": False, "reasoning": "no", "suggested_department_id": 42})
        )

        verdict = LLMDepartmentHead().evaluate(
            _research_department(),
            "obj",
            agent_registry=_head_agent_registry(),
            model_gateway=ModelGateway(provider),
            session=session,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict.suggested_department_id is None

    def test_unparseable_response_fails_toward_reject(self, session: Session) -> None:
        _grant(session, "research_head_001")
        provider = _FakeProvider("this is not json at all")

        verdict = LLMDepartmentHead().evaluate(
            _research_department(),
            "obj",
            agent_registry=_head_agent_registry(),
            model_gateway=ModelGateway(provider),
            session=session,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict.accepted is False
        assert verdict.suggested_department_id is None

    def test_provider_failure_propagates_not_a_verdict(self, session: Session) -> None:
        _grant(session, "research_head_001")

        with pytest.raises(RuntimeError, match="rate limited"):
            LLMDepartmentHead().evaluate(
                _research_department(),
                "obj",
                agent_registry=_head_agent_registry(),
                model_gateway=ModelGateway(_FailingProvider()),
                session=session,
                coo_id="coo",
                telemetry=None,
            )

    def test_missing_head_agent_raises(self, session: Session) -> None:
        with pytest.raises(ValueError, match="no registered head agent"):
            LLMDepartmentHead().evaluate(
                _research_department(),
                "obj",
                agent_registry=AgentRegistry("."),  # empty - research_head_001 not registered
                model_gateway=ModelGateway(_FakeProvider("{}")),
                session=session,
                coo_id="coo",
                telemetry=None,
            )


def test_create_head_from_env_selects_auto_accept_by_default() -> None:
    head = create_head_from_env(env={})
    assert isinstance(head, AutoAcceptDepartmentHead)


def test_create_head_from_env_selects_llm() -> None:
    head = create_head_from_env(env={"DEPARTMENT_HEAD_TRIAGE": "llm"})
    assert isinstance(head, LLMDepartmentHead)


def test_create_head_from_env_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="Unknown DEPARTMENT_HEAD_TRIAGE"):
        create_head_from_env(env={"DEPARTMENT_HEAD_TRIAGE": "made_up"})


@pytest.mark.skipif(
    not (os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("RUN_REAL_ANTHROPIC_SMOKE_TEST") == "1"),
    reason="Real Claude API smoke test - set ANTHROPIC_API_KEY and RUN_REAL_ANTHROPIC_SMOKE_TEST=1 to run",
)
def test_real_llm_department_head_smoke_test(session: Session) -> None:
    """Same gated-smoke-test pattern as Tests/integration/test_llm_department_classifier.py's
    test_real_llm_classification_smoke_test. Loads the real on-disk research_head_001 (Task 2
    of this plan) rather than a constructed fake, so this only passes once Task 2 has landed -
    by design, skipped by default so it never blocks CI."""

    from shared.providers.anthropic_provider import AnthropicModelProvider

    _grant(session, "research_head_001")
    department_registry = DepartmentRegistry(REPO_ROOT / "departments")
    department_registry.load_all()
    agent_registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    agent_registry.load_all()

    verdict = LLMDepartmentHead().evaluate(
        department_registry.get("research"),
        "Research current renewable energy storage trends",
        agent_registry=agent_registry,
        model_gateway=ModelGateway(AnthropicModelProvider()),
        session=session,
        coo_id="coo",
        telemetry=None,
    )

    assert verdict.accepted is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest Tests/integration/test_department_head.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'orchestrator.head'`

- [ ] **Step 3: Promote `leader` to a first-class field in `department_registry.py`**

`head.py`'s tests (Step 1) construct `DepartmentDefinition(leader=..., ...)`, and `head.py`
itself reads `department.leader`. `DepartmentDefinition` doesn't declare that field yet -
Pydantic's default `extra="ignore"` behavior means passing `leader=` today is silently
dropped, not an error, so `department.leader` would raise `AttributeError`. Promote it now
rather than in Task 2, since Task 1 cannot pass its own tests without it.

In `services/orchestrator/department_registry.py`, replace:

```python
class DepartmentDefinition(BaseModel):
    id: str
    name: str
    purpose: str = ""
    mission: str = ""
    capabilities: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    lifecycle_state: str = "proposed"
    extra: dict[str, Any] = Field(default_factory=dict)


def load_department_definition(path: str | Path) -> DepartmentDefinition:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    data = raw["department"]
    known_fields = {"id", "name", "purpose", "mission", "capabilities", "agents", "lifecycle_state"}
    extra = {k: v for k, v in data.items() if k not in known_fields}
    return DepartmentDefinition(**{k: v for k, v in data.items() if k in known_fields}, extra=extra)
```

with:

```python
class DepartmentDefinition(BaseModel):
    id: str
    name: str
    purpose: str = ""
    mission: str = ""
    # DOMS sec.5/8-9 (Department Leadership / Department Leader Authority) - the identity id
    # of this department's head agent, looked up directly via AgentRegistry.get(leader), never
    # through capability matching. Empty string means no head is registered (e.g. Strategy -
    # see Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3).
    leader: str = ""
    capabilities: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    lifecycle_state: str = "proposed"
    extra: dict[str, Any] = Field(default_factory=dict)


def load_department_definition(path: str | Path) -> DepartmentDefinition:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    data = raw["department"]
    known_fields = {
        "id", "name", "purpose", "mission", "leader", "capabilities", "agents", "lifecycle_state",
    }
    extra = {k: v for k, v in data.items() if k not in known_fields}
    return DepartmentDefinition(**{k: v for k, v in data.items() if k in known_fields}, extra=extra)
```

This does not touch any `departments/*/definition.yaml` file - every department's `leader`
stays `""` (now a declared field's default instead of an `extra` entry) until Task 2 sets the
four dispatch-relevant departments' real values. Run `python -m pytest Tests/ -q` after this
step to confirm no other test depended on `leader` living in `extra`.

- [ ] **Step 4: Create `services/orchestrator/head.py`**

```python
"""Department Head Triage.

Source: Documentation/plans/2026-07-19-department-head-triage-design.md. Every
departments/*/definition.yaml already carries a `leader` field (DOMS sec.5/8-9) but nothing
in the codebase ever read it or acted on it - once orchestrator/classification.py picked a
department, that department had no say. This module gives each dispatch-relevant department a
real Head agent that can accept or reject an objective before COOOrchestrator.receive_objective()
commits to it, via the same dispatch() (orchestrator/router.py) -> AgentRuntime.execute_task()
cycle any other agent's work already goes through - not a bespoke model_gateway.generate() call
like classification.py/intake.py use, per DOMS sec.8's Leader accountability.

Two swappable implementations of one interface, exactly parallel to
orchestrator/classification.py's DepartmentClassifier pattern:

- AutoAcceptDepartmentHead (dev/test default): always accepts, zero model/dispatch calls,
  mirrors KeywordDepartmentClassifier's zero-network-call nature.
  COOOrchestrator.__init__ defaults to this, so every existing call site that constructs a
  COOOrchestrator without a `head` kwarg needs zero changes.
- LLMDepartmentHead: production, dispatches to the department's own registered head agent.
  Selected via DEPARTMENT_HEAD_TRIAGE=llm, exactly parallel to DEPARTMENT_CLASSIFIER.

A suggested_department_id in a reject verdict is NOT validated here - the caller
(orchestrator/controller.py's single-department retry loop, workflow_engine/engine.py's
multi-department loop) is the one holding the real DepartmentRegistry and the set of
departments already attempted in this call, so registry-membership and already-attempted
validation happen there, the same discipline LLMDepartmentClassifier already applies to
hallucinated department IDs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Mapping, Protocol

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry
from observability_service.telemetry import TelemetrySink
from orchestrator.department_registry import DepartmentDefinition
from orchestrator.router import dispatch
from shared.llm_json import strip_code_fence
from shared.model_gateway import ModelGateway


@dataclass
class HeadVerdict:
    accepted: bool
    reasoning: str
    suggested_department_id: str | None = None  # only meaningful when accepted=False


class DepartmentHead(Protocol):
    def evaluate(
        self,
        department: DepartmentDefinition,
        objective: str,
        *,
        agent_registry: AgentRegistry,
        model_gateway: ModelGateway,
        session: Session,
        coo_id: str,
        telemetry: TelemetrySink | None,
    ) -> HeadVerdict: ...


class AutoAcceptDepartmentHead:
    """Dev/test default - always accepts, zero calls."""

    def evaluate(self, department: DepartmentDefinition, objective: str, **_: object) -> HeadVerdict:
        return HeadVerdict(
            accepted=True,
            reasoning="Auto-accept (dev/test default).",
            suggested_department_id=None,
        )


class LLMDepartmentHead:
    """Production: dispatches to department.leader's registered head agent via the existing
    dispatch() cycle. Stateless - model_gateway is supplied per call like every other
    DepartmentHead.evaluate() implementation, so this needs no constructor."""

    def evaluate(
        self,
        department: DepartmentDefinition,
        objective: str,
        *,
        agent_registry: AgentRegistry,
        model_gateway: ModelGateway,
        session: Session,
        coo_id: str,
        telemetry: TelemetrySink | None,
    ) -> HeadVerdict:
        head_agent = agent_registry.get(department.leader)
        if head_agent is None:
            raise ValueError(
                f"Department '{department.id}' has no registered head agent for "
                f"leader '{department.leader}'."
            )

        result = dispatch(
            session,
            coo_id=coo_id,
            agent=head_agent,
            objective=(
                f"Evaluate whether this objective belongs to the {department.name} "
                f"({department.mission}): {objective}"
            ),
            required_output=(
                'Respond with ONLY a JSON object: {"accepted": true|false, "reasoning": '
                '"...", "suggested_department_id": "<id>|null"}'
            ),
            model_gateway=model_gateway,
            telemetry=telemetry,
        )

        try:
            data = json.loads(strip_code_fence(result.output))
            accepted = bool(data["accepted"])
            reasoning = str(data["reasoning"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return HeadVerdict(
                accepted=False,
                reasoning=(
                    f"Department Head response was not valid JSON in the expected shape: "
                    f"{result.output!r} ({exc})"
                ),
                suggested_department_id=None,
            )

        suggested = data.get("suggested_department_id")
        return HeadVerdict(
            accepted=accepted,
            reasoning=reasoning,
            suggested_department_id=suggested if isinstance(suggested, str) else None,
        )


_HEADS = ("auto_accept", "llm")


def create_head_from_env(env: Mapping[str, str] | None = None) -> DepartmentHead:
    """DEPARTMENT_HEAD_TRIAGE env var: "auto_accept" (default) or "llm" - exactly parallel to
    DEPARTMENT_CLASSIFIER."""

    source = env if env is not None else os.environ
    selected = source.get("DEPARTMENT_HEAD_TRIAGE", "auto_accept").strip().lower()

    if selected == "auto_accept":
        return AutoAcceptDepartmentHead()
    if selected == "llm":
        return LLMDepartmentHead()

    raise ValueError(f"Unknown DEPARTMENT_HEAD_TRIAGE={selected!r}; expected one of {_HEADS}.")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest Tests/integration/test_department_head.py -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add services/orchestrator/head.py services/orchestrator/department_registry.py \
  Tests/integration/test_department_head.py
git commit -m "feat: add DepartmentHead protocol with auto-accept and LLM implementations"
```

---

### Task 2: Department Head agent registration

**Files:**
- Create: `agents/active/research_head/agent.yaml`
- Create: `agents/active/engineering_head/agent.yaml`
- Create: `agents/active/compliance_head/agent.yaml`
- Create: `agents/active/operations_head/agent.yaml`
- Modify: `departments/research/definition.yaml`
- Modify: `departments/engineering/definition.yaml`
- Modify: `departments/compliance/definition.yaml`
- Modify: `departments/operations/definition.yaml`
- Test: `Tests/unit/test_department_registry.py`

**Interfaces:**
- Consumes: `DepartmentDefinition.leader: str` (Task 1 already promoted this to a first-class
  field - do not modify `services/orchestrator/department_registry.py` in this task).
- Produces: four registered `AgentDefinition`s (`research_head_001`, `engineering_head_001`,
  `compliance_head_001`, `operations_head_001`) reachable via `AgentRegistry.get(...)`; each
  department's `leader` field set to the matching head's identity id. Task 3/4 depend on
  `department.leader` resolving to a real agent for research/engineering/compliance/operations.

- [ ] **Step 1: Write the failing tests**

Create `Tests/unit/test_department_registry.py`:

```python
"""Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3's Department
Head agent registration: `department.leader` promoted from department_registry.py's
catch-all `extra` dict to a first-class field, and the four dispatch-relevant departments
(research, engineering, compliance, operations) each carry a real head agent identity.
Strategy is deliberately excluded - its empty `agents` list already keeps it out of the
classifier's matches before triage would ever run.
"""

from __future__ import annotations

from pathlib import Path

from agent_runtime.registry import AgentRegistry
from orchestrator.department_registry import DepartmentRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]


def _departments() -> DepartmentRegistry:
    registry = DepartmentRegistry(REPO_ROOT / "departments")
    registry.load_all()
    return registry


def _agents() -> AgentRegistry:
    registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    registry.load_all()
    return registry


def test_leader_is_a_first_class_field_not_in_extra() -> None:
    research = _departments().get("research")

    assert research is not None
    assert research.leader == "research_head_001"
    assert "leader" not in research.extra


class TestDispatchRelevantDepartmentsHaveARegisteredHead:
    def test_research_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        research = departments.get("research")

        assert research is not None
        assert agents.get(research.leader) is not None
        assert research.leader not in research.agents

    def test_engineering_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        engineering = departments.get("engineering")

        assert engineering is not None
        assert agents.get(engineering.leader) is not None
        assert engineering.leader not in engineering.agents

    def test_compliance_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        compliance = departments.get("compliance")

        assert compliance is not None
        assert agents.get(compliance.leader) is not None
        assert compliance.leader not in compliance.agents

    def test_operations_head_is_registered_and_out_of_the_worker_agents_list(self) -> None:
        departments, agents = _departments(), _agents()
        operations = departments.get("operations")

        assert operations is not None
        assert agents.get(operations.leader) is not None
        assert operations.leader not in operations.agents


def test_strategy_has_no_head_by_design() -> None:
    departments, agents = _departments(), _agents()
    strategy = departments.get("strategy")

    assert strategy is not None
    assert strategy.leader == ""
    assert agents.get("strategy_head_001") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest Tests/unit/test_department_registry.py -v`
Expected: FAIL - `research.leader == ""` (not yet `"research_head_001"`), and
`agents.get(research.leader)` is `None` (no head agents registered yet). `DepartmentDefinition`
already has the `leader` field (Task 1) - this task only fails on data, not on a missing field.

- [ ] **Step 3: Set `leader` in the four dispatch-relevant `departments/*/definition.yaml` files**

In `departments/research/definition.yaml`, change `leader: ""` to `leader: research_head_001`.
In `departments/engineering/definition.yaml`, change `leader: ""` to `leader: engineering_head_001`.
In `departments/compliance/definition.yaml`, change `leader: ""` to `leader: compliance_head_001`.
In `departments/operations/definition.yaml`, change `leader: ""` to `leader: operations_head_001`.
Leave `departments/strategy/definition.yaml`'s `leader: ""` unchanged.

- [ ] **Step 4: Create `agents/active/research_head/agent.yaml`**
```yaml
# Agent definition. Schema: agents/templates/agent_template.yaml (ADLS).
# Department Head (DOMS sec.8-9): triage only, not a work-product agent - see
# Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3. Its identity
# stays out of departments/research/definition.yaml's `agents:` list (allocator.py's
# capability-based select_agent() must never pick it for substantive work); it is looked up
# directly via department.leader instead.

agent:
  identity:
    id: research_head_001
    name: "Research Department Head"
    version: "1.0"
    created_by: ""
    created_date: ""
    status: draft

  mission:
    objective: "Evaluate whether an objective genuinely requires the Research Department's capabilities, or belongs elsewhere, or isn't worth the swarm at all."
    responsibilities:
      - "Accept objectives that genuinely require research, analysis, or reporting."
      - "Reject objectives that belong to another department, naming which one when clear."
      - "Reject objectives that are not worth dispatching the swarm for at all."
    boundaries:
      - "Does not perform the research work itself - triage only."
    success_definition: "Delivers an accept/reject verdict with documented reasoning within scope."

  department:
    name: research
    manager: ""
    scope: ""

  capabilities:
    - triage

  knowledge:
    sources: []
    domains: []
    restrictions: []
    validation_required: true

  memory:
    short_term: true
    long_term: false
    department_memory: allowed
    enterprise_memory: restricted
    retention_policy: ""

  tools:
    available: []
    permissions: []
    execution_limits: []
    approval_required: []

  workflow_access:
    allowed: []
    restricted: []
    creation_permission: false

  permissions:
    read: [department_objectives]
    write: [triage_verdicts]
    execute: []
    approve: []
    communicate: [department, coo]
    deploy: false

  behaviour:
    communication_style: ""
    decision_style: "evidence-based"
    risk_tolerance: "low"
    escalation_rules: "Escalate unresolved department-assignment disputes to the COO."
    failure_handling: ""

  security:
    identity_level: ""
    trust_level: operational
    audit_required: true
    data_classification: ""
    restrictions: []

  evaluation:
    metrics:
      accuracy: null
      quality: null
      speed: null
      cost: null
    human_feedback: ""
    improvement_targets: []

  lifecycle:
    status: draft
    owner: ""
    review_date: ""
    replacement_strategy: ""
```

- [ ] **Step 5: Create `agents/active/engineering_head/agent.yaml`**
```yaml
# Agent definition. Schema: agents/templates/agent_template.yaml (ADLS).
# Department Head (DOMS sec.8-9): triage only, not a work-product agent - see
# Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3. Its identity
# stays out of departments/engineering/definition.yaml's `agents:` list (allocator.py's
# capability-based select_agent() must never pick it for substantive work); it is looked up
# directly via department.leader instead.

agent:
  identity:
    id: engineering_head_001
    name: "Engineering Department Head"
    version: "1.0"
    created_by: ""
    created_date: ""
    status: draft

  mission:
    objective: "Evaluate whether an objective genuinely requires the Engineering Department's capabilities, or belongs elsewhere, or isn't worth the swarm at all."
    responsibilities:
      - "Accept objectives that genuinely require building or maintaining technical capabilities."
      - "Reject objectives that belong to another department, naming which one when clear."
      - "Reject objectives that are not worth dispatching the swarm for at all."
    boundaries:
      - "Does not perform the engineering work itself - triage only."
    success_definition: "Delivers an accept/reject verdict with documented reasoning within scope."

  department:
    name: engineering
    manager: ""
    scope: ""

  capabilities:
    - triage

  knowledge:
    sources: []
    domains: []
    restrictions: []
    validation_required: true

  memory:
    short_term: true
    long_term: false
    department_memory: allowed
    enterprise_memory: restricted
    retention_policy: ""

  tools:
    available: []
    permissions: []
    execution_limits: []
    approval_required: []

  workflow_access:
    allowed: []
    restricted: []
    creation_permission: false

  permissions:
    read: [department_objectives]
    write: [triage_verdicts]
    execute: []
    approve: []
    communicate: [department, coo]
    deploy: false

  behaviour:
    communication_style: ""
    decision_style: "evidence-based"
    risk_tolerance: "low"
    escalation_rules: "Escalate unresolved department-assignment disputes to the COO."
    failure_handling: ""

  security:
    identity_level: ""
    trust_level: operational
    audit_required: true
    data_classification: ""
    restrictions: []

  evaluation:
    metrics:
      accuracy: null
      quality: null
      speed: null
      cost: null
    human_feedback: ""
    improvement_targets: []

  lifecycle:
    status: draft
    owner: ""
    review_date: ""
    replacement_strategy: ""
```

- [ ] **Step 6: Create `agents/active/compliance_head/agent.yaml`**
```yaml
# Agent definition. Schema: agents/templates/agent_template.yaml (ADLS).
# Department Head (DOMS sec.8-9): triage only, not a work-product agent - see
# Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3. Its identity
# stays out of departments/compliance/definition.yaml's `agents:` list (allocator.py's
# capability-based select_agent() must never pick it for substantive work); it is looked up
# directly via department.leader instead.

agent:
  identity:
    id: compliance_head_001
    name: "Compliance Department Head"
    version: "1.0"
    created_by: ""
    created_date: ""
    status: draft

  mission:
    objective: "Evaluate whether an objective genuinely requires the Compliance Department's capabilities, or belongs elsewhere, or isn't worth the swarm at all."
    responsibilities:
      - "Accept objectives that genuinely require identifying applicable obligations or assessing risk."
      - "Reject objectives that belong to another department, naming which one when clear."
      - "Reject objectives that are not worth dispatching the swarm for at all."
    boundaries:
      - "Does not perform the compliance work itself - triage only."
    success_definition: "Delivers an accept/reject verdict with documented reasoning within scope."

  department:
    name: compliance
    manager: ""
    scope: ""

  capabilities:
    - triage

  knowledge:
    sources: []
    domains: []
    restrictions: []
    validation_required: true

  memory:
    short_term: true
    long_term: false
    department_memory: allowed
    enterprise_memory: restricted
    retention_policy: ""

  tools:
    available: []
    permissions: []
    execution_limits: []
    approval_required: []

  workflow_access:
    allowed: []
    restricted: []
    creation_permission: false

  permissions:
    read: [department_objectives]
    write: [triage_verdicts]
    execute: []
    approve: []
    communicate: [department, coo]
    deploy: false

  behaviour:
    communication_style: ""
    decision_style: "evidence-based"
    risk_tolerance: "low"
    escalation_rules: "Escalate unresolved department-assignment disputes to the COO."
    failure_handling: ""

  security:
    identity_level: ""
    trust_level: operational
    audit_required: true
    data_classification: ""
    restrictions: []

  evaluation:
    metrics:
      accuracy: null
      quality: null
      speed: null
      cost: null
    human_feedback: ""
    improvement_targets: []

  lifecycle:
    status: draft
    owner: ""
    review_date: ""
    replacement_strategy: ""
```

- [ ] **Step 7: Create `agents/active/operations_head/agent.yaml`**
```yaml
# Agent definition. Schema: agents/templates/agent_template.yaml (ADLS).
# Department Head (DOMS sec.8-9): triage only, not a work-product agent - see
# Documentation/plans/2026-07-19-department-head-triage-design.md Section 3.3. Its identity
# stays out of departments/operations/definition.yaml's `agents:` list (allocator.py's
# capability-based select_agent() must never pick it for substantive work); it is looked up
# directly via department.leader instead.

agent:
  identity:
    id: operations_head_001
    name: "Operations Department Head"
    version: "1.0"
    created_by: ""
    created_date: ""
    status: draft

  mission:
    objective: "Evaluate whether an objective genuinely requires the Operations Department's capabilities, or belongs elsewhere, or isn't worth the swarm at all."
    responsibilities:
      - "Accept objectives that genuinely require validating outputs or monitoring workflow execution."
      - "Reject objectives that belong to another department, naming which one when clear."
      - "Reject objectives that are not worth dispatching the swarm for at all."
    boundaries:
      - "Does not perform the review work itself - triage only."
    success_definition: "Delivers an accept/reject verdict with documented reasoning within scope."

  department:
    name: operations
    manager: ""
    scope: ""

  capabilities:
    - triage

  knowledge:
    sources: []
    domains: []
    restrictions: []
    validation_required: true

  memory:
    short_term: true
    long_term: false
    department_memory: allowed
    enterprise_memory: restricted
    retention_policy: ""

  tools:
    available: []
    permissions: []
    execution_limits: []
    approval_required: []

  workflow_access:
    allowed: []
    restricted: []
    creation_permission: false

  permissions:
    read: [department_objectives]
    write: [triage_verdicts]
    execute: []
    approve: []
    communicate: [department, coo]
    deploy: false

  behaviour:
    communication_style: ""
    decision_style: "evidence-based"
    risk_tolerance: "low"
    escalation_rules: "Escalate unresolved department-assignment disputes to the COO."
    failure_handling: ""

  security:
    identity_level: ""
    trust_level: operational
    audit_required: true
    data_classification: ""
    restrictions: []

  evaluation:
    metrics:
      accuracy: null
      quality: null
      speed: null
      cost: null
    human_feedback: ""
    improvement_targets: []

  lifecycle:
    status: draft
    owner: ""
    review_date: ""
    replacement_strategy: ""
```

- [ ] **Step 8: Run tests to verify they pass**
Run: `python -m pytest Tests/unit/test_department_registry.py -v`
Expected: all tests PASS

- [ ] **Step 9: Run the full existing suite to confirm no regressions**
Run: `python -m pytest Tests/ -q`
Expected: all tests PASS (the four departments' `agents:` lists are unchanged, so
`KeywordDepartmentClassifier`/`allocator.select_agent()` behavior is unaffected)

- [ ] **Step 10: Commit**
```bash
git add agents/active/research_head/agent.yaml agents/active/engineering_head/agent.yaml \
  agents/active/compliance_head/agent.yaml agents/active/operations_head/agent.yaml \
  departments/research/definition.yaml departments/engineering/definition.yaml \
  departments/compliance/definition.yaml departments/operations/definition.yaml \
  Tests/unit/test_department_registry.py
git commit -m "feat: register a Department Head agent for each dispatch-relevant department"
```

---

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

### Task 6: Documentation

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `Documentation/plans/2026-07-19-department-head-triage-design.md`

**Interfaces:**
- Consumes: nothing (documentation only, no code).

- [ ] **Step 1: Append a CHANGELOG.md entry**

Append to the end of `CHANGELOG.md`:

```markdown
- **Department Head Triage (Phase 2 of Dynamic Model Selection, `Documentation/plans/2026-07-19-department-head-triage-design.md`)**: `orchestrator/head.py` (new module) - `HeadVerdict`/`DepartmentHead` protocol, `AutoAcceptDepartmentHead` (dev/test default, zero calls) and `LLMDepartmentHead` (production: dispatches to the department's own registered head agent via the existing `orchestrator/router.py` `dispatch()` -> `AgentRuntime.execute_task()` cycle, not a bespoke `model_gateway.generate()` call), selected via `DEPARTMENT_HEAD_TRIAGE` env var exactly parallel to `DEPARTMENT_CLASSIFIER`. `department.leader` (DOMS sec.5/8-9), previously unread and falling into `department_registry.py`'s catch-all `extra` dict, is now a first-class `DepartmentDefinition` field, set on the four dispatch-relevant departments (`<dept>_head_001`, new `agents/active/<dept>_head/agent.yaml` files) - Strategy is excluded, since its empty `agents` list already keeps it out of the classifier's matches. `orchestrator/controller.py`'s single-department path now triages once (2 attempts total: the classifier's match, then one retry at a Head-suggested department) before Select Agents; `workflow_engine/engine.py`'s multi-department path triages each substantive department immediately before its dispatch, halting forward progress on a reject the same way a failed validation already does (no rollback, no reassignment). A terminal reject writes a Decision Record and a new fifth framework condition, `DEPARTMENT_REJECTED` (`orchestrator/escalation.py`), then raises `DepartmentRejectedError` - the same normal-reply-not-HTTP-error treatment `apps/api_gateway/main.py`/`dashboard_api.py` already give `NoMatchingDepartmentError`. Every existing test constructing a `COOOrchestrator` (or calling `execute_workflow()`) without a `head` kwarg keeps passing unmodified - `AutoAcceptDepartmentHead` preserves prior behavior exactly. Deferred, not designed here (design doc Section 6): dynamic agent/specialist selection, token/cost budgets, real model tier selection.
```

- [ ] **Step 2: Mark the design doc implemented**

In `Documentation/plans/2026-07-19-department-head-triage-design.md`, replace:

```
**Status:** Approved design, not yet implemented.
```

with:

```
**Status:** Implemented.
```

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md Documentation/plans/2026-07-19-department-head-triage-design.md
git commit -m "docs: record Department Head Triage completion in the changelog"
```
