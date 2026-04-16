"""rename_idempotency_processing_to_pending

Revision ID: 20260407_0009
Revises: 20260407_0008
Create Date: 2026-04-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260407_0009"
down_revision = "20260407_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE idempotency_key_status RENAME VALUE 'processing' TO 'pending'"
    )
    op.alter_column(
        "idempotency_keys",
        "status",
        server_default=sa.text("'pending'"),
    )


def downgrade() -> None:
    op.alter_column(
        "idempotency_keys",
        "status",
        server_default=sa.text("'processing'"),
    )
    op.execute(
        "ALTER TYPE idempotency_key_status RENAME VALUE 'pending' TO 'processing'"
    )
