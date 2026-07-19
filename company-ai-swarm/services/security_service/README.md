# Security Service

Enforces authentication, authorization, and audit.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Security and Trust Architecture Specification (ESTAS).md

**Status:** `permissions.py`/`audit.py` (Phase 1): `authorize()` (Identity Check -> Permission
Check -> audit, per ESTAS sec.10 - Risk Assessment moved to the COO's four-condition
escalation policy in Phase 8, see `orchestrator/escalation.py`, rather than living here),
`grant_permission()`, and an audit trail queryable by actor. Phase 8 added:

- `trust.py` - `compute_trust_score()`/`update_trust_level()` (ESTAS sec.26). Only "Error
  rate" (denied-decision ratio from the actor's own audit trail) is computed - Compliance
  performance, Security behaviour, and Validation results all need machinery this corpus
  doesn't build (see module docstring). Trust level is computed and persisted onto
  `Identity.trust_level`; wiring it to actually influence Permissions/Review
  requirements/Resource allocation (ESTAS sec.26's last paragraph) is not done in this pass.
- `incidents.py` - `open_incident()`/`advance_incident()` (ESTAS sec.27-28's seven-stage
  Incident Workflow: Detection -> Classification -> Containment -> Investigation ->
  Remediation -> Review -> Knowledge Update), forward-only, one stage at a time. Opened
  explicitly by whatever detects a security-relevant event - not wired into
  `orchestrator/escalation.py`'s four-condition policy, a distinct concern (workflow
  governance verdicts vs. security events) per ESTAS's own Trust/Authority/Autonomy
  separation.

Prompt-injection defence and agent behaviour monitoring (ESTAS sec.22-23) are still not
implemented.

**Tests:** `Tests/security/test_mvs_007_security_validation.py` (Phase 1),
`Tests/security/test_trust_and_incidents.py` (Phase 8).
