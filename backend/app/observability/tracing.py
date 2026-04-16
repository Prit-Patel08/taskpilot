from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

SERVICE_NAME = "taskpilot-backend"
_tracing_initialized = False


def init_tracing(app: FastAPI) -> None:
    global _tracing_initialized

    if _tracing_initialized:
        return

    resource = Resource.create({"service.name": SERVICE_NAME})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    app.state.tracer_provider = tracer_provider
    _tracing_initialized = True


def shutdown_tracing(app: FastAPI) -> None:
    tracer_provider = getattr(app.state, "tracer_provider", None)
    if tracer_provider is not None:
        tracer_provider.shutdown()
