from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

SERVICE_NAME = "taskpilot-workers"
_tracing_initialized = False


def init_tracing() -> None:
    global _tracing_initialized

    if _tracing_initialized:
        return

    resource = Resource.create({"service.name": SERVICE_NAME})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(tracer_provider)
    _tracing_initialized = True


def shutdown_tracing() -> None:
    tracer_provider = trace.get_tracer_provider()
    shutdown = getattr(tracer_provider, "shutdown", None)
    if callable(shutdown):
        shutdown()
