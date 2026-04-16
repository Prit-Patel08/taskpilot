from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ResumeCreateRequest(BaseModel):
    file_key: str = Field(min_length=1, max_length=2048)

    @field_validator("file_key")
    @classmethod
    def normalize_file_key(cls, value: str) -> str:
        normalized = value.strip().lstrip("/")
        if not normalized:
            raise ValueError("file_key is required")
        if ".." in normalized.split("/"):
            raise ValueError("file_key must not contain parent path segments")
        return normalized


class ResumeCreateData(BaseModel):
    user_id: UUID
    file_key: str = Field(min_length=1, max_length=2048)


class ResumeReadResponse(BaseModel):
    resume_id: UUID
    user_id: UUID
    file_key: str
    created_at: datetime
    updated_at: datetime


class ResumeListResponse(BaseModel):
    resumes: list[ResumeReadResponse]


class ResumeCreatedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_name: Literal["resume.created"] = "resume.created"
    request_id: str
    user_id: str
    resource_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]
