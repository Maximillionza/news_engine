# Observability Service

Collects metrics, logs, and traces across the enterprise.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Observability and Control Plane Specification (EOCCS).md

**Status:** `telemetry.py` (Phase 3): `TelemetrySink` provides `record`/`query` per RCS
sec.18 (component, action, timestamp, duration, result, error) and EOCCS sec.6. Phase 8
added the query layer beneath EOCCS sec.21's Enterprise Command Centre - no dashboard/
frontend exists, these are the dataclasses one would query:

- `views.py` - `director_view`/`coo_view`/`department_view` (EOCCS sec.22-24), read-only
  aggregations over `TelemetrySink` plus `orchestrator`'s Decision and Escalation Records.
  Fields sec.22-24 name that need data this codebase doesn't track yet (Director's
  "Long-term trends," COO's "Resource utilization"/"Agent availability," Department's
  "Demand"/"Knowledge growth") are documented as not populated, not faked - see module
  docstring.
- `alerting.py` - `generate_alerts()` (EOCCS sec.25's Information/Warning/High Risk/Critical
  ladder), rule-based over telemetry DENIED/FAILURE records and unresolved Escalation
  Records. Thresholds are illustrative defaults, not tuned from real operational data - same
  honesty as every other fixed-default decision in this corpus.

**Tests:** `Tests/integration/test_communication_backbone.py` (Phase 3),
`Tests/integration/test_observability_platform.py` (Phase 8, MVS-009 + views + alerting).
