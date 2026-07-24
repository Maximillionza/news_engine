"""Model Gateway.

Source: Specifications/2 - construction-framework/Resource Definition Language (RDL).md
sec.11 ("Model Routing Engine SHALL select models dynamically") and sec.14 ("Agent-Model
Relationship... Agents SHALL not directly depend on individual models"), and EIAS sec.11
("Models SHALL not be directly called by agents. Required pattern: Agent -> Model Gateway ->
Available Models").

This is the ONLY object in the codebase permitted to hold a reference to a ModelProvider.
AgentRuntime (agent_runtime/runtime.py) is constructed with a ModelGateway and never with a
provider directly - there is no code path by which an agent can reach a model except through
`ModelGateway.generate()`. IMPLEMENTATION_PLAN.md Phase 4 exit criteria requires this to be
"verifiably enforced" - see Tests/integration/test_agent_runtime.py for the enforcement test.

Dev/test provider: StubModelProvider, deterministic, no external API calls, no network
access, no API key required. Production swaps in a real provider (Claude, GPT, etc.)
implementing the same ModelProvider protocol - same substitution pattern as every other
Phase 0-3 infrastructure module.
"""

from __future__ import annotations

import time
from typing import Protocol

from observability_service.telemetry import TelemetryResult, TelemetrySink, default_sink


class ModelProvider(Protocol):
    """Anything a ModelGateway can route to. Real providers (Claude, GPT, ...) implement
    this same shape; nothing else in the codebase is allowed to call `generate` on a
    provider directly.

    `allowed_tools` (Phase 12, IMPLEMENTATION_PLAN.md, 2026-07-23): the calling agent's own
    per-call tool allowlist (from its AgentDefinition.tools["available"] - see
    agent_runtime/runtime.py's Execute step), not a provider-level setting. Empty by default
    - most providers/agents don't need it, and a provider that has no concept of tool use
    (AnthropicModelProvider's raw Messages API call) accepts and ignores it rather than
    erroring, so this stays a single shared Protocol every provider implements identically."""

    def generate(self, prompt: str, *, allowed_tools: list[str] | None = None) -> str: ...


class StubModelProvider:
    """Deterministic dev/test provider. Not connected to any real model."""

    def generate(self, prompt: str, *, allowed_tools: list[str] | None = None) -> str:
        return f"[stub model output for prompt of length {len(prompt)}]"


class ModelGateway:
    """RDL sec.11 Model Routing Engine, minimal Phase 4 form: single registered provider,
    no dynamic tier-based routing yet (that needs the Reasoning Tier Classification from
    RDL sec.8 wired to real task-complexity scoring, which doesn't exist until the COO does
    in Phase 5 - see COOS sec.9's note that no numeric complexity algorithm exists in the
    source corpus). The abstraction boundary is what Phase 4 needs; the routing logic can
    grow later without changing any caller.
    """

    def __init__(self, provider: ModelProvider, telemetry: TelemetrySink | None = None) -> None:
        self._provider = provider
        self._telemetry = telemetry if telemetry is not None else default_sink
        self.call_count = 0

    def replace_provider(self, provider: ModelProvider) -> None:
        """Phase 9 addition (MVS sec.14 Test Category 010, Failure Recovery): hot-swaps the
        underlying provider without requiring any caller (AgentRuntime, workflow_engine, ...)
        to change - the same "swap without touching callers" principle already stated above
        for the dev/test-to-production substitution. Manually triggered here, not an
        automated detect-and-recover daemon - EOCCS sec.20's "Automated Intervention" full
        loop (Detection -> ... -> Recovery) is not built; a human or operator code decides
        when to call this."""

        self._provider = provider

    def generate(self, *, requester: str, prompt: str, allowed_tools: list[str] | None = None) -> str:
        start = time.perf_counter()
        try:
            output = self._provider.generate(prompt, allowed_tools=allowed_tools)
        except Exception as exc:  # noqa: BLE001 - recorded, then re-raised
            self._telemetry.record(
                component="model_gateway",
                action=f"generate:{requester}",
                duration_ms=(time.perf_counter() - start) * 1000,
                result=TelemetryResult.FAILURE,
                error=str(exc),
            )
            raise
        self.call_count += 1
        self._telemetry.record(
            component="model_gateway",
            action=f"generate:{requester}",
            duration_ms=(time.perf_counter() - start) * 1000,
            result=TelemetryResult.SUCCESS,
        )
        return output
