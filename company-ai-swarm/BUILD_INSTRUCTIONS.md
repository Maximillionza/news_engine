# The Company — Build Instructions

This file is a pointer, not a duplicate. Build sequencing is defined in `Specifications/3 - execution-framework/`.

## Source documents

- `IMPLEMENTATION_PLAN.md` (repository root) — the concrete, milestone-based, independently-testable phase plan. Start here.
- `AI Builder Master Execution Package (ABMEP).md` — 12-phase build sequence and acceptance criteria per phase.
- `Claude Code Bootstrap Package (CCBP).md` — the first ten commands for an AI builder, technology decisions, definition of done.
- `Runtime Contract Specification (RCS).md` — interface contracts that must exist before implementing any component.
- `MVP Validation Specification (MVS).md` — the acceptance test suite that defines when the MVP is complete.

## Current state

Repository structure only. No services, agents, or workflows have been implemented. Each leaf directory contains either a `README.md` explaining its purpose and owning specification, or a configuration template (`*.yaml`) with no executable logic.

## Next step

Follow `IMPLEMENTATION_PLAN.md` Phase 0 (Foundation & Contracts) before writing any service code: interface contracts, identity, and the data layer precede the Agent Runtime and COO Orchestrator (Phases 4–5).
