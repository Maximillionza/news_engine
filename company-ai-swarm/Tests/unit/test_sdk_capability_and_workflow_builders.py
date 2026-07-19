"""Phase 10: sdk/capability_builder and sdk/workflow_builder (ESDKS sec.5.3/5.4). Schema
Validation only - see each module's docstring for why the other pipeline gates don't apply
to definitions with no runtime to test.
"""

from __future__ import annotations

import pytest

from capability_builder.builder import Capability, build_capability
from validation.pipeline import ComponentValidationError
from workflow_builder.builder import WorkflowStep, WorkflowTemplate, build_workflow_template


class TestCapabilityBuilder:
    def test_valid_capability_is_built(self) -> None:
        capability = build_capability(
            name="Regulatory Analysis",
            description="Assess regulatory applicability for a given activity.",
            inputs=["business_activity", "location"],
            outputs=["applicability_assessment"],
        )

        assert isinstance(capability, Capability)
        assert capability.name == "Regulatory Analysis"
        assert capability.complexity == "Level 2 Standard"

    def test_missing_name_fails_schema_validation(self) -> None:
        with pytest.raises(ComponentValidationError):
            build_capability(description="No name provided.")


class TestWorkflowBuilder:
    def test_valid_workflow_template_is_built(self) -> None:
        template = build_workflow_template(
            name="Research to Report",
            trigger="objective_received",
            steps=[
                WorkflowStep(name="Research", required_capability="research"),
                WorkflowStep(name="Report", required_capability="reporting"),
            ],
            dependencies={"Report": ["Research"]},
            agents=["research_agent_001"],
        )

        assert isinstance(template, WorkflowTemplate)
        assert [s.name for s in template.steps] == ["Research", "Report"]
        assert template.dependencies["Report"] == ["Research"]

    def test_missing_name_fails_schema_validation(self) -> None:
        with pytest.raises(ComponentValidationError):
            build_workflow_template(trigger="x")
