"""Structured telemetry sink.

Source: Specifications/1 - enterprise-architecture/Enterprise Observability & Control Plane
Specification (EOCCS).md sec.6 (Enterprise Telemetry Model) and Specifications/3 -
execution-framework/Runtime Contract Specification (RCS).md sec.18 (Observability Contract).

Dev/test implementation: in-process list. Production deployment swaps this for a real
observability platform (per EDIS sec.21 "Observability Platform") - the interface (`record`,
`query`) is deliberately small so that swap doesn't touch callers, same pattern as
shared/db.py, shared/vector_store.py, and shared/object_storage.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class TelemetryResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


@dataclass(frozen=True)
class TelemetryRecord:
    """RCS sec.18 fields: component, action, timestamp, duration, result, error."""

    component: str
    action: str
    timestamp: datetime
    duration_ms: float
    result: TelemetryResult
    error: str | None = None


class TelemetrySink:
    def __init__(self) -> None:
        self._records: list[TelemetryRecord] = []

    def record(
        self,
        *,
        component: str,
        action: str,
        duration_ms: float,
        result: TelemetryResult,
        error: str | None = None,
    ) -> TelemetryRecord:
        rec = TelemetryRecord(
            component=component,
            action=action,
            timestamp=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            result=result,
            error=error,
        )
        self._records.append(rec)
        return rec

    def query(
        self, *, component: str | None = None, action: str | None = None
    ) -> list[TelemetryRecord]:
        results = self._records
        if component is not None:
            results = [r for r in results if r.component == component]
        if action is not None:
            results = [r for r in results if r.action == action]
        return results

    def __len__(self) -> int:
        return len(self._records)


# Module-level default sink. Buses in event_service/shared.service_bus record here unless a
# different sink is explicitly passed in - keeps call sites simple while still allowing
# tests to construct an isolated TelemetrySink() when they need to assert on it in isolation.
default_sink = TelemetrySink()
