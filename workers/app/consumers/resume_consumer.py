from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
import logging
from time import perf_counter
from typing import Any
from uuid import UUID

from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractRobustChannel,
    AbstractRobustConnection,
    AbstractRobustQueue,
)
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.propagate import inject
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode

from app.core.config import get_settings
from app.core.rabbitmq import (
    RESUME_QUEUE_NAME,
    RESUME_RETRY_ROUTING_KEY_PREFIX,
    create_resume_channel,
    get_retry_delay_seconds,
    get_retry_routing_key,
    publish_with_headers,
)
from app.observability.metrics import (
    observe_worker_job_failure,
    observe_worker_job_outcome,
    observe_worker_retry_attempt,
    observe_worker_retry_exhausted,
)
from app.processors.application_processor import mark_application_failed_for_event
from app.processors.resume_processor import process_resume_event
from app.retries import RetryClassification, classify_exception, sanitize_retry_count
from app.schemas.resume import ResumeCreatedEvent

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
MAX_PROCESSING_SECONDS = 30
settings = get_settings()
MAX_RETRIES = settings.application_retry_max_retries
BASE_RETRY_DELAY_SECONDS = settings.application_retry_base_delay_seconds


def _log(
    event_name: str,
    *,
    request_id: str,
    application_id: str,
    event_id: str,
    attempt: int,
    error_message: str | None = None,
    retry_count: int | None = None,
    retry_max: int | None = None,
    retry_delay_seconds: int | None = None,
    retry_reason: str | None = None,
    retry_classification: str | None = None,
    retry_error_code: str | None = None,
    retry_error_type: str | None = None,
    retry_error_message_short: str | None = None,
    retry_error_fingerprint: str | None = None,
    retry_header_corrupted: bool | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": event_name,
        "request_id": request_id,
        "application_id": application_id,
        "event_id": event_id,
        "attempt": attempt,
        "service": "workers",
        "layer": "consumer",
    }
    if error_message is not None:
        payload["error_message"] = error_message
    if retry_count is not None:
        payload["retry_count"] = retry_count
    if retry_max is not None:
        payload["retry_max"] = retry_max
    if retry_delay_seconds is not None:
        payload["retry_delay_seconds"] = retry_delay_seconds
    if retry_reason is not None:
        payload["retry_reason"] = retry_reason
    if retry_classification is not None:
        payload["retry_classification"] = retry_classification
    if retry_error_code is not None:
        payload["retry_error_code"] = retry_error_code
    if retry_error_type is not None:
        payload["retry_error_type"] = retry_error_type
    if retry_error_message_short is not None:
        payload["retry_error_message_short"] = retry_error_message_short
    if retry_error_fingerprint is not None:
        payload["retry_error_fingerprint"] = retry_error_fingerprint
    if retry_header_corrupted is not None:
        payload["retry_header_corrupted"] = retry_header_corrupted

    logger.info(json.dumps(payload))


def _apply_retry_metadata_to_span(
    span: Any,
    *,
    classification: RetryClassification,
    retry_header_corrupted: bool,
) -> None:
    span.set_attribute("retry.reason", classification.reason)
    span.set_attribute("retry.classification", classification.classification)
    span.set_attribute("retry.error_code", classification.error_code)
    span.set_attribute("retry.error_type", classification.error_type)
    span.set_attribute("retry.error_message_short", classification.error_message_short)
    span.set_attribute("retry.error_fingerprint", classification.error_fingerprint)
    span.set_attribute("retry.retryable", classification.retryable)
    span.set_attribute("retry.header_corrupted", retry_header_corrupted)


def _extract_retry_count(message: AbstractIncomingMessage) -> tuple[int, bool]:
    headers = message.headers or {}
    for key in ("retry_count", "x-retry-count", "retry-count"):
        if key in headers:
            return sanitize_retry_count(headers.get(key), max_retries=MAX_RETRIES)
    return 0, False


def _decode_message_body(message: AbstractIncomingMessage) -> dict[str, Any]:
    payload = json.loads(message.body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("event body must be a JSON object")
    return payload


def _build_trace_headers(message: AbstractIncomingMessage) -> dict[str, str]:
    normalized_headers: dict[str, str] = {}
    for key, value in (message.headers or {}).items():
        normalized_key = str(key)
        if isinstance(value, bytes):
            normalized_headers[normalized_key] = value.decode("utf-8", errors="ignore")
        else:
            normalized_headers[normalized_key] = str(value)
    return normalized_headers


def _build_retry_headers(
    *,
    message: AbstractIncomingMessage,
    next_retry_count: int,
) -> dict[str, Any]:
    trace_headers: dict[str, str] = {}
    inject(trace_headers)
    original_timestamp = (message.headers or {}).get("original_timestamp")
    if isinstance(original_timestamp, bytes):
        original_timestamp = original_timestamp.decode("utf-8", errors="ignore")
    if not isinstance(original_timestamp, str) or not original_timestamp.strip():
        original_timestamp = datetime.now(UTC).isoformat()
    return {
        **trace_headers,
        "retry_count": next_retry_count,
        "original_timestamp": original_timestamp,
    }


def _is_valid_application_id(application_id: str) -> bool:
    try:
        UUID(application_id)
    except ValueError:
        return False
    return True


async def _send_to_dlq(
    message: AbstractIncomingMessage,
    *,
    metric_event_name: str,
    request_id: str,
    application_id: str,
    event_id: str,
    attempt: int,
    retry_count: int,
    duration_seconds: float,
    classification: RetryClassification,
    retry_header_corrupted: bool,
    retry_exhausted: bool,
) -> None:
    _log(
        "job_sent_to_dlq",
        request_id=request_id,
        application_id=application_id,
        event_id=event_id,
        attempt=attempt,
        error_message=classification.error_message_short,
        retry_count=retry_count,
        retry_max=MAX_RETRIES,
        retry_reason=classification.reason,
        retry_classification=classification.classification,
        retry_error_code=classification.error_code,
        retry_error_type=classification.error_type,
        retry_error_message_short=classification.error_message_short,
        retry_error_fingerprint=classification.error_fingerprint,
        retry_header_corrupted=retry_header_corrupted,
    )
    observe_worker_job_outcome(
        event_name=metric_event_name,
        status="dlq",
        queue_name=RESUME_QUEUE_NAME,
        duration_seconds=duration_seconds,
    )
    observe_worker_job_failure(
        event_name=metric_event_name,
        status="dlq",
        queue_name=RESUME_QUEUE_NAME,
    )
    if retry_exhausted:
        observe_worker_retry_exhausted(
            event_name=metric_event_name,
            status="exhausted",
            queue_name=RESUME_QUEUE_NAME,
        )
    await message.nack(requeue=False)


class ResumeConsumer:
    def __init__(self) -> None:
        self._channel: AbstractRobustChannel | None = None
        self._queue: AbstractRobustQueue | None = None
        self._exchange: Any | None = None
        self._consumer_tag: str | None = None
        self._inflight_tasks: set[asyncio.Task[Any]] = set()

    async def start(self, connection: AbstractRobustConnection) -> None:
        self._channel, self._queue, self._exchange = await create_resume_channel(connection)
        self._consumer_tag = await self._queue.consume(self._handle_message)

    async def stop(self) -> None:
        if self._queue is not None and self._consumer_tag is not None:
            await self._queue.cancel(self._consumer_tag)
            self._consumer_tag = None
        pending_tasks = [
            task
            for task in self._inflight_tasks
            if task is not asyncio.current_task()
        ]
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()
        self._exchange = None

    async def _schedule_retry(
        self,
        *,
        message: AbstractIncomingMessage,
        metric_event_name: str,
        request_id: str,
        application_id: str,
        event_id: str,
        attempt: int,
        retry_count: int,
        duration_seconds: float,
        classification: RetryClassification,
        retry_header_corrupted: bool,
    ) -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitMQ exchange is not initialized")

        next_retry_count = retry_count + 1
        retry_delay_seconds = get_retry_delay_seconds(
            base_delay_seconds=BASE_RETRY_DELAY_SECONDS,
            retry_number=next_retry_count,
        )
        retry_routing_key = get_retry_routing_key(
            next_retry_count,
            prefix=RESUME_RETRY_ROUTING_KEY_PREFIX,
        )
        retry_headers = _build_retry_headers(
            message=message,
            next_retry_count=next_retry_count,
        )

        await publish_with_headers(
            self._exchange,
            routing_key=retry_routing_key,
            body=message.body,
            headers=retry_headers,
        )
        _log(
            "retry_scheduled",
            request_id=request_id,
            application_id=application_id,
            event_id=event_id,
            attempt=attempt,
            error_message=classification.error_message_short,
            retry_count=next_retry_count,
            retry_max=MAX_RETRIES,
            retry_delay_seconds=retry_delay_seconds,
            retry_reason=classification.reason,
            retry_classification=classification.classification,
            retry_error_code=classification.error_code,
            retry_error_type=classification.error_type,
            retry_error_message_short=classification.error_message_short,
            retry_error_fingerprint=classification.error_fingerprint,
            retry_header_corrupted=retry_header_corrupted,
        )
        observe_worker_retry_attempt(
            event_name=metric_event_name,
            status="scheduled",
            queue_name=RESUME_QUEUE_NAME,
        )
        observe_worker_job_outcome(
            event_name=metric_event_name,
            status="retry_scheduled",
            queue_name=RESUME_QUEUE_NAME,
            duration_seconds=duration_seconds,
        )
        await message.ack()

    async def _mark_failed_before_dlq(
        self,
        *,
        application_id: str,
        request_id: str,
        event_id: str,
        attempt: int,
        failure_reason: str,
    ) -> None:
        if not _is_valid_application_id(application_id):
            return
        try:
            await mark_application_failed_for_event(
                application_id=application_id,
                request_id=request_id,
                event_id=event_id,
                attempt=attempt,
                failure_reason=failure_reason,
            )
        except ValueError:
            return

    async def _handle_processing_failure(
        self,
        *,
        message: AbstractIncomingMessage,
        metric_event_name: str,
        request_id: str,
        application_id: str,
        event_id: str,
        attempt: int,
        retry_count: int,
        retry_header_corrupted: bool,
        failure_reason: str,
        classification: RetryClassification,
        duration_seconds: float,
    ) -> None:
        _log(
            "resume_processing_failed",
            request_id=request_id,
            application_id=application_id,
            event_id=event_id,
            attempt=attempt,
            error_message=classification.error_message_short,
            retry_count=retry_count,
            retry_max=MAX_RETRIES,
            retry_reason=classification.reason,
            retry_classification=classification.classification,
            retry_error_code=classification.error_code,
            retry_error_type=classification.error_type,
            retry_error_message_short=classification.error_message_short,
            retry_error_fingerprint=classification.error_fingerprint,
            retry_header_corrupted=retry_header_corrupted,
        )
        observe_worker_job_outcome(
            event_name=metric_event_name,
            status="failed",
            queue_name=RESUME_QUEUE_NAME,
            duration_seconds=duration_seconds,
        )
        observe_worker_job_failure(
            event_name=metric_event_name,
            status="failed",
            queue_name=RESUME_QUEUE_NAME,
        )

        if classification.retryable and retry_count < MAX_RETRIES:
            await self._schedule_retry(
                message=message,
                metric_event_name=metric_event_name,
                request_id=request_id,
                application_id=application_id,
                event_id=event_id,
                attempt=attempt,
                retry_count=retry_count,
                duration_seconds=duration_seconds,
                classification=classification,
                retry_header_corrupted=retry_header_corrupted,
            )
            return

        await self._mark_failed_before_dlq(
            application_id=application_id,
            request_id=request_id,
            event_id=event_id,
            attempt=attempt,
            failure_reason=failure_reason,
        )
        await _send_to_dlq(
            message,
            metric_event_name=metric_event_name,
            request_id=request_id,
            application_id=application_id,
            event_id=event_id,
            attempt=attempt,
            retry_count=retry_count,
            duration_seconds=duration_seconds,
            classification=classification,
            retry_header_corrupted=retry_header_corrupted,
            retry_exhausted=classification.retryable and retry_count >= MAX_RETRIES,
        )

    async def _handle_message(self, message: AbstractIncomingMessage) -> None:
        current_task = asyncio.current_task()
        if current_task is not None:
            self._inflight_tasks.add(current_task)

        request_id = "unknown"
        application_id = "unknown"
        event_id = "unknown"
        metric_event_name = "unknown"
        retry_count, retry_header_corrupted = _extract_retry_count(message)
        attempt = retry_count + 1
        started_at = perf_counter()
        trace_headers = _build_trace_headers(message)
        parent_context = extract(trace_headers)

        try:
            with tracer.start_as_current_span(
                "resume.message.receive",
                kind=SpanKind.CONSUMER,
                context=parent_context,
            ) as receive_span:
                receive_span.set_attribute("messaging.system", "rabbitmq")
                receive_span.set_attribute("messaging.operation", "process")
                receive_span.set_attribute("messaging.destination", RESUME_QUEUE_NAME)
                receive_span.set_attribute("messaging.destination.name", RESUME_QUEUE_NAME)
                try:
                    raw_payload = _decode_message_body(message)
                    request_id = str(raw_payload.get("request_id", "unknown"))
                    application_id = str(raw_payload.get("resource_id", "unknown"))
                    event_id = str(raw_payload.get("event_id", "unknown"))
                    metric_event_name = str(raw_payload.get("event_name", "unknown"))
                    event = ResumeCreatedEvent.model_validate(raw_payload)

                    _log(
                        "job_received",
                        request_id=request_id,
                        application_id=application_id,
                        event_id=event_id,
                        attempt=attempt,
                        retry_count=retry_count,
                        retry_max=MAX_RETRIES,
                        retry_header_corrupted=retry_header_corrupted,
                    )

                    await asyncio.wait_for(
                        process_resume_event(event, attempt=attempt),
                        timeout=MAX_PROCESSING_SECONDS,
                    )
                    observe_worker_job_outcome(
                        event_name=event.event_name,
                        status="success",
                        queue_name=RESUME_QUEUE_NAME,
                        duration_seconds=perf_counter() - started_at,
                    )
                    await message.ack()
                except Exception as exc:
                    classification = classify_exception(exc)
                    _apply_retry_metadata_to_span(
                        receive_span,
                        classification=classification,
                        retry_header_corrupted=retry_header_corrupted,
                    )
                    receive_span.record_exception(exc)
                    receive_span.set_status(Status(StatusCode.ERROR))
                    await self._handle_processing_failure(
                        message=message,
                        metric_event_name=metric_event_name,
                        request_id=request_id,
                        application_id=application_id,
                        event_id=event_id,
                        attempt=attempt,
                        retry_count=retry_count,
                        retry_header_corrupted=retry_header_corrupted,
                        failure_reason=str(exc) or exc.__class__.__name__,
                        classification=classification,
                        duration_seconds=perf_counter() - started_at,
                    )
                    return
        finally:
            if current_task is not None:
                self._inflight_tasks.discard(current_task)
