"""Agent Registry: loads agent.yaml files (agents/templates/agent_template.yaml's schema,
per ADLS sec.4 Core Agent Schema) into structured definitions.

Note on location: `agent_runtime/` has no counterpart in CRBS's explicit services/ list
(orchestrator, workflow_engine, memory_service, knowledge_service, identity_service,
security_service, compliance_service, observability_service, event_service) - same
situation as `services/shared/` in Phase 0. TAS Layer 3 names "Agent Runtime" as a distinct
architectural layer, so this directory fills that gap; agents/ itself (per CRBS sec.7-8)
holds agent *definitions* (data), not the runtime *code* that executes them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AgentIdentity(BaseModel):
    id: str
    name: str
    version: str = "1.0"
    status: str = "draft"


class AgentMission(BaseModel):
    objective: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    success_definition: str = ""


class AgentDepartment(BaseModel):
    name: str
    manager: str = ""
    scope: str = ""


class AgentDefinition(BaseModel):
    """Structured form of an agent.yaml. Nested sections whose internal shape doesn't yet
    affect runtime behaviour (tools, memory, workflow_access, behaviour, security,
    evaluation, lifecycle) are kept as plain dicts rather than fully modelled - ADLS sec.4-17
    defines their schemas exhaustively, but Phase 4's Agent Runtime only needs identity,
    mission, department, capabilities, and permissions to execute a task."""

    identity: AgentIdentity
    mission: AgentMission = Field(default_factory=AgentMission)
    department: AgentDepartment
    capabilities: list[str] = Field(default_factory=list)
    knowledge: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    tools: dict[str, Any] = Field(default_factory=dict)
    workflow_access: dict[str, Any] = Field(default_factory=dict)
    permissions: dict[str, Any] = Field(default_factory=dict)
    behaviour: dict[str, Any] = Field(default_factory=dict)
    security: dict[str, Any] = Field(default_factory=dict)
    evaluation: dict[str, Any] = Field(default_factory=dict)
    lifecycle: dict[str, Any] = Field(default_factory=dict)


def load_agent_definition(path: str | Path) -> AgentDefinition:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AgentDefinition.model_validate(raw["agent"])


class AgentRegistry:
    """Loads every agents/active/*/agent.yaml under a given root."""

    def __init__(self, active_dir: str | Path) -> None:
        self._active_dir = Path(active_dir)
        self._agents: dict[str, AgentDefinition] = {}

    def load_all(self) -> None:
        for agent_dir in sorted(self._active_dir.iterdir()):
            agent_file = agent_dir / "agent.yaml"
            if agent_file.exists():
                definition = load_agent_definition(agent_file)
                self._agents[definition.identity.id] = definition

    def get(self, agent_id: str) -> AgentDefinition | None:
        return self._agents.get(agent_id)

    def all(self) -> list[AgentDefinition]:
        return list(self._agents.values())

    def __len__(self) -> int:
        return len(self._agents)
