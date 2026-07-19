"""Phase B exit-criteria test (Documentation/plans/SDK_MIGRATION_PLAN.md Section 6:
test_api_gateway_async.py "fire-and-forget endpoints, polling result"): the full async
round-trip through the real HTTP layer - POST /chat (fire-and-forget) -> queue worker
processes it -> GET /objectives/{id}/result -> GET /chat shows the eventual reply -> GET
/activity's in_flight_objectives reflects queued/executing/settled states.

Uses `main.drain_queue_once()` to force one worker cycle deterministically instead of
sleeping and hoping a background thread got to it - see main.py's comment on why no
background thread runs during tests.
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


def test_chat_is_fire_and_forget() -> None:
    client = _client()
    response = client.post(
        "/chat", headers=HEADERS, json={"message": "Research current market trends."}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["objective_id"].startswith("OBJ-")
    assert body["status"] == "queued"
    # The old synchronous shape is gone from this endpoint - it moved to /chat/sync.
    assert "reply" not in body
    assert "decision_id" not in body


def test_result_endpoint_reflects_full_lifecycle() -> None:
    client = _client()
    objective_id = client.post(
        "/chat", headers=HEADERS, json={"message": "Research current market trends."}
    ).json()["objective_id"]

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
    objective_id = client.post(
        "/chat", headers=HEADERS, json={"message": "Research quantum computing basics."}
    ).json()["objective_id"]

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
    dashboard_api._run_objective_and_format_reply's docstring)."""

    client = _client()
    # Same input test_api_gateway_objectives.py uses for /objectives' 400 case - department
    # matching is keyword-based, so this needs to be an exact known non-match, not just
    # gibberish (a generic message can still route broadly across every department).
    objective_id = client.post(
        "/chat", headers=HEADERS, json={"message": "xyz qqq zzz"}
    ).json()["objective_id"]

    gateway_main.drain_queue_once()

    result = client.get(f"/objectives/{objective_id}/result", headers=HEADERS).json()
    assert result["status"] == "completed"
    assert "No department matched" in result["result"]["reply"]
    assert result["result"]["decision_id"] is None


def test_activity_shows_in_flight_objective_before_draining() -> None:
    client = _client()
    objective_id = client.post(
        "/chat", headers=HEADERS, json={"message": "Research current market trends."}
    ).json()["objective_id"]

    activity = client.get("/activity", headers=HEADERS).json()
    in_flight_ids = {o["id"] for o in activity["in_flight_objectives"]}
    assert objective_id in in_flight_ids

    gateway_main.drain_queue_once()

    activity_after = client.get("/activity", headers=HEADERS).json()
    in_flight_ids_after = {o["id"] for o in activity_after["in_flight_objectives"]}
    assert objective_id not in in_flight_ids_after
