from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.models.score import Score
from app.schemas.auth import CurrentUser
from app.schemas.application import (
    ApplicationAcceptedResponse,
    ApplicationCreateData,
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationReadResponse,
)
from app.services.application_service import (
    create_application_service,
    get_application_service,
    IdempotencyConflictError,
    list_applications_service,
)

router = APIRouter(prefix="/applications", tags=["applications"])

logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=ApplicationAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_application(
    request: ApplicationCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> JSONResponse:
    request_id = x_request_id or str(uuid4())
    normalized_idempotency_key = (idempotency_key or "").strip()
    if not normalized_idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required.",
        )
    if len(normalized_idempotency_key) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header must be 255 characters or fewer.",
        )

    try:
        result = await create_application_service(
            session,
            ApplicationCreateData(
                user_id=current_user.id,
                resume_id=request.resume_id,
                job_listing_id=request.job_listing_id,
            ),
            request_id=request_id,
            idempotency_key=normalized_idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    logger.info(
        json.dumps(
                {
                    "event": "application_create_accepted",
                    "request_id": request_id,
                    "application_id": str(result.response_body["application_id"]),
                    "user_id": str(current_user.id),
                    "idempotency_key": normalized_idempotency_key,
                    "service": "backend",
                    "layer": "api",
                }
            )
        )

    return JSONResponse(
        status_code=result.response_status,
        content=result.response_body,
    )


@router.get(
    "",
    response_model=ApplicationListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_applications(
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> ApplicationListResponse:
    request_id = x_request_id or str(uuid4())
    applications = await list_applications_service(
        session,
        current_user.id,
        request_id,
    )

    logger.info(
        json.dumps(
            {
                "event": "application_list",
                "request_id": request_id,
                "user_id": str(current_user.id),
                "service": "backend",
                "layer": "api",
                "application_count": len(applications),
            }
        )
    )

    return ApplicationListResponse(
        applications=[
            ApplicationReadResponse(
                application_id=application.id,
                user_id=application.user_id,
                status=application.status,
                resume_id=application.resume_id,
                job_listing_id=application.job_listing_id,
                created_at=application.created_at,
            )
            for application in applications
        ]
    )


@router.get(
    "/{application_id}",
    status_code=status.HTTP_200_OK,
)
async def get_application(
    application_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> JSONResponse:
    request_id = x_request_id or str(uuid4())
    application = await get_application_service(session, application_id, request_id)

    if application is None:
        logger.info(
            json.dumps(
                {
                    "event": "application_not_found",
                    "request_id": request_id,
                    "application_id": str(application_id),
                    "user_id": str(current_user.id),
                    "service": "backend",
                    "layer": "api",
                }
            )
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="application not found",
        )

    if application.user_id != current_user.id:
        logger.info(
            json.dumps(
                {
                    "event": "application_forbidden",
                    "request_id": request_id,
                    "application_id": str(application_id),
                    "user_id": str(current_user.id),
                    "service": "backend",
                    "layer": "api",
                }
            )
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this application.",
        )

    logger.info(
        json.dumps(
            {
                "event": "application_read",
                "request_id": request_id,
                "application_id": str(application.id),
                "user_id": str(current_user.id),
                "service": "backend",
                "layer": "api",
            }
        )
    )

    score_result = await session.execute(
        select(Score.score, Score.breakdown).where(
            Score.application_id == application.id
        )
    )
    score_row = score_result.one_or_none()

    return JSONResponse(
        content={
            "application_id": str(application.id),
            "status": application.status,
            "resume_id": str(application.resume_id),
            "job_listing_id": str(application.job_listing_id),
            "created_at": application.created_at.isoformat(),
            "score": score_row.score if score_row is not None else None,
            "score_breakdown": (
                score_row.breakdown if score_row is not None else None
            ),
        }
    )
