"""Phase A test (Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.1): AgentSDKModelProvider
implements ModelProvider correctly, using a fake async runner so no real Agent SDK call, no
installed `claude-agent-sdk` package, and no Claude Code credentials are required to run
these in CI. A separate, gated test at the bottom makes one real call - skipped unless the
SDK is installed and RUN_REAL_AGENT_SDK_SMOKE_TEST=1.
"""

from __future__ import annotations

import os
from typing import Sequence

import pytest

from shared.providers.agent_sdk_provider import AgentSDKModelProvider, AgentSDKProviderError


def _runner_returning(text: str):
    calls: list[dict[str, object]] = []

    async def runner(prompt: str, allowed_tools: Sequence[str]) -> str:
        calls.append({"prompt": prompt, "allowed_tools": tuple(allowed_tools)})
        return text

    runner.calls = calls
    return runner


def _runner_raising(exc: Exception):
    async def runner(prompt: str, allowed_tools: Sequence[str]) -> str:
        raise exc

    return runner


def test_generate_returns_runner_result() -> None:
    runner = _runner_returning("hello from the agent sdk")
    provider = AgentSDKModelProvider(runner=runner)

    output = provider.generate("say hello")

    assert output == "hello from the agent sdk"
    assert runner.calls == [{"prompt": "say hello", "allowed_tools": ()}]


def test_generate_passes_allowed_tools_through() -> None:
    runner = _runner_returning("ok")
    provider = AgentSDKModelProvider(allowed_tools=["Read", "Bash"], runner=runner)

    provider.generate("prompt")

    assert runner.calls == [{"prompt": "prompt", "allowed_tools": ("Read", "Bash")}]


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


@pytest.mark.skipif(
    os.environ.get("RUN_REAL_AGENT_SDK_SMOKE_TEST") != "1",
    reason=(
        "Real Agent SDK smoke test - requires claude-agent-sdk installed and Claude Code "
        "credentials (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN or a /login session); "
        "set RUN_REAL_AGENT_SDK_SMOKE_TEST=1 to run"
    ),
)
def test_real_agent_sdk_call_smoke_test() -> None:
    provider = AgentSDKModelProvider()
    output = provider.generate("Reply with exactly the word: pong")
    assert "pong" in output.lower()
