"""SDK Workflow Builder.

Source: Specifications/4 - future-expansion/Enterprise SDK Architecture Specification
(ESDKS).md sec.5.4: creates repeatable business processes. Schema: name, trigger, steps,
dependencies, agents, validation.

Phase 10 scope: Schema Validation only, same reasoning as capability_builder.py. Not yet
consumed by workflow_engine.execute_workflow() (Phase 6/7), whose task list is still derived
from department keyword-matching (orchestrator/classification.py, originally
orchestrator/planner.py), not from a stored WorkflowTemplate - a named gap, not silently
dropped. A future phase could add "run this
stored template" as an alternate Workflow Engine entry point without touching
execute_workflow()'s existing, tested behaviour.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from validation.pipeline import ValidationReport


class WorkflowStep(BaseModel):
    name: str = Field(..., min_length=1)
    required_capability: str = ""


class WorkflowTemplate(BaseModel):
    name: str = Field(..., min_length=1)
    trigger: str = ""
    steps: list[WorkflowStep] = Field(default_factory=list)
    # Step name -> prerequisite step names (EWOS sec.5's `Dependencies` field, still not
    # consumed by any resolver anywhere in this corpus - see workflow_engine/engine.py).
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    agents: list[str] = Field(default_factory=list)
    validation: str = ""


def build_workflow_template(**fields: object) -> WorkflowTemplate:
    report = ValidationReport()
    try:
        template = WorkflowTemplate(**fields)
        report.record("schema_validation", passed=True)
    except Exception as exc:  # noqa: BLE001 - record() raises ComponentValidationError from here
        report.record("schema_validation", passed=False, detail=str(exc))
    return template
