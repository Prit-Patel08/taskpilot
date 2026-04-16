"""separate_resumes_from_applications

Revision ID: 20260409_0014
Revises: 20260409_0013
Create Date: 2026-04-09 00:00:00.000000
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260409_0014"
down_revision = "20260409_0013"
branch_labels = None
depends_on = None

LEGACY_JOB_LISTING_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_key", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"], unique=False)
    op.create_index("ix_resumes_created_at", "resumes", ["created_at"], unique=False)

    op.add_column(
        "applications",
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("job_listing_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    application_count = bind.execute(
        sa.text("SELECT count(*) FROM applications")
    ).scalar_one()

    if application_count:
        bind.execute(
            sa.text(
                """
                INSERT INTO job_listings (
                    id,
                    title,
                    company_name,
                    location,
                    description,
                    required_skills,
                    nice_to_have_skills,
                    min_experience_years,
                    max_experience_years,
                    employment_type,
                    remote,
                    source,
                    external_url
                )
                SELECT
                    :legacy_job_listing_id,
                    'Legacy Imported Job',
                    'Legacy',
                    NULL,
                    'Legacy job listing created during applications backfill.',
                    ARRAY['legacy']::text[],
                    ARRAY[]::text[],
                    NULL,
                    NULL,
                    NULL,
                    false,
                    'manual',
                    NULL
                WHERE NOT EXISTS (
                    SELECT 1 FROM job_listings WHERE id = :legacy_job_listing_id
                )
                """
            ),
            {"legacy_job_listing_id": LEGACY_JOB_LISTING_ID},
        )

        bind.execute(
            sa.text(
                """
                INSERT INTO resumes (id, user_id, file_key, created_at, updated_at)
                SELECT
                    applications.id,
                    applications.user_id,
                    CASE
                        WHEN applications.resume_url LIKE 's3://%/%'
                            THEN regexp_replace(applications.resume_url, '^s3://[^/]+/', '')
                        ELSE applications.resume_url
                    END,
                    applications.created_at,
                    applications.updated_at
                FROM applications
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM resumes
                    WHERE resumes.id = applications.id
                )
                """
            )
        )

        bind.execute(
            sa.text(
                """
                UPDATE applications
                SET resume_id = applications.id
                WHERE resume_id IS NULL
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE applications
                SET job_listing_id = :legacy_job_listing_id
                WHERE job_listing_id IS NULL
                """
            ),
            {"legacy_job_listing_id": LEGACY_JOB_LISTING_ID},
        )

    op.create_index("ix_applications_resume_id", "applications", ["resume_id"], unique=False)
    op.create_index(
        "ix_applications_job_listing_id",
        "applications",
        ["job_listing_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_applications_resume_id_resumes",
        "applications",
        "resumes",
        ["resume_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_applications_job_listing_id_job_listings",
        "applications",
        "job_listings",
        ["job_listing_id"],
        ["id"],
    )
    op.alter_column("applications", "resume_id", nullable=False)
    op.alter_column("applications", "job_listing_id", nullable=False)

    op.execute(
        """
        DO $$
        DECLARE fk_name text;
        BEGIN
            SELECT tc.constraint_name
            INTO fk_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_name = 'resume_extractions'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND kcu.column_name = 'resume_id'
            LIMIT 1;

            IF fk_name IS NOT NULL THEN
                EXECUTE format(
                    'ALTER TABLE resume_extractions DROP CONSTRAINT %I',
                    fk_name
                );
            END IF;
        END$$;
        """
    )
    op.create_foreign_key(
        "fk_resume_extractions_resume_id_resumes",
        "resume_extractions",
        "resumes",
        ["resume_id"],
        ["id"],
    )

    # TODO: drop legacy applications.resume_url once all readers and in-flight jobs are migrated.


def downgrade() -> None:
    op.drop_constraint(
        "fk_resume_extractions_resume_id_resumes",
        "resume_extractions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_resume_extractions_resume_id_applications",
        "resume_extractions",
        "applications",
        ["resume_id"],
        ["id"],
    )
    op.drop_constraint(
        "fk_applications_job_listing_id_job_listings",
        "applications",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_applications_resume_id_resumes",
        "applications",
        type_="foreignkey",
    )
    op.drop_index("ix_applications_job_listing_id", table_name="applications")
    op.drop_index("ix_applications_resume_id", table_name="applications")
    op.drop_column("applications", "job_listing_id")
    op.drop_column("applications", "resume_id")
    op.drop_index("ix_resumes_created_at", table_name="resumes")
    op.drop_index("ix_resumes_user_id", table_name="resumes")
    op.drop_table("resumes")
