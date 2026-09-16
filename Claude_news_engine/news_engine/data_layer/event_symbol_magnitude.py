"""
Phase 2 of a three-phase plan (see docs/superpowers/specs/2026-09-16-
event-symbol-magnitude-grid-design.md): a static, hand-curated
magnitude tier for each of Phase 1's 94 RELEVANT (event_type, symbol)
cells -- LOW/MEDIUM/HIGH (cited) or honestly UNVERIFIED where no real
evidence pins down a typical move size. Same discipline as
data_layer/exposure.py and data_layer/event_symbol_relevance.py -- a
real Python constant, never a database table or a live fetch.

This is a REFERENCE TABLE ONLY. Nothing here is wired into live
scoring, the dashboard, or the tier1-cpi-ppi-autoresearch scheduled
task -- that's phase 3, explicitly deferred by user decision.

Scoped EXACTLY to the 94 pairs data_layer.event_symbol_relevance's
get_relevance() already resolved RELEVANT as of 2026-09-16 -- never
edited here, only read. A pair that's NOT_RELEVANT or UNVERIFIED in
that module has no entry here and never will until its own relevance
is resolved first.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MagnitudeTier(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNVERIFIED = "unverified"  # relevance is confirmed real (Phase 1's
                                 # RELEVANT), but no real evidence pins
                                 # down a typical magnitude -- honest,
                                 # not a guess


@dataclass(frozen=True)
class MagnitudeJudgment:
    tier: MagnitudeTier
    citation: str  # required, non-empty for every tier -- for
                    # LOW/MEDIUM/HIGH, the real occurrence(s) that
                    # justify the tier (often reused directly from
                    # event_symbol_relevance's own citation for that
                    # cell); for UNVERIFIED, a short honest note on
                    # what wasn't found


# Populated by Tasks 2-10 below -- every one of the 94 real RELEVANT
# (event_type, symbol) pairs from data_layer.event_symbol_relevance
# must be present by the time Task 11 runs its completeness test.
# Deliberately scoped to exactly that 94-pair subset, never the full
# 108 -- a pair that's NOT_RELEVANT or UNVERIFIED in that module has no
# key here.
_MAGNITUDE_TABLE: dict[tuple[str, str], MagnitudeJudgment] = {}


def get_magnitude(event_type: str, symbol: str) -> MagnitudeJudgment:
    """
    Returns the real, sourced magnitude tier for (event_type, symbol).
    Raises KeyError for anything outside the 94-pair RELEVANT scope --
    this never fabricates a judgment for a pair it doesn't recognize,
    including a real Phase 1 pair that was NOT_RELEVANT or UNVERIFIED
    there (magnitude is only ever researched for a confirmed-RELEVANT
    pair).
    """
    return _MAGNITUDE_TABLE[(event_type, symbol)]
