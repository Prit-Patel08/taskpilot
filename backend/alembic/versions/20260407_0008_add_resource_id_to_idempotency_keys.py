"""add_resource_id_to_idempotency_keys

Revision ID: 20260407_0008
Revises: 20260407_0007
Create Date: 2026-04-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260407_0008"
down_revision = "20260407_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "idempotency_keys",
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_idempotency_keys_resource_id_applications",
        "idempotency_keys",
        "applications",
        ["resource_id"],
        ["id"],
    )
    op.create_index(
        "ix_idempotency_keys_resource_id",
        "idempotency_keys",
        ["resource_id"],
    )
    op.execute(
        """
        UPDATE idempotency_keys
        SET resource_id = NULLIF(response_json ->> 'application_id', '')::uuid
        WHERE response_json IS NOT NULL
          AND response_json ? 'application_id'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_resource_id", table_name="idempotency_keys")
    op.drop_constraint(
        "fk_idempotency_keys_resource_id_applications",
        "idempotency_keys",
        type_="foreignkey",
    )
    op.drop_column("idempotency_keys", "resource_id")
