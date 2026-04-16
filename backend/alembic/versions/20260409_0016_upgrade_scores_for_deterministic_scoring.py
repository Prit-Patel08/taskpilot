"""upgrade_scores_for_deterministic_scoring

Revision ID: 20260409_0016
Revises: 20260409_0015
Create Date: 2026-04-09 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260409_0016"
down_revision = "20260409_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("scores", "score_breakdown", new_column_name="breakdown")
    op.add_column(
        "scores",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )


def downgrade() -> None:
    op.drop_column("scores", "version")
    op.alter_column("scores", "breakdown", new_column_name="score_breakdown")
