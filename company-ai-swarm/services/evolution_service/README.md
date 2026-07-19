# Evolution Service

The Evolution Engine: detects inefficiencies, requests simulations, and proposes
improvements - with human approval as a hard gate.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Evolution & Self-Improvement Specification (EESIS).md sec.5-14, sec.17

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 11, post-MVP Intelligence Systems).
This is the piece Phase 11's own exit test (MVS Test Category 011) exercises end to end.

- `models.py` - `ImprovementOpportunity` (EESIS sec.7) and `ChangeProposal` (EESIS sec.8),
  modeled literally.
- `detection.py` - `detect_inefficiencies()` reuses `orchestrator/escalation.py`'s
  GATE_INTEGRITY_SUPERFICIAL condition (Phase 8) - a review that ran with nothing to review
  - as the one real, already-produced inefficiency signal in this codebase. Not a synthetic
  inefficiency invented for this phase; not a second detection mechanism either.
- `pipeline.py` - `EvolutionEngine`: `detect_and_propose()` (Analyse -> Request simulation ->
  Propose, EESIS sec.11) always creates a `PENDING` proposal - nothing in this class can set
  it to `APPROVED` directly. `approve_change()`/`reject_change()` require an identity that
  passes `security_service.authorize()` against `evolution:change_proposal` - the engine's
  own identity is never granted this by anything in this codebase, so it structurally cannot
  approve its own proposals (EESIS sec.10, ESTAS sec.21). `implement_change()` raises unless
  the proposal is already `APPROVED`, and writes an EESIS sec.14 Evolution Memory record via
  `memory_service.write_memory()` at the Historical tier - reusing Phase 9's Learn-step
  infrastructure rather than a parallel mechanism. This does **not** automatically mutate
  `workflow_engine`'s runtime behaviour for future objectives - see the module docstring for
  why that's named as real, separate follow-up work rather than claimed here, mirroring
  Phase 9's own precedent that an approved lesson promotion writes memory, it doesn't
  automatically change agent behaviour either.

**Tests:** `Tests/integration/test_evolution_engine.py`
