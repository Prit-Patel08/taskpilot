from __future__ import annotations

from dataclasses import dataclass
import os
import re
import unicodedata
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.storage import generate_presigned_upload_url

ALLOWED_UPLOAD_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
FILENAME_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
settings = get_settings()


@dataclass(frozen=True)
class UploadPresignResult:
    upload_url: str
    object_key: str
    file_url: str
    expires_in: int
    max_upload_size_bytes: int
    upload_headers: dict[str, str]


def _sanitize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKD", filename).strip()
    if "/" in normalized or "\\" in normalized:
        raise ValueError("Filename must not contain path separators.")
    basename = os.path.basename(normalized)
    sanitized = FILENAME_SANITIZE_PATTERN.sub("-", basename).strip(".-")
    return sanitized or "resume"


def _validate_filename_and_content_type(*, filename: str, content_type: str) -> tuple[str, str]:
    sanitized_filename = _sanitize_filename(filename)
    _, extension = os.path.splitext(sanitized_filename)
    normalized_extension = extension.lower()
    if normalized_extension not in ALLOWED_UPLOAD_TYPES:
        raise ValueError("Unsupported file type. Only PDF and DOCX are allowed.")

    normalized_content_type = content_type.strip().lower()
    expected_content_type = ALLOWED_UPLOAD_TYPES[normalized_extension]
    if normalized_content_type != expected_content_type:
        raise ValueError("Content type must exactly match the filename extension.")

    return sanitized_filename, expected_content_type


def _validate_declared_size(file_size_bytes: int | None) -> int | None:
    if file_size_bytes is None:
        return None
    if file_size_bytes <= 0:
        raise ValueError("Declared file size must be greater than zero.")
    if file_size_bytes > settings.max_upload_size_bytes:
        raise ValueError("Declared file size exceeds the maximum allowed upload size.")
    return file_size_bytes


def _build_object_key(*, user_id: UUID, filename: str) -> str:
    return f"resumes/{user_id}/{uuid4()}-{filename}"


async def generate_upload_presign(
    *,
    user_id: UUID,
    filename: str,
    content_type: str,
    file_size_bytes: int | None = None,
) -> UploadPresignResult:
    validated_filename, normalized_content_type = _validate_filename_and_content_type(
        filename=filename,
        content_type=content_type,
    )
    validated_file_size = _validate_declared_size(file_size_bytes)
    object_key = _build_object_key(
        user_id=user_id,
        filename=validated_filename,
    )
    presigned = await generate_presigned_upload_url(
        str(user_id),
        object_key,
        normalized_content_type,
        declared_size_bytes=validated_file_size,
    )
    return UploadPresignResult(
        upload_url=presigned.upload_url,
        object_key=presigned.object_key,
        file_url=presigned.public_url,
        expires_in=presigned.expires_in,
        max_upload_size_bytes=settings.max_upload_size_bytes,
        upload_headers=presigned.upload_headers,
    )
