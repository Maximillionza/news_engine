"""Enterprise Service Bus.

Source: Specifications/2 - construction-framework/The Company Technical Architecture
Specification (TAS).md Layer 7 (Enterprise Service Bus), and RCS's Universal Request/
Response Contract + Service Contract.

Lives in services/shared/ rather than a dedicated services/<name>/ directory because CRBS's
repository blueprint names an event_service but no separate service-bus directory - routing
between services is treated as shared infrastructure (like shared/db.py, shared/contracts.py)
rather than a domain service. If a dedicated service ever needs its own lifecycle
(deployment, scaling) separate from other shared modules, split it out then.

Per RCS Principle 002 and IMPLEMENTATION_PLAN.md Phase 3 exit criteria, every dispatch is
authorized through security_service.authorize() using the request's own security_context
before the target handler runs.
"""

from __future__ import annotations

import time
from typing import Callable

from sqlalchemy.orm import Session

from observability_service.telemetry import TelemetryResult, TelemetrySink, default_sink
from security_service.permissions import authorize
from shared.contracts import RequestContract, ResponseContract, ResponseStatus, ServiceContract

ServiceHandler = Callable[[RequestContract], dict]


class InMemoryServiceBus:
    def __init__(self, telemetry: TelemetrySink | None = None) -> None:
        self._services: dict[str, ServiceContract] = {}
        self._handlers: dict[str, ServiceHandler] = {}
        # Deliberately `is None`, not `telemetry or default_sink`: TelemetrySink defines
        # __len__, so an empty (freshly-created) sink is falsy and `or` would silently
        # discard it in favour of default_sink.
        self._telemetry = telemetry if telemetry is not None else default_sink

    def register(self, contract: ServiceContract, handler: ServiceHandler) -> None:
        """Register a service and the handler that fulfils requests addressed to it."""

        self._services[contract.name] = contract
        self._handlers[contract.name] = handler

    def get_service(self, name: str) -> ServiceContract | None:
        return self._services.get(name)

    def dispatch(self, session: Session, request: RequestContract) -> ResponseContract:
        """Authorize, then invoke the registered handler for `request.receiver`.

        Always returns a ResponseContract - denial, an unknown receiver, and handler
        exceptions are all represented as a response rather than a raised exception, since
        (per RCS sec.7) failure is a status, not necessarily a control-flow break for the
        caller.
        """

        start = time.perf_counter()

        if request.receiver not in self._handlers:
            duration_ms = (time.perf_counter() - start) * 1000
            self._telemetry.record(
                component="service_bus",
                action=f"dispatch:{request.receiver}:{request.action}",
                duration_ms=duration_ms,
                result=TelemetryResult.FAILURE,
                error="unknown receiver",
            )
            return ResponseContract(
                request_id=request.id,
                status=ResponseStatus.FAILURE,
                errors=[f"Unknown receiver: {request.receiver}"],
                trace_id=request.trace_id,
            )

        result = authorize(
            session,
            identity_id=request.security_context.identity,
            resource=f"service:{request.receiver}",
            action=request.action,
        )
        if not result.allowed:
            duration_ms = (time.perf_counter() - start) * 1000
            self._telemetry.record(
                component="service_bus",
                action=f"dispatch:{request.receiver}:{request.action}",
                duration_ms=duration_ms,
                result=TelemetryResult.DENIED,
                error=result.reason,
            )
            return ResponseContract(
                request_id=request.id,
                status=ResponseStatus.DENIED,
                errors=[result.reason],
                trace_id=request.trace_id,
            )

        handler = self._handlers[request.receiver]
        try:
            output = handler(request)
        except Exception as exc:  # noqa: BLE001 - represented as a FAILURE response
            duration_ms = (time.perf_counter() - start) * 1000
            self._telemetry.record(
                component="service_bus",
                action=f"dispatch:{request.receiver}:{request.action}",
                duration_ms=duration_ms,
                result=TelemetryResult.FAILURE,
                error=str(exc),
            )
            return ResponseContract(
                request_id=request.id,
                status=ResponseStatus.FAILURE,
                errors=[str(exc)],
                trace_id=request.trace_id,
            )

        duration_ms = (time.perf_counter() - start) * 1000
        self._telemetry.record(
            component="service_bus",
            action=f"dispatch:{request.receiver}:{request.action}",
            duration_ms=duration_ms,
            result=TelemetryResult.SUCCESS,
        )
        return ResponseContract(
            request_id=request.id,
            status=ResponseStatus.SUCCESS,
            result=output,
            trace_id=request.trace_id,
        )
