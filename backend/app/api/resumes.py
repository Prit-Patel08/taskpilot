from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.core.queue import build_resume_created_outbox_message
from app.repositories.outbox_repository import create_outbox_event
from app.repositories.resume_repository import (
    create_resume,
    get_resume_by_id,
    list_resumes_by_user_id,
)
from app.schemas.auth import CurrentUser
from app.schemas.outbox import OutboxEventCreateData
from app.schemas.resume import (
    ResumeCreateData,
    ResumeCreateRequest,
    ResumeCreatedEvent,
    ResumeListResponse,
    ResumeReadResponse,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=ResumeReadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resume_route(
    request: ResumeCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> ResumeReadResponse:
    request_id = x_request_id or str(uuid4())
    async with session.begin():
        resume = await create_resume(
            session,
            ResumeCreateData(
                user_id=current_user.id,
                file_key=request.file_key,
            ),
        )
        event = ResumeCreatedEvent(
            request_id=request_id,
            user_id=str(current_user.id),
            resource_id=resume.id,
            payload={
                "resume_id": str(resume.id),
                "user_id": str(current_user.id),
                "file_key": resume.file_key,
            },
        )
        payload, headers = build_resume_created_outbox_message(event)
        await create_outbox_event(
            session,
            OutboxEventCreateData(
                event_name=event.event_name,
                payload=payload,
                headers=headers,
            ),
        )

    logger.info(
        json.dumps(
            {
                "event": "resume_created",
                "request_id": request_id,
                "resume_id": str(resume.id),
                "user_id": str(current_user.id),
                "service": "backend",
                "layer": "api",
            }
        )
    )
    return ResumeReadResponse(
        resume_id=resume.id,
        user_id=resume.user_id,
        file_key=resume.file_key,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


@router.get(
    "",
    response_model=ResumeListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_resumes_route(
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> ResumeListResponse:
    request_id = x_request_id or str(uuid4())
    resumes = await list_resumes_by_user_id(session, current_user.id)
    logger.info(
        json.dumps(
            {
                "event": "resume_list",
                "request_id": request_id,
                "user_id": str(current_user.id),
                "resume_count": len(resumes),
                "service": "backend",
                "layer": "api",
            }
        )
    )
    return ResumeListResponse(
        resumes=[
            ResumeReadResponse(
                resume_id=resume.id,
                user_id=resume.user_id,
                file_key=resume.file_key,
                created_at=resume.created_at,
                updated_at=resume.updated_at,
            )
            for resume in resumes
        ]
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeReadResponse,
    status_code=status.HTTP_200_OK,
)
async def get_resume_route(
    resume_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> ResumeReadResponse:
    request_id = x_request_id or str(uuid4())
    resume = await get_resume_by_id(session, resume_id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="resume not found",
        )
    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this resume.",
        )

    logger.info(
        json.dumps(
            {
                "event": "resume_read",
                "request_id": request_id,
                "resume_id": str(resume.id),
                "user_id": str(current_user.id),
                "service": "backend",
                "layer": "api",
            }
        )
    )
    return ResumeReadResponse(
        resume_id=resume.id,
        user_id=resume.user_id,
        file_key=resume.file_key,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )
