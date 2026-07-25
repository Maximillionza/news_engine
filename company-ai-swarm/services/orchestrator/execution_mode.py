"""Lean/Fast execution mode.

Source: this session's 2026-07-25 vision comparison - the founder's original design: "By
default the Orchestrator is lean with usage always looking at using the appropriate model...
but the user can change it to be Faster meaning it uses a higher tier model for most tasks."
Phase 20 (IMPLEMENTATION_PLAN.md): built on top of workflow_engine/complexity.py's tier
assessment, which must exist first for this mode switch to mean anything real rather than a
cosmetic toggle - see that module and IMPLEMENTATION_PLAN.md's Phase 20 section.

Exactly parallel to shared/providers/create_provider_from_env() and orchestrator/
classification.py's create_classifier_from_env(): an env-var-driven factory, "lean" is the
safe default (every pre-Phase-20 deployment that never sets EXECUTION_MODE keeps getting
whatever workflow_engine/complexity.py assesses as appropriate, not a forced upgrade).
"""

from __future__ import annotations

import os
from typing import Mapping

from workflow_engine.complexity import MODEL_TIER_STANDARD

EXECUTION_MODE_LEAN = "lean"
EXECUTION_MODE_FAST = "fast"
EXECUTION_MODES = (EXECUTION_MODE_LEAN, EXECUTION_MODE_FAST)


def resolve_model_tier(assessed_tier: str, *, mode: str) -> str:
    """Lean: use the assessed tier verbatim - this is the entire point of "lean," not a
    corner cut. Fast: never downgrade below "standard," regardless of what was assessed -
    trades away Lean's cost savings for a floor on model quality/speed. With only two tiers
    defined today (workflow_engine/complexity.py), Fast mode's effect is exactly "always
    standard" - this will do something more graduated once a tier above "standard" exists."""

    if mode == EXECUTION_MODE_FAST:
        return MODEL_TIER_STANDARD
    return assessed_tier


def create_execution_mode_from_env(env: Mapping[str, str] | None = None) -> str:
    """EXECUTION_MODE env var: "lean" (default) or "fast"."""

    source = env if env is not None else os.environ
    selected = source.get("EXECUTION_MODE", EXECUTION_MODE_LEAN).strip().lower()

    if selected not in EXECUTION_MODES:
        raise ValueError(f"Unknown EXECUTION_MODE={selected!r}; expected one of {EXECUTION_MODES}.")

    return selected
