from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.schemas.application import ApplicationCreateData


async def create_application(
    session: AsyncSession, application_data: ApplicationCreateData
) -> Application:
    application = Application(
        user_id=application_data.user_id,
        resume_id=application_data.resume_id,
        job_listing_id=application_data.job_listing_id,
        is_legacy=False,
        status="queued",
    )

    session.add(application)
    await session.flush()
    await session.refresh(application)

    return application


async def get_application_by_id(
    session: AsyncSession, application_id: UUID
) -> Application | None:
    return await session.get(Application, application_id)


async def list_applications_by_user_id(
    session: AsyncSession,
    user_id: UUID,
) -> list[Application]:
    result = await session.execute(
        select(Application)
        .where(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
    )
    return list(result.scalars().all())


async def get_application_by_id_for_scoring(
    session: AsyncSession,
    application_id: UUID,
) -> Application | None:
    result = await session.execute(
        select(Application).where(
            Application.id == application_id,
            Application.is_legacy.is_(False),
            Application.job_listing_id.is_not(None),
        )
    )
    return result.scalar_one_or_none()
