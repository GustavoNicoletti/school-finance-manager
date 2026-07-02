"""Add financial constraints and tuition uniqueness.

Revision ID: 20260614_0003
Revises: 20260614_0002
Create Date: 2026-06-14 00:03:00.000000
"""

from alembic import op


revision = "20260614_0003"
down_revision = "20260614_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint("ck_receivables_amount_positive", "receivables", "amount > 0")
    op.create_check_constraint("ck_receivables_paid_amount_non_negative", "receivables", "paid_amount >= 0")
    op.create_check_constraint("ck_receivables_paid_amount_lte_amount", "receivables", "paid_amount <= amount")
    op.create_check_constraint("ck_payables_amount_positive", "payables", "amount > 0")
    op.execute(
        """
        CREATE UNIQUE INDEX ux_receivables_tuition_student_month_active
        ON receivables (student_id, EXTRACT(YEAR FROM due_date), EXTRACT(MONTH FROM due_date), type)
        WHERE type = 'mensalidade' AND status <> 'cancelado'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_receivables_tuition_student_month_active")
    op.drop_constraint("ck_payables_amount_positive", "payables", type_="check")
    op.drop_constraint("ck_receivables_paid_amount_lte_amount", "receivables", type_="check")
    op.drop_constraint("ck_receivables_paid_amount_non_negative", "receivables", type_="check")
    op.drop_constraint("ck_receivables_amount_positive", "receivables", type_="check")
