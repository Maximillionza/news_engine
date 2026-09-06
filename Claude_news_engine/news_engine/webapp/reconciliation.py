"""
Read-time reconciliation for co-released tracked events — titles that
share the exact same event_time_utc (e.g. 2026-09-04T12:30 UTC's
Non-Farm Employment Change, Unemployment Rate, and Average Hourly
Earnings m/m, all from one BLS jobs report). Each title is scored fully
independently by scoring/probability_engine.py's accumulator (see
data_layer/event_context.py's per-title EVENT_RELEVANCE_KEYWORDS_BY_TITLE
article filter — different titles pull different article samples even
when released simultaneously), which can and does produce contradictory
per-instrument directional calls for what is economically one USD move
at one instant. Confirmed live 2026-09-04: US30 scored bullish under NFP,
bullish under AHE, bearish under Unemployment Rate, for the same
30-minute window.

Uses strict unanimity, not a confidence-weighted contest (2026-09-05
design revision — see docs/superpowers/specs/2026-09-04-co-released-
event-reconciliation-design.md): an earlier confidence-weighted design
let two moderately-confident agreeing titles outvote a single dissenting
title, and tested against this exact real occurrence, that resolved to
"no conflict" even though the dissenting title (Unemployment Rate,
bearish) was the one that matched the real subsequent price move
(XAUUSD -1.73%). A confidence contest can pick the wrong side; strict
unanimity never silently overrules a real disagreement.

This module never scores anything itself and never writes anything —
it's a pure, read-time validation layer over Prediction rows the caller
already fetched from scoring.backtest_store. See
docs/superpowers/specs/2026-09-04-co-released-event-reconciliation-design.md
for the full design and docs/superpowers/plans/2026-09-04-co-released-event-reconciliation.md
for how webapp/app.py wires this in.

Deliberately does NOT touch: scoring/probability_engine.py (no rescoring),
scoring/backtest_store.py's write path (predictions table is untouched),
or webapp/history.py (History keeps grading every title independently).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from scoring.backtest_store import Prediction


@dataclass
class ReconciledCall:
    conflict: bool
    # Only set when conflict is False — the highest-confidence
    # non-neutral title's OWN Prediction object, completely untouched
    # (never a synthetic blend of multiple titles' numbers). Only used
    # to pick WHICH of several unanimous titles' prediction to display,
    # never to decide whether they agree in the first place.
    prediction: Optional[Prediction] = None
    # Only set when conflict is True — every non-neutral title in the
    # group, for the caller to report/display which titles disagreed.
    conflicting_titles: Optional[list[str]] = None


def reconcile_group(predictions_by_title: dict[str, Prediction]) -> Optional[ReconciledCall]:
    """
    predictions_by_title: every co-released title's latest prediction for
    ONE instrument (caller is responsible for scoping this to a single
    instrument and a single event_time_utc group before calling).

    Returns None when there are fewer than 2 non-neutral-direction titles
    in the group -- nothing to reconcile, caller falls through to
    whatever plain single-title display it already had. Otherwise:

    1. Titles with direction == 'neutral' are excluded entirely — a
       neutral call has no direction to agree or conflict with, and
       plays no role in either outcome.
    2. If every remaining (non-neutral) title shares the SAME direction
       -> conflict=False, returning the highest-confidence one of
       those titles' own Prediction object untouched. Confidence here
       only breaks a tie among titles that already agree; it is never a
       contest between titles that disagree.
    3. If the non-neutral titles do NOT all share the same direction
       -> conflict=True, regardless of any confidence gap between them —
       one real dissenting title is enough, however low its confidence
       relative to the others.
    """
    non_neutral = {
        title: pred for title, pred in predictions_by_title.items()
        if pred.direction != "neutral"
    }
    if len(non_neutral) < 2:
        return None

    directions = {pred.direction for pred in non_neutral.values()}
    if len(directions) == 1:
        dominant = max(non_neutral.values(), key=lambda pred: pred.confidence)
        return ReconciledCall(conflict=False, prediction=dominant)

    return ReconciledCall(conflict=True, conflicting_titles=sorted(non_neutral.keys()))
