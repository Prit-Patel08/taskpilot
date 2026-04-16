from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.schemas.resume import ResumeCreateData


async def create_resume(
    session: AsyncSession,
    data: ResumeCreateData,
) -> Resume:
    resume = Resume(
        user_id=data.user_id,
        file_key=data.file_key,
    )
    session.add(resume)
    await session.flush()
    await session.refresh(resume)
    return resume


async def get_resume_by_id(
    session: AsyncSession,
    resume_id: UUID,
) -> Resume | None:
    return await session.get(Resume, resume_id)


async def list_resumes_by_user_id(
    session: AsyncSession,
    user_id: UUID,
) -> list[Resume]:
    result = await session.execute(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
    )
    return list(result.scalars().all())
