"""Agent Allocation Engine.

Source: Specifications/1 - enterprise-architecture/The Company COO Orchestrator
Specification (COOS).md sec.13:

    Capability Match + Performance History + Availability + Cost + Risk

Phase 5 honesty note: only Capability Match is implemented. Performance History requires
accumulated task outcomes (none exist yet - this is the first task ever run through the
COO); Availability requires concurrent-task tracking (Phase 5 is single-task, sequential);
Cost and Risk require the Reasoning Tier / Resource Economics machinery documented as not
yet implemented in Documentation/operations/technology_decisions.md. Each factor is a real
gap to fill as the corresponding capability gets built, not silently assumed away.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_runtime.registry import AgentDefinition, AgentRegistry
from orchestrator.department_registry import DepartmentDefinition


@dataclass
class AllocationResult:
    agent: AgentDefinition
    reasoning: str


def select_agent(
    department: DepartmentDefinition, agent_registry: AgentRegistry
) -> AllocationResult:
    """Phase 5 scope: exactly one agent per department, so "allocation" is selecting the
    single agent belonging to the given department. Generalizes cleanly to Phase 6+ (multiple
    agents per department) once Performance History/Availability/Cost/Risk data exists to
    choose between them - see module docstring."""

    if not department.agents:
        raise ValueError(f"Department '{department.id}' has no agents assigned.")

    candidates = [agent_registry.get(agent_id) for agent_id in department.agents]
    available = [a for a in candidates if a is not None]

    if not available:
        raise ValueError(
            f"Department '{department.id}' lists agents {department.agents}, but none are "
            f"registered in the Agent Registry."
        )

    chosen = available[0]
    return AllocationResult(
        agent=chosen,
        reasoning=(
            f"Capability match: '{chosen.identity.id}' is the agent assigned to department "
            f"'{department.id}', whose capabilities ({department.capabilities}) matched the "
            f"objective. Performance History, Availability, Cost, and Risk were not "
            f"evaluated (see module docstring)."
        ),
    )
