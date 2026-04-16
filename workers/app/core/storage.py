from __future__ import annotations

import asyncio
from functools import lru_cache
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from botocore.response import StreamingBody

from app.core.config import get_settings
from app.errors.domain_errors import ExternalServiceTimeout, FileNotFoundError


@lru_cache
def _get_s3_client():
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


def parse_s3_url(file_url: str) -> tuple[str, str]:
    parsed = urlparse(file_url)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError("resume_url must be a valid s3://bucket/key URL")
    return parsed.netloc, parsed.path.lstrip("/")


async def fetch_s3_object(file_url: str) -> bytes:
    settings = get_settings()
    bucket, key = parse_s3_url(file_url)
    client = _get_s3_client()
    try:
        response = await asyncio.to_thread(
            client.get_object,
            Bucket=bucket,
            Key=key,
        )
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", "")).strip()
        if error_code in {"NoSuchKey", "404", "NoSuchBucket"}:
            raise FileNotFoundError(f"S3 object not found for {file_url}") from exc
        raise ExternalServiceTimeout("Temporary S3 access failure") from exc
    except BotoCoreError as exc:
        raise ExternalServiceTimeout("Temporary S3 access failure") from exc

    body = response.get("Body")
    content_length = response.get("ContentLength")
    if not isinstance(body, StreamingBody):
        raise ExternalServiceTimeout("S3 object body was unavailable")
    if isinstance(content_length, int) and content_length > settings.max_upload_size_bytes:
        raise ValueError("S3 object exceeds the maximum allowed upload size")

    try:
        return await asyncio.to_thread(body.read)
    except BotoCoreError as exc:
        raise ExternalServiceTimeout("Temporary S3 read failure") from exc
