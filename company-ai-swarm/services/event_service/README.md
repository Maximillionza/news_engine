# Event Service

Enterprise Event Bus for asynchronous, fact-based communication.

**Spec:** Specifications/3 - execution-framework/Runtime Contract Specification (RCS).md

**Status:** Implemented (IMPLEMENTATION_PLAN.md Phase 3). `InMemoryEventBus` provides
`publish`/`subscribe`; every publish is authorized through security_service.authorize()
using the event's own security_context before any subscriber runs, and every publish
(allowed or denied) produces a telemetry record. In-process pub/sub is a dev/test
substitute for Redis Streams -- see Documentation/operations/technology_decisions.md.

**Tests:** `Tests/integration/test_communication_backbone.py`
