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
from typing import Any, Awaitable, Callable, Sequence

from observability_service.telemetry import TelemetryResult, TelemetrySink

# Same reasoning as AnthropicModelProvider's DEFAULT_MODEL (services/shared/providers/
# anthropic_provider.py): one bounded, single-shot prompt per generate() call is Sonnet 5's
# sweet spot, not Opus's - doubly so here, since this provider's calls draw down a personal
# subscription's usage window rather than (or in addition to) per-token API cost.
DEFAULT_MODEL = "claude-sonnet-5"


class AgentSDKProviderError(Exception):
    """Raised when the Agent SDK query fails, or the `claude-agent-sdk` package isn't
    installed."""


def _describe_result_error(message: Any) -> str:
    """ResultMessage.api_error_status carries the real HTTP status (e.g. 429/500/529) when
    is_error=True but subtype stays "success" - a documented Agent SDK quirk where a
    transient API failure surfaces this way. Ported from the sibling Samaritan project's
    core/provider.py, which hit the same quirk. Prefer api_error_status when present; it's
    what actually explains an otherwise-opaque "returned an error result: success"-shaped
    message.

    Note: this only fires when the SDK actually yields a ResultMessage with is_error=True -
    a failure below that layer (e.g. a transport/control-channel error raised before any
    ResultMessage is produced) surfaces as a bare Exception from claude_agent_sdk itself,
    which this can't intercept; AgentSDKModelProvider.generate()'s broader except clause
    still catches those, just without this extra detail."""

    if getattr(message, "api_error_status", None) is not None:
        return (
            f"Agent SDK query failed with HTTP {message.api_error_status} from the "
            f"underlying API (result: {message.result!r})."
        )
    return f"Agent SDK query returned an error result: {message.result}"


async def _default_runner(
    prompt: str,
    allowed_tools: Sequence[str],
    model: str | None,
    *,
    on_tool_use: Callable[[str], None] | None = None,
) -> str:
    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            ServerToolUseBlock,
            ToolUseBlock,
            query,
        )
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
    #
    # setting_sources=[] is deliberate: with the default (None), the SDK discovers this
    # machine's user/project/local Claude Code settings - which, run from inside this very
    # repo, means a swarm agent's reasoning call would silently pick up The Company's own
    # .claude/ settings, hooks, or CLAUDE.md. A department agent executing a task has no
    # business inheriting the operator's personal Claude Code configuration; empty sources
    # keeps every call deterministic and isolated from whatever machine it happens to run on.
    options = ClaudeAgentOptions(
        allowed_tools=list(allowed_tools), model=model, setting_sources=[]
    )

    result_text: str | None = None
    async for message in query(prompt=prompt, options=options):
        # Phase 12 (IMPLEMENTATION_PLAN.md, 2026-07-23): AssistantMessage.content carries
        # ToolUseBlock (a CLI-side tool like WebSearch/Bash/Read) or ServerToolUseBlock (an
        # Anthropic-hosted server tool) entries when the model actually invokes a tool mid-
        # reasoning - this is the only place that's ever observable, since the terminal
        # ResultMessage below only carries the final text. on_tool_use is None unless the
        # caller (AgentSDKModelProvider.generate()) was constructed with a telemetry sink.
        if on_tool_use is not None and isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, (ToolUseBlock, ServerToolUseBlock)):
                    on_tool_use(block.name)

        # SystemMessage/AssistantMessage/etc. stream first; the terminal ResultMessage
        # carries `.result` and `.is_error` (see agent-sdk quickstart's
        # `if hasattr(message, "result")`). is_error must be checked explicitly - a prior
        # version of this loop only checked for a truthy `.result`, which would have
        # silently treated an error ResultMessage's result text as real output instead of
        # raising.
        if isinstance(message, ResultMessage):
            if message.is_error:
                raise AgentSDKProviderError(_describe_result_error(message))
            result_text = message.result
    if result_text is None:
        raise AgentSDKProviderError("Agent SDK query produced no result message.")
    return result_text


class AgentSDKModelProvider:
    """Implements `shared.model_gateway.ModelProvider` by invoking Claude through the Agent
    SDK harness (built-in tools + agent loop) rather than a single raw Messages API call.
    `allowed_tools` defaults to empty - a swarm agent's reasoning doesn't need Bash/Read/
    Edit access to the host filesystem; pass explicit tools only for agents that are meant
    to act on the local machine. `model=None` defers to whatever Claude Code itself
    defaults to (its own `/model` setting) rather than forcing DEFAULT_MODEL - pass
    `model=DEFAULT_MODEL` explicitly (or another model string) when this provider is
    selected specifically because it should behave like AnthropicModelProvider's choice.

    `allowed_tools` set here is the constructor-level default; Phase 12 (IMPLEMENTATION_PLAN.md,
    2026-07-23) lets `generate()`'s own `allowed_tools` (the calling agent's own
    `AgentDefinition.tools["available"]`, per `shared.model_gateway.ModelProvider`'s
    docstring) override it per call, since one shared provider instance serves every agent -
    see `shared/model_gateway.py`'s docstring on why there's only one.

    `telemetry`, if given, makes a real tool invocation observable: `generate()` records a
    `tool_use:{tool_name}` event as it happens, not just inferable from the final text
    output - the exit criterion this phase actually needs."""

    def __init__(
        self,
        *,
        model: str | None = None,
        allowed_tools: Sequence[str] = (),
        runner: Callable[..., Awaitable[str]] = _default_runner,
        telemetry: TelemetrySink | None = None,
    ) -> None:
        self._model = model
        self._allowed_tools = tuple(allowed_tools)
        self._runner = runner
        self._telemetry = telemetry

    @property
    def model(self) -> str | None:
        """Read-only - `None` means "whatever Claude Code itself defaults to", not
        DEFAULT_MODEL; see the class docstring."""
        return self._model

    def generate(
        self, prompt: str, *, allowed_tools: list[str] | None = None, model: str | None = None
    ) -> str:
        # model (Phase 20, IMPLEMENTATION_PLAN.md, 2026-07-25): per-call override, same
        # precedence as allowed_tools above - falls back to this instance's own constructor-
        # level default (None, meaning "whatever Claude Code itself defaults to") when not
        # given, reproducing every pre-Phase-20 call exactly.
        tools = tuple(allowed_tools) if allowed_tools else self._allowed_tools
        effective_model = model if model is not None else self._model
        on_tool_use = self._record_tool_use if self._telemetry is not None else None
        try:
            return asyncio.run(self._runner(prompt, tools, effective_model, on_tool_use=on_tool_use))
        except AgentSDKProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - ModelGateway.generate() records + re-raises
            raise AgentSDKProviderError(f"Agent SDK query failed: {exc}") from exc

    def _record_tool_use(self, tool_name: str) -> None:
        assert self._telemetry is not None  # only ever bound as a callback when this is set
        self._telemetry.record(
            component="agent_sdk_provider",
            action=f"tool_use:{tool_name}",
            duration_ms=0.0,
            result=TelemetryResult.SUCCESS,
        )
