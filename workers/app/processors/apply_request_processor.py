from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import logging
import random
from dataclasses import dataclass

from app.core.database import SessionLocal
from app.errors import InvalidApplicationState
from app.repositories.apply_repository import (
    create_application_attempt,
    enqueue_apply_execute_event,
    get_application_attempt,
    get_application_for_apply_request,
    get_daily_count,
    has_already_applied,
    increment_daily_limit,
    mark_application_rate_limited,
)
from app.schemas.apply import ApplyExecuteEvent, ApplyRequestedEvent

logger = logging.getLogger(__name__)
DAILY_APPLICATION_LIMIT = 20


@dataclass(frozen=True)
class ApplyRequestResult:
    skipped: bool
    status: str
    skip_reason: str | None = None


def _log(
    event_name: str,
    *,
    queue_event_name: str,
    application_id: str,
    attempt: int,
    request_id: str,
    event_id: str,
    skip_reason: str | None = None,
) -> None:
    payload: dict[str, str | int] = {
        "event": event_name,
        "queue_event_name": queue_event_name,
        "application_id": application_id,
        "attempt": attempt,
        "request_id": request_id,
        "event_id": event_id,
        "service": "workers",
        "layer": "processor",
    }
    if skip_reason is not None:
        payload["skip_reason"] = skip_reason
    logger.info(json.dumps(payload))


def _build_apply_execute_headers(*, created_at: datetime) -> dict[str, str | int]:
    return {
        "retry_count": 0,
        "original_timestamp": created_at.isoformat(),
    }


def _build_scheduled_at(*, created_at: datetime) -> datetime:
    return created_at + timedelta(seconds=random.randint(10, 60))


async def process_apply_requested_event(
    event: ApplyRequestedEvent,
    *,
    attempt: int,
) -> ApplyRequestResult:
    application_id = event.resource_id
    application_id_str = str(application_id)
    request_id = event.request_id
    event_id = str(event.event_id)
    queue_event_name = event.event_name

    async with SessionLocal() as session:
        async with session.begin():
            application = await get_application_for_apply_request(session, application_id)
            if application is None:
                _log(
                    "apply_request_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="application_not_found",
                )
                return ApplyRequestResult(
                    skipped=True,
                    status="skipped",
                    skip_reason="application_not_found",
                )

            if await has_already_applied(session, application_id):
                existing_attempt = await get_application_attempt(session, application_id)
                _log(
                    "apply_request_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="already_attempted",
                )
                return ApplyRequestResult(
                    skipped=True,
                    status=existing_attempt.status,
                    skip_reason="already_attempted",
                )

            if application.status != "completed":
                _log(
                    "apply_request_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason=f"invalid_state:{application.status}",
                )
                raise InvalidApplicationState(
                    f"Application must be completed before apply scheduling; current state={application.status}"
                )

            today = datetime.now(UTC).date()
            current_daily_count = await get_daily_count(
                session,
                application.user_id,
                on_date=today,
            )
            if current_daily_count >= DAILY_APPLICATION_LIMIT:
                await mark_application_rate_limited(session, application_id)
                _log(
                    "apply_request_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="daily_limit_exceeded",
                )
                return ApplyRequestResult(
                    skipped=True,
                    status="rate_limited",
                    skip_reason="daily_limit_exceeded",
                )

            updated_count = await increment_daily_limit(
                session,
                application.user_id,
                on_date=today,
            )
            if updated_count > DAILY_APPLICATION_LIMIT:
                await mark_application_rate_limited(session, application_id)
                _log(
                    "apply_request_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="daily_limit_exceeded",
                )
                return ApplyRequestResult(
                    skipped=True,
                    status="rate_limited",
                    skip_reason="daily_limit_exceeded",
                )

            created_at = datetime.now(UTC)
            scheduled_at = _build_scheduled_at(created_at=created_at)
            created = await create_application_attempt(
                session,
                application_id=application_id,
                status="scheduled",
                scheduled_at=scheduled_at,
                created_at=created_at,
            )
            if not created:
                _log(
                    "apply_request_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="already_attempted",
                )
                return ApplyRequestResult(
                    skipped=True,
                    status="scheduled",
                    skip_reason="already_attempted",
                )

            execute_event = ApplyExecuteEvent(
                request_id=request_id,
                user_id=str(application.user_id),
                resource_id=application.id,
                correlation_id=application.id,
                created_at=created_at,
                payload={
                    "application_id": application_id_str,
                    "scheduled_at": scheduled_at.isoformat(),
                },
            )
            await enqueue_apply_execute_event(
                session,
                payload=execute_event.model_dump(mode="json"),
                headers=_build_apply_execute_headers(created_at=execute_event.created_at),
                created_at=execute_event.created_at,
            )

    _log(
        "apply_request_completed",
        queue_event_name=queue_event_name,
        application_id=application_id_str,
        attempt=attempt,
        request_id=request_id,
        event_id=event_id,
    )
    return ApplyRequestResult(skipped=False, status="scheduled")
