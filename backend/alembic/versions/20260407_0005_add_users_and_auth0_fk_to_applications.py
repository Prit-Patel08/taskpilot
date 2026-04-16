"""add_users_and_auth0_fk_to_applications

Revision ID: 20260407_0005
Revises: 20260407_0004
Create Date: 2026-04-07 00:00:00.000000
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260407_0005"
down_revision = "20260407_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "auth_provider",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'auth0'"),
        ),
        sa.Column("auth_subject", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
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
    op.create_index("ix_users_auth_subject", "users", ["auth_subject"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.add_column(
        "applications",
        sa.Column("user_id_uuid", postgresql.UUID(as_uuid=True), nullable=True),
    )

    bind = op.get_bind()
    distinct_user_ids = bind.execute(
        sa.text(
            """
            SELECT DISTINCT user_id
            FROM applications
            WHERE user_id IS NOT NULL
            """
        )
    ).fetchall()

    now = datetime.now(timezone.utc)
    for row in distinct_user_ids:
        bind.execute(
            sa.text(
                """
                INSERT INTO users (id, auth_provider, auth_subject, email, created_at, updated_at)
                VALUES (:id, 'auth0', :auth_subject, NULL, :created_at, :updated_at)
                ON CONFLICT (auth_subject) DO NOTHING
                """
            ),
            {
                "id": uuid.uuid4(),
                "auth_subject": row.user_id,
                "created_at": now,
                "updated_at": now,
            },
        )

    bind.execute(
        sa.text(
            """
            UPDATE applications AS applications
            SET user_id_uuid = users.id
            FROM users
            WHERE applications.user_id = users.auth_subject
            """
        )
    )

    op.alter_column("applications", "user_id_uuid", nullable=False)
    op.drop_index("ix_applications_user_id", table_name="applications")
    op.drop_column("applications", "user_id")
    op.alter_column("applications", "user_id_uuid", new_column_name="user_id")
    op.create_foreign_key(
        "fk_applications_user_id",
        "applications",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"], unique=False)


def downgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("user_id_legacy", sa.String(length=255), nullable=True),
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE applications AS applications
            SET user_id_legacy = users.auth_subject
            FROM users
            WHERE applications.user_id = users.id
            """
        )
    )

    op.alter_column("applications", "user_id_legacy", nullable=False)
    op.drop_index("ix_applications_user_id", table_name="applications")
    op.drop_constraint("fk_applications_user_id", "applications", type_="foreignkey")
    op.drop_column("applications", "user_id")
    op.alter_column("applications", "user_id_legacy", new_column_name="user_id")
    op.create_index("ix_applications_user_id", "applications", ["user_id"], unique=False)

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_auth_subject", table_name="users")
    op.drop_table("users")
