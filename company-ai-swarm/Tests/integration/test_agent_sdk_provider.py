"""AgentSDKModelProvider implements ModelProvider correctly, using a fake async runner so no
real Agent SDK call, no installed `claude-agent-sdk` package, and no Claude Code credentials
are required to run these in CI. A separate, gated test at the bottom makes one real call -
skipped unless the SDK is installed and RUN_REAL_AGENT_SDK_SMOKE_TEST=1.

`_default_runner`'s own ClaudeAgentOptions construction (model, setting_sources) is covered
separately below, since the fake-runner tests bypass it entirely by design.
"""

from __future__ import annotations

import os
from typing import Sequence

import pytest

from shared.providers.agent_sdk_provider import (
    DEFAULT_MODEL,
    AgentSDKModelProvider,
    AgentSDKProviderError,
)


def _runner_returning(text: str):
    calls: list[dict[str, object]] = []

    async def runner(
        prompt: str, allowed_tools: Sequence[str], model: str | None, *, on_tool_use=None
    ) -> str:
        calls.append({"prompt": prompt, "allowed_tools": tuple(allowed_tools), "model": model})
        return text

    runner.calls = calls
    return runner


def _runner_raising(exc: Exception):
    async def runner(
        prompt: str, allowed_tools: Sequence[str], model: str | None, *, on_tool_use=None
    ) -> str:
        raise exc

    return runner


def test_generate_returns_runner_result() -> None:
    runner = _runner_returning("hello from the agent sdk")
    provider = AgentSDKModelProvider(runner=runner)

    output = provider.generate("say hello")

    assert output == "hello from the agent sdk"
    assert runner.calls == [{"prompt": "say hello", "allowed_tools": (), "model": None}]


def test_generate_passes_allowed_tools_through() -> None:
    runner = _runner_returning("ok")
    provider = AgentSDKModelProvider(allowed_tools=["Read", "Bash"], runner=runner)

    provider.generate("prompt")

    assert runner.calls[0]["allowed_tools"] == ("Read", "Bash")


def test_generate_passes_model_through() -> None:
    runner = _runner_returning("ok")
    provider = AgentSDKModelProvider(model=DEFAULT_MODEL, runner=runner)

    provider.generate("prompt")

    assert runner.calls[0]["model"] == DEFAULT_MODEL


def test_model_defaults_to_none_not_forced() -> None:
    """Constructing without `model=` should defer to Claude Code's own default, not silently
    force DEFAULT_MODEL - see the class docstring on why that's a deliberate choice left to
    the caller (shared.providers.create_provider_from_env does pass it explicitly)."""

    runner = _runner_returning("ok")
    provider = AgentSDKModelProvider(runner=runner)

    provider.generate("prompt")

    assert runner.calls[0]["model"] is None


def test_generate_per_call_model_overrides_constructor_default() -> None:
    """Phase 20 (IMPLEMENTATION_PLAN.md, 2026-07-25): mirrors allowed_tools' own per-call
    override precedent (Phase 12) - workflow_engine/complexity.py's tier assessment has to
    win over whatever the provider was constructed with, not the other way around."""

    runner = _runner_returning("ok")
    provider = AgentSDKModelProvider(model=DEFAULT_MODEL, runner=runner)

    provider.generate("prompt", model="claude-haiku-4-5-20251001")

    assert runner.calls[0]["model"] == "claude-haiku-4-5-20251001"


def test_generate_falls_back_to_constructor_default_model_when_no_per_call_model_given() -> None:
    runner = _runner_returning("ok")
    provider = AgentSDKModelProvider(model=DEFAULT_MODEL, runner=runner)

    provider.generate("prompt")

    assert runner.calls[0]["model"] == DEFAULT_MODEL


def test_generate_per_call_allowed_tools_overrides_constructor_default() -> None:
    """Phase 12 (IMPLEMENTATION_PLAN.md, 2026-07-23): one shared provider instance serves
    every agent - the calling agent's own tool list (passed per generate() call, from its
    AgentDefinition.tools["available"]) has to win over whatever the provider was
    constructed with, not the other way around."""

    runner = _runner_returning("ok")
    provider = AgentSDKModelProvider(allowed_tools=["Bash"], runner=runner)

    provider.generate("prompt", allowed_tools=["WebSearch"])

    assert runner.calls[0]["allowed_tools"] == ("WebSearch",)


def test_generate_falls_back_to_constructor_default_when_no_per_call_tools_given() -> None:
    runner = _runner_returning("ok")
    provider = AgentSDKModelProvider(allowed_tools=["Bash"], runner=runner)

    provider.generate("prompt")

    assert runner.calls[0]["allowed_tools"] == ("Bash",)


def test_generate_records_tool_use_to_telemetry_when_configured() -> None:
    """The actual exit criterion: a tool call has to be visible in
    observability_service/telemetry.py, not just inferable from the final text output."""

    from observability_service.telemetry import TelemetrySink

    class _ToolUseBlock:
        def __init__(self, name: str) -> None:
            self.name = name

    class _AssistantMessage:
        def __init__(self, content) -> None:
            self.content = content

    class _ResultMessage:
        def __init__(self, result: str) -> None:
            self.result = result
            self.is_error = False

    async def runner(prompt, allowed_tools, model, *, on_tool_use=None):
        if on_tool_use is not None:
            on_tool_use("WebSearch")
        return "found it via search"

    telemetry = TelemetrySink()
    provider = AgentSDKModelProvider(runner=runner, telemetry=telemetry)

    output = provider.generate("look this up", allowed_tools=["WebSearch"])

    assert output == "found it via search"
    records = telemetry.query()
    tool_records = [r for r in records if r.action == "tool_use:WebSearch"]
    assert len(tool_records) == 1
    assert tool_records[0].component == "agent_sdk_provider"


def test_generate_does_not_record_telemetry_when_no_sink_configured() -> None:
    """No telemetry sink means no attempt to use one - the callback must be None, not a
    silent no-op wrapper, so a runner that doesn't care never has to handle it specially."""

    calls: list[object] = []

    async def runner(prompt, allowed_tools, model, *, on_tool_use=None):
        calls.append(on_tool_use)
        return "ok"

    provider = AgentSDKModelProvider(runner=runner)
    provider.generate("prompt")

    assert calls == [None]


def test_default_runner_calls_on_tool_use_for_each_tool_block(monkeypatch) -> None:
    """Exercises the real _default_runner's message-stream inspection, not just the fake
    runner tests above - proves ToolUseBlock/ServerToolUseBlock entries in AssistantMessage.
    content actually get detected as the SDK really shapes them."""

    import sys
    import types
    import asyncio

    class _ToolUseBlock:
        def __init__(self, name: str) -> None:
            self.name = name

    class _ServerToolUseBlock:
        def __init__(self, name: str) -> None:
            self.name = name

    class _AssistantMessage:
        def __init__(self, content) -> None:
            self.content = content

    class _ResultMessage:
        result = "done"
        is_error = False

    class _FakeOptions:
        def __init__(self, **kwargs):
            pass

    async def _fake_query(*, prompt, options):
        yield _AssistantMessage([_ToolUseBlock("WebSearch"), _ServerToolUseBlock("web_fetch")])
        yield _ResultMessage()

    fake_module = types.ModuleType("claude_agent_sdk")
    fake_module.ClaudeAgentOptions = _FakeOptions
    fake_module.ResultMessage = _ResultMessage
    fake_module.AssistantMessage = _AssistantMessage
    fake_module.ToolUseBlock = _ToolUseBlock
    fake_module.ServerToolUseBlock = _ServerToolUseBlock
    fake_module.query = _fake_query
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake_module)

    from shared.providers.agent_sdk_provider import _default_runner

    seen: list[str] = []
    output = asyncio.run(_default_runner("prompt", [], None, on_tool_use=seen.append))

    assert output == "done"
    assert seen == ["WebSearch", "web_fetch"]


def test_generate_wraps_runner_exceptions() -> None:
    provider = AgentSDKModelProvider(runner=_runner_raising(RuntimeError("session died")))

    with pytest.raises(AgentSDKProviderError, match="session died"):
        provider.generate("prompt")


def test_generate_propagates_provider_error_unwrapped() -> None:
    """A runner that already raises AgentSDKProviderError (e.g. "no result message") should
    not get double-wrapped into a generic "Agent SDK query failed: ..." message."""

    provider = AgentSDKModelProvider(runner=_runner_raising(AgentSDKProviderError("no result message")))

    with pytest.raises(AgentSDKProviderError, match="^no result message$"):
        provider.generate("prompt")


def test_default_runner_builds_options_with_model_and_isolated_settings(monkeypatch) -> None:
    """The real `_default_runner` must actually pass `model=` and `setting_sources=[]` into
    ClaudeAgentOptions - the isolation fix documented in this module's docstring (a swarm
    agent call run from inside this repo should not pick up The Company's own .claude/
    settings). Faked at the claude_agent_sdk module boundary since the package may not be
    installed in every environment this test suite runs in."""

    import sys
    import types

    captured_options: list[object] = []

    class _FakeOptions:
        def __init__(self, **kwargs):
            captured_options.append(kwargs)

    class _FakeResult:
        result = "faked output"
        is_error = False

    async def _fake_query(*, prompt, options):
        yield _FakeResult()

    fake_module = types.ModuleType("claude_agent_sdk")
    fake_module.ClaudeAgentOptions = _FakeOptions
    fake_module.ResultMessage = _FakeResult
    fake_module.query = _fake_query
    # Phase 12 (IMPLEMENTATION_PLAN.md, 2026-07-23): _default_runner now also imports these
    # to detect tool-use mid-stream - not exercised by this test's single-ResultMessage fake
    # stream, but the import itself must succeed.
    fake_module.AssistantMessage = type("AssistantMessage", (), {})
    fake_module.ToolUseBlock = type("ToolUseBlock", (), {})
    fake_module.ServerToolUseBlock = type("ServerToolUseBlock", (), {})
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake_module)

    from shared.providers.agent_sdk_provider import _default_runner

    import asyncio

    output = asyncio.run(_default_runner("prompt", ["Read"], "claude-sonnet-5"))

    assert output == "faked output"
    assert captured_options == [
        {"allowed_tools": ["Read"], "model": "claude-sonnet-5", "setting_sources": []}
    ]


def _install_fake_claude_agent_sdk(monkeypatch, *, is_error: bool, result: str, api_error_status=None):
    import sys
    import types

    class _FakeOptions:
        def __init__(self, **kwargs):
            pass

    class _FakeResult:
        pass

    fake_result = _FakeResult()
    fake_result.result = result
    fake_result.is_error = is_error
    fake_result.api_error_status = api_error_status

    async def _fake_query(*, prompt, options):
        yield fake_result

    fake_module = types.ModuleType("claude_agent_sdk")
    fake_module.ClaudeAgentOptions = _FakeOptions
    fake_module.ResultMessage = _FakeResult
    fake_module.query = _fake_query
    fake_module.AssistantMessage = type("AssistantMessage", (), {})
    fake_module.ToolUseBlock = type("ToolUseBlock", (), {})
    fake_module.ServerToolUseBlock = type("ServerToolUseBlock", (), {})
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake_module)


def test_default_runner_raises_with_http_status_when_api_error_status_present(monkeypatch) -> None:
    """The quirk this ports from Samaritan's core/provider.py: is_error=True with subtype
    "success" hides the real HTTP status unless api_error_status is checked explicitly."""

    import asyncio

    _install_fake_claude_agent_sdk(
        monkeypatch, is_error=True, result="error result text", api_error_status=529
    )

    from shared.providers.agent_sdk_provider import AgentSDKProviderError, _default_runner

    with pytest.raises(AgentSDKProviderError, match="HTTP 529"):
        asyncio.run(_default_runner("prompt", [], None))


def test_default_runner_raises_with_fallback_message_when_no_api_error_status(monkeypatch) -> None:
    import asyncio

    _install_fake_claude_agent_sdk(
        monkeypatch, is_error=True, result="something went wrong", api_error_status=None
    )

    from shared.providers.agent_sdk_provider import AgentSDKProviderError, _default_runner

    with pytest.raises(AgentSDKProviderError, match="something went wrong"):
        asyncio.run(_default_runner("prompt", [], None))


def test_default_runner_does_not_treat_error_result_text_as_output(monkeypatch) -> None:
    """Regression test for the exact bug this fix closes: before this change, any ResultMessage
    with a truthy `.result` was accepted as real output, is_error or not."""

    import asyncio

    _install_fake_claude_agent_sdk(
        monkeypatch, is_error=True, result="this looks like real output but isn't"
    )

    from shared.providers.agent_sdk_provider import AgentSDKProviderError, _default_runner

    with pytest.raises(AgentSDKProviderError):
        asyncio.run(_default_runner("prompt", [], None))


@pytest.mark.skipif(
    os.environ.get("RUN_REAL_AGENT_SDK_SMOKE_TEST") != "1",
    reason=(
        "Real Agent SDK smoke test - requires claude-agent-sdk installed and Claude Code "
        "credentials (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN or a /login session); "
        "set RUN_REAL_AGENT_SDK_SMOKE_TEST=1 to run"
    ),
)
def test_real_agent_sdk_call_smoke_test() -> None:
    provider = AgentSDKModelProvider(model=DEFAULT_MODEL)
    output = provider.generate("Reply with exactly the word: pong")
    assert "pong" in output.lower()
