# Workflow Builder

SDK module for creating new workflows.

**Spec:** Specifications/4 - future-expansion/Enterprise SDK Architecture Specification (ESDKS).md sec.5.4

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 10, post-MVP Expansion Layer).
`builder.py`'s `build_workflow_template()` validates and returns a `WorkflowTemplate` object
(name, trigger, steps, dependencies, agents, validation) - Schema Validation only, same
reasoning as `capability_builder`. **Not yet consumed by
`workflow_engine.execute_workflow()`** (Phase 6/7), whose task list is still derived from
department keyword-matching, not from a stored template - a named gap, not silently
dropped. A future phase could add "run this stored template" as an alternate Workflow
Engine entry point without touching `execute_workflow()`'s existing, tested behaviour.

**Tests:** `Tests/unit/test_sdk_capability_and_workflow_builders.py`
