"""Phase 3 exit-criteria test: synthetic producer/consumer for both the Service Bus
(request-response) and the Event Bus (publish-subscribe), with no real agents involved.

Source: IMPLEMENTATION_PLAN.md Phase 3 test spec:
    1. A test service registers on the Service Bus and responds to a request using the
       RCS Universal Request/Response Contract.
    2. A test event is published on the Event Bus and received by a subscribed test
       consumer.
    3. Both actions appear in telemetry with correct component/action/timestamp/duration
       fields, and both carry a valid security_context validated in Phase 1.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from event_service.bus import AuthorizationError, InMemoryEventBus
from identity_service.models import EntityType
from identity_service.repository import create_identity
from observability_service.telemetry import TelemetryResult, TelemetrySink
from security_service.permissions import grant_permission
from shared.contracts import (
    Classification,
    EventContract,
    RequestContract,
    ResponseStatus,
    SecurityContext,
    ServiceContract,
)
from shared.db import Base, make_engine, make_session_factory
from shared.service_bus import InMemoryServiceBus


@pytest.fixture()
def session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s


@pytest.fixture()
def telemetry() -> TelemetrySink:
    return TelemetrySink()


def _security_context(identity: str, role: str, permission: str) -> SecurityContext:
    return SecurityContext(
        identity=identity, role=role, permission=permission, classification=Classification.INTERNAL
    )


class TestServiceBus:
    def test_registered_service_responds_to_a_request(
        self, session: Session, telemetry: TelemetrySink
    ) -> None:
        create_identity(session, id="AGT-000001", entity_type=EntityType.AGENT, name="Caller Agent")
        grant_permission(session, subject="AGT-000001", resource="service:echo_service", action="echo")

        bus = InMemoryServiceBus(telemetry=telemetry)
        bus.register(
            ServiceContract(
                name="echo_service", version="0.1.0", purpose="Echoes the request payload back."
            ),
            handler=lambda request: {"echoed": request.parameters},
        )

        request = RequestContract(
            sender="AGT-000001",
            receiver="echo_service",
            purpose="test the service bus",
            action="echo",
            parameters={"message": "hello"},
            security_context=_security_context("AGT-000001", "caller", "service:echo_service:echo"),
        )

        response = bus.dispatch(session, request)

        assert response.status == ResponseStatus.SUCCESS
        assert response.result == {"echoed": {"message": "hello"}}
        assert response.request_id == request.id
        assert response.trace_id == request.trace_id

    def test_dispatch_without_permission_is_denied_not_delivered(
        self, session: Session, telemetry: TelemetrySink
    ) -> None:
        create_identity(session, id="AGT-000002", entity_type=EntityType.AGENT, name="Unpermitted Caller")

        delivered = []
        bus = InMemoryServiceBus(telemetry=telemetry)
        bus.register(
            ServiceContract(name="echo_service", version="0.1.0", purpose="Echo."),
            handler=lambda request: delivered.append(request) or {},
        )

        request = RequestContract(
            sender="AGT-000002",
            receiver="echo_service",
            purpose="unauthorized attempt",
            action="echo",
            security_context=_security_context("AGT-000002", "caller", "service:echo_service:echo"),
        )

        response = bus.dispatch(session, request)

        assert response.status == ResponseStatus.DENIED
        assert delivered == []  # handler never ran

    def test_unknown_receiver_returns_failure(self, session: Session, telemetry: TelemetrySink) -> None:
        create_identity(session, id="AGT-000001", entity_type=EntityType.AGENT, name="Caller")
        bus = InMemoryServiceBus(telemetry=telemetry)

        request = RequestContract(
            sender="AGT-000001",
            receiver="nonexistent_service",
            purpose="test",
            action="echo",
            security_context=_security_context("AGT-000001", "caller", "service:x:echo"),
        )

        response = bus.dispatch(session, request)

        assert response.status == ResponseStatus.FAILURE
        assert "Unknown receiver" in response.errors[0]

    def test_dispatch_produces_telemetry_with_required_fields(
        self, session: Session, telemetry: TelemetrySink
    ) -> None:
        create_identity(session, id="AGT-000001", entity_type=EntityType.AGENT, name="Caller Agent")
        grant_permission(session, subject="AGT-000001", resource="service:echo_service", action="echo")

        bus = InMemoryServiceBus(telemetry=telemetry)
        bus.register(
            ServiceContract(name="echo_service", version="0.1.0", purpose="Echo."),
            handler=lambda request: {},
        )
        bus.dispatch(
            session,
            RequestContract(
                sender="AGT-000001",
                receiver="echo_service",
                purpose="telemetry check",
                action="echo",
                security_context=_security_context("AGT-000001", "caller", "service:echo_service:echo"),
            ),
        )

        records = telemetry.query(component="service_bus")
        assert len(records) == 1
        record = records[0]
        assert record.action == "dispatch:echo_service:echo"
        assert record.timestamp is not None
        assert record.duration_ms >= 0
        assert record.result == TelemetryResult.SUCCESS


class TestEventBus:
    def test_published_event_is_received_by_subscriber(
        self, session: Session, telemetry: TelemetrySink
    ) -> None:
        create_identity(session, id="AGT-000003", entity_type=EntityType.AGENT, name="Publisher Agent")
        grant_permission(session, subject="AGT-000003", resource="event:TestEvent", action="publish")

        received = []
        bus = InMemoryEventBus(telemetry=telemetry)
        bus.subscribe("TestEvent", lambda event: received.append(event))

        event = EventContract(
            type="TestEvent",
            source="test-producer",
            payload={"detail": "something happened"},
            security_context=_security_context("AGT-000003", "publisher", "event:TestEvent:publish"),
        )

        delivered_count = bus.publish(session, event)

        assert delivered_count == 1
        assert len(received) == 1
        assert received[0].event_id == event.event_id
        assert received[0].payload == {"detail": "something happened"}

    def test_publish_without_permission_is_denied_not_delivered(
        self, session: Session, telemetry: TelemetrySink
    ) -> None:
        create_identity(session, id="AGT-000004", entity_type=EntityType.AGENT, name="Unpermitted Publisher")

        received = []
        bus = InMemoryEventBus(telemetry=telemetry)
        bus.subscribe("TestEvent", lambda event: received.append(event))

        event = EventContract(
            type="TestEvent",
            source="test-producer",
            security_context=_security_context("AGT-000004", "publisher", "event:TestEvent:publish"),
        )

        with pytest.raises(AuthorizationError):
            bus.publish(session, event)

        assert received == []  # subscriber never invoked

    def test_publish_produces_telemetry_with_required_fields(
        self, session: Session, telemetry: TelemetrySink
    ) -> None:
        create_identity(session, id="AGT-000003", entity_type=EntityType.AGENT, name="Publisher Agent")
        grant_permission(session, subject="AGT-000003", resource="event:TestEvent", action="publish")

        bus = InMemoryEventBus(telemetry=telemetry)
        bus.subscribe("TestEvent", lambda event: None)
        bus.publish(
            session,
            EventContract(
                type="TestEvent",
                source="test-producer",
                security_context=_security_context("AGT-000003", "publisher", "event:TestEvent:publish"),
            ),
        )

        records = telemetry.query(component="event_bus")
        assert len(records) == 1
        record = records[0]
        assert record.action == "publish:TestEvent"
        assert record.timestamp is not None
        assert record.duration_ms >= 0
        assert record.result == TelemetryResult.SUCCESS

    def test_multiple_subscribers_all_receive_the_event(
        self, session: Session, telemetry: TelemetrySink
    ) -> None:
        create_identity(session, id="AGT-000003", entity_type=EntityType.AGENT, name="Publisher Agent")
        grant_permission(session, subject="AGT-000003", resource="event:TestEvent", action="publish")

        counts = {"a": 0, "b": 0}
        bus = InMemoryEventBus(telemetry=telemetry)
        bus.subscribe("TestEvent", lambda event: counts.__setitem__("a", counts["a"] + 1))
        bus.subscribe("TestEvent", lambda event: counts.__setitem__("b", counts["b"] + 1))

        delivered_count = bus.publish(
            session,
            EventContract(
                type="TestEvent",
                source="test-producer",
                security_context=_security_context("AGT-000003", "publisher", "event:TestEvent:publish"),
            ),
        )

        assert delivered_count == 2
        assert counts == {"a": 1, "b": 1}
