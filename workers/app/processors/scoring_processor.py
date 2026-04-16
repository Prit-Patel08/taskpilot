from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from dataclasses import dataclass
from typing import Any

from app.core.database import SessionLocal
from app.errors import DataMissing
from app.repositories.scoring_repository import (
    create_score,
    enqueue_apply_requested_event,
    get_application_by_id_for_scoring,
    get_existing_score,
    get_job_listing,
    get_resume_extraction,
    mark_application_completed,
    mark_application_scoring,
)
from app.schemas.apply import ApplyRequestedEvent
from app.schemas.score import ScoreCalculateEvent
from app.services.scoring_service import compute_score

logger = logging.getLogger(__name__)
SCORE_VERSION = 1


@dataclass(frozen=True)
class ScoringResult:
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
    error_message: str | None = None,
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
    if error_message is not None:
        payload["error_message"] = error_message
    logger.info(json.dumps(payload))


def _build_apply_headers(*, created_at: datetime) -> dict[str, str | int]:
    return {
        "retry_count": 0,
        "original_timestamp": created_at.isoformat(),
    }


async def _enqueue_apply_requested(
    *,
    session: Any,
    application: Any,
    application_id_str: str,
    request_id: str,
    created_at: datetime,
) -> None:
    apply_event = ApplyRequestedEvent(
        request_id=request_id,
        user_id=str(application.user_id),
        resource_id=application.id,
        correlation_id=application.id,
        created_at=created_at,
        payload={
            "application_id": application_id_str,
        },
    )
    await enqueue_apply_requested_event(
        session,
        payload=apply_event.model_dump(mode="json"),
        headers=_build_apply_headers(created_at=apply_event.created_at),
        created_at=apply_event.created_at,
    )


async def process_scoring_event(
    event: ScoreCalculateEvent,
    *,
    attempt: int,
) -> ScoringResult:
    application_id = event.resource_id
    application_id_str = str(application_id)
    request_id = event.request_id
    event_id = str(event.event_id)
    queue_event_name = event.event_name

    async with SessionLocal() as session:
        async with session.begin():
            application = await get_application_by_id_for_scoring(session, application_id)
            if application is None:
                _log(
                    "scoring_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="application_not_scorable",
                )
                return ScoringResult(
                    skipped=True,
                    status="skipped",
                    skip_reason="application_not_scorable",
                )

            if application.status == "completed":
                _log(
                    "scoring_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="already_completed",
                )
                return ScoringResult(skipped=True, status="completed", skip_reason="already_completed")
            if application.status == "failed":
                _log(
                    "scoring_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="already_failed",
                )
                return ScoringResult(skipped=True, status="failed", skip_reason="already_failed")
            if application.status not in {"resume_processed", "scoring"}:
                _log(
                    "scoring_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason=f"invalid_state:{application.status}",
                )
                return ScoringResult(skipped=True, status=application.status, skip_reason="invalid_state")

            existing_score = await get_existing_score(session, application_id)
            if existing_score is not None:
                created_at = datetime.now(UTC)
                await _enqueue_apply_requested(
                    session=session,
                    application=application,
                    application_id_str=application_id_str,
                    request_id=request_id,
                    created_at=created_at,
                )
                await mark_application_completed(session, application_id)
                _log(
                    "scoring_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="score_already_exists",
                )
                return ScoringResult(
                    skipped=True,
                    status="completed",
                    skip_reason="score_already_exists",
                )

            resume_extraction = await get_resume_extraction(session, application.resume_id)
            if resume_extraction is None:
                raise DataMissing("Resume extraction is missing for scoring")

            job_listing = await get_job_listing(session, application.job_listing_id)
            if job_listing is None:
                raise DataMissing("Job listing is missing for scoring")

            if application.status == "resume_processed":
                transitioned = await mark_application_scoring(session, application_id)
                if not transitioned:
                    _log(
                        "scoring_completed",
                        queue_event_name=queue_event_name,
                        application_id=application_id_str,
                        attempt=attempt,
                        request_id=request_id,
                        event_id=event_id,
                        skip_reason="transition_conflict",
                    )
                    return ScoringResult(
                        skipped=True,
                        status=application.status,
                        skip_reason="transition_conflict",
                    )

            _log(
                "scoring_started",
                queue_event_name=queue_event_name,
                application_id=application_id_str,
                attempt=attempt,
                request_id=request_id,
                event_id=event_id,
            )

            scoring_output = compute_score(resume_extraction, job_listing)
            created_at = datetime.now(UTC)
            inserted = await create_score(
                session,
                application_id=application_id,
                score=int(scoring_output["score"]),
                breakdown=dict(scoring_output["breakdown"]),
                version=SCORE_VERSION,
                created_at=created_at,
            )
            if not inserted:
                await _enqueue_apply_requested(
                    session=session,
                    application=application,
                    application_id_str=application_id_str,
                    request_id=request_id,
                    created_at=created_at,
                )
                await mark_application_completed(session, application_id)
                _log(
                    "scoring_completed",
                    queue_event_name=queue_event_name,
                    application_id=application_id_str,
                    attempt=attempt,
                    request_id=request_id,
                    event_id=event_id,
                    skip_reason="score_already_exists",
                )
                return ScoringResult(
                    skipped=True,
                    status="completed",
                    skip_reason="score_already_exists",
                )

            await _enqueue_apply_requested(
                session=session,
                application=application,
                application_id_str=application_id_str,
                request_id=request_id,
                created_at=created_at,
            )
            completed = await mark_application_completed(session, application_id)
            if not completed:
                raise DataMissing("Application could not be marked completed after scoring")

    _log(
        "scoring_completed",
        queue_event_name=queue_event_name,
        application_id=application_id_str,
        attempt=attempt,
        request_id=request_id,
        event_id=event_id,
    )
    return ScoringResult(skipped=False, status="completed")
