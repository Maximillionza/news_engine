"""SDK Capability Builder.

Source: Specifications/4 - future-expansion/Enterprise SDK Architecture Specification
(ESDKS).md sec.5.3: defines reusable enterprise abilities. Schema: name, description,
inputs, outputs, required_tools, complexity, evaluation.

Phase 10 scope: Schema Validation only (ESDKS sec.7's Security Review/Capability
Test/Architecture Check gates apply to running components like agents - a capability
definition has no runtime to test or activate). Not yet wired into department/agent
capability MATCHING elsewhere in this codebase (orchestrator/planner.py's
select_all_matching_departments, orchestrator/allocator.py) - those still compare plain
capability strings, a known weakness documented since Phase 5/6. This richer object is a
real step toward closing that gap, not a claim it's already closed.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from validation.pipeline import ValidationReport


class Capability(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    # TDL sec.7's own tier vocabulary - see orchestrator/planner.py for why this is a fixed
    # default everywhere else in this corpus too (no numeric complexity algorithm exists).
    complexity: str = "Level 2 Standard"
    evaluation: dict = Field(default_factory=dict)


def build_capability(**fields: object) -> Capability:
    report = ValidationReport()
    try:
        capability = Capability(**fields)
        report.record("schema_validation", passed=True)
    except Exception as exc:  # noqa: BLE001 - record() raises ComponentValidationError from here
        report.record("schema_validation", passed=False, detail=str(exc))
    return capability
