"""orchestrator.execution_mode - Lean/Fast (Phase 20, IMPLEMENTATION_PLAN.md, 2026-07-25).
Mirrors Tests/unit/test_provider_factory.py's pattern for create_provider_from_env()."""

from __future__ import annotations

import pytest

from orchestrator.execution_mode import (
    EXECUTION_MODE_FAST,
    EXECUTION_MODE_LEAN,
    create_execution_mode_from_env,
    resolve_model_tier,
)
from workflow_engine.complexity import MODEL_TIER_LEAN, MODEL_TIER_STANDARD


def test_lean_mode_uses_assessed_tier_verbatim() -> None:
    assert resolve_model_tier(MODEL_TIER_LEAN, mode=EXECUTION_MODE_LEAN) == MODEL_TIER_LEAN
    assert resolve_model_tier(MODEL_TIER_STANDARD, mode=EXECUTION_MODE_LEAN) == MODEL_TIER_STANDARD


def test_fast_mode_never_downgrades_below_standard() -> None:
    assert resolve_model_tier(MODEL_TIER_LEAN, mode=EXECUTION_MODE_FAST) == MODEL_TIER_STANDARD
    assert resolve_model_tier(MODEL_TIER_STANDARD, mode=EXECUTION_MODE_FAST) == MODEL_TIER_STANDARD


def test_defaults_to_lean_when_unset() -> None:
    assert create_execution_mode_from_env(env={}) == EXECUTION_MODE_LEAN


def test_selects_fast_explicitly() -> None:
    assert create_execution_mode_from_env(env={"EXECUTION_MODE": "fast"}) == EXECUTION_MODE_FAST


def test_selection_is_case_insensitive() -> None:
    assert create_execution_mode_from_env(env={"EXECUTION_MODE": "FAST"}) == EXECUTION_MODE_FAST


def test_unknown_mode_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown EXECUTION_MODE"):
        create_execution_mode_from_env(env={"EXECUTION_MODE": "turbo"})
