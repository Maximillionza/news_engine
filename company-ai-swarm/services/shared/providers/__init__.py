"""Real ModelProvider implementations, plus an env-var-driven factory for selecting one.

Source: Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.1 ("ModelGateway.__init__()
gets env var support: MODEL_PROVIDER=anthropic vs agent_sdk vs stub"). `ModelGateway` itself
still takes an already-constructed provider (shared/model_gateway.py's existing contract -
"the ONLY object in the codebase permitted to hold a reference to a ModelProvider" is about
agents never touching a provider directly, not about ModelGateway constructing one itself),
so the env-var switch lives here as a factory, used at the one call site that currently
hardcodes StubModelProvider() - apps/api_gateway/main.py.
"""

from __future__ import annotations

import os
from typing import Mapping

from shared.model_gateway import ModelProvider, StubModelProvider

from .agent_sdk_provider import AgentSDKModelProvider, AgentSDKProviderError
from .anthropic_provider import AnthropicModelProvider, AnthropicProviderError

_PROVIDERS = ("stub", "anthropic", "agent_sdk")


def create_provider_from_env(env: Mapping[str, str] | None = None) -> ModelProvider:
    """Reads `MODEL_PROVIDER` (default: "stub") and returns the matching provider.

    - "stub"      -> StubModelProvider() - no credentials, no network, dev/test default.
    - "anthropic" -> AnthropicModelProvider() - reads ANTHROPIC_API_KEY, per-token billing.
    - "agent_sdk" -> AgentSDKModelProvider() - reads Claude Code's own credential precedence
                     chain (CLAUDE_CODE_OAUTH_TOKEN if set, else ANTHROPIC_API_KEY); the one
                     that can draw on a Claude subscription instead of API billing.

    Raises ValueError for anything else, so a typo in the env var fails at startup rather
    than silently falling back to the stub.
    """

    source = env if env is not None else os.environ
    selected = source.get("MODEL_PROVIDER", "stub").strip().lower()

    if selected == "stub":
        return StubModelProvider()
    if selected == "anthropic":
        # Threaded through explicitly (not left to AnthropicModelProvider's own
        # os.environ.get() fallback) so an injected `env` mapping - e.g. a test's fake env -
        # is actually honored end-to-end, rather than silently falling back to whatever the
        # real process environment happens to contain.
        return AnthropicModelProvider(api_key=source.get("ANTHROPIC_API_KEY"))
    if selected == "agent_sdk":
        return AgentSDKModelProvider()

    raise ValueError(
        f"Unknown MODEL_PROVIDER={selected!r}; expected one of {_PROVIDERS}."
    )


__all__ = [
    "AgentSDKModelProvider",
    "AgentSDKProviderError",
    "AnthropicModelProvider",
    "AnthropicProviderError",
    "create_provider_from_env",
]
