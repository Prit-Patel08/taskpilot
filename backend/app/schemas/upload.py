from __future__ import annotations

from pydantic import BaseModel, Field


class UploadPresignRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    file_size_bytes: int | None = Field(default=None, gt=0)


class UploadPresignResponse(BaseModel):
    upload_url: str
    object_key: str
    file_url: str
    expires_in: int
    max_upload_size_bytes: int
    upload_headers: dict[str, str]
