from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Any
from uuid import UUID

import boto3
from sqlalchemy import column, func, select, table, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.config import get_settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

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
class OutboxRecord:
    id: UUID
    event_name: str
    payload: dict[str, Any]
    headers: dict[str, Any]
    status: str
    attempts: int
    created_at: datetime
    next_attempt_at: datetime


class SQSPublisher:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._client = boto3.client(
            "sqs",
            region_name=self._settings.aws_region,
            aws_access_key_id=self._settings.aws_access_key_id,
            aws_secret_access_key=self._settings.aws_secret_access_key,
            aws_session_token=self._settings.aws_session_token,
        )
        self._queue_map = {
            "resume.process": self._settings.resume_queue_url,
            "ats.analyze": self._settings.ats_queue_url,
            "score.calculate": self._settings.scoring_queue_url,
            "apply.requested": self._settings.apply_queue_url,
            "apply.execute": self._settings.apply_queue_url,
            "tracking.update": self._settings.tracking_queue_url,
            "resume.created": self._settings.resume_queue_url,
            "application.created": self._settings.scoring_queue_url,
        }

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="sqs-outbox-publisher")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            processed = 0
            try:
                processed = await self._publish_pending_sweep()
            except Exception as exc:
                logger.error(
                    json.dumps(
                        {
                            "event": "sqs_outbox_loop_iteration_failed",
                            "service": "workers",
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

    async def _publish_pending_sweep(self) -> int:
        claimed_events = await self._claim_due_batch()
        if not claimed_events:
            return 0

        processed = 0
        for outbox_event in claimed_events:
            await self._publish_claimed_event(outbox_event)
            processed += 1
        return processed

    async def _claim_due_batch(self) -> list[OutboxRecord]:
        lease_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self._settings.outbox_processing_timeout_seconds
        )
        async with SessionLocal() as session:
            async with session.begin():
                claim_statement = (
                    select(outbox_events_table.c.id)
                    .where(
                        outbox_events_table.c.status.in_(("pending", "processing")),
                        outbox_events_table.c.attempts <= self._settings.outbox_max_attempts,
                        outbox_events_table.c.next_attempt_at <= func.now(),
                    )
                    .order_by(outbox_events_table.c.created_at)
                    .limit(self._settings.outbox_batch_size)
                    .with_for_update(skip_locked=True)
                )
                result = await session.execute(claim_statement)
                claimed_ids = list(result.scalars().all())
                if not claimed_ids:
                    return []

                await session.execute(
                    update(outbox_events_table)
                    .where(outbox_events_table.c.id.in_(claimed_ids))
                    .values(
                        status="processing",
                        next_attempt_at=lease_expires_at,
                    )
                )

                claimed_events_result = await session.execute(
                    select(
                        outbox_events_table.c.id,
                        outbox_events_table.c.event_name,
                        outbox_events_table.c.payload,
                        outbox_events_table.c.headers,
                        outbox_events_table.c.status,
                        outbox_events_table.c.attempts,
                        outbox_events_table.c.created_at,
                        outbox_events_table.c.next_attempt_at,
                    )
                    .where(outbox_events_table.c.id.in_(claimed_ids))
                    .order_by(outbox_events_table.c.created_at)
                )
                rows = claimed_events_result.all()

        return [
            OutboxRecord(
                id=row.id,
                event_name=str(row.event_name),
                payload=dict(row.payload or {}),
                headers=dict(row.headers or {}),
                status=str(row.status),
                attempts=int(row.attempts),
                created_at=row.created_at,
                next_attempt_at=row.next_attempt_at,
            )
            for row in rows
        ]

    async def _publish_claimed_event(self, outbox_event: OutboxRecord) -> None:
        queue_url = self._queue_map.get(outbox_event.event_name)
        if not queue_url:
            await self._mark_event_failed(
                outbox_event=outbox_event,
                attempts=outbox_event.attempts + 1,
            )
            logger.error(
                json.dumps(
                    {
                        "event": "sqs_outbox_event_unsupported",
                        "outbox_event_id": str(outbox_event.id),
                        "queue_event_name": outbox_event.event_name,
                        "service": "workers",
                        "layer": "outbox",
                    }
                )
            )
            return

        message_body = json.dumps(self._build_message_body(outbox_event))
        try:
            await asyncio.to_thread(
                self._client.send_message,
                QueueUrl=queue_url,
                MessageBody=message_body,
                MessageAttributes={
                    "event_name": {
                        "StringValue": outbox_event.event_name,
                        "DataType": "String",
                    }
                },
            )
        except Exception as exc:
            await self._handle_publish_failure(outbox_event, exc)
            return

        async with SessionLocal() as session:
            async with session.begin():
                await session.execute(
                    update(outbox_events_table)
                    .where(
                        outbox_events_table.c.id == outbox_event.id,
                        outbox_events_table.c.status == "processing",
                    )
                    .values(
                        status="sent",
                        sent_at=func.now(),
                    )
                )

        logger.info(
            json.dumps(
                {
                    "event": "sqs_outbox_event_published",
                    "outbox_event_id": str(outbox_event.id),
                    "queue_event_name": outbox_event.event_name,
                    "queue_url": queue_url,
                    "correlation_id": str(
                        outbox_event.payload.get("correlation_id")
                        or outbox_event.payload.get("resource_id", "unknown")
                    ),
                    "service": "workers",
                    "layer": "outbox",
                    "queue_publish_mode": "sqs",
                }
            )
        )

    async def _handle_publish_failure(
        self,
        outbox_event: OutboxRecord,
        exc: Exception,
    ) -> None:
        next_attempts = outbox_event.attempts + 1
        backoff_seconds = min(2**next_attempts, 300)
        next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)

        async with SessionLocal() as session:
            async with session.begin():
                if next_attempts > self._settings.outbox_max_attempts:
                    await self._mark_event_failed(
                        outbox_event=outbox_event,
                        attempts=next_attempts,
                        session=session,
                    )
                else:
                    await session.execute(
                        update(outbox_events_table)
                        .where(
                            outbox_events_table.c.id == outbox_event.id,
                            outbox_events_table.c.status == "processing",
                        )
                        .values(
                            status="pending",
                            attempts=next_attempts,
                            next_attempt_at=next_attempt_at,
                        )
                    )

        logger.error(
            json.dumps(
                {
                    "event": "sqs_outbox_event_publish_failed",
                    "outbox_event_id": str(outbox_event.id),
                    "queue_event_name": outbox_event.event_name,
                    "attempts": next_attempts,
                    "backoff_seconds": backoff_seconds,
                    "service": "workers",
                    "layer": "outbox",
                    "error_message": str(exc),
                }
            )
        )

    async def _mark_event_failed(
        self,
        *,
        outbox_event: OutboxRecord,
        attempts: int,
        session: Any | None = None,
    ) -> None:
        async def _apply(active_session: Any) -> None:
            await active_session.execute(
                update(outbox_events_table)
                .where(
                    outbox_events_table.c.id == outbox_event.id,
                    outbox_events_table.c.status == "processing",
                )
                .values(
                    status="failed",
                    attempts=attempts,
                    next_attempt_at=func.now(),
                )
            )

        if session is not None:
            await _apply(session)
            return

        async with SessionLocal() as local_session:
            async with local_session.begin():
                await _apply(local_session)

    def _build_message_body(self, outbox_event: OutboxRecord) -> dict[str, Any]:
        payload = dict(outbox_event.payload)
        payload["event_id"] = str(payload.get("event_id") or outbox_event.id)
        payload["event_name"] = str(payload.get("event_name") or outbox_event.event_name)
        if payload.get("correlation_id") is None and payload.get("resource_id") is not None:
            payload["correlation_id"] = str(payload["resource_id"])
        payload["retry_count"] = int(outbox_event.headers.get("retry_count", 0))
        return payload


sqs_publisher = SQSPublisher()
