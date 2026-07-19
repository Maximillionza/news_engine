"""RCS (Runtime Contract Specification) message contracts, implemented as validated schemas.

Source: Specifications/3 - execution-framework/Runtime Contract Specification (RCS).md

Per RCS Principle 004 ("Contracts Before Implementation"), these schemas exist before any
service that uses them. Per RCS Principle 002 ("Every Action Has Context"), SecurityContext
is a required field on every request, event, and agent message - not optional.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Classification(str, Enum):
    """ESTAS Sec.13 Data Security Architecture classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    HIGHLY_RESTRICTED = "highly_restricted"


class SecurityContext(BaseModel):
    """RCS Sec.17 Security Contract. Required on every request, event, and agent message."""

    identity: str = Field(..., min_length=1, description="Identity ID of the acting entity")
    role: str = Field(..., min_length=1)
    permission: str = Field(..., min_length=1, description="Permission being exercised")
    classification: Classification = Classification.INTERNAL
    approval: str | None = Field(default=None, description="Approval reference, if required")


class RequestContract(BaseModel):
    """RCS Sec.6 Universal Request Contract."""

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=_now)
    sender: str = Field(..., min_length=1)
    receiver: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    security_context: SecurityContext
    trace_id: UUID = Field(default_factory=uuid4)


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    PENDING = "pending"


class ResponseContract(BaseModel):
    """RCS Sec.7 Universal Response Contract."""

    request_id: UUID
    status: ResponseStatus
    result: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    trace_id: UUID


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class EventContract(BaseModel):
    """RCS Sec.11 Event Contract.

    Phase 3 addition: `security_context` was missing from the original Phase 0 schema.
    RCS Principle 002 ("Every Action Has Context") applies to events as much as requests -
    publishing is an action - so this brings EventContract in line with RequestContract
    rather than relying on the looser `permissions` list alone."""

    event_id: UUID = Field(default_factory=uuid4)
    type: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=_now)
    payload: dict[str, Any] = Field(default_factory=dict)
    severity: EventSeverity = EventSeverity.INFO
    security_context: SecurityContext
    permissions: list[str] = Field(default_factory=list)


class HealthStatus(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class ServiceContract(BaseModel):
    """RCS Sec.13 Service Contract."""

    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    health_status: HealthStatus = HealthStatus.UNKNOWN


class AgentMessageContract(BaseModel):
    """RCS Sec.8 Agent Communication Contract."""

    sender_agent: str = Field(..., min_length=1)
    receiver_agent: str = Field(..., min_length=1)
    task: str = Field(..., min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    required_output: str = Field(..., min_length=1)
    priority: str = "normal"
    permissions: list[str] = Field(default_factory=list)
    deadline: datetime | None = None


class AuditRecordContract(BaseModel):
    """ESTAS Sec.24 Audit Architecture schema, as a shared contract so every service that
    writes audit records (identity_service, security_service, and later the Agent Runtime)
    produces the same shape."""

    actor: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=_now)
    reason: str | None = None
    input_context: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    resources_used: list[str] = Field(default_factory=list)
    decision_path: list[str] = Field(default_factory=list)
    policy_evaluation: str | None = None
