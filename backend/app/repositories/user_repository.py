from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_auth_subject(
    session: AsyncSession,
    auth_subject: str,
) -> User | None:
    result = await session.execute(
        select(User).where(User.auth_subject == auth_subject)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    *,
    auth_subject: str,
    email: str | None,
) -> User:
    user = User(
        auth_provider="auth0",
        auth_subject=auth_subject,
        email=email,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def update_user_email(
    session: AsyncSession,
    *,
    user: User,
    email: str,
) -> None:
    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(email=email)
    )
    await session.refresh(user)
