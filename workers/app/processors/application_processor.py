from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
import json
import logging
from uuid import UUID, uuid4

from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode
from sqlalchemy import column, func, insert, select, table, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.errors import ResumeExtractionPending
from app.schemas.application import ApplicationCreatedEvent
from app.schemas.score import ScoreCalculateEvent

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
MAX_FAILURE_REASON_LENGTH = 512
applications_table = table(
    "applications",
    column("id", PGUUID(as_uuid=True)),
    column("user_id"),
    column("status"),
    column("resume_id", PGUUID(as_uuid=True)),
    column("job_listing_id", PGUUID(as_uuid=True)),
    column("retry_count"),
    column("failure_reason"),
    column("created_at"),
    column("updated_at"),
    column("processed_at"),
    column("processing_started_at"),
    column("last_heartbeat_at"),
)
resume_extractions_table = table(
    "resume_extractions",
    column("id", PGUUID(as_uuid=True)),
    column("resume_id", PGUUID(as_uuid=True)),
    column("parsed_json", JSONB),
    column("created_at"),
)
outbox_events_table = table(
    "outbox_events",
    column("id", PGUUID(as_uuid=True)),
    column("event_name"),
    column("payload", JSONB),
    column("headers", JSONB),
    column("status"),
    column("attempts"),
    column("created_at"),
    column("next_attempt_at"),
    column("sent_at"),
)


@dataclass(frozen=True)
class ApplicationProcessingResult:
    skipped: bool
    status: str
    skip_reason: str | None = None


@dataclass(frozen=True)
class StatusTransitionResult:
    applied: bool
    current_status: str | None


@dataclass(frozen=True)
class StuckApplicationRecord:
    id: UUID
    user_id: str
    resume_id: UUID
    job_listing_id: UUID
    retry_count: int
    created_at: datetime
    last_heartbeat_at: datetime | None


def _log(
    event_name: str,
    *,
    request_id: str,
    application_id: str,
    event_id: str,
    attempt: int,
    failure_reason: str | None = None,
    skip_reason: str | None = None,
    current_status: str | None = None,
) -> None:
    payload = {
        "event": event_name,
        "request_id": request_id,
        "application_id": application_id,
        "event_id": event_id,
        "attempt": attempt,
        "service": "workers",
        "layer": "processor",
    }
    if failure_reason is not None:
        payload["failure_reason"] = failure_reason
    if skip_reason is not None:
        payload["skip_reason"] = skip_reason
    if current_status is not None:
        payload["current_status"] = current_status
    logger.info(json.dumps(payload))


def _normalize_failure_reason(failure_reason: str) -> str:
    normalized = failure_reason.strip() or "unknown failure"
    if len(normalized) <= MAX_FAILURE_REASON_LENGTH:
        return normalized
    return normalized[: MAX_FAILURE_REASON_LENGTH - 3] + "..."


def _build_skip_result(
    *,
    request_id: str,
    application_id: str,
    event_id: str,
    attempt: int,
    current_status: str,
    skip_reason: str,
) -> ApplicationProcessingResult:
    current_span = trace.get_current_span()
    current_span.set_attribute("idempotent.skip", True)
    current_span.set_attribute("idempotent.skip_reason", skip_reason)
    current_span.set_attribute("application.current_status", current_status)

    _log(
        "job_idempotent_skipped",
        request_id=request_id,
        application_id=application_id,
        event_id=event_id,
        attempt=attempt,
        skip_reason=skip_reason,
        current_status=current_status,
    )
    return ApplicationProcessingResult(
        skipped=True,
        status=current_status,
        skip_reason=skip_reason,
    )


async def _get_application_status(
    session: AsyncSession,
    application_id: UUID,
) -> str | None:
    result = await session.execute(
        select(applications_table.c.status).where(applications_table.c.id == application_id)
    )
    return result.scalar_one_or_none()


async def _resume_extraction_exists(
    session: AsyncSession,
    *,
    resume_id: UUID,
) -> bool:
    result = await session.execute(
        select(resume_extractions_table.c.id)
        .where(resume_extractions_table.c.resume_id == resume_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_stuck_processing_applications(
    session: AsyncSession,
    *,
    updated_before: datetime,
    limit: int,
) -> list[StuckApplicationRecord]:
    result = await session.execute(
        select(
            applications_table.c.id,
            applications_table.c.user_id,
            applications_table.c.resume_id,
            applications_table.c.job_listing_id,
            applications_table.c.retry_count,
            applications_table.c.created_at,
            applications_table.c.last_heartbeat_at,
        )
        .where(
            applications_table.c.status == "processing",
            applications_table.c.last_heartbeat_at < updated_before,
        )
        .order_by(applications_table.c.last_heartbeat_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return [
        StuckApplicationRecord(
            id=row.id,
            user_id=row.user_id,
            resume_id=row.resume_id,
            job_listing_id=row.job_listing_id,
            retry_count=row.retry_count,
            created_at=row.created_at,
            last_heartbeat_at=row.last_heartbeat_at,
        )
        for row in result.all()
    ]


async def _transition_status(
    session: AsyncSession,
    *,
    application_id: UUID,
    expected_status: str,
    next_status: str,
    clear_processing_fields: bool = False,
    start_processing_fields: bool = False,
) -> StatusTransitionResult:
    values: dict[str, object] = {
        "status": next_status,
        "updated_at": func.now(),
    }
    if start_processing_fields:
        values["processing_started_at"] = func.now()
        values["last_heartbeat_at"] = func.now()
    if clear_processing_fields:
        values["processing_started_at"] = None
        values["last_heartbeat_at"] = None

    result = await session.execute(
        update(applications_table)
        .where(
            applications_table.c.id == application_id,
            applications_table.c.status == expected_status,
        )
        .values(**values)
    )
    if result.rowcount and result.rowcount > 0:
        return StatusTransitionResult(applied=True, current_status=next_status)
    return StatusTransitionResult(
        applied=False,
        current_status=await _get_application_status(session, application_id),
    )


async def requeue_stuck_application(
    session: AsyncSession,
    *,
    application_id: UUID,
    updated_before: datetime,
) -> bool:
    result = await session.execute(
        update(applications_table)
        .where(
            applications_table.c.id == application_id,
            applications_table.c.status == "processing",
            applications_table.c.last_heartbeat_at < updated_before,
        )
        .values(
            status="queued",
            retry_count=applications_table.c.retry_count + 1,
            updated_at=func.now(),
            processing_started_at=None,
            last_heartbeat_at=None,
        )
    )
    return bool(result.rowcount and result.rowcount > 0)


async def mark_stuck_application_failed(
    session: AsyncSession,
    *,
    application_id: UUID,
    updated_before: datetime,
    failure_reason: str,
) -> bool:
    result = await session.execute(
        update(applications_table)
        .where(
            applications_table.c.id == application_id,
            applications_table.c.status == "processing",
            applications_table.c.last_heartbeat_at < updated_before,
        )
        .values(
            status="failed",
            failure_reason=_normalize_failure_reason(failure_reason),
            updated_at=func.now(),
            processing_started_at=None,
            last_heartbeat_at=None,
        )
    )
    return bool(result.rowcount and result.rowcount > 0)


async def mark_application_failed(
    session: AsyncSession,
    application_id: UUID,
    failure_reason: str,
) -> str | None:
    result = await session.execute(
        update(applications_table)
        .where(
            applications_table.c.id == application_id,
            applications_table.c.status.not_in(("completed", "resume_processed")),
        )
        .values(
            status="failed",
            failure_reason=_normalize_failure_reason(failure_reason),
            updated_at=func.now(),
            processed_at=None,
            processing_started_at=None,
            last_heartbeat_at=None,
        )
    )
    if result.rowcount and result.rowcount > 0:
        return "failed"
    return await _get_application_status(session, application_id)


def _build_score_headers(*, created_at: datetime) -> dict[str, str | int]:
    trace_headers: dict[str, str] = {}
    inject(trace_headers)
    return {
        **trace_headers,
        "retry_count": 0,
        "original_timestamp": created_at.isoformat(),
    }


async def _enqueue_scoring(
    session: AsyncSession,
    *,
    event: ScoreCalculateEvent,
) -> None:
    payload = event.model_dump(mode="json")
    await session.execute(
        insert(outbox_events_table).values(
            id=uuid4(),
            event_name=event.event_name,
            payload=payload,
            headers=_build_score_headers(created_at=event.created_at),
            status="pending",
            attempts=0,
            created_at=event.created_at,
            next_attempt_at=event.created_at,
            sent_at=None,
        )
    )


async def mark_application_failed_for_event(
    *,
    application_id: str,
    request_id: str,
    event_id: str,
    attempt: int,
    failure_reason: str,
) -> None:
    normalized_reason = _normalize_failure_reason(failure_reason)
    application_uuid = UUID(application_id)

    with tracer.start_as_current_span(
        "application.db.mark_failed",
        kind=SpanKind.INTERNAL,
    ) as span:
        span.set_attribute("application.id", application_id)
        span.set_attribute("application.failure_reason", normalized_reason)
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("status.transition", "not-completed->failed")
        try:
            async with SessionLocal() as session:
                async with session.begin():
                    current_status = await mark_application_failed(
                        session,
                        application_uuid,
                        normalized_reason,
                    )
                    if current_status is None:
                        raise ValueError("application not found")
                    if current_status == "completed":
                        return
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR))
            raise

    _log(
        "job_marked_failed",
        request_id=request_id,
        application_id=application_id,
        event_id=event_id,
        attempt=attempt,
        failure_reason=normalized_reason,
    )


async def process_application_created(
    event: ApplicationCreatedEvent,
    *,
    attempt: int,
) -> ApplicationProcessingResult:
    request_id = event.request_id
    event_id = str(event.event_id)
    application_id = event.resource_id
    application_id_str = str(application_id)

    async with SessionLocal() as session:
        with tracer.start_as_current_span(
            "application.db.transition_to_scoring_ready",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("application.id", application_id_str)
            span.set_attribute("db.system", "postgresql")
            span.set_attribute("status.transition", "queued->resume_processed")
            try:
                async with session.begin():
                    result = await session.execute(
                        select(
                            applications_table.c.status,
                            applications_table.c.resume_id,
                            applications_table.c.job_listing_id,
                        )
                        .where(applications_table.c.id == application_id)
                        .with_for_update()
                    )
                    row = result.one_or_none()
                    if row is None:
                        raise ValueError("application not found")

                    current_status = str(row.status)
                    if current_status in {"completed", "resume_processed"}:
                        return _build_skip_result(
                            request_id=request_id,
                            application_id=application_id_str,
                            event_id=event_id,
                            attempt=attempt,
                            current_status=current_status,
                            skip_reason="already_processed",
                        )
                    if current_status == "failed":
                        return _build_skip_result(
                            request_id=request_id,
                            application_id=application_id_str,
                            event_id=event_id,
                            attempt=attempt,
                            current_status=current_status,
                            skip_reason="already_failed",
                        )
                    if current_status == "processing":
                        return _build_skip_result(
                            request_id=request_id,
                            application_id=application_id_str,
                            event_id=event_id,
                            attempt=attempt,
                            current_status=current_status,
                            skip_reason="already_processing",
                        )
                    if current_status != "queued":
                        return _build_skip_result(
                            request_id=request_id,
                            application_id=application_id_str,
                            event_id=event_id,
                            attempt=attempt,
                            current_status=current_status,
                            skip_reason="unexpected_status",
                        )

                    if not await _resume_extraction_exists(
                        session,
                        resume_id=row.resume_id,
                    ):
                        raise ResumeExtractionPending(
                            "Resume extraction is not ready for this application"
                        )

                    transition_result = await _transition_status(
                        session,
                        application_id=application_id,
                        expected_status="queued",
                        next_status="resume_processed",
                        clear_processing_fields=True,
                    )
                    if not transition_result.applied:
                        return _build_skip_result(
                            request_id=request_id,
                            application_id=application_id_str,
                            event_id=event_id,
                            attempt=attempt,
                            current_status=transition_result.current_status or "unknown",
                            skip_reason="transition_conflict",
                        )

                    score_event = ScoreCalculateEvent(
                        request_id=request_id,
                        user_id=event.user_id,
                        resource_id=application_id,
                        payload={
                            "application_id": application_id_str,
                            "resume_id": str(row.resume_id),
                            "job_listing_id": str(row.job_listing_id),
                        },
                    )
                    await _enqueue_scoring(
                        session,
                        event=score_event,
                    )
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise

    _log(
        "job_completed",
        request_id=request_id,
        application_id=application_id_str,
        event_id=event_id,
        attempt=attempt,
    )
    return ApplicationProcessingResult(skipped=False, status="resume_processed")
