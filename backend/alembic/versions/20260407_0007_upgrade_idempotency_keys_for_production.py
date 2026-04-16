"""upgrade_idempotency_keys_for_production

Revision ID: 20260407_0007
Revises: 20260407_0006
Create Date: 2026-04-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260407_0007"
down_revision = "20260407_0006"
branch_labels = None
depends_on = None


idempotency_status = postgresql.ENUM(
    "processing",
    "completed",
    "failed",
    name="idempotency_key_status",
)


def upgrade() -> None:
    idempotency_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "idempotency_keys",
        sa.Column(
            "status",
            idempotency_status,
            nullable=False,
            server_default="processing",
        ),
    )
    op.add_column(
        "idempotency_keys",
        sa.Column(
            "response_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "idempotency_keys",
        sa.Column(
            "error_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "idempotency_keys",
        sa.Column(
            "locked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE idempotency_keys
        SET
            response_json = response_body,
            status = CASE
                WHEN response_body IS NOT NULL THEN 'completed'::idempotency_key_status
                ELSE 'failed'::idempotency_key_status
            END,
            error_json = CASE
                WHEN response_body IS NULL THEN jsonb_build_object(
                    'error_type', 'LEGACY_INCOMPLETE_RECORD',
                    'message', 'Legacy idempotency record migrated without stored response.'
                )
                ELSE NULL
            END
        """
    )

    op.drop_column("idempotency_keys", "response_body")

    op.create_index(
        "ix_idempotency_keys_user_id",
        "idempotency_keys",
        ["user_id"],
    )
    op.create_index(
        "ix_idempotency_keys_idempotency_key",
        "idempotency_keys",
        ["idempotency_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_idempotency_key", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_user_id", table_name="idempotency_keys")

    op.add_column(
        "idempotency_keys",
        sa.Column(
            "response_body",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE idempotency_keys
        SET response_body = response_json
        """
    )

    op.drop_column("idempotency_keys", "locked_at")
    op.drop_column("idempotency_keys", "error_json")
    op.drop_column("idempotency_keys", "response_json")
    op.drop_column("idempotency_keys", "status")

    idempotency_status.drop(op.get_bind(), checkfirst=True)
