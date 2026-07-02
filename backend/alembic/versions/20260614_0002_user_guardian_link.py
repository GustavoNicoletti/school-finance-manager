"""Add guardian link to users.

Revision ID: 20260614_0002
Revises: 20260614_0001
Create Date: 2026-06-14 00:02:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260614_0002"
down_revision = "20260614_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("guardian_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_users_guardian_id"), "users", ["guardian_id"], unique=False)
    op.create_foreign_key(
        "fk_users_guardian_id_guardians",
        "users",
        "guardians",
        ["guardian_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_guardian_id_guardians", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_guardian_id"), table_name="users")
    op.drop_column("users", "guardian_id")
