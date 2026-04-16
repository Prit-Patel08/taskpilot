from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
from time import perf_counter
from typing import Any

import boto3

from app.core.config import get_settings
from app.observability.metrics import (
    observe_worker_job_failure,
    observe_worker_job_outcome,
    observe_worker_retry_exhausted,
)
from app.processors.application_processor import (
    mark_application_failed_for_event,
    process_application_created,
)
from app.processors.resume_processor import process_resume_event
from app.processors.scoring_processor import process_scoring_event
from app.retries import classify_exception
from app.schemas.application import ApplicationCreatedEvent
from app.schemas.resume import ResumeCreatedEvent
from app.schemas.score import ScoreCalculateEvent

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass(frozen=True)
class SQSMessage:
    queue_url: str
    queue_name: str
    message_id: str
    receipt_handle: str
    body: dict[str, Any]
    receive_count: int


class SQSConsumer:
    def __init__(self) -> None:
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._client = boto3.client(
            "sqs",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
        )
        self._queue_map = {
            "resume": settings.resume_queue_url,
            "ats": settings.ats_queue_url,
            "scoring": settings.scoring_queue_url,
            "apply": settings.apply_queue_url,
            "tracking": settings.tracking_queue_url,
        }

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="sqs-consumer")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            idle = True
            for queue_name, queue_url in self._queue_map.items():
                if self._stop_event.is_set():
                    return
                messages = await self._receive_messages(queue_name=queue_name, queue_url=queue_url)
                if not messages:
                    continue
                idle = False
                for message in messages:
                    if self._stop_event.is_set():
                        return
                    await self._process_message(message)
            if idle:
                await asyncio.sleep(0)

    async def _receive_messages(self, *, queue_name: str, queue_url: str) -> list[SQSMessage]:
        response = await asyncio.to_thread(
            self._client.receive_message,
            QueueUrl=queue_url,
            MaxNumberOfMessages=settings.sqs_max_number_of_messages,
            WaitTimeSeconds=settings.sqs_wait_time_seconds,
            VisibilityTimeout=settings.sqs_visibility_timeout_seconds,
            AttributeNames=["ApproximateReceiveCount"],
            MessageAttributeNames=["All"],
        )
        raw_messages = response.get("Messages", [])
        parsed_messages: list[SQSMessage] = []
        for raw_message in raw_messages:
            try:
                payload = json.loads(raw_message["Body"])
            except (KeyError, json.JSONDecodeError) as exc:
                logger.error(
                    json.dumps(
                        {
                            "event": "sqs_message_decode_failed",
                            "service": "workers",
                            "layer": "consumer",
                            "queue_name": queue_name,
                            "message_id": raw_message.get("MessageId", "unknown"),
                            "error_message": str(exc),
                        }
                    )
                )
                continue

            receive_count_raw = raw_message.get("Attributes", {}).get(
                "ApproximateReceiveCount",
                "1",
            )
            try:
                receive_count = max(int(receive_count_raw), 1)
            except ValueError:
                receive_count = 1

            parsed_messages.append(
                SQSMessage(
                    queue_url=queue_url,
                    queue_name=queue_name,
                    message_id=raw_message["MessageId"],
                    receipt_handle=raw_message["ReceiptHandle"],
                    body=payload,
                    receive_count=receive_count,
                )
            )
        return parsed_messages

    async def _process_message(self, message: SQSMessage) -> None:
        event_name = str(message.body.get("event_name", "unknown"))
        resource_id = str(message.body.get("resource_id", "unknown"))
        request_id = str(message.body.get("request_id", "unknown"))
        event_id = str(message.body.get("event_id", message.message_id))
        attempt = message.receive_count
        started_at = perf_counter()
        visibility_task = asyncio.create_task(
            self._extend_visibility_until_done(
                queue_url=message.queue_url,
                receipt_handle=message.receipt_handle,
            ),
            name=f"sqs-visibility-{message.message_id}",
        )

        try:
            await asyncio.wait_for(
                self._dispatch_event(event_name=event_name, payload=message.body, attempt=attempt),
                timeout=settings.application_processing_timeout_seconds,
            )
            observe_worker_job_outcome(
                event_name=event_name,
                status="success",
                queue_name=message.queue_name,
                duration_seconds=perf_counter() - started_at,
            )
            await self._delete_message(
                queue_url=message.queue_url,
                receipt_handle=message.receipt_handle,
            )
        except Exception as exc:
            classification = classify_exception(exc)
            duration_seconds = perf_counter() - started_at
            logger.error(
                json.dumps(
                    {
                        "event": "sqs_message_processing_failed",
                        "service": "workers",
                        "layer": "consumer",
                        "queue_name": message.queue_name,
                        "message_id": message.message_id,
                        "queue_event_name": event_name,
                        "request_id": request_id,
                        "resource_id": resource_id,
                        "event_id": event_id,
                        "attempt": attempt,
                        "retryable": classification.retryable,
                        "error_code": classification.error_code,
                        "error_message": classification.error_message_short,
                    }
                )
            )
            observe_worker_job_outcome(
                event_name=event_name,
                status="failed",
                queue_name=message.queue_name,
                duration_seconds=duration_seconds,
            )
            observe_worker_job_failure(
                event_name=event_name,
                status="failed",
                queue_name=message.queue_name,
            )
            if not classification.retryable:
                if event_name in {"application.created", "score.calculate"} and resource_id != "unknown":
                    await mark_application_failed_for_event(
                        application_id=resource_id,
                        request_id=request_id,
                        event_id=event_id,
                        attempt=attempt,
                        failure_reason=classification.error_message_short,
                    )
                if message.receive_count >= settings.application_retry_max_retries:
                    observe_worker_retry_exhausted(
                        event_name=event_name,
                        status="exhausted",
                        queue_name=message.queue_name,
                    )
            else:
                if message.receive_count >= settings.application_retry_max_retries:
                    observe_worker_retry_exhausted(
                        event_name=event_name,
                        status="exhausted",
                        queue_name=message.queue_name,
                    )
        finally:
            visibility_task.cancel()
            await asyncio.gather(visibility_task, return_exceptions=True)

    async def _dispatch_event(
        self,
        *,
        event_name: str,
        payload: dict[str, Any],
        attempt: int,
    ) -> None:
        if event_name == "application.created":
            await process_application_created(
                ApplicationCreatedEvent.model_validate(payload),
                attempt=attempt,
            )
            return
        if event_name in {"resume.created", "resume.process"}:
            await process_resume_event(
                ResumeCreatedEvent.model_validate(payload),
                attempt=attempt,
            )
            return
        if event_name == "score.calculate":
            await process_scoring_event(
                ScoreCalculateEvent.model_validate(payload),
                attempt=attempt,
            )
            return
        raise ValueError(f"Unsupported SQS event: {event_name}")

    async def _extend_visibility_until_done(
        self,
        *,
        queue_url: str,
        receipt_handle: str,
    ) -> None:
        refresh_interval = max(settings.sqs_visibility_timeout_seconds // 2, 5)
        while True:
            await asyncio.sleep(refresh_interval)
            await asyncio.to_thread(
                self._client.change_message_visibility,
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=settings.sqs_visibility_timeout_seconds,
            )

    async def _delete_message(
        self,
        *,
        queue_url: str,
        receipt_handle: str,
    ) -> None:
        await asyncio.to_thread(
            self._client.delete_message,
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle,
        )
