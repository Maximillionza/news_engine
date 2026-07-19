"""AgentSDKModelProvider: real Claude reasoning via the Claude Agent SDK, not the raw API.

Source: Documentation/plans/SDK_MIGRATION_PLAN.md Section 1 (billing correction) and
Section 4.1. Implements the same `shared.model_gateway.ModelProvider` protocol as
StubModelProvider and AnthropicModelProvider - `ModelGateway` and everything upstream of it
is unchanged by this swap.

Why this exists alongside AnthropicModelProvider: the Agent SDK (`claude_agent_sdk.query`)
resolves credentials via Claude Code's own precedence chain - `ANTHROPIC_API_KEY` /
`ANTHROPIC_AUTH_TOKEN` / `apiKeyHelper`, then `CLAUDE_CODE_OAUTH_TOKEN` (generated once via
`claude setup-token`), then a plain `/login` subscription session. Only this provider can
draw on a personal Claude Pro/Max/Team/Enterprise subscription instead of per-token API
billing - the raw `anthropic` client `AnthropicModelProvider` uses only ever accepts an API
key. See SDK_MIGRATION_PLAN.md Section 1 for the caveats that apply (single-Director/
personal use only; any other user's traffic must move to API-key billing).

`query()` is async; `ModelProvider.generate()` is synchronous (AgentRuntime and
ModelGateway are both sync code), so `generate()` bridges with `asyncio.run()`.

The `claude-agent-sdk` package is an optional dependency (pyproject.toml `providers` extra),
imported lazily inside `_default_runner` so this module stays importable, and `runner`
remains overridable in tests, without the package installed.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Sequence


class AgentSDKProviderError(Exception):
    """Raised when the Agent SDK query fails, or the `claude-agent-sdk` package isn't
    installed."""


async def _default_runner(prompt: str, allowed_tools: Sequence[str]) -> str:
    try:
        from claude_agent_sdk import ClaudeAgentOptions, query
    except ImportError as exc:  # pragma: no cover - exercised only when the extra isn't installed
        raise AgentSDKProviderError(
            "The 'claude-agent-sdk' package is required for AgentSDKModelProvider. "
            "Install it with: pip install 'the-company[providers]' (or: pip install claude-agent-sdk)"
        ) from exc

    # No --bare here: this calls the SDK's query() function directly, not a `claude -p
    # --bare` subprocess, so there is no bare-mode flag to accidentally set. The credential
    # precedence caveat still applies - see this module's docstring - but the specific
    # "--bare ignores CLAUDE_CODE_OAUTH_TOKEN" trap (SDK_MIGRATION_PLAN.md Section 1) is a
    # CLI-invocation concern, not one this code path can trigger.
    options = ClaudeAgentOptions(allowed_tools=list(allowed_tools))

    result_text: str | None = None
    async for message in query(prompt=prompt, options=options):
        # SystemMessage/AssistantMessage/etc. stream first; the terminal ResultMessage
        # carries `.result` (see agent-sdk quickstart's `if hasattr(message, "result")`).
        if hasattr(message, "result") and message.result:
            result_text = message.result
    if result_text is None:
        raise AgentSDKProviderError("Agent SDK query produced no result message.")
    return result_text


class AgentSDKModelProvider:
    """Implements `shared.model_gateway.ModelProvider` by invoking Claude through the Agent
    SDK harness (built-in tools + agent loop) rather than a single raw Messages API call.
    `allowed_tools` defaults to empty - a swarm agent's reasoning doesn't need Bash/Read/
    Edit access to the host filesystem; pass explicit tools only for agents that are meant
    to act on the local machine."""

    def __init__(
        self,
        *,
        allowed_tools: Sequence[str] = (),
        runner: Callable[[str, Sequence[str]], Awaitable[str]] = _default_runner,
    ) -> None:
        self._allowed_tools = tuple(allowed_tools)
        self._runner = runner

    def generate(self, prompt: str) -> str:
        try:
            return asyncio.run(self._runner(prompt, self._allowed_tools))
        except AgentSDKProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - ModelGateway.generate() records + re-raises
            raise AgentSDKProviderError(f"Agent SDK query failed: {exc}") from exc
