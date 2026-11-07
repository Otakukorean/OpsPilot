from typing import Literal
from uuid import UUID

from ninja import Field, Schema
from pydantic import SecretStr


class LoginIn(Schema):
    email: str = Field(
        min_length=3,
        max_length=254,
        description="Email address for an active OpsPilot user.",
        json_schema_extra={"format": "email"},
    )
    password: SecretStr = Field(
        min_length=1,
        max_length=128,
        description="User password. It is never returned or logged by the API.",
    )


class WorkspaceOut(Schema):
    id: UUID = Field(description="Server-issued workspace identifier.")
    name: str = Field(description="Display name of the workspace.")


class MembershipOut(Schema):
    workspace: WorkspaceOut
    role: Literal["admin", "analyst", "viewer"] = Field(
        description="Role resolved from the active server-side membership."
    )


class UserContextOut(Schema):
    id: UUID
    email: str
    first_name: str
    last_name: str
    membership: MembershipOut | None = Field(
        description="The user's active workspace membership, if one exists."
    )


class MessageOut(Schema):
    message: str


class ErrorOut(Schema):
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Safe human-readable error message.")
    request_id: str = Field(description="Correlation ID for troubleshooting.")


class ValidationIssueOut(Schema):
    location: str
    message: str
    type: str


class ValidationErrorOut(ErrorOut):
    details: list[ValidationIssueOut]
