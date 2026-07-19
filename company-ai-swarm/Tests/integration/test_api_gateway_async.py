"""Phase B exit-criteria test (Documentation/plans/SDK_MIGRATION_PLAN.md Section 6:
test_api_gateway_async.py "fire-and-forget endpoints, polling result"): the full async
round-trip through the real HTTP layer - POST /chat (fire-and-forget) -> queue worker
processes it -> GET /objectives/{id}/result -> GET /chat shows the eventual reply -> GET
/activity's in_flight_objectives reflects queued/executing/settled states.

Uses `main.drain_queue_once()` to force one worker cycle deterministically instead of
sleeping and hoping a background thread got to it - see main.py's comment on why no
background thread runs during tests.

Updated for Documentation/plans/2026-07-19-dynamic-department-routing-design.md's sufficiency
check: StubModelProvider's fixed placeholder text is never parseable sufficiency JSON, so a
single /chat call no longer reliably enqueues - it comes back needs_clarification for up to 2
rounds first (both rounds hit the JSON-parse-failure fallback path in orchestrator/intake.py,
since the stub ignores the prompt's round-specific instructions entirely). _send_until_queued()
resends the same message until it's actually queued, bounded at 3 attempts by the sufficiency
check's own hard cap, so these tests keep exercising the same async-queue behavior they always
did, just past that new gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api_gateway"))

from fastapi.testclient import TestClient

import main as gateway_main

HEADERS = {"X-API-Key": "dev-only-api-key"}


def _client() -> TestClient:
    return TestClient(gateway_main.app)


def _send_until_queued(client: TestClient, message: str) -> dict:
    """Resends `message` until POST /chat returns status="queued", instead of assuming a
    fixed round count - tests in this file share one persistent dev database
    (apps/api_gateway/main.py's module-level session factory), so leftover
    clarification-round state left over from a previous test can vary. The sufficiency
    check's own 3-round cap (orchestrator/intake.py) guarantees this converges within 3
    attempts regardless of starting state."""

    body: dict = {}
    for _ in range(3):
        body = client.post("/chat", headers=HEADERS, json={"message": message}).json()
        if body.get("status") == "queued":
            return body
    return body


def test_chat_is_fire_and_forget() -> None:
    client = _client()
    body = _send_until_queued(client, "Research current market trends.")

    assert body["objective_id"].startswith("OBJ-")
    assert body["status"] == "queued"
    # The old synchronous shape is gone from this endpoint - it moved to /chat/sync.
    assert "reply" not in body
    assert "decision_id" not in body


def test_result_endpoint_reflects_full_lifecycle() -> None:
    client = _client()
    objective_id = _send_until_queued(client, "Research current market trends.")["objective_id"]

    queued = client.get(f"/objectives/{objective_id}/result", headers=HEADERS)
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"
    assert queued.json()["result"] is None

    cycle = gateway_main.drain_queue_once()
    assert objective_id in cycle.claimed

    settled = client.get(f"/objectives/{objective_id}/result", headers=HEADERS)
    assert settled.status_code == 200
    body = settled.json()
    assert body["status"] in {"completed", "failed"}
    assert body["started_at"] is not None
    assert body["completed_at"] is not None


def test_result_endpoint_requires_api_key() -> None:
    response = _client().get("/objectives/OBJ-doesnotexist/result")
    assert response.status_code == 401


def test_result_endpoint_404s_on_unknown_id() -> None:
    response = _client().get("/objectives/OBJ-doesnotexist/result", headers=HEADERS)
    assert response.status_code == 404


def test_chat_history_shows_reply_after_worker_processes_it() -> None:
    client = _client()
    objective_id = _send_until_queued(client, "Research quantum computing basics.")["objective_id"]

    gateway_main.drain_queue_once()

    result = client.get(f"/objectives/{objective_id}/result", headers=HEADERS).json()
    assert result["status"] == "completed"
    reply = result["result"]["reply"]

    history = client.get("/chat", headers=HEADERS).json()
    assert history["messages"][-1]["role"] == "coo"
    assert history["messages"][-1]["content"] == reply


def test_no_matching_department_completes_not_fails() -> None:
    """The pre-Phase-B synchronous /chat treated NoMatchingDepartmentError as a normal
    reply, not an HTTP error - the async path must preserve that (see
    dashboard_api._run_objective_and_format_reply's docstring).

    Note: by the time this reaches round 3, the consolidated objective text
    (orchestrator/intake.py + dashboard_api._consolidate_intake_conversation) includes the
    COO's own fallback clarifying-question text alongside "xyz qqq zzz" three times. If this
    assertion ever starts failing because the consolidated text accidentally overlaps some
    department's keywords, that's a real signal worth investigating (KeywordDepartmentClassifier
    is unchanged, keyword-overlap based) - don't just swap in a different nonsense string
    without checking why first."""

    client = _client()
    # Same input test_api_gateway_objectives.py uses for /objectives' 400 case - department
    # matching is keyword-based, so this needs to be an exact known non-match, not just
    # gibberish (a generic message can still route broadly across every department).
    objective_id = _send_until_queued(client, "xyz qqq zzz")["objective_id"]

    gateway_main.drain_queue_once()

    result = client.get(f"/objectives/{objective_id}/result", headers=HEADERS).json()
    assert result["status"] == "completed"
    assert "No department matched" in result["result"]["reply"]
    assert result["result"]["decision_id"] is None


def test_activity_shows_in_flight_objective_before_draining() -> None:
    client = _client()
    objective_id = _send_until_queued(client, "Research current market trends.")["objective_id"]

    activity = client.get("/activity", headers=HEADERS).json()
    in_flight_ids = {o["id"] for o in activity["in_flight_objectives"]}
    assert objective_id in in_flight_ids

    gateway_main.drain_queue_once()

    activity_after = client.get("/activity", headers=HEADERS).json()
    in_flight_ids_after = {o["id"] for o in activity_after["in_flight_objectives"]}
    assert objective_id not in in_flight_ids_after


def test_chat_insufficient_request_asks_a_clarifying_question_without_enqueueing() -> None:
    """StubModelProvider's fixed text isn't parseable JSON, so the default dev/test gateway
    always fails toward 'insufficient' with the fallback question - this test exercises that
    real code path (not a mock standing in for it), same as
    test_coo_orchestration.py's new assess_sufficiency test."""

    client = _client()

    response = client.post("/chat", headers=HEADERS, json={"message": "Do something vague"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert "reply" in body
    assert "objective_id" not in body

    history = client.get("/chat", headers=HEADERS).json()
    assert history["messages"][-1]["role"] == "coo"
    assert history["messages"][-1]["content"] == body["reply"]


def test_chat_third_round_forces_proceed_and_enqueues() -> None:
    """Two clarifying rounds, then a third message must enqueue regardless of what the
    (stub-backed, always-insufficient) sufficiency check would otherwise say."""

    client = _client()

    # This file's tests share one persistent dev database (see _send_until_queued's
    # docstring above), so a trailing clarifying round left dangling by a previous test
    # (e.g. test_chat_insufficient_request_..., which deliberately stops after one
    # needs_clarification reply without draining) would shift the round arithmetic this
    # test depends on by however many rounds are still pending. Push any such leftover
    # round through to completion and drain it so the round-by-round sequence below is
    # guaranteed to start at round 1, regardless of what ran immediately before it (or
    # if this test is run standalone with a completely fresh database).
    _send_until_queued(client, "warm-up message to clear any leftover clarifying round")
    gateway_main.drain_queue_once()

    first = client.post("/chat", headers=HEADERS, json={"message": "round one"})
    assert first.json()["status"] == "needs_clarification"

    second = client.post("/chat", headers=HEADERS, json={"message": "round two"})
    assert second.json()["status"] == "needs_clarification"

    third = client.post("/chat", headers=HEADERS, json={"message": "round three"})
    body = third.json()
    assert body["status"] == "queued"
    assert "objective_id" in body

    # The enqueued objective consolidates the whole exchange, not just "round three".
    gateway_main.drain_queue_once()
    result = client.get(f"/objectives/{body['objective_id']}/result", headers=HEADERS).json()
    assert "round one" in result["objective"]
    assert "round two" in result["objective"]
    assert "round three" in result["objective"]
