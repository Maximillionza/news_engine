# Identity Service

Manages identity for humans, agents, and services.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Security and Trust Architecture Specification (ESTAS).md

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 1). Provides `create_identity` and
`get_identity`. Identity lifecycle transitions beyond create/active (suspend, retire) are not
yet implemented -- out of Phase 1 scope.

**Tests:** `Tests/security/test_mvs_007_security_validation.py`
