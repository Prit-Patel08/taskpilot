"""make_applications_job_listing_safe

Revision ID: 20260409_0015
Revises: 20260409_0014
Create Date: 2026-04-09 00:00:00.000000
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260409_0015"
down_revision = "20260409_0014"
branch_labels = None
depends_on = None

LEGACY_JOB_LISTING_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column(
            "is_legacy",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column("applications", "job_listing_id", nullable=True)

    op.execute(
        sa.text(
            """
            UPDATE applications
            SET
                job_listing_id = NULL,
                is_legacy = true
            WHERE job_listing_id = :legacy_job_listing_id
            """
        ).bindparams(legacy_job_listing_id=LEGACY_JOB_LISTING_ID)
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_applications_resume_id ON applications (resume_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_applications_job_listing_id ON applications (job_listing_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_resume_extractions_resume_id ON resume_extractions (resume_id)"
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE applications
            SET job_listing_id = :legacy_job_listing_id
            WHERE is_legacy = true AND job_listing_id IS NULL
            """
        ).bindparams(legacy_job_listing_id=LEGACY_JOB_LISTING_ID)
    )
    op.alter_column("applications", "job_listing_id", nullable=False)
    op.drop_column("applications", "is_legacy")
