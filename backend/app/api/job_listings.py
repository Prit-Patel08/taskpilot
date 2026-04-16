from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.auth import get_current_user
from app.core.dependencies import get_db
from app.repositories.job_listing_repository import (
    create_job_listing,
    get_job_listing,
    list_job_listings,
)
from app.schemas.auth import CurrentUser
from app.schemas.job_listing import (
    JobListingCreateData,
    JobListingCreateRequest,
    JobListingListResponse,
    JobListingResponse,
)

router = APIRouter(prefix="/job-listings", tags=["job-listings"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=JobListingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_listing_route(
    request: JobListingCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> JobListingResponse:
    request_id = x_request_id or str(uuid4())
    job_listing = await create_job_listing(
        session,
        JobListingCreateData(**request.model_dump()),
    )
    await session.commit()

    logger.info(
        json.dumps(
            {
                "event": "job_listing_created",
                "request_id": request_id,
                "job_listing_id": str(job_listing.id),
                "user_id": str(current_user.id),
                "service": "backend",
                "layer": "api",
            }
        )
    )
    return JobListingResponse.model_validate(job_listing)


@router.get(
    "/{job_id}",
    response_model=JobListingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_job_listing_route(
    job_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> JobListingResponse:
    request_id = x_request_id or str(uuid4())
    job_listing = await get_job_listing(session, job_id)
    if job_listing is None:
        logger.info(
            json.dumps(
                {
                    "event": "job_listing_not_found",
                    "request_id": request_id,
                    "job_listing_id": str(job_id),
                    "user_id": str(current_user.id),
                    "service": "backend",
                    "layer": "api",
                }
            )
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="job listing not found",
        )

    logger.info(
        json.dumps(
            {
                "event": "job_listing_read",
                "request_id": request_id,
                "job_listing_id": str(job_listing.id),
                "user_id": str(current_user.id),
                "service": "backend",
                "layer": "api",
            }
        )
    )
    return JobListingResponse.model_validate(job_listing)


@router.get(
    "",
    response_model=JobListingListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_job_listings_route(
    session: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> JobListingListResponse:
    request_id = x_request_id or str(uuid4())
    job_listings = await list_job_listings(session)

    logger.info(
        json.dumps(
            {
                "event": "job_listing_list",
                "request_id": request_id,
                "job_listing_count": len(job_listings),
                "user_id": str(current_user.id),
                "service": "backend",
                "layer": "api",
            }
        )
    )
    return JobListingListResponse(
        job_listings=[
            JobListingResponse.model_validate(job_listing)
            for job_listing in job_listings
        ]
    )
