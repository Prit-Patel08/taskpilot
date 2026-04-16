from contextlib import asynccontextmanager
import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.router import api_router
from app.core.config import get_settings
from app.observability.metrics import build_http_event_name, observe_http_request
from app.observability.tracing import init_tracing, shutdown_tracing

logging.basicConfig(level=logging.INFO, format="%(message)s")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        shutdown_tracing(app)


app = FastAPI(title="taskpilot-backend", version="0.1.0", lifespan=lifespan)
init_tracing(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        observe_http_request(
            event_name=build_http_event_name(request),
            status=str(status_code),
            duration_seconds=perf_counter() - start_time,
        )


app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(api_router, prefix="/v1")
