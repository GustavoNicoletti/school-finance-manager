from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, distinct, func, or_
from sqlalchemy.orm import Session

from app.models.finance import Payable, PaymentStatus, Receivable
from app.models.student import Student, StudentStatus
from app.schemas.dashboard import DashboardSummary


@dataclass
class DashboardSnapshot:
    reference_month: str
    period_start: date
    period_end: date
    reference_date: date
    total_active_students: int
    expected_revenue_month: Decimal
    received_revenue_month: Decimal
    expenses_month: Decimal
    pending_expenses_month: Decimal
    monthly_balance: Decimal
    overdue_students_count: int
    total_overdue_amount: Decimal
    average_cost_per_student: Decimal
    cash_cost_per_student: Decimal


def _decimal(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(value).quantize(Decimal("0.01"))


def _month_range(reference_date: date) -> tuple[date, date]:
    first_day = reference_date.replace(day=1)
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1)
    return first_day, next_month


def _month_end(next_month_start: date) -> date:
    return next_month_start.fromordinal(next_month_start.toordinal() - 1)


def _snapshot_reference_date(month_start: date, month_end: date, today: date) -> date:
    current_month_start = today.replace(day=1)
    if month_start == current_month_start:
        return today
    return month_end


def _previous_month(month_start: date) -> date:
    return month_start.fromordinal(month_start.toordinal() - 1).replace(day=1)


def _build_snapshot(db: Session, month_reference: date, today: date) -> DashboardSnapshot:
    month_start, next_month_start = _month_range(month_reference)
    month_end = _month_end(next_month_start)
    overdue_reference_date = _snapshot_reference_date(month_start, month_end, today)

    active_students = (
        db.query(func.count(Student.id))
        .filter(Student.status == StudentStatus.ACTIVE)
        .scalar()
        or 0
    )

    expected_revenue = (
        db.query(func.coalesce(func.sum(Receivable.amount), 0))
        .filter(
            Receivable.due_date >= month_start,
            Receivable.due_date < next_month_start,
            Receivable.status != PaymentStatus.CANCELED,
        )
        .scalar()
    )

    received_revenue = (
        db.query(func.coalesce(func.sum(Receivable.paid_amount), 0))
        .filter(
            Receivable.payment_date >= month_start,
            Receivable.payment_date < next_month_start,
            Receivable.status == PaymentStatus.PAID,
        )
        .scalar()
    )

    expenses = (
        db.query(func.coalesce(func.sum(Payable.amount), 0))
        .filter(
            Payable.payment_date >= month_start,
            Payable.payment_date < next_month_start,
            Payable.status == PaymentStatus.PAID,
        )
        .scalar()
    )

    pending_expenses = (
        db.query(func.coalesce(func.sum(Payable.amount), 0))
        .filter(
            Payable.due_date >= month_start,
            Payable.due_date < next_month_start,
            Payable.status != PaymentStatus.PAID,
            Payable.status != PaymentStatus.CANCELED,
        )
        .scalar()
    )

    operating_expenses = (
        db.query(func.coalesce(func.sum(Payable.amount), 0))
        .filter(
            Payable.due_date >= month_start,
            Payable.due_date < next_month_start,
            Payable.status != PaymentStatus.CANCELED,
        )
        .scalar()
    )

    overdue_filter = and_(
        Receivable.status != PaymentStatus.CANCELED,
        Receivable.status != PaymentStatus.PAID,
        or_(Receivable.status == PaymentStatus.OVERDUE, Receivable.due_date < overdue_reference_date),
    )

    overdue_students = db.query(func.count(distinct(Receivable.student_id))).filter(overdue_filter).scalar() or 0
    total_overdue = (
        db.query(func.coalesce(func.sum(Receivable.amount - Receivable.paid_amount), 0))
        .filter(overdue_filter)
        .scalar()
    )

    expenses_decimal = _decimal(expenses)
    operating_expenses_decimal = _decimal(operating_expenses)
    received_decimal = _decimal(received_revenue)
    average_cost = operating_expenses_decimal / active_students if active_students else Decimal("0.00")
    cash_cost = expenses_decimal / active_students if active_students else Decimal("0.00")

    return DashboardSnapshot(
        reference_month=month_start.strftime("%Y-%m"),
        period_start=month_start,
        period_end=month_end,
        reference_date=overdue_reference_date,
        total_active_students=active_students,
        expected_revenue_month=_decimal(expected_revenue),
        received_revenue_month=received_decimal,
        expenses_month=expenses_decimal,
        pending_expenses_month=_decimal(pending_expenses),
        monthly_balance=received_decimal - expenses_decimal,
        overdue_students_count=overdue_students,
        total_overdue_amount=_decimal(total_overdue),
        average_cost_per_student=average_cost.quantize(Decimal("0.01")),
        cash_cost_per_student=cash_cost.quantize(Decimal("0.01")),
    )


def get_dashboard_summary(db: Session, reference_date: date | None = None) -> DashboardSummary:
    today = date.today()
    current_snapshot = _build_snapshot(db, reference_date or today, today)
    previous_snapshot = _build_snapshot(db, _previous_month(current_snapshot.period_start), today)

    return DashboardSummary(
        reference_month=current_snapshot.reference_month,
        period_start=current_snapshot.period_start,
        period_end=current_snapshot.period_end,
        reference_date=current_snapshot.reference_date,
        comparison_month=previous_snapshot.reference_month,
        total_active_students=current_snapshot.total_active_students,
        expected_revenue_month=current_snapshot.expected_revenue_month,
        received_revenue_month=current_snapshot.received_revenue_month,
        expenses_month=current_snapshot.expenses_month,
        pending_expenses_month=current_snapshot.pending_expenses_month,
        monthly_balance=current_snapshot.monthly_balance,
        overdue_students_count=current_snapshot.overdue_students_count,
        total_overdue_amount=current_snapshot.total_overdue_amount,
        average_cost_per_student=current_snapshot.average_cost_per_student,
        cash_cost_per_student=current_snapshot.cash_cost_per_student,
        expected_revenue_delta=current_snapshot.expected_revenue_month - previous_snapshot.expected_revenue_month,
        received_revenue_delta=current_snapshot.received_revenue_month - previous_snapshot.received_revenue_month,
        expenses_delta=current_snapshot.expenses_month - previous_snapshot.expenses_month,
        pending_expenses_delta=current_snapshot.pending_expenses_month - previous_snapshot.pending_expenses_month,
        monthly_balance_delta=current_snapshot.monthly_balance - previous_snapshot.monthly_balance,
        overdue_students_delta=current_snapshot.overdue_students_count - previous_snapshot.overdue_students_count,
        total_overdue_amount_delta=current_snapshot.total_overdue_amount - previous_snapshot.total_overdue_amount,
        average_cost_per_student_delta=current_snapshot.average_cost_per_student - previous_snapshot.average_cost_per_student,
        cash_cost_per_student_delta=current_snapshot.cash_cost_per_student - previous_snapshot.cash_cost_per_student,
    )
