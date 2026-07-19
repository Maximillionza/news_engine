# Plugin Registry

Index of all known plugins and their metadata.

**Spec:** Specifications/4 - future-expansion/Enterprise Plugin Architecture Specification (EPAS).md sec.6-10

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 10, post-MVP Expansion Layer). This
directory holds no code - the registry logic lives at `services/plugin_service/` (the same
data-directory-vs-service-code split CRBS already uses for `departments/` +
`orchestrator/department_registry.py`). `plugin_service/registry.py` implements EPAS
sec.18's MVP Plugin Requirements: registration, a Schema Check + minimal Security Review
(`validate_plugin()`), explicit human-triggered approve/activate/disable transitions, and
Agent Plugin Access (sec.10: `grant_agent_access()`/`agent_has_access()`, logged via the
existing `security_service` audit trail). Capability Test and Integration Test (sec.8) are
named, not implemented - no plugin runtime exists anywhere in this corpus to test against.

**Tests:** `Tests/integration/test_plugin_service.py`
