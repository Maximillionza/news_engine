"""Task dispatch: hands an allocated task to the Agent Runtime (Phase 4).

This is where the COO stops deciding and Phase 4's already-built, already-tested
AgentRuntime takes over - the COO does not re-implement the Agent Execution Cycle, it
constructs an AgentMessageContract (RCS sec.8) and calls the runtime, exactly the same
contract shape Tests/integration/test_agent_runtime.py already exercises directly.

Phase 9 addition (MVS sec.9 Test Category 005, Memory Validation): every task that completes
successfully has its outcome recorded as a Department-tier OBSERVATION memory object,
authored by the agent itself - the mechanism that makes "second execution improves via
stored knowledge" real rather than aspirational, since agent_runtime/runtime.py's Step 3
(Retrieve Relevant Knowledge) already queries Department-tier memory but nothing was ever
writing to it. See _record_department_observation()'s docstring for why this is best-effort.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentDefinition
from agent_runtime.runtime import AgentRuntime, ExecutionResult
from memory_service.models import MemoryTier, MemoryType
from memory_service.repository import write_memory
from security_service.audit import write_audit_record
from shared.contracts import AgentMessageContract
from shared.model_gateway import ModelGateway
from observability_service.telemetry import TelemetrySink


def dispatch(
    session: Session,
    *,
    coo_id: str,
    agent: AgentDefinition,
    objective: str,
    required_output: str,
    model_gateway: ModelGateway,
    telemetry: TelemetrySink | None = None,
    model: str | None = None,
) -> ExecutionResult:
    """`model` (Phase 20, IMPLEMENTATION_PLAN.md, 2026-07-25): threaded straight through to
    AgentRuntime.execute_task() - see that method's docstring. None reproduces every
    pre-Phase-20 call exactly."""

    message = AgentMessageContract(
        sender_agent=coo_id,
        receiver_agent=agent.identity.id,
        task=objective,
        required_output=required_output,
    )
    runtime = AgentRuntime(agent, model_gateway=model_gateway, telemetry=telemetry)
    result = runtime.execute_task(session, message, model=model)

    _record_department_observation(session, agent=agent, result=result)

    return result


def _record_department_observation(
    session: Session, *, agent: AgentDefinition, result: ExecutionResult
) -> None:
    """Best-effort: if the agent's identity wasn't granted `memory:department` write (most
    pre-Phase-9 test fixtures only grant read, since nothing wrote before this phase - see
    Documentation/operations/technology_decisions.md's Phase 9 note), the write is skipped
    and audited, not raised. A missing memory contribution must never undo a task that
    already completed successfully - this runs after execute_task() has already returned."""

    try:
        write_memory(
            session,
            identity_id=agent.identity.id,
            id=f"OBS-{uuid4().hex[:8]}",
            type=MemoryType.OBSERVATION,
            content=f"Completed task '{result.task}': {result.output}",
            creator=agent.identity.id,
            tier=MemoryTier.DEPARTMENT,
            department_id=agent.department.name,
        )
    except PermissionError as exc:
        write_audit_record(
            session,
            actor=agent.identity.id,
            action="record_department_observation",
            decision="denied",
            reason=str(exc),
        )
