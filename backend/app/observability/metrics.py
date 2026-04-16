from __future__ import annotations

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram

HTTP_QUEUE_NAME = "http"

http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests handled by the backend.",
    ["event_name", "status", "queue_name"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["event_name", "status", "queue_name"],
)
outbox_pending_total = Gauge(
    "outbox_pending_total",
    "Current number of pending outbox events.",
)
outbox_inflight_total = Gauge(
    "outbox_inflight_total",
    "Current number of outbox events claimed for publishing.",
)
outbox_batch_size = Gauge(
    "outbox_batch_size",
    "Number of outbox events claimed in the most recent batch.",
)
outbox_published_total = Counter(
    "outbox_published_total",
    "Total number of outbox events published to RabbitMQ.",
    ["event_name"],
)
outbox_failed_total = Counter(
    "outbox_failed_total",
    "Total number of outbox events marked failed.",
    ["event_name"],
)


def build_http_event_name(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    return f"{request.method} {route_path}"


def observe_http_request(*, event_name: str, status: str, duration_seconds: float) -> None:
    http_requests_total.labels(
        event_name=event_name,
        status=status,
        queue_name=HTTP_QUEUE_NAME,
    ).inc()
    http_request_duration_seconds.labels(
        event_name=event_name,
        status=status,
        queue_name=HTTP_QUEUE_NAME,
    ).observe(duration_seconds)


def set_outbox_pending_total(count: int) -> None:
    outbox_pending_total.set(count)


def set_outbox_inflight_total(count: int) -> None:
    outbox_inflight_total.set(count)


def set_outbox_batch_size(count: int) -> None:
    outbox_batch_size.set(count)


def observe_outbox_published(*, event_name: str) -> None:
    outbox_published_total.labels(event_name=event_name).inc()


def observe_outbox_failed(*, event_name: str) -> None:
    outbox_failed_total.labels(event_name=event_name).inc()
