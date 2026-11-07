from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import Field, Schema


class CreateThreadIn(Schema):
    title: str = Field(
        min_length=1,
        max_length=120,
        pattern=r".*\S.*",
        description="Short conversation title.",
    )


class CreateMessageIn(Schema):
    text: str = Field(
        min_length=1,
        max_length=4_000,
        pattern=r".*\S.*",
        description="User-authored message. It is stored but not sent to an LLM yet.",
    )


class PageQuery(Schema):
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10_000)


class ThreadOut(Schema):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AgentCitationOut(Schema):
    source_number: int
    title: str
    page: int | None
    excerpt: str


class MessageOut(Schema):
    id: UUID
    role: Literal["user", "assistant"]
    body: str
    status: Literal["stored", "pending", "completed", "failed"]
    created_at: datetime
    citations: list[AgentCitationOut]


class AgentRunOut(Schema):
    id: UUID
    status: Literal["completed"]
    model: str
    llm_calls: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    message: MessageOut
    citations: list[AgentCitationOut]


class ThreadPageOut(Schema):
    items: list[ThreadOut]
    total: int
    limit: int
    offset: int


class MessagePageOut(Schema):
    items: list[MessageOut]
    total: int
    limit: int
    offset: int
