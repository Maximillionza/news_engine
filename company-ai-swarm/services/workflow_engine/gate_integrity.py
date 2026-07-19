"""Gate Integrity Check: is a nominally-passing review actually superficial?

Source: Specifications/2 - construction-framework/Task Definition Language (TDL).md sec.13
("Acceptance SHALL never rely upon subjective judgement alone") and sec.14 (Evidence Model:
Supporting Artifacts, Source References, Validation Results, Quality Reports, Review Records,
Confidence Assessment), applied to the Phase 7 review step.

Escalation condition 3 (orchestrator/escalation.py): a review can pass
evaluator.validate_outcome()'s check (full Agent Execution Cycle completed, non-empty output)
while still being superficial - most concretely, a review that ran but had nothing to review.
That is a real, reachable case in this codebase: an objective whose vocabulary matches only
"operations" produces zero substantive tasks before the review step runs (see
workflow_engine/engine.py) - the Review Agent still executes cleanly and produces stub
output, so the naive check says "passed," but there was nothing behind the pass.

This module checks the review's evidence is actually populated, not just that execution
succeeded. Confidence Assessment is deliberately excluded from the check: no
confidence-scoring mechanism exists anywhere in this corpus (see shared/model_gateway.py), so
requiring it non-empty would flag every review this codebase can ever produce, which isn't a
meaningful signal - it would always fire, not sometimes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_REQUIRED_NON_EMPTY_FIELDS = ("supporting_artifacts", "source_references", "validation_results")


@dataclass
class GateIntegrityResult:
    superficial: bool
    missing_fields: list[str] = field(default_factory=list)


def check_gate_integrity(evidence: dict) -> GateIntegrityResult:
    missing = [f for f in _REQUIRED_NON_EMPTY_FIELDS if not evidence.get(f)]
    return GateIntegrityResult(superficial=bool(missing), missing_fields=missing)
