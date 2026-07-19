# Digital Twin State

Current and historical state snapshots.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Simulation & Digital Twin Specification (ESDTS).md sec.6

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 11, post-MVP Intelligence Systems).
This directory holds no code - snapshots are rows in `digital_twin_snapshots`
(`services/digital_twin_service/models.py`), following the same data-dir/service-code split
as `departments/` + `orchestrator/department_registry.py`.

**Tests:** `Tests/integration/test_digital_twin_and_simulation.py`
