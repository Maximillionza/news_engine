# Marketplace Registry

Index of reusable capabilities available for discovery.

**Spec:** Specifications/4 - future-expansion/Enterprise Marketplace Architecture Specification (EMAS).md sec.6-10, sec.13

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 10, post-MVP Expansion Layer). This
directory holds no code - the registry logic lives at `services/marketplace_service/`, same
split as `plugins/registry/`. `marketplace_service/registry.py` implements EMAS sec.20's MVP
Marketplace Requirements: asset submission/validation/publishing across the four asset types
(Agent/Workflow/Plugin/Capability Packages), search by name/capability/type (sec.10's
Performance/Compatibility/Risk-level search dimensions are not implemented - none of that
data is tracked), and evaluation tracking (`record_evaluation()`/
`average_evaluation_score()` - a running average, not sec.13's Capability Ranking formula,
which doesn't exist anywhere in this corpus). `validate_asset()` performs Architecture
Validation and a minimal Security Validation; Technical and Performance Validation (sec.9)
are named, not implemented - they'd require executing the packaged asset.

**Tests:** `Tests/integration/test_marketplace_service.py`
