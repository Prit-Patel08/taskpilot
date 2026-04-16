"""add_application_limits_and_attempts

Revision ID: 20260416_0017
Revises: 20260409_0016
Create Date: 2026-04-16 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260416_0017"
down_revision = "20260409_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_limits",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("applications_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "date"),
    )
    op.create_index(
        "ix_application_limits_user_id",
        "application_limits",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "application_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_attempts_application_id",
        "application_attempts",
        ["application_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_application_attempts_application_id", table_name="application_attempts")
    op.drop_table("application_attempts")
    op.drop_index("ix_application_limits_user_id", table_name="application_limits")
    op.drop_table("application_limits")
