from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class TokenClaims(BaseModel):
    auth_subject: str
    email: str | None = None


class CurrentUser(BaseModel):
    id: UUID
    auth_subject: str
    email: str | None = None
