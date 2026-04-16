"""add_job_listings

Revision ID: 20260409_0013
Revises: 20260409_0012
Create Date: 2026-04-09 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260409_0013"
down_revision = "20260409_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "required_skills",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "nice_to_have_skills",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("min_experience_years", sa.Integer(), nullable=True),
        sa.Column("max_experience_years", sa.Integer(), nullable=True),
        sa.Column("employment_type", sa.Text(), nullable=True),
        sa.Column(
            "remote",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "source",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column("external_url", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_listings_company_name",
        "job_listings",
        ["company_name"],
        unique=False,
    )
    op.create_index(
        "ix_job_listings_created_at",
        "job_listings",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_job_listings_source",
        "job_listings",
        ["source"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_job_listings_source", table_name="job_listings")
    op.drop_index("ix_job_listings_created_at", table_name="job_listings")
    op.drop_index("ix_job_listings_company_name", table_name="job_listings")
    op.drop_table("job_listings")
