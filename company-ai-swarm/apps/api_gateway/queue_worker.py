"""Queue worker skeleton: polls `objective_queue`, claims a row, runs a handler, records the
outcome.

Source: Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.2/5 Phase A ("Queue worker
skeleton (doesn't execute yet, just transitions state)"). This module intentionally has no
dependency on COOOrchestrator or any other orchestration code - `QueueWorker` takes a
`handler: Callable[[str, str], dict]` (objective, required_output) -> result dict, so Phase
A can prove the full queued -> executing -> completed/failed state machine against a trivial
stub handler in tests, without wiring a background loop into apps/api_gateway/main.py yet.

Phase B ("Queue worker core loop") is expected to: (1) run this on an interval in a
background thread/process alongside the FastAPI app, and (2) pass a handler that calls
`COOOrchestrator.receive_objective()` and shapes its return value into the `dict` this
worker persists as `ObjectiveQueueRecord.result`. Neither of those exists yet - this module
only defines the claim/execute/record mechanics `run_once()` needs, so Phase B is additive
wiring, not a rewrite (same "swap without touching callers" principle used everywhere else
in this codebase).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

# apps/ is not a package (see apps/api_gateway/main.py's note on dashboard_api) - this is a
# same-directory sibling import, valid once apps/api_gateway is on sys.path (main.py does
# this for dashboard_api already; tests that import this module do the same, see
# Tests/integration/test_async_objective_queue.py).
from objective_queue import (
    ObjectiveQueueRecord,
    get_objective,
    list_queued_objectives,
    mark_completed,
    mark_executing,
    mark_failed,
)

Handler = Callable[[str, str], dict[str, Any]]


@dataclass
class WorkerCycleResult:
    """What one `run_once()` call did, for callers (tests, a future scheduler loop) that
    want to log or assert on it without re-querying the table."""

    claimed: list[str]
    completed: list[str]
    failed: list[str]


class QueueWorker:
    def __init__(self, *, handler: Handler) -> None:
        self._handler = handler

    def run_once(self, session: Session, *, batch_size: int = 10) -> WorkerCycleResult:
        """Claims up to `batch_size` queued objectives (oldest first) and runs `handler` on
        each. A handler exception fails that objective (`mark_failed`) and does not stop the
        rest of the batch - one bad objective should not starve the others.

        Not safe for multiple worker processes/threads calling this concurrently against the
        same rows yet - `list_queued_objectives` + `mark_executing` is a read-then-write with
        no row-level locking (e.g. `SELECT ... FOR UPDATE SKIP LOCKED`) between them. Phase A
        is single-worker-in-process, matching Section 5's "Queue worker skeleton"; concurrent
        workers are out of scope until that's added."""

        claimed: list[str] = []
        completed: list[str] = []
        failed: list[str] = []

        for queued in list_queued_objectives(session, limit=batch_size):
            record = mark_executing(session, queued.id)
            claimed.append(record.id)
            self._run_one(session, record, completed=completed, failed=failed)

        return WorkerCycleResult(claimed=claimed, completed=completed, failed=failed)

    def _run_one(
        self,
        session: Session,
        record: ObjectiveQueueRecord,
        *,
        completed: list[str],
        failed: list[str],
    ) -> None:
        try:
            result = self._handler(record.objective, record.required_output)
        except Exception as exc:  # noqa: BLE001 - one objective's failure, not the worker's
            mark_failed(session, record.id, f"{type(exc).__name__}: {exc}")
            failed.append(record.id)
            return

        mark_completed(session, record.id, result)
        completed.append(record.id)


def run_once(session: Session, *, handler: Handler, batch_size: int = 10) -> WorkerCycleResult:
    """Module-level convenience wrapper for callers that don't need to reuse a `QueueWorker`
    instance across cycles."""

    return QueueWorker(handler=handler).run_once(session, batch_size=batch_size)


__all__ = [
    "Handler",
    "QueueWorker",
    "WorkerCycleResult",
    "get_objective",
    "run_once",
]
