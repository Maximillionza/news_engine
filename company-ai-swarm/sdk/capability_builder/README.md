# Capability Builder

SDK module for creating new capabilities.

**Spec:** Specifications/4 - future-expansion/Enterprise SDK Architecture Specification (ESDKS).md sec.5.3

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 10, post-MVP Expansion Layer).
`builder.py`'s `build_capability()` validates and returns a `Capability` object (name,
description, inputs, outputs, required_tools, complexity, evaluation) - Schema Validation
only, see the module docstring for why the other pipeline gates don't apply. **Not yet wired
into department/agent capability matching** (`orchestrator/classification.py`, originally
`orchestrator/planner.py`; `orchestrator/allocator.py`) - those still compare plain
capability strings, a known weakness documented since Phase 5/6. This is a real step
toward closing that gap, not a
claim it's already closed.

**Tests:** `Tests/unit/test_sdk_capability_and_workflow_builders.py`
