from __future__ import annotations

from prometheus_client import Counter, Histogram, start_http_server

WORKER_METRICS_HOST = "0.0.0.0"
WORKER_METRICS_PORT = 9001

worker_jobs_total = Counter(
    "worker_jobs_total",
    "Total worker job outcomes by event and queue.",
    ["event_name", "status", "queue_name"],
)

worker_job_duration_seconds = Histogram(
    "worker_job_duration_seconds",
    "Worker job processing duration in seconds.",
    ["event_name", "status", "queue_name"],
)

worker_job_failures_total = Counter(
    "worker_job_failures_total",
    "Total worker job failures by event and queue.",
    ["event_name", "status", "queue_name"],
)

retry_attempt_total = Counter(
    "retry_attempt_total",
    "Total scheduled worker retries by event and queue.",
    ["event_name", "status", "queue_name"],
)

retry_exhausted_total = Counter(
    "retry_exhausted_total",
    "Total worker jobs that exhausted retries by event and queue.",
    ["event_name", "status", "queue_name"],
)

heartbeat_failures_total = Counter(
    "heartbeat_failures_total",
    "Total worker heartbeat update failures by event and queue.",
    ["event_name", "status", "queue_name"],
)

stuck_jobs_detected_total = Counter(
    "stuck_jobs_detected_total",
    "Total stuck jobs detected by the recovery loop.",
    ["event_name", "status", "queue_name"],
)

stuck_jobs_recovered_total = Counter(
    "stuck_jobs_recovered_total",
    "Total stuck jobs safely requeued by the recovery loop.",
    ["event_name", "status", "queue_name"],
)

stuck_jobs_skipped_total = Counter(
    "stuck_jobs_skipped_total",
    "Total stuck jobs skipped by recovery due to retry exhaustion or invalid state.",
    ["event_name", "status", "queue_name"],
)

stuck_job_scan_duration_seconds = Histogram(
    "stuck_job_scan_duration_seconds",
    "Duration of stuck job recovery scans in seconds.",
    ["event_name", "status", "queue_name"],
)


def start_worker_metrics_server() -> None:
    start_http_server(WORKER_METRICS_PORT, addr=WORKER_METRICS_HOST)


def observe_worker_job_outcome(
    *,
    event_name: str,
    status: str,
    queue_name: str,
    duration_seconds: float,
) -> None:
    worker_jobs_total.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).inc()
    worker_job_duration_seconds.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).observe(duration_seconds)


def observe_worker_job_failure(
    *,
    event_name: str,
    status: str,
    queue_name: str,
) -> None:
    worker_job_failures_total.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).inc()


def observe_worker_retry_attempt(
    *,
    event_name: str,
    status: str,
    queue_name: str,
) -> None:
    retry_attempt_total.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).inc()


def observe_worker_retry_exhausted(
    *,
    event_name: str,
    status: str,
    queue_name: str,
) -> None:
    retry_exhausted_total.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).inc()


def observe_heartbeat_failure(
    *,
    event_name: str,
    status: str,
    queue_name: str,
) -> None:
    heartbeat_failures_total.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).inc()


def observe_stuck_job_detected(
    *,
    event_name: str,
    status: str,
    queue_name: str,
) -> None:
    stuck_jobs_detected_total.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).inc()


def observe_stuck_job_recovered(
    *,
    event_name: str,
    status: str,
    queue_name: str,
) -> None:
    stuck_jobs_recovered_total.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).inc()


def observe_stuck_job_skipped(
    *,
    event_name: str,
    status: str,
    queue_name: str,
) -> None:
    stuck_jobs_skipped_total.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).inc()


def observe_stuck_job_scan_duration(
    *,
    event_name: str,
    status: str,
    queue_name: str,
    duration_seconds: float,
) -> None:
    stuck_job_scan_duration_seconds.labels(
        event_name=event_name,
        status=status,
        queue_name=queue_name,
    ).observe(duration_seconds)
