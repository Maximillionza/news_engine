# Digital Twin Synchronisation

Event-driven synchronisation from operational systems.

**Spec:** Specifications/1 - enterprise-architecture/Enterprise Simulation & Digital Twin Specification (ESDTS).md sec.31 ("Event synchronisation")

**Status:** Partially implemented (IMPLEMENTATION_PLAN.md Phase 11, post-MVP Intelligence
Systems). `services/digital_twin_service/snapshot.py`'s `capture_snapshot()` synchronises
on demand - it pulls current state fresh every time it's called, it does not subscribe to a
continuous change feed. No durable event log exists anywhere in this corpus
(`event_service.InMemoryEventBus` is in-process pub/sub only, not a change log a snapshot
process could tail) - true event-driven synchronisation is real, separate follow-up work.
