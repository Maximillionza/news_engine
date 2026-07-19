# Digital Twin Service

Point-in-time representation of enterprise state.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Simulation & Digital Twin Specification (ESDTS).md sec.4, sec.6, sec.31

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 11, post-MVP Intelligence Systems).
`snapshot.py`'s `capture_snapshot()` pulls real, current state from the already-built
`AgentRegistry`, `DepartmentRegistry`, and recent COO Decision Records into a persisted
`DigitalTwinSnapshot` - not a live-updating mirror, and not a mock. ESDTS sec.31's "Event
synchronisation" requirement is satisfied by capturing a fresh snapshot on demand, not a
continuous change-feed subscription - no durable event log exists anywhere in this corpus
(`event_service.InMemoryEventBus` is in-process pub/sub only).

**Tests:** `Tests/integration/test_digital_twin_and_simulation.py`
