"""Phase 4 exit-criteria test: load research_agent/agent.yaml, issue one canned task
directly to the Agent Runtime (bypassing the COO entirely), and confirm:

    1. The agent runtime traverses all Agent Execution Cycle steps (ROM sec.11),
       observable via telemetry from Phase 3.
    2. Output is produced and an audit record exists (Phase 1).
    3. The agent never calls a model directly - only through the Model Gateway.

Source: IMPLEMENTATION_PLAN.md Phase 4 test spec.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from agent_runtime.registry import AgentRegistry, load_agent_definition
from agent_runtime.runtime import AgentRuntime
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetryResult, TelemetrySink
from security_service.audit import get_audit_trail
from security_service.permissions import grant_permission
from shared.contracts import AgentMessageContract
from shared.db import Base, make_engine, make_session_factory
from shared.model_gateway import ModelGateway, StubModelProvider

REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_AGENT_YAML = REPO_ROOT / "agents" / "active" / "research_agent" / "agent.yaml"

ALL_EXECUTION_CYCLE_STEPS = [
    "receive_task",
    "load_context",
    "retrieve_knowledge",
    "check_policies",
    "plan_approach",
    "execute",
    "validate",
    "produce_artifact",
    "report_outcome",
    "release_context",
]


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


@pytest.fixture()
def telemetry() -> TelemetrySink:
    return TelemetrySink()


def test_research_agent_yaml_loads_from_the_real_scaffolded_file() -> None:
    definition = load_agent_definition(RESEARCH_AGENT_YAML)

    assert definition.identity.id == "research_agent_001"
    assert definition.department.name == "research"
    assert "research" in definition.capabilities


def test_agent_registry_loads_all_active_agents() -> None:
    registry = AgentRegistry(REPO_ROOT / "agents" / "active")
    registry.load_all()

    assert registry.get("research_agent_001") is not None
    assert len(registry) == 8  # research, engineering, compliance, review + 4 heads


class TestAgentExecutesTaskWithoutCOO:
    @pytest.fixture()
    def authorized_agent_id(self, session: Session) -> str:
        agent_id = "research_agent_001"
        create_identity(session, id=agent_id, entity_type=EntityType.AGENT, name="Research Agent", department="research")
        grant_permission(session, subject=agent_id, resource=f"agent_execution:{agent_id}", action="execute")
        grant_permission(session, subject=agent_id, resource="memory:department", action="read")
        return agent_id

    def test_end_to_end_execution_produces_output_and_audit_record(
        self, session: Session, telemetry: TelemetrySink, authorized_agent_id: str
    ) -> None:
        definition = load_agent_definition(RESEARCH_AGENT_YAML)
        gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
        runtime = AgentRuntime(definition, model_gateway=gateway, telemetry=telemetry)

        message = AgentMessageContract(
            sender_agent="test-harness",
            receiver_agent=authorized_agent_id,
            task="Summarize recent renewable energy market trends",
            required_output="A structured summary with sources",
        )

        result = runtime.execute_task(session, message)

        # 1. Output produced.
        assert result.output != ""
        assert result.artifact["task"] == message.task

        # 2. Audit record exists (Phase 1).
        trail = get_audit_trail(session, authorized_agent_id)
        report_outcome_records = [r for r in trail if r.action.startswith("execute_task:")]
        assert len(report_outcome_records) == 1
        assert report_outcome_records[0].decision == "completed"

    def test_agent_yaml_tools_available_reaches_the_provider(
        self, session: Session, telemetry: TelemetrySink, authorized_agent_id: str
    ) -> None:
        """Phase 12 (IMPLEMENTATION_PLAN.md, 2026-07-23) end-to-end: research_agent/agent.yaml
        really does have tools.available: [WebSearch] on disk, and the Execute step really
        does read AgentDefinition.tools (previously present in the schema but never having
        any runtime effect at all) and pass it all the way through
        ModelGateway.generate(allowed_tools=...) to the provider - not just plumbing that
        compiles, an actual value flowing from the yaml file to the model call."""

        class _SpyProvider:
            def __init__(self) -> None:
                self.received_allowed_tools: list[object] = []

            def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
                self.received_allowed_tools.append(allowed_tools)
                return "researched it"

        definition = load_agent_definition(RESEARCH_AGENT_YAML)
        assert definition.tools.get("available") == ["WebSearch"]  # the real file, not a fixture

        provider = _SpyProvider()
        gateway = ModelGateway(provider, telemetry=telemetry)
        runtime = AgentRuntime(definition, model_gateway=gateway, telemetry=telemetry)

        message = AgentMessageContract(
            sender_agent="test-harness",
            receiver_agent=authorized_agent_id,
            task="Summarize recent renewable energy market trends",
            required_output="A structured summary with sources",
        )
        runtime.execute_task(session, message)

        assert provider.received_allowed_tools == [["WebSearch"]]

    def test_all_execution_cycle_steps_are_observable_via_telemetry(
        self, session: Session, telemetry: TelemetrySink, authorized_agent_id: str
    ) -> None:
        definition = load_agent_definition(RESEARCH_AGENT_YAML)
        gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
        runtime = AgentRuntime(definition, model_gateway=gateway, telemetry=telemetry)

        message = AgentMessageContract(
            sender_agent="test-harness",
            receiver_agent=authorized_agent_id,
            task="Summarize recent renewable energy market trends",
            required_output="A structured summary with sources",
        )

        result = runtime.execute_task(session, message)

        assert result.steps_completed == ALL_EXECUTION_CYCLE_STEPS

        component = f"agent_runtime:{authorized_agent_id}"
        recorded_actions = [r.action for r in telemetry.query(component=component)]
        for step in ALL_EXECUTION_CYCLE_STEPS:
            assert step in recorded_actions, f"step {step!r} was not recorded to telemetry"

    def test_model_is_reachable_only_through_the_gateway(
        self, session: Session, telemetry: TelemetrySink, authorized_agent_id: str
    ) -> None:
        """Enforcement test for exit criterion 3. StubModelProvider.generate is the only
        place model output could originate; ModelGateway.call_count proves it was invoked
        exactly once, and the runtime holds no other reference capable of producing output -
        `AgentRuntime` has no attribute except `_model_gateway` that could reach a model."""

        definition = load_agent_definition(RESEARCH_AGENT_YAML)
        provider = StubModelProvider()
        gateway = ModelGateway(provider, telemetry=telemetry)
        runtime = AgentRuntime(definition, model_gateway=gateway, telemetry=telemetry)

        # Structural check: the runtime has no attribute that is itself a ModelProvider or
        # exposes .generate() outside of the gateway.
        model_capable_attrs = [
            name
            for name in vars(runtime)
            if hasattr(getattr(runtime, name), "generate") and getattr(runtime, name) is not gateway
        ]
        assert model_capable_attrs == []

        message = AgentMessageContract(
            sender_agent="test-harness",
            receiver_agent=authorized_agent_id,
            task="Summarize recent renewable energy market trends",
            required_output="A structured summary with sources",
        )
        result = runtime.execute_task(session, message)

        assert gateway.call_count == 1
        # The output must be exactly what StubModelProvider produces - proving the content
        # genuinely flowed through the gateway, not a bypass path.
        assert result.output.startswith("[stub model output for prompt of length")

        gateway_records = telemetry.query(component="model_gateway")
        assert len(gateway_records) == 1
        assert gateway_records[0].result == TelemetryResult.SUCCESS

    def test_task_addressed_to_a_different_agent_is_rejected(
        self, session: Session, telemetry: TelemetrySink, authorized_agent_id: str
    ) -> None:
        definition = load_agent_definition(RESEARCH_AGENT_YAML)
        gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
        runtime = AgentRuntime(definition, model_gateway=gateway, telemetry=telemetry)

        message = AgentMessageContract(
            sender_agent="test-harness",
            receiver_agent="engineering_agent_001",  # not this runtime's agent
            task="Do something",
            required_output="Anything",
        )

        with pytest.raises(ValueError, match="not this agent"):
            runtime.execute_task(session, message)

        assert gateway.call_count == 0  # never reached the Execute step

    def test_execution_without_permission_is_denied_before_any_model_call(
        self, session: Session, telemetry: TelemetrySink
    ) -> None:
        agent_id = "research_agent_001"
        create_identity(session, id=agent_id, entity_type=EntityType.AGENT, name="Research Agent")
        # No permission granted this time.

        definition = load_agent_definition(RESEARCH_AGENT_YAML)
        gateway = ModelGateway(StubModelProvider(), telemetry=telemetry)
        runtime = AgentRuntime(definition, model_gateway=gateway, telemetry=telemetry)

        message = AgentMessageContract(
            sender_agent="test-harness",
            receiver_agent=agent_id,
            task="Summarize recent renewable energy market trends",
            required_output="A structured summary with sources",
        )

        with pytest.raises(PermissionError):
            runtime.execute_task(session, message)

        assert gateway.call_count == 0  # Check Policies gates Execute
