"""Enterprise Event Bus.

Source: Specifications/2 - construction-framework/The Company Technical Architecture
Specification (TAS).md Layer 7 (Event Bus), and the RCS Event Contract.

Dev/test implementation: in-process, synchronous fan-out pub/sub. Production deployment
swaps this for Redis Streams (Documentation/operations/technology_decisions.md) - the
interface (`publish`, `subscribe`) is deliberately small so that swap doesn't touch callers.

Per RCS Principle 002 and IMPLEMENTATION_PLAN.md Phase 3 exit criteria, every publish is
authorized through security_service.authorize() using the event's own security_context
before any subscriber sees it - an event with no permission to publish never reaches a
handler, regardless of how many subscribers exist.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from sqlalchemy.orm import Session

from observability_service.telemetry import TelemetryResult, TelemetrySink, default_sink
from security_service.permissions import authorize
from shared.contracts import EventContract

EventHandler = Callable[[EventContract], None]


class AuthorizationError(PermissionError):
    pass


class InMemoryEventBus:
    def __init__(self, telemetry: TelemetrySink | None = None) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        # Deliberately `is None`, not `telemetry or default_sink`: TelemetrySink defines
        # __len__, so an empty (freshly-created) sink is falsy and `or` would silently
        # discard it in favour of default_sink.
        self._telemetry = telemetry if telemetry is not None else default_sink

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, session: Session, event: EventContract) -> int:
        """Authorize, then dispatch to every subscriber of `event.type`.

        Returns the number of subscribers the event was delivered to. Raises
        AuthorizationError if the publishing identity lacks permission - subscribers are
        never invoked in that case.
        """

        start = time.perf_counter()
        result = authorize(
            session,
            identity_id=event.security_context.identity,
            resource=f"event:{event.type}",
            action="publish",
        )
        duration_ms = (time.perf_counter() - start) * 1000

        if not result.allowed:
            self._telemetry.record(
                component="event_bus",
                action=f"publish:{event.type}",
                duration_ms=duration_ms,
                result=TelemetryResult.DENIED,
                error=result.reason,
            )
            raise AuthorizationError(
                f"{event.security_context.identity} may not publish {event.type}: {result.reason}"
            )

        delivered = 0
        try:
            for handler in self._subscribers.get(event.type, []):
                handler(event)
                delivered += 1
        except Exception as exc:  # noqa: BLE001 - recorded, then re-raised
            self._telemetry.record(
                component="event_bus",
                action=f"publish:{event.type}",
                duration_ms=(time.perf_counter() - start) * 1000,
                result=TelemetryResult.FAILURE,
                error=str(exc),
            )
            raise

        self._telemetry.record(
            component="event_bus",
            action=f"publish:{event.type}",
            duration_ms=(time.perf_counter() - start) * 1000,
            result=TelemetryResult.SUCCESS,
        )
        return delivered
