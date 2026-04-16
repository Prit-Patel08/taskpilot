from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from app.core.config import get_settings


@dataclass(frozen=True)
class PresignedUploadUrl:
    upload_url: str
    object_key: str
    public_url: str
    expires_in: int
    upload_headers: dict[str, str]


@lru_cache
def _get_s3_client() -> BaseClient:
    settings = get_settings()
    client_kwargs: dict[str, object] = {
        "service_name": "s3",
        "region_name": settings.s3_region,
    }
    if settings.aws_access_key_id:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
    if settings.aws_secret_access_key:
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.aws_session_token:
        client_kwargs["aws_session_token"] = settings.aws_session_token
    if settings.s3_endpoint_url:
        client_kwargs["endpoint_url"] = settings.s3_endpoint_url
        client_kwargs["config"] = Config(signature_version="s3v4", s3={"addressing_style": "path"})
    return boto3.client(**client_kwargs)


def _build_public_url(*, object_key: str) -> str:
    settings = get_settings()
    return f"s3://{settings.s3_bucket_name}/{object_key}"


async def generate_presigned_upload_url(
    user_id: str,
    filename: str,
    content_type: str,
    declared_size_bytes: int | None = None,
) -> PresignedUploadUrl:
    settings = get_settings()
    client = _get_s3_client()
    object_key = filename

    if declared_size_bytes is not None and declared_size_bytes > settings.max_upload_size_bytes:
        raise ValueError("Declared file size exceeds the maximum allowed upload size.")

    upload_headers = {
        "Content-Type": content_type,
        "x-amz-meta-user-id": user_id,
        "x-amz-meta-upload-type": "resume",
    }

    upload_url = await asyncio.to_thread(
        client.generate_presigned_url,
        "put_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": object_key,
            "ContentType": content_type,
            "Metadata": {
                "user-id": user_id,
                "upload-type": "resume",
            },
        },
        ExpiresIn=settings.s3_presign_expiration_seconds,
    )

    return PresignedUploadUrl(
        upload_url=upload_url,
        object_key=object_key,
        public_url=_build_public_url(object_key=object_key),
        expires_in=settings.s3_presign_expiration_seconds,
        upload_headers=upload_headers,
    )
