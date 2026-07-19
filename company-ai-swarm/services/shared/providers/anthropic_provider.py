"""AnthropicModelProvider: real Claude reasoning via the raw Claude Messages API.

Source: Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.1. Implements the same
`shared.model_gateway.ModelProvider` protocol as StubModelProvider - `ModelGateway` and
everything upstream of it (AgentRuntime, orchestrator/controller.py) is unchanged by this
swap, per model_gateway.py's "swap without touching callers" invariant.

Bills per-token against ANTHROPIC_API_KEY (or an Anthropic-compatible base URL). Cannot use
Claude subscription billing - that requires going through the Agent SDK/CLI instead, see
AgentSDKModelProvider (agent_sdk_provider.py) and the billing correction in
SDK_MIGRATION_PLAN.md Section 1.

The `anthropic` package is an optional dependency (pyproject.toml `providers` extra) so the
rest of the codebase can be installed and tested without it, matching the dev/test
substitution pattern used throughout (StubModelProvider needs no external package either).
It is imported lazily, inside `_default_client_factory`, not at module load time - so this
module remains importable, and `client_factory` remains overridable in tests, even when
`anthropic` isn't installed.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Protocol

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 4096


class AnthropicProviderError(Exception):
    """Raised when the Claude API call fails, or the `anthropic` package isn't installed."""


class _MessagesClient(Protocol):
    """The minimal shape this provider needs from an `anthropic.Anthropic()` client -
    documented here so a test's fake client only has to implement this, not the real
    package's full surface."""

    messages: Any


def _default_client_factory(api_key: str, *, base_url: str | None) -> _MessagesClient:
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - exercised only when the extra isn't installed
        raise AnthropicProviderError(
            "The 'anthropic' package is required for AnthropicModelProvider. "
            "Install it with: pip install 'the-company[providers]' (or: pip install anthropic)"
        ) from exc

    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return anthropic.Anthropic(**kwargs)


class AnthropicModelProvider:
    """Implements `shared.model_gateway.ModelProvider` by calling the Claude Messages API
    directly (`client.messages.create(...)`), one request per `generate()` call - no
    conversation history, no tool use; ModelGateway.generate()'s caller
    (AgentRuntime.execute_task's Execute step) already builds one self-contained prompt per
    call, so there is nothing to carry across turns here."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        base_url: str | None = None,
        client_factory: Callable[..., _MessagesClient] = _default_client_factory,
    ) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise AnthropicProviderError(
                "AnthropicModelProvider requires an API key: pass api_key=, or set "
                "ANTHROPIC_API_KEY."
            )
        self._model = model
        self._max_tokens = max_tokens
        self._client = client_factory(resolved_key, base_url=base_url)

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except AnthropicProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - ModelGateway.generate() records + re-raises
            raise AnthropicProviderError(f"Claude API call failed: {exc}") from exc

        text_blocks = [
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ]
        if not text_blocks:
            raise AnthropicProviderError(
                f"Claude API returned no text content (stop_reason={getattr(response, 'stop_reason', None)!r})."
            )
        return "".join(text_blocks)
