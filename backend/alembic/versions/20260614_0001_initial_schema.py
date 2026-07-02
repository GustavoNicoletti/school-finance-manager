"""initial schema

Revision ID: 20260614_0001
Revises:
Create Date: 2026-06-14 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260614_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_role = postgresql.ENUM(
    "administrador",
    "diretor",
    "financeiro",
    "secretaria",
    "professor",
    "responsavel",
    name="user_role",
    create_type=False,
)
student_status = postgresql.ENUM("ativo", "inativo", "transferido", name="student_status", create_type=False)
payment_status = postgresql.ENUM("pendente", "pago", "atrasado", "cancelado", name="payment_status", create_type=False)
payable_status = postgresql.ENUM("pendente", "pago", "atrasado", "cancelado", name="payable_status", create_type=False)
receivable_type = postgresql.ENUM("mensalidade", "taxa_extra", "material", "outro", name="receivable_type", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    student_status.create(bind, checkfirst=True)
    payment_status.create(bind, checkfirst=True)
    payable_status.create(bind, checkfirst=True)
    receivable_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("class_name", sa.String(length=80), nullable=True),
        sa.Column("status", student_status, nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("medical_information", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_students_full_name"), "students", ["full_name"], unique=False)
    op.create_index(op.f("ix_students_id"), "students", ["id"], unique=False)

    op.create_table(
        "guardians",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("cpf", sa.String(length=14), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("kinship", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpf"),
    )
    op.create_index(op.f("ix_guardians_full_name"), "guardians", ["full_name"], unique=False)
    op.create_index(op.f("ix_guardians_id"), "guardians", ["id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("previous_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)

    op.create_table(
        "payables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("status", payable_status, nullable=False),
        sa.Column("supplier", sa.String(length=150), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payables_due_date"), "payables", ["due_date"], unique=False)
    op.create_index(op.f("ix_payables_id"), "payables", ["id"], unique=False)

    op.create_table(
        "receivables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=180), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("type", receivable_type, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_receivables_due_date"), "receivables", ["due_date"], unique=False)
    op.create_index(op.f("ix_receivables_id"), "receivables", ["id"], unique=False)
    op.create_index(op.f("ix_receivables_student_id"), "receivables", ["student_id"], unique=False)

    op.create_table(
        "student_guardians",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("guardian_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["guardian_id"], ["guardians.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("student_id", "guardian_id"),
    )


def downgrade() -> None:
    op.drop_table("student_guardians")
    op.drop_index(op.f("ix_receivables_student_id"), table_name="receivables")
    op.drop_index(op.f("ix_receivables_id"), table_name="receivables")
    op.drop_index(op.f("ix_receivables_due_date"), table_name="receivables")
    op.drop_table("receivables")
    op.drop_index(op.f("ix_payables_id"), table_name="payables")
    op.drop_index(op.f("ix_payables_due_date"), table_name="payables")
    op.drop_table("payables")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_guardians_id"), table_name="guardians")
    op.drop_index(op.f("ix_guardians_full_name"), table_name="guardians")
    op.drop_table("guardians")
    op.drop_index(op.f("ix_students_id"), table_name="students")
    op.drop_index(op.f("ix_students_full_name"), table_name="students")
    op.drop_table("students")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    receivable_type.drop(op.get_bind(), checkfirst=True)
    payable_status.drop(op.get_bind(), checkfirst=True)
    payment_status.drop(op.get_bind(), checkfirst=True)
    student_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
