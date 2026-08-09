"""
Tracks a sequence of ProbabilityResult snapshots for a single event over
time — this is what powers "keep checking through the event to catch
indecision" from the requirements.

This is distinct from the intra-bundle recent-vs-older contradiction check
in probability_engine.py. That check compares recent vs. older articles
within ONE scoring run. This tracker compares direction ACROSS separate
runs (e.g. a score computed 2 days out, another 12 hours out, another right
at release, another 15 minutes after) — catching the case where each
individual run looks confident and consistent internally, but the overall
narrative has actually flipped since the last check.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from scoring.probability_engine import Direction, ProbabilityResult


@dataclass
class DirectionFlip:
    from_snapshot: ProbabilityResult
    to_snapshot: ProbabilityResult

    def describe(self) -> str:
        return (
            f"Direction flipped from {self.from_snapshot.direction.value.upper()} "
            f"({self.from_snapshot.as_of_utc.strftime('%H:%M UTC')}) to "
            f"{self.to_snapshot.direction.value.upper()} "
            f"({self.to_snapshot.as_of_utc.strftime('%H:%M UTC')})"
        )


@dataclass
class EventScoreTracker:
    """
    One tracker per (event, instrument) pair. Call record() each time you
    re-run scoring for this event (e.g. every POST_EVENT_REFRESH_MINUTES),
    and it maintains the history plus flip detection.
    """
    instrument: str
    event_label: str
    snapshots: list[ProbabilityResult] = field(default_factory=list)

    def record(self, result: ProbabilityResult) -> DirectionFlip | None:
        """
        Add a new snapshot. Returns a DirectionFlip if this snapshot's
        direction differs from the previous non-neutral snapshot's
        direction (neutral snapshots are treated as "no read yet" rather
        than a flip in either direction, so they don't trigger false flips).
        """
        previous_directional = next(
            (s for s in reversed(self.snapshots) if s.direction != Direction.NEUTRAL),
            None,
        )
        self.snapshots.append(result)

        if (
            previous_directional is not None
            and result.direction != Direction.NEUTRAL
            and result.direction != previous_directional.direction
        ):
            return DirectionFlip(from_snapshot=previous_directional, to_snapshot=result)
        return None

    def is_stable(self, lookback: int = 3) -> bool:
        """
        True if the last `lookback` non-neutral snapshots all agree on
        direction. Useful as a simple "is this signal trustworthy right
        now" gate before acting on it.
        """
        directional = [s for s in self.snapshots if s.direction != Direction.NEUTRAL]
        if len(directional) < lookback:
            return False
        recent = directional[-lookback:]
        return len({s.direction for s in recent}) == 1

    def latest(self) -> ProbabilityResult | None:
        return self.snapshots[-1] if self.snapshots else None

    def history_summary(self) -> str:
        if not self.snapshots:
            return f"{self.event_label} [{self.instrument}]: no snapshots yet"
        lines = [f"{self.event_label} [{self.instrument}] — {len(self.snapshots)} snapshots:"]
        for s in self.snapshots:
            lines.append(f"  {s.as_of_utc.strftime('%Y-%m-%d %H:%M UTC')}  {s.summary()}")
        return "\n".join(lines)
