from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class ApplicationCreatedEvent(BaseModel):
    event_id: UUID
    event_name: Literal["application.created"]
    request_id: str
    user_id: str
    resource_id: UUID
    created_at: datetime
    payload: dict[str, Any]
