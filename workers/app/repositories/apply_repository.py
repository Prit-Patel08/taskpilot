from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, column, insert, select, table, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

applications_table = table(
    "applications",
    column("id", PGUUID(as_uuid=True)),
    column("user_id", PGUUID(as_uuid=True)),
    column("status"),
    column("is_legacy"),
    column("updated_at"),
)
application_limits_table = table(
    "application_limits",
    column("user_id", PGUUID(as_uuid=True)),
    column("date", Date),
    column("applications_count"),
)
application_attempts_table = table(
    "application_attempts",
    column("id", PGUUID(as_uuid=True)),
    column("application_id", PGUUID(as_uuid=True)),
    column("status"),
    column("scheduled_at"),
    column("created_at"),
)
outbox_events_table = table(
    "outbox_events",
    column("id", PGUUID(as_uuid=True)),
    column("event_name"),
    column("payload", JSONB),
    column("headers", JSONB),
    column("status"),
    column("attempts"),
    column("created_at"),
    column("next_attempt_at"),
    column("sent_at"),
)


@dataclass(frozen=True)
class ApplyRequestApplication:
    id: UUID
    user_id: UUID
    status: str
    is_legacy: bool


@dataclass(frozen=True)
class ApplicationAttemptRecord:
    id: UUID
    application_id: UUID
    status: str
    scheduled_at: datetime | None
    created_at: datetime


async def get_application_for_apply_request(
    session: AsyncSession,
    application_id: UUID,
) -> ApplyRequestApplication | None:
    result = await session.execute(
        select(
            applications_table.c.id,
            applications_table.c.user_id,
            applications_table.c.status,
            applications_table.c.is_legacy,
        ).where(
            applications_table.c.id == application_id,
            applications_table.c.is_legacy.is_(False),
        )
    )
    row = result.one_or_none()
    if row is None:
        return None
    return ApplyRequestApplication(
        id=row.id,
        user_id=row.user_id,
        status=str(row.status),
        is_legacy=bool(row.is_legacy),
    )


async def has_already_applied(
    session: AsyncSession,
    application_id: UUID,
) -> bool:
    return await get_application_attempt(session, application_id) is not None


async def get_application_attempt(
    session: AsyncSession,
    application_id: UUID,
) -> ApplicationAttemptRecord | None:
    result = await session.execute(
        select(
            application_attempts_table.c.id,
            application_attempts_table.c.application_id,
            application_attempts_table.c.status,
            application_attempts_table.c.scheduled_at,
            application_attempts_table.c.created_at,
        ).where(application_attempts_table.c.application_id == application_id)
    )
    row = result.one_or_none()
    if row is None:
        return None
    return ApplicationAttemptRecord(
        id=row.id,
        application_id=row.application_id,
        status=str(row.status),
        scheduled_at=row.scheduled_at,
        created_at=row.created_at,
    )


async def get_daily_count(
    session: AsyncSession,
    user_id: UUID,
    *,
    on_date: date,
) -> int:
    result = await session.execute(
        select(application_limits_table.c.applications_count).where(
            application_limits_table.c.user_id == user_id,
            application_limits_table.c.date == on_date,
        )
    )
    row = result.one_or_none()
    if row is None:
        return 0
    return int(row.applications_count)


async def increment_daily_limit(
    session: AsyncSession,
    user_id: UUID,
    *,
    on_date: date,
) -> int:
    statement = (
        pg_insert(application_limits_table)
        .values(
            user_id=user_id,
            date=on_date,
            applications_count=1,
        )
        .on_conflict_do_update(
            index_elements=[
                application_limits_table.c.user_id,
                application_limits_table.c.date,
            ],
            set_={
                "applications_count": application_limits_table.c.applications_count + 1,
            },
        )
        .returning(application_limits_table.c.applications_count)
    )
    result = await session.execute(statement)
    return int(result.scalar_one())


async def create_application_attempt(
    session: AsyncSession,
    *,
    application_id: UUID,
    status: str,
    scheduled_at: datetime,
    created_at: datetime,
) -> bool:
    statement = (
        pg_insert(application_attempts_table)
        .values(
            id=uuid4(),
            application_id=application_id,
            status=status,
            scheduled_at=scheduled_at,
            created_at=created_at,
        )
        .on_conflict_do_nothing(index_elements=[application_attempts_table.c.application_id])
    )
    result = await session.execute(statement)
    return bool(result.rowcount and result.rowcount > 0)


async def mark_application_rate_limited(
    session: AsyncSession,
    application_id: UUID,
) -> bool:
    result = await session.execute(
        update(applications_table)
        .where(applications_table.c.id == application_id)
        .values(
            status="rate_limited",
            updated_at=datetime.now(UTC),
        )
    )
    return bool(result.rowcount and result.rowcount > 0)


async def enqueue_apply_execute_event(
    session: AsyncSession,
    *,
    payload: dict,
    headers: dict,
    created_at: datetime,
) -> None:
    await session.execute(
        insert(outbox_events_table).values(
            id=uuid4(),
            event_name="apply.execute",
            payload=payload,
            headers=headers,
            status="pending",
            attempts=0,
            created_at=created_at,
            next_attempt_at=created_at,
            sent_at=None,
        )
    )
