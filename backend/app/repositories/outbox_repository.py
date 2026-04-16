from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox_event import OutboxEvent
from app.schemas.outbox import OutboxEventCreateData


async def create_outbox_event(
    session: AsyncSession,
    outbox_event_data: OutboxEventCreateData,
) -> OutboxEvent:
    outbox_event = OutboxEvent(
        event_name=outbox_event_data.event_name,
        payload=outbox_event_data.payload,
        headers=outbox_event_data.headers,
    )
    session.add(outbox_event)
    await session.flush()
    await session.refresh(outbox_event)
    return outbox_event


async def claim_due_outbox_events(
    session: AsyncSession,
    *,
    batch_size: int,
    max_attempts: int,
    processing_timeout_seconds: int,
) -> list[OutboxEvent]:
    lease_expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=processing_timeout_seconds
    )
    claim_statement = (
        select(OutboxEvent.id)
        .where(
            OutboxEvent.status.in_(("pending", "processing")),
            OutboxEvent.attempts <= max_attempts,
            OutboxEvent.next_attempt_at <= func.now(),
        )
        .order_by(OutboxEvent.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(claim_statement)
    claimed_ids = list(result.scalars().all())
    if not claimed_ids:
        return []

    await session.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id.in_(claimed_ids))
        .values(
            status="processing",
            next_attempt_at=lease_expires_at,
        )
    )

    claimed_events_result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.id.in_(claimed_ids))
        .order_by(OutboxEvent.created_at)
    )
    return list(claimed_events_result.scalars().all())


async def mark_outbox_event_sent(session: AsyncSession, outbox_event_id: UUID) -> None:
    await session.execute(
        update(OutboxEvent)
        .where(
            OutboxEvent.id == outbox_event_id,
            OutboxEvent.status == "processing",
        )
        .values(
            status="sent",
            next_attempt_at=func.now(),
            sent_at=func.now(),
        )
    )


async def schedule_outbox_event_retry(
    session: AsyncSession,
    *,
    outbox_event_id: UUID,
    attempts: int,
    next_attempt_at: datetime,
) -> None:
    await session.execute(
        update(OutboxEvent)
        .where(
            OutboxEvent.id == outbox_event_id,
            OutboxEvent.status == "processing",
        )
        .values(
            status="pending",
            attempts=attempts,
            next_attempt_at=next_attempt_at,
        )
    )


async def mark_outbox_event_failed(
    session: AsyncSession,
    *,
    outbox_event_id: UUID,
    attempts: int,
) -> None:
    await session.execute(
        update(OutboxEvent)
        .where(
            OutboxEvent.id == outbox_event_id,
            OutboxEvent.status == "processing",
        )
        .values(
            status="failed",
            attempts=attempts,
            next_attempt_at=func.now(),
        )
    )


async def count_pending_outbox_events(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(OutboxEvent)
        .where(OutboxEvent.status == "pending")
    )
    return int(result.scalar_one())


async def count_inflight_outbox_events(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(OutboxEvent)
        .where(OutboxEvent.status == "processing")
    )
    return int(result.scalar_one())
