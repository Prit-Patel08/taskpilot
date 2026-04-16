from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_listing import JobListing
from app.schemas.job_listing import JobListingCreateData, JobListingUpdateData


async def create_job_listing(
    session: AsyncSession,
    data: JobListingCreateData,
) -> JobListing:
    job_listing = JobListing(
        title=data.title,
        company_name=data.company_name,
        location=data.location,
        description=data.description,
        required_skills=data.required_skills,
        nice_to_have_skills=data.nice_to_have_skills,
        min_experience_years=data.min_experience_years,
        max_experience_years=data.max_experience_years,
        employment_type=data.employment_type,
        remote=data.remote,
        source=data.source,
        external_url=data.external_url,
    )
    session.add(job_listing)
    await session.flush()
    await session.refresh(job_listing)
    return job_listing


async def get_job_listing(
    session: AsyncSession,
    job_id: UUID,
) -> JobListing | None:
    return await session.get(JobListing, job_id)


async def list_job_listings(
    session: AsyncSession,
) -> list[JobListing]:
    result = await session.execute(
        select(JobListing).order_by(JobListing.created_at.desc())
    )
    return list(result.scalars().all())


async def update_job_listing(
    session: AsyncSession,
    *,
    job_listing: JobListing,
    data: JobListingUpdateData,
) -> JobListing:
    update_data = data.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(job_listing, field_name, value)
    await session.flush()
    await session.refresh(job_listing)
    return job_listing
