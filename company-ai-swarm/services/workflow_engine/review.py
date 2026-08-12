"""Risk-proportional Task Review tier mapping.

Source: Specifications/2 - construction-framework/Task Definition Language (TDL).md sec.17:

    Routine    -> Self-validation
    Standard   -> Peer review
    Advanced   -> Department review
    Critical   -> Independent review + Executive approval

sec.17's tiers key off sec.7's 5-level Task Complexity Model (Routine/Standard/Advanced/
Expert/Enterprise Critical); sec.17's table has 4 rows for 5 levels, so Expert and Enterprise
Critical are both treated as "Critical" here - the corpus doesn't disambiguate them further.

Honesty note, same shape as every other complexity-dependent module in this codebase
(orchestrator/controller.py, shared/model_gateway.py): no numeric Task Complexity or Task Risk
scoring exists anywhere in the source corpus (TDL sec.7-8 define the scales, not how to
compute a score). orchestrator/controller.py's complexity_level is a fixed "Level 2 Standard"
default (originally set in orchestrator/planner.py before that logic was relocated), so this
table's "peer_review" row is the only tier Phase 7 can ever actually produce. The full table is implemented and consumable regardless, so that when real
complexity scoring exists, the other three tiers activate without redesigning this module.
"""

from __future__ import annotations

REVIEW_TIER_BY_COMPLEXITY: dict[str, str] = {
    "Level 1 Routine": "self_validation",
    "Level 2 Standard": "peer_review",
    "Level 3 Advanced": "department_review",
    "Level 4 Expert": "independent_review_and_executive_approval",
    "Level 5 Enterprise Critical": "independent_review_and_executive_approval",
}

DEFAULT_TIER = "peer_review"


def determine_review_tier(complexity_level: str) -> str:
    return REVIEW_TIER_BY_COMPLEXITY.get(complexity_level, DEFAULT_TIER)
