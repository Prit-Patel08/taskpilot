from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ResumeCreatedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_name: Literal["resume.created", "resume.process"] = "resume.created"
    request_id: str
    user_id: str
    resource_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]
