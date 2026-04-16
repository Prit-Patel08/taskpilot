from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKey, IdempotencyStatus


async def get_with_lock(
    session: AsyncSession,
    *,
    user_id: UUID,
    idempotency_key: str,
) -> IdempotencyKey | None:
    result = await session.execute(
        select(IdempotencyKey)
        .where(
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.idempotency_key == idempotency_key,
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def create_key(
    session: AsyncSession,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_hash: str,
    locked_at: datetime | None = None,
) -> IdempotencyKey | None:
    record = IdempotencyKey(
        user_id=user_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        status=IdempotencyStatus.PENDING,
        locked_at=locked_at or datetime.now(UTC),
    )
    try:
        async with session.begin_nested():
            session.add(record)
            await session.flush()
            await session.refresh(record)
    except IntegrityError:
        return None
    return record


async def update_to_pending(
    session: AsyncSession,
    *,
    idempotency_key_id: UUID,
    locked_at: datetime,
) -> None:
    await session.execute(
        update(IdempotencyKey)
        .where(IdempotencyKey.id == idempotency_key_id)
        .values(
            status=IdempotencyStatus.PENDING,
            error_json=None,
            locked_at=locked_at,
            updated_at=func.now(),
        )
    )


async def update_locked_at(
    session: AsyncSession,
    *,
    idempotency_key_id: UUID,
    locked_at: datetime,
) -> None:
    await session.execute(
        update(IdempotencyKey)
        .where(IdempotencyKey.id == idempotency_key_id)
        .values(
            locked_at=locked_at,
            updated_at=func.now(),
        )
    )


async def update_to_completed(
    session: AsyncSession,
    *,
    idempotency_key_id: UUID,
    response_status: int | None,
    response_json: dict[str, Any],
    resource_id: UUID | None,
) -> None:
    await session.execute(
        update(IdempotencyKey)
        .where(IdempotencyKey.id == idempotency_key_id)
        .values(
            status=IdempotencyStatus.COMPLETED,
            response_status=response_status,
            response_json=response_json,
            resource_id=resource_id,
            error_json=None,
            locked_at=None,
            updated_at=func.now(),
        )
    )


async def update_to_failed(
    session: AsyncSession,
    *,
    idempotency_key_id: UUID,
    error_json: dict[str, Any],
) -> None:
    await session.execute(
        update(IdempotencyKey)
        .where(IdempotencyKey.id == idempotency_key_id)
        .values(
            status=IdempotencyStatus.FAILED,
            error_json=error_json,
            locked_at=None,
            updated_at=func.now(),
        )
    )


async def get_idempotency_key_for_update(
    session: AsyncSession,
    *,
    user_id: UUID,
    idempotency_key: str,
) -> IdempotencyKey | None:
    return await get_with_lock(
        session,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )


async def create_idempotency_key(
    session: AsyncSession,
    *,
    user_id: UUID,
    idempotency_key: str,
    request_hash: str,
) -> IdempotencyKey:
    record = await create_key(
        session,
        user_id=user_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if record is None:
        raise IntegrityError("Idempotency key already exists.", params=None, orig=None)
    return record


async def store_idempotency_response(
    session: AsyncSession,
    *,
    idempotency_key_id: UUID,
    response_status: int,
    response_body: dict[str, Any],
    resource_id: UUID | None,
) -> None:
    await update_to_completed(
        session,
        idempotency_key_id=idempotency_key_id,
        response_status=response_status,
        response_json=response_body,
        resource_id=resource_id,
    )
