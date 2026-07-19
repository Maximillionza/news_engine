"""Phase 0 exit-criteria test: RCS contract schemas validate example payloads.

For each contract type: one valid payload must parse successfully, and one deliberately
invalid payload must be rejected. This is the standalone test for
IMPLEMENTATION_PLAN.md Phase 0 - it requires no service, agent, or database to exist.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from shared.contracts import (
    AgentMessageContract,
    AuditRecordContract,
    Classification,
    EventContract,
    EventSeverity,
    HealthStatus,
    RequestContract,
    ResponseContract,
    ResponseStatus,
    SecurityContext,
    ServiceContract,
)


def _valid_security_context() -> SecurityContext:
    return SecurityContext(
        identity="AGT-000001",
        role="research_agent",
        permission="read:research_data",
        classification=Classification.INTERNAL,
    )


class TestRequestContract:
    def test_valid_request_parses(self) -> None:
        req = RequestContract(
            sender="coo",
            receiver="research_agent",
            purpose="Summarize market trends",
            action="execute_task",
            parameters={"topic": "renewable energy"},
            security_context=_valid_security_context(),
        )
        assert req.sender == "coo"
        assert req.security_context.identity == "AGT-000001"

    def test_missing_security_context_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RequestContract(
                sender="coo",
                receiver="research_agent",
                purpose="Summarize market trends",
                action="execute_task",
            )  # type: ignore[call-arg]

    def test_empty_sender_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RequestContract(
                sender="",
                receiver="research_agent",
                purpose="x",
                action="execute_task",
                security_context=_valid_security_context(),
            )


class TestResponseContract:
    def test_valid_response_parses(self) -> None:
        req_id = uuid4()
        trace_id = uuid4()
        resp = ResponseContract(
            request_id=req_id,
            status=ResponseStatus.SUCCESS,
            result={"summary": "..."},
            trace_id=trace_id,
        )
        assert resp.status == ResponseStatus.SUCCESS

    def test_invalid_status_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ResponseContract(
                request_id=uuid4(),
                status="not_a_real_status",  # type: ignore[arg-type]
                trace_id=uuid4(),
            )


class TestEventContract:
    def test_valid_event_parses(self) -> None:
        event = EventContract(
            type="TaskCompleted",
            source="workflow_engine",
            payload={"task_id": "TSK-000001"},
            severity=EventSeverity.INFO,
            security_context=_valid_security_context(),
        )
        assert event.type == "TaskCompleted"

    def test_empty_type_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EventContract(
                type="",
                source="workflow_engine",
                security_context=_valid_security_context(),
            )

    def test_missing_security_context_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EventContract(type="TaskCompleted", source="workflow_engine")  # type: ignore[call-arg]


class TestServiceContract:
    def test_valid_service_parses(self) -> None:
        svc = ServiceContract(
            name="identity_service",
            version="0.1.0",
            purpose="Manage identity records for humans, agents, and services.",
            health_status=HealthStatus.HEALTHY,
        )
        assert svc.name == "identity_service"

    def test_missing_purpose_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ServiceContract(name="identity_service", version="0.1.0")  # type: ignore[call-arg]


class TestAgentMessageContract:
    def test_valid_message_parses(self) -> None:
        msg = AgentMessageContract(
            sender_agent="coo",
            receiver_agent="research_agent",
            task="Research renewable energy trends",
            required_output="A structured summary with sources",
        )
        assert msg.task.startswith("Research")

    def test_empty_required_output_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentMessageContract(
                sender_agent="coo",
                receiver_agent="research_agent",
                task="Research renewable energy trends",
                required_output="",
            )


class TestAuditRecordContract:
    def test_valid_audit_record_parses(self) -> None:
        record = AuditRecordContract(
            actor="AGT-000001",
            action="read:research_data",
            output={"allowed": True},
        )
        assert record.actor == "AGT-000001"

    def test_empty_actor_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AuditRecordContract(actor="", action="read:research_data")
