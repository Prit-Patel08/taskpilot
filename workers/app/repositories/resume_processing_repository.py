from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import column, exists, insert, select, table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

resumes_table = table(
    "resumes",
    column("id", PGUUID(as_uuid=True)),
    column("user_id", PGUUID(as_uuid=True)),
    column("file_key"),
    column("created_at"),
    column("updated_at"),
)
resume_extractions_table = table(
    "resume_extractions",
    column("id", PGUUID(as_uuid=True)),
    column("resume_id", PGUUID(as_uuid=True)),
    column("parsed_json", JSONB),
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
class ResumeRecord:
    id: UUID
    user_id: UUID
    file_key: str


async def get_locked_resume(
    session: AsyncSession,
    *,
    resume_id: UUID,
) -> ResumeRecord | None:
    result = await session.execute(
        select(
            resumes_table.c.id,
            resumes_table.c.user_id,
            resumes_table.c.file_key,
        )
        .where(resumes_table.c.id == resume_id)
        .with_for_update()
    )
    row = result.one_or_none()
    if row is None:
        return None
    return ResumeRecord(
        id=row.id,
        user_id=row.user_id,
        file_key=str(row.file_key),
    )


async def resume_extraction_exists(
    session: AsyncSession,
    *,
    resume_id: UUID,
) -> bool:
    result = await session.execute(
        select(exists().where(resume_extractions_table.c.resume_id == resume_id))
    )
    return bool(result.scalar())


async def insert_resume_extraction(
    session: AsyncSession,
    *,
    resume_id: UUID,
    parsed_json: dict,
    created_at: datetime,
) -> UUID:
    extraction_id = uuid4()
    await session.execute(
        insert(resume_extractions_table).values(
            id=extraction_id,
            resume_id=resume_id,
            parsed_json=parsed_json,
            created_at=created_at,
        )
    )
    return extraction_id


async def enqueue_ats_analyze_event(
    session: AsyncSession,
    *,
    payload: dict,
    headers: dict,
    created_at: datetime,
) -> None:
    await session.execute(
        insert(outbox_events_table).values(
            id=uuid4(),
            event_name="ats.analyze",
            payload=payload,
            headers=headers,
            status="pending",
            attempts=0,
            created_at=created_at,
            next_attempt_at=created_at,
            sent_at=None,
        )
    )
