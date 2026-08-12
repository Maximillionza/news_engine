"""
Plain-Python trend summary over webapp.store's event_history rows — no
I/O, no network, no LLM call. Two consumers share one arithmetic core
(_analyze_trend, below): summarize_trend() formats it as a human-readable
string for the dashboard's History panel; compute_trend_signal() maps it
to a numeric (direction, strength) signal for
scoring/backtest_accumulator.py to blend into score_bundle() (see
docs/superpowers/specs/2026-08-12-trend-history-scoring-feedback-design.md).
Deliberately arithmetic, not inference — same "cheap and deterministic
before reaching for anything smarter" pattern as scoring/sentiment.py's
lexicon tier.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from webapp.store import EventHistoryRow

MIN_CONFIRMED_ROWS_FOR_A_TREND = 2
MIN_STREAK_LENGTH = 2

# compute_trend_signal()'s strength formula denominator for a consecutive
# streak — a streak this long or longer saturates strength at 1.0.
STREAK_LENGTH_FOR_FULL_STRENGTH = 5


@dataclass
class TrendSignal:
    """direction: 'higher' | 'lower'. strength: 0.0-1.0."""
    direction: str
    strength: float


@dataclass
class _TrendAnalysis:
    """Internal shared result of the streak-then-tally arithmetic — never exposed outside this module."""
    kind: str  # "streak" | "tally" | "mixed"
    direction: Optional[str]
    streak_length: Optional[int] = None   # set when kind == "streak"
    majority_count: Optional[int] = None  # set when kind == "tally"
    directional_total: Optional[int] = None  # set when kind == "tally"
    window: int = 0  # len(confirmed_rows) — used by the "mixed" message/gate


def _analyze_trend(confirmed_rows: list[EventHistoryRow]) -> _TrendAnalysis:
    """
    `confirmed_rows` must already be filtered to non-None surprise_direction,
    most-recent-first (get_event_history()'s existing order), and must be
    non-empty (callers apply their own minimum-count gate before calling
    this — see summarize_trend()/compute_trend_signal() below).
    """
    streak_direction = confirmed_rows[0].surprise_direction
    streak_length = 1
    for row in confirmed_rows[1:]:
        if row.surprise_direction == streak_direction:
            streak_length += 1
        else:
            break

    if streak_length >= MIN_STREAK_LENGTH and streak_direction in ("higher", "lower"):
        return _TrendAnalysis(kind="streak", direction=streak_direction, streak_length=streak_length, window=len(confirmed_rows))

    higher_count = sum(1 for r in confirmed_rows if r.surprise_direction == "higher")
    lower_count = sum(1 for r in confirmed_rows if r.surprise_direction == "lower")
    directional_total = higher_count + lower_count

    if directional_total == 0:
        return _TrendAnalysis(kind="mixed", direction=None, window=len(confirmed_rows))

    if higher_count > lower_count:
        return _TrendAnalysis(kind="tally", direction="higher", majority_count=higher_count, directional_total=directional_total, window=len(confirmed_rows))
    if lower_count > higher_count:
        return _TrendAnalysis(kind="tally", direction="lower", majority_count=lower_count, directional_total=directional_total, window=len(confirmed_rows))
    return _TrendAnalysis(kind="mixed", direction=None, window=len(confirmed_rows))


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

    analysis = _analyze_trend(confirmed)
    if analysis.kind == "streak":
        return f"Trending {analysis.direction} for {analysis.streak_length} consecutive releases"
    if analysis.kind == "tally":
        verb = "Beat" if analysis.direction == "higher" else "Missed"
        return f"{verb} forecast {analysis.majority_count} of last {analysis.directional_total}"
    return f"Mixed — no clean streak over the last {analysis.window} prints"


def compute_trend_signal(confirmed_rows: list[EventHistoryRow]) -> Optional[TrendSignal]:
    """
    Maps the same streak-then-tally arithmetic summarize_trend() uses to a
    numeric (direction, strength) signal for scoring feed-back. Unlike
    summarize_trend(), this function applies NO minimum-row-count gate
    itself — the caller (scoring/backtest_accumulator.py) enforces the
    stricter MIN_OCCURRENCES_FOR_TREND_PRIOR (config.settings) before ever
    calling this, since trusting a pattern enough to nudge a live
    prediction is a bigger claim than merely displaying it. Returns None
    for a "mixed"/no-majority result — never a zero-strength signal.

    `confirmed_rows` must already be filtered to non-None surprise_direction
    and non-empty — passing an empty list is a caller bug (would raise on
    the [0] index in _analyze_trend), not a case this function handles.
    """
    analysis = _analyze_trend(confirmed_rows)
    if analysis.kind == "streak":
        strength = min(1.0, analysis.streak_length / STREAK_LENGTH_FOR_FULL_STRENGTH)
        return TrendSignal(direction=analysis.direction, strength=strength)
    if analysis.kind == "tally":
        strength = (analysis.majority_count / analysis.directional_total - 0.5) * 2
        return TrendSignal(direction=analysis.direction, strength=strength)
    return None
