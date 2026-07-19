"""Queue worker: polls `objective_queue`, claims a row, runs a handler, records the outcome.

Source: Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.2/5. Phase A shipped the
claim/execute/record mechanics (`QueueWorker.run_once`) against a trivial stub handler, with
no dependency on COOOrchestrator. Phase B ("Queue worker core loop") adds:

    1. `run_forever()` - the actual polling loop ("every 100ms", Section 4.2 item 3),
       intended to run as its own OS process (Section 4.2 item 3: "New background worker
       (separate from FastAPI process)") - see Scripts/run_queue_worker.py - not an
       in-process background thread inside apps/api_gateway/main.py. Keeping it a separate
       process means the FastAPI app's module import (which Tests/integration/*.py trigger
       repeatedly against the same on-disk dev sqlite file) never has a live worker racing
       test assertions in the background.
    2. `Handler` now takes `(session, record)` instead of `(objective, required_output)` -
       the real handler (`apps/api_gateway/dashboard_api.py`'s `build_queue_handler`) needs
       the session to call `COOOrchestrator.receive_objective()` and to write the dashboard's
       chat reply in the same transaction, and needs the full record for `submitted_by`/`id`,
       not just the two prompt fields. This is a breaking change to Phase A's own handler
       signature; Tests/integration/test_async_objective_queue.py is updated to match.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session, sessionmaker

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

Handler = Callable[[Session, ObjectiveQueueRecord], dict[str, Any]]

DEFAULT_POLL_INTERVAL_SECONDS = 0.1


@dataclass
class WorkerCycleResult:
    """What one `run_once()` call did, for callers (tests, `run_forever()`'s loop) that want
    to log or assert on it without re-querying the table."""

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
        no row-level locking (e.g. `SELECT ... FOR UPDATE SKIP LOCKED`) between them. This
        codebase runs exactly one worker process (Scripts/run_queue_worker.py); concurrent
        workers are out of scope until that's needed."""

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
            result = self._handler(session, record)
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


def run_forever(
    session_factory: sessionmaker[Session],
    *,
    handler: Handler,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    batch_size: int = 10,
    stop_event: threading.Event | None = None,
) -> None:
    """The actual "poll `objective_queue` every 100ms" loop (Section 4.2 item 3). Opens one
    short-lived session per cycle (not one long-lived session for the process's whole
    lifetime) so a handler exception or a long `receive_objective()` call can't leave a
    session open and accumulating uncommitted state across cycles.

    Runs until `stop_event` is set (default: never - the intended caller is a dedicated
    process, see Scripts/run_queue_worker.py, killed by the OS rather than asked to stop
    in-process). Tests that need a bounded run should pass their own `threading.Event` and
    set it from another thread, or call `run_once`/`QueueWorker.run_once` directly instead -
    this function is for the standalone worker process, not for test assertions that need a
    single deterministic cycle.
    """

    worker = QueueWorker(handler=handler)
    stop_event = stop_event if stop_event is not None else threading.Event()
    while not stop_event.is_set():
        with session_factory() as session:
            worker.run_once(session, batch_size=batch_size)
        stop_event.wait(poll_interval_seconds)


__all__ = [
    "DEFAULT_POLL_INTERVAL_SECONDS",
    "Handler",
    "QueueWorker",
    "WorkerCycleResult",
    "get_objective",
    "run_forever",
    "run_once",
]
