"""Agent Runtime: executes one task for one agent, no COO in the loop.

Source: Specifications/3 - execution-framework/Runtime Operating Manual (ROM).md sec.11
Agent Execution Cycle:

    Receive Task -> Load Context -> Retrieve Relevant Knowledge -> Check Policies ->
    Plan Approach -> Execute -> Validate -> Produce Artifact -> Report Outcome ->
    Release Context

Each step is recorded to telemetry (component=f"agent_runtime:{agent_id}") so a caller can
observe the full cycle without instrumenting anything itself - this is what
IMPLEMENTATION_PLAN.md Phase 4's test means by "observable via telemetry."

The only model access path is `self._model_gateway.generate(...)` at the Execute step -
this class holds no other reference to a model or model provider (see
shared/model_gateway.py's docstring for why that matters).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentDefinition
from memory_service.models import MemoryTier
from memory_service.repository import query_memory
from observability_service.telemetry import TelemetryResult, TelemetrySink, default_sink
from security_service.audit import write_audit_record
from security_service.permissions import authorize
from shared.contracts import AgentMessageContract
from shared.model_gateway import ModelGateway


@dataclass
class ExecutionResult:
    task: str
    output: str
    artifact: dict[str, Any]
    steps_completed: list[str] = field(default_factory=list)


class AgentRuntime:
    def __init__(
        self,
        agent: AgentDefinition,
        model_gateway: ModelGateway,
        telemetry: TelemetrySink | None = None,
    ) -> None:
        self.agent = agent
        self._model_gateway = model_gateway
        self._telemetry = telemetry if telemetry is not None else default_sink
        self._component = f"agent_runtime:{agent.identity.id}"

    def _record(self, step: str, *, result: TelemetryResult, duration_ms: float, error: str | None = None) -> None:
        self._telemetry.record(
            component=self._component,
            action=step,
            duration_ms=duration_ms,
            result=result,
            error=error,
        )

    def execute_task(self, session: Session, message: AgentMessageContract) -> ExecutionResult:
        steps_completed: list[str] = []

        # Step 1: Receive Task
        start = time.perf_counter()
        if message.receiver_agent != self.agent.identity.id:
            raise ValueError(
                f"Task addressed to {message.receiver_agent}, not this agent "
                f"({self.agent.identity.id})"
            )
        self._record("receive_task", result=TelemetryResult.SUCCESS, duration_ms=(time.perf_counter() - start) * 1000)
        steps_completed.append("receive_task")

        # Step 2: Load Context
        start = time.perf_counter()
        context: dict[str, Any] = {
            "task": message.task,
            "sender": message.sender_agent,
            "required_output": message.required_output,
            "agent_context": message.context,
            "mission": self.agent.mission.objective,
            "capabilities": self.agent.capabilities,
        }
        self._record("load_context", result=TelemetryResult.SUCCESS, duration_ms=(time.perf_counter() - start) * 1000)
        steps_completed.append("load_context")

        # Step 3: Retrieve Relevant Knowledge (EMAS Department-tier memory for this
        # agent's department; a permission-denied here is not fatal - an agent with no
        # memory access yet simply proceeds with no prior knowledge, per EMAS sec.12's
        # "Is it authorized?" context-filtering question).
        start = time.perf_counter()
        knowledge: list[str] = []
        try:
            memories = query_memory(
                session,
                identity_id=self.agent.identity.id,
                tier=MemoryTier.DEPARTMENT,
                department_id=self.agent.department.name,
            )
            knowledge = [m.content for m in memories]
            result = TelemetryResult.SUCCESS
            error = None
        except PermissionError as exc:
            result = TelemetryResult.DENIED
            error = str(exc)
        self._record("retrieve_knowledge", result=result, duration_ms=(time.perf_counter() - start) * 1000, error=error)
        steps_completed.append("retrieve_knowledge")
        context["knowledge"] = knowledge

        # Step 4: Check Policies (ESTAS sec.10 Agent Action Validation, reused from Phase 1)
        start = time.perf_counter()
        auth = authorize(
            session,
            identity_id=self.agent.identity.id,
            resource=f"agent_execution:{self.agent.identity.id}",
            action="execute",
        )
        duration_ms = (time.perf_counter() - start) * 1000
        if not auth.allowed:
            self._record("check_policies", result=TelemetryResult.DENIED, duration_ms=duration_ms, error=auth.reason)
            raise PermissionError(
                f"{self.agent.identity.id} is not authorized to execute tasks: {auth.reason}"
            )
        self._record("check_policies", result=TelemetryResult.SUCCESS, duration_ms=duration_ms)
        steps_completed.append("check_policies")

        # Step 5: Plan Approach
        start = time.perf_counter()
        plan = (
            f"Address '{message.task}' using capabilities {self.agent.capabilities}, "
            f"drawing on {len(knowledge)} prior department-memory item(s)."
        )
        context["plan"] = plan
        self._record("plan_approach", result=TelemetryResult.SUCCESS, duration_ms=(time.perf_counter() - start) * 1000)
        steps_completed.append("plan_approach")

        # Step 6: Execute - the ONLY step that touches a model, and only via the gateway.
        start = time.perf_counter()
        prompt = (
            f"Mission: {self.agent.mission.objective}\n"
            f"Plan: {plan}\n"
            f"Task: {message.task}\n"
            f"Required output: {message.required_output}\n"
        )
        # Phase 12 (IMPLEMENTATION_PLAN.md, 2026-07-23): this agent's own fixed tool
        # allowlist, from its agent.yaml's tools.available - previously present in the
        # schema (ADLS sec.4-17) but never read by anything; this is the first runtime
        # effect it has. Empty for any agent that doesn't set one, reproducing today's
        # exact no-tools behavior.
        allowed_tools = self.agent.tools.get("available", [])
        output = self._model_gateway.generate(
            requester=self.agent.identity.id, prompt=prompt, allowed_tools=allowed_tools
        )
        self._record("execute", result=TelemetryResult.SUCCESS, duration_ms=(time.perf_counter() - start) * 1000)
        steps_completed.append("execute")

        # Step 7: Validate
        start = time.perf_counter()
        is_valid = bool(output and output.strip())
        if not is_valid:
            self._record("validate", result=TelemetryResult.FAILURE, duration_ms=(time.perf_counter() - start) * 1000, error="empty output")
            raise ValueError("Agent produced empty output; validation failed")
        self._record("validate", result=TelemetryResult.SUCCESS, duration_ms=(time.perf_counter() - start) * 1000)
        steps_completed.append("validate")

        # Step 8: Produce Artifact
        start = time.perf_counter()
        artifact = {
            "agent_id": self.agent.identity.id,
            "task": message.task,
            "output": output,
            "required_output": message.required_output,
        }
        self._record("produce_artifact", result=TelemetryResult.SUCCESS, duration_ms=(time.perf_counter() - start) * 1000)
        steps_completed.append("produce_artifact")

        # Step 9: Report Outcome (ESTAS sec.19/sec.24 audit record, reused from Phase 1)
        start = time.perf_counter()
        write_audit_record(
            session,
            actor=self.agent.identity.id,
            action=f"execute_task:{message.task}",
            decision="completed",
            resource=f"agent_execution:{self.agent.identity.id}",
            evidence={"output_length": len(output)},
        )
        self._record("report_outcome", result=TelemetryResult.SUCCESS, duration_ms=(time.perf_counter() - start) * 1000)
        steps_completed.append("report_outcome")

        # Step 10: Release Context
        start = time.perf_counter()
        context.clear()
        self._record("release_context", result=TelemetryResult.SUCCESS, duration_ms=(time.perf_counter() - start) * 1000)
        steps_completed.append("release_context")

        return ExecutionResult(
            task=message.task, output=output, artifact=artifact, steps_completed=steps_completed
        )
