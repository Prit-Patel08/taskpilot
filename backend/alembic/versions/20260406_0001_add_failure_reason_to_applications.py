"""add_failure_reason_to_applications

Revision ID: 20260406_0001
Revises: 20260406_0000
Create Date: 2026-04-06 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260406_0001"
down_revision = "20260406_0000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("failure_reason", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("applications", "failure_reason")
