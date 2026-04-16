from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCode
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.queue import build_application_created_outbox_message
from app.repositories.application_repository import (
    create_application,
    get_application_by_id,
    list_applications_by_user_id,
)
from app.repositories.job_listing_repository import get_job_listing
from app.repositories.outbox_repository import create_outbox_event
from app.repositories.resume_repository import get_resume_by_id
from app.schemas.application import ApplicationCreateData, ApplicationCreatedEvent
from app.schemas.outbox import OutboxEventCreateData
from app.services.idempotency_service import (
    execute_with_idempotency,
    IdempotencyConflictError,
    IdempotentOperationResult,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
APPLICATION_CREATE_STATUS_CODE = 202


@dataclass(frozen=True)
class ApplicationCreateResult:
    response_status: int
    response_body: dict[str, Any]


def _build_application_create_response(*, application_id: UUID, status: str) -> dict[str, Any]:
    return {
        "application_id": str(application_id),
        "status": status,
    }


async def _create_application_operation(
    session: AsyncSession,
    *,
    data: ApplicationCreateData,
    request_id: str,
    idempotency_key: str,
) -> IdempotentOperationResult:
    with tracer.start_as_current_span(
        "application.db.write",
        kind=SpanKind.INTERNAL,
    ) as span:
        span.set_attribute("db.system", "postgresql")
        try:
            application = await create_application(
                session,
                ApplicationCreateData(
                    user_id=data.user_id,
                    resume_id=data.resume_id,
                    job_listing_id=data.job_listing_id,
                ),
            )
            span.set_attribute("application.id", str(application.id))
            span.set_attribute("application.user_id", str(application.user_id))
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR))
            raise

    event = ApplicationCreatedEvent(
        request_id=request_id,
        user_id=str(application.user_id),
        resource_id=application.id,
        payload={
            "application_id": str(application.id),
            "resume_id": str(application.resume_id),
            "job_listing_id": str(application.job_listing_id),
            "status": application.status,
        },
    )
    event_payload, event_headers = build_application_created_outbox_message(event)

    outbox_event = await create_outbox_event(
        session,
        OutboxEventCreateData(
            event_name=event.event_name,
            payload=event_payload,
            headers=event_headers,
        ),
    )

    response_body = _build_application_create_response(
        application_id=application.id,
        status=application.status,
    )

    logger.info(
        json.dumps(
            {
                "event": "application_outbox_enqueued",
                "request_id": request_id,
                "application_id": str(application.id),
                "outbox_event_id": str(outbox_event.id),
                "idempotency_key": idempotency_key,
                "service": "backend",
                "layer": "service",
            }
        )
    )

    return IdempotentOperationResult(
        response_status=APPLICATION_CREATE_STATUS_CODE,
        response_json=response_body,
        resource_id=application.id,
    )


async def create_application_service(
    session: AsyncSession,
    data: ApplicationCreateData,
    request_id: str,
    *,
    idempotency_key: str,
) -> ApplicationCreateResult:
    request_payload = {
        "resume_id": str(data.resume_id),
        "job_listing_id": str(data.job_listing_id),
    }

    async with session.begin():
        resume = await get_resume_by_id(session, data.resume_id)
        if resume is None or resume.user_id != data.user_id:
            raise ValueError("resume_id is invalid for this user")

        job_listing = await get_job_listing(session, data.job_listing_id)
        if job_listing is None:
            raise ValueError("job_listing_id is invalid")

        result = await execute_with_idempotency(
            session,
            user_id=data.user_id,
            idempotency_key=idempotency_key,
            request_payload=request_payload,
            operation=lambda: _create_application_operation(
                session,
                data=data,
                request_id=request_id,
                idempotency_key=idempotency_key,
            ),
        )

        if result.resource_id is not None:
            application = await get_application_by_id(session, result.resource_id)
            if application is not None:
                return ApplicationCreateResult(
                    response_status=result.response_status,
                    response_body=_build_application_create_response(
                        application_id=application.id,
                        status=application.status,
                    ),
                )

    return ApplicationCreateResult(
        response_status=result.response_status,
        response_body=result.response_json,
    )


async def get_application_service(
    session: AsyncSession, application_id: UUID, request_id: str
):
    application = await get_application_by_id(session, application_id)

    logger.info(
        json.dumps(
            {
                "event": "application_read_lookup",
                "request_id": request_id,
                "application_id": str(application_id),
                "service": "backend",
                "layer": "service",
            }
        )
    )

    return application


async def list_applications_service(
    session: AsyncSession,
    user_id: UUID,
    request_id: str,
):
    applications = await list_applications_by_user_id(session, user_id)

    logger.info(
        json.dumps(
            {
                "event": "application_list_lookup",
                "request_id": request_id,
                "user_id": str(user_id),
                "service": "backend",
                "layer": "service",
                "application_count": len(applications),
            }
        )
    )

    return applications
