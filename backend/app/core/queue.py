from __future__ import annotations

import json
import logging
from typing import Any

from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.propagate import inject
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode

from app.core.rabbitmq import (
    APPLICATION_CREATED_ROUTING_KEY,
    APPLICATION_EVENTS_EXCHANGE,
    APPLICATION_QUEUE_NAME,
    APPLY_QUEUE_NAME,
    APPLY_REQUESTED_ROUTING_KEY,
    ATS_ANALYZE_ROUTING_KEY,
    ATS_QUEUE_NAME,
    RESUME_CREATED_ROUTING_KEY,
    RESUME_PROCESS_ROUTING_KEY,
    RESUME_QUEUE_NAME,
    SCORING_CALCULATE_ROUTING_KEY,
    SCORING_QUEUE_NAME,
    rabbitmq_client,
)
from app.schemas.application import ApplicationCreatedEvent
from app.schemas.resume import ResumeCreatedEvent

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def build_outbox_headers(*, created_at: Any) -> dict[str, Any]:
    trace_headers: dict[str, str] = {}
    inject(trace_headers)
    return {
        **trace_headers,
        "retry_count": 0,
        "original_timestamp": created_at.isoformat(),
    }


def build_application_created_outbox_message(
    event: ApplicationCreatedEvent,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return event.model_dump(mode="json"), build_outbox_headers(created_at=event.created_at)


def build_resume_created_outbox_message(
    event: ResumeCreatedEvent,
) -> tuple[dict[str, Any], dict[str, Any]]:
    return event.model_dump(mode="json"), build_outbox_headers(created_at=event.created_at)


def _resolve_rabbitmq_target(event_name: str) -> tuple[str, str]:
    if event_name == "application.created":
        return APPLICATION_CREATED_ROUTING_KEY, APPLICATION_QUEUE_NAME
    if event_name == "resume.created":
        return RESUME_CREATED_ROUTING_KEY, RESUME_QUEUE_NAME
    if event_name == "resume.process":
        return RESUME_PROCESS_ROUTING_KEY, RESUME_QUEUE_NAME
    if event_name == "ats.analyze":
        return ATS_ANALYZE_ROUTING_KEY, ATS_QUEUE_NAME
    if event_name == "score.calculate":
        return SCORING_CALCULATE_ROUTING_KEY, SCORING_QUEUE_NAME
    if event_name == "apply.requested":
        return APPLY_REQUESTED_ROUTING_KEY, APPLY_QUEUE_NAME
    raise ValueError(f"Unsupported outbox event name: {event_name}")


def _normalize_headers(headers: dict[str, Any]) -> dict[str, str]:
    normalized_headers: dict[str, str] = {}
    for key, value in headers.items():
        normalized_key = str(key)
        if isinstance(value, bytes):
            normalized_headers[normalized_key] = value.decode("utf-8", errors="ignore")
        else:
            normalized_headers[normalized_key] = str(value)
    return normalized_headers


async def publish_outbox_event(
    *,
    event_name: str,
    payload: dict[str, Any],
    headers: dict[str, Any],
) -> None:
    message_body = json.dumps(payload).encode("utf-8")
    parent_context = extract(_normalize_headers(headers))
    application_id = str(payload.get("resource_id", "unknown"))
    routing_key, queue_name = _resolve_rabbitmq_target(event_name)

    with tracer.start_as_current_span(
        "outbox.queue.publish",
        kind=SpanKind.PRODUCER,
        context=parent_context,
    ) as span:
        span.set_attribute("messaging.system", "rabbitmq")
        span.set_attribute("messaging.destination", queue_name)
        span.set_attribute("messaging.destination.name", queue_name)
        span.set_attribute("messaging.rabbitmq.exchange", APPLICATION_EVENTS_EXCHANGE)
        span.set_attribute("messaging.rabbitmq.routing_key", routing_key)
        span.set_attribute("event.type", event_name)
        span.set_attribute("application.id", application_id)
        span.set_attribute("retry.count", int(headers.get("retry_count", 0)))

        try:
            await rabbitmq_client.publish(
                routing_key=routing_key,
                body=message_body,
                headers=headers,
            )
        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "outbox_queue_publish_failed",
                        "request_id": str(payload.get("request_id", "unknown")),
                        "application_id": application_id,
                        "service": "backend",
                        "layer": "outbox",
                        "event_id": str(payload.get("event_id", "unknown")),
                        "queue_event_name": event_name,
                        "created_at": str(payload.get("created_at", "unknown")),
                        "exchange": APPLICATION_EVENTS_EXCHANGE,
                        "routing_key": routing_key,
                        "error_message": str(exc),
                    }
                )
            )
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR))
            raise

        logger.info(
            json.dumps(
                {
                    "event": "outbox_queue_publish",
                    "request_id": str(payload.get("request_id", "unknown")),
                    "application_id": application_id,
                    "service": "backend",
                    "layer": "outbox",
                    "event_id": str(payload.get("event_id", "unknown")),
                    "queue_event_name": event_name,
                    "created_at": str(payload.get("created_at", "unknown")),
                    "exchange": APPLICATION_EVENTS_EXCHANGE,
                    "routing_key": routing_key,
                    "queue_publish_mode": "rabbitmq",
                }
            )
        )
