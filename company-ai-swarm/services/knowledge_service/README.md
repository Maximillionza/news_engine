# Knowledge Service

Maintains the Enterprise Knowledge Graph.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Knowledge Graph Specification (EKGS).md

**Status:** Storage layer built in Phase 2 (`create_entity`, `create_relationship`,
`get_entity`, `get_relationships_for_entity`); Phase 7 added `get_or_create_entity` so
`services/workflow_engine/knowledge.py` can record entities that recur across separate
workflow runs (an Agent or Capability) without a duplicate-key error, and wired real
workflow-generated data into it for the first time (see `workflow_engine/`'s README). Still
not wired to a graph query/traversal engine or semantic search - relationships are queried
by entity ID only (`get_relationships_for_entity`), not by pattern or path; that's still
open, not claimed here.

**Tests:** `Tests/integration/test_knowledge_storage.py` (Phase 2, storage CRUD),
`Tests/integration/test_knowledge_graph_review.py` (Phase 7, entities/relationships produced
by real workflow execution).
