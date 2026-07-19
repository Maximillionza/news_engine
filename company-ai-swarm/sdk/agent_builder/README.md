# Agent Builder

SDK module for creating new agents.

**Spec:** Specifications/4 - future-expansion/Enterprise SDK Architecture Specification (ESDKS).md sec.5.1, sec.7, sec.8

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 10, post-MVP Expansion Layer).
`builder.py`'s `build_agent()` runs an `AgentDraft` through ESDKS sec.7's Validation Pipeline
end to end: Schema Validation (`agent_runtime.registry.AgentDefinition`'s own Pydantic
validation), Security Review (department must exist; identity created + permissioned
through the unmodified Phase 1 chain), Capability Test (a real smoke-test execution through
the unmodified Phase 4 `AgentRuntime` - this is also Phase 10's own exit criterion, not a
separate invented check), Architecture Check (no agent-id collision), Activate (`agent.yaml`
written to disk under a caller-supplied root, and registered directly into the given
in-memory `AgentRegistry`). No core runtime code is touched - `AgentDefinition`,
`AgentRegistry`, `AgentRuntime`, `DepartmentRegistry`, `identity_service`, and
`security_service` are all reused exactly as Phases 1-4 built them.

**Tests:** `Tests/integration/test_sdk_agent_builder.py`
