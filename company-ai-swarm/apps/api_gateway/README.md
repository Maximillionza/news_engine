# API Gateway

External entry point routing requests into The Company.

**Spec:** Specifications/4 - future-expansion/Enterprise API Architecture Specification (EAAS).md sec.18

**Status:** Phase 0 built only `/health`. Phase 10 (IMPLEMENTATION_PLAN.md, post-MVP
Expansion Layer) wires this to the already-built `COOOrchestrator` (Phases 5-9) - no new
orchestration logic, this is the external HTTP surface over what already exists. Implements
EAAS sec.18's MVP API Requirements:

- `POST /objectives` - Objective submission, via the unmodified `COOOrchestrator.receive_objective()`.
- `GET /objectives/{decision_id}` - Task tracking / Workflow status / Result retrieval, from the existing COOS sec.22 Decision Record.
- `GET /agents` - Agent visibility, from the existing `AgentRegistry`.
- Authentication: a single static `X-API-Key` header check - explicitly a placeholder, not
  OAuth/JWT/session-based auth; EAAS sec.18 requires "Authentication" exist, not a specific
  scheme. Swap when a real identity provider is wired in.
- Audit logging: reuses `security_service`'s existing audit trail - no second mechanism.

Dev/test: a SQLite file next to `main.py` (gitignored), same substitution pattern as every
other service. Production: the already-provisioned Postgres instance (`docker-compose.yml`).

**Tests:** `Tests/integration/test_api_gateway_health.py` (Phase 0),
`Tests/integration/test_api_gateway_objectives.py` (Phase 10).
