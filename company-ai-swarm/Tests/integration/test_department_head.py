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

    def generate(self, prompt: str, *, allowed_tools=None) -> str:
        self.prompts.append(prompt)
        return self.response_text


class _FailingProvider:
    def generate(self, prompt: str, *, allowed_tools=None) -> str:
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

    def test_resolved_true_sets_resolved_output(self, session: Session) -> None:
        """Phase 16 (IMPLEMENTATION_PLAN.md, 2026-07-23): the Head can complete the objective
        itself in the same call that accepts it."""
        _grant(session, "research_head_001")
        provider = _FakeProvider(
            json.dumps(
                {
                    "accepted": True,
                    "reasoning": "Simple enough to answer directly.",
                    "resolved": True,
                    "output": "EUR/USD is trading sideways today.",
                    "needs_specialist": False,
                    "insufficient_information": False,
                }
            )
        )

        verdict = LLMDepartmentHead().evaluate(
            _research_department(),
            "What's EUR/USD doing?",
            agent_registry=_head_agent_registry(),
            model_gateway=ModelGateway(provider),
            session=session,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict.accepted is True
        assert verdict.resolved_output == "EUR/USD is trading sideways today."
        assert verdict.needs_specialist is False

    def test_resolved_true_with_non_string_output_becomes_empty_string_not_none(
        self, session: Session
    ) -> None:
        """A malformed/missing output on a claimed resolution must not silently fall through
        to the normal dispatch path (resolved_output=None means exactly that to
        resolve_verdict_execution()) - it has to surface as a real, failed execution instead,
        so validate_outcome()'s existing empty-output handling catches it."""
        _grant(session, "research_head_001")
        provider = _FakeProvider(
            json.dumps({"accepted": True, "reasoning": "ok", "resolved": True, "output": None})
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

        assert verdict.resolved_output == ""

    def test_needs_specialist_true_when_not_resolved(self, session: Session) -> None:
        _grant(session, "research_head_001")
        provider = _FakeProvider(
            json.dumps(
                {
                    "accepted": True,
                    "reasoning": "Requires deep statistical modeling beyond my own depth.",
                    "resolved": False,
                    "needs_specialist": True,
                }
            )
        )

        verdict = LLMDepartmentHead().evaluate(
            _research_department(),
            "Build a full econometric forecast model",
            agent_registry=_head_agent_registry(),
            model_gateway=ModelGateway(provider),
            session=session,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict.accepted is True
        assert verdict.needs_specialist is True
        assert verdict.resolved_output is None

    def test_insufficient_information_is_a_rejection_not_a_spawn(self, session: Session) -> None:
        """Deliberately NOT a spawn trigger (see LLMDepartmentHead's own docstring): a second
        agent has no information the first lacked, so this folds into a rejection instead,
        with reasoning distinguishing it from a wrong-department reject."""
        _grant(session, "research_head_001")
        provider = _FakeProvider(
            json.dumps(
                {
                    "accepted": True,
                    "reasoning": "Can't tell what's actually being asked for.",
                    "resolved": False,
                    "needs_specialist": False,
                    "insufficient_information": True,
                }
            )
        )

        verdict = LLMDepartmentHead().evaluate(
            _research_department(),
            "do the thing",
            agent_registry=_head_agent_registry(),
            model_gateway=ModelGateway(provider),
            session=session,
            coo_id="coo",
            telemetry=None,
        )

        assert verdict.accepted is False
        assert verdict.needs_specialist is False
        assert verdict.suggested_department_id is None
        assert "Insufficient information" in verdict.reasoning
        assert "Can't tell what's actually being asked for." in verdict.reasoning

    def test_accepted_with_neither_resolved_nor_needs_specialist_reproduces_normal_path(
        self, session: Session
    ) -> None:
        """Backward compatibility: a response using only the pre-Phase-16 shape (accepted/
        reasoning/suggested_department_id, no new keys at all) must still produce a verdict
        resolve_verdict_execution() treats as "fall through to normal select_agent()+
        dispatch()" - this is exactly what every pre-Phase-16 test in this class already
        sends and asserts on above."""
        _grant(session, "research_head_001")
        provider = _FakeProvider(
            json.dumps({"accepted": True, "reasoning": "Genuinely research work.", "suggested_department_id": None})
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

        assert verdict.accepted is True
        assert verdict.resolved_output is None
        assert verdict.needs_specialist is False

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
