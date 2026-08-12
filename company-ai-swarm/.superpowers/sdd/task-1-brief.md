### Task 1: `services/orchestrator/head.py` - the DepartmentHead protocol

**Files:**
- Create: `services/orchestrator/head.py`
- Test: `Tests/integration/test_department_head.py`

**Interfaces:**
- Produces: `HeadVerdict(accepted: bool, reasoning: str, suggested_department_id: str | None
  = None)`; `DepartmentHead` Protocol with `evaluate(self, department: DepartmentDefinition,
  objective: str, *, agent_registry: AgentRegistry, model_gateway: ModelGateway, session:
  Session, coo_id: str, telemetry: TelemetrySink | None) -> HeadVerdict`;
  `AutoAcceptDepartmentHead`; `LLMDepartmentHead`; `create_head_from_env(env: Mapping[str,
  str] | None = None) -> DepartmentHead`.

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

- [ ] **Step 3: Create `services/orchestrator/head.py`**

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest Tests/integration/test_department_head.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/orchestrator/head.py Tests/integration/test_department_head.py
git commit -m "feat: add DepartmentHead protocol with auto-accept and LLM implementations"
```

---

