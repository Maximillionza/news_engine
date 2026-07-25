"""Dashboard API endpoints (apps/api_gateway/dashboard_api.py).

Follows test_api_gateway_objectives.py's pattern (sys.path insert, fresh TestClient, real
COOOrchestrator underneath - no mocks). Covers the aggregated /activity poll target, file
upload to the pickup inbox, and the proposal endpoints' auth surface.

Phase B (Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.2) made `POST /chat`
fire-and-forget - it no longer returns a decision_id immediately, and the "coo" reply isn't
written until a queue worker processes the objective. The full async round-trip (POST /chat
-> drain the queue -> GET /objectives/{id}/result -> GET /chat shows the reply) is covered in
Tests/integration/test_api_gateway_async.py; this file keeps `/chat/sync`'s test, since that
endpoint preserves the exact pre-Phase-B synchronous behavior these tests originally covered.
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

    # Phase B addition (SDK_MIGRATION_PLAN.md Section 4.3) - present even when nothing is
    # in flight.
    assert isinstance(data["in_flight_objectives"], list)
    assert data["metrics"]["objectives_in_flight"] == len(data["in_flight_objectives"])


def _send_sync_until_processed(client: TestClient, message: str) -> dict:
    """Resends `message` to /chat/sync until it actually runs through the COO (decision_id is
    not None), instead of assuming a fixed round count - mirrors
    test_api_gateway_async.py's _send_until_queued() for the same reason: /chat/sync shares
    the same DashboardChatMessage table (and therefore the same round-counting) as /chat, so
    leftover clarification-round state from another test in this shared persistent dev
    database can vary. Bounded at 3 attempts by the sufficiency check's own hard cap
    (orchestrator/intake.py)."""

    body: dict = {}
    for _ in range(3):
        body = client.post("/chat/sync", headers=HEADERS, json={"message": message}).json()
        if body.get("decision_id") is not None:
            return body
    return body


def test_chat_sync_message_routes_through_coo_and_returns_last_ten() -> None:
    """POST /chat/sync preserves the pre-Phase-B blocking behavior these dashboard tests
    originally exercised - see this module's docstring. Phase 15 (2026-07-23) added the same
    sufficiency pre-flight check /chat already had, so a single call is no longer guaranteed
    to route through immediately - see _send_sync_until_processed()."""

    client = _client()
    response = _send_sync_until_processed(client, "Research current market trends.")
    assert response["decision_id"] is not None

    history = client.get("/chat", headers=HEADERS)
    assert history.status_code == 200
    body = history.json()
    assert len(body["messages"]) <= 10
    assert body["messages"][-1]["role"] == "coo"


def test_chat_sync_insufficient_request_asks_a_clarifying_question_without_processing() -> None:
    """StubModelProvider's fixed text isn't parseable JSON, so the default dev/test gateway
    always fails toward 'insufficient' with the fallback question - same real code path as
    test_api_gateway_async.py's equivalent /chat test, exercised here for /chat/sync.

    Deliberately uses "Research current market trends." - a message the pre-existing test in
    this file already proves matches a real department under keyword classification - so a
    None decision_id here can only mean the sufficiency gate blocked it, not an unrelated
    NoMatchingDepartmentError coincidence (an earlier, vaguer message caused exactly that
    false-positive during development of this test)."""

    client = _client()

    response = client.post(
        "/chat/sync", headers=HEADERS, json={"message": "Research current market trends."}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision_id"] is None
    assert "reply" in body

    history = client.get("/chat", headers=HEADERS).json()
    assert history["messages"][-1]["role"] == "coo"
    assert history["messages"][-1]["content"] == body["reply"]


def test_chat_sync_third_round_forces_proceed() -> None:
    """Two clarifying rounds, then a third message must process regardless of what the
    (stub-backed, always-insufficient) sufficiency check would otherwise say - mirrors
    test_api_gateway_async.py's test_chat_third_round_forces_proceed_and_enqueues().

    All three rounds use "Research current market trends." (proven to match a real
    department, see the insufficient-request test above) plus a distinguishing suffix, so a
    non-None decision_id on round three can only mean the round cap forced it through, not
    that department matching coincidentally succeeded or failed."""

    client = _client()

    # Clear any leftover clarifying round from a previous test sharing this persistent dev
    # database, same discipline as the async test's warm-up call.
    _send_sync_until_processed(client, "Research current market trends. (warm-up)")

    first = client.post(
        "/chat/sync", headers=HEADERS, json={"message": "Research current market trends. (round one)"}
    )
    assert first.json()["decision_id"] is None

    second = client.post(
        "/chat/sync", headers=HEADERS, json={"message": "Research current market trends. (round two)"}
    )
    assert second.json()["decision_id"] is None

    third = client.post(
        "/chat/sync", headers=HEADERS, json={"message": "Research current market trends. (round three)"}
    )
    third_body = third.json()
    assert third_body["decision_id"] is not None

    # The processed objective consolidates the whole exchange, not just round three.
    result = client.get(f"/objectives/{third_body['decision_id']}", headers=HEADERS).json()
    assert "(round one)" in result["objective"]
    assert "(round two)" in result["objective"]
    assert "(round three)" in result["objective"]


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


def test_chat_sync_department_rejection_is_a_normal_reply_not_an_error() -> None:
    """The sufficiency gate runs before department dispatch, so _AlwaysRejectHead below is
    never exercised unless the round cap has already been reached first (Phase 15, 2026-07-23)
    - warm up with the real (non-swapped) head to legitimately reach a processed state, which
    resets the round counter, then swap in the always-reject head and push through exactly 3
    more rounds to deterministically land on the forced-sufficient round."""

    from orchestrator.head import HeadVerdict

    class _AlwaysRejectHead:
        def evaluate(self, department, objective, **_):
            return HeadVerdict(accepted=False, reasoning="Rejected for test.", suggested_department_id=None)

    client = _client()
    _send_sync_until_processed(client, "Research current market trends. (warm-up, real head)")

    original_head = gateway_main._coo._head
    gateway_main._coo._head = _AlwaysRejectHead()
    try:
        client.post("/chat/sync", headers=HEADERS, json={"message": "Research current market trends. (r1)"})
        client.post("/chat/sync", headers=HEADERS, json={"message": "Research current market trends. (r2)"})
        response = client.post(
            "/chat/sync", headers=HEADERS, json={"message": "Research current market trends. (r3)"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["decision_id"] is None
        assert "rejected" in body["reply"].lower()
    finally:
        gateway_main._coo._head = original_head


class _SequencedJSONThenGenericProvider:
    """Returns each queued JSON response in order for the gate calls (sufficiency, scope
    confirmation) this test controls precisely, then falls back to plain non-JSON text for
    every call after that - the real department agents' own dispatch() calls, whose exact
    count isn't this test's concern and don't need parseable JSON, just non-empty output."""

    def __init__(self, json_responses: list[str]) -> None:
        self._responses = list(json_responses)
        self.prompts: list[str] = []

    def generate(self, prompt: str, *, allowed_tools=None, model=None) -> str:
        self.prompts.append(prompt)
        if self._responses:
            return self._responses.pop(0)
        return "[generic agent output]"


def test_chat_sync_multi_department_objective_asks_scope_confirmation_then_proceeds() -> None:
    """Phase 22 (IMPLEMENTATION_PLAN.md, 2026-07-26): end-to-end through the real gateway -
    a multi-department objective gets a scope-confirmation question after sufficiency passes,
    and the reply to that question is not asked again (is_scope_confirmation gate), letting
    the objective actually process."""

    import json

    client = _client()
    _send_sync_until_processed(client, "Research current market trends. (warm-up, real gateway)")

    provider = _SequencedJSONThenGenericProvider(
        [
            json.dumps({"sufficient": True, "clarifying_question": None, "reasoning": "Clear enough."}),
            json.dumps(
                {
                    "needs_confirmation": True,
                    "clarifying_question": "Just the build, or the full review too?",
                    "reasoning": "Genuinely ambiguous.",
                }
            ),
            json.dumps({"sufficient": True, "clarifying_question": None, "reasoning": "Still clear."}),
        ]
    )
    original_provider = gateway_main._coo._model_gateway._provider
    gateway_main._coo._model_gateway.replace_provider(provider)
    try:
        first = client.post(
            "/chat/sync",
            headers=HEADERS,
            json={"message": "Research current trends and build a working prototype based on the findings."},
        )
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["decision_id"] is None
        assert first_body["reply"] == "Just the build, or the full review too?"

        second = client.post(
            "/chat/sync", headers=HEADERS, json={"message": "Just the build, thanks."}
        )
        assert second.status_code == 200
        second_body = second.json()
        assert second_body["decision_id"] is not None
    finally:
        gateway_main._coo._model_gateway.replace_provider(original_provider)
