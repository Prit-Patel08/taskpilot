from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class OutboxEventCreateData(BaseModel):
    event_name: str
    payload: dict[str, Any]
    headers: dict[str, Any]


class OutboxPublishEnvelope(BaseModel):
    id: UUID
    event_name: str
    payload: dict[str, Any]
    headers: dict[str, Any]
    attempts: int
