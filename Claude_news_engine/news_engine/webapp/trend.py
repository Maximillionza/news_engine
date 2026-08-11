"""
Plain-Python trend summary over webapp.store's event_history rows — no
I/O, no network, no LLM call. "beat forecast N of last M" / "trending
{direction} for N consecutive releases" / a "mixed" fallback / "not
enough history yet" when there's too little confirmed data to say
anything. Deliberately arithmetic, not inference — same "cheap and
deterministic before reaching for anything smarter" pattern as
scoring/sentiment.py's lexicon tier.
"""
from __future__ import annotations

from webapp.store import EventHistoryRow

MIN_CONFIRMED_ROWS_FOR_A_TREND = 2
MIN_STREAK_LENGTH = 2


def summarize_trend(rows: list[EventHistoryRow]) -> str:
    """
    `rows` is expected most-recent-first (get_event_history()'s existing
    order). Only rows with a non-None surprise_direction count as
    "confirmed" — a still-pending occurrence (event hasn't printed yet)
    doesn't count toward the trend.
    """
    confirmed = [r for r in rows if r.surprise_direction is not None]
    if len(confirmed) < MIN_CONFIRMED_ROWS_FOR_A_TREND:
        return "Not enough history yet"

    # Consecutive-streak check, most recent backward.
    streak_direction = confirmed[0].surprise_direction
    streak_length = 1
    for row in confirmed[1:]:
        if row.surprise_direction == streak_direction:
            streak_length += 1
        else:
            break

    if streak_length >= MIN_STREAK_LENGTH and streak_direction in ("higher", "lower"):
        return f"Trending {streak_direction} for {streak_length} consecutive releases"

    # Fall back to a beat/miss tally over the confirmed window —
    # 'in_line' rows count toward the window total but not toward
    # either side, since they're neither a beat nor a miss.
    higher_count = sum(1 for r in confirmed if r.surprise_direction == "higher")
    lower_count = sum(1 for r in confirmed if r.surprise_direction == "lower")
    directional_total = higher_count + lower_count

    if directional_total == 0:
        return "Mixed — no clean streak over the last {} prints".format(len(confirmed))

    if higher_count > lower_count:
        return f"Beat forecast {higher_count} of last {directional_total}"
    if lower_count > higher_count:
        return f"Missed forecast {lower_count} of last {directional_total}"
    return f"Mixed — no clean streak over the last {len(confirmed)} prints"
