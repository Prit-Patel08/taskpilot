from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.queue import publish_outbox_event
from app.models.outbox_event import OutboxEvent
from app.observability.metrics import (
    observe_outbox_failed,
    observe_outbox_published,
    set_outbox_batch_size,
    set_outbox_inflight_total,
    set_outbox_pending_total,
)
from app.repositories.outbox_repository import (
    claim_due_outbox_events,
    count_inflight_outbox_events,
    count_pending_outbox_events,
    mark_outbox_event_failed,
    mark_outbox_event_sent,
    schedule_outbox_event_retry,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass(slots=True)
class PublishResult:
    outcome: str
    attempts: int
    retry_delay_seconds: int | None = None
    error_message: str | None = None


class OutboxPublisher:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="outbox-publisher")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            processed = 0
            batch_size = 0
            try:
                processed, batch_size = await self._publish_pending_sweep()
                await self._refresh_outbox_metrics(batch_size=batch_size)
            except Exception as exc:
                logger.error(
                    json.dumps(
                        {
                            "event": "outbox_loop_iteration_failed",
                            "service": "backend",
                            "layer": "outbox",
                            "error_message": str(exc),
                        }
                    )
                )
            if processed == 0:
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._settings.outbox_poll_interval_seconds,
                    )
                except TimeoutError:
                    continue

    async def _publish_pending_sweep(self) -> tuple[int, int]:
        claimed_events = await self._claim_due_batch()
        batch_size = len(claimed_events)
        if not claimed_events:
            return 0, 0

        processed = 0
        for outbox_event in claimed_events:
            await self._publish_claimed_event(outbox_event)
            processed += 1
        return processed, batch_size

    async def _claim_due_batch(self) -> list[OutboxEvent]:
        async with SessionLocal() as session:
            async with session.begin():
                return await claim_due_outbox_events(
                    session,
                    batch_size=self._settings.outbox_batch_size,
                    max_attempts=self._settings.outbox_max_attempts,
                    processing_timeout_seconds=self._settings.outbox_processing_timeout_seconds,
                )

    async def _publish_claimed_event(self, outbox_event: OutboxEvent) -> None:
        application_id = str(outbox_event.payload.get("resource_id", "unknown"))

        with tracer.start_as_current_span(
            "outbox.event.dispatch",
            kind=SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("outbox.event_id", str(outbox_event.id))
            span.set_attribute("event.type", outbox_event.event_name)
            span.set_attribute("application.id", application_id)
            span.set_attribute("outbox.attempts", outbox_event.attempts)
            span.set_attribute("outbox.status", outbox_event.status)

            try:
                await publish_outbox_event(
                    event_name=outbox_event.event_name,
                    payload=outbox_event.payload,
                    headers=outbox_event.headers,
                )
            except Exception as exc:
                result = await self._handle_publish_failure(outbox_event, exc)
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                span.set_attribute("outbox.outcome", result.outcome)
                span.set_attribute("outbox.attempts", result.attempts)
                if result.retry_delay_seconds is not None:
                    span.set_attribute("outbox.retry_delay_seconds", result.retry_delay_seconds)
                return

            await self._mark_event_sent(outbox_event)
            span.set_attribute("outbox.outcome", "sent")

    async def _handle_publish_failure(
        self,
        outbox_event: OutboxEvent,
        exc: Exception,
    ) -> PublishResult:
        next_attempts = outbox_event.attempts + 1
        if next_attempts > self._settings.outbox_max_attempts:
            async with SessionLocal() as session:
                async with session.begin():
                    await mark_outbox_event_failed(
                        session,
                        outbox_event_id=outbox_event.id,
                        attempts=next_attempts,
                    )

            observe_outbox_failed(event_name=outbox_event.event_name)
            logger.error(
                json.dumps(
                    {
                        "event": "outbox_event_failed",
                        "outbox_event_id": str(outbox_event.id),
                        "event_name": outbox_event.event_name,
                        "application_id": str(
                            outbox_event.payload.get("resource_id", "unknown")
                        ),
                        "attempts": next_attempts,
                        "service": "backend",
                        "layer": "outbox",
                        "error_message": str(exc),
                    }
                )
            )
            return PublishResult(
                outcome="failed",
                attempts=next_attempts,
                error_message=str(exc),
            )

        retry_delay_seconds = self._compute_retry_delay_seconds(next_attempts)
        next_attempt_at = datetime.now(timezone.utc) + timedelta(
            seconds=retry_delay_seconds
        )
        async with SessionLocal() as session:
            async with session.begin():
                await schedule_outbox_event_retry(
                    session,
                    outbox_event_id=outbox_event.id,
                    attempts=next_attempts,
                    next_attempt_at=next_attempt_at,
                )

        logger.warning(
            json.dumps(
                {
                    "event": "outbox_event_retry_pending",
                    "outbox_event_id": str(outbox_event.id),
                    "event_name": outbox_event.event_name,
                    "application_id": str(outbox_event.payload.get("resource_id", "unknown")),
                    "attempts": next_attempts,
                    "next_attempt_at": next_attempt_at.isoformat(),
                    "retry_delay_seconds": retry_delay_seconds,
                    "service": "backend",
                    "layer": "outbox",
                    "error_message": str(exc),
                }
            )
        )
        return PublishResult(
            outcome="pending",
            attempts=next_attempts,
            retry_delay_seconds=retry_delay_seconds,
            error_message=str(exc),
        )

    async def _mark_event_sent(self, outbox_event: OutboxEvent) -> None:
        async with SessionLocal() as session:
            async with session.begin():
                await mark_outbox_event_sent(session, outbox_event.id)

        observe_outbox_published(event_name=outbox_event.event_name)
        logger.info(
            json.dumps(
                {
                    "event": "outbox_event_published",
                    "outbox_event_id": str(outbox_event.id),
                    "event_name": outbox_event.event_name,
                    "application_id": str(outbox_event.payload.get("resource_id", "unknown")),
                    "service": "backend",
                    "layer": "outbox",
                }
            )
        )

    async def _refresh_outbox_metrics(self, *, batch_size: int) -> None:
        async with SessionLocal() as session:
            pending_total = await count_pending_outbox_events(session)
            inflight_total = await count_inflight_outbox_events(session)
        set_outbox_pending_total(pending_total)
        set_outbox_inflight_total(inflight_total)
        set_outbox_batch_size(batch_size)

    def _compute_retry_delay_seconds(self, attempts: int) -> int:
        exponent = max(attempts - 1, 0)
        return self._settings.outbox_retry_base_delay_seconds * (2**exponent)


outbox_publisher = OutboxPublisher()
