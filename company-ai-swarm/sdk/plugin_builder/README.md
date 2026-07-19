# Plugin Builder

SDK module for creating new plugins.

**Spec:** Specifications/4 - future-expansion/Enterprise Plugin Architecture Specification (EPAS).md sec.12 ("The SDK creates plugins")

**Status:** Still a placeholder as of Phase 10. Plugin creation currently goes straight
through `services/plugin_service.registry.register_plugin()` (see
`plugins/registry/README.md`), which already performs its own Schema Check inline - there
was no separate draft/validation object worth building here yet, unlike
`agent_builder`/`capability_builder`/`workflow_builder`, each of which wraps a Pydantic
schema plus `sdk/validation`'s report shape. Revisit if plugin creation grows enough
distinct pre-registration logic (e.g. a real Capability/Integration Test against a live
plugin runtime, once one exists) to justify a dedicated builder.
