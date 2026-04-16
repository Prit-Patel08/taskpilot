from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ApplyRequestedEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_name: Literal["apply.requested"] = "apply.requested"
    request_id: str
    user_id: str
    resource_id: UUID
    correlation_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]


class ApplyExecuteEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_name: Literal["apply.execute"] = "apply.execute"
    request_id: str
    user_id: str
    resource_id: UUID
    correlation_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]
