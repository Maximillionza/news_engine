"""Phase A test (Documentation/plans/SDK_MIGRATION_PLAN.md Section 6): AnthropicModelProvider
implements ModelProvider correctly, using a fake client so no real API call or installed
`anthropic` package is required to run these in CI. A separate, gated test at the bottom
makes one real call - skipped unless ANTHROPIC_API_KEY is set and
RUN_REAL_ANTHROPIC_SMOKE_TEST=1, matching the plan's "optional, gated to CI with API key."
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pytest

from shared.providers.anthropic_provider import (
    DEFAULT_TIMEOUT_SECONDS,
    AnthropicModelProvider,
    AnthropicProviderError,
)


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeMessage:
    content: list[Any]
    stop_reason: str = "end_turn"


@dataclass
class _FakeMessagesResource:
    response: _FakeMessage
    exception: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def create(self, **kwargs: Any) -> _FakeMessage:
        self.calls.append(kwargs)
        if self.exception is not None:
            raise self.exception
        return self.response


@dataclass
class _FakeClient:
    messages: _FakeMessagesResource


def _factory_for(response: _FakeMessage | None = None, exception: Exception | None = None):
    resource = _FakeMessagesResource(
        response=response or _FakeMessage(content=[_FakeTextBlock(text="fake output")]),
        exception=exception,
    )
    client = _FakeClient(messages=resource)

    def factory(api_key: str, *, base_url: str | None, timeout_seconds: float) -> _FakeClient:
        factory.calls.append(
            {"api_key": api_key, "base_url": base_url, "timeout_seconds": timeout_seconds}
        )
        return client

    factory.calls = []
    factory.resource = resource
    return factory


def test_requires_api_key() -> None:
    with pytest.raises(AnthropicProviderError):
        AnthropicModelProvider(api_key=None, client_factory=_factory_for())


def test_generate_returns_text_content() -> None:
    factory = _factory_for(_FakeMessage(content=[_FakeTextBlock(text="hello from claude")]))
    provider = AnthropicModelProvider(api_key="sk-ant-fake", client_factory=factory)

    output = provider.generate("say hello")

    assert output == "hello from claude"
    assert factory.calls == [
        {"api_key": "sk-ant-fake", "base_url": None, "timeout_seconds": DEFAULT_TIMEOUT_SECONDS}
    ]
    assert factory.resource.calls[0]["messages"] == [{"role": "user", "content": "say hello"}]


def test_generate_joins_multiple_text_blocks() -> None:
    factory = _factory_for(
        _FakeMessage(content=[_FakeTextBlock(text="part one "), _FakeTextBlock(text="part two")])
    )
    provider = AnthropicModelProvider(api_key="sk-ant-fake", client_factory=factory)

    assert provider.generate("prompt") == "part one part two"


def test_generate_raises_on_empty_content() -> None:
    factory = _factory_for(_FakeMessage(content=[], stop_reason="max_tokens"))
    provider = AnthropicModelProvider(api_key="sk-ant-fake", client_factory=factory)

    with pytest.raises(AnthropicProviderError, match="no text content"):
        provider.generate("prompt")


def test_generate_wraps_client_exceptions() -> None:
    factory = _factory_for(exception=RuntimeError("rate limited"))
    provider = AnthropicModelProvider(api_key="sk-ant-fake", client_factory=factory)

    with pytest.raises(AnthropicProviderError, match="rate limited"):
        provider.generate("prompt")


def test_reads_api_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")
    factory = _factory_for()

    AnthropicModelProvider(client_factory=factory)

    assert factory.calls == [
        {"api_key": "sk-ant-from-env", "base_url": None, "timeout_seconds": DEFAULT_TIMEOUT_SECONDS}
    ]


def test_custom_timeout_is_passed_to_client_factory() -> None:
    factory = _factory_for()

    AnthropicModelProvider(api_key="sk-ant-fake", timeout_seconds=30.0, client_factory=factory)

    assert factory.calls[0]["timeout_seconds"] == 30.0


def test_generate_uses_constructor_default_model_when_no_override_given() -> None:
    factory = _factory_for()
    provider = AnthropicModelProvider(api_key="sk-ant-fake", model="claude-sonnet-5", client_factory=factory)

    provider.generate("prompt")

    assert factory.resource.calls[0]["model"] == "claude-sonnet-5"


def test_generate_model_override_wins_over_constructor_default() -> None:
    """Phase 20 (IMPLEMENTATION_PLAN.md, 2026-07-25): a per-call model override, from
    workflow_engine/complexity.py's tier assessment - None (the default) reproduces every
    pre-Phase-20 call exactly, but an explicit value takes precedence."""
    factory = _factory_for()
    provider = AnthropicModelProvider(api_key="sk-ant-fake", model="claude-sonnet-5", client_factory=factory)

    provider.generate("prompt", model="claude-haiku-4-5-20251001")

    assert factory.resource.calls[0]["model"] == "claude-haiku-4-5-20251001"


@pytest.mark.skipif(
    not (os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("RUN_REAL_ANTHROPIC_SMOKE_TEST") == "1"),
    reason="Real Claude API smoke test - set ANTHROPIC_API_KEY and RUN_REAL_ANTHROPIC_SMOKE_TEST=1 to run",
)
def test_real_claude_api_call_smoke_test() -> None:
    provider = AnthropicModelProvider()
    output = provider.generate("Reply with exactly the word: pong")
    assert "pong" in output.lower()
