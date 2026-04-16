from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import column, insert, select, table, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

applications_table = table(
    "applications",
    column("id", PGUUID(as_uuid=True)),
    column("user_id", PGUUID(as_uuid=True)),
    column("status"),
    column("resume_id", PGUUID(as_uuid=True)),
    column("job_listing_id", PGUUID(as_uuid=True)),
    column("is_legacy"),
    column("updated_at"),
)
resume_extractions_table = table(
    "resume_extractions",
    column("id", PGUUID(as_uuid=True)),
    column("resume_id", PGUUID(as_uuid=True)),
    column("parsed_json", JSONB),
    column("created_at"),
)
job_listings_table = table(
    "job_listings",
    column("id", PGUUID(as_uuid=True)),
    column("title"),
    column("company_name"),
    column("location"),
    column("description"),
    column("required_skills"),
    column("nice_to_have_skills"),
    column("min_experience_years"),
    column("max_experience_years"),
    column("employment_type"),
    column("remote"),
    column("source"),
    column("external_url"),
    column("created_at"),
    column("updated_at"),
)
scores_table = table(
    "scores",
    column("id", PGUUID(as_uuid=True)),
    column("application_id", PGUUID(as_uuid=True)),
    column("score"),
    column("breakdown", JSONB),
    column("version"),
    column("created_at"),
    column("updated_at"),
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
class ScoringApplication:
    id: UUID
    user_id: UUID
    status: str
    resume_id: UUID
    job_listing_id: UUID
    is_legacy: bool


@dataclass(frozen=True)
class ExistingScore:
    id: UUID
    application_id: UUID
    score: int
    breakdown: dict
    version: int


async def get_application_by_id_for_scoring(
    session: AsyncSession,
    application_id: UUID,
) -> ScoringApplication | None:
    result = await session.execute(
        select(
            applications_table.c.id,
            applications_table.c.user_id,
            applications_table.c.status,
            applications_table.c.resume_id,
            applications_table.c.job_listing_id,
            applications_table.c.is_legacy,
        )
        .where(
            applications_table.c.id == application_id,
            applications_table.c.is_legacy.is_(False),
            applications_table.c.job_listing_id.is_not(None),
        )
    )
    row = result.one_or_none()
    if row is None:
        return None
    return ScoringApplication(
        id=row.id,
        user_id=row.user_id,
        status=str(row.status),
        resume_id=row.resume_id,
        job_listing_id=row.job_listing_id,
        is_legacy=bool(row.is_legacy),
    )


async def get_existing_score(
    session: AsyncSession,
    application_id: UUID,
) -> ExistingScore | None:
    result = await session.execute(
        select(
            scores_table.c.id,
            scores_table.c.application_id,
            scores_table.c.score,
            scores_table.c.breakdown,
            scores_table.c.version,
        ).where(scores_table.c.application_id == application_id)
    )
    row = result.one_or_none()
    if row is None:
        return None
    return ExistingScore(
        id=row.id,
        application_id=row.application_id,
        score=int(row.score),
        breakdown=dict(row.breakdown),
        version=int(row.version),
    )


async def get_resume_extraction(
    session: AsyncSession,
    resume_id: UUID,
) -> dict | None:
    result = await session.execute(
        select(resume_extractions_table.c.parsed_json).where(
            resume_extractions_table.c.resume_id == resume_id
        )
    )
    row = result.one_or_none()
    return dict(row.parsed_json) if row is not None else None


async def get_job_listing(
    session: AsyncSession,
    job_listing_id: UUID,
) -> dict | None:
    result = await session.execute(
        select(
            job_listings_table.c.id,
            job_listings_table.c.title,
            job_listings_table.c.company_name,
            job_listings_table.c.location,
            job_listings_table.c.description,
            job_listings_table.c.required_skills,
            job_listings_table.c.nice_to_have_skills,
            job_listings_table.c.min_experience_years,
            job_listings_table.c.max_experience_years,
            job_listings_table.c.employment_type,
            job_listings_table.c.remote,
            job_listings_table.c.source,
            job_listings_table.c.external_url,
        ).where(job_listings_table.c.id == job_listing_id)
    )
    row = result.one_or_none()
    if row is None:
        return None
    return dict(row._mapping)


async def mark_application_scoring(
    session: AsyncSession,
    application_id: UUID,
) -> bool:
    result = await session.execute(
        update(applications_table)
        .where(
            applications_table.c.id == application_id,
            applications_table.c.status == "resume_processed",
        )
        .values(
            status="scoring",
            updated_at=datetime.now(UTC),
        )
    )
    return bool(result.rowcount and result.rowcount > 0)


async def mark_application_completed(
    session: AsyncSession,
    application_id: UUID,
) -> bool:
    result = await session.execute(
        update(applications_table)
        .where(
            applications_table.c.id == application_id,
            applications_table.c.status.in_(("resume_processed", "scoring")),
        )
        .values(
            status="completed",
            updated_at=datetime.now(UTC),
        )
    )
    return bool(result.rowcount and result.rowcount > 0)


async def create_score(
    session: AsyncSession,
    *,
    application_id: UUID,
    score: int,
    breakdown: dict,
    version: int,
    created_at: datetime,
) -> bool:
    statement = (
        pg_insert(scores_table)
        .values(
            id=uuid4(),
            application_id=application_id,
            score=score,
            breakdown=breakdown,
            version=version,
            created_at=created_at,
            updated_at=created_at,
        )
        .on_conflict_do_nothing(index_elements=[scores_table.c.application_id])
    )
    result = await session.execute(statement)
    return bool(result.rowcount and result.rowcount > 0)


async def enqueue_apply_requested_event(
    session: AsyncSession,
    *,
    payload: dict,
    headers: dict,
    created_at: datetime,
) -> None:
    await session.execute(
        insert(outbox_events_table).values(
            id=uuid4(),
            event_name="apply.requested",
            payload=payload,
            headers=headers,
            status="pending",
            attempts=0,
            created_at=created_at,
            next_attempt_at=created_at,
            sent_at=None,
        )
    )
