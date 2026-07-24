"""Phase 10: the API Gateway's EAAS sec.18 MVP endpoints (Objective submission, Task
tracking, Agent visibility, Result retrieval, Authentication) over the already-built
COOOrchestrator - no new orchestration logic, this tests the HTTP surface.

Follows Tests/integration/test_api_gateway_health.py's existing pattern (sys.path insert,
since apps/ is not on pytest's configured pythonpath - only services/ and sdk/ are).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api_gateway"))

from fastapi.testclient import TestClient

from main import _API_KEY, _coo, app  # noqa: E402 - must follow the sys.path insert above
from orchestrator.intake import SufficiencyAssessment  # noqa: E402

client = TestClient(app)
HEADERS = {"X-API-Key": _API_KEY}


def _assume_sufficient(monkeypatch) -> None:
    """StubModelProvider's fixed placeholder text is never parseable sufficiency JSON, so the
    real check (Phase 15, IMPLEMENTATION_PLAN.md, 2026-07-23) always says insufficient under
    the default dev/test gateway - and /objectives, unlike /chat(/sync), has no round-3
    forcing escape hatch (it's a stateless, single-shot endpoint, not a conversation). Tests
    below that are actually about routing/no-match/rejection behavior, not sufficiency, bypass
    the check the same way test_chat_returns_502_when_sufficiency_check_raises (Tests/
    integration/test_api_gateway_async.py) monkeypatches assess_sufficiency directly - the
    real insufficient-request path has its own dedicated test further down."""

    monkeypatch.setattr(
        _coo,
        "assess_sufficiency",
        lambda *a, **k: SufficiencyAssessment(sufficient=True, clarifying_question=None, reasoning="test bypass"),
    )


def test_health_endpoint_still_responds() -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_missing_api_key_is_rejected() -> None:
    response = client.get("/agents")
    assert response.status_code == 401


def test_wrong_api_key_is_rejected() -> None:
    response = client.get("/agents", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_list_agents_returns_the_mvp_roster() -> None:
    response = client.get("/agents", headers=HEADERS)
    assert response.status_code == 200
    ids = {a["id"] for a in response.json()}
    assert {"research_agent_001", "engineering_agent_001", "compliance_agent_001", "review_agent_001"} <= ids


def test_submit_objective_routes_to_research_and_result_is_retrievable(monkeypatch) -> None:
    _assume_sufficient(monkeypatch)
    response = client.post(
        "/objectives",
        headers=HEADERS,
        json={"objective": "Create a market intelligence report", "required_output": "A structured summary"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["objective_achieved"] is True
    assert body["departments"] == ["research"]
    assert body["tasks"][0]["agent_id"] == "research_agent_001"
    assert body["tasks"][0]["output"] != ""

    status_response = client.get(f"/objectives/{body['decision_id']}", headers=HEADERS)
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["objective"] == "Create a market intelligence report"
    assert "research_agent_001" in status_body["agents_selected"]


def test_submit_objective_with_no_matching_department_returns_400(monkeypatch) -> None:
    _assume_sufficient(monkeypatch)
    response = client.post(
        "/objectives", headers=HEADERS, json={"objective": "xyz qqq zzz", "required_output": "anything"}
    )
    assert response.status_code == 400


def test_unknown_decision_id_returns_404() -> None:
    response = client.get("/objectives/DEC-doesnotexist", headers=HEADERS)
    assert response.status_code == 404


def test_missing_required_fields_returns_422() -> None:
    response = client.post("/objectives", headers=HEADERS, json={"objective": "x"})
    assert response.status_code == 422


def test_submit_objective_insufficient_request_returns_422_with_clarifying_question() -> None:
    """Real stub-backed sufficiency check, no bypass - StubModelProvider's fixed text is never
    parseable JSON, so the default dev/test gateway always says insufficient. Unlike
    /chat(/sync), there's no round-3 forcing here (see this file's module-level docstring on
    _assume_sufficient) - a 422 with the clarifying question is the terminal response, not one
    step in a loop."""

    response = client.post(
        "/objectives",
        headers=HEADERS,
        json={"objective": "Create a market intelligence report", "required_output": "A structured summary"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]


def test_submit_objective_with_department_rejection_returns_400(monkeypatch) -> None:
    _assume_sufficient(monkeypatch)
    from orchestrator.head import HeadVerdict

    class _AlwaysRejectHead:
        def evaluate(self, department, objective, **_):
            return HeadVerdict(accepted=False, reasoning="Rejected for test.", suggested_department_id=None)

    original_head = _coo._head
    _coo._head = _AlwaysRejectHead()
    try:
        response = client.post(
            "/objectives",
            headers=HEADERS,
            json={"objective": "Create a market intelligence report", "required_output": "A structured summary"},
        )
        assert response.status_code == 400
    finally:
        _coo._head = original_head
