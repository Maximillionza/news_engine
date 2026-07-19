"""Knowledge Graph recording for workflow execution.

Source: Specifications/1 - enterprise-architecture/Enterprise Knowledge Graph Specification
(EKGS).md sec.5 (Object Model), Universal Ontology (UOL) sec.6 (relationship types).
IMPLEMENTATION_PLAN.md Phase 7 deliverable: "Knowledge Graph service, wired to record
entities and relationships produced by workflow execution." Storage itself (knowledge_service)
was already built in Phase 2; this module is the wiring, not new storage.

For every completed task, records the path IMPLEMENTATION_PLAN.md's own Phase 7 test names:

    Agent --USES--> Capability --APPLIES_TO--> Workflow

Phase 7 scope: one Capability recorded per task - the department's first-listed capability,
not every capability a task might have drawn on. TDL sec.9's Capability Requirements model
(tasks request capabilities, not departments) isn't implemented at that granularity yet; this
mirrors the same task-decomposition honesty already documented in workflow_engine/engine.py
(one Task per department, not per fine-grained capability).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from agent_runtime.registry import AgentDefinition
from knowledge_service.repository import create_relationship, get_or_create_entity
from orchestrator.department_registry import DepartmentDefinition


def record_task_knowledge(
    session: Session,
    *,
    workflow_id: str,
    objective: str,
    department: DepartmentDefinition,
    agent: AgentDefinition,
) -> None:
    agent_entity = get_or_create_entity(
        session, id=f"agent:{agent.identity.id}", object_type="Agent", name=agent.identity.name
    )

    capability_name = department.capabilities[0] if department.capabilities else department.id
    capability_entity = get_or_create_entity(
        session,
        id=f"capability:{department.id}:{capability_name}",
        object_type="Capability",
        name=capability_name,
    )

    workflow_entity = get_or_create_entity(
        session, id=f"workflow:{workflow_id}", object_type="Workflow", name=objective
    )

    create_relationship(
        session,
        source_entity_id=agent_entity.id,
        relationship_type="USES",
        target_entity_id=capability_entity.id,
    )
    create_relationship(
        session,
        source_entity_id=capability_entity.id,
        relationship_type="APPLIES_TO",
        target_entity_id=workflow_entity.id,
    )
