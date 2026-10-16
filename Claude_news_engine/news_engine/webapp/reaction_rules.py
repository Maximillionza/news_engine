# webapp/reaction_rules.py
"""
Pure rules for the Stats "Market reaction" sub-tab
(docs/superpowers/specs/2026-10-16-market-reaction-design.md §4, §4.1, §4.2, §5).

No I/O and no webapp imports. Reaction is an association measured over 5 minutes against a
typical move for that hour (the 75th percentile of ordinary 5-minute moves); it is never proof that a release caused the move.
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from typing import Optional

# "Typical" move = this quantile of ordinary |5-minute moves| for the instrument and UTC hour (owner ruling
# 2026-10-16: the 75th percentile, so an ordinary window crosses it ~25% of the time; the median gave ~50%).
REACTION_BASELINE_QUANTILE = 0.75
REACTION_MIN_MULTIPLE = 1.0   # |move| must exceed typical (the quantile value) * this to count as a reaction
MIN_PERCENT_RELEASES = 20     # below this many releases the percentage is hidden (counts stay)
FEW_RELEASES_TAG = 8          # below this many releases a title carries a "few releases" tag
# Same-title rows this close to the earliest row of their run are one event listed twice (Phase 0 ruling 2:
# ADP Weekly 12:14/12:15/12:16, Federal Budget Balance 17:58/18:00; a 9-minute RCM/TIPP pair stays two events).
DUPLICATE_WITHIN = dt.timedelta(minutes=3)

# Absolute tolerance (1e-9): move and typical must be in the same absolute price units; it exists so
# float noise at the threshold (0.1 * 3 != 0.3 exactly) cannot flip "equal to typical" into a reaction.
_EPS = 1e-9
_IMPACT_ORDER = ("High", "Medium", "Low")   # tie-break order, strongest first


def classify_reaction(
    move: Optional[float],
    typical: Optional[float],
    multiple: float = REACTION_MIN_MULTIPLE,
) -> Optional[str]:
    """
    'buy' / 'sell' when |move| exceeds typical * multiple, 'none' otherwise, None when unjudgeable.
    `typical` is the REACTION_BASELINE_QUANTILE (75th-percentile) ordinary |5-minute move| for that hour.
    """
    if move is None or typical is None or typical <= 0:
        return None
    if abs(move) <= typical * multiple + _EPS:
        return "none"
    return "buy" if move > 0 else "sell"


def single_outcome(lean: str, reaction: Optional[str]) -> str:
    """Hit / miss for one signal. 'no_signal' is decided before 'no_data'."""
    if lean not in ("buy", "sell"):
        return "no_signal"
    if reaction is None:
        return "no_data"
    if reaction == "none":
        return "no_reaction"
    return "hit" if lean == reaction else "miss"


def cluster_credit(leans: dict[str, str], reaction: Optional[str]) -> dict[str, str]:
    """
    Credit label per event id for one cluster (same release minute) on one instrument.
    Solo / shared / conflict rules follow spec §4.1; credit is shared or matched, never exclusive.
    """
    leaned = {key: lean for key, lean in leans.items() if lean in ("buy", "sell")}
    credit: dict[str, str] = {}
    for key in leans:
        if key not in leaned:
            credit[key] = "no_signal"          # no lean: listed, never scored

    if not leaned:
        return credit
    if reaction is None:
        credit.update({key: "no_data" for key in leaned})
        return credit
    if reaction == "none":
        credit.update({key: "no_reaction" for key in leaned})
        return credit

    distinct_leans = set(leaned.values())
    if len(distinct_leans) > 1:                # conflict: both buy and sell leans present
        for key, lean in leaned.items():
            credit[key] = "matched" if lean == reaction else "overruled"
    elif len(leaned) == 1:                     # solo
        for key, lean in leaned.items():
            credit[key] = "solo_hit" if lean == reaction else "solo_miss"
    else:                                      # agree: two or more events, one shared lean
        for key, lean in leaned.items():
            credit[key] = "shared_hit" if lean == reaction else "shared_miss"
    return credit


def wilson_interval(k: int, n: int, z: float = 1.96) -> Optional[tuple[float, float]]:
    """Wilson score interval for k successes in n trials, rounded to 4 decimals. None when n == 0."""
    if k < 0 or k > n:
        raise ValueError(f"k must be between 0 and n (got k={k}, n={n})")
    if n == 0:
        return None
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    lo = max(0.0, centre - half)
    hi = min(1.0, centre + half)
    return round(lo, 4), round(hi, 4)


def rate_display(k: int, n: int) -> dict:
    """k of n with a percent (hidden under MIN_PERCENT_RELEASES), Wilson interval and a 'few' flag."""
    interval = wilson_interval(k, n)
    return {
        "k": k,
        "n": n,
        "percent": round(k / n * 100, 1) if n >= MIN_PERCENT_RELEASES else None,
        "interval": list(interval) if interval is not None else None,
        "few": n < FEW_RELEASES_TAG,
    }


def impact_info(own_tag: Optional[str], title_tags: dict[str, int]) -> dict:
    """
    Effective impact for a row (spec §5): its own tag, else the most common tag for the same
    title (ties -> High > Medium > Low), else 'Unrated'. 'bucket' is the filter chip it belongs to.
    """
    if own_tag:
        return {"bucket": own_tag, "effective": own_tag, "inferred": False}
    effective = "Unrated"
    best = 0
    for tag in _IMPACT_ORDER:                  # strict '>' keeps the earlier (stronger) tag on ties
        count = title_tags.get(tag, 0)
        if count > best:
            best, effective = count, tag
    return {"bucket": "Unrated", "effective": effective, "inferred": True}


def collapse_same_title_duplicates(
    events: list[tuple[str, dt.datetime]], within: dt.timedelta = DUPLICATE_WITHIN,
) -> list[tuple[str, dt.datetime]]:
    """
    Same-title rows within `within` of the earliest row of their run collapse into that row (ruling 2),
    so a 12:14/12:15/12:16 chain is one release at 12:14. Anchored on the kept row, not chained pairwise,
    so a collapse never spans more than `within`. Returns the kept rows sorted by (time, title).
    """
    by_title: dict[str, list[dt.datetime]] = defaultdict(list)
    for title, when in events:
        by_title[title].append(when)
    kept = []
    for title, times in by_title.items():
        anchor: Optional[dt.datetime] = None
        for when in sorted(times):
            if anchor is None or when - anchor > within:
                kept.append((title, when))
                anchor = when
    return sorted(kept, key=lambda event: (event[1], event[0]))
