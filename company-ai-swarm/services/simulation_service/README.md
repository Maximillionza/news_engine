# Simulation Service

Experiments with The Company before changes reach production.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Simulation & Digital Twin Specification (ESDTS).md sec.9, sec.11, sec.12.5, sec.14

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 11, post-MVP Intelligence Systems).
Only the **Workflow Simulation Engine** (ESDTS sec.11/12.5) is built - Scenario Generator,
Behaviour Simulation Engine, and Resource Simulation Engine (sec.11) are not.
`workflow_simulation.py`'s `simulate_workflow_change()` is a real dry run, not a fabricated
prediction: both a baseline and a proposed department list are executed through the
unmodified `workflow_engine.execute_workflow()`, each against its own throwaway in-memory
database and freshly-granted identities - never the caller's real session - so a simulation
can never write production state (ESDTS sec.9's Environment Separation, taken literally).
Metrics (task count, telemetry record count, success) are measured from real execution.
`models.py`'s `SimulationRun` implements ESDTS sec.14's canonical `simulation_input`/
`simulation_output` schema (the spec's own text calls this the schema that "supersedes the
two other independently-drafted variants" elsewhere in the corpus). `confidence` is
deliberately low (0.4) and explained in `limitations` - no real model or business-outcome
measure exists anywhere in this corpus, so "predicted_results" means "observed dry-run
metrics," not a forecast.

**Tests:** `Tests/integration/test_digital_twin_and_simulation.py`
