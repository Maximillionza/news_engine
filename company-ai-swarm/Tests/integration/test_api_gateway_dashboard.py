"""Dashboard API endpoints (apps/api_gateway/dashboard_api.py).

Follows test_api_gateway_objectives.py's pattern (sys.path insert, fresh TestClient, real
COOOrchestrator underneath - no mocks). Covers the aggregated /activity poll target, the
COO chat round-trip (message -> objective -> reply), file upload to the pickup inbox, and
the proposal endpoints' auth surface.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api_gateway"))

from fastapi.testclient import TestClient

import main as gateway_main

HEADERS = {"X-API-Key": "dev-only-api-key"}


def _client() -> TestClient:
    return TestClient(gateway_main.app)


def test_activity_requires_api_key() -> None:
    response = _client().get("/activity")
    assert response.status_code == 401


def test_activity_aggregates_departments_agents_and_metrics() -> None:
    response = _client().get("/activity", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()

    department_ids = {d["id"] for d in data["departments"]}
    assert {"research", "engineering", "compliance", "operations"} <= department_ids

    assert data["metrics"]["agents_total"] == len(data["agents"])
    for agent in data["agents"]:
        assert agent["status"] in {"working", "idle"}


def test_chat_message_routes_through_coo_and_returns_last_ten() -> None:
    client = _client()
    response = client.post(
        "/chat", headers=HEADERS, json={"message": "Research current market trends."}
    )
    assert response.status_code == 200
    assert response.json()["decision_id"] is not None

    history = client.get("/chat", headers=HEADERS)
    assert history.status_code == 200
    body = history.json()
    assert len(body["messages"]) <= 10
    assert body["messages"][-1]["role"] == "coo"


def test_file_upload_saves_to_inbox() -> None:
    content = base64.b64encode(b"hello swarm").decode()
    response = _client().post(
        "/files", headers=HEADERS, json={"filename": "notes.txt", "content_base64": content}
    )
    assert response.status_code == 200
    saved = Path(response.json()["path"])
    assert saved.exists()
    assert saved.read_bytes() == b"hello swarm"
    saved.unlink()


def test_proposal_actions_404_on_unknown_id() -> None:
    response = _client().post("/proposals/PROP-nope/approve", headers=HEADERS)
    assert response.status_code == 404
