from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import Field, Schema


class AuditQuery(Schema):
    action: str | None = Field(default=None, min_length=1, max_length=100)
    outcome: Literal["allowed", "denied"] | None = None
    resource_type: str | None = Field(default=None, min_length=1, max_length=32)
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10_000)


class AuditEventOut(Schema):
    id: UUID
    actor_id: UUID | None
    action: str
    outcome: Literal["allowed", "denied"]
    resource_type: str
    reason: str
    request_id: str
    duration_ms: float | None
    created_at: datetime


class AuditEventPageOut(Schema):
    items: list[AuditEventOut]
    total: int
    limit: int
    offset: int
