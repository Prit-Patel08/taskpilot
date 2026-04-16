from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import json
import logging
from random import uniform
from time import perf_counter
from typing import Any
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode
from sqlalchemy import column, insert, table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.rabbitmq import APPLICATION_QUEUE_NAME
from app.observability.metrics import (
    observe_stuck_job_detected,
    observe_stuck_job_recovered,
    observe_stuck_job_scan_duration,
    observe_stuck_job_skipped,
)
from app.processors.application_processor import (
    StuckApplicationRecord,
    get_stuck_processing_applications,
    mark_stuck_application_failed,
    requeue_stuck_application,
)
from app.schemas.application import ApplicationCreatedEvent

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
settings = get_settings()

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


def _log(
    event_name: str,
    *,
    request_id: str,
    application_id: str,
    event_id: str,
    last_heartbeat_at: str | None,
    retry_count: int | None = None,
    error_message: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": event_name,
        "request_id": request_id,
        "application_id": application_id,
        "event_id": event_id,
        "service": "workers",
        "layer": "recovery",
    }
    if last_heartbeat_at is not None:
        payload["last_heartbeat_at"] = last_heartbeat_at
    if retry_count is not None:
        payload["retry_count"] = retry_count
    if error_message is not None:
        payload["error_message"] = error_message
    logger.info(json.dumps(payload))


def _build_recovery_event(job: StuckApplicationRecord) -> ApplicationCreatedEvent:
    now = datetime.now(UTC)
    request_id = f"stuck-recovery-{uuid4()}"
    return ApplicationCreatedEvent(
        event_id=uuid4(),
        event_name="application.created",
        request_id=request_id,
        user_id=job.user_id,
        resource_id=job.id,
        created_at=now,
        payload={
            "application_id": str(job.id),
            "resume_id": str(job.resume_id),
            "job_listing_id": str(job.job_listing_id),
            "status": "queued",
        },
    )


def _build_recovery_headers(created_at: datetime) -> dict[str, Any]:
    trace_headers: dict[str, str] = {}
    inject(trace_headers)
    return {
        **trace_headers,
        "retry_count": 0,
        "original_timestamp": created_at.isoformat(),
    }


async def _insert_recovery_outbox_event(
    session: AsyncSession,
    *,
    event: ApplicationCreatedEvent,
    headers: dict[str, Any],
) -> None:
    payload = event.model_dump(mode="json")
    await session.execute(
        insert(outbox_events_table).values(
            id=uuid4(),
            event_name=event.event_name,
            payload=payload,
            headers=headers,
            status="pending",
            attempts=0,
            created_at=event.created_at,
            next_attempt_at=event.created_at,
            sent_at=None,
        )
    )


class StuckJobRecoveryLoop:
    def __init__(self) -> None:
        self._settings = settings
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(
            self._run_loop(),
            name="stuck-job-recovery",
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            handled_count = 0
            scan_status = "success"
            started_at = perf_counter()
            try:
                handled_count = await self._recover_stuck_jobs()
            except Exception as exc:
                scan_status = "failed"
                logger.error(
                    json.dumps(
                        {
                            "event": "stuck_job_scan_failed",
                            "service": "workers",
                            "layer": "recovery",
                            "error_message": str(exc),
                        }
                    )
                )
            finally:
                observe_stuck_job_scan_duration(
                    event_name="application.created",
                    status=scan_status,
                    queue_name=APPLICATION_QUEUE_NAME,
                    duration_seconds=perf_counter() - started_at,
                )

            try:
                sleep_seconds = (
                    self._settings.stuck_job_scan_interval_seconds
                    + uniform(0, self._settings.stuck_job_scan_jitter_seconds)
                )
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=sleep_seconds,
                )
            except TimeoutError:
                continue

    async def _recover_stuck_jobs(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(
            seconds=self._settings.application_processing_timeout_seconds
        )
        handled_count = 0
        for _ in range(self._settings.stuck_job_scan_batch_size):
            recovered = await self._recover_next_stuck_job(cutoff=cutoff)
            if not recovered:
                break
            handled_count += 1

        return handled_count

    async def _recover_next_stuck_job(self, *, cutoff: datetime) -> bool:
        async with SessionLocal() as session:
            async with session.begin():
                stuck_jobs = await get_stuck_processing_applications(
                    session,
                    updated_before=cutoff,
                    limit=1,
                )
                if not stuck_jobs:
                    return False

                job = stuck_jobs[0]
                observe_stuck_job_detected(
                    event_name="application.created",
                    status="detected",
                    queue_name=APPLICATION_QUEUE_NAME,
                )
                _log(
                    "stuck_job_detected",
                    request_id="stuck-recovery-scan",
                    application_id=str(job.id),
                    event_id="stuck-recovery-scan",
                    last_heartbeat_at=(
                        job.last_heartbeat_at.isoformat()
                        if job.last_heartbeat_at is not None
                        else None
                    ),
                    retry_count=job.retry_count,
                )

                if job.retry_count >= self._settings.application_retry_max_retries:
                    failure_reason = "stuck job exceeded recovery retry limit"
                    skipped = await mark_stuck_application_failed(
                        session,
                        application_id=job.id,
                        updated_before=cutoff,
                        failure_reason=failure_reason,
                    )
                    if skipped:
                        observe_stuck_job_skipped(
                            event_name="application.created",
                            status="retry_exhausted",
                            queue_name=APPLICATION_QUEUE_NAME,
                        )
                        _log(
                            "stuck_job_failed",
                            request_id="stuck-recovery-scan",
                            application_id=str(job.id),
                            event_id="stuck-recovery-scan",
                            last_heartbeat_at=(
                                job.last_heartbeat_at.isoformat()
                                if job.last_heartbeat_at is not None
                                else None
                            ),
                            retry_count=job.retry_count,
                            error_message=failure_reason,
                        )
                        return True
                    return False

                event = _build_recovery_event(job)
                headers = _build_recovery_headers(event.created_at)
                with tracer.start_as_current_span(
                    "application.stuck_recovery.enqueue",
                    kind=SpanKind.INTERNAL,
                ) as span:
                    span.set_attribute("application.id", str(job.id))
                    span.set_attribute("event.type", event.event_name)
                    span.set_attribute(
                        "stuck.timeout_seconds",
                        self._settings.application_processing_timeout_seconds,
                    )
                    span.set_attribute("application.retry_count", job.retry_count)
                    try:
                        requeued = await requeue_stuck_application(
                            session,
                            application_id=job.id,
                            updated_before=cutoff,
                        )
                        if not requeued:
                            return False
                        await _insert_recovery_outbox_event(
                            session,
                            event=event,
                            headers=headers,
                        )
                    except Exception as exc:
                        span.record_exception(exc)
                        span.set_status(Status(StatusCode.ERROR))
                        raise

                observe_stuck_job_recovered(
                    event_name=event.event_name,
                    status="recovered",
                    queue_name=APPLICATION_QUEUE_NAME,
                )
                _log(
                    "stuck_job_recovered",
                    request_id=event.request_id,
                    application_id=str(job.id),
                    event_id=str(event.event_id),
                    last_heartbeat_at=(
                        job.last_heartbeat_at.isoformat()
                        if job.last_heartbeat_at is not None
                        else None
                    ),
                    retry_count=job.retry_count + 1,
                )
                return True
