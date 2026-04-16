"""add_application_processing_heartbeat_fields

Revision ID: 20260407_0004
Revises: 20260407_0003
Create Date: 2026-04-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260407_0004"
down_revision = "20260407_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "applications",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_applications_status_last_heartbeat_at",
        "applications",
        ["status", "last_heartbeat_at"],
    )
    op.execute(
        """
        UPDATE applications
        SET processing_started_at = updated_at,
            last_heartbeat_at = updated_at
        WHERE status = 'processing'
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_applications_status_last_heartbeat_at",
        table_name="applications",
    )
    op.drop_column("applications", "last_heartbeat_at")
    op.drop_column("applications", "processing_started_at")
    op.drop_column("applications", "retry_count")
