"""add_next_attempt_at_to_outbox_events

Revision ID: 20260407_0003
Revises: 20260407_0002
Create Date: 2026-04-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260407_0003"
down_revision = "20260407_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_outbox_events_status_next_attempt_at_created_at",
        "outbox_events",
        ["status", "next_attempt_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outbox_events_status_next_attempt_at_created_at",
        table_name="outbox_events",
    )
    op.drop_column("outbox_events", "next_attempt_at")
