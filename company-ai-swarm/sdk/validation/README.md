# SDK Validation

Validation pipeline shared by all SDK builders.

**Spec:** Specifications/4 - future-expansion/Enterprise SDK Architecture Specification (ESDKS).md sec.7

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 10, post-MVP Expansion Layer).
`pipeline.py`'s `ValidationReport`/`ValidationStep`/`ComponentValidationError` are the
generic, fail-fast report shape ESDKS sec.7's five-gate pipeline (Schema Validation ->
Security Review -> Capability Test -> Architecture Check -> Activate) records into.
`sdk/agent_builder/builder.py` is the only consumer that exercises all five gates - it is
also the only SDK component IMPLEMENTATION_PLAN.md's Phase 10 test requires.
`sdk/capability_builder/` and `sdk/workflow_builder/` only exercise Schema Validation - they
produce definitions, not running components, so there is nothing to Capability-Test or
Architecture-Check yet.

**Tests:** exercised indirectly via `Tests/integration/test_sdk_agent_builder.py` and
`Tests/unit/test_sdk_capability_and_workflow_builders.py` - no dedicated test file of its own.
