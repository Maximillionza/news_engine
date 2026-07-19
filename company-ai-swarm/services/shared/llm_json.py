"""Small shared helper for parsing JSON that Claude sometimes wraps in a markdown code
fence even when explicitly told to respond with only JSON. Used by both
orchestrator/classification.py's LLMDepartmentClassifier and orchestrator/intake.py's
assess_sufficiency() - factored out once, rather than duplicated in each."""

from __future__ import annotations

import re

_OPENING_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?")
_CLOSING_FENCE_RE = re.compile(r"\n?```$")


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = _OPENING_FENCE_RE.sub("", stripped)
        stripped = _CLOSING_FENCE_RE.sub("", stripped)
    return stripped.strip()
