from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ApplicationCreateRequest(BaseModel):
    resume_id: UUID
    job_listing_id: UUID


class ApplicationCreateData(BaseModel):
    user_id: UUID
    resume_id: UUID
    job_listing_id: UUID


class ApplicationAcceptedResponse(BaseModel):
    application_id: UUID
    status: str


class ApplicationReadResponse(BaseModel):
    application_id: UUID
    user_id: UUID
    status: str
    resume_id: UUID
    job_listing_id: UUID
    created_at: datetime


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationReadResponse]


class ApplicationCreatedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_name: Literal["application.created"] = "application.created"
    request_id: str
    user_id: str
    resource_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]
