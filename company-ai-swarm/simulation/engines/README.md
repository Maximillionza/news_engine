# Simulation Engines

Scenario, forecasting, and optimization engines.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Simulation & Digital Twin Specification (ESDTS).md sec.11

**Status:** Partially implemented (IMPLEMENTATION_PLAN.md Phase 11, post-MVP Intelligence
Systems). Only the Workflow Simulation Engine is built -
`services/simulation_service/workflow_simulation.py` (real dry-run execution through the
unmodified `workflow_engine`, in an isolated sandbox - see that service's README for detail).
The Scenario Generator, Behaviour Simulation Engine, and Resource Simulation Engine
(ESDTS sec.11) are not implemented.

**Tests:** `Tests/integration/test_digital_twin_and_simulation.py`
