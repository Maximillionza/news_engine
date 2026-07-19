"""SDK Agent Builder.

Source: Specifications/4 - future-expansion/Enterprise SDK Architecture Specification
(ESDKS).md sec.5.1 (Agent Builder), sec.7 (Validation Pipeline), sec.8 (Agent Creation
Workflow: Define Role -> Create Capability Set -> Generate Agent Template -> Assign
Department -> Assign Permissions -> Create Tests -> Deploy).

IMPLEMENTATION_PLAN.md Phase 10's own test: "Use the SDK to define a new agent (not one of
the original four) without editing core runtime code; confirm it registers in the Agent
Registry and executes a task successfully through the existing COO/workflow path from
Phases 5-7." `build_agent()` below is that path end to end:

    AgentDraft (Define Role) -> AgentDefinition (Generate Agent Template, ESDKS sec.7
    Schema Validation - agent_runtime.registry.AgentDefinition IS the schema) -> Security
    Review (department must exist; identity created + permissioned, ESTAS's own
    identity/permission chain, no bypass) -> Capability Test (a real smoke-test task
    executed through the unmodified Phase 4 AgentRuntime - this is also Phase 10's own exit
    criterion, not a separate check invented for it) -> Architecture Check (no id collision)
    -> Activate (agent.yaml written under agents_root, AND registered directly into the
    given in-memory AgentRegistry so it's usable immediately in this process without
    restarting anything).

No core runtime code changes here: AgentDefinition, AgentRegistry, AgentRuntime,
DepartmentRegistry, identity_service, and security_service are all reused exactly as Phases
1-4 built them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from agent_runtime.registry import (
    AgentDefinition,
    AgentDepartment,
    AgentIdentity,
    AgentMission,
    AgentRegistry,
)
from agent_runtime.runtime import AgentRuntime
from identity_service.models import EntityType
from identity_service.repository import create_identity, get_identity
from orchestrator.department_registry import DepartmentRegistry
from security_service.permissions import grant_permission
from shared.contracts import AgentMessageContract
from shared.model_gateway import ModelGateway
from validation.pipeline import ValidationReport


@dataclass
class AgentDraft:
    """ESDKS sec.5.1's Agent Builder input, minus `tools`/`evaluation` - AgentDefinition
    (agent_runtime/registry.py) already keeps those as untyped dicts (Phase 4's own
    documented scope: only identity/mission/department/capabilities/permissions affect
    runtime behaviour), so a draft has nothing structured to add there yet."""

    identity_id: str
    name: str
    department: str
    mission: str
    capabilities: list[str] = field(default_factory=list)
    smoke_test_task: str = "Confirm this agent can execute a task end to end."
    smoke_test_required_output: str = "A short confirmation."


def _write_agent_yaml(agents_root: Path, definition: AgentDefinition) -> Path:
    agent_dir = agents_root / definition.identity.id
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_file = agent_dir / "agent.yaml"
    payload: dict[str, Any] = {"agent": definition.model_dump()}
    with agent_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)
    return agent_file


def build_agent(
    draft: AgentDraft,
    *,
    session: Session,
    department_registry: DepartmentRegistry,
    agent_registry: AgentRegistry,
    model_gateway: ModelGateway,
    agents_root: Path,
) -> AgentDefinition:
    report = ValidationReport()

    # Generate Agent Template + Schema Validation: AgentDefinition's own Pydantic
    # validation IS the schema check (ESDKS sec.7) - an invalid shape raises here.
    try:
        definition = AgentDefinition(
            identity=AgentIdentity(id=draft.identity_id, name=draft.name, status="active"),
            mission=AgentMission(objective=draft.mission),
            department=AgentDepartment(name=draft.department),
            capabilities=list(draft.capabilities),
        )
        report.record("schema_validation", passed=True)
    except Exception as exc:  # noqa: BLE001 - record() raises ComponentValidationError from here
        report.record("schema_validation", passed=False, detail=str(exc))

    # Assign Department + Security Review: the department must actually exist, and the
    # identity must go through the same create-then-grant chain every other identity in
    # this codebase goes through - no bypass for SDK-created agents.
    department = department_registry.get(draft.department)
    report.record(
        "security_review",
        passed=department is not None,
        detail=f"Unknown department: {draft.department}" if department is None else "",
    )

    if get_identity(session, definition.identity.id) is None:
        create_identity(
            session,
            id=definition.identity.id,
            entity_type=EntityType.AGENT,
            name=definition.identity.name,
            department=draft.department,
        )
    grant_permission(
        session,
        subject=definition.identity.id,
        resource=f"agent_execution:{definition.identity.id}",
        action="execute",
    )
    grant_permission(session, subject=definition.identity.id, resource="memory:department", action="read")

    # Capability Test: a real execution through the unmodified Phase 4 AgentRuntime - the
    # same mechanism Phase 10's exit criterion asks for, not a separate invented check.
    runtime = AgentRuntime(definition, model_gateway=model_gateway)
    message = AgentMessageContract(
        sender_agent="sdk.agent_builder",
        receiver_agent=definition.identity.id,
        task=draft.smoke_test_task,
        required_output=draft.smoke_test_required_output,
    )
    result = runtime.execute_task(session, message)
    report.record(
        "capability_test",
        passed=bool(result.output.strip()),
        detail="" if result.output.strip() else "Smoke-test execution produced empty output.",
    )

    # Architecture Check: no id collision with an already-registered agent.
    report.record(
        "architecture_check",
        passed=agent_registry.get(definition.identity.id) is None,
        detail=f"Agent id already registered: {definition.identity.id}",
    )

    # Activate: written to disk (so a future AgentRegistry.load_all() - e.g. after a
    # restart - picks it up with zero runtime code changes) and registered directly into
    # the live registry so it is usable in this process immediately.
    _write_agent_yaml(agents_root, definition)
    agent_registry._agents[definition.identity.id] = definition  # same slot load_all() fills

    return definition
