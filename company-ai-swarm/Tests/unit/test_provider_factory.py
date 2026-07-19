"""Phase A test: shared.providers.create_provider_from_env() selects the right provider for
MODEL_PROVIDER, without making any real API/network calls."""

from __future__ import annotations

import pytest

from shared.model_gateway import StubModelProvider
from shared.providers import create_provider_from_env
from shared.providers.agent_sdk_provider import AgentSDKModelProvider
from shared.providers.anthropic_provider import AnthropicModelProvider, AnthropicProviderError


def test_defaults_to_stub_when_unset() -> None:
    assert isinstance(create_provider_from_env(env={}), StubModelProvider)


def test_stub_selected_explicitly() -> None:
    assert isinstance(create_provider_from_env(env={"MODEL_PROVIDER": "stub"}), StubModelProvider)


def test_anthropic_selected_with_api_key_present() -> None:
    provider = create_provider_from_env(env={"MODEL_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "sk-ant-fake"})
    assert isinstance(provider, AnthropicModelProvider)


def test_anthropic_selected_without_api_key_raises() -> None:
    with pytest.raises(AnthropicProviderError):
        create_provider_from_env(env={"MODEL_PROVIDER": "anthropic"})


def test_agent_sdk_selected_needs_no_upfront_credentials() -> None:
    # AgentSDKModelProvider defers credential resolution to Claude Code's own precedence
    # chain at generate()-time; construction itself never requires an env var.
    provider = create_provider_from_env(env={"MODEL_PROVIDER": "agent_sdk"})
    assert isinstance(provider, AgentSDKModelProvider)


def test_selection_is_case_insensitive() -> None:
    assert isinstance(create_provider_from_env(env={"MODEL_PROVIDER": "STUB"}), StubModelProvider)


def test_unknown_provider_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown MODEL_PROVIDER"):
        create_provider_from_env(env={"MODEL_PROVIDER": "made_up_provider"})
