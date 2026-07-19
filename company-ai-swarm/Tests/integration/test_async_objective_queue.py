"""Queue lifecycle test (Documentation/plans/SDK_MIGRATION_PLAN.md Section 6): queued ->
executing -> completed / failed, against the ORM model and CRUD functions directly - no HTTP
layer here (that's Tests/integration/test_api_gateway_async.py), and no COOOrchestrator
involved (the `handler` in every test below is a plain stub - the real one lives in
apps/api_gateway/dashboard_api.py's `build_queue_handler`).

Phase B updated `Handler`'s signature from `(objective, required_output) -> dict` to
`(session, record) -> dict` (queue_worker.py's docstring explains why); the stub handlers
here were updated to match.

apps/ is not a package (see apps/api_gateway/main.py's note on dashboard_api), so this test
sys.path-inserts apps/api_gateway and imports objective_queue / queue_worker as top-level
sibling modules, the same way Tests/integration/test_api_gateway_health.py imports `main`.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api_gateway"))

import pytest
from sqlalchemy.orm import Session

from objective_queue import (
    ObjectiveStatus,
    enqueue_objective,
    get_objective,
    list_queued_objectives,
    mark_completed,
    mark_executing,
    mark_failed,
)
from queue_worker import QueueWorker, run_once
from shared.db import Base, make_engine, make_session_factory


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


def test_enqueue_creates_queued_record(session: Session) -> None:
    record = enqueue_objective(
        session, objective="Research X", required_output="a summary", submitted_by="voice_director"
    )

    assert record.id.startswith("OBJ-")
    assert record.status == ObjectiveStatus.QUEUED.value
    assert record.submitted_by == "voice_director"
    assert record.started_at is None
    assert record.completed_at is None
    assert get_objective(session, record.id) is not None


def test_list_queued_objectives_is_oldest_first(session: Session) -> None:
    first = enqueue_objective(session, objective="first", required_output="out")
    second = enqueue_objective(session, objective="second", required_output="out")

    queued = list_queued_objectives(session)

    assert [r.id for r in queued] == [first.id, second.id]


def test_list_queued_objectives_excludes_non_queued(session: Session) -> None:
    record = enqueue_objective(session, objective="obj", required_output="out")
    mark_executing(session, record.id)

    assert list_queued_objectives(session) == []


def test_mark_executing_then_completed_lifecycle(session: Session) -> None:
    record = enqueue_objective(session, objective="obj", required_output="out")

    executing = mark_executing(session, record.id)
    assert executing.status == ObjectiveStatus.EXECUTING.value
    assert executing.started_at is not None

    completed = mark_completed(session, record.id, {"output": "done"})
    assert completed.status == ObjectiveStatus.COMPLETED.value
    assert completed.result == {"output": "done"}
    assert completed.completed_at is not None


def test_mark_failed_records_error(session: Session) -> None:
    record = enqueue_objective(session, objective="obj", required_output="out")
    mark_executing(session, record.id)

    failed = mark_failed(session, record.id, "boom")

    assert failed.status == ObjectiveStatus.FAILED.value
    assert failed.error == "boom"
    assert failed.completed_at is not None


def test_mark_executing_unknown_id_raises(session: Session) -> None:
    with pytest.raises(ValueError, match="Unknown objective_id"):
        mark_executing(session, "OBJ-doesnotexist")


def test_worker_run_once_completes_objective_via_handler(session: Session) -> None:
    enqueue_objective(session, objective="Research blockchain app ideas", required_output="ideas")

    def handler(worker_session: Session, record) -> dict[str, str]:
        assert worker_session is session
        return {"output": f"handled: {record.objective} -> {record.required_output}"}

    result = run_once(session, handler=handler)

    assert len(result.claimed) == 1
    assert result.claimed == result.completed
    assert result.failed == []

    record = get_objective(session, result.completed[0])
    assert record.status == ObjectiveStatus.COMPLETED.value
    assert record.result == {"output": "handled: Research blockchain app ideas -> ideas"}


def test_worker_run_once_marks_failed_on_handler_exception(session: Session) -> None:
    enqueue_objective(session, objective="obj", required_output="out")

    def failing_handler(worker_session: Session, record) -> dict[str, str]:
        raise RuntimeError("orchestrator exploded")

    result = run_once(session, handler=failing_handler)

    assert result.completed == []
    assert len(result.failed) == 1
    record = get_objective(session, result.failed[0])
    assert record.status == ObjectiveStatus.FAILED.value
    assert "orchestrator exploded" in record.error


def test_worker_processes_batch_independently(session: Session) -> None:
    """One failing objective in a batch must not prevent the others from completing."""

    ok_one = enqueue_objective(session, objective="ok-one", required_output="out")
    bad = enqueue_objective(session, objective="bad", required_output="out")
    ok_two = enqueue_objective(session, objective="ok-two", required_output="out")

    def handler(worker_session: Session, record) -> dict[str, str]:
        if record.objective == "bad":
            raise ValueError("bad objective")
        return {"output": record.objective}

    worker = QueueWorker(handler=handler)
    result = worker.run_once(session)

    assert set(result.claimed) == {ok_one.id, bad.id, ok_two.id}
    assert set(result.completed) == {ok_one.id, ok_two.id}
    assert result.failed == [bad.id]
    assert list_queued_objectives(session) == []


def test_worker_respects_batch_size(session: Session) -> None:
    for i in range(5):
        enqueue_objective(session, objective=f"obj-{i}", required_output="out")

    result = run_once(session, handler=lambda s, record: {"output": record.objective}, batch_size=2)

    assert len(result.claimed) == 2
    assert len(list_queued_objectives(session)) == 3


def test_run_forever_processes_until_stop_event_and_uses_fresh_sessions(tmp_path) -> None:
    """`run_forever()` opens one session per cycle (not one held open for its whole life) -
    proven by writing an objective mid-loop and asserting it still gets picked up, since a
    stale single-session view would not see a commit made from a different session."""

    import threading

    from shared.db import make_session_factory

    engine = make_engine(f"sqlite:///{tmp_path / 'run_forever.sqlite3'}")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)

    from queue_worker import run_forever

    processed: list[str] = []

    def handler(worker_session: Session, record) -> dict[str, str]:
        processed.append(record.objective)
        return {"output": record.objective}

    with factory() as seed_session:
        enqueue_objective(seed_session, objective="seeded-before-start", required_output="out")

    stop_event = threading.Event()
    worker_thread = threading.Thread(
        target=run_forever,
        kwargs={
            "session_factory": factory,
            "handler": handler,
            "poll_interval_seconds": 0.01,
            "stop_event": stop_event,
        },
        daemon=True,
    )
    worker_thread.start()

    deadline = time.monotonic() + 5
    while "seeded-before-start" not in processed and time.monotonic() < deadline:
        time.sleep(0.02)

    stop_event.set()
    worker_thread.join(timeout=2)

    assert "seeded-before-start" in processed
    assert not worker_thread.is_alive()
