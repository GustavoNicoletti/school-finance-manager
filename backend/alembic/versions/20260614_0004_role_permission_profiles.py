"""create role permission profiles

Revision ID: 20260614_0004
Revises: 20260614_0003
Create Date: 2026-06-14 20:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260614_0004"
down_revision: str | None = "20260614_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "role_permission_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "administrador",
                "diretor",
                "financeiro",
                "secretaria",
                "professor",
                "responsavel",
                name="user_role",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_role_permission_profiles_id"), "role_permission_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_role_permission_profiles_role"), "role_permission_profiles", ["role"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_role_permission_profiles_role"), table_name="role_permission_profiles")
    op.drop_index(op.f("ix_role_permission_profiles_id"), table_name="role_permission_profiles")
    op.drop_table("role_permission_profiles")
