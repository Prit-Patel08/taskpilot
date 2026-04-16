from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import (
    create_user,
    get_user_by_auth_subject,
    update_user_email,
)


async def get_or_create_user(
    session: AsyncSession,
    *,
    auth_subject: str,
    email: str | None,
) -> User:
    existing_user = await get_user_by_auth_subject(session, auth_subject)
    if existing_user is not None:
        if email and existing_user.email != email:
            await update_user_email(
                session,
                user=existing_user,
                email=email,
            )
            await session.commit()
        else:
            await session.commit()
        return existing_user

    try:
        user = await create_user(
            session,
            auth_subject=auth_subject,
            email=email,
        )
        await session.commit()
        return user
    except IntegrityError:
        await session.rollback()
        user = await get_user_by_auth_subject(session, auth_subject)
        if user is None:
            raise
        if email and user.email != email:
            await update_user_email(
                session,
                user=user,
                email=email,
            )
            await session.commit()
        return user
