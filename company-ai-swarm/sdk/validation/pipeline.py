"""SDK Component Validation Pipeline.

Source: Specifications/4 - future-expansion/Enterprise SDK Architecture Specification
(ESDKS).md sec.7:

    Component Created -> Schema Validation -> Security Review -> Capability Test ->
    Architecture Check -> Activate

Phase 10 scope (IMPLEMENTATION_PLAN.md, post-MVP Expansion Layer): this module is the
generic report/fail-fast shape every builder records its steps into.
`sdk/agent_builder/builder.py` is the only consumer that exercises all five gates - it is
also the only SDK component IMPLEMENTATION_PLAN.md's own Phase 10 test requires
("confirm it registers in the Agent Registry and executes a task successfully"), which maps
directly onto Schema Validation + Security Review + Capability Test + Activate below.
`sdk/capability_builder/` and `sdk/workflow_builder/` only exercise Schema Validation - they
produce definitions, not running components, so there is nothing to Capability-Test or
Architecture-Check yet (see their own module docstrings).
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ComponentValidationError(Exception):
    """Raised by the first failing step - the pipeline is fail-fast, per ESDKS sec.7's own
    linear Design -> Generate -> Validate -> ... -> Activate shape (sec.6): a component that
    fails Schema Validation is never subjected to a Security Review, etc."""


@dataclass
class ValidationStep:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ValidationReport:
    steps: list[ValidationStep] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.steps) and all(s.passed for s in self.steps)

    def record(self, name: str, *, passed: bool, detail: str = "") -> None:
        self.steps.append(ValidationStep(name=name, passed=passed, detail=detail))
        if not passed:
            raise ComponentValidationError(f"{name} failed: {detail}")
