from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.storage import fetch_s3_object
from app.repositories.resume_processing_repository import (
    enqueue_ats_analyze_event,
    get_locked_resume,
    insert_resume_extraction,
    resume_extraction_exists,
)
from app.schemas.ats import AtsAnalyzeEvent
from app.schemas.resume import ResumeCreatedEvent
from app.services.resume_parser import parse_resume
from app.services.resume_text_extractor import extract_text

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass(frozen=True)
class ResumeProcessingResult:
    skipped: bool
    status: str
    skip_reason: str | None = None


def _log(
    event_name: str,
    *,
    queue_event_name: str,
    resume_id: str,
    attempt: int,
    request_id: str,
    event_id: str,
    skip_reason: str | None = None,
    error_message: str | None = None,
) -> None:
    payload: dict[str, str | int] = {
        "event": event_name,
        "queue_event_name": queue_event_name,
        "resume_id": resume_id,
        "attempt": attempt,
        "request_id": request_id,
        "event_id": event_id,
        "service": "workers",
        "layer": "processor",
    }
    if skip_reason is not None:
        payload["skip_reason"] = skip_reason
    if error_message is not None:
        payload["error_message"] = error_message
    logger.info(json.dumps(payload))


def _build_ats_headers(*, created_at: datetime) -> dict[str, str | int]:
    return {
        "retry_count": 0,
        "original_timestamp": created_at.isoformat(),
    }


def _build_s3_url(*, file_key: str) -> str:
    normalized_key = file_key.strip().lstrip("/")
    return f"s3://{settings.s3_bucket_name}/{normalized_key}"


async def _load_and_validate_resume(
    *,
    resume_id: UUID,
    resume_id_str: str,
    queue_event_name: str,
    attempt: int,
    request_id: str,
    event_id: str,
) -> str | ResumeProcessingResult:
    async with SessionLocal() as session:
        async with session.begin():
            resume = await get_locked_resume(
                session,
                resume_id=resume_id,
            )
            if resume is None:
                raise ValueError("resume not found")
            if await resume_extraction_exists(session, resume_id=resume.id):
                _log(
                    "resume_processing_completed",
                    queue_event_name=queue_event_name,
                    resume_id=resume_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="already_extracted",
                )
                return ResumeProcessingResult(
                    skipped=True,
                    status="already_extracted",
                    skip_reason="already_extracted",
                )

            _log(
                "resume_processing_started",
                queue_event_name=queue_event_name,
                resume_id=resume_id_str,
                attempt=attempt,
                request_id=request_id,
                event_id=event_id,
            )
            return resume.file_key


async def _extract_and_parse_resume(*, file_key: str) -> dict[str, Any]:
    file_bytes = await fetch_s3_object(_build_s3_url(file_key=file_key))
    extracted_text = await asyncio.to_thread(extract_text, file_bytes)
    return await asyncio.to_thread(parse_resume, extracted_text)


async def _store_extraction_and_enqueue_ats(
    *,
    event: ResumeCreatedEvent,
    parsed_resume: dict[str, Any],
) -> bool:
    ats_event = AtsAnalyzeEvent(
        request_id=event.request_id,
        user_id=event.user_id,
        resource_id=event.resource_id,
        payload={
            "resume_id": str(event.resource_id),
        },
    )

    async with SessionLocal() as session:
        async with session.begin():
            resume = await get_locked_resume(
                session,
                resume_id=event.resource_id,
            )
            if resume is None:
                raise ValueError("resume not found")
            if await resume_extraction_exists(session, resume_id=event.resource_id):
                return False

            await insert_resume_extraction(
                session,
                resume_id=event.resource_id,
                parsed_json=parsed_resume,
                created_at=ats_event.created_at,
            )
            await enqueue_ats_analyze_event(
                session,
                payload=ats_event.model_dump(mode="json"),
                headers=_build_ats_headers(created_at=ats_event.created_at),
                created_at=ats_event.created_at,
            )
            return True


async def process_resume_event(
    event: ResumeCreatedEvent,
    *,
    attempt: int,
) -> ResumeProcessingResult:
    resume_id = event.resource_id
    resume_id_str = str(resume_id)
    request_id = event.request_id
    event_id = str(event.event_id)
    queue_event_name = event.event_name

    loaded_resume = await _load_and_validate_resume(
        resume_id=resume_id,
        resume_id_str=resume_id_str,
        queue_event_name=queue_event_name,
        attempt=attempt,
        request_id=request_id,
        event_id=event_id,
    )
    if isinstance(loaded_resume, ResumeProcessingResult):
        return loaded_resume

    try:
        parsed_resume = await _extract_and_parse_resume(file_key=loaded_resume)
    except Exception as exc:
        _log(
            "resume_processing_failed",
            queue_event_name=queue_event_name,
            resume_id=resume_id_str,
            attempt=attempt,
            request_id=request_id,
            event_id=event_id,
            error_message=str(exc),
        )
        raise

    stored = await _store_extraction_and_enqueue_ats(
        event=event,
        parsed_resume=parsed_resume,
    )
    if not stored:
        _log(
            "resume_processing_completed",
            queue_event_name=queue_event_name,
            resume_id=resume_id_str,
            attempt=attempt,
            request_id=request_id,
            event_id=event_id,
            skip_reason="already_extracted",
        )
        return ResumeProcessingResult(
            skipped=True,
            status="already_extracted",
            skip_reason="already_extracted",
        )

    _log(
        "resume_processing_completed",
        queue_event_name=queue_event_name,
        resume_id=resume_id_str,
        attempt=attempt,
        request_id=request_id,
        event_id=event_id,
    )
    return ResumeProcessingResult(
        skipped=False,
        status="parsed",
    )
