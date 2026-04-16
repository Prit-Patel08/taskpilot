"""add_resume_extractions

Revision ID: 20260409_0012
Revises: 20260407_0011
Create Date: 2026-04-09 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260409_0012"
down_revision = "20260407_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "parsed_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["resume_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resume_extractions_resume_id",
        "resume_extractions",
        ["resume_id"],
        unique=True,
    )
    op.create_index(
        "ix_resume_extractions_created_at",
        "resume_extractions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_resume_extractions_created_at", table_name="resume_extractions")
    op.drop_index("ix_resume_extractions_resume_id", table_name="resume_extractions")
    op.drop_table("resume_extractions")
