from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import Field, Schema


class TransactionOut(Schema):
    id: UUID
    code: str = Field(description="Synthetic transaction reference.")
    status: str
    public_detail: str = Field(description="Safe, fictional operational detail.")
    created_at: datetime


class TicketOut(Schema):
    id: UUID
    code: str = Field(description="Synthetic support ticket reference.")
    status: str
    public_detail: str = Field(description="Safe, fictional support detail.")
    created_at: datetime


class TransactionQuery(Schema):
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=32,
        pattern=r".*\S.*",
        description="Exact synthetic transaction reference, case-insensitive.",
    )
    status: Literal["pending", "completed", "failed"] | None = None
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10_000)


class TicketQuery(Schema):
    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r".*\S.*",
        description="Search synthetic ticket code and safe public detail.",
    )
    status: Literal["open", "in_progress", "resolved"] | None = None
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10_000)


class TransactionPageOut(Schema):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int


class TicketPageOut(Schema):
    items: list[TicketOut]
    total: int
    limit: int
    offset: int
